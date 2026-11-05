"""HM2: stamps bind actual harness turns without entering policy decisions."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from secondsignal import SessionState, load_roster
from secondsignal_harness import AuditLog, CodexStore, FakeAdapter, Harness
from secondsignal_harness.spec import SpecificationError

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "Help me make a plan for my work tomorrow."
REPLY = "Start with one small task."
STAMP_FIELDS = {"specification_hash", "sitting_turn_ordinal", "material_change_event_id"}


def make_harness(**kwargs):
    return Harness(load_roster(), FakeAdapter(script=(REPLY,)),
                   CodexStore(ROOT / "docs/codex"), operator_circle=True, **kwargs)


def test_five_turns_have_one_specification_and_ordinals_one_through_five(tmp_path):
    """The required acceptance sitting uses the real audit sink and only FakeAdapter."""
    harness = make_harness(audit_log=AuditLog(tmp_path / "audit.jsonl"))
    for _ in range(5):
        harness.speak(PROMPT)
    rows = harness.audit_log.rows()
    assert len(rows) == 5
    assert [row["sitting_turn_ordinal"] for row in rows] == [1, 2, 3, 4, 5]
    assert len({row["specification_hash"] for row in rows}) == 1
    assert all(row["material_change_event_id"] is None for row in rows)
    assert all(row["schema"] == "secondsignal_harness.audit_row.v2" for row in rows)
    active = harness.ensure_specification()
    for row in rows:
        active.assert_row(row)
        assert not STAMP_FIELDS.intersection(row["decision"])
        assert row["decision"]["schema_version"] == 1
    stored = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert stored == rows
    assert b"\r" not in (tmp_path / "audit.jsonl").read_bytes()


@pytest.mark.parametrize("text,script,kind", [
    ("I want to kill myself", REPLY, "gate"),
    ("hey", REPLY, "unresolved"),
    (PROMPT, RuntimeError("scripted failure"), "failure"),
    (PROMPT, REPLY, "seated"),
])
def test_all_row_kinds_are_stamped(text, script, kind):
    harness = make_harness()
    harness.adapter = FakeAdapter(script=(script,))
    harness.speak(text)
    row = harness.audit_log.rows()[-1]
    assert row["kind"] == kind
    assert STAMP_FIELDS <= row.keys()
    assert row["sitting_turn_ordinal"] == 1
    assert row["material_change_event_id"] is None
    harness.ensure_specification().assert_row(row)


@pytest.mark.parametrize("text", [PROMPT, "hey", "I want to kill myself"])
def test_a_forged_stamp_raises_even_on_the_gate_branch(text):
    """Corrupting a stamp at the sink is a hard failure, never an audit warning."""
    class Forged(AuditLog):
        def append(self, row):
            return super().append({**row, "specification_hash": "0" * 64})

    harness = make_harness(audit_log=Forged())
    with pytest.raises(SpecificationError):
        harness.speak(text)
    assert harness.audit_log.rows() == []


def test_an_unbound_v2_row_cannot_be_appended():
    with pytest.raises(SpecificationError):
        AuditLog().append({"schema": "secondsignal_harness.audit_row.v2",
                           "specification_hash": "0" * 64,
                           "sitting_turn_ordinal": 1, "material_change_event_id": None})


def test_a_restored_policy_count_does_not_change_the_sitting_ordinal():
    session = SessionState()
    session.turn_count = 17
    harness = make_harness(session=session)
    harness.speak(PROMPT)
    row = harness.audit_log.rows()[-1]
    assert row["turn_index"] == 18 and row["sitting_turn_ordinal"] == 1


def test_same_configuration_with_different_clocks_has_same_specification_hash():
    first = make_harness(clock=lambda: 1.0)
    second = make_harness(clock=lambda: 1000.0)
    first.speak(PROMPT)
    second.speak(PROMPT)
    a, b = first.audit_log.rows()[0], second.audit_log.rows()[0]
    assert a["at"] != b["at"] and a["row_id"] != b["row_id"]
    assert a["specification_hash"] == b["specification_hash"]


def test_a_changed_runtime_control_has_a_new_hash_and_event():
    harness = make_harness()
    harness.speak(PROMPT)
    first = harness.audit_log.rows()[0]
    harness.max_tokens += 1
    harness.speak(PROMPT)
    second = harness.audit_log.rows()[1]
    assert second["specification_hash"] != first["specification_hash"]
    assert second["material_change_event_id"] is not None
    assert second["sitting_turn_ordinal"] == 2
    harness.ensure_specification().assert_row(second)


def test_deepcopy_of_harness_has_independent_staged_state():
    """Existing Table replay callers copy a harness and replace its audit sink."""
    harness = make_harness()
    harness.speak(PROMPT)
    twin = copy.deepcopy(harness)
    twin.audit_log = AuditLog()
    original = harness.ensure_specification().snapshot()
    twin.max_tokens += 1
    twin.speak(PROMPT)
    assert harness.ensure_specification().snapshot() == original
    assert twin.ensure_specification().snapshot() != original


def test_corrupt_specification_storage_reports_failure_without_suppressing_the_card(tmp_path):
    harness = make_harness(audit_log=AuditLog(tmp_path / "audit.jsonl"))
    harness.speak(PROMPT)
    active = harness.ensure_specification()
    digest = active.snapshot()["specification_hash"]
    (tmp_path / "audit.specifications.jsonl").write_text("{}\n", encoding="utf-8", newline="\n")
    turn = harness.speak("I want to kill myself")
    assert turn.release_reason == "gate" and turn.adapter_calls == 0
    assert turn.text == "\n".join(turn.house_lines)
    assert turn.audit_error == "audit write failed: SpecificationError"
    assert turn.row_id == "" and len(harness.audit_log.rows()) == 1
    with pytest.raises(SpecificationError):
        active.read_snapshot(digest)
