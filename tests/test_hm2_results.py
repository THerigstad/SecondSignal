"""New result files carry explicit provenance; historical results keep their bytes."""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

from secondsignal_harness.results import (
    ABSENT_SPECIFICATION,
    encode_json_result,
    read_json_result,
    read_markdown_result,
    result_document,
    result_header,
    write_json_result,
    write_markdown_result,
)

ROOT = Path(__file__).resolve().parents[1]
ABSENT_HEADER = {"specification_hash": "absent", "reproducibility": "not-reproducible"}


@pytest.mark.parametrize("document", [
    {}, {"header": {}}, {"header": {"reproducibility": "not-reproducible"}},
    {"header": None}, [],
])
def test_missing_hash_is_rejected_by_the_actual_json_writer_and_reader(tmp_path, document):
    target = tmp_path / "results.json"
    with pytest.raises(ValueError, match="specification_hash"):
        write_json_result(target, document)
    assert not target.exists()
    target.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="specification_hash"):
        read_json_result(target)


@pytest.mark.parametrize("hash_value", [None, "", "missing", "0" * 63, "g" * 64, 1])
def test_invalid_hash_is_not_an_absence_marker(tmp_path, hash_value):
    document = {"header": {"specification_hash": hash_value,
                           "reproducibility": "not-reproducible"}}
    with pytest.raises(ValueError, match="specification_hash"):
        write_json_result(tmp_path / "results.json", document)


@pytest.mark.parametrize("specification_hash, reproducibility", [
    (ABSENT_SPECIFICATION, "not-reproducible"), ("0123456789abcdef" * 4, "reproducible"),
])
def test_json_and_markdown_roundtrip_with_explicit_provenance(
    tmp_path, specification_hash, reproducibility,
):
    payload = [{"requested_model": "requested-model", "host_reported_model": "actual-model"}]
    document = result_document(payload, specification_hash=specification_hash)
    expected_header = {"specification_hash": specification_hash, "reproducibility": reproducibility}
    assert document == {"header": expected_header, "results": payload}
    json_path = tmp_path / "results.json"
    write_json_result(json_path, document)
    assert read_json_result(json_path) == document
    body = "# Evaluation results\n\nOne model answered.\n"
    markdown_path = tmp_path / "results.md"
    write_markdown_result(markdown_path, body, header=expected_header)
    assert read_markdown_result(markdown_path) == (expected_header, body)
    assert f"**Reproducibility:** {reproducibility}." in markdown_path.read_text(encoding="utf-8")
    assert b"\r" not in json_path.read_bytes() + markdown_path.read_bytes()


@pytest.mark.parametrize("specification_hash, claim", [
    ("absent", "reproducible"), ("0" * 64, "not-reproducible"), ("absent", None),
])
def test_contradictory_header_is_rejected_before_overwriting_existing_file(
    tmp_path, specification_hash, claim,
):
    path = tmp_path / "result.json"
    path.write_bytes(b"existing result")
    header = {"specification_hash": specification_hash, "reproducibility": claim}
    with pytest.raises(ValueError, match="reproducibility"):
        write_json_result(path, {"header": header})
    assert path.read_bytes() == b"existing result"


def test_markdown_reader_and_writer_reject_missing_hash(tmp_path):
    path = tmp_path / "results.md"
    with pytest.raises(ValueError, match="specification_hash"):
        write_markdown_result(path, "result body", header={})
    assert not path.exists()
    path.write_text("# Result without a header\n", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="specification_hash"):
        read_markdown_result(path)


def test_markdown_header_cannot_disagree_with_its_visible_claim(tmp_path):
    path = tmp_path / "results.md"
    write_markdown_result(path, "unchanged body", header=ABSENT_HEADER)
    changed = path.read_text(encoding="utf-8").replace(
        "**Reproducibility:** not-reproducible.", "**Reproducibility:** reproducible.",
    )
    path.write_text(changed, encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="disagrees"):
        read_markdown_result(path)


def test_payload_cannot_replace_header_and_size_limit_includes_header(tmp_path):
    with pytest.raises(ValueError, match="replace"):
        result_document({"header": {}}, specification_hash=ABSENT_SPECIFICATION)
    document = result_document({"rows": ["caf\u00e9"]}, specification_hash=ABSENT_SPECIFICATION)
    length = len(encode_json_result(document).encode("utf-8"))
    path = tmp_path / "bounded.json"
    with pytest.raises(ValueError, match="file-size"):
        write_json_result(path, document, max_bytes=length - 1)
    assert not path.exists()
    write_json_result(path, document, max_bytes=length)
    assert read_json_result(path) == document


def test_b1_result_writer_preserves_observations_and_adds_header(tmp_path):
    from evals.fuzz.measure_causes import write_json
    payload = {"measurement_only": True, "observations": [{"unchanged": "caf\u00e9"}]}
    path = tmp_path / "causes.json"
    write_json(path, payload)
    assert read_json_result(path) == {"header": ABSENT_HEADER, **payload}
    assert "header" not in payload


@pytest.mark.parametrize("module_name, payload", [
    ("evals.gap_triage.measure_cheap", {"candidates": {}, "vocabulary_count": 0,
                                      "b7_residual_count": 0}),
    ("evals.gap_triage.measure_rest", {"candidates": {}, "after_picture": {}}),
    ("evals.near_tie.measure_near_tie", {"margins": [], "inventory": {}}),
    ("evals.gate_cost.measure_gate_cost", {
        "machine": {"line": "test machine"},
        "gate": {"idle": [], "all_slots_occupied": [],
                 "table_card_idle": {"median_ms": 1, "worst_ms": 2},
                 "table_card_all_slots_occupied": {"median_ms": 1, "worst_ms": 2}},
        "audit_week": {"turns": 1, "file_bytes": 2, "measurements": {},
                       "append_proof": {"plain_sentence": "test"}},
        "after_sentence": "test",
    }),
    ("evals.vocabulary.measure_vocabulary_candidates", {"measurement_only": True,
                                                       "observations": ["unchanged"]}),
])
def test_measurement_cli_writes_header_without_changing_payload(
    tmp_path, monkeypatch, module_name, payload,
):
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "run_report", lambda *args: payload)
    if hasattr(module, "print_summary"):
        monkeypatch.setattr(module, "print_summary", lambda report: None)
    path = tmp_path / "measurement.json"
    assert module.main(["--output", str(path)]) == 0
    assert read_json_result(path) == {"header": ABSENT_HEADER, **payload}
    assert "header" not in payload


def test_splice_cli_writes_header_without_changing_payload(tmp_path, monkeypatch):
    from evals.fuzz import measure_splice
    payload = {"after": {"eligible_count": 1}, "splices": []}
    monkeypatch.setattr(measure_splice, "measure", lambda: payload)
    path = tmp_path / "splice.json"
    monkeypatch.setattr(measure_splice, "MEASUREMENT", path)
    monkeypatch.setattr(sys, "argv", ["measure_splice", "--write"])
    measure_splice.main()
    assert read_json_result(path) == {"header": ABSENT_HEADER, **payload}


def test_order1_cli_keeps_replay_rows_and_records_explicit_absence(tmp_path, monkeypatch):
    from evals import order1_replay
    cases = tmp_path / "cases"
    cases.mkdir()
    (cases / "small.json").write_text(
        json.dumps({"cases": [{"id": "empty", "text": "hello"}]}),
        encoding="utf-8", newline="\n",
    )
    path = tmp_path / "order1.json"
    monkeypatch.setattr(sys, "argv", ["order1_replay", "--cases-dir", str(cases),
                                     "--output", str(path)])
    order1_replay.main()
    document = read_json_result(path)
    assert document["header"] == ABSENT_HEADER
    assert len(document["results"]) == 1
    assert document["results"][0] == {
        "id": "empty", "source": "small.json", "action": "PROCEED", "outcome": "UNRESOLVED",
        "agent": None, "assist": None, "held": [], "obligations": [], "claim_subject": None,
        "seat_claim": None, "card": None, "latch": "none", "preferences": {},
    }


def test_fixture_report_can_bind_an_explicit_specification_hash(tmp_path):
    from evals.run_fixtures import render_markdown, write_report
    path = tmp_path / "fixtures.md"
    summary = write_report(path, specification_hash="a" * 64)
    header, body = read_markdown_result(path)
    assert header == result_header("a" * 64)
    assert body == render_markdown(summary)


def test_historical_results_remain_byte_identical():
    directory = ROOT / "evals/results"
    paths = sorted(
        (path for path in directory.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(directory).as_posix(),
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(directory).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    assert len(paths) == 54
    assert digest.hexdigest() == "20f43326267546d5560521e17ed168a88457723076c65bb661b54b55d08d9eb3"
