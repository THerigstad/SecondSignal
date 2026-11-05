"""Hand-worked calibration examples and honest missing-data/report boundaries."""
from __future__ import annotations

import copy
import json

import pytest

from evals.or1.metrics import (
    SET_MEASURES,
    binary_calibration,
    categorical_agreement,
    corpus_agreement,
    set_measures,
    summarize_model,
    summarize_question,
)
from evals.or1.provenance import read_json_result, read_markdown_result, result_document
from evals.or1.report import build_report, write_report

QUESTION = {"id": "crisis_read", "type": "yes-or-no", "allowed_values": ["yes", "no"]}
MODEL_AUTHOR = {
    "role": "outside_reviewer_model", "kind": "model", "author": "reviewer",
    "model_authored": True, "evidence": "synthetic test record",
}


def _row(case_id, *, label="yes", answer="yes", probability=0.8, status="ok"):
    return {
        "kind": "model", "source_file": "synthetic.json", "case_id": case_id,
        "requested_model": "fake:0", "host_reported_model": "scripted-host:0",
        "labels": {"crisis_read": {
            "status": "labelled" if label is not None else "unlabelled", "value": label,
            "source_field": "expect.crisis_read" if label is not None else None,
            "authorship": copy.deepcopy(MODEL_AUTHOR),
        }},
        "answers": {"crisis_read": {
            "status": status, "answer": answer if status == "ok" else None,
            "probabilities": ({"yes": probability, "no": 1 - probability}
                              if status == "ok" and probability is not None else None),
            "reason": None if status == "ok" else "scripted refusal" if status == "refusal" else "bad JSON",
        }},
    }


def test_binary_calibration_matches_hand_worked_example_and_fixed_bins():
    result = binary_calibration([0.1, 0.2, 0.8, 0.9], [0, 1, 1, 0], [MODEL_AUTHOR] * 4)
    # (.01 + .64 + .04 + .81) / 4 = .375; (.1 + .8 + .2 + .9) / 4 = .5.
    assert result["brier"]["value"] == pytest.approx(0.375)
    assert result["expected_calibration_error"]["value"] == pytest.approx(0.5)
    assert result["brier"]["n"] == 4
    assert sum(result["brier"]["by_authorship"].values()) == 4
    assert len(result["calibration_curve"]) == 10
    assert sum(item["n"] for item in result["calibration_curve"]) == 4
    boundaries = binary_calibration([0, 0.1, 1], [0, 0, 1])["calibration_curve"]
    assert boundaries[0]["n"] == boundaries[1]["n"] == boundaries[9]["n"] == 1
    assert boundaries[9]["upper_inclusive"] is True
    assert boundaries[2]["mean_probability"] is None
    # Two probabilities in one bin must be calibrated against that bin's frequency.
    shared = binary_calibration([0.12, 0.18], [0, 1])
    assert shared["expected_calibration_error"]["value"] == pytest.approx(0.35)
    assert shared["brier"]["value"] == pytest.approx(0.3434)


def test_choice_calibration_declares_normalized_one_versus_rest_scores():
    question = {"id": "domain", "type": "choice", "allowed_values": ["a", "b", "c"]}
    row = _row("choice")
    row["labels"] = {"domain": {"status": "labelled", "value": "a", "authorship": MODEL_AUTHOR}}
    row["answers"] = {"domain": {
        "status": "ok", "answer": "a", "probabilities": {"a": 0.7, "b": 0.2, "c": 0.1},
    }}
    result = summarize_question([row], question)
    # ((.7-1)^2 + .2^2 + .1^2) / 3 = .14/3.
    assert result["brier"]["value"] == pytest.approx(0.14 / 3)
    assert result["expected_calibration_error"]["value"] == pytest.approx(0.2)
    assert result["brier"]["n"] == 1
    assert set(result["options"]) == {"a", "b", "c"}
    assert result["options"]["a"]["brier"]["value"] == pytest.approx(0.09)
    assert "normalized" in result["convention"]


def test_all_six_set_measures_match_hand_worked_sets():
    # Casewise exact = 0,0,1 and Jaccard = .5,0,1.
    # Totals TP=1, FP=1, FN=2. Label a F1=2/3, recall=1/2; b has both zero.
    result = set_measures([{"a", "b"}, {"a"}, set()], [{"a"}, {"b"}, set()],
                          authorships=[MODEL_AUTHOR] * 3)
    expected = dict(zip(SET_MEASURES, [1 / 3, 0.5, 0.4, 1 / 3, 1 / 3, 0.25]))
    for name, value in expected.items():
        assert result[name]["value"] == pytest.approx(value)
        assert result[name]["n"] == 3
        assert sum(result[name]["by_authorship"].values()) == 3
    empty = set_measures([], [])
    assert all(empty[name]["value"] is None for name in SET_MEASURES)
    assert empty["n"] == 0


def test_imbalanced_agreement_matches_kappa_and_ac1_by_hand():
    # 98 no/no; one yes/no; one no/yes. Observed=.98, kappa chance=.9802,
    # AC1 chance=.0198: kappa=-1/99, AC1=4801/4901.
    result = categorical_agreement(["no"] * 98 + ["yes", "no"],
                                   ["no"] * 98 + ["no", "yes"], categories=["yes", "no"])
    assert result["n"] == 100
    assert result["observed_agreement"] == pytest.approx(0.98)
    assert result["cohen_kappa"] == pytest.approx(-1 / 99)
    assert result["gwet_ac1"] == pytest.approx(4801 / 4901)
    assert result["gwet_ac1"] - result["cohen_kappa"] > 0.98


def test_missing_second_labels_and_constant_marginals_are_explicit():
    row = _row("single")
    row["kind"] = "labels"
    result = corpus_agreement([row], [QUESTION])
    assert result["n"] == 0
    assert result["cohen_kappa"] is result["gwet_ac1"] is None
    assert result["status"] == "not-computable"
    assert result["left_by_authorship"] == result["right_by_authorship"] == {}
    assert result["both_labellers_explicitly_human"] is False
    constant = categorical_agreement(["no"] * 3, ["no"] * 3, categories=["yes", "no"])
    assert constant["cohen_kappa"] is None
    assert constant["gwet_ac1"] == 1
    assert constant["status"] == "partly-computable"


def test_unlabelled_refusal_and_malformed_never_become_negative_answers():
    rows = [
        _row("good"), _row("unlabelled", label=None, probability=0.01),
        _row("refused", status="refusal"), _row("malformed", status="malformed"),
    ]
    result = summarize_model(rows, [QUESTION], "fake:0")
    question = result["questions"][0]
    assert question["labelled_pairs"] == 3
    assert question["unlabelled_pairs"] == 1
    assert question["brier"]["n"] == 1
    assert question["brier"]["value"] == pytest.approx(0.04)
    assert question["refusals"] == {"count": 1, "reasons": {"scripted refusal": 1}}
    assert question["malformed"] == 1
    assert result["partial_sets"]["n"] == result["complete_sets"]["n"] == 1
    assert all(json.loads(key)["kind"] == "model" for key in question["brier"]["by_authorship"])


def test_answer_only_data_can_enter_sets_but_never_calibration():
    result = summarize_model([_row("answer-only", probability=None)], [QUESTION], "fake:0")
    question = result["questions"][0]
    assert question["answer_only_pairs"] == 1
    assert question["brier"]["value"] is None
    assert question["brier"]["n"] == 0
    assert result["complete_sets"]["exact_match"]["value"] == 1
    assert result["complete_sets"]["n"] == 1


def test_partial_sets_expose_missing_questions_and_empty_complete_denominator():
    second = {"id": "domain_present:grief", "type": "yes-or-no", "allowed_values": ["yes", "no"]}
    row = _row("partial")
    row["labels"][second["id"]] = {"status": "unlabelled", "value": None, "authorship": {}}
    row["answers"][second["id"]] = {
        "status": "ok", "answer": "no", "probabilities": {"yes": 0.1, "no": 0.9},
    }
    result = summarize_model([row], [QUESTION, second], "fake:0")
    assert result["complete_sets"]["n"] == 0
    assert all(result["complete_sets"][name]["value"] is None for name in SET_MEASURES)
    assert result["partial_sets"]["n"] == 1
    assert result["partial_sets"]["labelled_pairs"] == 1
    assert "not full-question-set" in result["partial_sets"]["warning"]
    assert result["questions"][1]["brier"]["value"] is None
    assert result["questions"][1]["unlabelled_pairs"] == 1


def test_mixed_model_versions_duplicate_rows_and_invalid_probabilities_fail_loudly():
    one, two = _row("one"), _row("two")
    two["requested_model"] = "fake:1"
    with pytest.raises(ValueError, match="cannot pool"):
        summarize_model([one, two], [QUESTION], "fake:0")
    two["requested_model"] = "fake:0"
    two["host_reported_model"] = "another-version"
    with pytest.raises(ValueError, match="cannot pool"):
        summarize_question([one, two], QUESTION)
    with pytest.raises(ValueError, match="duplicate"):
        summarize_model([one, one], [QUESTION], "fake:0")
    bad = _row("bad")
    bad["answers"]["crisis_read"]["probabilities"]["yes"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        summarize_model([bad], [QUESTION], "fake:0")
    bad["answers"]["crisis_read"]["probabilities"] = {"yes": 0.8, "no": 0.8}
    with pytest.raises(ValueError, match="sum to one"):
        summarize_model([bad], [QUESTION], "fake:0")


def test_agreement_preserves_model_authorship_and_uses_only_explicit_second_labels():
    row = _row("paired")
    row["kind"] = "labels"
    row["second_labels"] = copy.deepcopy(row["labels"])
    row["second_labels"]["crisis_read"]["authorship"] = {
        "role": "operator", "kind": "human", "author": "test human", "model_authored": False,
    }
    result = corpus_agreement([row], [QUESTION])
    assert result["n"] == 1
    assert result["both_labellers_explicitly_human"] is False
    assert all(json.loads(key)["kind"] == "model" for key in result["left_by_authorship"])
    assert all(json.loads(key)["kind"] == "human" for key in result["right_by_authorship"])
    row["kind"] = "model"
    with pytest.raises(ValueError, match="never model predictions"):
        corpus_agreement([row], [QUESTION])


def test_score_questions_explicitly_decline_undefined_calibration():
    question = {"id": "score", "type": "score", "allowed_values": [0, 1]}
    row = _row("score")
    row["labels"] = {"score": {"status": "labelled", "value": 1, "authorship": MODEL_AUTHOR}}
    row["answers"] = {"score": {"status": "ok", "answer": 1, "probabilities": None}}
    result = summarize_question([row], question)
    assert result["status"] == "not-computable"
    assert result["brier"]["value"] is None
    assert "No score calibration scale" in result["reason"]


def test_report_keeps_only_separate_model_comparisons_and_preserves_header(tmp_path):
    one, two = _row("case"), _row("case", answer="no", probability=0.2)
    two["requested_model"] = "fake:1"
    two["host_reported_model"] = "scripted-host:1"
    labels = copy.deepcopy(one)
    labels["kind"] = "labels"
    document = result_document({
        "rows": [one, two, labels], "excluded": [], "out_of_scope": [],
        "run": {"mode": "scripted_fake", "completed": True},
    }, specification_hash="absent")
    document["header"].update(tree_commit="test-commit", question_set_sha256="a" * 64)
    report = write_report(tmp_path, document, [QUESTION])
    assert set(report) == {
        "header", "schema_version", "mode", "completed", "scope", "excluded", "out_of_scope",
        "corpus_agreement", "comparison_table",
    }
    assert len(report["comparison_table"]) == 2
    assert report["comparison_table"][0]["questions"][0]["brier"]["value"] == pytest.approx(0.04)
    assert report["comparison_table"][1]["questions"][0]["brier"]["value"] == pytest.approx(0.64)
    assert read_json_result(tmp_path / "calibration.json") == report
    header, markdown = read_markdown_result(tmp_path / "calibration.md")
    assert header == document["header"]
    assert "not measurements of vendor model quality" in markdown
    assert "None were excluded" in markdown
    assert markdown.count("| [0.0, 0.1)") == 2
    assert "Authorship counts" in markdown
    assert b"\r" not in (tmp_path / "calibration.json").read_bytes()
    assert b"\r" not in (tmp_path / "calibration.md").read_bytes()
    damaged = dict(document)
    damaged.pop("header")
    with pytest.raises(ValueError, match="header"):
        build_report(damaged, [QUESTION])


def test_agreement_scope_is_invariant_to_other_paired_question_scales():
    domain = {"id": "domain", "type": "choice", "allowed_values": ["grief", "abuse", "none"]}
    risk = {"id": "risk_ongoing", "type": "yes-or-no", "allowed_values": ["yes", "no"]}
    rows = []
    for index in range(100):
        row = _row(str(index), label="yes" if index == 98 else "no")
        row["kind"] = "labels"
        row["second_labels"] = copy.deepcopy(row["labels"])
        row["second_labels"]["crisis_read"]["value"] = "yes" if index == 99 else "no"
        rows.append(row)
    baseline = corpus_agreement(rows, [QUESTION])
    for row in rows:
        for question, left, right in ((domain, "grief", "abuse"), (risk, "yes", "yes")):
            row["labels"][question["id"]] = {
                "status": "labelled", "value": left, "authorship": MODEL_AUTHOR,
            }
            row["second_labels"][question["id"]] = {
                "status": "labelled", "value": right, "authorship": MODEL_AUTHOR,
            }
    expanded = corpus_agreement(rows, [QUESTION, domain, risk])
    assert expanded["cohen_kappa"] == baseline["cohen_kappa"] == pytest.approx(-1 / 99)
    assert expanded["gwet_ac1"] == baseline["gwet_ac1"] == pytest.approx(4801 / 4901)
    assert expanded["categories"] == baseline["categories"]
    assert expanded["n"] == 100
    assert expanded["scope_question_id"] == "crisis_read"
    assert expanded["excluded_by_scope"] == 200
    assert expanded["excluded_pairs_by_question"] == {"domain": 100, "risk_ongoing": 100}
    assert expanded["paired_by_question"] == {"crisis_read": 100}
    assert sum(expanded["left_by_authorship"].values()) == 100
