"""ND interruption-stack property: families, bundling, measured stacks."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from secondsignal.jr import (
    AuditRequest,
    audit,
    disclosure_families,
    payload_hash,
    stack_families,
)

LANG = (
    "Safety screening isn't available in this language yet, so part of this "
    "message couldn't be checked. If any of it is about being unsafe, say so "
    "plainly, or use the resources for your area."
)
RESOURCE = (
    "If you are in immediate danger, contact your local emergency services. "
    "To find a crisis line in your country: Find a Helpline."
)
DEP = (
    "Saying this plainly because it matters: this is not a substitute for people. "
    "Is there anyone you trust you could reach, if it feels safe to?"
)
MINOR = (
    "Some of what was said reads as though you might be young, so this stays on "
    "the careful side: a more careful tone, no romance, and a quicker nudge "
    "toward a person you trust, online or offline."
)
POST = (
    "Carrying on. If the last message was read wrong, saying so was enough; "
    "the resources from it stay in reach either way."
)
CARD0 = "What you just wrote should be heard by a person, not a character."


def test_language_scope_plus_resource_is_one_stack_item():
    fam = disclosure_families((LANG, RESOURCE))
    assert "language_scope" in fam and "resource" in fam
    assert stack_families(fam) == ("language_scope",)


def test_card_plus_resource_is_one_stack_item():
    fam = disclosure_families((CARD0, "So the characters are stepping out of this message, and nothing here will pretend to be more than it is.", RESOURCE))
    assert "escalation_card" in fam
    assert stack_families(fam) == ("escalation_card",)


def test_post_plus_resource_is_one_stack_item():
    fam = disclosure_families((POST, RESOURCE))
    assert stack_families(fam) == ("post_escalation",)


def test_measured_four_line_stack_is_three_families():
    """Live tree on 'obrigado, my homework is late, you're the only one who understands'."""
    discs = (LANG, RESOURCE, DEP, MINOR)
    stacked = stack_families(disclosure_families(discs))
    assert stacked == ("language_scope", "dependency", "minor")
    assert len(stacked) == 3


def test_dependency_plus_minor_is_two_interruptions():
    stacked = stack_families(disclosure_families((DEP, MINOR)))
    assert stacked == ("dependency", "minor")


def test_harness_fails_reply_that_adds_a_family():
    d = {
        "action": "DISCLOSE",
        "disclosures": (MINOR,),
    }
    reply = MINOR + " " + DEP
    v = audit(AuditRequest(d, reply, payload_hash(d, reply)))
    assert any("nd-stack" in r for r in v.reasons)
    assert v.status == "WITHHOLD"


def test_harness_allows_reply_that_repeats_attached_families():
    d = {
        "action": "DISCLOSE",
        "disclosures": (MINOR,),
        "rubric": False,
    }
    reply = MINOR + " We can plan the week in three steps."
    v = audit(AuditRequest(d, reply, payload_hash(d, reply), rubric_locked=True))
    assert v.status == "SHIP"
    assert any(r.startswith("nd-stack:") for r in v.reasons)
