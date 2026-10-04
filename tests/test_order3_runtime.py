"""Order 3: audit errors are fixed text; supplied runtime repairs stay pinned."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from secondsignal import Action, SessionState, load_roster, route
from secondsignal.profiles import AgentProfile, find_stabilizers
from secondsignal.router import no_signal_seat
from secondsignal.safety import AFTERMATH_TURNS
from secondsignal_harness import AuditLog, CodexStore, FakeAdapter, Harness
from secondsignal_harness.adapters import AdapterError
from secondsignal_harness.harness import FAILURE_LINE, RELEASE_FAILURE

ROOT = Path(__file__).resolve().parents[1]
FIXED_ADAPTER_ERROR = "adapter error: the model call failed."


def _fixture_text(filename: str, case_id: str) -> str:
    data = json.loads((ROOT / "evals" / "cases" / filename).read_text(encoding="utf-8"))
    return next(case["text"] for case in data["cases"] if case["id"] == case_id)


@pytest.fixture(scope="module")
def roster():
    return load_roster()


@pytest.mark.parametrize("kind", ["adapter", "vendor", "exception_name"])
@pytest.mark.parametrize("retries", [0, 1])
def test_adapter_exception_details_never_enter_the_audit(roster, kind, retries) -> None:
    secret = "sk-order3-" + "a" * 24  # Synthetic marker, deliberately confined to a test.
    exception_type = {
        "adapter": AdapterError,
        "vendor": ValueError,
        "exception_name": type(secret, (RuntimeError,), {}),
    }[kind]
    adapter = FakeAdapter(script=(exception_type(secret),))
    harness = Harness(
        roster, adapter, CodexStore(ROOT / "docs" / "codex"),
        audit_log=AuditLog(), retries=retries,
    )

    turn = harness.speak(_fixture_text("routing.json", "analysis-career-tradeoff"))

    assert turn.release_reason == RELEASE_FAILURE
    assert turn.released is False
    assert turn.text == FAILURE_LINE
    assert turn.adapter_calls == len(adapter.calls) == 1 + retries
    row = harness.audit_log.read(turn.row_id)
    assert row is not None
    # Boolean assertions keep a deliberately failing regression from printing the marker.
    fixed_error = row["error"] == FIXED_ADAPTER_ERROR
    leaked_error = secret in json.dumps(harness.audit_log.rows())
    assert fixed_error
    assert not leaked_error


def test_unscreened_card_protects_the_bounded_aftermath(roster) -> None:
    text = _fixture_text("safety_gate.json", "french-ideation-escalates-for-the-honest-reason")
    ordinary = _fixture_text("routing.json", "analysis-career-tradeoff")
    session = SessionState(locale="US")
    card = route(text, roster, session=session)
    assert card.safety.action is Action.HUMAN_ESCALATION
    assert card.safety.language_scope == "unscreened"
    assert session.aftermath_turns == AFTERMATH_TURNS

    first = route(ordinary, roster, session=session)
    acknowledgement = route("ok", roster, session=session)
    assert session.aftermath_turns == AFTERMATH_TURNS
    second = route(ordinary, roster, session=session)
    # Ruling 15 of 3 October 2026: the reply that spends the last count is itself protected, so
    # the second consuming turn (``last``) stays protected and the turn after it is released.
    last = route(ordinary, roster, session=session)
    assert session.aftermath_turns == 0
    for protected in (first, acknowledgement, second, last):
        assert "no_joke" in protected.obligations
        assert "humor" in protected.mode_vetoes
        assert any("988" in line for line in protected.safety.disclosures)
    after = route(ordinary, roster, session=session)
    assert session.aftermath_turns == 0
    assert "no_joke" not in after.obligations
    assert "humor" not in after.mode_vetoes
    assert after.safety.action is Action.PROCEED


def test_another_unscreened_card_renews_the_aftermath(roster) -> None:
    text = _fixture_text("safety_gate.json", "french-ideation-escalates-for-the-honest-reason")
    session = SessionState(locale="US", aftermath_turns=1, declared_age_band="minor")
    card = route(text, roster, session=session)
    assert card.safety.action is Action.HUMAN_ESCALATION
    assert session.aftermath_turns == AFTERMATH_TURNS
    assert session.latch == "hard"


@pytest.mark.parametrize("order", [("zebra", "middle", "alpha"), ("middle", "alpha", "zebra")])
def test_stabilizers_and_the_fallback_seat_ignore_roster_insertion_order(order) -> None:
    profiles = {
        name: AgentProfile(id=name, display_name=name.title(), one_line="Test profile")
        for name in order
    }
    profiles["veto"] = AgentProfile(
        id="veto", display_name="Veto", one_line="Test profile",
        contraindications=frozenset({"humor"}),
    )
    profiles["raised_floor"] = AgentProfile(
        id="raised_floor", display_name="Raised floor", one_line="Test profile",
        regulation_window=(0.2, 1.0),
    )
    assert find_stabilizers(profiles) == ["alpha", "middle", "zebra"]
    assert no_signal_seat(profiles) == "alpha"
