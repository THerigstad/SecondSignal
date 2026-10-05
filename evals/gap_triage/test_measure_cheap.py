"""One smoke test of three existing cases; no new crisis fixture text."""
import importlib.util
import sys
from pathlib import Path


def test_measure_three_existing_cases_and_report_shape():
    path = Path(__file__).with_name("measure_cheap.py")
    spec = importlib.util.spec_from_file_location("b5_measure_cheap", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original_screen = module.safety.crisis_screen
    ids = ["gap-obfuscation-b7-013", "gap-obfuscation-b7-028", "gap-obfuscation-b7-066"]
    report = module.run_report(candidate_names=["separators_only", "lookalikes_only", "both"], case_ids=ids, control_limit=1)
    assert report["measurement_only"] is True
    assert len(report["gap_baseline"]) == 3
    assert set(report["candidates"]) == {"separators_only", "lookalikes_only", "both"}
    assert report["candidates"]["separators_only"]["recovered"] == 1
    assert report["candidates"]["lookalikes_only"]["recovered"] == 1
    assert report["candidates"]["both"]["recovered"] == 2
    assert report["b7_residual_count"] == 1
    assert module.safety.crisis_screen is original_screen
    for result in report["candidates"].values():
        assert all(row["route_input"] == row["text"] for row in result["rows"])
        assert all("baseline_false_alarms" in group and "new_false_alarms" in group for group in result["controls"].values())
