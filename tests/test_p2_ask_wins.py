"""Order P2V1: a declared ask wins only inside eligibility and carried competence."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest
from test_eval_cases import CASES

import secondsignal.router as router_module
from secondsignal import SessionState, load_roster, route
from secondsignal.profiles import AgentProfile
from secondsignal.router import EXHAUSTIVE_TIE, Outcome
from secondsignal.signals import RequestSignals


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _case(case_id):
    return next(case for _, case in CASES if case["id"] == case_id)


def _candidate(decision, agent_id):
    return next(row for row in decision.ranked if row.agent_id == agent_id)


def test_eligible_ask_carrying_topic_beats_a_higher_score(roster):
    text = _case("grief-plain")["text"]
    baseline = route(text, roster)
    decision = route(text, roster, asked="rowan")
    assert baseline.agent_id == "willow"
    assert _candidate(baseline, "willow").score > _candidate(baseline, "rowan").score
    assert decision.agent_id == "rowan" and decision.ask_outcome == "honoured"
    assert decision.reason == (
        "declared ask honoured: rowan (eligible; carries grief); hold on grief carried by the seat"
    )
    assert decision.ranked == baseline.ranked
    assert "acknowledge:grief" in decision.obligations
    assert decision.to_dict()["ask_outcome"] == "honoured"
    assert "asked      = rowan (declared by a control; honoured)" in decision.explain()


def test_regulation_only_ask_wins_with_nothing_to_route(roster):
    baseline = route("I am overwhelmed.", roster)
    decision = route("I am overwhelmed.", roster, asked="rowan")
    assert not baseline.signals.is_empty
    assert not baseline.signals.domains and not baseline.signals.modes
    assert baseline.agent_id == "cody"
    assert decision.agent_id == "rowan" and decision.ask_outcome == "honoured"
    assert decision.reason == "declared ask honoured: rowan (eligible; nothing to route)"
    assert decision.ranked == baseline.ranked


@pytest.mark.parametrize("asked", ("cody", "ellis", "nikki", "rowan", "seren", "vandal", "willow"))
def test_fully_empty_asks_seat_and_keep_vague_observation(roster, asked, monkeypatch):
    examined = []
    original_eligible = router_module.eligible

    def track_eligibility(profile, *args, **kwargs):
        examined.append(profile.id)
        return original_eligible(profile, *args, **kwargs)

    monkeypatch.setattr(router_module, "eligible", track_eligibility)
    baseline_session, session = SessionState(), SessionState()
    for turn in range(1, 4):
        baseline = route("hello", roster, session=baseline_session)
        examined.clear()
        decision = route("hello", roster, session=session, asked=asked)
        assert examined == [asked], "a fully empty declaration evaluates only its named character"
        assert baseline.signals.is_empty and decision.signals == baseline.signals
        assert decision.agent_id == asked and decision.ask_outcome == "honoured"
        assert decision.outcome is Outcome.ROUTED and decision.house_ask is None
        assert decision.reason == f"declared ask honoured: {asked} (eligible; nothing to route)"
        assert len(decision.ranked) == 1
        assert decision.ranked[0].agent_id == asked and decision.ranked[0].status == "scored"
        assert decision.ranked[0].score == 0.0 and decision.ranked[0].rationale == ()
        assert session.__dict__ == baseline_session.__dict__ and session.empty_streak == turn
        assert baseline.agent_id == ("cody" if turn == 3 else None)
        assert baseline.house_ask == ({1: "first", 2: "second"}.get(turn))
        assert all(row.status == "no_signal" for row in baseline.ranked)


def test_seat_claim_refuses_an_ask_and_names_the_claim(roster):
    text = "I am shaking."
    baseline = route(text, roster)
    decision = route(text, roster, asked="rowan")
    assert decision.agent_id == baseline.agent_id == "cody"
    assert decision.ask_outcome == "not_seated"
    assert _candidate(decision, "rowan").status == "outranked"
    assert decision.reason == baseline.reason + (
        "; asked rowan not seated: outranked: seat-claiming domain 'somatic_distress' present; "
        "agent does not carry it"
    )


def test_carried_hold_refuses_contraindicated_ask_with_kind(roster):
    session = SessionState()
    route(_case("grief-plain")["text"], roster, session=session)
    baseline_session = copy.deepcopy(session)
    baseline = route("I need help with my career.", roster, session=baseline_session)
    decision = route("I need help with my career.", roster, session=session, asked="vandal")
    assert "grief" not in decision.signals.domains and "grief" in decision.held
    assert decision.agent_id == baseline.agent_id and decision.agent_id != "vandal"
    assert decision.ask_outcome == "not_seated"
    assert _candidate(decision, "vandal").status == "vetoed"
    refusal = "vetoed: contraindicated for: grief (safety) (cannot honor hold: grief)"
    assert f"; asked vandal not seated: {refusal}" in decision.reason
    assert f"asked      = vandal (declared by a control; not seated: {refusal})" in decision.explain()
    assert "acknowledge:grief" in decision.obligations and "no_joke" in decision.obligations
    assert session.__dict__ == baseline_session.__dict__


def test_empty_ask_carries_hold_obligations_without_changing_observation(roster):
    session = SessionState()
    route(_case("grief-plain")["text"], roster, session=session)
    baseline_session = copy.deepcopy(session)
    baseline = route("hello", roster, session=baseline_session)
    decision = route("hello", roster, session=session, asked="rowan")
    assert baseline.agent_id is None and baseline.house_ask == "first"
    assert decision.agent_id == "rowan" and decision.ask_outcome == "honoured"
    assert decision.house_ask is None and len(decision.ranked) == 1
    assert decision.ranked[0].agent_id == "rowan" and decision.ranked[0].status == "scored"
    assert "acknowledge:grief" in decision.obligations and "no_joke" in decision.obligations
    assert decision.held == ("grief",)
    assert decision.reason.endswith("; hold on grief carried by the seat")
    assert session.active_holds == ("grief",) and session.__dict__ == baseline_session.__dict__


@pytest.mark.parametrize("prior, expected_status, why", [
    ("grief-plain", "vetoed", "contraindicated for: grief (safety) (cannot honor hold: grief)"),
    (None, "capped", "every offered mode is vetoed this turn (challenge, humor)"),
])
def test_empty_refused_ask_keeps_existing_no_signal_path(roster, prior, expected_status, why):
    session = SessionState()
    prior_text = _case(prior)["text"] if prior else "I am being abused at home."
    route(prior_text, roster, session=session)
    baseline_session = copy.deepcopy(session)
    for _ in range(3):
        baseline = route("hello", roster, session=baseline_session)
        decision = route("hello", roster, session=session, asked="vandal")
        assert decision.signals.is_empty and decision.ask_outcome == "not_seated"
        assert decision.agent_id == baseline.agent_id and decision.house_ask == baseline.house_ask
        assert decision.outcome == baseline.outcome and decision.obligations == baseline.obligations
        assert len(decision.ranked) == 1 and decision.ranked[0].agent_id == "vandal"
        assert decision.ranked[0].status == expected_status
        assert decision.reason == baseline.reason + f"; asked vandal not seated: {expected_status}: {why}"
        assert session.__dict__ == baseline_session.__dict__


@pytest.mark.parametrize("empty", [False, True])
def test_regulation_floor_refuses_even_a_nothing_to_route_ask(roster, empty):
    signals = RequestSignals(regulation=0.1, evidence={} if empty else {"regulation:low": ("overwhelmed",)})
    baseline = route("hello", roster, signals=signals)
    decision = route("hello", roster, signals=signals, asked="vandal")
    assert signals.is_empty == empty
    assert decision.agent_id == baseline.agent_id and decision.house_ask == baseline.house_ask
    assert decision.ask_outcome == "not_seated"
    assert _candidate(decision, "vandal").status == "below_floor"
    assert decision.reason == baseline.reason + (
        "; asked vandal not seated: below_floor: below regulation floor 0.55: caller at 0.1"
    )


def test_eligible_character_without_carried_topic_is_refused(roster):
    baseline = route("I need to compare these options.", roster)
    decision = route("I need to compare these options.", roster, asked="rowan")
    assert _candidate(decision, "rowan").status == "scored"
    assert decision.agent_id == baseline.agent_id == "seren" and decision.ask_outcome == "not_seated"
    assert decision.reason == baseline.reason + "; asked rowan not seated: does not carry analysis"


def test_ask_for_existing_winner_changes_only_declaration_and_outcome(roster):
    text = _case("grief-plain")["text"]
    baseline = route(text, roster)
    decision = route(text, roster, asked=baseline.agent_id)
    assert decision.ask_outcome == "honoured" and decision.agent_id == "willow"
    assert replace(decision, asked_agent_id=None, ask_outcome=None) == baseline


def test_exhaustive_tie_is_resolved_only_by_a_competent_ask():
    alpha = AgentProfile(id="alpha", display_name="A", one_line="", domains=frozenset({"grief"}),
                         modes=frozenset({"comfort"}), regulation_window=(0.0, 1.0))
    beta = replace(alpha, id="beta")
    gamma = replace(alpha, id="gamma", domains=frozenset({"identity"}))
    roster = {profile.id: profile for profile in (alpha, beta, gamma)}
    text = _case("grief-plain")["text"]
    baseline = route(text, roster)
    assert baseline.agent_id is None and EXHAUSTIVE_TIE in baseline.reason
    for asked in ("alpha", "beta"):
        decision = route(text, roster, asked=asked)
        assert decision.agent_id == asked and decision.ask_outcome == "honoured"
        assert decision.reason == (
            f"declared ask honoured: {asked} (resolved an exhaustive tie); hold on grief carried by the seat"
        )
        assert decision.outcome is Outcome.ROUTED and decision.house_ask is None
        assert "acknowledge:grief" in decision.obligations
    refused = route(text, roster, asked="gamma")
    assert refused.agent_id is None and refused.outcome is baseline.outcome
    assert refused.house_ask == baseline.house_ask and refused.ask_outcome == "not_seated"
    assert refused.reason == baseline.reason + "; asked gamma not seated: does not carry grief"


def test_existing_card_fixture_ignores_all_seven_declared_asks(roster):
    text = _case("crisis-direct")["text"]
    baseline = route(text, roster)
    assert baseline.preempted and baseline.agent_id is None
    for asked in roster:
        decision = route(text, roster, asked=asked)
        assert decision.ask_outcome == "not_seated"
        assert replace(decision, asked_agent_id=None, ask_outcome=None) == baseline
        assert decision.ranked == () and decision.reason == "safety gate holds the floor"


def test_known_alias_honours_the_canonical_seat(roster):
    text = _case("grief-plain")["text"]
    baseline = route(text, roster)
    decision = route(text, roster, asked="ravi")
    assert baseline.agent_id == "willow"
    assert decision.asked_agent_id == decision.agent_id == "rowan" and decision.ask_outcome == "honoured"
    assert decision == route(text, roster, asked="rowan")
    assert "declared ask honoured: rowan (eligible; carries grief)" in decision.reason
