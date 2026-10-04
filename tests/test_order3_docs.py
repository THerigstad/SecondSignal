"""Order 3 documentation claims checked against their sources and runtime evidence."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from secondsignal import SessionState, load_roster, route

ROOT = Path(__file__).resolve().parents[1]
TRAJECTORIES = ROOT / "evals" / "cases" / "trajectories"


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _trajectory() -> dict:
    return json.loads((TRAJECTORIES / "slow-slope-001.json").read_text(encoding="utf-8"))


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_aftermath_documentation_cites_the_contracts_that_own_it() -> None:
    for path in (
        "docs/adr/0028-trajectory-fixtures.md",
        "evals/cases/trajectories/README.md",
    ):
        text = _text(path)
        for number in ("0023", "0018"):
            assert f"ADR-{number}" in text
        retired_record_number = "0019"
        assert f"ADR-{retired_record_number}" not in text


def test_adjust_note_quotes_the_acknowledgement_exemption_without_extending_it() -> None:
    quote = "an acknowledgement after the card does not consume a count"
    record = _normalized(_text("docs/adr/0023-ledger-and-interlock.md"))
    note = _trajectory()["adjust_note"]
    assert quote in record
    assert quote in note
    assert "not a rule stated by that record" in note
    assert "question for the operator" in note
    assert "misread the record twice" not in note


def test_turn_seven_records_a_verdict_reason_and_no_correction_row() -> None:
    fixture = _trajectory()
    session = SessionState(locale=fixture["locale"], **fixture["session"])
    roster = load_roster()
    for turn in fixture["turns"][:7]:
        decision = route(turn["text"], roster, session=session)
    assert any("retraction after a card recorded as evidence" in reason for reason in decision.safety.reasons)
    assert session.latch_history == []
    assert session.aftermath_turns == fixture["turns"][6]["expect"]["aftermath"]
    why = fixture["turns"][6]["why"]
    assert "verdict reasons" in why and "no correction row" in why


def test_directory_guard_credit_resolves_to_its_actual_function() -> None:
    name = "test_trajectory_files_are_never_collected_as_single_cases"
    tree = ast.parse(_text("tests/test_eval_cases.py"))
    assert any(isinstance(node, ast.FunctionDef) and node.name == name for node in ast.walk(tree))
    citation = f"tests/test_eval_cases.py::{name}"
    for path in (
        "docs/adr/0028-trajectory-fixtures.md",
        "evals/cases/trajectories/README.md",
    ):
        assert citation in _text(path)


def test_ledger_index_distinguishes_built_aftermath_from_unbuilt_ledger() -> None:
    index = json.loads(_text("docs/adr/index.json"))
    row = next(row for row in index["records"] if row["number"] == "0023")
    assert row["decision"] == "Proposed"
    assert "ledger and interlock are not built" in row["notes"]
    assert "bounded aftermath counter and no_joke obligation" in row["notes"]
    evidence = "tests/test_danger_lane.py::test_two_substantive_turns_after_a_card_carry_no_joke_and_the_resources"
    assert evidence in row["evidence"]
    for entry in row["evidence"]:
        filename, name = entry.split("::")
        tree = ast.parse(_text(filename))
        assert any(isinstance(node, ast.FunctionDef) and node.name == name for node in ast.walk(tree))


def test_presentations_decision_incorporates_the_existing_amendment() -> None:
    record = _text("docs/adr/0026-twins-two-presentations-one-routing-contract.md")
    decision = _normalized(record.split("## Decision\n", 1)[1].split("## Amendment 1,", 1)[0])
    assert "three presentations: a woman, a man, or neither" in decision
    assert "as written, women, men, neither" in decision
    assert "per-persona overrides included from the first build" in decision
    assert "full form as the default" in decision
    assert "has two presentations" not in decision
    assert "overrides allowed later" not in decision


def test_qwen_note_matches_the_relative_hold_and_its_family_obligations() -> None:
    document = json.loads(_text("evals/cases/round1_2026-09-02/qwen.json"))
    case = next(case for case in document["cases"] if case["id"] == "qwn-d3-thirdperson-relapse-001")
    decision = route(case["text"], load_roster(), session=SessionState())
    assert decision.seat_claim is None
    assert decision.claim_subject == "other"
    assert "addiction_recovery" in decision.held
    assert decision.agent_id == "cody"
    assert {"affected_person:other", "acknowledge:addiction_recovery", "no_joke"} <= set(decision.obligations)
    assert "hold, not a seat-claim" in case["dispute_note"]
    assert "hold's specialist" in case["dispute_note"]
    assert case["disputed"] is True


@pytest.mark.parametrize("persona,acronym,former", [
    ("cody", "C.A.L.D.E.R.", "Calder"),
    ("ellis", "E.L.L.I.E.", "Ellie"),
    ("rowan", "R.A.V.I.", "Ravi"),
    ("seren", "S.E.R.A.", "Sera"),
])
def test_retired_acronym_headers_are_explicitly_historical(persona, acronym, former) -> None:
    # Expectation flipped under ruling 9 of 3 October 2026: the operator dropped every acronym
    # header, so the retired-name acronym is gone from the header and the retired name lives
    # on only in the alias layer and the change log (it was labelled historical on 30 September).
    text = _text(f"docs/codex/{persona}.md")
    header = text.split("## Part A.", 1)[0]
    assert acronym not in header
    assert "Historical acronym" not in header
    assert former not in header.splitlines()[2], "the tagline under the title names no retired name"
    profile = json.loads(_text(f"src/secondsignal/profiles/{persona}.json"))
    assert former.lower() in profile["aliases"]
    assert header.startswith(f"# {profile['display_name']} codex:")


@pytest.mark.parametrize("persona", ["cody", "ellis", "nikki", "rowan", "seren", "vandal", "willow"])
def test_family_split_logs_name_the_house_block_version_they_carry(persona) -> None:
    text = _text(f"docs/codex/{persona}.md")
    lock = json.loads(_text("docs/codex/house-block.lock.json"))
    part_a = text.split("## Part A.", 1)[1].split("## Part B.", 1)[0]
    assert f"Version {lock['version']}," in part_a
    assert f"Part A, the house block v{lock['version']}, is added" in text
    assert "### v1.1, 11 September 2026: the presentation line" in text
