"""H1: append timing measures the actual write proof, not a historical lookup."""
from evals.gate_cost.measure_gate_cost import audit_week, offline
from secondsignal_harness.audit_log import AuditLog


def test_h1_measurement_times_actual_append_proof(tmp_path, monkeypatch):
    """The report times two real append proofs after a warm-up and keeps historical metrics separate."""
    calls = []
    original = AuditLog.append

    def observed(self, row):
        result = original(self, row)
        if self.path.name == "audit.jsonl":
            calls.append(result)
        return result

    monkeypatch.setattr(AuditLog, "append", observed)
    with offline():
        report = audit_week(tmp_path, turns_per_day=2, repeats=2)
    proof = report["append_proof"]
    assert proof["proof_method"] == "bounded_tail"
    assert proof["starting_rows"] == 14
    assert proof["repetitions"] == len(proof["samples_ms"]) == 2
    assert len(calls) == 3 + 1 + 2
    assert set(report["measurements"]) == {
        "auditlog_open_parse", "table_build_harness_reopen", "read_first",
        "read_last", "read_missing", "rows_in_memory_copy",
    }
