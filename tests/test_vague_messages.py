"""Vague messages (ruling 5 of 3 October 2026), adapted from Grok's night-order-5
test ``tests/test_vague_message_eval.py`` of 30 September 2026.

Grok's eval found 22 of 30 everyday openers getting a question back and 8
seating a character on a single word ("Too much laundry" seated the
stabilizer; "Phone died" seated the grief persona with a grief hold), and its
five trajectories locked in the policy of the day: the stabilizer seated on
the second vague message. The operator ruled otherwise:

* a second vague message in a row gets a second, different question, not a
  repeat of the first; the decision records which ask is due (``house_ask``);
* the stabilizer seats on the third vague message in a row, with a question
  attached (the ``ask_question`` obligation), not a plan;
* the rider: a lone weak word or fragment never seats anyone and never sets a
  hold; it gets a question.

Every expected answer here is written from that rule. Grok's own files and
expectations stand in its return file, which is never edited.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_eval_cases import field_failures, make_session

from secondsignal import Action, Outcome, SessionState, extract, load_roster, route
from secondsignal.router import (
    ASK_QUESTION_OBLIGATION,
    HOUSE_ASKS,
    NO_SIGNAL_SEAT_AFTER_TURNS,
    no_signal_seat,
)
from secondsignal.signals import FRAGMENT_MAX_TOKENS, lone_fragment

ROOT = Path(__file__).resolve().parents[1]
OPENERS = ROOT / "evals" / "cases" / "vague_openers_2026-09-30.json"
TRAJECTORIES = ROOT / "evals" / "cases" / "trajectories"

# The eight openers Grok's return marked known_gap because the policy of
# 30 September seated a character on one word; under the rider each is a
# question. Grok's note on each stands in its return file.
GROK_SEATED = {
    "vague-opener-023": "staring at this",
    "vague-opener-024": "snoozed too much",
    "vague-opener-025": "can't get comfortable",
    "vague-opener-026": "no one picked up",
    "vague-opener-027": "loss for words",
    "vague-opener-028": "phone died",
    "vague-opener-029": "too much laundry",
    "vague-opener-030": "review later maybe",
}


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _openers() -> list[dict]:
    doc = json.loads(OPENERS.read_text(encoding="utf-8"))
    assert doc.get("plane", "policy") == "policy" and doc.get("kind") != "trajectory"
    return doc["cases"]


# --- the thirty openers ------------------------------------------------------------------------


def test_the_ported_file_keeps_groks_thirty_texts_and_expects_a_question_on_each() -> None:
    cases = _openers()
    assert len(cases) == 30
    for case in cases:
        assert case["expect"]["outcome"] == "UNRESOLVED"
        assert case["expect"]["agent"] is None
        assert "ask for one more sentence" in case["expect"]["reason_contains"]
        assert not case.get("known_gap"), f"{case['id']}: the rider makes the question the ruled answer"
        assert case["port_note"], f"{case['id']} carries no port note"
    assert {c["id"]: c["text"] for c in cases if c["id"] in GROK_SEATED} == GROK_SEATED


@pytest.mark.parametrize("case", _openers(), ids=[c["id"] for c in _openers()])
def test_every_opener_gets_a_question_and_sets_no_hold(case: dict, roster) -> None:
    session = make_session(case)
    decision = route(case["text"], roster, session=session)
    assert decision.outcome is Outcome.UNRESOLVED, (case["text"], decision.reason)
    assert decision.agent_id is None and decision.assist_agent_id is None
    assert decision.held == () and decision.safety.holds == (), "a vague opener never sets a hold"
    assert decision.obligations == ()
    assert decision.house_ask == "first"
    assert decision.safety.action is Action.PROCEED
    assert not field_failures(case, decision, session)


@pytest.mark.parametrize("case_id,text", sorted(GROK_SEATED.items()))
def test_the_eight_single_word_seatings_are_lone_fragments(case_id: str, text: str, roster) -> None:
    """The rider named: no seat, no hold, a question, and the record says why."""
    decision = route(text, roster, session=SessionState(locale="US", declared_age_band="adult"))
    assert decision.outcome is Outcome.UNRESOLVED and decision.agent_id is None
    assert decision.held == () and decision.safety.holds == ()
    assert "a lone fragment" in decision.reason and "ruling 5 of 3 October 2026" in decision.reason
    signals = extract(text)
    assert signals.is_empty
    assert "fragment" in signals.evidence and signals.evidence["fragment:dropped"], text


# --- the rider ----------------------------------------------------------------------------------


@pytest.mark.parametrize("text,dropped", [
    ("phone died", "domain:grief"),
    ("too much laundry", "regulation:down"),
    ("no one picked up", "domain:isolation"),
    ("loss for words", "domain:grief"),
    ("review later maybe", "regulation:up"),
    ("can't get comfortable", "mode:comfort"),
])
def test_a_lone_fragment_drops_its_weak_reading_and_records_it(text: str, dropped: str) -> None:
    signals = extract(text)
    assert signals.is_empty and not signals.domains and not signals.modes
    assert dropped in signals.evidence["fragment:dropped"]
    assert signals.evidence["fragment"][0].endswith("no first-person subject, no clear ask")
    assert signals.regulation == 0.7


@pytest.mark.parametrize("text,seat,claim,held", [
    ("my grandmother died", "willow", None, ("grief",)),   # a first-person token: not a fragment, the grief hold sets
    ("I'm lonely", "willow", None, ()),                   # the person says something about themselves
    ("relapsed again", "cody", "addiction_recovery", ()),  # a bare first-person return to use claims the seat (decision 7)
    ("Jake relapsed again", "cody", None, ("addiction_recovery",)),  # a relative's return to use is a hold (decision 7); never weak
    ("panic attack", "cody", "somatic_distress", ()),      # a seat-claiming domain is never weak
    ("abusive ex", "cody", None, ("abuse",)),             # the abuse vocabulary is never an everyday word
    ("not eating", "cody", None, ("eating_distress",)),   # nor is the eating-distress vocabulary
    ("spiraling, losing it", "cody", None, ()),           # acute dysregulation (two markers) keeps the stabilizer
    ("make it funny", "nikki", None, ()),                 # a clear ask: a mode term matched as a whole word
])
def test_strong_short_messages_still_seat(text: str, seat: str, claim: str | None, held: tuple, roster) -> None:
    decision = route(text, roster, session=SessionState(locale="US"))
    assert decision.outcome is Outcome.ROUTED and decision.agent_id == seat, (text, decision.reason)
    assert decision.seat_claim == claim
    assert decision.held == held
    assert "fragment" not in extract(text).evidence


def test_the_grief_hold_sets_on_a_sentence_and_not_on_the_fragment(roster) -> None:
    fragment = route("phone died", roster, session=SessionState(locale="US"))
    sentence = route("my phone died and then my grandmother died the same night", roster, session=SessionState(locale="US"))
    assert fragment.held == () and fragment.outcome is Outcome.UNRESOLVED
    assert "grief" in sentence.held and sentence.outcome is Outcome.ROUTED


@pytest.mark.parametrize("text", ["mom died", "grandmother died yesterday", "dad's funeral tomorrow", "cat died"])
def test_a_grief_fragment_that_names_the_person_or_animal_is_not_a_fragment(text: str, roster) -> None:
    """Integration note of 4 October 2026 on the rider: "phone died" names a
    thing and gets a question; a fragment that names who is gone has told the
    house something and gets the grief seat and hold."""
    decision = route(text, roster, session=SessionState(locale="US", declared_age_band="adult"))
    assert "grief" in decision.held and decision.outcome is Outcome.ROUTED
    assert lone_fragment(text.lower(), {"grief"}, {"domain:grief": ("died",)}, 0) is None


def test_the_fragment_rule_is_bounded_and_named() -> None:
    assert FRAGMENT_MAX_TOKENS == 4
    assert lone_fragment("phone died", {"grief"}, {"domain:grief": ("died",)}, 0) == "2 token(s), no first-person subject, no clear ask"
    assert lone_fragment("my phone died", {"grief"}, {"domain:grief": ("died",)}, 0) is None
    assert lone_fragment("the phone died again tonight", {"grief"}, {"domain:grief": ("died",)}, 0) is None
    assert lone_fragment("panic attack", {"somatic_distress"}, {}, 1) is None
    assert lone_fragment("Jake relapsed again", {"addiction_recovery"}, {"domain:addiction_recovery": ("relapsed",)}, 0) is None
    assert lone_fragment("spiraling, losing it", set(), {}, 2) is None
    assert lone_fragment("make it funny", set(), {"mode:humor": ("funny",)}, 0) is None
    assert lone_fragment("can't get comfortable", set(), {"mode:comfort": ("comfort",)}, 0) is not None


def test_the_crisis_gate_is_untouched_by_the_rider(roster) -> None:
    """A two-word crisis phrase still cards: the gate reads the raw text."""
    decision = route("kill myself", roster, session=SessionState(locale="US"))
    assert decision.safety.action is Action.HUMAN_ESCALATION and decision.preempted


# --- the second question and the third seat -----------------------------------------------------


def test_three_vague_messages_in_a_row_ask_ask_then_seat_with_a_question(roster) -> None:
    session = SessionState(locale="US")
    first = route("hey", roster, session=session)
    second = route("so yeah", roster, session=session)
    third = route("just tired", roster, session=session)
    fourth = route("whatever", roster, session=session)

    assert first.outcome is Outcome.UNRESOLVED and first.house_ask == "first"
    assert "ask for one more sentence" in first.reason

    assert second.outcome is Outcome.UNRESOLVED and second.agent_id is None
    assert second.house_ask == "second"
    assert "second, different question" in second.reason
    assert second.reason != first.reason, "the second ask is never a repeat of the first"
    assert "a second, different question is due" in second.explain()
    assert "house ask  = second" in second.explain()

    seat = no_signal_seat(roster)
    assert third.outcome is Outcome.ROUTED and third.agent_id == seat == "cody"
    assert ASK_QUESTION_OBLIGATION in third.obligations, "seated with a question attached, not a plan"
    assert "with a question attached, not a plan" in third.reason and "by role" in third.reason
    assert third.house_ask is None

    assert fourth.outcome is Outcome.ROUTED and fourth.agent_id == seat
    assert ASK_QUESTION_OBLIGATION in fourth.obligations
    assert NO_SIGNAL_SEAT_AFTER_TURNS == 3
    assert HOUSE_ASKS == ("first", "second")


def test_a_real_message_breaks_the_vague_streak(roster) -> None:
    session = SessionState(locale="US")
    route("hey", roster, session=session)
    route("so yeah", roster, session=session)
    real = route("my grandmother died last week", roster, session=session)
    assert real.outcome is Outcome.ROUTED and real.agent_id == "willow" and real.house_ask is None
    again = route("hey", roster, session=session)
    assert again.outcome is Outcome.UNRESOLVED and again.house_ask == "first"


def test_the_record_carries_the_ask_and_the_seated_turn_carries_none(roster) -> None:
    session = SessionState(locale="US")
    first = route("hey", roster, session=session).to_dict()
    second = route("so yeah", roster, session=session).to_dict()
    third = route("just tired", roster, session=session).to_dict()
    assert (first["house_ask"], second["house_ask"], third["house_ask"]) == ("first", "second", None)
    assert ASK_QUESTION_OBLIGATION in third["obligations"]
    seated = route("my grandmother died last week", roster, session=SessionState()).to_dict()
    assert seated["house_ask"] is None


def test_a_required_disclosure_on_an_empty_turn_still_seats_the_stabilizer(roster) -> None:
    """Unchanged by the ruling: a disclosure must be delivered by a persona."""
    session = SessionState(locale="US")
    route("I want to die", roster, session=session)
    grace = route("ok", roster, session=session)
    assert grace.outcome is Outcome.ROUTED and grace.agent_id == no_signal_seat(roster)
    assert grace.house_ask is None and "required disclosure" in grace.reason


# --- Grok's five trajectories, rewritten to the rule --------------------------------------------


def _vague_trajectories() -> list[Path]:
    return sorted(TRAJECTORIES.glob("grok-traj-vague-slope-00*.json"))


def test_five_vague_slope_trajectories_live_with_the_runner() -> None:
    """Ported from Grok's night-order-5 return; moved into the trajectories
    directory on 4 October 2026 with the runner's provenance block, Grok's
    expectations kept as original_expect (contract-adjusted under ruling 5)."""
    paths = _vague_trajectories()
    assert len(paths) == 5, [p.name for p in paths]
    for path in paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["kind"] == "trajectory" and doc["id"].startswith("grok-traj-vague-slope-")
        assert len(doc["turns"]) >= 4
        assert doc["turns"][0]["expect"]["outcome"] == "UNRESOLVED"
        assert doc["turns"][1]["expect"]["outcome"] == "UNRESOLVED"
        assert "second, different question" in doc["turns"][1]["expect"]["reason_contains"]
        assert "ruling 5 of 3 October 2026" in doc["port_note"]
        assert doc["original_why"].startswith("Grok, 30 September 2026:")
        assert doc["provenance"]["texts_by"] == "model"
        assert doc["provenance"]["expectations_by"] == "model"
        assert doc["provenance"]["counts_toward_recall"] is False
        assert doc["contract_adjusted"] is True
        assert "original_expect" in doc["turns"][1]


@pytest.mark.parametrize("path", _vague_trajectories(), ids=[p.stem for p in _vague_trajectories()])
def test_each_vague_trajectory_replays_as_written(path: Path, roster) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    session = SessionState(locale=doc.get("locale"), declared_age_band=doc["session"].get("declared_age_band", "unknown"))
    escalated: list[int] = []
    cards = 0
    for turn in doc["turns"]:
        decision = route(turn["text"], roster, session=session)
        expect = dict(turn.get("expect", {}))
        aftermath = expect.pop("aftermath", None)
        bad = field_failures({"expect": expect}, decision, session)
        assert not bad, f"{path.name} turn {turn['n']}: {bad}"
        if aftermath is not None:
            assert session.aftermath_turns == aftermath, f"{path.name} turn {turn['n']}: aftermath {session.aftermath_turns}"
        if decision.safety.action is Action.HUMAN_ESCALATION:
            escalated.append(turn["n"])
        cards += bool(decision.safety.card)
        assert "id order" not in decision.reason
    texp = doc["trajectory_expect"]
    assert escalated == texp["escalation_turns"] and escalated[0] == texp["first_escalation_turn"]
    assert cards == texp["cards_total"]


def test_the_fifth_trajectory_reaches_the_third_message_seat(roster) -> None:
    doc = json.loads((TRAJECTORIES / "grok-traj-vague-slope-005.json").read_text(encoding="utf-8"))
    session = SessionState(locale="US", declared_age_band="adult")
    decisions = [route(turn["text"], roster, session=session) for turn in doc["turns"]]
    assert [d.house_ask for d in decisions[:2]] == ["first", "second"]
    third = decisions[2]
    assert third.agent_id == no_signal_seat(roster) and ASK_QUESTION_OBLIGATION in third.obligations
    assert third.held == (), "the lone fragment 'no one picked up' sets no hold"
