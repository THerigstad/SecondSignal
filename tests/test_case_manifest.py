"""The case manifest: every labelled evaluation case, inventoried.

Measured on 2026-09-05: an unrelated regression injected into a case that was
already marked ``known_gap`` still came out of the suite as an expected
failure, because the runner xfailed on the first assertion that failed and did
not care which one it was. A suite that absorbs regressions into its expected
failures is not evidence, and this project's whole claim rests on the expected
failures being honest.

``evals/case-manifest.json`` is the fix. It records, for every case, where it
lives, its plane, its disposition, and -- when the case is expected to fail --
exactly which fields it is allowed to fail on. The runner asserts every other
field normally. These tests keep the manifest and the case files in step, so a
case cannot be added, removed, re-dispositioned or quietly widened without the
change being visible in a diff.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from test_eval_cases import CASES, EXPECT_KEYS, field_failures, run_case

from secondsignal import load_roster

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "evals" / "case-manifest.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
ENTRIES = MANIFEST["cases"]
BY_ID = {entry["id"]: entry for entry in ENTRIES}

DISPOSITIONS = frozenset({"accepted", "known_gap", "disputed", "contract_adjusted"})


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _disposition(case: dict) -> str:
    if case.get("known_gap"):
        return "known_gap"
    if case.get("disputed"):
        return "disputed"
    if case.get("contract_adjusted"):
        return "contract_adjusted"
    return "accepted"


def test_the_manifest_has_no_duplicate_ids() -> None:
    counts = Counter(entry["id"] for entry in ENTRIES)
    assert not [i for i, n in counts.items() if n > 1], "duplicate ids in the manifest"


def test_every_case_on_disk_is_in_the_manifest() -> None:
    missing = sorted({case["id"] for _, case in CASES} - set(BY_ID))
    assert not missing, (
        f"{len(missing)} case(s) exist but are not inventoried: {missing[:5]}. "
        "A new case is a deliberate addition; record it in evals/case-manifest.json."
    )


def test_every_manifest_entry_still_exists_on_disk() -> None:
    on_disk = {case["id"] for _, case in CASES}
    removed = sorted(set(BY_ID) - on_disk)
    assert not removed, (
        f"{len(removed)} inventoried case(s) have disappeared: {removed[:5]}. "
        "Deleting a reviewer's case is how a disagreement stops being data."
    )


def test_every_disposition_is_a_known_one() -> None:
    unknown = {e["id"]: e["disposition"] for e in ENTRIES if e["disposition"] not in DISPOSITIONS}
    assert not unknown, unknown


def test_the_manifest_disposition_matches_the_case_file() -> None:
    drifted = {
        case["id"]: (BY_ID[case["id"]]["disposition"], _disposition(case))
        for _, case in CASES
        if case["id"] in BY_ID and BY_ID[case["id"]]["disposition"] != _disposition(case)
    }
    assert not drifted, (
        f"disposition changed without updating the manifest: {drifted}. "
        "Marking a case as a gap, or un-marking one, is a decision with a reason."
    )


def test_the_manifest_plane_matches_the_case_file() -> None:
    drifted = {
        case["id"]: (BY_ID[case["id"]]["plane"], case.get("plane", "policy"))
        for _, case in CASES
        if case["id"] in BY_ID and BY_ID[case["id"]]["plane"] != case.get("plane", "policy")
    }
    assert not drifted, f"plane changed without updating the manifest: {drifted}"


def test_no_case_uses_an_expectation_key_the_runner_cannot_check() -> None:
    """A misspelled key is worse than a missing one: the fixture looks as if it
    asserts something and asserts nothing at all."""
    unknown = {
        f"{label}": sorted(set(case["expect"]) - EXPECT_KEYS)
        for label, case in CASES
        if set(case["expect"]) - EXPECT_KEYS
    }
    assert not unknown, (
        f"expectation keys the runner does not check: {unknown}. "
        "Add the check and the name to EXPECT_KEYS together, or fix the spelling."
    )


def test_every_expected_failure_names_the_fields_it_may_fail_on() -> None:
    silent = [
        e["id"] for e in ENTRIES
        if e["disposition"] in ("known_gap", "disputed") and "mismatch_fields" not in e
    ]
    assert not silent, (
        f"expected-to-fail cases with no approved fields: {silent[:5]}. "
        "An expected failure with no named fields absorbs any regression in that case."
    )


def test_every_expected_failure_carries_a_reason() -> None:
    silent = [
        e["id"] for e in ENTRIES
        if e["disposition"] in ("known_gap", "disputed") and not e.get("reason", "").strip()
    ]
    assert not silent, f"expected-to-fail cases with no recorded reason: {silent[:5]}"


def test_no_approved_mismatch_names_a_field_the_case_does_not_assert() -> None:
    """The manifest may not widen a case beyond what it claims.

    Approving a field the case never asserts is how an inventory quietly turns
    into a blanket permission: the field costs nothing today and absorbs a
    regression tomorrow. An approval is only meaningful against an assertion
    that exists. ``id_order`` is the one runner-level check every case gets
    and is allowed without appearing in ``expect``.
    """
    widened = {}
    for _, case in CASES:
        entry = BY_ID.get(case["id"])
        if not entry or not entry.get("mismatch_fields"):
            continue
        asserted = (set(case["expect"]) & EXPECT_KEYS) | {"id_order"}
        extra = sorted(set(entry["mismatch_fields"]) - asserted)
        if extra:
            widened[case["id"]] = extra
    assert not widened, (
        f"the manifest approves fields these cases never assert: {widened}. "
        "Remove the approval or add the assertion."
    )


def test_an_unrelated_regression_inside_a_gap_fails_instead_of_xfailing(roster) -> None:
    """The behaviour this whole file exists for.

    Take a real expected-to-fail case and inject an expectation it cannot
    meet, standing in for a regression somewhere else in the tree. The runner
    must surface a failing field the manifest has not approved, rather than
    folding it into the expected failure and reporting a green suite.
    """
    gap = next(
        case for _, case in CASES
        if _disposition(case) in ("known_gap", "disputed")
        and case["id"] in BY_ID
        and "agent" not in BY_ID[case["id"]].get("mismatch_fields", [])
    )
    decision, session = run_case(gap, roster)
    approved = set(BY_ID[gap["id"]].get("mismatch_fields", []))

    injected = dict(gap, expect=dict(gap["expect"], agent="__no_such_agent__"))
    bad = field_failures(injected, decision, session)

    assert "agent" in bad, "the injected regression must be detected at all"
    assert set(bad) - approved, (
        "after removing the fields this gap is allowed to fail on, an unapproved "
        "field must remain -- that is what turns the xfail into a red test"
    )
    assert "agent" not in approved, "the injected field must not be pre-approved"


def test_the_same_regression_would_have_been_invisible_before(roster) -> None:
    """The counterfactual, kept as evidence rather than as a story.

    The old runner stopped at the first failing assertion and xfailed on it
    whatever it was. With the fields collected instead, the approved failure
    and the injected one are distinguishable, which is the entire difference.
    """
    gap = next(
        case for _, case in CASES
        if _disposition(case) in ("known_gap", "disputed")
        and case["id"] in BY_ID
        and BY_ID[case["id"]].get("mismatch_fields")
        and "agent" not in BY_ID[case["id"]]["mismatch_fields"]
    )
    decision, session = run_case(gap, roster)
    injected = dict(gap, expect=dict(gap["expect"], agent="__no_such_agent__"))
    bad = field_failures(injected, decision, session)
    approved = set(BY_ID[gap["id"]]["mismatch_fields"])

    assert approved & set(bad), "the case still fails on the field it is supposed to"
    assert set(bad) - approved == {"agent"}, (
        "exactly the injected field is left over once the approved ones are removed"
    )
