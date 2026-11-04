"""G2B5B: replay the frozen full before-run cohorts through plain production.

One permanent test per B5b install. Successful look-alike variants omitted by
measure_rest are retained in the observational before-cohort manifest, keyed
by source case, replacement offset and source code point. No candidate wrapper
is applied by these tests; the installed production pipeline must do the work.
"""
from __future__ import annotations

import hashlib
import json
import string
from collections import Counter, defaultdict
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from evals.fuzz import confusables
from evals.fuzz import measure_causes as b1
from evals.gap_triage import measure_cheap
from evals.gap_triage.generate_second_broom_data import (
    generate_confusables_bytes,
    generate_crisis_bytes,
    generate_everyday_bytes,
    generate_reviewed_remainder_bytes,
)
from secondsignal import load_roster
from secondsignal.normalize import SKELETON

ROOT = Path(__file__).resolve().parents[1]
MEASUREMENTS = ROOT / "evals/gap_triage/measurements"
BEFORE_PATH = MEASUREMENTS / "second_broom_before_2026-11-04.json"
COHORT_PATH = MEASUREMENTS / "second_broom_before_cohorts_2026-11-04.json"
BEFORE_SHA256 = "6d385df25877cf91f7cc168466381607c34137665852aac81d88a86d4fa1337c"
COHORT_SHA256 = "2ff28f279ccfbed5771ec2f12dcdf287d5823279254b7ba9f8f87414f9b57431"
MAP_SHA256 = "95d10e9b4fc0d98fbd4a2555efb7b4a2806863f6641472b9c5c31467430f1f9f"
BEFORE = json.loads(BEFORE_PATH.read_text(encoding="utf-8"))
COHORT = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
CARD = "HUMAN_ESCALATION"
THREE_CONTROLS = ("literal_three_lists", "historical_policy_proceed", "policy_proceed")
CONTROL_FIELDS = (
    "safety", "outcome", "agent", "assist", "held", "seat_claim",
    "claim_subject", "obligations", "latch",
)


@lru_cache(maxsize=1)
def _roster():
    return load_roster()


@lru_cache(maxsize=1)
def _cases() -> dict[str, dict[str, Any]]:
    # Read the unchanged reviewer cases to preserve expectations, asks, locale
    # and prior turns, including cases no longer dispositioned as known gaps.
    return {case["id"]: case for _, case in measure_cheap.case_runner.CASES}


@lru_cache(maxsize=1)
def _historical() -> dict[str, dict[str, Any]]:
    rows = COHORT["historical_crisis_lines"]
    by_id = {case["id"]: case for case in rows}
    assert len(by_id) == len(rows), "duplicate historical crisis case ID"
    return by_id


@cache
def _observe_serialized(serialized: str) -> dict[str, Any]:
    # candidate=None is deliberate: only production is allowed to recover.
    return measure_cheap.run_one(json.loads(serialized), _roster())


def _observe(case: dict[str, Any]) -> dict[str, Any]:
    return _observe_serialized(json.dumps(case, sort_keys=True, ensure_ascii=False))


@cache
def _fuzz_observe(case_id: str, text: str) -> dict[str, Any]:
    # Same original session/prior-turn replay as the measured fuzz, without
    # candidate_scope or any input-rewriting test wrapper.
    return b1.observe(_historical()[case_id], text, _roster())


def _group(name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key = COHORT["control_groups"][name]
    return COHORT["controls"][key], COHORT["control_baseline"][key]


def _assert_controls(names: tuple[str, ...], *, measured_recovery: bool = False) -> None:
    for name in names:
        cases, before = _group(name)
        assert [case["id"] for case in cases] == [row["id"] for row in before]
        reference = BEFORE["candidates"]["guarded_one_letter"]["controls"][name]
        assert len(cases) == reference["total"], name
        expected_cards = {row["id"] for row in before if row["safety"] == CARD}
        assert len(expected_cards) == reference["baseline_false_alarms"], name
        actual = [_observe(case) for case in cases]
        assert {row["id"] for row in actual if row["safety"] == CARD} == expected_cards, name
        if measured_recovery:
            differences = {
                old["id"]: {
                    field: (old[field], new[field]) for field in CONTROL_FIELDS
                    if old[field] != new[field]
                }
                for old, new in zip(before, actual)
                if any(old[field] != new[field] for field in CONTROL_FIELDS)
            }
            measured = BEFORE["candidates"]["narrowed_recovery_routing_experiment"]["controls"][name]
            expected = {
                change["id"]: {field: (values["before"], values["after"])
                               for field, values in change["differences"].items()}
                for change in measured["decision_changes"]
            }
            assert differences == expected, (name, differences)  # G2B5B part 5: old {} -> exact measured deltas; the five required recoveries are also PROCEED controls.


def _assert_retention(*, current: bool = False) -> None:
    name = "current_crisis_lines" if current else "historical_crisis_lines"
    report_key = "extended_current_card_retention" if current else "real_card_retention"
    reference = BEFORE["candidates"]["corrected_confusables"][report_key]
    cases = COHORT[name]
    assert len(cases) == reference["total"]
    assert reference["cards_lost"] == 0
    lost = [case["id"] for case in cases if _observe(case)["safety"] != CARD]
    assert lost == [], lost


def _variant_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return row["id"], row["source"], row["replacement_index"]


def _variant_id(key: tuple[str, str, int]) -> str:
    case_id, source, index = key
    return f"{case_id}::U+{ord(source):04X}@{index}"


def _assert_confusables_cohort() -> dict[tuple[str, str, int], bool]:
    reference = BEFORE["candidates"]["corrected_confusables"]["fuzz"]
    rows = COHORT["confusables_misses"]
    misses = {_variant_key(row): row["recovered"] for row in rows}
    assert len(misses) == len(rows) == reference["failing_today"]
    assert sum(misses.values()) == reference["recovered"]
    assert {key for key, recovered in misses.items() if not recovered} == {
        _variant_key(row) for row in reference["residuals"]
    }
    # Reconstruct the complete ORIGINAL source enumeration. Using today's
    # expanded SKELETON here would silently shrink the tested denominator.
    sources: dict[str, list[str]] = defaultdict(list)
    for source, target in confusables.full_fold_map().items():
        if source not in COHORT["original_skeleton"]:
            sources[target].append(source)
    groups: dict[str, Counter[str]] = defaultdict(Counter)
    seen_misses: set[tuple[str, str, int]] = set()
    variants = 0
    for case in COHORT["historical_crisis_lines"]:
        positions: dict[str, int] = {}
        for index, character in enumerate(case["text"]):
            if character in string.ascii_letters:
                positions.setdefault(character.casefold(), index)
        for target, index in sorted(positions.items()):
            for source in sources.get(target, ()):
                key = (case["id"], source, index)
                variants += 1
                failing = key in misses
                recovered = failing and misses[key]
                if failing:
                    seen_misses.add(key)
                for group in ("target:" + target, "script:" + confusables.script_from_name(source)):
                    groups[group].update(
                        variants=1, failing_today=int(failing), recovered=int(recovered),
                    )
    assert variants == reference["variants"]
    assert seen_misses == set(misses)
    assert {name: dict(counts) for name, counts in sorted(groups.items())} == reference["summary_groups"]
    return misses


def test_b5b_part_1_guarded_one_letter() -> None:
    """Every before-run recovered/missed typo keeps its measured result."""
    assert hashlib.sha256(BEFORE_PATH.read_bytes()).hexdigest() == BEFORE_SHA256
    assert hashlib.sha256(COHORT_PATH.read_bytes()).hexdigest() == COHORT_SHA256
    assert BEFORE["scope"] == "full"
    guard_path = ROOT / "src/secondsignal/everyday_words.txt"
    assert guard_path.read_bytes() == generate_everyday_bytes()
    assert (ROOT / "src/secondsignal/crisis_words.txt").read_bytes() == generate_crisis_bytes()
    reference = BEFORE["candidates"]["guarded_one_letter"]
    fuzz = reference["fuzz"]
    rows = fuzz["rows"]
    keys = {(row["id"], row["transform"]) for row in rows}
    assert len(keys) == len(rows) == fuzz["failing_today"]
    expected_recovered = {(row["id"], row["transform"]) for row in rows if row["recovered"]}
    assert len(expected_recovered) == fuzz["recovered"]
    actual_recovered = set()
    for row in rows:
        actual = _fuzz_observe(row["id"], row["variant"])
        key = (row["id"], row["transform"])
        if actual["action"] == CARD:
            actual_recovered.add(key)
        assert (actual["action"] == CARD) == row["recovered"], (key, row["variant"], actual)
    assert actual_recovered == expected_recovered
    assert keys - actual_recovered == keys - expected_recovered
    # Pin the documented gap outcomes too; no candidate is run here.
    for row in reference["rows"]:
        case = _cases()[row["id"]]
        assert case["text"] == row["text"]
        actual = _observe(case)
        assert actual["mismatch_fields"] == row["mismatch_fields"], (row["id"], actual)
    _assert_controls(THREE_CONTROLS)
    _assert_retention()
    everyday, _ = _group("recovery_everyday")
    rain = next(case for case in everyday if case["id"] == "recovery-everyday-02")
    actual = _observe(rain)
    assert actual["safety"] == "PROCEED"
    assert actual["route_input"] == rain["text"]


def test_b5b_part_2_corrected_confusables() -> None:
    """All original miss IDs and target/script summaries remain accounted for."""
    path = ROOT / "src/secondsignal/corrected_confusables.json"
    payload = path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == MAP_SHA256
    assert payload == generate_confusables_bytes()
    remainder_path = ROOT / "src/secondsignal/reviewed_skeleton_remainder.json"
    assert remainder_path.read_bytes() == generate_reviewed_remainder_bytes()
    mapping = json.loads(payload)
    assert mapping == SKELETON
    assert len(mapping) == BEFORE["candidates"]["corrected_confusables"]["map"]["candidate_sources"]
    assert not any(source.isascii() for source in mapping)
    misses = _assert_confusables_cohort()
    recovered_ids = set()
    for key, recovered in misses.items():
        case_id, source, index = key
        original = _historical()[case_id]["text"]
        variant = original[:index] + source + original[index + 1:]
        actual = _fuzz_observe(case_id, variant)
        if actual["action"] == CARD:
            recovered_ids.add(_variant_id(key))
        assert (actual["action"] == CARD) == recovered, (_variant_id(key), variant, actual)
    assert recovered_ids == {_variant_id(key) for key, recovered in misses.items() if recovered}
    reference = BEFORE["candidates"]["corrected_confusables"]["fuzz"]
    assert len(misses) - len(recovered_ids) == reference["unrecovered"]
    _assert_controls((*THREE_CONTROLS, "non_latin"))
    _assert_retention()
    _assert_retention(current=True)


def test_b5b_part_3_wider_fold() -> None:
    """Before-run wider gap IDs recover; leading-zero residuals remain open."""
    reference = BEFORE["candidates"]["wider_all"]
    rows = reference["rows"]
    expected_recovered = set(reference["recovered_ids"])
    assert len(rows) == BEFORE["wider_measurement_denominator"]
    assert len(expected_recovered) == reference["recovered"]
    residual_ids = {row["id"] for row in BEFORE["wider_unrecovered"]}
    assert len(residual_ids) == BEFORE["wider_unrecovered_count"]
    assert {row["id"] for row in rows} - expected_recovered == residual_ids
    actual_recovered = set()
    for row in rows:
        case = _cases()[row["id"]]
        assert case["text"] == row["text"]
        actual = _observe(case)
        if actual["safety"] == CARD:
            actual_recovered.add(row["id"])
        assert (actual["safety"] == CARD) == (row["id"] in expected_recovered), (row["id"], actual)
        assert actual["mismatch_fields"] == row["mismatch_fields"], (row["id"], actual)
    assert actual_recovered == expected_recovered
    assert {row["id"] for row in rows} - actual_recovered == residual_ids
    _assert_controls((*THREE_CONTROLS, "digit_tokens"))
    _assert_retention()


def test_b5b_part_4_stutter_retention() -> None:
    """Keep all historical stutters already recovered on this before tree."""
    reference = BEFORE["candidates"]["wider_all"]["stutter_leftovers"]
    rows = reference["rows"]
    assert len(rows) == reference["total"]
    assert sum(row["recovered"] for row in rows) == reference["recovered"]
    for row in rows:
        actual = _fuzz_observe(row["id"], row["variant"])
        assert (actual["action"] == CARD) == row["recovered"], (row["id"], row["transform"], actual)
    # B3 had already recovered the historical nine before this order. The
    # additional before replay prevents a zero-current-leftover test passing
    # vacuously and prevents the new wider folds from undoing B3's recovery.
    historical = COHORT["historical_stutter_before"]
    assert historical
    keys = {(row["id"], row["transform"]) for row in historical}
    assert len(keys) == len(historical)
    expected = {(row["id"], row["transform"]) for row in historical if row["plain_recovered"]}
    actual_recovered = set()
    for row in historical:
        actual = _fuzz_observe(row["id"], row["variant"])
        key = (row["id"], row["transform"])
        if actual["action"] == CARD:
            actual_recovered.add(key)
        assert (actual["action"] == CARD) == row["plain_recovered"], (key, actual)
    assert actual_recovered == expected
    assert keys - actual_recovered == keys - expected
    _assert_controls((*THREE_CONTROLS, "digit_tokens"))
    _assert_retention()


def test_b5b_part_5_narrowed_recovery() -> None:
    """Recover the measured five frames and release every everyday control."""
    reference = BEFORE["candidates"]["narrowed_recovery_routing_experiment"]
    expected_recovered = set(reference["recovered_ids"])
    assert len(expected_recovered) == reference["recovered"]
    actual_recovered = set()
    residual_ids = set()
    for row in reference["rows"]:
        case = _cases()[row["id"]]
        assert case["text"] == row["text"]
        actual = _observe(case)
        if not actual["mismatch_fields"]:
            actual_recovered.add(row["id"])
        else:
            residual_ids.add(row["id"])
        assert actual["mismatch_fields"] == row["mismatch_fields"], (row["id"], actual)
        for field in ("safety", "crisis_read", "outcome", "agent", "held", "seat_claim", "claim_subject"):
            assert actual[field] == row[field], (row["id"], field, row[field], actual[field])
    assert actual_recovered == expected_recovered
    assert residual_ids == {row["id"] for row in reference["rows"]} - expected_recovered
    everyday, _ = _group("recovery_everyday")
    release = reference["everyday_release"]
    assert {case["id"] for case in everyday} == {row["id"] for row in release["rows"]}
    assert len(everyday) == release["total"] == release["released"]
    for case in everyday:
        actual = _observe(case)
        assert actual["safety"] == "PROCEED", (case["id"], actual)
        assert actual["seat_claim"] != "addiction_recovery", (case["id"], actual)
        assert "addiction_recovery" not in actual["held"], (case["id"], actual)
    _assert_controls(THREE_CONTROLS, measured_recovery=True)
