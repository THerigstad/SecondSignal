"""One test: run B5b on three existing cases and check the saved report."""
import json

from evals.gap_triage import measure_rest


def test_measure_rest_three_cases_and_report_shape(tmp_path):
    original = measure_rest.cheap.safety.crisis_screen
    output = tmp_path / "rest.json"
    ids = ["gap-obfuscation-b7-032", "gap-obfuscation-b7-013", "order1-recovery-phrase-001"]
    argv = ["--output", str(output), "--control-limit", "2",
            "--variant-line-limit", "1", "--source-limit", "2"]
    for case_id in ids:
        argv.extend(("--case-id", case_id))
    assert measure_rest.main(argv) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["measurement_only"] is True
    assert {row["id"] for row in report["gap_baseline"]} == set(ids)
    candidates = report["candidates"]
    assert len(candidates) == 12
    assert candidates["wider_all"]["recovered_ids"] == [ids[0]]
    assert candidates["narrowed_recovery_crisis_only"]["recovered"] == 0
    assert candidates["narrowed_recovery_routing_experiment"]["recovered_ids"] == [ids[2]]
    for candidate in candidates.values():
        assert candidate["real_card_retention"]["total"] == 1
        assert candidate["line"] and candidate["plain_sentence"]
        for group in candidate["controls"].values():
            assert group["total"] == 2
            assert 0 <= group["new_false_alarms"] <= group["candidate_false_alarms"] <= 2
        if candidate["scope"] == "crisis_only":
            assert all(row["route_input"] == row["text"] for row in candidate["rows"])
    assert report["wider_unrecovered_count"] == 1
    assert report["fake_adapter_smoke"]["adapter"] == "fake"
    assert measure_rest.cheap.safety.crisis_screen is original
