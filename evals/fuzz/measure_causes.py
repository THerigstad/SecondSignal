"""B1 measurement only, 4 October 2026; no policy or production matcher changes.

Run ``python -m evals.fuzz.measure_causes`` from the repository root. All
variants come mechanically from existing labelled fixtures. No model adapter
is needed: measurements call the real deterministic route function directly.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from secondsignal import load_roster, route
from secondsignal.normalize import collapse_spacing
from secondsignal.safety import CRISIS_CLASSES

from .run import _ROOT, _load_single_cases, _prior_text, _session, crisis_lines
from .transforms import TRANSFORMS

MEASUREMENTS = Path(__file__).with_name("measurements")
DATE = "2026-10-04"
STUTTER_TRANSFORMS = (
    "first_word_stuttered_with_commas",
    "middle_word_repeated_with_comma",
    "um_before_the_middle_word",
    "uh_before_the_last_word",
    "false_start_of_two_words",
    "first_long_word_syllable_stuttered",
)
CAUSE_TRANSFORMS = {
    "doubled punctuation": ("punctuation_doubled",),
    "tripled letter": ("one_letter_repeated_three_times",),
    "dropped letter": ("one_letter_dropped",),
    "swapped letters": ("two_neighbouring_letters_swapped",),
    "stutter": STUTTER_TRANSFORMS,
}
WORD = re.compile(r"[^\W\d_]+")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def control_sets() -> tuple[list[dict], list[dict]]:
    """Read the exact four constant lists without importing pytest/test code."""
    names = {
        "CONTROLS", "SPOKEN_SURFACE_CONTROLS",
        "KNOWN_SPOKEN_SURFACE_OVERRESTRICTIONS", "INTERNET_SLANG_DEATH_CONTROLS",
    }
    module = ast.parse((_ROOT / "tests/test_crisis_gate.py").read_text(encoding="utf-8"))
    values = {}
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    values[target.id] = ast.literal_eval(node.value)
    texts = values["CONTROLS"] + [
        text for text in values["SPOKEN_SURFACE_CONTROLS"]
        if text not in values["KNOWN_SPOKEN_SURFACE_OVERRESTRICTIONS"]
    ] + values["INTERNET_SLANG_DEATH_CONTROLS"]
    sentences = [{"id": f"control-sentence-{i:02d}", "text": text}
                 for i, text in enumerate(texts, 1)]
    cases = [case for case in _load_single_cases()
             if case.get("expect", {}).get("safety") == "PROCEED"
             and isinstance(case.get("text"), str)]
    return sentences, cases


def extract_vocabulary() -> dict:
    """Maximal literal letter runs, not generated regex-language inflections.

    Regex escapes are removed first so ``\\b`` cannot turn ``kill`` into
    ``bkill``. Three-letter fragments such as ``ing``/``tak`` are retained:
    the order asks for words occurring literally, not expanded alternatives.
    Negative lookahead literals are included too. Only hit pattern values
    are read from en.json, never their ids, classes, masks, or metadata.
    """
    sources = [{"source": f"CRISIS_CLASSES.{name}[{index}]", "pattern": pattern.pattern}
               for name, patterns in CRISIS_CLASSES.items()
               for index, pattern in enumerate(patterns)]
    pack = json.loads((_ROOT / "src/secondsignal/packs/en.json").read_text(encoding="utf-8"))
    sources.extend({"source": f"en.hits.{hit['id']}", "pattern": hit["pattern"]}
                   for hit in pack["hits"])
    words = set()
    for source in sources:
        # Unicode/hex/named escapes denote characters, not literal English words.
        plain = re.sub(r"\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{2}|N\{[^}]*\}|.)",
                       " ", source["pattern"])
        literal_words = sorted({m.group().casefold() for m in WORD.finditer(plain)
                                if len(m.group()) >= 3})
        source["literal_words"] = literal_words
        words.update(literal_words)
    return {"count": len(words), "words": sorted(words), "sources": sources,
            "method": "Remove regex escapes; collect maximal letters-only literal runs of length >=3, casefold and deduplicate; do not expand regex branches or inflections."}


def observe(case: dict, text: str, roster) -> dict:
    session = _session(case)
    for prior in case.get("prior_turns", []):
        route(_prior_text(prior), roster, session=session)
    decision = route(text, roster, session=session)
    return {
        "action": decision.safety.action.name,
        "crisis_read": decision.safety.crisis_read,
        "outcome": decision.outcome.value,
        "agent_id": decision.agent_id,
        "assist": decision.assist_agent_id,
    }


def collapse_punctuation(text: str) -> str:
    return re.sub(r"(.)\1+", lambda m: m[1] if unicodedata.category(m[1]).startswith("P")
                  else m[0], text, flags=re.DOTALL)


def collapse_tripled_letters(text: str) -> str:
    return re.sub(r"([^\W\d_])\1{2,}", r"\1", text)


def fold_stutter(text: str) -> str:
    """Only the requested fillers and adjacent repeated words, no hyphen repair."""
    text = re.sub(r"\b(?:um|uh|erm|uhm)\b", "", text, flags=re.IGNORECASE)
    text = collapse_spacing(text)
    repeated = re.compile(r"\b([^\W\d_]+)(?:\s*,\s*|\s+)\1\b", re.IGNORECASE)
    while True:
        folded = repeated.sub(r"\1", text)
        if folded == text:
            return text
        text = folded


TEXT_CANDIDATES = {
    "doubled punctuation": collapse_punctuation,
    "tripled letter": collapse_tripled_letters,
    "stutter": fold_stutter,
}


def distance_at_most_one(left: str, right: str) -> int | None:
    """Exact Damerau-Levenshtein at threshold 1 (including adjacent swaps)."""
    if left == right:
        return 0
    if abs(len(left) - len(right)) > 1:
        return None
    if len(left) == len(right):
        different = [i for i, (a, b) in enumerate(zip(left, right)) if a != b]
        if len(different) == 1:
            return 1
        if len(different) == 2:
            a, b = different
            if b == a + 1 and left[a] == right[b] and left[b] == right[a]:
                return 1
        return None
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    i = 0
    while i < len(shorter) and shorter[i] == longer[i]:
        i += 1
    return 1 if shorter[i:] == longer[i + 1:] else None


def token_risk(controls: list[dict], vocabulary: list[str]) -> dict:
    rows = []
    total_tokens = 0
    for case in controls:
        for index, match in enumerate(WORD.finditer(case["text"])):
            total_tokens += 1
            token = match.group().casefold()
            matches = [{"word": word, "distance": distance}
                       for word in vocabulary
                       if (distance := distance_at_most_one(token, word)) is not None]
            if matches:
                rows.append({"case_id": case["id"], "token_index": index,
                             "span": list(match.span()), "token": match.group(),
                             "casefolded_token": token, "matches": matches,
                             "exact_vocabulary_token": token in vocabulary})
    novel = [row for row in rows if not row["exact_vocabulary_token"]]
    return {
        "controls": len(controls), "total_token_occurrences": total_tokens,
        "within_one_token_occurrences": len(rows),
        "exact_vocabulary_token_occurrences": len(rows) - len(novel),
        "new_distance_one_token_occurrences": len(novel),
        "new_distance_one_unique_tokens": sorted({r["casefolded_token"] for r in novel}),
        "within_one_unique_tokens": sorted({r["casefolded_token"] for r in rows}),
        "controls_with_new_distance_one_token": len({r["case_id"] for r in novel}),
        "tokens": rows,
        "meaning": "Risk only, not card predictions: raw letters-only tokens casefolded; distance 0 reported separately from newly admitted distance-1 tokens; all source controls included, even those already over-restricted today.",
    }


def candidate_controls(controls: list[dict], candidate, roster) -> dict:
    rows = []
    for case in controls:
        before = observe(case, case["text"], roster)
        transformed = candidate(case["text"])
        after = observe(case, transformed, roster)
        rows.append({"id": case["id"], "text": case["text"], "candidate_text": transformed,
                     "before": before, "after": after,
                     "false_alarm": before["action"] == "PROCEED"
                     and after["action"] == "HUMAN_ESCALATION"})
    return {"total": len(rows), "baseline_actions": dict(Counter(r["before"]["action"] for r in rows)),
            "candidate_cards": sum(r["after"]["action"] == "HUMAN_ESCALATION" for r in rows),
            "false_alarms": sum(r["false_alarm"] for r in rows), "rows": rows}


def measure_fuzz_causes(lines, sentences, cases, vocabulary, roster) -> list[dict]:
    risk = None
    reports = []
    for cause, names in CAUSE_TRANSFORMS.items():
        failures = []
        candidate = TEXT_CANDIDATES.get(cause)
        for name in names:
            for case in lines:
                variant = TRANSFORMS[name](case["text"])
                before = observe(case, variant, roster)
                if before["action"] == "HUMAN_ESCALATION":
                    continue
                row = {"case_id": case["id"], "transform": name, "original": case["text"],
                       "variant": variant, "before": before}
                if candidate is not None:
                    row["candidate_text"] = candidate(variant)
                    row["after"] = observe(case, row["candidate_text"], roster)
                    row["recovered"] = row["after"]["action"] == "HUMAN_ESCALATION"
                failures.append(row)
        ids = {r["case_id"] for r in failures}
        item = {"cause": cause, "lines_tested": len(lines),
                "variants_tested": len(lines) * len(names),
                "failing_line_count": len(ids), "failing_variant_count": len(failures),
                "failures_by_transform": {name: sum(r["transform"] == name for r in failures)
                                          for name in names}, "failures": failures}
        prefix = f"{cause}: {len(ids)} of {len(lines)} lines fail today ({len(failures)} variants); "
        if candidate:
            recovered = sum(row["recovered"] for row in failures)
            item.update({"recovered_variants": recovered,
                         "fully_recovered_line_count": sum(all(r["recovered"] for r in failures
                                                               if r["case_id"] == ident) for ident in ids),
                         "control_sentences": candidate_controls(sentences, candidate, roster),
                         "control_cases": candidate_controls(cases, candidate, roster)})
            a, b = item["control_sentences"]["false_alarms"], item["control_cases"]["false_alarms"]
            item["line"] = (prefix + f"candidate recovers {recovered} of {len(failures)} failing variants "
                            f"(all failing variants for {item['fully_recovered_line_count']} of {len(ids)} lines); "
                            f"false alarms {a} of {len(sentences)} sentences and {b} of {len(cases)} cases.")
            item["plain_sentence"] = (f"This candidate restores the card on {recovered} missed variants and "
                                      f"newly interrupts {a + b} controls that proceed today; "
                                      f"{len(failures) - recovered} missed variants remain.")
        else:
            if risk is None:
                risk = {"sentences": token_risk(sentences, vocabulary),
                        "cases": token_risk(cases, vocabulary)}
            item.update({"recovered_variants": None, "recovery_status": "not measured: matcher risk only",
                         "distance_one_risk": risk, "control_sentences": None, "control_cases": None})
            a, b = risk["sentences"], risk["cases"]
            item["line"] = (prefix + "recovery not measured (matcher risk only); "
                            f"distance <=1 token occurrences {a['within_one_token_occurrences']} in {len(sentences)} sentences "
                            f"and {b['within_one_token_occurrences']} in {len(cases)} cases "
                            f"({a['new_distance_one_token_occurrences']} and {b['new_distance_one_token_occurrences']} newly admitted).")
            item["plain_sentence"] = ("Allowing a one-letter edit would also admit ordinary control words; "
                                      "these token counts show possible confusion, not recovered cards or predicted false alarms.")
        reports.append(item)
    return reports


# Part 4 and Part 5 functions are below; all candidate behaviour remains local.




def measure_spacing(roster, control_cases):
    """Compare current routing with spacing folded before every route call.

    Selection and session construction mirror the two fixture runners.  All
    prior turns are compared too, so a change cannot be hidden by an unchanged
    final decision.  The two alternatives use separate fresh sessions.
    """
    import json
    from collections import Counter

    from evals.fuzz.run import CASE_DIR, _load_single_cases, _prior_text, _session
    from evals.fuzz.transforms import TRANSFORMS
    from secondsignal import route
    from secondsignal.normalize import collapse_spacing

    def snapshot(decision):
        return {
            "action": decision.safety.action.name,
            "outcome": decision.outcome.value,
            "agent_id": decision.agent_id,
            "assist": decision.assist_agent_id,
            "disclosures": list(decision.safety.disclosures),
        }

    def difference(before, after):
        return [key for key in before if before[key] != after[key]]

    def seating_changed(row):
        return bool({"agent_id", "assist"} & set(row["changed_fields"]))

    def replay_case(case, current_text, fold=False):
        session = _session(case)
        prepare = collapse_spacing if fold else lambda text: text
        for prior in case.get("prior_turns", []):
            route(prepare(_prior_text(prior)), roster, session=session)
        return snapshot(route(prepare(current_text), roster, session=session))

    singles = _load_single_cases()
    single_changes = []
    prior_changes = []
    changed_case_ids = set()
    prior_turns = 0
    for case in singles:
        current_session, option_b_session = _session(case), _session(case)
        texts = [_prior_text(prior) for prior in case.get("prior_turns", [])]
        prior_turns += len(texts)
        texts.append(case["text"])
        for index, text in enumerate(texts, start=1):
            before = snapshot(route(text, roster, session=current_session))
            folded = collapse_spacing(text)
            after = snapshot(route(folded, roster, session=option_b_session))
            fields = difference(before, after)
            if fields:
                row = {
                    "case_id": case["id"],
                    "turn_index": index,
                    "phase": "current" if index == len(texts) else "prior",
                    "text": text,
                    "folded_text": folded,
                    "changed_fields": fields,
                    "current": before,
                    "option_b": after,
                }
                (single_changes if index == len(texts) else prior_changes).append(row)
                changed_case_ids.add(case["id"])

    trajectory_changes = []
    changed_trajectory_ids = set()
    trajectories = trajectory_turns = 0
    for path in sorted((CASE_DIR / "trajectories").glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture.get("kind") != "trajectory":
            raise ValueError(f"Not a trajectory: {path.name}")
        current_session, option_b_session = _session(fixture), _session(fixture)
        trajectories += 1
        for index, turn in enumerate(fixture["turns"], start=1):
            text = turn["text"]
            trajectory_turns += 1
            before = snapshot(route(text, roster, session=current_session))
            folded = collapse_spacing(text)
            after = snapshot(route(folded, roster, session=option_b_session))
            fields = difference(before, after)
            if fields:
                trajectory_changes.append({
                    "trajectory_id": fixture["id"],
                    "turn_index": index,
                    "text": text,
                    "folded_text": folded,
                    "changed_fields": fields,
                    "current": before,
                    "option_b": after,
                })
                changed_trajectory_ids.add(fixture["id"])

    spacing_results = []
    for transform_name in (
        "two_spaces_between_words", "tab_between_words", "line_break_between_words"
    ):
        changes = []
        original_changes = []
        for case in control_cases:
            original = replay_case(case, case["text"])
            variant = TRANSFORMS[transform_name](case["text"])
            current = replay_case(case, variant)
            option_b = replay_case(case, variant, fold=True)
            for rows, baseline, baseline_name in (
                (changes, current, "current_variant"),
                (original_changes, original, "original_case"),
            ):
                fields = difference(baseline, option_b)
                if fields:
                    rows.append({
                        "case_id": case["id"],
                        "text": case["text"],
                        "variant": variant,
                        "folded_variant": collapse_spacing(variant),
                        "changed_fields": fields,
                        baseline_name: baseline,
                        "option_b": option_b,
                    })
        spacing_results.append({
            "transform": transform_name,
            "control_cases": len(control_cases),
            "current_variant_to_option_b_changes": changes,
            "current_variant_to_option_b_seating_changes": [
                row for row in changes if seating_changed(row)
            ],
            "original_case_to_option_b_changes": original_changes,
            "original_case_to_option_b_seating_changes": [
                row for row in original_changes if seating_changed(row)
            ],
        })

    all_changes = single_changes + prior_changes + trajectory_changes
    return {
        "method": (
            "Two independent sessions per fixture: current routing uses each text "
            "unchanged, option B applies collapse_spacing before every route call, "
            "including prior turns; only action, outcome, agent_id, assist and "
            "disclosures are compared."
        ),
        "single_turn_cases": len(singles),
        "single_case_prior_turns": prior_turns,
        "single_case_decisions_including_prior": len(singles) + prior_turns,
        "single_cases_changed_on_any_turn": len(changed_case_ids),
        "single_case_ids_changed": sorted(changed_case_ids),
        "single_case_final_changes": single_changes,
        "single_case_prior_changes": prior_changes,
        "trajectories": trajectories,
        "trajectory_turns": trajectory_turns,
        "trajectories_changed": len(changed_trajectory_ids),
        "trajectory_ids_changed": sorted(changed_trajectory_ids),
        "trajectory_turn_changes": trajectory_changes,
        "changed_fields_counts": dict(sorted(Counter(
            field for row in all_changes for field in row["changed_fields"]
        ).items())),
        "spacing_control_method": (
            "Each transform changes only the current control text, as in the fuzz; "
            "option B also collapses prior texts. Compare the current spacing "
            "variant with option B to show B's effect, and compare the original "
            "unmodified case with option B to show whether its seat is restored."
        ),
        "spacing_control_variants": len(control_cases) * 3,
        "spacing_controls": spacing_results,
        "spaced_letters_note": (
            "collapse_spacing folds whitespace runs, not spaces between letters; "
            "the separate spaced-letter gap remains open."
        ),
    }


def measure_labels(roster):
    """Verify curated labels against their unchanged source turns and replay.

    This checks and counts a labelled set; it does not build a policy detector.
    The deliberately minimal keyword rule is evaluated on these rows only.
    """
    import json
    import re
    from collections import Counter

    from evals.fuzz.run import CASE_DIR, _session
    from secondsignal import route

    path = CASE_DIR.parent / "fuzz" / "measurements" / "targets_the_crisis_labels_2026-10-04.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    labelled = {(row["trajectory_id"], row["turn_index"]): row for row in report["turns"]}
    seen = set()
    for trajectory_path in sorted((CASE_DIR / "trajectories").glob("*.json")):
        fixture = json.loads(trajectory_path.read_text(encoding="utf-8"))
        session = _session(fixture)
        previous_card = None
        for index, turn in enumerate(fixture["turns"], start=1):
            before = session.aftermath_turns
            decision = route(turn["text"], roster, session=session)
            key = fixture["id"], index
            if key in labelled:
                row = labelled[key]
                if row["text"] != turn["text"] or previous_card is None:
                    raise ValueError(f"Label source changed or no earlier card: {key}")
                live = decision.safety.aftermath_live
                if row["label"] == "A" and live or row["label"] == "D" and not live:
                    raise ValueError(f"Label window mismatch: {key}")
                row.update({
                    "preceding_card_turn": previous_card,
                    "aftermath_before": before,
                    "aftermath_after": session.aftermath_turns,
                    "aftermath_live_for_reply": live,
                    "observed_action": decision.safety.action.name,
                    "observed_agent_id": decision.agent_id,
                    "observed_no_joke": "no_joke" in decision.obligations,
                    "simple_rule_refuses": bool(re.search(r"\b(?:crisis|card)\b", row["text"], re.I)),
                })
                seen.add(key)
            if decision.safety.action.name == "HUMAN_ESCALATION":
                previous_card = index
    if seen != set(labelled):
        raise ValueError(f"Missing labelled source turns: {sorted(set(labelled) - seen)}")
    counts = Counter(row["label"] for row in report["turns"])
    report["counts"] = {label: counts[label] for label in "ABCD"}
    report["simple_rule"] = {
        "rule": (
            "Refuse a humour request if its same-message text contains the whole "
            "word crisis or card, case-insensitively."
        ),
        "a_wrongly_refused": sum(row["label"] == "A" and row["simple_rule_refuses"] for row in report["turns"]),
        "a_total": counts["A"],
        "b_missed": sum(row["label"] == "B" and not row["simple_rule_refuses"] for row in report["turns"]),
        "b_total": counts["B"],
        "c_rule_triggers": sum(row["label"] == "C" and row["simple_rule_refuses"] for row in report["turns"]),
        "d_rule_triggers": sum(row["label"] == "D" and row["simple_rule_refuses"] for row in report["turns"]),
        "wrongly_refused_turns": [
            [row["trajectory_id"], row["turn_index"]] for row in report["turns"]
            if row["label"] == "A" and row["simple_rule_refuses"]
        ],
        "missed_target_turns": [
            [row["trajectory_id"], row["turn_index"]] for row in report["turns"]
            if row["label"] == "B" and not row["simple_rule_refuses"]
        ],
        "interpretation": (
            "The keyword rule refuses no ordinary post-window request, but misses "
            "the one clear crisis-targeted paraphrase; C is unscored and D is "
            "already protected by the live window."
        ),
    }
    return report


def confusables_cause(report: dict, sentence_count: int, case_count: int) -> dict:
    failures = [row for row in report["variants"] if row["failed_today"]]
    remaining_ids = {row["case_id"] for row in failures if not row["recovered"]}
    fully_recovered = report["affected_lines"] - len(remaining_ids)
    a = report["controls"]["sentences"]["false_alarms_from_proceed"]
    b = report["controls"]["cases"]["false_alarms_from_proceed"]
    recovered = report["candidate_recovered_variants"]
    failed = report["today_failed_variants"]
    return {
        "cause": "confusables", "lines_tested": report["lines"],
        "variants_tested": report["total_variants"],
        "failing_line_count": report["affected_lines"], "failing_variant_count": failed,
        "recovered_variants": recovered, "fully_recovered_line_count": fully_recovered,
        "at_least_one_variant_recovered_line_count": report["candidate_recovered_lines"],
        "control_sentences": report["controls"]["sentences"],
        "control_cases": report["controls"]["cases"],
        "details": "The confusables field in this report contains every variant and Part 2 result.",
        "line": (f"confusables: {report['affected_lines']} of {report['lines']} lines fail today "
                 f"({failed} of {report['total_variants']} variants); candidate recovers {recovered} of {failed} "
                 f"failing variants (all failing variants for {fully_recovered} of {report['affected_lines']} lines); "
                 f"false alarms {a} of {sentence_count} sentences and {b} of {case_count} cases."),
        "plain_sentence": (f"The literal full fold restores {recovered} missed cards and newly cards {a + b} "
                           f"previously proceeding controls, but also removes the card from "
                           f"{report['original_crisis_retention']['lost_cards']} unchanged labelled crisis lines; "
                           "its ASCII mappings and replacement semantics need an operator ruling."),
    }


def run_measurement(*, lines=None, output_dir=MEASUREMENTS, fold_map=None,
                    include_replays=True) -> dict:
    """Run the requested measurements; optional limits are for focused tests only."""
    from .confusables import measure_confusables

    roster = load_roster()
    selected = crisis_lines(roster) if lines is None else list(lines)
    sentences, cases = control_sets()
    vocabulary = extract_vocabulary()
    causes = measure_fuzz_causes(selected, sentences, cases, vocabulary["words"], roster)
    confusables = measure_confusables(selected, sentences, cases, vocabulary["words"], roster,
                                     fold_map=fold_map)
    causes.append(confusables_cause(confusables, len(sentences), len(cases)))
    report = {
        "measurement_date": DATE,
        "policy_changed": False,
        "model_calls": 0,
        "network_calls": 0,
        "scope": "full" if lines is None and fold_map is None and include_replays else "limited test run",
        "crisis_lines": len(selected),
        "control_sentences": len(sentences),
        "control_cases": len(cases),
        "control_baseline_note": "Ten of the 160 expected-PROCEED cases already card; false alarms count only new cards among today's PROCEED cases.",
        "vocabulary": vocabulary,
        "causes": causes,
        "confusables": confusables,
        "spacing": measure_spacing(roster, cases) if include_replays else None,
        "targets_the_crisis": measure_labels(roster) if include_replays else None,
    }
    output_dir = Path(output_dir)
    write_json(output_dir / f"crisis_vocabulary_{DATE}.json", vocabulary)
    write_json(output_dir / f"confusables_{DATE}.json", confusables)
    if include_replays:
        write_json(output_dir / f"spacing_{DATE}.json", report["spacing"])
        write_json(output_dir / f"targets_the_crisis_labels_{DATE}.json", report["targets_the_crisis"])
    write_json(output_dir / f"causes_{DATE}.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=MEASUREMENTS)
    args = parser.parse_args(argv)
    report = run_measurement(output_dir=args.output_dir)
    for cause in report["causes"]:
        print(cause["line"])
        print(cause["plain_sentence"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
