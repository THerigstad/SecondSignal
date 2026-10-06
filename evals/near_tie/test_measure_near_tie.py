"""One M1 smoke test, using unchanged labelled fixtures and sessions."""
from __future__ import annotations

import json
import sys

from evals.near_tie import measure_near_tie as measure
from secondsignal import load_roster, route
from secondsignal.router import ScoredAgent


def test_near_tie_report_shape_and_observation_equivalence():
    ids = {"analysis-career-tradeoff", "crisis-direct", "rr2-aftermath-acks-do-not-consume-window"}
    profile_before = sys.getprofile()
    report = measure.run_report(ids, {"traj-slow-slope-001"})
    assert sys.getprofile() is profile_before
    assert report["schema_version"] == 1 and report["measurement_only"] is True
    assert report["scope"] == "limited smoke"
    assert report["inventory"]["single_turn_cases"] == 3
    assert report["inventory"]["trajectory_files"] == 1
    assert len(report["rows"]) == report["inventory"]["labelled_turns"]
    assert [result["margin_fraction"] for result in report["margins"]] == [0.05, 0.10, 0.15]
    assert len(json.loads(json.dumps(report))["rows"]) == len(report["rows"])

    roster = load_roster()
    for label, case in measure.cases.CASES:
        if case["id"] not in ids:
            continue
        baseline, baseline_session = measure.cases.run_case(case, roster)
        with measure.observe_scores() as observations:
            observed, observed_session = measure.cases.run_case(case, roster)
        assert observed.to_dict() == baseline.to_dict()
        assert observed_session == baseline_session
        assert len(observations) == 1 + len(case.get("prior_turns", []))
        assert len(observations[-1][1]) == len(roster)
        row = next(row for row in report["rows"] if row["label"] == label)
        assert row["turn"] == baseline_session.turn_count
        assert row["top_two_eligible"] == [measure.candidate_row(candidate)
            for candidate in observations[-1][1] if candidate.eligible][:2]
        assert row["actual_agent"] == baseline.agent_id
        if baseline.preempted:
            assert baseline.ranked == ()
            assert row["exclusions"]["card"]
            assert not row["door_margins"]

    trajectory = json.loads((measure.ROOT / "evals/cases/trajectories/slow-slope-001.json")
                            .read_text(encoding="utf-8"))
    session = measure.cases.make_session(trajectory)
    trajectory_rows = [row for row in report["rows"] if row["cohort"] == "trajectory"]
    for index, (turn, row) in enumerate(zip(trajectory["turns"], trajectory_rows), 1):
        decision = route(turn["text"], roster, session=session)
        assert row["turn"] == index
        assert row["latch_after"] == session.latch
        assert row["aftermath_after"] == session.aftermath_turns
        assert row["actual_agent"] == decision.agent_id
    assert len(trajectory_rows) == len(trajectory["turns"])

    previous_doors = 0
    for result in report["margins"]:
        count = result["true_near_tie_doors_literal_floor"]
        assert count >= previous_doors
        previous_doors = count
        assert count + result["excluded_unique_turns"] == result["turns_with_second_within_margin"]
        assert sum(result["precision_timeout_comparison"].values()) == count
        assert sum(pair["turns"] for pair in result["pairs"]) == count
        assert result["exclusions_among_near_ties"]["contraindicated"] == 0
        assert result["plain_sentence"]

    pair = [ScoredAgent("cody", 1.0, ()), ScoredAgent("seren", 0.95, ())]
    assert measure.within_margin(pair, 5)
    assert not measure.within_margin([pair[0], ScoredAgent("seren", 0.9499, ())], 5)
    assert not measure.within_margin([ScoredAgent("cody", 0.0, ()), pair[1]], 15)
    assert measure.timeout_comparison({"agent_any_of": ["cody", "seren"]}, pair, roster)["comparison"] == "both"
    assert measure.timeout_comparison({"agent": "willow"}, pair, roster)["comparison"] == "neither"
    assert measure.timeout_comparison({"agent": None}, pair, roster)["comparison"] == "no_seat_expected"
    assert measure.timeout_comparison({}, pair, roster)["comparison"] == "unlabelled"
    assert report["questions_for_the_operator"]
