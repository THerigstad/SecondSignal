"""Order R1M, 6 October 2026: offline vocabulary measurements, no policy edits.

Run from the repository root:
    python evals/vocabulary/measure_vocabulary_candidates.py

An alarm means HIT or INCONCLUSIVE, following the existing fail-closed screen.
Controls are evidence of overlap, not automatically evidence of a false alarm.
The supplied pack format has masks and crisis classes but no recovery aliases;
the requested alias dry run therefore remains explicitly unmeasured.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import socket
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from secondsignal.lexicon import PACKS, apply_masks, screen_packs  # noqa: E402
from secondsignal.normalize import analyze, screen_fold  # noqa: E402
from secondsignal.safety import crisis_screen  # noqa: E402

HERE = ROOT / "evals/vocabulary"
INPUT = HERE / "vocabulary_2026-10-06.json"
OUTPUT = HERE / "measurements/candidates_2026-10-06.json"
CARRIERS = (
    'The glossary includes the expression "{term}".',
    'I wrote "{term}" in my notebook.',
    'We discussed the meaning of "{term}" at the workshop.',
)
CATEGORIES = {
    "recovery", "gender_identity", "sexuality", "neurodivergence",
    "identity_statement", "other",
}
USES = {"recognise", "never_alarm", "respect", "none", "withheld_from_tree"}
FIELDS = {
    "term", "variants", "category", "meaning", "register", "sources", "systems",
    "agreement", "already_carried", "proposed_use", "note",
}
DOORS = {
    "ChatGPT, the app on the operator's PC, Chat",
    "DeepSeek, chat.deepseek.com",
    "Perplexity, Search mode, GPT-6 Sol Thinking",
    "Perplexity, Search mode, Grok 4.7 Thinking, first thread",
    "Perplexity, Search mode, Grok 4.7 Thinking, second thread",
    "Perplexity, Search mode, Grok 4.7",
    "Grok, grok.com, Expert",
}
WITHHELD_MEANING = "A sensitive term is retained only in the operator-only record."
ALIAS_REASON = (
    "Not measured: this tree's Pack and load_pack support masks, hits and "
    "inconclusive patterns, but no recovery alias or alias scope. "
    "Recovery terms are in signals.py; inventing alias semantics requires an operator ruling."
)


def validate(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Vocabulary must be a nonempty list")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("Every vocabulary record must have exactly the required fields")
        for field in ("term", "meaning", "register", "note"):
            if not isinstance(row[field], str) or not row[field].strip():
                raise ValueError(f"Missing text in {field}")
        if row["category"] not in CATEGORIES or row["proposed_use"] not in USES:
            raise ValueError("Unknown category or proposed use")
        if row["agreement"] not in {"agree", "differ", "single"}:
            raise ValueError("Unknown agreement")
        if not isinstance(row["variants"], list) or any(
            not isinstance(value, str) or not value for value in row["variants"]
        ):
            raise ValueError("Variants must be nonempty strings")
        sources = row["sources"]
        if not isinstance(sources, list) or not sources:
            raise ValueError("Every record must retain a contributing door")
        for source in sources:
            if set(source) != {"door", "citation"} or not isinstance(source["door"], str):
                raise ValueError("Invalid source")
            if source["door"] not in DOORS:
                raise ValueError("Unknown source door")
            if source["citation"] is not None and not isinstance(source["citation"], str):
                raise ValueError("Invalid citation")
        if all(source["citation"] is None for source in sources) and "uncited" not in row["note"].lower():
            raise ValueError("A term without a citation must be marked uncited")
        if type(row["systems"]) is not int or row["systems"] != len({s["door"] for s in sources}):
            raise ValueError("Systems must count distinct doors")
        if not 1 <= row["systems"] <= 7:
            raise ValueError("Invalid system count")
        if (row["agreement"] == "single") != (row["systems"] == 1):
            raise ValueError("Single must describe exactly one door")
        if row["agreement"] == "differ" and "differ" not in row["note"].lower():
            raise ValueError("A conflict needs its explanation")
        carried = row["already_carried"]
        if carried is not None:
            if (not isinstance(carried, str) or Path(carried).is_absolute()
                    or not (ROOT / carried).resolve().is_relative_to(ROOT)
                    or not (ROOT / carried).is_file()):
                raise ValueError("Already-carried references must name a tree file")
            if row["proposed_use"] == "recognise":
                raise ValueError("Already-carried terms cannot be proposed again")
        if row["proposed_use"] == "withheld_from_tree":
            if not re.fullmatch(r"a (?:reclaimed|sensitive|sexual) term for [a-z_]+ \(withheld [0-9]{3}\)", row["term"]):
                raise ValueError("Withheld term must be a neutral numbered placeholder")
            if row["variants"] or row["meaning"] != WITHHELD_MEANING:
                raise ValueError("Withheld variants and meaning may not carry spellings")
        key = (row["category"], row["term"].casefold())
        if key in seen:
            raise ValueError("Duplicate term")
        seen.add(key)
    if rows != sorted(rows, key=lambda r: (r["category"], r["term"].casefold())):
        raise ValueError("Records must be sorted by category then term")


def source_snapshot():
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "src").rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def literal_constants(path, names):
    found = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    found[target.id] = ast.literal_eval(node.value)
    if set(found) != set(names):
        raise ValueError(f"Control list inventory changed in {path.name}")
    return found


def load_controls():
    """The full B3/B5b ordinary corpora, including known over-restrictions.

    PROCEED fixtures describe ordinary *safety* even if recovery is their topic.
    Such a lexical overlap is reported, not labelled a recovery false positive.
    tests/data has one harness reply block on this tree and no control word list.
    """
    rows = []
    relative = "tests/test_crisis_gate.py"
    constants = literal_constants(ROOT / relative, (
        "CONTROLS", "SPOKEN_SURFACE_CONTROLS", "INTERNET_SLANG_DEATH_CONTROLS",
    ))
    for name, texts in constants.items():
        for index, text in enumerate(texts, 1):
            rows.append({"id": f"{name}:{index:02d}", "text": text, "source": relative,
                         "group": "literal_three_lists"})
    relative = "evals/gap_triage/measure_cheap.py"
    texts = literal_constants(ROOT / relative, ("RECOVERY_EVERYDAY_CONTROLS",))
    for index, text in enumerate(texts["RECOVERY_EVERYDAY_CONTROLS"], 1):
        rows.append({"id": f"recovery-everyday-{index:02d}", "text": text,
                     "source": relative, "group": "recovery_everyday"})
    for relative, field, group in (
        ("evals/gap_triage/digit_token_controls_2026-10-05.json", "cases", "digit_tokens"),
        ("evals/fuzz/measurements/non_latin_controls_2026-10-04.json", "controls", "non_latin"),
    ):
        for case in json.loads((ROOT / relative).read_text(encoding="utf-8"))[field]:
            rows.append({"id": case["id"], "text": case["text"], "source": relative,
                         "group": group})
    for path in sorted((ROOT / "evals/cases").rglob("*.json")):
        if "deferred" in path.parts:
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("kind") == "trajectory":
            continue
        if document.get("plane", "policy") != "policy":
            continue
        for case in document.get("cases", []):
            if case.get("expect", {}).get("safety") == "PROCEED":
                rows.append({"id": case["id"], "text": case["text"],
                             "source": path.relative_to(ROOT).as_posix(),
                             "group": "policy_proceed"})
    return rows


def phrase_pattern(term):
    """Whole phrases, folding case, hyphens and whitespace, without substring hits."""
    pieces = re.split(r"[\s\-\u2010-\u2015]+", term.strip())
    return re.compile(r"(?<!\w)" + r"[\s\-\u2010-\u2015]*".join(
        re.escape(piece) for piece in pieces
    ) + r"(?!\w)", re.IGNORECASE)


def control_occurrences(forms, controls):
    found = []
    for control in controls:
        matched = [form for form in forms if phrase_pattern(form).search(control["text"])]
        if matched:
            found.append({key: value for key, value in control.items() if key != "text"} | {
                "matched_forms": matched,
            })
    return found


def screen(text):
    result = crisis_screen(text)
    return {"text": text, "read": result.read, "alarm": result.read != "MISS",
            "pattern_ids": sorted({span.pattern_id for span in result.hit_spans}),
            "folds": list(result.screen_folds)}


def pack_matches(forms):
    """Actual individual-pack mask/hit matches, with scopes from the shipped loader."""
    found = []
    for form in forms:
        for carrier_index, text in enumerate((form, *(c.format(term=form) for c in CARRIERS))):
            for crisis_only in (False, True):
                norm = analyze(text).text
                if crisis_only:
                    norm, _ = screen_fold(norm)
                for pack in PACKS.values():
                    masked, masks = apply_masks(norm, (pack,), crisis_only=crisis_only)
                    hits, inconclusive = screen_packs(masked, (pack,)) if crisis_only else ((), ())
                    for span in (*masks, *hits, *inconclusive):
                        scope = "crisis_only" if span.kind != "mask" or span.pattern_id in pack.crisis_only_masks else "all_screens"
                        item = {"form": form, "carrier": carrier_index, "pack": pack.id,
                                "kind": span.kind, "pattern_id": span.pattern_id,
                                "scope": scope, "domain": span.domain}
                        if item not in found:
                            found.append(item)
    return found


def alias_capability():
    """Load an independent raw pack copy; do not invent unsupported alias fields."""
    pack = copy.deepcopy(json.loads((ROOT / "src/secondsignal/packs/en.json").read_text(encoding="utf-8")))
    if "recovery_aliases" in pack or "aliases" in pack:
        raise ValueError("Pack format changed: review alias semantics before rerunning R1M")
    return {"status": "unavailable", "scope": None, "collides": None,
            "collisions": None, "reason": ALIAS_REASON}


def run_report(rows):
    validate(rows)
    before = source_snapshot()
    controls = load_controls()
    results = []
    for row in rows:
        if row["proposed_use"] not in {"recognise", "never_alarm"}:
            continue
        forms = list(dict.fromkeys([row["term"], *row["variants"]]))
        alone = screen(row["term"])
        carriers = [screen(carrier.format(term=row["term"])) for carrier in CARRIERS]
        variants = [{"form": form, "alone": screen(form),
                     "carriers": [screen(c.format(term=form)) for c in CARRIERS]}
                    for form in forms[1:]]
        alarms = alone["alarm"] or any(x["alarm"] for x in carriers) or any(
            v["alone"]["alarm"] or any(c["alarm"] for c in v["carriers"]) for v in variants
        )
        overlap = control_occurrences(forms, controls)
        recovery = row["category"] == "recovery" and row["proposed_use"] == "recognise"
        alias = alias_capability() if recovery else {"status": "not_applicable"}
        status = "alarm" if alarms else "control_overlap" if overlap else "unmeasured_alias" if recovery else "clean"
        results.append({"term": row["term"], "category": row["category"],
                        "proposed_use": row["proposed_use"], "term_alone": alone,
                        "neutral_carriers": carriers, "variant_screens": variants,
                        "pack_matches": pack_matches(forms), "control_occurrences": overlap,
                        "recovery_alias_dry_run": alias, "any_alarm": bool(alarms),
                        "assessment": status})
    recognised = [r for r in results if r["proposed_use"] == "recognise"]
    summary = {
        "measured_terms": len(results), "recognise_candidates": len(recognised),
        "recognise_clean": sum(r["assessment"] == "clean" for r in recognised),
        "recognise_with_alarm": [r["term"] for r in recognised if r["any_alarm"]],
        "recognise_control_overlaps": [
            {"term": r["term"], "controls": [c["id"] for c in r["control_occurrences"]]}
            for r in recognised if r["control_occurrences"]
        ],
        "recovery_alias_unmeasured": sum(r["recovery_alias_dry_run"]["status"] == "unavailable" for r in recognised),
        "alias_collisions": None,
        "never_alarm_current_alarms": [r["term"] for r in results if r["proposed_use"] == "never_alarm" and r["any_alarm"]],
    }
    after = source_snapshot()
    if before != after:
        raise RuntimeError("Source files changed during measurement")
    return {"schema_version": 1, "date": "2026-10-06", "measurement_only": True,
            "carriers": list(CARRIERS), "alarm_definition": "HIT or INCONCLUSIVE",
            "control_counts": dict(sorted(Counter(c["group"] for c in controls).items())),
            "control_overlap_definition": "Whole-phrase occurrence of term or a listed variant; not a proven alias collision.",
            "tests_data_inventory": [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "tests/data").rglob("*")) if p.is_file()],
            "source_files_unchanged": True, "summary": summary, "candidates": results}


def print_summary(report):
    summary = report["summary"]
    print(f"Measured terms: {summary['measured_terms']}; recognise candidates: {summary['recognise_candidates']}")
    print(f"Recognise clean (no alarm, no control overlap, no pending alias check): {summary['recognise_clean']}")
    print("Recognise alarms: " + (", ".join(summary["recognise_with_alarm"]) or "none"))
    print(f"Recognise control overlaps: {len(summary['recognise_control_overlaps'])}")
    for row in summary["recognise_control_overlaps"]:
        print("  " + row["term"] + ": " + ", ".join(row["controls"]))
    print(f"Recovery alias collision checks unavailable: {summary['recovery_alias_unmeasured']}; collision count unknown")
    print("Never-alarm terms alarming today: " + (", ".join(summary["never_alarm_current_alarms"]) or "none"))
    print("Source files unchanged: yes; network: blocked; model calls: none")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    destination = args.output.resolve()
    if destination.is_relative_to((ROOT / "src").resolve()):
        raise ValueError("Output under src is forbidden")
    rows = json.loads(args.input.read_text(encoding="utf-8"))

    def no_network(*args, **kwargs):
        raise RuntimeError("R1M measurement forbids network access")

    with patch.object(socket.socket, "connect", no_network), patch.object(socket.socket, "connect_ex", no_network), patch.object(socket, "create_connection", no_network):
        report = run_report(rows)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if len(payload.encode("utf-8")) >= 2_000_000:
        raise ValueError("Report exceeds the order's file-size limit")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload, encoding="utf-8")
    print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
