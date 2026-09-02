"""Run every labeled case under ``evals/cases/`` through the real pipeline.

Cases were documentation until the external review (2026-09-01) showed that a
suite can pass on the winner alone: four cases landed on the right agent by
alphabetical accident. Every case now carries what it expects and *why*:

* ``expect.safety``          the safety action name
* ``expect.outcome``         ROUTED | PREEMPTED | UNRESOLVED
* ``expect.agent``           exact agent id, or null when no persona may engage
* ``expect.agent_any_of``    accepted ids when the gold is a documented disagreement
* ``expect.reason_contains`` a substring the decision's reason must carry
* ``expect.ineligible``      ids that must not be seated and, if in the roster,
                             must appear vetoed or below their floor in the trace
* ``expect.crisis_read``     HIT | MISS | INCONCLUSIVE
* ``expect.integrity_event`` whether an override attempt was recorded

A case marked ``known_gap`` is a documented failure the reference lexicon is
not expected to pass. It is run as a strict expected failure: if it starts
passing, the run fails so the marker gets removed rather than forgotten.
Deleting a failing case to make the suite green is not an option this runner
offers.

Schema version 1 cases (``text``, ``expect.safety``, ``expect.agent``, ``why``)
are still accepted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from secondsignal import Action, Outcome, SessionState, load_roster, route

CASE_DIR = Path(__file__).resolve().parents[1] / "evals" / "cases"


def _load_cases() -> list[tuple[str, dict]]:
    cases: list[tuple[str, dict]] = []
    for path in sorted(CASE_DIR.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("plane", "policy") != "policy":
            continue
        for case in doc["cases"]:
            cases.append((f"{path.stem}::{case['id']}", case))
    return cases


CASES = _load_cases()


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _run(case: dict, roster):
    session = SessionState(locale=case.get("locale"))
    for prior in case.get("prior_turns", []):
        route(prior, roster, session=session)
    return route(case["text"], roster, session=session)


def _check(case: dict, decision) -> None:
    expect = case["expect"]

    assert decision.safety.action is Action[expect["safety"]], (
        f"safety: expected {expect['safety']}, got {decision.safety.action.name}; "
        f"reasons={decision.safety.reasons}"
    )
    if "outcome" in expect:
        assert decision.outcome is Outcome[expect["outcome"]], (
            f"outcome: expected {expect['outcome']}, got {decision.outcome.value} ({decision.reason})"
        )
    if "agent" in expect:
        assert decision.agent_id == expect["agent"], (
            f"agent: expected {expect['agent']!r}, got {decision.agent_id!r}; reason={decision.reason!r}; "
            f"ranked={[(s.agent_id, s.status, s.score) for s in decision.ranked]}"
        )
    if "agent_any_of" in expect:
        assert decision.agent_id in expect["agent_any_of"], (
            f"agent: expected one of {expect['agent_any_of']}, got {decision.agent_id!r}; reason={decision.reason!r}"
        )
    if "reason_contains" in expect:
        assert expect["reason_contains"] in decision.reason, (
            f"reason: expected to contain {expect['reason_contains']!r}, got {decision.reason!r}"
        )
    if "crisis_read" in expect:
        assert decision.safety.crisis_read == expect["crisis_read"], (
            f"crisis_read: expected {expect['crisis_read']}, got {decision.safety.crisis_read}"
        )
    if "integrity_event" in expect:
        assert decision.safety.integrity_event is expect["integrity_event"]
    statuses = {s.agent_id: s.status for s in decision.ranked}
    for agent_id in expect.get("ineligible", []):
        assert decision.agent_id != agent_id, f"{agent_id!r} was seated but must be ineligible"
        if agent_id in statuses and not decision.preempted:
            assert statuses[agent_id] in {"vetoed", "below_floor"}, (
                f"{agent_id!r} must be vetoed or below floor in the trace; status={statuses[agent_id]!r}"
            )
    assert "id order" not in decision.reason, (
        f"a labeled case must never resolve by id order: {decision.reason!r}"
    )


@pytest.mark.parametrize("label,case", CASES, ids=[label for label, _ in CASES])
def test_eval_case(label: str, case: dict, roster) -> None:
    decision = _run(case, roster)
    if case.get("known_gap"):
        try:
            _check(case, decision)
        except AssertionError as exc:
            pytest.xfail(f"known gap: {case.get('gap_note', case.get('why', ''))} :: {exc}")
        pytest.fail(
            f"{label} is marked known_gap but now passes; remove the marker so the gap is not forgotten"
        )
    _check(case, decision)


def test_every_case_carries_a_reason_or_is_schema_v1() -> None:
    """Winner-only cases are how accidental passes hide. Version-2 cases must
    say what rule they expect; version-1 cases are grandfathered but counted."""
    for path in sorted(CASE_DIR.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("plane", "policy") != "policy":
            continue
        if doc.get("schema_version", 1) >= 2:
            for case in doc["cases"]:
                assert "reason_contains" in case["expect"] or "outcome" in case["expect"], (
                    f"{path.name}::{case['id']} has no reason or outcome expectation"
                )


def test_deferred_plane_fixtures_are_not_run_as_policy_cases() -> None:
    """Generation-, harness- and transport-plane fixtures are stored, labeled,
    and deliberately not run against the policy layer (ADR-0013)."""
    deferred = CASE_DIR / "deferred"
    assert deferred.is_dir()
    for path in sorted(deferred.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc.get("plane") in {"generation", "harness", "transport"}, path.name
        assert doc.get("runnable_here") is False, path.name
