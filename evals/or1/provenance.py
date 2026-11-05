"""Use the existing results leaf without executing the harness package.

The package initializer imports the runtime harness and therefore the policy.
This evaluation-only adapter loads the unchanged standard-library leaf by its
exact source path. It never creates a replacement package or changes sys.modules.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_RESULTS_PATH = Path(__file__).resolve().parents[2] / "src" / "secondsignal_harness" / "results.py"
_SPEC = importlib.util.spec_from_file_location("secondsignal_harness.results", _RESULTS_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("The required secondsignal_harness.results leaf is unavailable")
_results = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_results)

ABSENT_SPECIFICATION = _results.ABSENT_SPECIFICATION
result_header = _results.result_header
validate_result = _results.validate_result
result_document = _results.result_document
encode_json_result = _results.encode_json_result
write_json_result = _results.write_json_result
read_json_result = _results.read_json_result
render_result_header = _results.render_result_header
write_markdown_result = _results.write_markdown_result
read_markdown_result = _results.read_markdown_result
