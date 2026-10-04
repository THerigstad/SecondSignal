"""Full manifest explanations must survive refresh, including their endings."""

import importlib.util
import json
from pathlib import Path

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


def test_checked_in_manifest_matches_full_reason_refresh():
    module = _generator()
    document = json.loads(module.MANIFEST_PATH.read_text(encoding="utf-8"))
    assert document == module.build()
