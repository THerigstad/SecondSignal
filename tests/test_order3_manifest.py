"""Full manifest explanations must survive refresh, including their endings."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _generator():
    spec = importlib.util.spec_from_file_location(
        "order3_manifest", ROOT / "evals" / "refresh_case_manifest.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_refresh_keeps_every_reason_complete():
    module = _generator()
    notes = {
        (label.split("::", 1)[0], case["id"]):
        case.get("gap_note") or case.get("dispute_note") or case.get("why", "")
        for label, case in module.runner.CASES
    }
    document = module.build()
    reasons = [row for row in document["cases"] if "reason" in row]
    assert reasons
    assert any(len(row["reason"]) > 200 for row in reasons)
    for row in reasons:
        assert row["reason"] == notes[(row["source"], row["id"])]


def test_checked_in_manifest_matches_full_reason_refresh(monkeypatch):
    module = _generator()
    document = json.loads(module.MANIFEST_PATH.read_text(encoding="utf-8"))
    assert document == module.build()
    closures = [row for row in document["cases"] if row.get("accepted_by_order") == "G2B5B"]
    assert len(closures) == 119  # G2B5B Part 7: raw-flag refresh discarded closures -> retain all 119 measured manifest-only acceptances.
    closure_id = closures[0]["id"]
    original = module.runner.field_failures

    def injected_regression(case, decision, session):
        bad = original(case, decision, session)
        return {**bad, "safety": "injected regression"} if case["id"] == closure_id else bad

    monkeypatch.setattr(module.runner, "field_failures", injected_regression)
    with pytest.raises(ValueError, match=f"Accepted manifest closure {closure_id} fails original expectations"):
        module.build()
