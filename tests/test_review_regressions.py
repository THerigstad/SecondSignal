"""Regression pins from the external review (2026-09-01).

Written deliberately against the API surface that existed *before* the review
(`route`, `load_roster`, `Action`, `SessionState` only), so this file runs on
the pre-review tree and fails there. Recorded in
docs/notes/test-audit-2026-08.md: red on the baseline, green after the fixes.
"""

from __future__ import annotations

import json

import pytest

from secondsignal import Action, load_roster, route
from secondsignal.profiles import DEFAULT_PROFILE_DIR


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def test_an_empty_message_does_not_seat_an_agent_by_alphabet(roster):
    """Pre-review: every agent tied at 0.62 and Calder won because 'c' sorts
    first. An empty extract must seat nobody on the first turn."""
    assert route("hey", roster).agent_id is None


def test_a_plural_verb_does_not_defeat_the_crisis_gate(roster):
    """Pre-review: 'wants to die' slipped past an exact substring 'want to die'."""
    assert route("the protagonist wants to die tonight", roster).safety.action is Action.HUMAN_ESCALATION


def test_slang_ideation_reaches_the_gate(roster):
    assert route("anyway if I yeet myself off the bridge lmao", roster).safety.action is Action.HUMAN_ESCALATION


def test_business_language_reaches_the_strategist_not_the_stabilizer(roster):
    """Pre-review: no topic matched and Calder won by sort order."""
    assert route("The art is finally flowing. I need a shop, a funnel, and a launch date.", roster).agent_id == "seren"


def test_a_roster_without_a_stabilizer_cannot_load(tmp_path):
    """Pre-review: deleting the stabilizer and cleaning the handoffs that
    pointed at it produced a roster that loaded without complaint."""
    target = tmp_path / "no_stabilizer"
    target.mkdir()
    for path in sorted(DEFAULT_PROFILE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["id"] == "cody":
            continue
        data["handoffs"] = {k: v for k, v in data.get("handoffs", {}).items() if v != "cody"}
        (target / path.name).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_roster(target)
