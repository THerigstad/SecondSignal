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
* ``expect.card``                standard | danger | compound: the card kind on an escalation
* ``expect.card_order``          the resource lines on the card in the order shown
                                 (self_harm, other_person_danger); an exact list
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
from secondsignal.profiles import canonicalize_expectation

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


EXPECT_KEYS: frozenset[str] = frozenset({
    "safety", "outcome", "agent", "agent_any_of", "reason_contains",
    "crisis_read", "integrity_event", "disclosures_contain", "latch",
    "latch_reasons", "held", "assist", "card", "preference_result",
    "language_scope", "not_seated", "obligations_contain", "ineligible",
    "card_order",
})
"""Every expectation key the runner knows how to check.

A key outside this set is silently ignored by an ``if "x" in expect`` runner,
so a fixture with a misspelled key looks like it is asserting something and
asserts nothing. ``tests/test_case_manifest.py`` fails on any key not listed
here; adding a key to a fixture means adding the check and the name together.
"""


def field_failures(case: dict, decision, session) -> dict[str, str]:
    """Check every expectation and return the failures keyed by field.

    Returning a dict instead of raising on the first failure is what lets an
    expected-to-fail case stay narrow. A case marked ``known_gap`` because of
    its ``safety`` verdict must still assert its seat, its holds and its
    obligations: before this, any one failure inside such a case produced an
    xfail, so an unrelated regression injected anywhere in it was recorded as
    an expected failure and never seen. Measured 2026-09-05; fixed here.
    """
    # A fixture may name a persona by an earlier name (the alias layer keeps
    # external reviewers' fixtures byte for byte); the decision carries the
    # canonical id, so the expectation is resolved before any comparison.
    expect = canonicalize_expectation(case["expect"])
    bad: dict[str, str] = {}

    def check(field: str, ok: bool, message: str) -> None:
        if not ok:
            bad[field] = message

    if "safety" in expect:
        check("safety", decision.safety.action is Action[expect["safety"]],
              f"expected {expect['safety']}, got {decision.safety.action.name}; "
              f"reasons={decision.safety.reasons}")
    if "outcome" in expect:
        check("outcome", decision.outcome is Outcome[expect["outcome"]],
              f"expected {expect['outcome']}, got {decision.outcome.value} ({decision.reason})")
    if "agent" in expect:
        check("agent", decision.agent_id == expect["agent"],
              f"expected {expect['agent']!r}, got {decision.agent_id!r}; reason={decision.reason!r}; "
              f"ranked={[(s.agent_id, s.status, s.score) for s in decision.ranked]}")
    if "agent_any_of" in expect:
        check("agent_any_of", decision.agent_id in expect["agent_any_of"],
              f"expected one of {expect['agent_any_of']}, got {decision.agent_id!r}; "
              f"reason={decision.reason!r}")
    if "reason_contains" in expect:
        trace = " || ".join([
            decision.reason,
            *decision.safety.reasons,
            decision.assist_reason,
            *(" ".join(s.rationale) for s in decision.ranked),
        ])
        check("reason_contains", expect["reason_contains"] in trace,
              f"expected the record to contain {expect['reason_contains']!r}; "
              f"reason={decision.reason!r}; safety={decision.safety.reasons}")
    if "crisis_read" in expect:
        check("crisis_read", decision.safety.crisis_read == expect["crisis_read"],
              f"expected {expect['crisis_read']}, got {decision.safety.crisis_read}")
    if "integrity_event" in expect:
        check("integrity_event", decision.safety.integrity_event is expect["integrity_event"],
              f"expected {expect['integrity_event']}, got {decision.safety.integrity_event}")
    if "disclosures_contain" in expect:
        needle = expect["disclosures_contain"]
        check("disclosures_contain", any(needle in d for d in decision.safety.disclosures),
              f"none contains {needle!r}; got {decision.safety.disclosures}")
    if "latch" in expect:
        check("latch", session.latch == expect["latch"],
              f"expected {expect['latch']}, got {session.latch} ({session.latch_reasons}); "
              f"history={session.latch_history}")
    if "latch_reasons" in expect:
        missing = [r for r in expect["latch_reasons"] if r not in decision.safety.latch_reasons]
        check("latch_reasons", not missing,
              f"expected {missing} in {decision.safety.latch_reasons}")
    if "held" in expect:
        missing = [d for d in expect["held"] if d not in decision.held]
        check("held", not missing, f"expected {missing} in {decision.held}")
    if "assist" in expect:
        check("assist", decision.assist_agent_id == expect["assist"],
              f"expected {expect['assist']!r}, got {decision.assist_agent_id!r} "
              f"({decision.assist_reason})")
    if "card" in expect and expect["card"] is not None:
        check("card", decision.safety.card == expect["card"],
              f"expected {expect['card']}, got {decision.safety.card}")
    if "card_order" in expect:
        check("card_order", list(decision.safety.card_order) == list(expect["card_order"]),
              f"expected {expect['card_order']}, got {list(decision.safety.card_order)}")
    if "preference_result" in expect:
        check("preference_result", decision.safety.preference_result == expect["preference_result"],
              f"expected {expect['preference_result']}, got {decision.safety.preference_result}; "
              f"reasons={decision.safety.reasons}")
    if "language_scope" in expect:
        check("language_scope", decision.safety.language_scope == expect["language_scope"],
              f"expected {expect['language_scope']}, got {decision.safety.language_scope}")
    seated = [a for a in expect.get("not_seated", [])
              if a in (decision.agent_id, decision.assist_agent_id)]
    if expect.get("not_seated"):
        check("not_seated", not seated, f"{seated} seated or assisted but must not be")
    if expect.get("obligations_contain"):
        missing = [n for n in expect["obligations_contain"]
                   if not any(n in o for o in decision.obligations)]
        check("obligations_contain", not missing,
              f"none contains {missing}; got {decision.obligations}")
    statuses = {s.agent_id: s.status for s in decision.ranked}
    if expect.get("ineligible"):
        problems = []
        for agent_id in expect["ineligible"]:
            if agent_id in (decision.agent_id, decision.assist_agent_id):
                problems.append(f"{agent_id!r} seated or assisted")
            elif (agent_id in statuses and not decision.preempted
                  and statuses[agent_id] not in INELIGIBLE_STATUSES):
                problems.append(f"{agent_id!r} status={statuses[agent_id]!r}")
        check("ineligible", not problems,
              f"must be vetoed, below floor, capped or outranked: {problems}")
    check("id_order", "id order" not in decision.reason,
          f"a labeled case must never resolve by id order: {decision.reason!r}")
    return bad


def check_case(case: dict, decision, session) -> None:
    """Raise on the first failing field. Kept for callers that want the old
    all-or-nothing behaviour."""
    bad = field_failures(case, decision, session)
    if bad:
        field, message = next(iter(bad.items()))
        raise AssertionError(f"{field}: {message}")


MANIFEST_PATH = Path(__file__).resolve().parents[1] / "evals" / "case-manifest.json"
MANIFEST = {
    entry["id"]: entry
    for entry in json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["cases"]
}


@pytest.mark.parametrize("label,case", CASES, ids=[label for label, _ in CASES])
def test_eval_case(label: str, case: dict, roster) -> None:
    decision, session = run_case(case, roster)
    bad = field_failures(case, decision, session)
    expected_to_fail = case.get("known_gap") or case.get("disputed")

    if not expected_to_fail:
        if bad:
            field, message = next(iter(bad.items()))
            raise AssertionError(f"{field}: {message}")
        return

    kind = "known gap" if case.get("known_gap") else "disputed"
    approved = set(MANIFEST.get(case["id"], {}).get("mismatch_fields", []))
    unapproved = {f: m for f, m in bad.items() if f not in approved}
    if unapproved:
        # The point of the manifest. This case is allowed to fail on the
        # fields its disposition names and on nothing else, so a regression
        # anywhere else inside it is a red test rather than one more
        # expected failure nobody reads.
        field, message = next(iter(unapproved.items()))
        pytest.fail(
            f"{label} is marked {kind} on {sorted(approved)}, but {field} also "
            f"fails now: {message}. Either this is a regression, or the "
            f"disposition changed and evals/case-manifest.json must say so."
        )
    if bad:
        note = case.get("gap_note") or case.get("dispute_note") or case.get("why", "")
        pytest.xfail(f"{kind} on {sorted(bad)}: {note}")
    pytest.fail(
        f"{label} is marked {kind} but now passes; "
        "remove the marker so the record stays honest"
    )


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
    """Generation-, harness-, transport-, orchestration- and persistence-plane
    fixtures are stored, labeled, and deliberately not run against the policy
    layer (ADR-0013)."""
    deferred = CASE_DIR / "deferred"
    assert deferred.is_dir()
    for path in sorted(deferred.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc.get("plane") in {"generation", "harness", "transport", "orchestration", "persistence"}, path.name
        assert doc.get("runnable_here") is False, path.name
