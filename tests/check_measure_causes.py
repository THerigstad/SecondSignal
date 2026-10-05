"""B1 checks run explicitly: python -m pytest -q tests/check_measure_causes.py.

The order reserves public count refreshes for the integrator, so these six new
checks run separately from the pinned default collection. All six must pass;
none is skipped. Production policy and existing fixtures stay intact.
"""

from evals.fuzz.measure_causes import (
    collapse_punctuation,
    collapse_tripled_letters,
    control_sets,
    distance_at_most_one,
    extract_vocabulary,
    fold_stutter,
    load_roster,
    measure_fuzz_causes,
    token_risk,
)
from evals.fuzz.run import crisis_lines


def test_distance_one_includes_each_edit_but_not_two_edits():
    for left, right in (("work", "works"), ("works", "work"),
                        ("work", "word"), ("work", "wrok")):
        assert distance_at_most_one(left, right) == 1
    assert distance_at_most_one("work", "work") == 0
    assert distance_at_most_one("work", "walk") is None
    assert distance_at_most_one("work", "worker") is None


def test_candidates_keep_unrequested_changes_out():
    assert collapse_punctuation("Hello!!! $100 $$") == "Hello! $100 $$"
    assert collapse_tripled_letters("Sooo cool; 111") == "So cool; 111"
    assert fold_stutter("Please um repeat, repeat this") == "Please repeat this"
    assert fold_stutter("Please w-w-work here") == "Please w-w-work here"
    assert fold_stutter("The album is on the shelf") == "The album is on the shelf"


def test_control_denominators_and_literal_vocabulary_sources():
    sentences, cases = control_sets()
    assert len(sentences) == 37 and len(cases) == 160
    vocabulary = extract_vocabulary()
    assert vocabulary["count"] == len(set(vocabulary["words"]))
    assert all(word.isalpha() and len(word) >= 3 for word in vocabulary["words"])
    assert "kill" in vocabulary["words"] and "bkill" not in vocabulary["words"]
    assert {s["source"].split(".")[0] for s in vocabulary["sources"]} == {"CRISIS_CLASSES", "en"}


def test_token_risk_counts_occurrences_without_calling_them_cards():
    report = token_risk([{"id": "ordinary", "text": "word work word"}], ["work"])
    assert report["within_one_token_occurrences"] == 3
    assert report["exact_vocabulary_token_occurrences"] == 1
    assert report["new_distance_one_token_occurrences"] == 2
    assert report["new_distance_one_unique_tokens"] == ["word"]


def test_three_labelled_lines_produce_auditable_cause_reports():
    roster = load_roster()
    lines = crisis_lines(roster)[:3]
    sentences, cases = control_sets()
    reports = measure_fuzz_causes(lines, sentences[:3], cases[:3],
                                 extract_vocabulary()["words"], roster)
    assert len(reports) == 5
    for report in reports:
        assert report["lines_tested"] == 3
        assert report["failing_line_count"] <= 3
        assert report["failing_variant_count"] == len(report["failures"])
        assert report["line"] and report["plain_sentence"]
        if report["cause"] in {"dropped letter", "swapped letters"}:
            assert report["recovered_variants"] is None
            assert report["distance_one_risk"]["sentences"]["controls"] == 3
        else:
            assert report["recovered_variants"] == sum(row["recovered"] for row in report["failures"])
            assert report["control_sentences"]["total"] == 3
            assert report["control_cases"]["total"] == 3


def test_full_report_on_three_lines_writes_six_causes_and_verifiable_map(tmp_path):
    import json

    from evals.fuzz.confusables import full_fold, full_fold_map
    from evals.fuzz.measure_causes import run_measurement

    mapping = full_fold_map()
    subset = {character: mapping[character] for character in ("0", "1", "I", "l", "𝐝")}
    # Translation must be simultaneous: the I -> l target must not be re-folded to i.
    assert full_fold("Il", subset) == "li"
    report = run_measurement(lines=crisis_lines()[:3], output_dir=tmp_path,
                             fold_map=subset, include_replays=False)
    saved = json.loads((tmp_path / "causes_2026-10-04.json").read_text(encoding="utf-8"))
    assert saved == report
    assert len(report["causes"]) == 6
    assert report["scope"] == "limited test run"
    assert report["confusables"]["map"]["size"] == 5
    assert report["confusables"]["total_variants"] == len(report["confusables"]["variants"])
    assert report["confusables"]["controls"]["cases"]["baseline_cards"] == 10
    assert report["confusables"]["non_latin"]["total"] == 30
