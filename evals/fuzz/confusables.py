"""B1 measurement of the supplied confusables table; never production policy.

Eligibility is decided *before casefold*: a single-codepoint source must list
exactly one distinct, literal ASCII letter. Its target is then lowercased. A
look-alike such as long s is not an ASCII letter merely because it casefolds
to one. The map is literal: ASCII sources, digits, and punctuation are not
silently exempted. In particular I -> l and l -> i are real table hazards.

The candidate translates raw text once, simultaneously, and passes that text
to the unchanged route. The real gate still does NFKC, its reviewed skeleton,
and casefold; this pre-route experiment is not an exact replacement of the
internal skeleton. No monkeypatch or policy mutation occurs here.
"""

from __future__ import annotations

import hashlib
import json
import re
import string
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from secondsignal import route
from secondsignal.normalize import SKELETON, normalize

from .run import _prior_text, _session

TABLE_PATH = Path(__file__).with_name("confusables_3.3.1.json")
TABLE_SHA256 = "2d8b4774cd9dc6f233a18681bc00423ae270037437f276fc6a8b80630941fe7d"
NON_LATIN_PATH = Path(__file__).with_name("measurements") / "non_latin_controls_2026-10-04.json"
CARD = "HUMAN_ESCALATION"
_WORDS = re.compile(r"[^\W\d_]+", re.UNICODE)


def full_fold_map() -> dict[str, str]:
    """Read the fixed table and return unambiguous literal ASCII targets.

    Exactly-one eligibility applies before casefold, to the distinct listed
    ASCII letters. The resulting ASCII target is casefolded only afterwards,
    so case-insensitive fixture enumeration uses one target per letter.
    """
    data = TABLE_PATH.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != TABLE_SHA256:
        raise ValueError(f"confusables table SHA-256 mismatch: {actual}")
    table = json.loads(data)
    result = {}
    for source, lookalikes in table.items():
        if len(source) != 1:
            continue
        targets = {
            item["c"] for item in lookalikes
            if len(item["c"]) == 1 and item["c"] in string.ascii_letters
        }
        if len(targets) == 1:
            result[source] = next(iter(targets)).casefold()
    return dict(sorted(result.items(), key=lambda pair: ord(pair[0])))


def full_fold(text: str, fold_map: dict[str, str] | None = None) -> str:
    """Translate each raw code point once; never recursively re-fold targets."""
    mapping = full_fold_map() if fold_map is None else fold_map
    return "".join(mapping.get(character, character) for character in text)


def script_from_name(character: str) -> str:
    """A reproducible name-derived grouping, not Unicode's Script property.

    Name families such as MATHEMATICAL, FULLWIDTH, and SYMBOL_OR_OTHER remain
    explicit because the bundled table does not provide the Script property.
    This avoids guessing that a styled Greek letter must be Latin.
    """
    name = unicodedata.name(character, "UNNAMED")
    prefixes = (
        "CANADIAN SYLLABICS", "OLD ITALIC", "OLD PERMIC", "OLD TURKIC",
        "WARANG CITI", "AHOM", "ARMENIAN", "BAMUM", "BENGALI", "CARIAN",
        "CHEROKEE", "COPTIC", "CYRILLIC", "DESERET", "DEVANAGARI",
        "ELBASAN", "ETHIOPIC", "GEORGIAN", "GREEK", "GUJARATI",
        "GURMUKHI", "KANNADA", "LAO", "LATIN", "LISU", "LYCIAN",
        "MALAYALAM", "MIAO", "MYANMAR", "ORIYA", "OSAGE", "RUNIC",
        "SINHALA", "TAMIL", "TELUGU", "THAI", "TIFINAGH", "TIRHUTA",
        "MATHEMATICAL", "FULLWIDTH", "HALFWIDTH",
    )
    return next((prefix for prefix in prefixes if name.startswith(prefix + " ")), "SYMBOL_OR_OTHER")


def _route(case: dict[str, Any], text: str, roster) -> dict[str, Any]:
    session = _session(case)
    for prior in case.get("prior_turns", []):
        route(_prior_text(prior), roster, session=session)
    record = route(text, roster, session=session).to_dict()
    safety = record["safety"]
    return {
        "action": str(safety["action"]),
        "agent_id": record.get("agent_id"),
        "crisis_read": safety["crisis_read"],
        "language_scope": safety["language_scope"],
        "crisis_classes": safety["crisis_classes"],
    }


def _map_metadata(mapping: dict[str, str]) -> dict[str, Any]:
    overlap = mapping.keys() & SKELETON.keys()
    conflicts = [
        {"character": ch, "codepoint": f"U+{ord(ch):04X}",
         "full_target": mapping[ch], "current_target": SKELETON[ch]}
        for ch in sorted(overlap, key=ord)
        if SKELETON[ch].casefold() != mapping[ch]
    ]
    return {
        "size": len(mapping),
        "table_sha256": TABLE_SHA256,
        "unicode_database_version": unicodedata.unidata_version,
        "current_skeleton_key_overlap": len(overlap),
        "current_skeleton_same_target": len(overlap) - len(conflicts),
        "current_skeleton_conflicts": conflicts,
        "effective_current_normalize_covered": sum(normalize(ch) == target for ch, target in mapping.items()),
        "eligible_variant_source_codepoints": len(mapping.keys() - SKELETON.keys()),
        "eligible_but_already_effectively_normalized": sum(
            normalize(ch) == target for ch, target in mapping.items() if ch not in SKELETON
        ),
        "ascii_sources": [
            {"character": ch, "codepoint": f"U+{ord(ch):04X}", "target": target}
            for ch, target in mapping.items() if ch.isascii()
        ],
    }


def _control_results(cases, roster, mapping, vocabulary=()) -> dict[str, Any]:
    rows = []
    vocabulary = set(vocabulary)
    for case in cases:
        baseline = _route(case, case["text"], roster)
        folded = full_fold(case["text"], mapping)
        candidate = _route(case, folded, roster)
        raw_vocabulary = sorted(set(_WORDS.findall(folded.casefold())) & vocabulary)
        normalized_vocabulary = sorted(set(_WORDS.findall(normalize(folded))) & vocabulary)
        rows.append({
            **{key: value for key, value in case.items() if key in {"id", "language", "group", "text"}},
            # Native controls need their English gloss; policy fixture rationale
            # stays in its original source document, identified by case id.
            **({"why": case["why"]} if "group" in case and "why" in case else {}),
            "folded_text": folded,
            "baseline": baseline,
            "candidate": candidate,
            "new_card": baseline["action"] != CARD and candidate["action"] == CARD,
            "false_alarm_from_proceed": baseline["action"] == "PROCEED" and candidate["action"] == CARD,
            "candidate_card_or_non_miss": candidate["action"] == CARD or candidate["crisis_read"] != "MISS",
            "new_card_or_non_miss": (
                baseline["action"] != CARD and baseline["crisis_read"] == "MISS"
                and (candidate["action"] == CARD or candidate["crisis_read"] != "MISS")
            ),
            "folded_vocabulary_words": raw_vocabulary,
            "after_gate_normalize_vocabulary_words": normalized_vocabulary,
        })
    return {
        "total": len(rows),
        "baseline_proceed": sum(row["baseline"]["action"] == "PROCEED" for row in rows),
        "baseline_cards": sum(row["baseline"]["action"] == CARD for row in rows),
        "baseline_non_miss": sum(row["baseline"]["crisis_read"] != "MISS" for row in rows),
        "candidate_cards": sum(row["candidate"]["action"] == CARD for row in rows),
        "candidate_non_miss": sum(row["candidate"]["crisis_read"] != "MISS" for row in rows),
        "candidate_card_or_non_miss": sum(row["candidate_card_or_non_miss"] for row in rows),
        "new_cards": sum(row["new_card"] for row in rows),
        "false_alarms_from_proceed": sum(row["false_alarm_from_proceed"] for row in rows),
        "new_card_or_non_miss": sum(row["new_card_or_non_miss"] for row in rows),
        "folded_contains_vocabulary": sum(bool(row["folded_vocabulary_words"]) for row in rows),
        "after_gate_normalize_contains_vocabulary": sum(bool(row["after_gate_normalize_vocabulary_words"]) for row in rows),
        "rows": rows,
    }


def measure_confusables(
    lines, control_sentences, control_cases, vocabulary, roster,
    fold_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return all Part 2 observations; the caller writes measurement artifacts.

    ``lines`` and controls are case dictionaries, with ``id`` and ``text``;
    labelled cases retain their own session and prior turns. ``fold_map`` is
    an optional explicit subset for a small report-shape test. By default the
    complete map is used. Every source absent from SKELETON is enumerated,
    even if NFKC already handles it. Current SKELETON keys are excluded even
    when their targets conflict, as specified by 'NOT folded by the current
    skeleton'; overlaps, disagreements and effective coverage are separate.
    """
    mapping = full_fold_map() if fold_map is None else dict(sorted(fold_map.items(), key=lambda pair: ord(pair[0])))
    sources = defaultdict(list)
    for character, target in mapping.items():
        if character not in SKELETON:
            sources[target].append(character)
    by_target = defaultdict(lambda: {"tried": 0, "failed": 0, "recovered": 0})
    by_script = defaultdict(lambda: {"tried": 0, "failed": 0, "recovered": 0})
    rows = []
    failed_cases: set[str] = set()
    recovered_cases: set[str] = set()
    unchanged_variants = 0
    for case in lines:
        text = case["text"]
        first_positions = {}
        for index, character in enumerate(text):
            if character in string.ascii_letters:
                first_positions.setdefault(character.casefold(), index)
        for target, index in sorted(first_positions.items()):
            for character in sources.get(target, ()):
                variant = text[:index] + character + text[index + 1:]
                unchanged_variants += variant == text
                baseline = _route(case, variant, roster)
                failed = baseline["action"] != CARD
                folded = full_fold(variant, mapping) if failed else None
                candidate = _route(case, folded, roster) if failed else None
                recovered = bool(candidate and candidate["action"] == CARD)
                group = script_from_name(character)
                for counter in (by_target[target], by_script[group]):
                    counter["tried"] += 1
                    counter["failed"] += failed
                    counter["recovered"] += recovered
                if failed:
                    failed_cases.add(case["id"])
                if recovered:
                    recovered_cases.add(case["id"])
                rows.append({
                    "case_id": case["id"], "target_letter": target,
                    "replaced_character": text[index], "replacement_index": index,
                    "character": character, "codepoint": f"U+{ord(character):04X}",
                    "unicode_name": unicodedata.name(character, "UNNAMED"),
                    "script_from_name": group,
                    "already_effectively_normalized": normalize(character) == target,
                    "variant": variant, "baseline": baseline,
                    "failed_today": failed, "candidate_text": folded,
                    "candidate": candidate, "recovered": recovered,
                })
    non_latin_doc = json.loads(NON_LATIN_PATH.read_text(encoding="utf-8"))
    non_latin_cases = non_latin_doc["controls"]
    retention = []
    for case in lines:
        folded = full_fold(case["text"], mapping)
        candidate = _route(case, folded, roster)
        retention.append({
            "case_id": case["id"], "text": case["text"], "folded_text": folded,
            "baseline": _route(case, case["text"], roster),
            "candidate": candidate, "lost_card": candidate["action"] != CARD,
        })
    return {
        "methodology": {
            "map_eligibility": "Before casefold: exactly one distinct literal ASCII letter among listed look-alikes; target casefolded only after eligibility.",
            "variant_letters": "Distinct ASCII letters are casefolded to lowercase; replace the first ASCII occurrence case-insensitively.",
            "excluded_sources": "All keys in the reviewed SKELETON are excluded; NFKC-only coverage is not excluded.",
            "candidate": "One simultaneous full-table translation of raw text before unchanged route; NFKC and reviewed skeleton still run inside gate. This is the requested text-fold experiment, not an exact internal skeleton replacement.",
            "candidate_scope": "Every failing variant is routed after folding; passing variants are not re-routed and loss of their existing coverage is not estimated by the recovery count.",
            "script_grouping": "Name-derived script or explicit name family, not the Unicode Script property; mathematical/fullwidth/halfwidth and symbols stay distinct.",
            "false_alarm": "A baseline PROCEED that becomes HUMAN_ESCALATION. Total candidate cards and any newly carded non-card baseline are also recorded.",
            "vocabulary": "Whole letters-only words, casefolded; report both the direct folded string and its subsequent current gate normalization.",
        },
        "map": _map_metadata(mapping),
        "lines": len(lines),
        "total_variants": len(rows),
        "unchanged_variants": unchanged_variants,
        "today_failed_variants": sum(row["failed_today"] for row in rows),
        "affected_lines": len(failed_cases),
        "candidate_recovered_variants": sum(row["recovered"] for row in rows),
        "candidate_recovered_lines": len(recovered_cases),
        "original_crisis_retention": {
            "total": len(retention),
            "retained_cards": sum(not row["lost_card"] for row in retention),
            "lost_cards": sum(row["lost_card"] for row in retention),
            "rows": retention,
        },
        "by_target": dict(sorted(by_target.items())),
        "by_script": dict(sorted(by_script.items())),
        "variants": rows,
        "controls": {
            "sentences": _control_results(control_sentences, roster, mapping, vocabulary),
            "cases": _control_results(control_cases, roster, mapping, vocabulary),
        },
        "non_latin": _control_results(non_latin_cases, roster, mapping, vocabulary),
    }
