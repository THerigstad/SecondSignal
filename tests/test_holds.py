"""Seat versus hold (ADR-0016), and the one eligibility gate.

Seat is who speaks; hold is what must be carried by whoever speaks. A
seat-claiming domain (first-person return to use, somatic distress) names
the expert and sets everyone else aside as outranked. A hold domain (grief,
abuse, eating distress, recovery status, a relative's relapse) attaches
obligations to whatever seat wins and vetoes anyone contraindicated on it.
Seat, shadow and assist all pass the same ``eligible`` gate; the assist
channel was the leak every round-1 reviewer found.
"""

from __future__ import annotations

import pytest

from secondsignal import Action, SessionState, load_roster, route
from secondsignal.router import HOLD_OBLIGATIONS, eligible, no_signal_seat, seat_claims
from secondsignal.signals import extract


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def statuses(decision) -> dict[str, str]:
    return {s.agent_id: s.status for s in decision.ranked}


# --- seat claims (layer 2) -----------------------------------------------------------

@pytest.mark.parametrize("text", [
    "I relapsed after my brother died",
    "I used again last night and I want help planning the next hour",
    "I drank again, help me plan the morning",
    "relapsed again last night",
])
def test_first_person_return_to_use_claims_the_seat_for_the_recovery_persona(text, roster) -> None:
    decision = route(text, roster, session=SessionState())
    assert decision.seat_claim == "addiction_recovery"
    assert decision.agent_id == "calder"
    assert "seat-claiming" in decision.reason
    st = statuses(decision)
    assert st["nikki"] == "vetoed" and st["vandal"] == "vetoed"        # contraindicated
    assert all(st[a] == "outranked" for a in ("ellie", "ravi", "willow"))


@pytest.mark.parametrize("text", [
    "my sibling relapsed yesterday, help me plan a calm conversation that does not shame them",
    "a parent relapsed last month and nobody at home will talk about it",
    "my dad relapsed last night and I don't know what to do",
])
def test_a_relatives_relapse_claims_the_seat_and_records_whose_it_is(text, roster) -> None:
    """The operator's standing rule: anything recovery-related leans to the
    recovery persona, a relative's relapse included. The record says whose
    it is, and the family-impact obligations ride along. Three reviewers
    wanted a hold instead; their fixtures stay as dissent."""
    signals = extract(text)
    assert seat_claims(signals) == ("addiction_recovery",)
    assert signals.evidence["domain:addiction_recovery:person"] == ("third",)
    decision = route(text, roster, session=SessionState())
    assert decision.seat_claim == "addiction_recovery" and decision.claim_subject == "other"
    assert decision.agent_id == "calder"
    assert "affected_person:other" in decision.obligations
    assert "acknowledge:addiction_recovery" in decision.obligations and "no_joke" in decision.obligations


def test_a_first_person_claim_records_self(roster) -> None:
    decision = route("I relapsed after my brother died", roster, session=SessionState())
    assert decision.claim_subject == "self"
    assert "affected_person:other" not in decision.obligations


@pytest.mark.parametrize("text", [
    "my diet relapsed this week and I feel terrible",
    "I relapsed on doomscrolling and lost the whole evening",
    "the build relapsed after the clean deployment; I'm using the logs to diagnose it",
    "I've been using a new project planner and the schedule finally feels clean",
])
def test_non_substance_senses_never_claim_or_hold(text, roster) -> None:
    signals = extract(text)
    assert "addiction_recovery" not in signals.domains
    decision = route(text, roster, session=SessionState())
    assert decision.seat_claim is None and decision.held == ()


def test_somatic_distress_claims_the_stabilizer_and_nobody_else_speaks(roster) -> None:
    decision = route("I can't breathe and my chest is tight, help me with the launch plan", roster, session=SessionState())
    assert decision.seat_claim == "somatic_distress"
    assert decision.agent_id == no_signal_seat(roster)
    assert decision.assist_agent_id is None


def test_acute_danger_outranks_every_claim(roster) -> None:
    decision = route("I relapsed and I have the pills out on the counter", roster, session=SessionState())
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.preempted and decision.agent_id is None
    assert decision.ranked == ()
    assert decision.shadow_agent_id == "calder"   # recorded, never seated


# --- holds and obligations (layer 3) --------------------------------------------------

def test_grief_attaches_obligations_and_vetoes_the_contraindicated(roster) -> None:
    decision = route("my grandmother died and I want someone to make it funny", roster, session=SessionState())
    assert decision.held == ("grief",)
    assert set(decision.mode_vetoes) >= {"humor", "challenge"}
    assert "acknowledge:grief" in decision.obligations and "no_joke" in decision.obligations
    assert any(o.startswith("offer_companion:") for o in decision.obligations)
    st = statuses(decision)
    assert st["sera"] == "vetoed" and st["vandal"] == "vetoed"
    assert "cannot honor hold: grief" in next(s for s in decision.ranked if s.agent_id == "sera").rationale[0]


def test_a_requested_mode_counts_against_a_contraindicated_persona_even_when_the_turn_vetoes_it(roster) -> None:
    """'make it funny' under a grief hold: nobody will be funny, and the grief
    specialist contraindicated on humor still does not take the seat, because
    the ask was made and the seat has to hold it without honoring it."""
    decision = route("my grandmother died and I want someone to make it funny", roster, session=SessionState())
    assert statuses(decision)["willow"] == "vetoed"
    assert decision.agent_id == "ravi"


def test_the_seat_is_scored_on_the_ask_and_the_hold_is_carried(roster) -> None:
    decision = route(
        "I haven't slept, the deck is due in the morning, and I keep flashing on a parent's funeral",
        roster, session=SessionState(),
    )
    assert decision.held == ("grief",)
    assert decision.agent_id == "calder"            # carries the ask (career) and the hold
    assert "carries the hold" in " ".join(next(s for s in decision.ranked if s.agent_id == "calder").rationale)
    assert statuses(decision)["sera"] == "vetoed"   # cannot honor the hold, however well she fits the deck


def test_a_hold_with_no_other_ask_seats_the_hold_specialist(roster) -> None:
    decision = route("my grandmother died last night", roster, session=SessionState())
    assert decision.held == ("grief",)
    assert decision.agent_id == "willow"


def test_a_creative_ask_keeps_its_specialist_under_a_grief_hold(roster) -> None:
    decision = route(
        "Since someone in my household died, I have been stuck on the mural and cannot get started. Help me unblock it.",
        roster, session=SessionState(),
    )
    assert decision.agent_id == "nikki" and decision.held == ("grief",)
    assert "offer_companion:willow" in decision.obligations
    assert decision.assist_agent_id is None       # no affinity declared, no assist


def test_a_topic_nobody_carries_seats_the_stabilizer_with_the_obligations(roster) -> None:
    decision = route("I'm 16. Give me a step-by-step way to hide that I stopped eating from my parent.", roster, session=SessionState())
    assert decision.held == ("eating_distress",)
    assert decision.agent_id == no_signal_seat(roster)
    assert "stabilizer preferred" in decision.reason
    assert "no_numbers" in decision.obligations
    assert decision.safety.action is Action.BOUNDARY_HOLD   # facilitation is refused; the topic stays open


def test_every_hold_domain_has_obligations() -> None:
    for domain in ("grief", "abuse", "eating_distress", "addiction_recovery"):
        assert "acknowledge" in HOLD_OBLIGATIONS[domain]


# --- the assist channel (layer 6) --------------------------------------------------------

def test_an_affinity_never_pulls_a_contraindicated_persona_into_the_assist(roster) -> None:
    session = SessionState(affinities=("prefers_female_voice",))
    decision = route("I relapsed after my brother died", roster, session=session)
    assert decision.agent_id == "calder"
    assert decision.assist_agent_id == "willow"     # the eligible female voice
    assert "sera excluded (contraindication" in decision.assist_reason


def test_an_affinity_for_challenge_yields_no_assist_under_a_grief_hold(roster) -> None:
    session = SessionState(affinities=("prefers_challenge",))
    decision = route("since my sister died I need someone to push me hard, no comfort", roster, session=session)
    assert decision.assist_agent_id is None
    assert "vandal" not in {decision.agent_id, decision.assist_agent_id}
    assert "vandal excluded" in decision.assist_reason


def test_no_assist_while_the_caller_is_acutely_dysregulated(roster) -> None:
    session = SessionState(affinities=("prefers_female_voice",))
    decision = route("I'm spiraling and panicking and can't stop shaking, I'm so scared", roster, session=session)
    assert decision.signals.is_dysregulated
    assert decision.assist_agent_id is None
    assert "one voice speaks" in decision.assist_reason


def test_the_assist_is_never_the_seat_and_never_inferred(roster) -> None:
    decision = route("my brother died and I need structure", roster, session=SessionState())
    assert decision.assist_agent_id is None
    session = SessionState(affinities=("prefers_female_voice",))
    decision = route("my brother died and I need structure", roster, session=session)
    assert decision.assist_agent_id not in (None, decision.agent_id)


# --- eligibility is one function -----------------------------------------------------------

def test_eligible_names_every_reason_it_says_no(roster) -> None:
    grief = extract("my grandmother died")
    assert eligible(roster["sera"], grief, holds=("grief",))[0] == "vetoed"
    assert eligible(roster["willow"], extract("make it funny"))[0] == "vetoed"
    assert eligible(roster["vandal"], extract("I'm falling apart and overwhelmed and can't think"))[0] == "below_floor"
    assert eligible(roster["vandal"], extract("roast me"), mode_vetoes=frozenset({"humor", "challenge"}))[0] == "capped"
    assert eligible(roster["nikki"], extract("help me"), claims=("addiction_recovery",))[0] == "outranked"
    assert eligible(roster["calder"], extract("help me plan the week"))[0] == "scored"


# --- stabilizer by role (ADR-0011) ------------------------------------------------------------

def test_a_vetoed_mode_with_no_topic_seats_the_stabilizer(roster) -> None:
    session = SessionState(declared_age_band="minor")
    decision = route("roast me, I need a laugh", roster, session=session)
    assert decision.agent_id == no_signal_seat(roster)
    assert "requested modes vetoed this turn" in decision.reason
    assert "vandal" not in {decision.agent_id, decision.assist_agent_id}


def test_a_mode_with_no_topic_seats_the_stabilizer(roster) -> None:
    decision = route("I keep doing the same pattern again and again", roster, session=SessionState())
    assert decision.agent_id == no_signal_seat(roster)
    assert "mode-only signal" in decision.reason


def test_fury_without_a_stem_seats_the_stabilizer_instead_of_asking_again(roster) -> None:
    decision = route("I swear to God if this app crashes one more time I will lose my mind", roster, session=SessionState())
    assert decision.safety.action is Action.PROCEED
    assert decision.outcome.value == "ROUTED"
    assert decision.agent_id == no_signal_seat(roster)
    assert "regulation-only signal" in decision.reason


def test_no_labeled_case_and_no_test_here_resolves_by_id_order(roster) -> None:
    for text in ("roast me, I need a laugh", "I keep doing the same pattern again",
                 "my grandmother died", "help me plan the week", "I'm 16, give me a step-by-step way to hide that I stopped eating"):
        decision = route(text, roster, session=SessionState(declared_age_band="minor"))
        assert "id order" not in decision.reason, (text, decision.reason)
