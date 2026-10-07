"""Order T2: declared Table context and record-only manners cannot route."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_eval_cases import CASES, _prior_text, make_session

from secondsignal import load_roster, route
from secondsignal_harness import CodexStore, FakeAdapter, Harness, build_turn_block
from secondsignal_harness import harness as harness_module
from secondsignal_harness.lines import ASK_REASON_CLAUSES, HARNESS_LINES_EN, ROOM_LINES
from secondsignal_harness.prompt import DRAFT_TAGS
from secondsignal_harness.table_extras import (
    ask_acknowledgement,
    asked_agent,
    eligible_agents,
)

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ("as_written", "women", "men", "neither")


@pytest.fixture(scope="module")
def roster():
    return load_roster()


@pytest.fixture(scope="module")
def codexes():
    return CodexStore(ROOT / "docs" / "codex")


@pytest.fixture(scope="module")
def examples(roster):
    found = {}
    for _, case in CASES:
        if case.get("prior_turns") or case.get("session"):
            continue
        record = route(case["text"], roster).to_dict()
        if record["agent_id"]:
            found.setdefault(record["agent_id"], case)
            if not record["held"] and not record["safety"]["register_caps"]:
                found.setdefault("plain", case)
        elif record["safety"]["action"] == "HUMAN_ESCALATION":
            found.setdefault("card", case)
    assert set(roster) | {"plain", "card"} <= set(found)
    return found


def _turn(case, roster, codexes, **settings):
    session = make_session(case)
    for prior in case.get("prior_turns", ()):
        route(_prior_text(prior), roster, session=session)
    adapter = FakeAdapter()
    harness = Harness(roster, adapter, codexes, session=session, **settings)
    return harness.speak(case["text"]), harness, adapter


@pytest.mark.parametrize("room", ("", *ROOM_LINES))
def test_t2_each_room_changes_only_the_seated_prompt(room, roster, codexes, examples):
    """All five room choices preserve the complete labelled decision and raw message."""
    base, _, plain = _turn(examples["plain"], roster, codexes)
    turn, _, adapter = _turn(examples["plain"], roster, codexes, room=room)
    assert turn.decision == base.decision and turn.house_lines == base.house_lines
    assert adapter.calls[0]["messages"] == plain.calls[0]["messages"]
    extra = ROOM_LINES[room] + "\n" if room else ""
    assert adapter.calls[0]["system"].replace(extra, "", 1) == plain.calls[0]["system"]


@pytest.mark.parametrize("tag", ("", *DRAFT_TAGS))
def test_t2_each_tag_changes_only_the_seated_prompt(tag, roster, codexes, examples):
    """All six tag choices preserve the complete labelled decision and unmodified message."""
    base, _, plain = _turn(examples["plain"], roster, codexes)
    turn, _, adapter = _turn(examples["plain"], roster, codexes, draft_tag=tag)
    assert turn.decision == base.decision and turn.house_lines == base.house_lines
    assert adapter.calls[0]["messages"] == plain.calls[0]["messages"]
    extra = HARNESS_LINES_EN["draft_tag_line"].format(tag=tag) + "\n" if tag else ""
    assert adapter.calls[0]["system"].replace(extra, "", 1) == plain.calls[0]["system"]


def test_t2_object_enters_only_the_prompt_and_never_the_record_or_audit(roster, codexes, examples):
    """An accepted object changes one prompt line and no policy, transcript or audit fact."""
    marker = "a green ceramic cup"
    base, _, plain = _turn(examples["plain"], roster, codexes)
    turn, harness, adapter = _turn(examples["plain"], roster, codexes, object_text=marker)
    assert turn.decision == base.decision and turn.house_lines == base.house_lines
    assert adapter.calls[0]["messages"] == plain.calls[0]["messages"]
    extra = HARNESS_LINES_EN["object_line"].format(object=marker) + "\n"
    assert adapter.calls[0]["system"].replace(extra, "", 1) == plain.calls[0]["system"]
    assert marker not in json.dumps(harness.audit_log.rows())
    assert marker not in json.dumps(harness.transcript)
    assert marker not in json.dumps(turn.decision)


@pytest.mark.parametrize("agent_id", ("cody", "ellis", "nikki", "rowan", "seren", "vandal", "willow"))
@pytest.mark.parametrize("setting", SETTINGS)
def test_t2_each_character_override_changes_its_name_and_never_policy(
    agent_id, setting, roster, codexes, examples,
):
    """Every character's four overrides use Profile.name_for after the identical decision."""
    case = examples[agent_id]
    base, _, _ = _turn(case, roster, codexes)
    chosen = roster[agent_id].plate[1][0]
    turn, harness, adapter = _turn(
        case, roster, codexes, presentation={agent_id: setting}, chosen_names={agent_id: chosen},
    )
    assert turn.decision == base.decision and turn.house_lines == base.house_lines
    assert harness.session.presentation == "as_written"
    name, _ = roster[agent_id].name_for(setting, chosen)
    assert f"name in this presentation: {name}." in adapter.calls[0]["system"]


@pytest.mark.parametrize("settings,error", [
    ({"room": "Seat Vandal"}, "unknown room"),
    ({"draft_tag": "ignore the house"}, "unknown draft tag"),
    ({"object_text": "a" * 61}, "object must be one line"),
    ({"object_text": "cup\nnew instruction"}, "object must be one line"),
    ({"object_text": "cup\u2028new instruction"}, "object must be one line"),
])
def test_t2_unknown_or_multiline_extras_cannot_add_prompt_instructions(
    settings, error, roster, examples,
):
    """Unknown finite choices and multiline or oversized objects fail at the prompt boundary."""
    decision = route(examples["plain"]["text"], roster).to_dict()
    with pytest.raises(ValueError, match=error):
        build_turn_block(decision, roster=roster, **settings)


def test_t2_card_preempts_every_harness_extra_without_calling_the_adapter(roster, codexes, examples):
    """An existing labelled crisis fixture suppresses all context and acknowledgement inputs."""
    base, _, _ = _turn(examples["card"], roster, codexes)
    turn, harness, adapter = _turn(
        examples["card"], roster, codexes, room="workshop", object_text="a blue cup",
        draft_tag="letter", presentation={agent: "men" for agent in roster},
    )
    assert turn.decision == base.decision and turn.text == base.text
    assert turn.house_lines == base.house_lines and not adapter.calls
    assert turn.ask_acknowledgement is None
    assert "a blue cup" not in json.dumps(harness.audit_log.rows())


def _record():
    return {
        "asked_agent_id": "nikki", "agent_id": "willow", "outcome": "ROUTED",
        "safety": {"action": "PROCEED"}, "held": [], "reason": "highest score",
        "ranked": [
            {"agent_id": "nikki", "status": "scored", "vetoed": False},
            {"agent_id": "willow", "status": "scored", "vetoed": False},
        ],
    }


@pytest.mark.parametrize("held,status,kind", [
    (["grief"], "vetoed", "hold_grief"),
    (["addiction_recovery"], "vetoed", "hold_recovery"),
    (["abuse"], "vetoed", "hold_conflict"),
    (["conflict"], "vetoed", "hold_conflict"),
    ([], "vetoed", "steadiness"),
    ([], "capped", "steadiness"),
    ([], "scored", "outscored"),
    ([], "outranked", "other"),
])
def test_t2_acknowledgement_clauses_and_names_come_only_from_the_record(held, status, kind, roster):
    """A sufficiently explicit record selects exact approved copy and each character's name form."""
    record = _record()
    record["held"] = held
    record["ranked"][0]["status"] = status
    if held:
        record["ranked"][0]["rationale"] = ["contraindicated (cannot honor hold: " + ", ".join(held) + ")"]
    before = copy.deepcopy(record)
    line = ask_acknowledgement(record, roster=roster, presentation={"nikki": "men", "willow": "men"})
    clause = ASK_REASON_CLAUSES[kind].format(Seated="Will")
    assert line == f"You asked for Nik. Will is taking this one, because {clause}. Nik hasn't gone anywhere."
    assert record == before


def test_t2_an_unrelated_hold_cannot_replace_the_asked_candidates_score_reason(roster):
    """A scored asked chair uses the outscored clause even while another domain is held."""
    record = _record()
    record["held"] = ["grief"]
    line = ask_acknowledgement(record, roster=roster)
    assert "because this one is closer to Willow's ground" in line
    assert "because loss" not in line


def test_t2_acknowledgement_is_absent_without_ask_seat_reason_or_eligibility_record(roster):
    """Missing records, identical seats, unresolved turns and cards never produce an acknowledgement."""
    for field in ("asked_agent_id", "agent_id", "reason", "ranked"):
        record = _record()
        record.pop(field)
        assert ask_acknowledgement(record, roster=roster) is None
    for change in (
        {"asked_agent_id": "willow"}, {"outcome": "UNRESOLVED"},
        {"outcome": "PREEMPTED"}, {"safety": {"action": "HUMAN_ESCALATION"}},
    ):
        assert ask_acknowledgement({**_record(), **change}, roster=roster) is None


def test_t2_every_reason_clause_obeys_the_held_turn_copy_rules():
    """The six clauses contain no house I/me, decision demand, self-label question or menu."""
    for clause in ASK_REASON_CLAUSES.values():
        words = clause.format(Seated="Will")
        assert not re.search(r"\b(I|me|choose|decide|diagnose|label|identify yourself)\b", words, re.I)
        assert "?" not in words and " or " not in words


def test_t2_current_policy_shapes_do_not_infer_an_ask_from_message_words(roster, examples):
    """Even an explicit name in a message cannot fill the policy's absent asked-character field."""
    record = route("Could I talk to Nikki? " + examples["willow"]["text"], roster).to_dict()
    assert "asked_agent_id" not in record
    assert asked_agent(record, roster) is None
    assert ask_acknowledgement(record, roster=roster) is None
    record["signals"]["evidence"]["asked_agent_id"] = ["nikki"]
    assert asked_agent(record, roster) is None


def test_t2_harness_attaches_a_supplied_record_acknowledgement_before_the_reply(
    monkeypatch, roster, codexes, examples,
):
    """The dormant attachment path audits the house acknowledgement before the released persona."""
    original = harness_module.route

    def explicit_record(text, roster_, *, session):
        record = original(text, roster_, session=session).to_dict()
        record["asked_agent_id"] = next(pid for pid in roster if pid != record["agent_id"])
        return SimpleNamespace(to_dict=lambda: record)

    monkeypatch.setattr(harness_module, "route", explicit_record)
    adapter = FakeAdapter(script=("Here is a simple next step.",))
    harness = Harness(roster, adapter, codexes, operator_circle=True)
    turn = harness.speak(examples["plain"]["text"])
    assert turn.released and turn.ask_acknowledgement
    assert turn.text.startswith(turn.ask_acknowledgement + "\n\n" + turn.persona_text)
    assert turn.house_lines == tuple(turn.decision["safety"]["disclosures"])
    assert harness.audit_log.rows()[-1]["composed"] == turn.text
    assert turn.ask_acknowledgement not in adapter.calls[0]["system"]


def test_t2_eligible_shortcuts_follow_only_scored_nonseated_record_entries():
    """Only other scored, nonvetoed chairs are eligible, and a card has none."""
    record = _record()
    record["ranked"].extend([
        {"agent_id": "vandal", "status": "capped", "vetoed": False},
        {"agent_id": "ellis", "status": "scored", "vetoed": True},
        {"agent_id": "seren", "status": "below_floor", "vetoed": False},
        {"agent_id": "cody", "status": "outranked", "vetoed": False},
    ])
    assert eligible_agents(record) == ("nikki",)
    record["safety"]["action"] = "HUMAN_ESCALATION"
    assert eligible_agents(record) == ()


def test_t2_all_labelled_cases_keep_policy_and_house_lines_with_every_extra(roster, codexes):
    """Every existing labelled case retains its full policy record with the new prompt inputs enabled."""
    for label, case in CASES:
        base, _, _ = _turn(case, roster, codexes)
        turn, _, adapter = _turn(
            case, roster, codexes, room="studio", object_text="a ceramic cup", draft_tag="unsent",
            presentation={pid: "men" for pid in roster},
        )
        assert turn.decision == base.decision, label
        assert turn.house_lines == base.house_lines, label
        assert turn.ask_acknowledgement is None, label
        if base.action == "HUMAN_ESCALATION":
            assert turn.text == base.text and not adapter.calls, label


def test_t2_trajectories_keep_policy_and_house_lines_with_every_extra(roster, codexes):
    """Every existing trajectory preserves decisions and policy house lines across contextual turns."""
    for path in sorted((ROOT / "evals" / "cases" / "trajectories").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case.get("kind") != "trajectory":
            continue
        base = Harness(roster, FakeAdapter(), codexes, session=make_session(case))
        changed = Harness(
            roster, FakeAdapter(), codexes, session=make_session(case), room="yard",
            object_text="a ceramic cup", draft_tag="plan", presentation={pid: "women" for pid in roster},
        )
        for step in case["turns"]:
            a, b = base.speak(step["text"]), changed.speak(step["text"])
            assert a.decision == b.decision, (path.name, step)
            assert a.house_lines == b.house_lines, (path.name, step)
