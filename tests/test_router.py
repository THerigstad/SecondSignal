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


# --- an exhaustive tie seats nobody (ruling 17 of 3 October 2026; ADR-0013) --------------------

import dataclasses  # noqa: E402

from evals.measure_id_order_fallback import measure  # noqa: E402
from secondsignal.profiles import AgentProfile, find_stabilizers  # noqa: E402
from secondsignal.router import EXHAUSTIVE_TIE, Outcome  # noqa: E402


def test_a_constructed_exhaustive_tie_seats_nobody():
    """Two candidates identical in every rule the selector knows: the same
    score, the same focus, the same floor. Until 4 October 2026 the first id
    won; now nobody does, and the reason names the tie."""
    alpha = AgentProfile(id="alpha", display_name="A", one_line="", domains=frozenset({"grief"}),
                         modes=frozenset({"comfort"}), regulation_window=(0.0, 1.0))
    beta = dataclasses.replace(alpha, id="beta")
    decision = route("my grandmother died last week", {"alpha": alpha, "beta": beta})
    assert decision.outcome is Outcome.UNRESOLVED and decision.agent_id is None
    assert decision.assist_agent_id is None
    assert EXHAUSTIVE_TIE in decision.reason and "alpha, beta" in decision.reason
    assert "ADR-0013" in decision.reason and "ruling 17 of 3 October 2026" in decision.reason
    assert "id order" not in decision.reason
    assert decision.house_ask == "first"
    assert decision.held == ("grief",), "the hold is still recorded for whoever answers next"
    assert "UNRESOLVED (no agent seated; ask for one more sentence)" in decision.explain()
    # Reversing the roster's insertion order changes nothing.
    reversed_roster = route("my grandmother died last week", {"beta": beta, "alpha": alpha})
    assert reversed_roster.agent_id is None and reversed_roster.reason == decision.reason


def test_a_tie_the_rules_can_break_is_still_broken_and_named():
    alpha = AgentProfile(id="alpha", display_name="A", one_line="", domains=frozenset({"grief"}),
                         modes=frozenset({"comfort"}), regulation_window=(0.0, 1.0))
    beta = dataclasses.replace(alpha, id="beta", regulation_window=(0.3, 1.0))
    decision = route("my grandmother died last week", {"alpha": alpha, "beta": beta})
    assert decision.agent_id == "alpha" and "wider safe window" in decision.reason


def test_no_labelled_case_or_trajectory_turn_reaches_the_exhaustive_tie():
    """The measurement ruling 17 asked for, kept as a test: the count the
    script prints is zero on this tree, so the branch could come out."""
    result = measure()
    assert result["cases"] >= 517 and result["trajectory_turns"] >= 9
    assert result["reached"] == [], result["reached"]


def test_find_stabilizers_is_sorted_whatever_the_roster_order(roster):
    """Codex's job 3 pinned this in tests/test_order3_runtime.py; confirmed
    here beside the tie rule it protects (find_stabilizers(roster)[0] is a
    sorted role, not load order)."""
    assert find_stabilizers(roster) == sorted(find_stabilizers(roster))
    shuffled = {pid: roster[pid] for pid in reversed(sorted(roster))}
    assert find_stabilizers(shuffled) == find_stabilizers(roster)
