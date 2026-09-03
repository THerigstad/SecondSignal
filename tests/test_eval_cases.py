"""Run every labeled case under ``evals/cases/`` through the real pipeline.

Cases were documentation until the external review (2026-09-01) showed that a
suite can pass on the winner alone: four cases landed on the right agent by
alphabetical accident. Every case now carries what it expects and *why*:

* ``expect.safety``              the safety action name
* ``expect.outcome``             ROUTED | PREEMPTED | UNRESOLVED
* ``expect.agent``               exact agent id, or null when no persona may engage
* ``expect.agent_any_of``        accepted ids when the gold is a documented disagreement
* ``expect.reason_contains``     a substring the decision record must carry: the
                                 routing reason, a safety reason, the assist
                                 reason, or a candidate's rationale
* ``expect.ineligible``          ids that must not be seated and, if in the roster,
                                 must appear vetoed, below floor, capped or
                                 outranked in the trace
* ``expect.not_seated``          ids that must not be the seat or the assist; the
                                 weaker claim, for a persona that simply lost
* ``expect.obligations_contain`` substrings each of which some obligation must carry
* ``expect.crisis_read``         HIT | MISS | INCONCLUSIVE
* ``expect.integrity_event``     whether an override attempt was recorded
* ``expect.disclosures_contain`` a substring some attached line must carry
* ``expect.latch``               none | soft | hard (session latch after the turn)
* ``expect.latch_reasons``       reasons that must all be present on the verdict
* ``expect.held``                hold domains that must all be on the decision
* ``expect.assist``              the assist id, or null for no assist
* ``expect.card``                standard (the one card) for escalations
* ``expect.preference_result``   ask_first | refused | accepted
* ``expect.language_scope``      screened | unscreened

A case may carry a ``session`` block -- ``declared_age_band``,
``declared_language``, ``affinities``, ``preferences`` -- which is the
operator's declared state, never something a message wrote.

A case marked ``known_gap`` is a documented failure the reference lexicon is
not expected to pass. It is run as a strict expected failure: if it starts
passing, the run fails so the marker gets removed rather than forgotten. A
case marked ``disputed`` carries a reviewer's expectation that the project
decided against, with the decision's justification in ``dispute_note`` and
in ``docs/notes/dissent-log.md``; it is run the same way, so that the
dissent stays measurable instead of deleted. A case marked
``contract_adjusted`` is a reviewer's case whose expectation was written
against a contract that has since moved (a language pack that now exists, a
field whose meaning was clarified, a stricter verdict); it runs and must
pass, and it keeps the reviewer's wording in ``original_expect`` with the
reason for the move in ``adjust_note``. Deleting a failing case to make the
suite green is not an option this runner offers.

Schema version 1 cases (``text``, ``expect.safety``, ``expect.agent``, ``why``)
are still accepted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from secondsignal import Action, Outcome, SessionState, load_roster, route

CASE_DIR = Path(__file__).resolve().parents[1] / "evals" / "cases"
INELIGIBLE_STATUSES = {"vetoed", "below_floor", "capped", "outranked"}


def _load_cases() -> list[tuple[str, dict]]:
    cases: list[tuple[str, dict]] = []
    for path in sorted(CASE_DIR.rglob("*.json")):
        if "deferred" in path.parts:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("plane", "policy") != "policy":
            continue
        rel = path.relative_to(CASE_DIR).with_suffix("").as_posix()
        for case in doc["cases"]:
            cases.append((f"{rel}::{case['id']}", case))
    return cases


CASES = _load_cases()


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def make_session(case: dict) -> SessionState:
    block = case.get("session") or {}
    return SessionState(
        locale=case.get("locale"),
        declared_language=block.get("declared_language"),
        declared_age_band=block.get("declared_age_band", "unknown"),
        affinities=tuple(block.get("affinities", ())),
        preferences=dict(block.get("preferences", {})),
    )


def _prior_text(turn) -> str:
    return turn["text"] if isinstance(turn, dict) else turn


def run_case(case: dict, roster):
    session = make_session(case)
    for prior in case.get("prior_turns", []):
        route(_prior_text(prior), roster, session=session)
    return route(case["text"], roster, session=session), session


def check_case(case: dict, decision, session) -> None:
    expect = case["expect"]

    if "safety" in expect:
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
        trace = " || ".join([
            decision.reason,
            *decision.safety.reasons,
            decision.assist_reason,
            *(" ".join(s.rationale) for s in decision.ranked),
        ])
        assert expect["reason_contains"] in trace, (
            f"reason: expected the record to contain {expect['reason_contains']!r}; "
            f"reason={decision.reason!r}; safety={decision.safety.reasons}"
        )
    if "crisis_read" in expect:
        assert decision.safety.crisis_read == expect["crisis_read"], (
            f"crisis_read: expected {expect['crisis_read']}, got {decision.safety.crisis_read}"
        )
    if "integrity_event" in expect:
        assert decision.safety.integrity_event is expect["integrity_event"]
    if "disclosures_contain" in expect:
        needle = expect["disclosures_contain"]
        assert any(needle in d for d in decision.safety.disclosures), (
            f"disclosures: none contains {needle!r}; got {decision.safety.disclosures}"
        )
    if "latch" in expect:
        assert session.latch == expect["latch"], (
            f"latch: expected {expect['latch']}, got {session.latch} ({session.latch_reasons}); "
            f"history={session.latch_history}"
        )
    if "latch_reasons" in expect:
        for reason in expect["latch_reasons"]:
            assert reason in decision.safety.latch_reasons, (
                f"latch_reasons: expected {reason!r} in {decision.safety.latch_reasons}"
            )
    if "held" in expect:
        for domain in expect["held"]:
            assert domain in decision.held, f"held: expected {domain!r} in {decision.held}"
    if "assist" in expect:
        assert decision.assist_agent_id == expect["assist"], (
            f"assist: expected {expect['assist']!r}, got {decision.assist_agent_id!r} ({decision.assist_reason})"
        )
    if "card" in expect and expect["card"] is not None:
        assert decision.safety.card == expect["card"], (
            f"card: expected {expect['card']}, got {decision.safety.card}"
        )
    if "preference_result" in expect:
        assert decision.safety.preference_result == expect["preference_result"], (
            f"preference_result: expected {expect['preference_result']}, got {decision.safety.preference_result}; "
            f"reasons={decision.safety.reasons}"
        )
    if "language_scope" in expect:
        assert decision.safety.language_scope == expect["language_scope"]
    for agent_id in expect.get("not_seated", []):
        assert decision.agent_id != agent_id, f"{agent_id!r} was seated but must not be"
        assert decision.assist_agent_id != agent_id, f"{agent_id!r} was the assist but must not be"
    for needle in expect.get("obligations_contain", []):
        assert any(needle in o for o in decision.obligations), (
            f"obligations: none contains {needle!r}; got {decision.obligations}"
        )
    statuses = {s.agent_id: s.status for s in decision.ranked}
    for agent_id in expect.get("ineligible", []):
        assert decision.agent_id != agent_id, f"{agent_id!r} was seated but must be ineligible"
        assert decision.assist_agent_id != agent_id, f"{agent_id!r} was the assist but must be ineligible"
        if agent_id in statuses and not decision.preempted:
            assert statuses[agent_id] in INELIGIBLE_STATUSES, (
                f"{agent_id!r} must be vetoed, below floor, capped or outranked in the trace; "
                f"status={statuses[agent_id]!r}"
            )
    assert "id order" not in decision.reason, (
        f"a labeled case must never resolve by id order: {decision.reason!r}"
    )


@pytest.mark.parametrize("label,case", CASES, ids=[label for label, _ in CASES])
def test_eval_case(label: str, case: dict, roster) -> None:
    decision, session = run_case(case, roster)
    expected_to_fail = case.get("known_gap") or case.get("disputed")
    if expected_to_fail:
        try:
            check_case(case, decision, session)
        except AssertionError as exc:
            kind = "known gap" if case.get("known_gap") else "disputed"
            note = case.get("gap_note") or case.get("dispute_note") or case.get("why", "")
            pytest.xfail(f"{kind}: {note} :: {exc}")
        pytest.fail(
            f"{label} is marked {'known_gap' if case.get('known_gap') else 'disputed'} but now passes; "
            "remove the marker so the record stays honest"
        )
    check_case(case, decision, session)


def test_every_case_carries_a_reason_or_is_schema_v1() -> None:
    """Winner-only cases are how accidental passes hide. Version-2 cases must
    say what rule they expect; version-1 cases are grandfathered but counted."""
    for path in sorted(CASE_DIR.rglob("*.json")):
        if "deferred" in path.parts:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("plane", "policy") != "policy":
            continue
        if doc.get("schema_version", 1) >= 2 and not doc.get("external"):
            for case in doc["cases"]:
                assert "reason_contains" in case["expect"] or "outcome" in case["expect"], (
                    f"{path.name}::{case['id']} has no reason or outcome expectation"
                )


def test_every_contract_adjusted_case_keeps_the_original() -> None:
    """A reviewer's expectation that the contract moved past is kept next to
    the adjusted one, with the reason. Nothing a reviewer wrote is erased."""
    for path in sorted(CASE_DIR.rglob("*.json")):
        if "deferred" in path.parts:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for case in doc.get("cases", []):
            if case.get("contract_adjusted"):
                assert case.get("original_expect"), f"{path.name}::{case['id']} is adjusted without original_expect"
                assert case.get("adjust_note"), f"{path.name}::{case['id']} is adjusted without adjust_note"
                assert case["original_expect"] != case["expect"], f"{path.name}::{case['id']} adjusted to itself"


def test_every_disputed_case_names_its_justification() -> None:
    """A dissent that lost a decision stays in the suite with the decision's
    reasons attached. No fixture is deleted for losing a vote."""
    for path in sorted(CASE_DIR.rglob("*.json")):
        if "deferred" in path.parts:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for case in doc.get("cases", []):
            if case.get("disputed"):
                assert case.get("dispute_note"), f"{path.name}::{case['id']} is disputed without a note"


def test_deferred_plane_fixtures_are_not_run_as_policy_cases() -> None:
    """Generation-, harness- and transport-plane fixtures are stored, labeled,
    and deliberately not run against the policy layer (ADR-0013)."""
    deferred = CASE_DIR / "deferred"
    assert deferred.is_dir()
    for path in sorted(deferred.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc.get("plane") in {"generation", "harness", "transport"}, path.name
        assert doc.get("runnable_here") is False, path.name
