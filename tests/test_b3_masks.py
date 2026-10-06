"""B3 mask fixtures and controls, drawn only from existing labelled text."""

from __future__ import annotations

from dataclasses import replace

import pytest
import test_crisis_gate as gate
from test_eval_cases import CASES, field_failures, run_case

from evals.gap_triage.measure_cheap import (
    mask_done_with_exit_candidate,
    mask_spoken_idiom_candidates,
    mask_thing_subject_candidate,
)
from secondsignal import Action, load_roster
from secondsignal.lexicon import PACKS, apply_masks
from secondsignal.normalize import normalize
from secondsignal.safety import crisis_screen

BY_ID = {case["id"]: case for _, case in CASES}
PAIRS = (
    ("b3_die_of_boredom", "gap-spoken-gonna-die-of-boredom", "grok-r2-gonna-die-001"),
    ("b3_die_compliment", "gap-spoken-wanna-die-compliment", "grok-r2-wanna-die-001"),
    ("b3_die_in_peace_show", "gap-spoken-let-me-die-show", "grok-r2-let-me-die-001"),
    ("b3_end_on_note", "gap-spoken-editors-end-note", "grok-r2-wanna-endit-001"),
    ("b3_end_after_credits", "gap-spoken-gonna-end-credits", "grok-r2-wanna-endit-001"),
    ("b3_done_with_exit", "gap-done-with-a-next-step-over-restricted", "inconclusive-done"),
    ("b3_thing_subject", "r3b-tense-known-gap-thing-subject-001", "r3b-tense-present-first-person-001"),
)


def control_text(control_id):
    if control_id == "inconclusive-done":
        # Reuse the first labelled fail-closed control from the existing test;
        # no new crisis sentence is authored for this order.
        marks = gate.test_inconclusive_language_escalates_under_fail_closed.pytestmark
        return next(mark.args[1][0] for mark in marks if mark.name == "parametrize")
    return BY_ID[control_id]["text"]


@pytest.mark.parametrize("mask_id,case_id,control_id", PAIRS, ids=[row[0] for row in PAIRS])
def test_b3_mask_releases_fixture_and_keeps_its_crisis_control(mask_id, case_id, control_id):
    """Each of seven masks releases its full fixture while its matching crisis shape still cards."""
    case = BY_ID[case_id]
    decision, session = run_case(case, load_roster())
    assert not field_failures(case, decision, session)
    assert mask_id in {span.pattern_id for span in decision.safety.masked_spans}
    control = gate.verdict(control_text(control_id))
    assert control.action is Action.HUMAN_ESCALATION
    assert mask_id not in {span.pattern_id for span in control.masked_spans}


@pytest.mark.parametrize("mask_id,case_id,control_id", PAIRS, ids=[row[0] for row in PAIRS])
def test_b3_mask_matches_measured_candidate_and_is_crisis_only(mask_id, case_id, control_id):
    """Each mask preserves the measured blanked span and leaves routing's mask input unchanged."""
    pack = replace(PACKS["en"],
                   regex_masks=tuple(row for row in PACKS["en"].regex_masks if row[0] == mask_id),
                   window_masks=())
    text = normalize(BY_ID[case_id]["text"])
    candidate = (mask_done_with_exit_candidate if mask_id == "b3_done_with_exit"
                 else mask_thing_subject_candidate if mask_id == "b3_thing_subject"
                 else mask_spoken_idiom_candidates)
    folded, spans = apply_masks(text, (pack,), crisis_only=True)
    assert folded == candidate(text)
    assert len(spans) == 1
    assert apply_masks(text, (pack,)) == (text, ())


def test_b3_masks_leave_the_sixth_idiom_and_second_next_step_documented():
    """The unresolved summary and bare next-step fixture keep their original expectations and markers."""
    for ident in ("gap-spoken-we-end-summary", "grok-r2-done-next-001"):
        case = BY_ID[ident]
        decision, session = run_case(case, load_roster())
        assert case["known_gap"]
        assert field_failures(case, decision, session)
    assert crisis_screen(BY_ID["grok-r2-done-next-001"]["text"]).read == "MISS"
