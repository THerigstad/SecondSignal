"""Order G1: proximity masks yield, exact idioms and monitor input stay pinned."""

from __future__ import annotations

import json
from dataclasses import replace
from unittest.mock import patch

import pytest
import test_crisis_gate as gate
import test_operator_live_test as live
from test_lexicon import WINDOW_MASK_FIXTURES

from evals.fuzz.measure_splice import (
    MEASUREMENT,
    SPLICES,
    before_context,
    hit_erasing_masks,
    labelled_cases,
    splice,
)
from evals.fuzz.run import _session
from secondsignal import Action, SessionState, load_roster, route, safety
from secondsignal.cli import main as cli_main
from secondsignal.lexicon import PACKS, apply_masks, load_pack
from secondsignal.normalize import normalize
from secondsignal.safety import MASK_PROTECTED_PATTERNS, crisis_screen


def test_splice_guard_keeps_every_labelled_card_except_recorded_gate_exclusions():
    """Every current single-message card survives each splice unless the data names its exclusion."""
    data = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    exceptions = {(r["id"], r["position"], r["phrase"]) for r in data["gate_exclusions"]}
    assert all(r["reason"] != "unclassified_exclusion" and not r["hit_erasing_mask_ids"]
               for r in data["gate_exclusions"])
    roster = load_roster()
    observed = set()
    for _, case in labelled_cases():
        if case.get("prior_turns") or case.get("expect", {}).get("safety") != "HUMAN_ESCALATION":
            continue
        if route(case["text"], roster, session=_session(case)).safety.action is not Action.HUMAN_ESCALATION:
            continue
        for position, phrase in SPLICES:
            text = splice(case["text"], position, phrase)
            decision = route(text, roster, session=_session(case))
            key = (case["id"], position, phrase)
            if key in exceptions:
                observed.add(key)
                assert decision.safety.action is not Action.HUMAN_ESCALATION, key
            else:
                assert decision.safety.action is Action.HUMAN_ESCALATION, key
    assert observed == exceptions


def test_protected_span_names_the_window_attempt_and_retains_its_offsets():
    case = next(c for _, c in labelled_cases() if c["id"] == "fuzz-one-letter-dropped-direct-ideation-001")
    screen = crisis_screen(case["text"])
    spans = [span for span in screen.masked_spans if span.kind == "protected"]
    assert spans and {s.pattern_id for s in spans} == {"game_jump"}
    assert all(screen.masked[s.start:s.end] == s.text and s.pack == "en" and s.domain == "crisis"
               for s in spans)


def test_exact_idiom_keeps_its_measured_exemption_from_matching_hit_classes():
    mark = next(m for m in live.test_idioms_and_named_objects_are_masked_before_the_lexicon_runs.pytestmark
                if m.name == "parametrize")
    text, mask_id = mark.args[1][1]
    norm = normalize(text)
    assert any(p.search(norm) for p in MASK_PROTECTED_PATTERNS)
    assert mask_id not in PACKS["en"].yields_to_gate
    masked, spans = apply_masks(norm, crisis_only=True, protect=MASK_PROTECTED_PATTERNS)
    assert masked != norm
    assert any(s.pattern_id == mask_id and s.kind == "mask" for s in spans)
    assert crisis_screen(text).read == "MISS"


def test_proximity_regex_yields_and_records_its_attempt():
    screen = crisis_screen(gate.CONTROLS[14])
    assert screen.read == "HIT"
    assert any(s.pattern_id == "game_death" and s.kind == "protected" for s in screen.masked_spans)
    with before_context():
        assert crisis_screen(gate.CONTROLS[14]).read == "MISS"


WINDOWS = [(pack_id, mask_id, pos) for pack_id, masks in WINDOW_MASK_FIXTURES.items()
           for mask_id, (pos, _) in masks.items()]


@pytest.mark.parametrize("pack_id,mask_id,positive", WINDOWS, ids=[f"{p}:{m}" for p,m,_ in WINDOWS])
def test_positive_windows_keep_masking_or_yield_to_the_matching_hit(pack_id, mask_id, positive):
    norm = normalize(positive)
    masked, spans = apply_masks(norm, protect=MASK_PROTECTED_PATTERNS)
    own_hits = tuple(pattern for pack in PACKS.values() for _, _, pattern in pack.hits)
    if any(p.search(norm) for p in MASK_PROTECTED_PATTERNS + own_hits):
        assert any(s.pattern_id == mask_id and s.kind == "protected" for s in spans)
    else:
        assert any(s.pattern_id == mask_id and s.kind == "mask" for s in spans)
        assert masked != norm


def test_negated_work_form_keeps_the_three_token_exception():
    text = "I don't want to die in this meeting"
    _, spans = apply_masks(normalize(text), protect=MASK_PROTECTED_PATTERNS)
    assert any(s.pattern_id == "negated_die_with_work_object" and s.kind == "mask" for s in spans)
    assert crisis_screen(text).read == "MISS"


def test_present_desire_protection_still_holds_without_caller_protection():
    text = WINDOW_MASK_FIXTURES["en"]["labor_die"][1] + " with the boss"
    masked, spans = apply_masks(normalize(text), protect=None)
    assert masked == normalize(text)
    assert not spans
    assert crisis_screen(text).read == "HIT"


def test_empty_tuple_enables_pack_hits_and_none_preserves_the_old_input():
    text = WINDOW_MASK_FIXTURES["es-419"]["muero_object"][0]
    norm = normalize(text)
    legacy, old = apply_masks(norm, protect=None)
    current, new = apply_masks(norm, protect=())
    assert legacy != norm and any(s.kind == "mask" for s in old)
    assert current == norm and any(s.kind == "protected" and s.pattern_id == "muero_object" for s in new)
    assert crisis_screen(text).read == "HIT"


def test_pack_inconclusive_read_remains_maskable():
    text = WINDOW_MASK_FIXTURES["es-419"]["matando_trabajo"][0]
    norm = normalize(text)
    assert any(p.search(norm) for _,p in PACKS["es-419"].inconclusive)
    _, spans = apply_masks(norm, protect=())
    assert any(s.pattern_id == "matando_trabajo" and s.kind == "mask" for s in spans)
    assert crisis_screen(text).read == "MISS"


@pytest.mark.parametrize("flag", [None, 0, 1, "false", [], {}], ids=["missing", "zero", "one", "string", "list", "object"])
def test_regex_mask_requires_an_explicit_boolean(tmp_path, flag):
    entry = {"id":"ordinary", "pattern":"ordinary"}
    if flag is not None:
        entry["yields_to_gate"] = flag
    path = tmp_path / "pack.json"
    path.write_text(json.dumps({"pack":"test", "regex_masks":[entry]}), encoding="utf-8")
    with pytest.raises(ValueError, match="yields_to_gate must be a boolean"):
        load_pack(path)


def test_only_the_four_reviewed_english_regex_masks_yield():
    assert PACKS["en"].yields_to_gate == {"game_death", "device_died", "character_died", "dead_compound"}
    assert PACKS["es-419"].yields_to_gate == frozenset()


def test_monitors_omit_protection_and_keep_every_manifest_input_byte_identical():
    legacy_packs = tuple(replace(p, yields_to_gate=frozenset()) for p in PACKS.values())
    for _, case in labelled_cases():
        texts = [p["text"] if isinstance(p,dict) else p for p in case.get("prior_turns", [])] + [case["text"]]
        session = SessionState()
        for text in texts:
            norm = safety._normalize(text)
            assert apply_masks(norm) == apply_masks(norm, protect=None) == apply_masks(norm, legacy_packs)
            with patch.object(safety, "apply_masks", wraps=apply_masks) as observed:
                session.observe(text)
            observed.assert_called_once_with(norm)


def test_protected_kind_survives_verdict_serialization_explain_and_cli(capsys):
    text = gate.CONTROLS[14]
    decision = route(text, load_roster())
    record = decision.to_dict()
    assert any(s["kind"] == "protected" for s in record["safety"]["masked_spans"])
    assert "game_death" in decision.explain()
    assert cli_main([text, "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert any(s["kind"] == "protected" for s in output["safety"]["masked_spans"])


def test_measurement_has_no_remaining_protected_hit_erasure():
    data = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    assert [(r["position"], r["phrase"]) for r in data["splices"]] == list(SPLICES)
    assert any(f["hit_erasing_mask_ids"] for r in data["splices"] for f in r["before"]["flips"])
    for row in data["splices"]:
        for phase in ("before", "after"):
            actions = row[phase]["actions"]
            assert set(actions) == set(data[phase]["eligible_ids"])
            assert {ident for ident, action in actions.items() if action != "HUMAN_ESCALATION"} == {
                flip["id"] for flip in row[phase]["flips"]
            }
        assert row["before"]["count"] == len(row["before"]["flips"])
        assert row["after"]["count"] == len(row["after"]["flips"])
        assert not any(f["hit_erasing_mask_ids"] for f in row["after"]["flips"])
    by_id = {case["id"]:case for _,case in labelled_cases()}
    for row in data["gate_exclusions"]:
        text = splice(by_id[row["id"]]["text"], row["position"], row["phrase"])
        assert not hit_erasing_masks(text, crisis_screen(text)), row["id"]
