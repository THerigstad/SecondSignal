"""M1 offline near-tie measurement; run from the repository root.

Read the actual `scored` local at route return, including its shadow-only
calculation on card turns. No scoring, selection or safety function is changed.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
import test_eval_cases as cases  # noqa: E402

from secondsignal import load_roster, route  # noqa: E402
from secondsignal.profiles import canonicalize_expectation, roster_hash  # noqa: E402
from secondsignal.router import no_signal_seat  # noqa: E402

HERE = ROOT / "evals" / "near_tie"
MARGINS = (5, 10, 15)
EXCLUSIONS = ("contraindicated", "below_stabilizer_floor", "card")
TIMEOUT_BUCKETS = (
    "specialist_only", "other_only", "both", "neither", "no_seat_expected",
    "unlabelled", "specialist_undefined",
)
QUESTIONS = [
    "Does 'below the stabilizer floor' mean the stabilizer profile's declared "
    "lower regulation bound (0.0 in this roster), or the existing dysregulation "
    "threshold (regulation < 0.45), or another published threshold?",
    "For a near-tie timeout, does 'specialist' mean the candidate with fewer "
    "declared domains (the router's exact-tie specialist-precision criterion), "
    "the current routed winner, or the specialist for the request's domain; "
    "and how should equal-precision pairs and multiway score ties be handled?",
    "Is a pre-contraindication counterfactual near-tie count required? The "
    "router gives vetoed candidates status vetoed and score 0 before scoring, "
    "so their hypothetical ungated closeness is not an existing computed fact.",
]


def no_network(*args, **kwargs):
    raise RuntimeError("M1 measurement forbids network access")


@contextmanager
def observe_scores():
    """Copy frozen candidates; do not replace route or alter frame locals."""
    observed = []
    previous = sys.getprofile()

    def observer(frame, event, result):
        if event == "return" and frame.f_code is route.__code__:
            scored = frame.f_locals.get("scored")
            if scored is None or result is None:
                raise RuntimeError("route did not expose its completed scored calculation")
            captured = tuple(scored)
            if result.ranked and result.ranked != captured:
                raise RuntimeError("Observed candidates differ from returned ranked candidates")
            observed.append((result, captured))

    try:
        sys.setprofile(observer)
        yield observed
    finally:
        sys.setprofile(previous)


def candidate_row(candidate):
    return {"agent_id": candidate.agent_id, "score": candidate.score,
            "status": candidate.status, "vetoed": candidate.vetoed}


def timeout_comparison(expected, pair, roster):
    """A conditional descriptor using existing precision, not a timeout policy."""
    ids = [candidate.agent_id for candidate in pair]
    counts = {agent: len(roster[agent].domains) for agent in ids}
    specialist = min(counts, key=counts.get) if len(set(counts.values())) == 2 else None
    label_present = "agent" in expected or "agent_any_of" in expected
    accepted = list(expected.get("agent_any_of", []))
    if "agent" in expected and expected["agent"] not in accepted:
        accepted.append(expected["agent"])
    if not label_present:
        bucket = "unlabelled"
    elif accepted == [None]:
        bucket = "no_seat_expected"
    elif specialist is None:
        bucket = "specialist_undefined"
    else:
        other = next(agent for agent in ids if agent != specialist)
        matches = (specialist in accepted, other in accepted)
        bucket = {(True, False): "specialist_only", (False, True): "other_only",
                  (True, True): "both", (False, False): "neither"}[matches]
    return {"precision_specialist_id": specialist, "domain_counts": counts,
            "expected_ids": accepted, "expected_label_present": label_present,
            "comparison": bucket}


def within_margin(pair, percent):
    if len(pair) < 2 or pair[0].score <= 0:
        return False
    # Router scores have four decimals: integer arithmetic pins inclusivity.
    top = round(pair[0].score * 10000)
    second = round(pair[1].score * 10000)
    return 100 * (top - second) <= percent * top


def turn_row(label, cohort, disposition, fixture, turn, decision, scored, session, roster):
    eligible = [candidate for candidate in scored if candidate.eligible]
    pair = eligible[:2]
    stabilizer = no_signal_seat(roster)
    if stabilizer is None:
        raise ValueError("Loaded roster has no stabilizer")
    floor = roster[stabilizer].regulation_window[0]
    excluded = {"contraindicated": any(candidate.vetoed for candidate in pair),
                "below_stabilizer_floor": decision.signals.regulation < floor,
                "card": decision.preempted or decision.safety.card is not None}
    expected = canonicalize_expectation(turn.get("expect") or {})
    close = [percent / 100 for percent in MARGINS if within_margin(pair, percent)]
    cutoff = [candidate.agent_id for candidate in eligible
              if len(pair) == 2 and candidate.score == pair[1].score]
    timeout = timeout_comparison(expected, pair, roster) if len(pair) == 2 else None
    return {
        "label": label, "cohort": cohort, "disposition": disposition,
        "turn": session.turn_count, "prior_turn_count": len(fixture.get("prior_turns", [])),
        "safety": decision.safety.action.name, "card": decision.safety.card,
        "outcome": decision.outcome.value, "actual_agent": decision.agent_id,
        "shadow_agent": decision.shadow_agent_id, "regulation": decision.signals.regulation,
        "is_dysregulated": decision.signals.is_dysregulated,
        "latch_after": session.latch, "aftermath_after": session.aftermath_turns,
        "expected_safety": expected.get("safety"), "expected_outcome": expected.get("outcome"),
        "expected_seat": {key: expected[key] for key in ("agent", "agent_any_of") if key in expected},
        "ranked_source": "shadow calculation observed at route return" if decision.preempted
        else "public decision ranked (checked against observed calculation)",
        "ranked": [candidate_row(candidate) for candidate in scored],
        "top_two_eligible": [candidate_row(candidate) for candidate in pair],
        "eligible_count": len(eligible), "second_score_tie_ids": cutoff,
        "multiway_cutoff_tie": len(eligible) > 2 and eligible[2].score == eligible[1].score,
        "relative_gap": (pair[0].score - pair[1].score) / pair[0].score
        if len(pair) == 2 and pair[0].score > 0 else None,
        "within_margins": close, "exclusions": excluded,
        "door_margins": close if not any(excluded.values()) else [],
        "precision_timeout_descriptor": timeout,
        "router_reason": decision.reason,
    }


def _disposition(fixture):
    return next((kind for kind in ("known_gap", "disputed", "contract_adjusted")
                 if fixture.get(kind)), "accepted")


def summarize(rows, percent):
    margin = percent / 100
    close = [row for row in rows if margin in row["within_margins"]]
    doors = [row for row in close if margin in row["door_margins"]]
    counts = {reason: sum(row["exclusions"][reason] for row in close) for reason in EXCLUSIONS}
    pairs = Counter(tuple(sorted(candidate["agent_id"] for candidate in row["top_two_eligible"]))
                    for row in doors)
    timeout = Counter(row["precision_timeout_descriptor"]["comparison"] for row in doors)
    accepted_doors = [row for row in doors if row["disposition"] in {"accepted", "contract_adjusted"}]
    sensitivity_removed = sum(row["is_dysregulated"] for row in doors)
    return {
        "margin_fraction": margin, "turns_with_second_within_margin": len(close),
        "exclusions_among_near_ties": counts,
        "excluded_unique_turns": len(close) - len(doors),
        "true_near_tie_doors_literal_floor": len(doors),
        "true_near_tie_doors_percent_all_turns": round(100 * len(doors) / len(rows), 3) if rows else 0,
        "by_cohort": dict(Counter(row["cohort"] for row in doors)),
        "by_disposition": dict(Counter(row["disposition"] for row in doors)),
        "multiway_cutoff_tie_doors": sum(row["multiway_cutoff_tie"] for row in doors),
        "current_winner_outside_reported_pair": sum(row["actual_agent"] not in
            [candidate["agent_id"] for candidate in row["top_two_eligible"]] for row in doors),
        "doors_on_expected_card_turns": sum(row["expected_safety"] == "HUMAN_ESCALATION" for row in doors),
        "pairs": [{"agents": list(pair), "turns": count}
                  for pair, count in sorted(pairs.items(), key=lambda item: (-item[1], item[0]))],
        "precision_timeout_comparison": {bucket: timeout[bucket] for bucket in TIMEOUT_BUCKETS},
        "accepted_or_adjusted_precision_timeout_comparison": {
            bucket: sum(row["precision_timeout_descriptor"]["comparison"] == bucket
                        for row in accepted_doors) for bucket in TIMEOUT_BUCKETS},
        "dysregulation_sensitivity": {"additional_excluded": sensitivity_removed,
                                     "remaining_doors": len(doors) - sensitivity_removed},
        "plain_sentence": f"At a {percent}% relative margin, {len(doors)} of {len(rows)} "
        "labelled turns would offer a person two eligible names under the literal profile-floor "
        f"reading, after {len(close) - len(doors)} close-score turns are excluded; "
        "this is a fixture frequency, not a forecast of live use, and the timeout and multiway pair rules remain undecided.",
    }


def run_report(case_ids=None, trajectory_ids=None):
    """Read-only full replay by default; selections support the one smoke test."""
    singles = cases.CASES
    if case_ids is not None:
        singles = [(label, case) for label, case in singles if case["id"] in case_ids]
        if {case["id"] for _, case in singles} != set(case_ids):
            raise ValueError("Unknown single-turn case id")
    trajectories = []
    for path in sorted((ROOT / "evals/cases/trajectories").glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if trajectory_ids is None or fixture["id"] in trajectory_ids:
            trajectories.append((path, fixture))
    if trajectory_ids is not None and {fixture["id"] for _, fixture in trajectories} != set(trajectory_ids):
        raise ValueError("Unknown trajectory id")
    roster = load_roster()
    rows = []
    with patch.object(socket.socket, "connect", no_network), \
            patch.object(socket.socket, "connect_ex", no_network), \
            patch.object(socket, "create_connection", no_network):
        for label, case in singles:
            with observe_scores() as observations:
                decision, session = cases.run_case(case, roster)
            if len(observations) != len(case.get("prior_turns", [])) + 1:
                raise RuntimeError("Single-case session replay observation count mismatch")
            observed_decision, scored = observations[-1]
            if observed_decision is not decision:
                raise RuntimeError("Final labelled turn was not the last observed route")
            rows.append(turn_row(label, "single", cases.MANIFEST[case["id"]]["disposition"],
                                 case, case, decision, scored, session, roster))
        for path, fixture in trajectories:
            session = cases.make_session(fixture)
            for index, turn in enumerate(fixture["turns"], 1):
                with observe_scores() as observations:
                    decision = route(turn["text"], roster, session=session)
                if len(observations) != 1:
                    raise RuntimeError("Trajectory turn observation count mismatch")
                label = f"{path.relative_to(cases.CASE_DIR).with_suffix('').as_posix()}::turn-{index}"
                rows.append(turn_row(label, "trajectory", _disposition(fixture), fixture, turn,
                                     decision, observations[0][1], session, roster))
    stabilizer = no_signal_seat(roster)
    status_counts = Counter(candidate["status"] for row in rows for candidate in row["ranked"])
    return {
        "schema_version": 1, "date": "2026-10-05", "measurement_only": True,
        "scope": "full" if case_ids is None and trajectory_ids is None else "limited smoke",
        "roster_hash": roster_hash(roster),
        "stabilizer": {"agent_id": stabilizer, "declared_floor": roster[stabilizer].regulation_window[0]},
        "method": {
            "selection": "Every policy single-turn case selected by tests/test_eval_cases.py, including known gaps and disputes; every trajectory turn. Deferred/non-policy fixtures are not router cases.",
            "sessions": "Single-case make_session/run_case is reused with all priors; trajectories use the same make_session and one continuous route-updated session as evals/run_trajectories.py. Priors establish state but are not extra labelled rows.",
            "observation": "Read-only sys.setprofile at the actual route return copies its scored tuple. Public ranked is checked for equality; card observations are shadow-only, never seats. No replacement, re-scoring or safety bypass; prior profiler restored.",
            "eligibility": "Only status scored is eligible. Contraindications, floors, caps and seat claims have already filtered the pair; contraindicated exclusions within an eligible pair are necessarily zero, not evidence that contraindications never matter.",
            "margin": "Inclusive (top-second)/top <= margin, top > 0; exact integer comparison of router scores rounded to four decimals. 5%, 10%, 15% provide narrow/middle/wide sensitivity using the order's published margins.",
            "pair_order": "The first two scored candidates in the router's existing descending-score/ID presentation order. Multiway ties at the second-place cutoff are flagged; this presentation ordering is not a proposed door-selection policy.",
            "floor": "Primary count uses the loaded stabilizer's declared lower bound literally; the existing is_dysregulated threshold is reported separately as sensitivity, not adopted policy.",
            "timeout": "Conditional descriptor only: the pair member with fewer declared domains is the precision specialist, using the router's named exact-tie criterion. Equal domain counts leave specialist undefined. This does not claim a timeout policy for unequal scores or override earlier router rules.",
            "expected_seat": "Canonicalize aliases with the real profile helper; exact agent and accepted agent_any_of retained. Missing seat labels are unlabelled; explicit null is no seat; both/neither and undefined specialist stay separate.",
            "exclusions": "Contraindicated, below literal stabilizer floor, and actual card flags are counted among close eligible pairs; unique excluded count avoids double counting.",
            "network": "Socket connections blocked; route only, no model adapter or vendor selected; no synthetic messages.",
        },
        "inventory": {"single_turn_cases": len(singles), "trajectory_files": len(trajectories),
                      "trajectory_turns": sum(len(fixture["turns"]) for _, fixture in trajectories),
                      "labelled_turns": len(rows), "context_prior_turns": sum(len(case.get("prior_turns", [])) for _, case in singles),
                      "card_turns": sum(row["exclusions"]["card"] for row in rows),
                      "fewer_than_two_eligible": sum(row["eligible_count"] < 2 for row in rows),
                      "candidate_status_counts": dict(status_counts),
                      "turns_with_vetoed_candidates": sum(any(candidate["vetoed"] for candidate in row["ranked"]) for row in rows)},
        "margins": [summarize(rows, percent) for percent in MARGINS],
        "questions_for_the_operator": QUESTIONS, "rows": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "measurements/near_tie_2026-10-05.json")
    args = parser.parse_args(argv)
    report = run_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Compact rows retain all observations within the 2 MB delivery limit.
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n"
    if len(payload.encode("utf-8")) > 2_000_000:
        raise ValueError("Report exceeds the order's 2 MB per-file limit")
    args.output.write_text(payload, encoding="utf-8")
    for margin in report["margins"]:
        print(margin["plain_sentence"])
    print(json.dumps(report["inventory"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
