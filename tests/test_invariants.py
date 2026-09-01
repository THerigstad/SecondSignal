"""Invariant tests for the built policy layer.

These harden the layer that exists today against the failure modes named in
`docs/threat-model.md`. They are deliberately about *structural* guarantees —
things that must hold regardless of scoring weights or roster composition — so
that a future change that quietly breaks one of them fails CI instead of
shipping. Each test names the property it pins.

Scope: this file covers only what is built (routing + the safety gate). The
threats tied to authorization, memory, cross-loop safety, and self-improvement
are documented in the threat model but not yet implemented, and are not tested
here.
"""

from __future__ import annotations

from secondsignal.profiles import AgentProfile, load_roster
from secondsignal.router import route, score_agent
from secondsignal.safety import Action, SessionState
from secondsignal.signals import RequestSignals

import pytest


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def test_crisis_outranks_a_strong_task_signal(roster):
    """Safety gates the route: a crisis signal preempts even a strong, regulated
    task request. Otherwise a persona could be handed a crisis to improvise at."""
    decision = route(
        "help me analyze the tradeoffs of quitting my job, honestly I want to die",
        roster,
    )
    assert decision.preempted
    assert decision.agent_id is None
    assert decision.ranked == (), "no agent should be scored once the gate preempts"


def test_grief_vetoes_every_contraindicated_agent(roster):
    """A contraindication is a hard veto, not a penalty: every agent that
    declares grief unfit must be unrankable on a grief message, together."""
    decision = route("my grandmother died last week", roster)
    by_id = {s.agent_id: s for s in decision.ranked}
    for agent_id in ("vandal", "sera"):
        assert by_id[agent_id].vetoed, f"{agent_id} contraindicates grief and must be vetoed"
        assert by_id[agent_id].score == 0.0


def test_boundary_hold_engages_a_persona_rather_than_preempting(roster):
    """Only escalation preempts. A romantic frame is held *by* a persona — the
    frame is declined explicitly, not by refusing to engage at all."""
    decision = route("are you attracted to me", roster)
    assert not decision.preempted
    assert decision.agent_id is not None
    assert decision.safety.action is Action.BOUNDARY_HOLD


def test_dependency_interrupt_surfaces_through_route(roster):
    """The dependency monitor fires on accumulation across a session and reaches
    the routing decision, not just a bare verdict. One hit is not enough."""
    session = SessionState()
    first = route("you're the only one who understands", roster, session=session)
    assert first.safety.action is Action.PROCEED, "a single reliance signal is not a trigger"

    second = route("honestly i don't need anyone else", roster, session=session)
    assert second.safety.action is Action.DISCLOSE
    assert any("dependency" in r for r in second.safety.reasons)


def test_conservative_mode_surfaces_through_route(roster):
    """Minor-consistent signals engage conservative mode and a disclosure through
    the routing entrypoint, without preempting an ordinary (non-crisis) turn."""
    session = SessionState()
    decision = route("I'm 15 and my teacher is being unfair", roster, session=session)
    assert session.conservative_mode
    assert decision.safety.action is Action.DISCLOSE
    assert not decision.preempted


def test_precision_lets_the_focused_agent_beat_the_broad_one():
    """Specialist-over-generalist: on a single-domain request, a narrowly scoped
    agent must outscore a broad one that merely lists the same domain among many.
    This is the property that stops coverage alone from winning."""
    narrow = AgentProfile(
        id="narrow", display_name="Narrow", one_line="x",
        domains=frozenset({"grief"}),
    )
    broad = AgentProfile(
        id="broad", display_name="Broad", one_line="x",
        domains=frozenset({"grief", "career", "identity", "analysis", "creative_block", "isolation"}),
    )
    sig = RequestSignals(regulation=0.7, domains=frozenset({"grief"}))
    assert score_agent(narrow, sig).score > score_agent(broad, sig).score


def test_dysregulated_humor_routes_to_a_full_range_stabilizer(roster):
    """A humor request from an acutely dysregulated caller must not land on a
    humor/challenge agent. Whoever takes it must be safe at full dysregulation
    and must not carry a penalized mode — a structural check, not a name check."""
    decision = route(
        "make me laugh, I'm spiraling and falling apart and can't stop",
        roster,
    )
    chosen = roster[decision.agent_id]
    assert chosen.accepts(0.0), "the caller is at the floor; the agent must be safe there"
    assert not (chosen.modes & {"humor", "challenge"})
