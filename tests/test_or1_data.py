"""Behavioural checks for the fixed question set and immutable fixture inputs."""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from evals.or1.corpus import case_disposition, labels_for_case, load_corpus
from evals.or1.questions import QUESTIONS_PATH, ROOT, load_questions, question_set_hash
from evals.or1_lexicon import build_lexicon, load_policy_modules, measure_text
from evals.run_fixtures import case_disposition as fixture_disposition


def _write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document) + "\n", encoding="utf-8", newline="\n")


def test_question_data_matches_tree_and_marks_clinical_review():
    questions = load_questions()
    by_id = {question["id"]: question for question in questions}
    signals, _ = load_policy_modules()
    assert len(questions) == 9
    assert {q["domain"] for q in questions if q["id"].startswith("domain_present:")} == set(signals.HOLD_DOMAINS)
    assert set(by_id["domain"]["allowed_values"]) == set(signals.DOMAIN_LEXICON) | {"none"}
    assert "regulation" not in by_id
    assert by_id["intent_to_act"]["most_clinically_loaded_label"] is True
    assert by_id["intent_to_act"]["clinical_review_priority"] == 1
    for identifier in ("risk_ongoing", "intent_to_act", "most_severe_risk"):
        assert by_id[identifier]["benchmark_equivalent"] is False
        assert "no publication identifier" in by_id[identifier]["source_status"]
    assert question_set_hash() == hashlib.sha256(QUESTIONS_PATH.read_bytes()).hexdigest()


def test_question_loader_rejects_ambiguous_option_data(tmp_path):
    document = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    document["questions"][0]["allowed_values"] = ["yes", "yes"]
    path = tmp_path / "q.json"
    _write(path, document)
    with pytest.raises(ValueError, match="ordered yes, no"):
        load_questions(path)
    document["questions"][0]["allowed_values"] = ["yes", "no"]
    document["questions"][1]["id"] = document["questions"][0]["id"]
    _write(path, document)
    with pytest.raises(ValueError, match="unique"):
        load_questions(path)


def test_only_explicit_binary_crisis_labels_are_used():
    corpus = load_corpus()
    counts = Counter()
    for case in corpus["cases"]:
        assert case["existing_labels"]["expect"] == case["fixture"].get("expect", {})
        for identifier, label in case["labels"].items():
            if label["status"] == "labelled":
                assert identifier == "crisis_read"
                assert label["source_field"] == "expect.crisis_read"
                assert label["source_value"] in {"HIT", "MISS"}
                counts[label["value"]] += 1
            else:
                assert label["value"] is None
    assert counts == {"yes": 18, "no": 110}
    case = {"id": "probe", "expect": {"safety": "HUMAN_ESCALATION", "agent": "willow"},
            "crisis_category": "direct_ideation"}
    labels = labels_for_case(case, load_questions(), {})
    assert all(label["status"] == "unlabelled" for label in labels.values())
    case["expect"]["crisis_read"] = "INCONCLUSIVE"
    labels = labels_for_case(case, load_questions(), {})
    assert labels["crisis_read"]["status"] == "unlabelled"
    assert labels["crisis_read"]["source_value"] == "INCONCLUSIVE"


def test_provenance_covers_every_file_without_changing_fixture_bytes():
    corpus = load_corpus()
    assert corpus["coverage"]["recorded_files"] == 65
    assert corpus["coverage"]["covered_files"] == 65
    assert corpus["coverage"]["selected_cases"] == 693
    assert corpus["coverage"]["missing_recorded_files"] == []
    assert len(corpus["out_of_scope"]) == 30
    assert corpus["excluded"] == []
    assert corpus["exclusion_status"] == "none"
    provenance = json.loads((ROOT / "evals/or1/data/corpus-provenance.json").read_text(encoding="utf-8"))
    for entry in provenance["files"]:
        assert entry["synthetic"] is True
        assert entry["sha256"] == hashlib.sha256((ROOT / entry["source_file"]).read_bytes()).hexdigest()


def test_absent_provenance_excludes_and_names_every_affected_case(tmp_path):
    provenance = json.loads((ROOT / "evals/or1/data/corpus-provenance.json").read_text(encoding="utf-8"))
    removed = "evals/cases/routing.json"
    provenance["files"] = [entry for entry in provenance["files"] if entry["source_file"] != removed]
    path = tmp_path / "p.json"
    _write(path, provenance)
    corpus = load_corpus(provenance_path=path)
    assert len(corpus["cases"]) == 687
    assert len(corpus["excluded"]) == 6
    assert {case["source_file"] for case in corpus["excluded"]} == {removed}
    assert {case["reason"] for case in corpus["excluded"]} == {"missing_corpus_provenance"}


def test_stale_provenance_hash_fails_instead_of_trusting_changed_text(tmp_path):
    provenance = json.loads((ROOT / "evals/or1/data/corpus-provenance.json").read_text(encoding="utf-8"))
    provenance["files"][0]["sha256"] = "0" * 64
    path = tmp_path / "p.json"
    _write(path, provenance)
    with pytest.raises(ValueError, match="fixture bytes differ"):
        load_corpus(provenance_path=path)


def test_model_authorship_and_current_adjustments_are_not_called_human():
    corpus = load_corpus()
    authored = [label["authorship"] for case in corpus["cases"] for label in case["labels"].values()
                if label["status"] == "labelled"]
    assert any(author["kind"] == "model" for author in authored)
    assert all(author["kind"] != "human" for author in authored)
    provenance = json.loads((ROOT / "evals/or1/data/corpus-provenance.json").read_text(encoding="utf-8"))
    adjusted = [override for entry in provenance["files"]
                for override in entry.get("case_overrides", {}).values()
                if "original_label_authorship" in override]
    assert len(adjusted) == 18
    assert all(override["label_authorship"]["kind"] == "unconfirmed" for override in adjusted)
    forged = {"label_authorship": {"kind": "human", "role": "outside_reviewer_model",
                                   "author": "fake model", "model_authored": True}}
    with pytest.raises(ValueError, match="cannot be reported as human"):
        labels_for_case({"id": "probe", "expect": {"crisis_read": "HIT"}}, load_questions(), forged)


def test_raw_flags_and_effective_dispositions_match_fixture_contract():
    corpus = load_corpus()
    manifest = json.loads((ROOT / "evals/case-manifest.json").read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in manifest["cases"]}
    closures = 0
    for case in corpus["cases"]:
        fixture = case["fixture"]
        source = case["source_file"].removeprefix("evals/cases/").removesuffix(".json")
        expected = fixture_disposition(fixture, by_id[case["case_id"]], source=source)
        assert case["disposition"] == expected
        assert case["raw_flags"] == {flag: fixture[flag] for flag in ("known_gap", "disputed", "contract_adjusted") if flag in fixture}
        assert case["effective_flags"] == {flag: expected == flag for flag in ("known_gap", "disputed", "contract_adjusted")}
        if fixture.get("known_gap") and expected == "accepted":
            closures += 1
    assert closures == 119
    assert corpus["coverage"]["dispositions"] == {
        "accepted": 609, "known_gap": 50, "disputed": 17, "contract_adjusted": 17}


def test_unapproved_manifest_closure_is_rejected():
    case = {"id": "probe", "known_gap": True, "gap_note": "original", "expect": {"safety": "HUMAN_ESCALATION"}}
    entry = {"id": "probe", "source": "probe", "disposition": "accepted",
             "previous_disposition": "known_gap", "accepted_by_order": "G2B5B",
             "accepted_on": "2026-11-04", "reason": "original", "acceptance_reason": "verified",
             "previous_mismatch_fields": ["safety"]}
    assert case_disposition(case, entry, source="probe") == "accepted"
    for key in ("accepted_by_order", "accepted_on", "reason", "acceptance_reason", "previous_mismatch_fields"):
        bad = copy.deepcopy(entry)
        bad.pop(key)
        with pytest.raises(ValueError):
            case_disposition(case, bad, source="probe")
    with pytest.raises(ValueError):
        case_disposition({**case, "disputed": True}, entry, source="probe")


def test_lexicon_preserves_multi_domain_and_unavailable_probes():
    measured = measure_text("My dad died and I need a plan for my job", load_questions())
    assert measured["questions"]["domain_present:grief"]["answer"] == "yes"
    assert len(measured["observed"]["domains"]) > 1
    assert measured["questions"]["domain"]["status"] == "unavailable"
    for identifier in ("risk_ongoing", "intent_to_act", "most_severe_risk"):
        assert measured["questions"][identifier]["status"] == "unavailable"
        assert measured["questions"][identifier]["answer"] is None
    inconclusive = measure_text("I don't want to die", load_questions())
    assert inconclusive["observed"]["crisis_read"] == "INCONCLUSIVE"
    assert inconclusive["questions"]["crisis_read"]["answer"] is None


def test_full_lexicon_export_has_provenance_and_all_cases(tmp_path):
    path = tmp_path / "lex.json"
    document = build_lexicon(output_path=path)
    assert len(document["verdicts"]) == 693
    assert document["header"]["specification_hash"] == "absent"
    assert document["header"]["reproducibility"] == "not-reproducible"
    assert document["header"]["question_set_sha256"] == question_set_hash()
    assert json.loads(path.read_text(encoding="utf-8")) == document
    assert all(len(row["questions"]) == 9 for row in document["verdicts"])
    expected_hashes = {
        (case["source_file"], case["case_id"]): hashlib.sha256(case["text"].encode("utf-8")).hexdigest()
        for case in load_corpus()["cases"]
    }
    assert {
        (row["source_file"], row["case_id"]): row["input_text_sha256"]
        for row in document["verdicts"]
    } == expected_hashes
