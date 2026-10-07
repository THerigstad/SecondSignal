"""Order R1M: provenance, redaction, and an offline read-only measurement."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from evals.vocabulary import measure_vocabulary_candidates as measure

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def vocabulary():
    return json.loads(measure.INPUT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def measured(tmp_path_factory):
    destination = tmp_path_factory.mktemp("r1m") / "report.json"
    before = measure.source_snapshot()
    # Audit actual writes, including transient writes restored before a hash check.
    probe = r'''
import os, runpy, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
def guard(event, args):
    writing = False
    targets = ()
    if event == "open":
        mode, flags = args[1], args[2]
        writing = (isinstance(mode, str) and any(x in mode for x in "wax+")) or (
            isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)))
        targets = args[:1]
    elif event in {"os.remove", "os.rmdir", "os.mkdir", "os.rename", "os.chmod", "os.utime"}:
        writing = True
        targets = args[:2] if event == "os.rename" else args[:1]
    if writing:
        for target in targets:
            if isinstance(target, (str, bytes, os.PathLike)):
                path = Path(os.fsdecode(target)).resolve()
                if path.is_relative_to(root / "src"):
                    raise AssertionError("measurement tried to write under src")
sys.addaudithook(guard)
destination = sys.argv[2]
sys.argv = ["measure_vocabulary_candidates.py", "--output", destination]
runpy.run_path(str(root / "evals/vocabulary/measure_vocabulary_candidates.py"), run_name="__main__")
'''
    result = subprocess.run(
        [sys.executable, "-B", "-c", probe, str(ROOT), str(destination)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "PIP_NO_INDEX": "1"},
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert destination.is_file()
    assert before == measure.source_snapshot()
    return json.loads(destination.read_text(encoding="utf-8")), result.stdout


def test_merged_vocabulary_has_complete_valid_records(vocabulary):
    measure.validate(vocabulary)
    assert measure.INPUT.stat().st_size < 2_000_000


def test_sources_count_doors_once_and_preserve_uncited_status(vocabulary):
    for row in vocabulary:
        assert row["sources"]
        assert row["systems"] == len({source["door"] for source in row["sources"]})
        if not any(source["citation"] for source in row["sources"]):
            assert "uncited" in row["note"].lower()


def test_withheld_records_cannot_contain_headwords_variants_or_definitions(vocabulary):
    withheld = [row for row in vocabulary if row["proposed_use"] == "withheld_from_tree"]
    assert withheld
    for row in withheld:
        assert row["term"].startswith("a ") and "(withheld " in row["term"]
        assert row["variants"] == []
        assert row["meaning"] == measure.WITHHELD_MEANING
    for field, bad in (("term", "unredacted spelling"), ("variants", ["unredacted spelling"]),
                       ("meaning", "unredacted definition")):
        corrupted = copy.deepcopy(withheld[0])
        corrupted[field] = bad
        with pytest.raises(ValueError, match="Withheld"):
            measure.validate([corrupted])


def test_already_carried_terms_are_never_proposed_again(vocabulary):
    import re
    import unicodedata

    from secondsignal.signals import (
        DOMAIN_LEXICON,
        DYSREGULATION_MARKERS,
        IDENTITY_STATEMENT_TERMS,
    )

    def fold(value):
        value = unicodedata.normalize("NFKC", value).casefold().replace("’", "'")
        return re.sub(r"[\s\-\u2010-\u2015]+", "", value).strip('"“”')

    canonical = {fold(term) for term in IDENTITY_STATEMENT_TERMS}
    for category in ("addiction_recovery", "identity", "neurodivergence"):
        canonical.update(fold(term) for term in DOMAIN_LEXICON[category])
    markers = {fold(term) for term in DYSREGULATION_MARKERS}
    attested = canonical | markers | {
        fold(term) for row in vocabulary for term in (row["term"], *row["variants"])
    }

    def singular(value):
        if value.endswith("ies") and value[:-3] + "y" in attested:
            return value[:-3] + "y"
        if value.endswith("s") and not value.endswith(("ss", "us", "is", "ics")):
            if value[:-1] in attested:
                return value[:-1]
        return value

    canonical = {singular(term) for term in canonical}
    markers = {singular(term) for term in markers}
    nd_path = "evals/cases/neurodivergent_grok_2026-09-30.json"
    nd_cases = json.loads((ROOT / nd_path).read_text(encoding="utf-8"))["cases"]
    nd_texts = [case["text"] for case in nd_cases
                if case.get("expect", {}).get("safety") == "PROCEED"]

    # Read the policy and fixtures independently: missing metadata must fail too.
    for row in vocabulary:
        terms = [row["term"], *row["variants"]]
        normalized = {singular(fold(term)) for term in terms}
        carrying_files = set()
        if normalized & canonical:
            carrying_files.add("src/secondsignal/signals.py")
        if row["category"] == "neurodivergence":
            if normalized & markers or any(term.startswith("rejectionsensitiv")
                                           for term in normalized):
                carrying_files.add("src/secondsignal/signals.py")
            if any(measure.phrase_pattern(term).search(text)
                   for term in terms for text in nd_texts):
                carrying_files.add(nd_path)
        if carrying_files:
            assert row["already_carried"] in carrying_files, row["term"]
            assert row["proposed_use"] != "recognise", row["term"]

    carried = [row for row in vocabulary if row["already_carried"]]
    assert carried
    for row in carried:
        assert (ROOT / row["already_carried"]).is_file()
        assert row["proposed_use"] != "recognise"
    corrupted = copy.deepcopy(carried[0])
    corrupted["proposed_use"] = "recognise"
    with pytest.raises(ValueError, match="Already-carried"):
        measure.validate([corrupted])


def test_schema_rejects_missing_fields_invalid_enums_and_wrong_counts(vocabulary):
    for field, bad in (("category", "invented"), ("proposed_use", "install"),
                       ("agreement", "certain"), ("systems", 99)):
        corrupted = copy.deepcopy(vocabulary[0])
        corrupted[field] = bad
        with pytest.raises(ValueError):
            measure.validate([corrupted])
    corrupted = copy.deepcopy(vocabulary[0])
    del corrupted["meaning"]
    with pytest.raises(ValueError):
        measure.validate([corrupted])


def test_measurement_cli_runs_on_complete_file_and_writes_report(measured, vocabulary):
    report, output = measured
    expected = {r["term"] for r in vocabulary if r["proposed_use"] in {"recognise", "never_alarm"}}
    assert {r["term"] for r in report["candidates"]} == expected
    assert report["summary"]["measured_terms"] == len(expected)
    assert "Source files unchanged: yes" in output
    for row in report["candidates"]:
        assert len(row["neutral_carriers"]) == 3
        assert all(carrier["text"] == pattern.format(term=row["term"])
                   for carrier, pattern in zip(row["neutral_carriers"], measure.CARRIERS))
        assert {"term_alone", "neutral_carriers", "pack_matches", "control_occurrences",
                "recovery_alias_dry_run"} <= row.keys()


def test_measurement_matches_saved_report_without_source_writes(measured):
    report, _ = measured
    assert report["source_files_unchanged"]
    assert report == json.loads(measure.OUTPUT.read_text(encoding="utf-8"))


def test_output_under_src_is_refused_before_a_write():
    target = ROOT / "src/r1m_must_not_exist.json"
    assert not target.exists()
    with pytest.raises(ValueError, match="under src is forbidden"):
        measure.main(["--output", str(target)])
    assert not target.exists()


def test_controls_include_all_b3_b5b_corpora_and_whole_phrase_boundaries():
    controls = measure.load_controls()
    counts = {name: sum(c["group"] == name for c in controls) for name in (
        "literal_three_lists", "policy_proceed", "digit_tokens", "recovery_everyday", "non_latin",
    )}
    assert counts == {"literal_three_lists": 43, "policy_proceed": 260,
                      "digit_tokens": 40, "recovery_everyday": 8, "non_latin": 30}
    assert not measure.phrase_pattern("trans").search("transferring")
    assert measure.phrase_pattern("non-binary").search("non binary")


def test_absent_alias_support_is_unknown_not_a_false_clean_result(measured):
    report, _ = measured
    recovery = [row for row in report["candidates"] if row["category"] == "recovery"
                and row["proposed_use"] == "recognise"]
    assert recovery
    for row in recovery:
        dry_run = row["recovery_alias_dry_run"]
        assert dry_run["status"] == "unavailable"
        assert dry_run["collides"] is None and dry_run["collisions"] is None
        assert row["assessment"] != "clean"


def test_pack_scope_distinguishes_masks_from_crisis_patterns():
    matches = measure.pack_matches(["AA batteries"])
    assert any(m["pack"] == "en" and m["kind"] == "mask"
               and m["scope"] == "all_screens" for m in matches)
    # Reuse an existing labelled fixture, never author crisis text for R1M.
    cases = json.loads((ROOT / "evals/cases/safety_gate.json").read_text(encoding="utf-8"))["cases"]
    text = next(c["text"] for c in cases if c["id"] == "crisis-direct")
    assert measure.screen(text)["alarm"] is True
    assert measure.screen("The workshop starts at noon.")["alarm"] is False
