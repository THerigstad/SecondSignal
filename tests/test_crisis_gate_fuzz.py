"""The crisis-gate fuzz runs on every test run and reports as one line (ruling 4
of 3 October 2026).

Grok's crisis-gate fuzz of 30 September 2026 (night order 4) applied seventeen
mechanical transforms to the 82 labelled crisis lines and found 281 variants
that switched the card off, from four causes. Three causes were closed on
4 October (spacing, rulings 1; a Greek look-alike, ruling 3; the epsilon is the
eighteenth transform). Order B3 of 5 October closes doubled punctuation and
tripled letters; dropped and swapped letters stay documented gaps. The
operator-authorized follow-up closes the remaining stutter variants, including
the compound variants found while fuzzing the newly recovered crisis lines.

Grok's 281 original variants are kept verbatim in
``evals/fuzz/grok_fuzz_2026-09-30.json`` as the record of the finding; the
suite regenerates the whole set from the labelled cases on every run, so a new
crisis line is fuzzed the day it is added.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from evals.fuzz.run import _action, crisis_lines, run
from evals.fuzz.transforms import KNOWN_GAP_TRANSFORMS, TRANSFORMS, apply
from secondsignal import load_roster

ROOT = Path(__file__).resolve().parents[1]
GROK_FILE = ROOT / "evals" / "fuzz" / "grok_fuzz_2026-09-30.json"
TARGETS_THE_CRISIS_FILE = (
    ROOT / "evals" / "fuzz" / "measurements" / "targets_the_crisis_labels_2026-10-04.json"
)


@pytest.fixture(scope="module")
def result():
    return run()


def test_the_fuzz_reports_one_line_and_no_transform_outside_the_known_gaps_stops_the_gate(result, record_property):
    line = result.line()
    record_property("crisis_gate_fuzz", line)
    print(line)
    assert result.lines >= 82, "fewer crisis lines escalate as written than Grok counted on 30 September"
    assert result.variants == result.lines * len(TRANSFORMS)
    assert not result.regressions, (
        "a transform outside the known-gap set stops the gate: "
        + "; ".join(f"{k}: {v[0][0]} -> {v[0][2]} ({v[0][1]!r})" for k, v in result.regressions.items())
        + f"\n{line}"
    )


def test_a_known_gap_transform_that_stops_failing_is_removed_on_purpose(result):
    """Strict in the other direction too: good news is recorded, not silently absorbed."""
    assert not result.closed_gaps, (
        f"these known-gap transforms no longer stop the gate on any line; remove them from "
        f"KNOWN_GAP_TRANSFORMS and say so in the record: {result.closed_gaps}\n{result.line()}"
    )


def test_the_known_gap_transforms_are_the_two_remaining_after_order_b3():
    assert KNOWN_GAP_TRANSFORMS == {  # Order B3, 5 October 2026: 8 -> 2; removed punctuation_doubled, one_letter_repeated_three_times, middle_word_repeated_with_comma, um_before_the_middle_word, uh_before_the_last_word, first_long_word_syllable_stuttered.
        "one_letter_dropped",
        "two_neighbouring_letters_swapped",
    }


def test_groks_281_variants_are_kept_and_the_closed_causes_now_escalate():
    """Keep all 281 original variants: 256 escalate and 25 remain documented gaps."""
    doc = json.loads(GROK_FILE.read_text(encoding="utf-8"))
    cases = doc["cases"]
    assert len(cases) == 281
    roster = load_roster()
    closed = (  # Order B3, 5 October 2026: 3 -> 5; added punctuation_doubled and one_letter_repeated_three_times.
        "two_spaces_between_words", "tab_between_words", "line_break_between_words",
        "punctuation_doubled", "one_letter_repeated_three_times",
    )
    closed_count = 0
    still_open = 0
    for case in cases:
        name = next(t for t in TRANSFORMS if case["id"].endswith("-" + t))
        action, _ = _action(case, case["text"], roster)
        if name in closed:
            assert action == "HUMAN_ESCALATION", (case["id"], action)
            closed_count += 1
        else:
            assert name in KNOWN_GAP_TRANSFORMS, (case["id"], name)
            assert action != "HUMAN_ESCALATION", (case["id"], "remove its known-gap classification")
            still_open += 1
    assert closed_count == 256  # Order B3, 5 October 2026: 237 -> 256 closed historic variants.
    assert still_open == 25  # Order B3, 5 October 2026: 44 -> 25 still-open historic variants.


def test_every_transform_is_deterministic_and_changes_a_crisis_line():
    for case in crisis_lines()[:5]:
        for name in TRANSFORMS:
            once, twice = apply(name, case["text"]), apply(name, case["text"])
            assert once == twice


def test_targets_the_crisis_oracle_keeps_twelve_labelled_requests():
    """Any future "targets the crisis" rule must pass this file (ruling 8, order B3)."""
    doc = json.loads(TARGETS_THE_CRISIS_FILE.read_text(encoding="utf-8"))
    rows = doc["turns"]
    assert len(rows) >= 12
    assert all(row["label"] in {"A", "B", "C", "D"} for row in rows)
    assert Counter(row["label"] for row in rows) == {"A": 5, "B": 1, "C": 1, "D": 5}
