"""B5b offline measurement; no production edits or disposition changes.

Run: python evals/gap_triage/measure_rest.py
All transformations are defined here and touch copied inputs only. The routing
experiment for recovery aliases is explicitly separate from the required
crisis-only result, because recovery claims are not made by crisis_screen.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import socket
import string
import sys
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from evals.fuzz import confusables as cf  # noqa: E402
from evals.fuzz import measure_causes as b1  # noqa: E402
from evals.fuzz.run import crisis_lines  # noqa: E402
from evals.fuzz.transforms import TRANSFORMS  # noqa: E402
from evals.gap_triage import measure_cheap as cheap  # noqa: E402
from secondsignal import load_roster  # noqa: E402
from secondsignal.normalize import SKELETON  # noqa: E402

HERE = ROOT / "evals/gap_triage"
CARD = "HUMAN_ESCALATION"
WORD = re.compile(r"[^\W\d_]+")
VOCABULARY = cheap.VOCABULARY
B7_CONTROL_FILES = {
    "identity_pairs_grok_2026-09-30", "neurodivergent_grok_2026-09-30",
}


def words(text):
    return {m.group().casefold() for m in WORD.finditer(text)}


def everyday_vocabulary(controls):
    """Every source text/prior, README, and prose outside Markdown code fences.

    No labelled failure variants enter the guard except when they already occur
    in the required documentation/PROCEED corpus. This is a corpus guard, not an
    independent held-out English dictionary. Inline code is kept conservatively.
    """
    vocabulary = set()
    sources = []
    for name in ("literal_three_lists", "policy_proceed", "digit_tokens"):
        texts = []
        for case in controls[name]:
            texts.append(case["text"])
            texts.extend(p["text"] if isinstance(p, dict) else p
                         for p in case.get("prior_turns", []))
        content = "\n".join(texts)
        vocabulary.update(words(content))
        sources.append({"source": name, "cases": len(controls[name]),
                        "sha256": hashlib.sha256(content.encode()).hexdigest()})
    paths = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        prose = re.sub(r"(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", content)
        vocabulary.update(words(prose))
        sources.append({"source": path.relative_to(ROOT).as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return frozenset(vocabulary), sources


def make_guarded_matcher(everyday, *, unique_only=False):
    targets = defaultdict(set)
    for word in VOCABULARY:
        for index in range(len(word)):
            targets[word[:index] + word[index + 1:]].add(word)
        for index in range(len(word) - 1):
            if word[index] != word[index + 1]:
                targets[word[:index] + word[index + 1] + word[index]
                        + word[index + 2:]].add(word)

    def options(token):
        token = token.casefold()
        if token in everyday or token in VOCABULARY:
            return ()
        return tuple(sorted(targets.get(token, ())))

    def transform(text):
        def replace(match):
            choices = options(match.group())
            # Match B5's lexical tie convention; retain unique-only sensitivity.
            return choices[0] if choices and (not unique_only or len(choices) == 1) else match.group()
        return WORD.sub(replace, text)
    return transform, options


def corrected_confusables_map():
    mapping = {ch: target for ch, target in cf.full_fold_map().items()
               if not ch.isascii()}
    conflicts = []
    for ch in mapping.keys() & SKELETON.keys():
        if mapping[ch] != SKELETON[ch].casefold():
            conflicts.append({"character": ch, "old": mapping[ch], "kept": SKELETON[ch]})
            mapping[ch] = SKELETON[ch]
    return mapping, sorted(conflicts, key=lambda row: ord(row["character"]))


def narrow_folds(text):
    """Port B5's exact complete-run separator then <=6 look-alike policy."""
    lookalikes = {"0": "o", "1": "il", "3": "e", "4": "a", "5": "s",
                  "7": "t", "8": "b", "@": "a", "$": "s", "!": "i"}
    char = r"[a-z0-9@$!]"
    separated = re.compile(r"(?<![\w@$!])" + char + r"(?:[ ._-]" + char + r")+(?![\w@$!])", re.I)
    token = re.compile(r"(?<![\w@$!])[a-z0-9@$!]+(?![\w@$!])", re.I)
    text = separated.sub(lambda match: re.sub(r"[ ._-]", "", match.group()), text)

    def replace(match):
        value = match.group()
        if len(value) > 6 or not any(ch in lookalikes for ch in value):
            return value
        choices = itertools.product(*(lookalikes.get(ch, ch) for ch in value.lower()))
        options = sorted({"".join(chars) for chars in choices} & VOCABULARY)
        return options[0] if options else value
    return token.sub(replace, text)


WIDER_QUOTES = frozenset("\"'\u2018\u2019\u201c\u201d")
WIDER_PLAIN_TOKEN = re.compile(r"(?<!\w)[a-z]+(?!\w)", re.IGNORECASE)
WIDER_FRAGMENT = re.compile(r"(?<![^\W_])[a-zA-Z]+(?![^\W_])")


def wider_join_punctuation(text: str, *, quotes: bool) -> str:
    """Join alphabetic fragments only if their complete joined run is a word.

    Quote folding admits only quotes/apostrophes. Symbol folding admits Unicode
    punctuation and symbols except quotes, spaces, and the narrow separator
    set; those last partial boundaries belong to the partial-split candidate.
    The runs cannot contain digits, and a symbol never substitutes for a letter.
    """
    def admitted(char: str) -> bool:
        if quotes:
            return char in WIDER_QUOTES
        return (
            char not in WIDER_QUOTES
            and char not in " ._-"
            and unicodedata.category(char)[0] in "PS"
        )

    # A maximal connected run includes all its letter pieces: a vocabulary
    # substring inside a larger punctuated token does not qualify on its own.
    output: list[str] = []
    cursor = 0
    while cursor < len(text):
        if not text[cursor].isascii() or not text[cursor].isalpha():
            output.append(text[cursor])
            cursor += 1
            continue
        start = cursor
        while cursor < len(text) and text[cursor].isascii() and text[cursor].isalpha():
            cursor += 1
        letters = text[start:cursor]
        has_separator = False
        while cursor < len(text):
            end = cursor
            while end < len(text) and admitted(text[end]):
                end += 1
            if end == cursor or end == len(text) or not (
                text[end].isascii() and text[end].isalpha()
            ):
                break
            next_end = end
            while next_end < len(text) and text[next_end].isascii() and text[next_end].isalpha():
                next_end += 1
            letters += text[end:next_end]
            cursor = next_end
            has_separator = True
        bounded = (
            (start == 0 or not (text[start - 1].isalnum() or text[start - 1] == "_"))
            and (cursor == len(text) or not (text[cursor].isalnum() or text[cursor] == "_"))
        )
        output.append(
            letters.lower()
            if bounded and has_separator and letters.lower() in cheap.VOCABULARY
            else text[start:cursor]
        )
    return "".join(output)


def wider_quotes(text: str) -> str:
    return wider_join_punctuation(text, quotes=True)


def wider_symbols(text: str) -> str:
    return wider_join_punctuation(text, quotes=False)


def wider_split_words(
    text: str, separators: frozenset[str], *, allow_interior_marks: bool = False
) -> str:
    """Join two or three fragments with an exact unique vocabulary target.

    At least one fragment must have <=2 letters, and at least one >1: complete
    runs of single letters are owned by the narrow fold. Longest admissible
    fragment span wins; scans resume after it. No arbitrary sentence-wide
    whitespace deletion or fuzzy spelling repair is performed.
    """
    def allowed_gap(gap: str) -> bool:
        if not gap:
            return False
        if all(char in separators for char in gap):
            return True
        # Existing normalize() already removes these categories between Latin
        # letters. A space created by the filler removal prevented that context
        # check; test precisely this combination as a vocabulary-gated partial
        # split, never stripping marks from arbitrary other-script text.
        return (
            allow_interior_marks
            and any(char in separators for char in gap)
            and all(
                char in separators or unicodedata.category(char) in {"Cf", "Mn", "Me"}
                for char in gap
            )
        )

    words = list(WIDER_FRAGMENT.finditer(text))
    output: list[str] = []
    cursor = 0
    index = 0
    while index < len(words):
        first = words[index]
        selected = None
        for count in (3, 2):
            pieces = words[index:index + count]
            if len(pieces) != count:
                continue
            lengths = [len(part.group()) for part in pieces]
            if min(lengths) > 2 or max(lengths) == 1:
                continue
            between = [text[left.end():right.start()] for left, right in pairwise(pieces)]
            if not all(allowed_gap(gap) for gap in between):
                continue
            joined = "".join(part.group() for part in pieces).lower()
            if joined in cheap.VOCABULARY:
                selected = (count, pieces[-1].end(), joined)
                break
        if selected is None:
            index += 1
            continue
        count, end, joined = selected
        output.extend((text[cursor:first.start()], joined))
        cursor = end
        index += count
    output.append(text[cursor:])
    return "".join(output)


def wider_whitespace(text: str) -> str:
    """Spacing has already erased tab/newline provenance; ordinary space too."""
    return wider_split_words(text, frozenset(" \t\r\n"))


def wider_partial(text: str) -> str:
    return wider_split_words(text, frozenset(" ._-\t\r\n"), allow_interior_marks=True)


def wider_doubled(text: str) -> str:
    """Delete exactly one duplicated letter, with one unique vocabulary word."""
    def replace(match: re.Match[str]) -> str:
        token = match.group().lower()
        if token in cheap.VOCABULARY:
            return match.group()
        targets = {
            token[:repeat.start()] + token[repeat.start() + 1:]
            for repeat in re.finditer(r"([a-z])\1", token)
        } & cheap.VOCABULARY
        return next(iter(targets)) if len(targets) == 1 else match.group()
    return WIDER_PLAIN_TOKEN.sub(replace, text)


def wider_all(text: str) -> str:
    for fold in (wider_quotes, wider_symbols, wider_partial, wider_doubled):
        text = fold(text)
    return text


def wider_transforms() -> dict[str, Callable[[str], str]]:
    folds = {
        "wider_quotes": wider_quotes,
        "wider_tabs_newlines": wider_whitespace,
        "wider_inserted_symbols": wider_symbols,
        "wider_doubled_letters": wider_doubled,
        "wider_partial_splits": wider_partial,
        "wider_all": wider_all,
    }
    return {
        name: lambda text, fold=fold: fold(narrow_folds(text))
        for name, fold in folds.items()
    }


def wider_residual_reason(text: str) -> str:
    """Explain syntax remaining after narrow folds without fixture-ID lookups."""
    narrow = narrow_folds(cheap.collapse_spacing(text))
    if re.search(r"\b([a-z])-\1-\1", text, re.IGNORECASE):
        return (
            "Hyphen syllable repetition needs both joining and removing repeated "
            "material; the intermediate is not a vocabulary word, and two-letter "
            "function words are outside the derived crisis vocabulary."
        )
    if re.search(r"(?<!\w)0[a-z0-9]*", narrow, re.IGNORECASE):
        return (
            "The leading 0 maps to o under the specified look-alike map; no "
            "approved spelling maps it to d, so no fold has a vocabulary target."
        )
    if any(unicodedata.category(char) in {"Cf", "Mn", "Me"} for char in narrow):
        return (
            "An invisible/combining split remains without a bounded vocabulary "
            "target under this sub-fold; only the partial/all candidates admit "
            "those marks together with a visible separator."
        )
    if re.search(r"\b([a-z])\1-[a-z]", narrow, re.IGNORECASE):
        return (
            "Hyphen syllable repetition requires both joining and deleting "
            "repeated material; no individual intermediate is a vocabulary word."
        )
    return (
        "No allowed separator removal or one doubled-letter deletion produces "
        "a bounded vocabulary word that restores all expected fields."
    )



def narrowed_recovery_aliases(text):
    """Finite first-person frames attested in the seven existing fixtures.

    These are measurement hypotheses, not a semantic proof. In particular a
    recent outing and a bare calendar date can have non-recovery meanings not
    covered by the eight controls. No frame or target crisis text is invented.
    """
    start = r"(^|[.!?;]\s+)"
    end = r"(?=[.!?]|$)"
    aliases = (
        (start + r"(i )went back out(?= last night(?:[.!?]|$))", r"\1\2relapsed"),
        (start + r"(i )picked up again(?= after \d+ days(?:[.!?]|$))", r"\1\2relapsed"),
        (start + r"(i )had a slip(?= this weekend(?:[.!?]|$))", r"\1\2relapsed"),
        (start + r"(i have to reset my )date" + end, r"\1\2sobriety date"),
        # The existing sponsor fixture has an introductory coordinated clause.
        (start + r"(things are wobbly and )?(i could use the kind of thing a )sponsor"
         r"(?= would say right now(?:[.!?]|$))", r"\1\2\3sponsor in recovery"),
    )
    for pattern, replacement in aliases:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def compact_row(row):
    keys = ("id", "text", "safety", "crisis_read", "outcome", "agent", "held",
            "seat_claim", "claim_subject", "mismatch_fields", "crisis_input", "route_input")
    return {key: row[key] for key in keys}


def observe(case, roster, candidate=None):
    return cheap.run_one(case, roster, candidate)


def control_report(cases, roster, candidate, before):
    measured = [observe(case, roster, candidate) for case in cases]
    summary = cheap.control_summary(before, measured)
    summary.pop("rows")
    summary["non_miss_screen_reads"] = sum(row["crisis_read"] != "MISS" for row in measured)
    summary["rows"] = [compact_row(row) for row in measured
                       if row["safety"] == CARD or row["id"] in summary["new_recovery_claim_or_hold_ids"]]
    return summary


def retention_report(lines, roster, candidate):
    rows = [observe(case, roster, candidate) for case in lines]
    lost = [row["id"] for row in rows if row["safety"] != CARD]
    return {"total": len(lines), "baseline_cards": len(lines),
            "retained_cards": len(lines) - len(lost), "cards_lost": len(lost),
            "lost_card_ids": lost,
            "non_miss_screen_reads": sum(row["crisis_read"] != "MISS" for row in rows)}


def gap_report(cases, roster, candidate, baseline):
    rows = [observe(case, roster, candidate) for case in cases]
    recovered = [r["id"] for r in rows
                 if baseline[r["id"]]["mismatch_fields"] and not r["mismatch_fields"]]
    return {"gaps": len(cases),
            "gaps_failing_today": sum(bool(baseline[c["id"]]["mismatch_fields"]) for c in cases),
            "recovered": len(recovered), "recovered_ids": recovered,
            "rows": [compact_row(row) for row in rows]}


def fuzz_report(lines, roster, candidate, transform_names):
    rows = []
    for name in transform_names:
        for case in lines:
            variant = TRANSFORMS[name](case["text"])
            variant_case = dict(case, text=variant)
            before = observe(variant_case, roster)
            if before["safety"] == CARD:
                continue
            after = observe(variant_case, roster, candidate)
            rows.append({"id": case["id"], "transform": name, "variant": variant,
                         "candidate_text": after["crisis_input"],
                         "before": before["safety"], "after": after["safety"],
                         "recovered": after["safety"] == CARD})
    return {"lines": len(lines), "variants": len(lines) * len(transform_names),
            "failing_today": len(rows), "recovered": sum(r["recovered"] for r in rows),
            "by_transform": {name: {
                "failing_today": sum(r["transform"] == name for r in rows),
                "recovered": sum(r["transform"] == name and r["recovered"] for r in rows),
            } for name in transform_names}, "rows": rows}


def confusables_report(lines, roster, candidate, source_limit=None):
    """Generate with B1's ORIGINAL map; only the candidate map is corrected."""
    sources = defaultdict(list)
    for character, target in cf.full_fold_map().items():
        if character not in SKELETON:
            sources[target].append(character)
    if source_limit is not None:
        sources = {target: chars[:source_limit] for target, chars in sources.items()}
    groups = defaultdict(Counter)
    residuals = []
    total = failed = recovered = 0
    for line_index, case in enumerate(lines, 1):
        positions = {}
        for index, character in enumerate(case["text"]):
            if character in string.ascii_letters:
                positions.setdefault(character.casefold(), index)
        for target, index in sorted(positions.items()):
            for character in sources.get(target, ()):
                total += 1
                variant = case["text"][:index] + character + case["text"][index + 1:]
                variant_case = dict(case, text=variant)
                before = b1.observe(variant_case, variant, roster)
                misses = before["action"] != CARD
                recovered_now = False
                if misses:
                    failed += 1
                    with cheap.candidate_scope(candidate):
                        after = b1.observe(variant_case, variant, roster)
                    recovered_now = after["action"] == CARD
                    recovered += recovered_now
                    if not recovered_now:
                        residuals.append({"id": case["id"], "source": character,
                                          "codepoint": f"U+{ord(character):04X}",
                                          "target": target, "replacement_index": index,
                                          "reason": "ASCII source deliberately excluded from candidate."
                                          if character.isascii() else "Unchanged screen still misses."})
                for group in ("target:" + target, "script:" + cf.script_from_name(character)):
                    groups[group].update(variants=1, failing_today=int(misses),
                                         recovered=int(recovered_now))
        if len(lines) > 1 and (line_index % 10 == 0 or line_index == len(lines)):
            print(f"Confusables: {line_index}/{len(lines)} source lines, {total} variants replayed.", flush=True)
    return {"lines": len(lines), "variants": total, "failing_today": failed,
            "recovered": recovered, "unrecovered": failed - recovered,
            "summary_groups": dict(sorted(groups.items())), "residuals": residuals,
            "omitted": "Per-variant success rows and 5,000+ recovered rows omitted for the 2 MB limit; deterministic generator, all group counts and every residual retained."}


def no_network(*args, **kwargs):
    raise RuntimeError("B5b forbids network access")


def run_report(case_ids=None, control_limit=None, variant_line_limit=None, source_limit=None):
    """Fresh original sessions; no file writes. Limits are solely for the smoke test."""
    with patch.object(socket.socket, "connect", no_network), \
            patch.object(socket.socket, "connect_ex", no_network), \
            patch.object(socket, "create_connection", no_network):
        return _run_report(case_ids, control_limit, variant_line_limit, source_limit)


def _run_report(case_ids, control_limit, variant_line_limit, source_limit):
    roster = load_roster()
    controls = cheap.load_controls()
    everyday, vocabulary_sources = everyday_vocabulary(controls)
    guarded, guard_options = make_guarded_matcher(everyday)
    guarded_unique, _ = make_guarded_matcher(everyday, unique_only=True)
    mapping, conflicts = corrected_confusables_map()
    corrected_table = str.maketrans(mapping)
    controls["historical_policy_proceed"] = [
        c for c in controls["policy_proceed"] if c["source"] not in B7_CONTROL_FILES]
    controls["non_latin"] = [dict(c, expect={"safety": "PROCEED"}) for c in
                             json.loads(cf.NON_LATIN_PATH.read_text(encoding="utf-8"))["controls"]]
    original_control_counts = {name: len(rows) for name, rows in controls.items()}
    if control_limit is not None:
        controls = {name: rows[:control_limit] for name, rows in controls.items()}
    triage = json.loads((HERE / "triage_2026-10-05.json").read_text(encoding="utf-8"))
    causes = {r["id"]: r["cause"] for r in triage["cases"]}
    gaps = cheap.load_gap_cases()
    if case_ids is not None:
        requested = set(case_ids)
        gaps = [c for c in gaps if c["id"] in requested]
        if {c["id"] for c in gaps} != requested:
            raise ValueError("Unknown or non-gap --case-id")
    all_lines = crisis_lines(roster)
    added_lines = [c for c in all_lines if c.get("source_case") and "B7" in c.get("port_note", "")]
    added_ids = {c["id"] for c in added_lines}
    lines = [c for c in all_lines if c["id"] not in added_ids]
    original_line_count = len(lines)
    if variant_line_limit is not None:
        lines = lines[:variant_line_limit]
    baseline = {c["id"]: observe(c, roster) for c in gaps}
    baseline_controls = {name: [observe(c, roster) for c in rows]
                         for name, rows in controls.items()}
    registry = {
        "guarded_one_letter": cheap.Candidate("guarded_one_letter", "one_letter", guarded),
        "guarded_one_letter_unique_only": cheap.Candidate(
            "guarded_one_letter_unique_only", "one_letter", guarded_unique),
        "corrected_confusables": cheap.Candidate(
            "corrected_confusables", "confusables", lambda text: text.translate(corrected_table)),
        "narrow_reference": cheap.Candidate("narrow_reference", "crisis_word_obfuscation", narrow_folds),
        **{name: cheap.Candidate(name, "crisis_word_obfuscation", transform)
           for name, transform in wider_transforms().items()},
        "narrowed_recovery_crisis_only": cheap.Candidate(
            "narrowed_recovery_crisis_only", "recovery_community_vocabulary", narrowed_recovery_aliases),
        "narrowed_recovery_routing_experiment": cheap.Candidate(
            "narrowed_recovery_routing_experiment", "recovery_community_vocabulary",
            narrowed_recovery_aliases, "routing"),
    }
    obfuscated = [c for c in gaps if causes[c["id"]] == "crisis_word_obfuscation"]
    narrow_rows = [observe(c, roster, registry["narrow_reference"]) for c in obfuscated]
    narrow_recovered_ids = {r["id"] for r in narrow_rows if not r["mismatch_fields"]}
    residual_cases = [c for c in obfuscated if c["id"] not in narrow_recovered_ids]
    results = {}
    for name, candidate in registry.items():
        if name.startswith("guarded_one_letter"):
            relevant = [c for c in gaps if causes[c["id"]] in
                        {"b1_one_letter_dropped", "b1_two_neighbouring_letters_swapped"}]
        elif name == "corrected_confusables":
            relevant = gaps  # Manifest reductions must be observed, not inferred from fuzz counts.
        elif name.startswith("wider_"):
            relevant = residual_cases
        else:
            relevant = [c for c in gaps if causes[c["id"]] == candidate.cause]
        result = gap_report(relevant, roster, candidate, baseline)
        result["scope"] = candidate.scope
        result["controls"] = {
            control_name: control_report(rows, roster, candidate, baseline_controls[control_name])
            for control_name, rows in controls.items()
        }
        result["real_card_retention"] = retention_report(lines, roster, candidate)
        results[name] = result
    guard = results["guarded_one_letter"]
    guard["fuzz"] = fuzz_report(lines, roster, registry["guarded_one_letter"],
                                ("one_letter_dropped", "two_neighbouring_letters_swapped"))
    results["guarded_one_letter_unique_only"]["fuzz"] = fuzz_report(
        lines, roster, registry["guarded_one_letter_unique_only"],
        ("one_letter_dropped", "two_neighbouring_letters_swapped"))
    guard["fuzz_ambiguous_targets"] = [
        {"id": row["id"], "transform": row["transform"], "token": match.group(),
         "targets": guard_options(match.group()), "chosen": guard_options(match.group())[0]}
        for row in guard["fuzz"]["rows"] for match in WORD.finditer(row["variant"])
        if len(guard_options(match.group())) > 1]
    escaped = []
    ambiguous = []
    for name in ("literal_three_lists", "policy_proceed", "digit_tokens", "recovery_everyday", "non_latin"):
        for case in controls[name]:
            for match in WORD.finditer(case["text"]):
                options = guard_options(match.group())
                if options:
                    row = {"group": name, "id": case["id"], "token": match.group(), "targets": options}
                    escaped.append(row)
                    if len(options) > 1:
                        ambiguous.append(row)
    guard["everyday_tokens_let_through"] = sorted({r["token"].casefold() for r in escaped})
    guard["everyday_token_occurrences_let_through"] = escaped
    guard["ambiguous_control_edits"] = ambiguous
    guard["vocabulary"] = {"everyday_count": len(everyday), "crisis_count": len(VOCABULARY),
                           "everyday_words": sorted(everyday), "sources": vocabulary_sources,
                           "sha256": hashlib.sha256("\n".join(sorted(everyday)).encode()).hexdigest(),
                           "tie_policy": "Lexical-first eligible target, matching B5; unique-only sensitivity reported separately."}
    conf = results["corrected_confusables"]
    conf["fuzz"] = confusables_report(lines, roster, registry["corrected_confusables"], source_limit)
    conf["map"] = {"candidate_sources": len(mapping), "b1_full_map_sources": len(cf.full_fold_map()),
                   "eligible_variant_sources": len(cf.full_fold_map().keys() - SKELETON.keys()),
                   "table_sha256": cf.TABLE_SHA256, "reviewed_conflicts": conflicts,
                   "ascii_sources_preserved": True}
    conf["extended_current_card_retention"] = retention_report(all_lines, roster, registry["corrected_confusables"])

    stutters = []
    for case in lines:
        for transform in b1.STUTTER_TRANSFORMS:
            variant = TRANSFORMS[transform](case["text"])
            prepared = b1.fold_stutter(variant)
            if b1.observe(case, variant, roster)["action"] != CARD and \
                    b1.observe(case, prepared, roster)["action"] != CARD:
                stutters.append(dict(case, text=variant, b3_prepared=prepared, transform=transform))
    for name in (n for n in registry if n.startswith("wider_")):
        transform = registry[name].transform
        composed = cheap.Candidate(name + "_after_stutter", "stutter",
                                   lambda text, fold=transform: fold(b1.fold_stutter(text)))
        rows = []
        for case in stutters:
            after = observe(case, roster, composed)
            rows.append({"id": case["id"], "transform": case["transform"], "variant": case["text"],
                         "b3_prepared": case["b3_prepared"], "candidate_text": after["crisis_input"],
                         "recovered": after["safety"] == CARD,
                         "reason_if_unrecovered": None if after["safety"] == CARD
                         else wider_residual_reason(case["b3_prepared"])})
        results[name]["stutter_leftovers"] = {"total": len(rows),
                                              "recovered": sum(r["recovered"] for r in rows), "rows": rows}
    recovered_any = set().union(*(set(r["recovered_ids"]) for name, r in results.items()
                                  if name.startswith("wider_")))
    unrecovered = [{"id": c["id"], "text": c["text"], "reason": wider_residual_reason(c["text"])}
                   for c in residual_cases if c["id"] not in recovered_any]
    recovery_controls = controls["recovery_everyday"]
    broad = cheap.Candidate("b5_broad_aliases", "recovery_community_vocabulary", cheap.recovery_phrase_aliases, "routing")
    broad_rows = [observe(c, roster, broad) for c in recovery_controls]
    narrowed_rows = [observe(c, roster, registry["narrowed_recovery_routing_experiment"])
                     for c in recovery_controls]
    releases = []
    for case, before, after in zip(recovery_controls, broad_rows, narrowed_rows):
        def recovery_signal(row):
            return row["seat_claim"] == "addiction_recovery" or "addiction_recovery" in row["held"]
        releases.append({"id": case["id"], "text": case["text"],
                         "broad_recovery_signal": recovery_signal(before),
                         "narrow_recovery_signal": recovery_signal(after),
                         "released": recovery_signal(before) and not recovery_signal(after)})
    results["narrowed_recovery_routing_experiment"]["everyday_release"] = {
        "total": len(releases), "released": sum(r["released"] for r in releases), "rows": releases}
    for name, result in results.items():
        if "fuzz" in result:
            failed, recovered = result["fuzz"]["failing_today"], result["fuzz"]["recovered"]
            units = "fuzz variants"
        else:
            failed, recovered = result["gaps_failing_today"], result["recovered"]
            units = "documented gaps"
        control_line = "; ".join(
            f"{key}={result['controls'][key]['candidate_false_alarms']}/{result['controls'][key]['total']}"
            f" (+{result['controls'][key]['new_false_alarms']} new)"
            for key in ("literal_three_lists", "historical_policy_proceed", "policy_proceed", "digit_tokens", "non_latin"))
        lost = result["real_card_retention"]["cards_lost"]
        result["line"] = (f"{name}: {failed} {units} fail today; {recovered} recovered; "
                          f"{control_line}; real cards lost={lost}/{len(lines)}.")
        result["plain_sentence"] = (
            f"This measured candidate restores {recovered} of {failed} {units}, "
            f"adds {sum(g['new_false_alarms'] for key, g in result['controls'].items() if key in ('literal_three_lists', 'policy_proceed', 'digit_tokens', 'non_latin'))} "
            f"new control cards, and loses {lost} real cards; existing control cards remain visible.")
        if name.startswith("guarded_one_letter"):
            result["plain_sentence"] += " The vocabulary contains its own controls, so this is not held-out English-word validation."
        if name == "narrowed_recovery_crisis_only":
            result["plain_sentence"] += " Changing crisis input cannot repair a recovery routing claim."
        if name == "narrowed_recovery_routing_experiment":
            result["plain_sentence"] += " These finite first-person frames release the eight supplied controls but do not prove recovery meaning in unseen sentences."
        if name == "corrected_confusables":
            result["plain_sentence"] += " All ordinary non-Latin screen reads remain MISS, but the unchanged language policy still cards them."
    eligible = [name for name, result in results.items() if name != "narrow_reference"
                and all(result["controls"][key]["candidate_false_alarms"] == 0
                        for key in ("literal_three_lists", "policy_proceed", "digit_tokens", "non_latin"))
                and result["real_card_retention"]["cards_lost"] == 0]
    additional = set().union(*(set(results[name]["recovered_ids"]) for name in eligible))
    after = {
        "documented_gaps_now": 204, "b3_given_closures": [36, 38],
        "after_b3": [166, 168], "b3_assumption": "Taken as given, not an observed B3 integration.",
        "literal_zero_total_false_alarm_eligible_candidates": eligible,
        "additional_documented_recoveries_from_eligible_candidates": len(additional),
        "after_all_eligible": [166 - len(additional), 168 - len(additional)],
        "meaning": "No measured candidate satisfies zero TOTAL control cards on this unchanged tree; +0 new cards is a different criterion. No closures are performed.",
        "next_cheapest": [
            "Rule on zero-total versus zero-new alarms and replay the candidates on B3 before counting any further closures.",
            "The remaining mechanical work is the leading-zero obfuscation, subject/function-word edits and syllable stutters, each requiring a separate bounded candidate and controls.",
            "Recovery's bare day-one and other-person frames need an ownership ruling and more everyday controls before an alias extension.",
            "Five Spanish exhaustion, clitic and integrity gaps need native review before small pack changes.",
            "The one legacy weapon case needs its expected contract reconciled before measuring a contraction repair.",
            "The threat and immediate-danger causes need the two-label expansion set before a threshold or vocabulary change.",
        ],
    }
    return {
        "schema_version": 1, "date": "2026-10-05", "measurement_only": True,
        "scope": "full" if all(v is None for v in (case_ids, control_limit, variant_line_limit, source_limit)) else "three-case smoke/limited run",
        "method": {"network": "Socket connect/connect_ex/create_connection blocked; FakeAdapter only.",
                   "candidate_scope": "Copy before unchanged crisis_screen, with original text/session/prior turns kept for routing; recovery routing experiment separately labelled.",
                   "false_alarm": "Any resulting control card, including baseline cards; new cards separately counted.",
                   "recovery": "Every expected field checked with existing field_failures; fuzz counts require a restored card.",
                   "guard": "Casefolded letter runs from every PROCEED message/prior, 43 controls, 40 digits, README and docs Markdown prose excluding fenced blocks; deletion/swap only, lexical-first target with unique-only sensitivity.",
                   "confusables": "B1 table/source enumeration unchanged, even ASCII source hazards; corrected candidate excludes all ASCII sources and preserves four reviewed conflicts.",
                   "b3_obfuscation_reference": "Exact measure_cheap separator/look-alike folds only; no claimed full B3 integration.",
                   "stutter_reference": "B1 filler/repeated-word fold followed by narrow and wider crisis-input folds, on nine residual variants.",
                   "omissions": "Successful per-case control rows omitted; counts, alarms, routing changes, gap rows and all confusable residuals retained."},
        "cohort_reconciliation": {"control_counts": original_control_counts,
                                  "historical_real_cards": original_line_count,
                                  "current_crisis_lines": len(all_lines),
                                  "added_b7_wrapper_ids": sorted(added_ids),
                                  "historical_selection": "Exclude B7 source_case/port_note wrappers to reproduce B1 86 and 56,909; retain all 260 current PROCEED controls plus separate historical160."},
        "gap_baseline": [compact_row(r) for r in baseline.values()],
        "candidates": results, "narrow_recovered_ids": sorted(narrow_recovered_ids),
        "wider_measurement_denominator": len(residual_cases),
        "wider_unrecovered": unrecovered, "wider_unrecovered_count": len(unrecovered),
        "raw_tab_newline_residual_ids": [c["id"] for c in residual_cases if any(ch in c["text"] for ch in "\t\n")],
        "after_picture": after,
        "fake_adapter_smoke": cheap.fake_adapter_smoke(roster, controls["passing_three_lists"][0]),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "measurements/rest_2026-10-05.json")
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--control-limit", type=int)
    parser.add_argument("--variant-line-limit", type=int)
    parser.add_argument("--source-limit", type=int)
    args = parser.parse_args(argv)
    report = run_report(args.case_id, args.control_limit, args.variant_line_limit, args.source_limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, result in report["candidates"].items():
        print(result["line"])
        print(result["plain_sentence"])
    print(json.dumps(report["after_picture"], ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
