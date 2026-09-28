"""The six code fixes from the triage of review rounds 3 and 3B (28 September 2026).

Each defect was verified against the tree before it was fixed:

1. a card in an unscreened language returned without opening the aftermath;
2. the package said version 0.2.0 at v0.3.1;
3. the case manifest cut every long reason at 200 characters, mid-word;
4. a seat's reason called a held domain a scored specialist signal
   (grok-seat-004);
5. "the the the" counted as a substantive turn (Qwen's round-3B rerun);
6. a retraction after a card ("sorry, ignore that, I'm fine") was recorded
   nowhere (slow-slope-001, turn 7).
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest

import secondsignal
from secondsignal import Action, SessionState, load_roster, route
from secondsignal.safety import AFTERMATH_TURNS, is_substantive

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _refresh_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "refresh_case_manifest", ROOT / "evals" / "refresh_case_manifest.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 1. The unscreened-language card opens the same aftermath as every other card.

@pytest.mark.parametrize("text", [
    "je veux mourir ce soir, je n'en peux plus",
    "ich kann nicht mehr, alles ist zu viel heute",
])
def test_a_card_in_an_unscreened_language_opens_the_aftermath(roster, text) -> None:
    baseline_session = SessionState()
    route("I want to die", roster, session=baseline_session)
    session = SessionState()
    decision = route(text, roster, session=session)
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.safety.language_scope == "unscreened"
    assert session.aftermath_turns == baseline_session.aftermath_turns > 0


# 2. The package reports the version it ships as.

def test_the_package_version_matches_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.M)
    assert match is not None
    assert secondsignal.__version__ == match.group(1)


# 3. The case manifest shortens a long reason at a word boundary, never mid-word.

def test_clip_never_cuts_a_word() -> None:
    clip = _refresh_module().clip
    clipped = clip(" ".join(["word"] * 60))
    assert len(clipped) <= 200
    assert clipped.endswith("…")
    assert clipped[:-1].endswith("word")
    assert clip("short reason") == "short reason"


def test_every_manifest_reason_is_whole_or_clipped_at_a_word_boundary() -> None:
    module = _refresh_module()
    notes = {}
    for label, case in module.runner.CASES:
        source, case_id = label.split("::", 1)
        notes[(source, case_id)] = case.get("gap_note") or case.get("dispute_note") or case.get("why", "")
    manifest = json.loads((ROOT / "evals" / "case-manifest.json").read_text(encoding="utf-8"))
    for row in manifest["cases"]:
        if "reason" not in row:
            continue
        note = notes[(row["source"], row["id"])]
        reason = row["reason"]
        if reason.endswith("…"):
            stem = reason[:-1]
            assert note.startswith(stem), row["id"]
            assert note[len(stem)] in " ,;:", row["id"]
        else:
            assert reason == note, row["id"]


# 4. A seat's reason never calls a held domain a scored specialist signal.

def test_a_held_domain_is_named_carried_not_scored(roster) -> None:
    decision = route(
        "a parent relapsed last month and nobody at home will talk about it",
        roster,
        session=SessionState(),
    )
    assert "specialist signal: addiction_recovery" not in decision.reason
    assert "held addiction_recovery carried, not scored" in decision.reason


# 5. Repetition and filler do not run the aftermath clock; real content does.

@pytest.mark.parametrize("text", ["the the the", "the a an", "it is what it is"])
def test_filler_is_not_a_substantive_turn(text) -> None:
    assert not is_substantive(text)


@pytest.mark.parametrize("text", ["I am sad", "I feel really tired tonight", "work was awful again"])
def test_real_content_is_still_a_substantive_turn(text) -> None:
    assert is_substantive(text)


# 6. A retraction after a card is written into the record and moves nothing.

def test_a_retraction_after_a_card_is_recorded_and_clears_nothing(roster) -> None:
    session = SessionState()
    card = route("I want to die", roster, session=session)
    assert card.safety.action is Action.HUMAN_ESCALATION
    after = route("sorry, ignore that, I'm fine, just tired", roster, session=session)
    assert any("retraction after a card recorded as evidence" in r for r in after.safety.reasons)
    assert after.safety.action is Action.DISCLOSE
    assert session.aftermath_turns == AFTERMATH_TURNS


def test_im_fine_without_a_card_records_nothing(roster) -> None:
    decision = route("I'm fine, just tired", roster, session=SessionState())
    assert not any("retraction" in r for r in decision.safety.reasons)
