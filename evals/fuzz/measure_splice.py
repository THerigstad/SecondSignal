"""Order G1, 10 October 2026: deterministic splice measurement, ids only.

Run from the repository root with ``python -m evals.fuzz.measure_splice``.
``--before`` selects the landing-8 mask path inside this script only;
``--write`` stores both readings so the comparison is reproducible offline.
Cases with prior turns are not single-message cases. Unspliced misses are
counted and set aside; no case text is written to the measurement.
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_ROOT), str(_ROOT / "src")]

from evals.fuzz.run import _session  # noqa: E402
from secondsignal import load_roster, route, safety  # noqa: E402
from secondsignal.lexicon import PACKS, apply_masks, tokenize  # noqa: E402
from secondsignal.normalize import analyze, screen_fold  # noqa: E402

MEASUREMENT = Path(__file__).with_name("measurements") / "splice_2026-10-10.json"
SPLICES = tuple(("suffix", phrase) for phrase in (
    " on my run", " after my run", " with the boss", " at the plant", " at my job",
    " on the raid", " at the deadline", " in the app", " on the server",
    " in the tutorial", " on the campaign", " on this level", " on my phone",
)) + tuple(("prefix", phrase) for phrase in (
    "after my run, ", "at the plant, ", "boss fight done, ", "on my shift, ",
))


def labelled_cases():
    manifest = json.loads((_ROOT / "evals/case-manifest.json").read_text(encoding="utf-8"))
    documents = {}
    for row in manifest["cases"]:
        source = row["source"]
        if source not in documents:
            doc = json.loads((_ROOT / "evals/cases" / (source + ".json")).read_text(encoding="utf-8"))
            documents[source] = {case["id"]: case for case in doc["cases"]}
        yield row, documents[source][row["id"]]


def splice(text, position, phrase):
    return text + phrase if position == "suffix" else phrase + text


def before_masks(norm, packs=None, *, crisis_only=False, protect=None):
    """The caller keyword is ignored only by the measurement's local patch."""
    return apply_masks(norm, packs, crisis_only=crisis_only, protect=None)


def before_context():
    return patch.object(safety, "apply_masks", before_masks)


def matched_patterns(screen):
    names = []
    for name, patterns in safety.CRISIS_CLASSES.items():
        names.extend(f"en:{name}[{i}]" for i, p in enumerate(patterns) if p.search(screen.masked))
    names.extend(f"en:inconclusive[{i}]" for i, p in enumerate(safety.INCONCLUSIVE_PATTERNS)
                 if p.search(screen.masked))
    names.extend(f"{pack.id}:{ident}" for pack in PACKS.values()
                 for ident, _, p in pack.hits if p.search(screen.masked))
    names.extend(f"{pack.id}:{ident}" for pack in PACKS.values()
                 for ident, p in pack.inconclusive if p.search(screen.masked))
    if safety._other_person_weapon_span(screen.masked):
        names.append("en:other_person_weapon")
    names.extend(f"en:other_person_danger:{group}"
                 for group, _ in safety._other_person_danger(screen.masked))
    return sorted(set(names))


def hit_erasing_masks(text, screen):
    """Name actual blanking spans overlapping an unnegated pre-mask hit."""
    norm, _ = screen_fold(analyze(text).text)
    negation = frozenset(word for pack in PACKS.values() for word in pack.negation)
    patterns = safety.MASK_PROTECTED_PATTERNS + tuple(p for pack in PACKS.values() for _, _, p in pack.hits)
    protected = [(m.start(), m.end()) for p in patterns for m in p.finditer(norm)
                 if not any(token in negation for token, _, _ in tokenize(norm[:m.start()])[-3:])]
    return sorted({span.pattern_id for span in screen.masked_spans if span.kind == "mask"
                   and any(span.start < end and span.end > start for start, end in protected)})


def exclusion_reason(base, current, text, phrase):
    patterns = matched_patterns(base)
    if base.negated:
        return "negated_ideation_three_token_exception"
    if "en:other_person_weapon" in patterns and phrase in {" at my job", "on my shift, "}:
        return "other_person_weapon_occupational_exclusion"
    if "en:direct_ideation[8]" in patterns and phrase == " with the boss":
        return "direct_ideation_tail_exclusion"
    if "en:inconclusive[18]" in patterns:
        norm, _ = screen_fold(analyze(text).text)
        if safety.INCONCLUSIVE_PATTERNS[18].search(norm):
            return "unprotected_inconclusive_jump_game_mask"
        return "inconclusive_jump_preposition_exclusion"
    if any(f"en:inconclusive[{i}]" in patterns for i in (7, 8, 9)):
        return "inconclusive_surrender_object_exclusion"
    if "es-419:es_inc_me_esta_matando" in patterns:
        return "spanish_work_idiom_resolves_inconclusive"
    return "unclassified_exclusion"


def run(before=False):
    roster = load_roster()
    eligible, set_aside, prior = [], [], []
    rows = [{"position":position, "phrase":phrase, "flips":[], "actions":{}} for position, phrase in SPLICES]
    with before_context() if before else nullcontext():
        for entry, case in labelled_cases():
            if case.get("expect", {}).get("safety") != "HUMAN_ESCALATION":
                continue
            if case.get("prior_turns"):
                prior.append(case["id"])
                continue
            base_decision = route(case["text"], roster, session=_session(case))
            if base_decision.safety.action.name != "HUMAN_ESCALATION":
                set_aside.append({"id":case["id"], "disposition":entry["disposition"],
                                  "action":base_decision.safety.action.name})
                continue
            eligible.append(case["id"])
            base = safety.crisis_screen(case["text"])
            for row in rows:
                text = splice(case["text"], row["position"], row["phrase"])
                decision = route(text, roster, session=_session(case))
                row["actions"][case["id"]] = decision.safety.action.name
                if decision.safety.action.name == "HUMAN_ESCALATION":
                    continue
                current = safety.crisis_screen(text)
                row["flips"].append({
                    "id":case["id"], "action":decision.safety.action.name,
                    "mask_ids":sorted({s.pattern_id for s in current.masked_spans if s.kind == "mask"}),
                    "hit_erasing_mask_ids":hit_erasing_masks(text, current),
                    "unspliced_patterns":matched_patterns(base),
                    "unspliced_classes":list(base_decision.safety.crisis_classes),
                    "mask_fired":any(s.kind == "mask" for s in current.masked_spans),
                    "reason":("proximity_mask_erasure" if hit_erasing_masks(text, current)
                              else exclusion_reason(base, current, text, row["phrase"])),
                })
    for row in rows:
        row["count"] = len(row["flips"])
    return {"eligible_count":len(eligible), "eligible_ids":eligible,
            "set_aside_count":len(set_aside), "set_aside":set_aside,
            "prior_turn_cases_excluded":prior, "splices":rows}


def measure():
    before, after = run(before=True), run()
    rows = []
    for left, right in zip(before["splices"], after["splices"]):
        rows.append({"position":left["position"], "phrase":left["phrase"],
                     "before":{k:v for k,v in left.items() if k not in {"position", "phrase"}},
                     "after":{k:v for k,v in right.items() if k not in {"position", "phrase"}}})
    return {"schema_version":1, "date":"2026-10-10", "order":"G1",
            "method":"Every manifest single-message expected card; unspliced misses set aside. Before uses protect=None through a script-local gate patch; after uses the shipped gate. No texts stored.",
            "before":{k:v for k,v in before.items() if k != "splices"},
            "after":{k:v for k,v in after.items() if k != "splices"},
            "splices":rows,
            "gate_exclusions":[{"position":row["position"], "phrase":row["phrase"], **flip}
                               for row in after["splices"] for flip in row["flips"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        result = measure()
        MEASUREMENT.parent.mkdir(parents=True, exist_ok=True)
        MEASUREMENT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        selected = "before" if args.before else "after"
        print(f"G1 splice: {result[selected]['eligible_count']} eligible cases ({selected})")
        for row in result["splices"]:
            print(f"{row['position']} {row['phrase']!r}: {row['before']['count']} -> {row['after']['count']}")
    else:
        result = run(before=args.before)
        print(f"G1 splice: {result['eligible_count']} eligible cases")
        for row in result["splices"]:
            print(f"{row['position']} {row['phrase']!r}: {row['count']}")


if __name__ == "__main__":
    main()
