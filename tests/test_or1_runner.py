"""Behavioral proofs for the measurement client's receipts and resume boundary."""
from __future__ import annotations

import json

import pytest

from evals.or1 import runner
from evals.or1.client import FakeClient, NotConfigured, RealClient, parse_response
from evals.or1.corpus import load_corpus
from evals.or1.provenance import read_json_result, result_document
from evals.or1.questions import DATA_DIR, ROOT, load_questions
from evals.or1.report import build_report, write_report

Q = [{"id": "crisis_read", "type": "yes-or-no", "allowed_values": ["yes", "no"]}]


def test_real_client_never_reads_environment_or_calls_a_provider(monkeypatch):
    import os

    def forbidden(*args, **kwargs):
        raise AssertionError("A real-client stub must not read a credential")
    monkeypatch.setattr(os, "getenv", forbidden)
    with pytest.raises(NotConfigured, match="No credential has been read"):
        RealClient()


def test_refusal_and_malformed_scripts_keep_reasons_and_host_identity():
    client = FakeClient()
    refused = client.request(requested_model="fake:0", case={}, questions=Q, ordinal=0)
    malformed = client.request(requested_model="fake:0", case={}, questions=Q, ordinal=1)
    a = parse_response(refused.raw_response, Q)["crisis_read"]
    b = parse_response(malformed.raw_response, Q)["crisis_read"]
    assert refused.host_reported_model == malformed.host_reported_model == "scripted/fixed-v1/0"
    assert a["status"] == "refusal" and a["reason"] and a["answer"] is None
    assert b["status"] == "malformed" and b["reason"] and b["answer"] is None
    assert a["probabilities"] is b["probabilities"] is None


def test_invalid_probability_claims_and_missing_answers_are_not_negatives():
    invalid = [
        {"yes": -0.1, "no": 1.1}, {"yes": float("nan"), "no": 0.5},
        {"yes": True, "no": 0}, {"yes": 0.9}, {"yes": 0.8, "no": 0.8},
    ]
    for distribution in invalid:
        raw = json.dumps({"answers": {"crisis_read": {
            "status": "ok", "answer": "yes", "probabilities": distribution,
        }}})
        answer = parse_response(raw, Q)["crisis_read"]
        assert answer["status"] == "malformed"
        assert answer["answer"] is None and answer["probabilities"] is None
    assert parse_response('{"answers": {}}', Q)["crisis_read"]["status"] == "malformed"
    assert parse_response(
        '{"answers":{"crisis_read":{"status":"refusal"}}}', Q
    )["crisis_read"]["status"] == "malformed"


def test_answer_without_probabilities_does_not_invent_confidence():
    raw = '{"answers":{"crisis_read":{"status":"ok","answer":"no"}}}'
    answer = parse_response(raw, Q)["crisis_read"]
    assert answer == {"status": "ok", "answer": "no", "probabilities": None, "reason": None}


def test_runner_writer_rejects_missing_or_false_receipts_before_overwrite(tmp_path):
    path = tmp_path / "r.json"
    path.write_bytes(b"existing")
    with pytest.raises(ValueError, match="header"):
        runner.write_results(path, {"rows": []})
    with pytest.raises(ValueError, match="tree_commit"):
        runner.write_results(path, result_document({"rows": []}, specification_hash="absent"))
    real_hash = result_document({"rows": []}, specification_hash="a" * 64)
    with pytest.raises(ValueError, match="absent"):
        runner.write_results(path, real_hash)
    assert path.read_bytes() == b"existing"


def _small_corpus(monkeypatch, count=2):
    corpus = load_corpus(root=ROOT, questions=load_questions())
    corpus["cases"] = corpus["cases"][:count]
    corpus["coverage"] = {**corpus["coverage"], "selected_cases": count}
    monkeypatch.setattr(runner, "load_corpus", lambda **kwargs: corpus)
    return corpus


def test_partial_resume_reuses_every_completed_response_and_rejects_changed_inputs(
    tmp_path, monkeypatch,
):
    corpus = _small_corpus(monkeypatch)
    path, checkpoints = tmp_path / "r.json", tmp_path / "c"
    first = runner.run(output=path, checkpoint_dir=checkpoints, max_model_rows=3)
    original = [r for r in first["rows"] if r["kind"] == "model"]
    assert len(original) == 3 and first["run"]["completed"] is False

    class RecordingFake(FakeClient):
        def __init__(self):
            self.calls = 0

        def request(self, **kwargs):
            self.calls += 1
            return super().request(**kwargs)

    client = RecordingFake()
    resumed = runner.run(output=path, checkpoint_dir=checkpoints, client=client)
    assert client.calls == len(corpus["cases"]) * 5 - 3
    assert resumed["run"]["completed"] is True
    for row in original:
        assert row in resumed["rows"]
    assert resumed["header"] == first["header"]
    assert read_json_result(path)["header"]["specification_hash"] == "absent"
    panel = json.loads((DATA_DIR / "model-panel.json").read_text(encoding="utf-8"))
    panel["models"][0]["display_name"] += " changed"
    changed = tmp_path / "p.json"
    changed.write_text(json.dumps(panel), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="Resume inputs changed"):
        runner.run(output=path, checkpoint_dir=checkpoints, panel_path=changed)


def test_interrupted_call_does_not_erase_completed_checkpoint(tmp_path, monkeypatch):
    _small_corpus(monkeypatch, 1)

    class InterruptingFake(FakeClient):
        def __init__(self):
            self.calls = 0

        def request(self, **kwargs):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("scripted interruption")
            return super().request(**kwargs)

    checkpoints = tmp_path / "c"
    with pytest.raises(RuntimeError, match="scripted interruption"):
        runner.run(output=tmp_path / "r.json", checkpoint_dir=checkpoints, client=InterruptingFake())
    assert len(list(checkpoints.glob("*.json"))) == 2  # manifest plus completed first response
    resumed = runner.run(output=tmp_path / "r.json", checkpoint_dir=checkpoints)
    assert resumed["run"]["reused_model_rows"] == 1
    assert resumed["run"]["new_model_rows"] == 4


def test_runner_lists_missing_provenance_cases_as_excluded(tmp_path):
    record = json.loads((DATA_DIR / "corpus-provenance.json").read_text(encoding="utf-8"))
    removed = next(e for e in record["files"] if e["scope"] == "single_case_policy")
    record["files"].remove(removed)
    path = tmp_path / "p.json"
    path.write_text(json.dumps(record), encoding="utf-8", newline="\n")
    result = runner.run(
        output=tmp_path / "r.json", checkpoint_dir=tmp_path / "c",
        provenance_path=path, max_model_rows=0,
    )
    excluded = [r for r in result["excluded"] if r["source_file"] == removed["source_file"]]
    assert excluded and all(r["reason"] == "missing_corpus_provenance" for r in excluded)
    assert all(r["source_file"] != removed["source_file"] for r in result["rows"])


def test_full_fake_corpus_writes_receipted_rows_and_question_tables(tmp_path):
    questions = load_questions()
    result = runner.run(output=tmp_path / "fake.json", checkpoint_dir=tmp_path / "c")
    assert result["run"]["completed"]
    assert result["run"]["case_count"] == 693
    assert len(result["rows"]) == 693 * (5 + 2)
    assert not result["excluded"] and result["exclusion_statement"].startswith("No cases")
    assert result["header"]["specification_hash"] == "absent"
    assert result["header"]["reproducibility"] == "not-reproducible"
    assert len(result["header"]["question_set_sha256"]) == 64
    by_kind = {}
    for row in result["rows"]:
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
        assert set(row["labels"]) == set(row["lexicon"]) == {q["id"] for q in questions}
        assert row["timestamp"] and "raw_response" in row and "token_counts" in row
    assert by_kind == {"labels": 693, "lexicon": 693, "model": 3465}
    report = build_report(result, questions)
    assert len(report["comparison_table"]) == 5
    write_report(tmp_path, result, questions)
    assert read_json_result(tmp_path / "calibration.json")["header"] == result["header"]
    table = (tmp_path / "calibration.md").read_text(encoding="utf-8")
    assert all(q["id"] in table for q in questions)
    assert "not-reproducible" in table


def test_stale_lexicon_cannot_follow_a_reused_case_id(tmp_path, monkeypatch):
    corpus = _small_corpus(monkeypatch, 1)
    corpus["cases"][0]["text"] += " A changed message."
    output = tmp_path / "r.json"
    with pytest.raises(ValueError, match="Lexicon input text differs"):
        runner.run(output=output, checkpoint_dir=tmp_path / "c", max_model_rows=0)
    assert not output.exists()
