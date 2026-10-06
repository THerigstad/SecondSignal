"""T1's receipt observer reads one routing result and can change nothing."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_eval_cases import CASES

from secondsignal import load_roster, route
from secondsignal_harness import CodexStore, FakeAdapter, Harness
from secondsignal_harness import harness as harness_module

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def records():
    roster = load_roster()
    chosen = {}
    for _, case in CASES:
        if case.get("prior_turns") or case.get("session"):
            continue
        record = route(case["text"], roster).to_dict()
        kind = "gate" if record["safety"]["action"] == "HUMAN_ESCALATION" else "seated" if record["agent_id"] else "house"
        chosen.setdefault(kind, case["text"])
        if len(chosen) == 3:
            break
    assert len(chosen) == 3
    return roster, CodexStore(ROOT / "docs" / "codex"), chosen


@pytest.mark.parametrize("kind", ["seated", "house"])
def test_t1_observer_receives_an_independent_copy_after_exactly_one_route(records, monkeypatch, kind):
    """Receipts observe the existing noncrisis route once without gaining a write path to its record."""
    roster, codexes, texts = records
    before = Harness(roster, FakeAdapter(), codexes).speak(texts[kind])
    calls = []
    observed = []
    original = harness_module.route

    def counted(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    def observer(record):
        observed.append(record)
        record["agent_id"] = "arbitrary observer edit"
        record["safety"]["disclosures"].append("arbitrary observer line")

    monkeypatch.setattr(harness_module, "route", counted)
    harness = Harness(roster, FakeAdapter(), codexes, decision_observer=observer)
    after = harness.speak(texts[kind])
    assert len(calls) == len(observed) == 1
    assert after.decision == before.decision
    assert after.house_lines == before.house_lines
    assert harness.audit_log.rows()[-1]["decision"] == before.decision


def test_t1_broken_receipt_observer_does_not_change_the_turn(records):
    """A receipt observer exception cannot withhold, replace or reroute the underlying turn."""
    roster, codexes, texts = records

    def broken(record):
        raise OSError("fixture observer unavailable")

    baseline = Harness(roster, FakeAdapter(), codexes).speak(texts["seated"])
    changed = Harness(roster, FakeAdapter(), codexes, decision_observer=broken).speak(texts["seated"])
    assert changed.decision == baseline.decision
    assert changed.text == baseline.text
    assert changed.release_reason == baseline.release_reason


def test_t1_crisis_never_calls_the_receipt_observer_or_adapter(records):
    """A card bypasses the noncrisis receipt observer and model entirely."""
    roster, codexes, texts = records
    calls = []
    adapter = FakeAdapter()
    harness = Harness(roster, adapter, codexes, decision_observer=calls.append)
    card = harness.speak(texts["gate"])
    assert card.action == "HUMAN_ESCALATION"
    assert calls == adapter.calls == []
    assert card.text == "\n".join(card.house_lines)
