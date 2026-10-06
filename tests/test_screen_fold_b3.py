"""Order B3, 5 October 2026: measured copies, existing labelled text only."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from test_eval_cases import CASES

from apps.talking_table.server import _card_decision
from evals.fuzz.transforms import TRANSFORMS
from evals.gap_triage.measure_cheap import crisis_vocabulary
from secondsignal import Action, SessionState, extract, load_roster, route
from secondsignal.normalize import _screen_vocabulary, normalize, screen_fold
from secondsignal.safety import crisis_screen
from secondsignal_harness import AuditLog, CodexStore, FakeAdapter, Harness

ROOT = Path(__file__).resolve().parents[1]
BY_ID = {case["id"]: case for _, case in CASES}
FOLD_CASES = [
    ("fuzz-punctuation-doubled-inconclusive-001", "doubled_punctuation"),
    ("fuzz-punctuation-doubled-other-person-danger-001", "doubled_punctuation"),
    ("fuzz-punctuation-doubled-passive-absence-001", "doubled_punctuation"),
    ("fuzz-one-letter-repeated-three-times-direct-ideation-001", "tripled_letters"),
    ("fuzz-one-letter-repeated-three-times-inconclusive-001", "tripled_letters"),
    ("fuzz-one-letter-repeated-three-times-other-person-weapon-001", "tripled_letters"),
    ("fuzz-one-letter-repeated-three-times-passive-absence-001", "tripled_letters"),
    ("grok-r2-spaced-die-001", "separators"),
    ("grok-r2-leet-die-001", "lookalikes"),
    ("grok-r2-norm-cgj-001", "doubled_vowel"),
]
EXTRA_STUTTERS = [
    ("uh_before_the_last_word", ident) for ident in (
        "grok-r2-norm-lrm-001", "grok-r2-norm-rlm-001", "grok-r2-norm-combining-001",
        "grok-r2-norm-cgj-001", "grok-r2-leet-die-001", "gap-obfuscation-b7-055",
        "gap-obfuscation-b7-056", "gap-obfuscation-b7-057", "gap-obfuscation-b7-060",
        "gap-obfuscation-b7-061", "gap-obfuscation-b7-062", "gap-obfuscation-b7-067",
        "gap-obfuscation-b7-091", "gap-obfuscation-b7-092", "gap-obfuscation-b7-093",
        "grok-hg-005",
    )
] + [
    ("middle_word_repeated_with_comma", "gap-obfuscation-b7-093"),
] + [
    ("first_long_word_syllable_stuttered", ident) for ident in (
        "grok-r2-mask-order-001", "live-modal-give-up-001",
        "r3b-tense-inconclusive-ending-it-001", "r3b-tense-inconclusive-ending-things-001",
        "grok-mask-007",
    )
]


def test_screen_vocabulary_is_exactly_the_measured_b5_vocabulary():
    """The production gate uses the measured mechanical vocabulary with no additions."""
    assert _screen_vocabulary() == crisis_vocabulary()


@pytest.mark.parametrize("case_id,fold_name", FOLD_CASES)
def test_closed_fold_fixture_escalates_and_names_the_changed_copy(case_id, fold_name):
    """Each existing fold fixture receives the card and records its applicable fold."""
    case = BY_ID[case_id]
    screen = crisis_screen(case["text"])
    assert screen.read in {"HIT", "INCONCLUSIVE"}
    assert fold_name in screen.screen_folds
    decision = route(case["text"], load_roster())
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.safety.screen_folds == screen.screen_folds
    assert decision.to_dict()["safety"]["screen_folds"] == list(screen.screen_folds)
    assert "folded copy" in decision.explain()


def test_screen_folds_leave_extraction_and_session_history_unfolded():
    """A rescued fixture reaches extraction and session history with its separators intact."""
    text = BY_ID["grok-r2-spaced-die-001"]["text"]
    session = SessionState()
    with patch("secondsignal.router.extract", wraps=extract) as observed:
        decision = route(text, load_roster(), session=session)
    assert observed.call_args.args[0] == text
    assert session.history == [normalize(text)]
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert "separators" in decision.safety.screen_folds


def test_fold_receipt_reaches_fake_harness_audit_and_nameless_debug_view():
    """Fold names survive the audit and card projection while the adapter remains unused."""
    text = BY_ID["grok-r2-leet-die-001"]["text"]
    audit_log, adapter = AuditLog(), FakeAdapter()
    harness = Harness(load_roster(), adapter, CodexStore(), audit_log=audit_log)
    turn = harness.speak(text)
    assert turn.action == "HUMAN_ESCALATION"
    assert turn.adapter_calls == 0 and adapter.calls == []
    row = audit_log.read(turn.row_id)
    assert row is not None and row["user_text"] == text
    assert row["decision"]["safety"]["screen_folds"] == ["lookalikes"]
    public = _card_decision(row["decision"])
    assert public["safety"]["screen_folds"] == ["lookalikes"]
    assert "Screen read a folded copy: lookalikes" in public["explain"]
    assert public["agent_id"] is None
    assert public["shadow_agent_id"] is None


def test_unchanged_control_has_an_empty_fold_receipt():
    """An existing everyday identifier control reports no fold when its copy is unchanged."""
    controls = json.loads((ROOT / "evals/gap_triage/digit_token_controls_2026-10-05.json").read_text(encoding="utf-8"))
    text = controls["cases"][0]["text"]
    norm = normalize(text)
    assert screen_fold(norm) == (norm, ())
    assert crisis_screen(text).screen_folds == ()
    assert route(text, load_roster()).safety.action is not Action.HUMAN_ESCALATION


@pytest.mark.parametrize("transform,case_id", EXTRA_STUTTERS)
def test_authorized_extra_stutter_variants_keep_the_card(transform, case_id):
    """The 22 extra stutter misses found during replay now retain their existing labelled card."""
    text = TRANSFORMS[transform](BY_ID[case_id]["text"])
    decision = route(text, load_roster())
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert "stutter" in decision.safety.screen_folds


@pytest.mark.parametrize("transform", (
    "middle_word_repeated_with_comma", "uh_before_the_last_word", "first_long_word_syllable_stuttered",
))
def test_authorized_extra_stutters_do_not_card_digit_controls(transform):
    """Stuttering each of the 40 existing identifier controls still causes no crisis card."""
    controls = json.loads((ROOT / "evals/gap_triage/digit_token_controls_2026-10-05.json").read_text(encoding="utf-8"))
    roster = load_roster()
    for case in controls["cases"]:
        text = TRANSFORMS[transform](case["text"])
        assert route(text, roster).safety.action is not Action.HUMAN_ESCALATION, case["id"]
