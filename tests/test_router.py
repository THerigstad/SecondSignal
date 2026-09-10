"""Tests for the routing policy.

Each test corresponds to a claim the README makes. If a claim cannot be
asserted here, it should not be in the README.
"""

from __future__ import annotations

import pytest

from secondsignal.profiles import load_roster
from secondsignal.router import route, score_agent
from secondsignal.safety import SessionState
from secondsignal.signals import extract


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def test_routing_is_deterministic(roster):
    text = "I'm blocked on this painting and I can't start"
    first = route(text, roster)
    second = route(text, roster)
    assert first.agent_id == second.agent_id
    assert [s.score for s in first.ranked] == [s.score for s in second.ranked]


def test_safety_preemption_selects_no_agent(roster):
    decision = route("I want to die", roster)
    assert decision.preempted
    assert decision.agent_id is None
    assert decision.ranked == (), "no agent should even be scored after preemption"


def test_contraindication_is_a_hard_veto_not_a_penalty(roster):
    """Vandal vetoes grief. He must be unrankable there, not merely unlikely."""
    decision = route("my grandmother died last week", roster)
    vandal = next(s for s in decision.ranked if s.agent_id == "vandal")
    assert vandal.vetoed
    assert vandal.score == 0.0
    assert decision.agent_id != "vandal"


def test_grief_routes_to_the_grief_agent(roster):
    decision = route("my grandmother died and I keep expecting to see her", roster)
    assert decision.agent_id == "willow"


def test_somatic_distress_routes_to_the_stabilizer(roster):
    decision = route("I'm panicking, chest tight, I can't breathe", roster)
    assert decision.agent_id == "cody"


def test_analysis_routes_to_the_analyst_when_regulated(roster):
    decision = route(
        "let's plan this out, I want to compare the tradeoffs and evaluate the options",
        roster,
    )
    assert decision.agent_id == "seren"


def test_challenge_agents_are_penalized_during_dysregulation(roster):
    """The same request scores differently depending on the caller's state."""
    calm = extract("roast me about this creative block")
    spiraling = extract("roast me, I'm spiraling and falling apart and can't stop")

    calm_score = score_agent(roster["vandal"], calm).score
    spiraling_score = score_agent(roster["vandal"], spiraling).score
    assert spiraling_score < calm_score


def test_dysregulated_humor_request_does_not_route_to_disruption(roster):
    decision = route(
        "make me laugh, I'm spiraling and falling apart and can't stop",
        roster,
    )
    assert decision.agent_id != "vandal"


def test_handoff_hints_are_emitted_for_out_of_scope_domains(roster):
    decision = route(
        "I'm stuck on this painting and also grieving my grandmother",
        roster,
    )
    conditions = {condition for condition, _ in decision.handoff_hints}
    assert conditions, "a mixed-domain request should surface at least one handoff"


def test_decision_explains_itself(roster):
    decision = route("I'm blocked creatively and it's making me feel alone", roster)
    trace = decision.explain()
    assert "regulation" in trace
    assert decision.agent_id in trace
    assert "domain fit" in trace


def test_every_scored_agent_carries_a_rationale(roster):
    decision = route("I need help organizing my job search", roster)
    for scored in decision.ranked:
        assert scored.rationale, f"{scored.agent_id} scored without explanation"


def test_session_state_advances_across_turns(roster):
    session = SessionState()
    route("first turn", roster, session=session)
    route("second turn", roster, session=session)
    assert session.turn_count == 2


def test_empty_roster_is_rejected():
    with pytest.raises(ValueError, match="roster is empty"):
        route("anything", {})


def test_injected_signals_bypass_the_default_extractor(roster):
    """The policy layer must be usable with a different signal source."""
    custom = extract("my grandmother died")
    decision = route("unrelated text", roster, signals=custom)
    assert decision.agent_id == "willow"
