"""The M1 script runs on a few cases and produces verifiable report fields."""
import json

from evals.gate_cost.measure_gate_cost import run_report


def test_gate_cost_report_shape_and_real_table_slots():
    report = run_report(repetitions=2, audit_repetitions=1, turns_per_day=2,
                        case_limit=3, synthetic_length=320)
    assert json.loads(json.dumps(report))["schema_version"] == 1
    assert report["measurement_only"] and report["scope"] == "smoke/limited"
    assert report["input_inventory"]["considered_for_largest"] == 3
    assert report["input_inventory"]["trajectory_turns"] > 0
    assert report["table_limits"]["everyday_characters"] == 16000
    assert report["machine"]["cpu"] and report["machine"]["python"]
    gate = report["gate"]
    assert gate["occupation"]["actual_slots"] == 4
    assert gate["occupation"]["fake_calls_started"] == 4
    assert gate["occupation"]["all_permits_occupied_before"]
    assert gate["occupation"]["all_permits_occupied_after"]
    for condition in ("idle", "all_slots_occupied"):
        assert len(gate[condition]) == 2
        for row in gate[condition]:
            assert row["identical_decisions_every_repeat"]
            assert "text" not in row["input"]
            for operation in ("crisis_screen", "route"):
                result = row[operation]
                assert result["repetitions"] == len(result["samples_ms"]) == 2
                assert 0 <= result["median_ms"] <= result["worst_ms"]
    for name in ("table_card_idle", "table_card_all_slots_occupied"):
        assert gate[name]["card_returns"] == 2
        assert gate[name]["actual_fake_calls"] == 0
    week = report["audit_week"]
    assert week["turns"] == 14 and week["file_bytes"] > 0
    assert week["template_schema"] == "secondsignal_harness.audit_row.v1"
    assert not week["temporary_file_retained"]
    assert set(week["measurements"]) == {"auditlog_open_parse", "table_build_harness_reopen",
                                         "read_first", "read_last", "read_missing", "rows_in_memory_copy"}
    assert "No fix is applied" in report["after_sentence"]
