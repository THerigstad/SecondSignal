"""The sentences that leave the repository are written from the snapshot, and this holds them there.

Five places on the operator's LinkedIn profile state the tree's numbers. They
were retyped by hand after each landing and fell behind the tree three times
(``docs/confessions.md``, C-35). ``evals/refresh_public_sentences.py`` now
renders them from ``evals/public-numbers.json`` into
``evals/public-sentences.md``, the file a person pastes from. Nothing in the
tree reaches LinkedIn; what can be held is that the file never disagrees with
the snapshot, and that is held here:

* the committed file is what the snapshot renders, byte for byte, for the date
  the file itself states;
* every sentence carries the snapshot's test count, and the record sentence
  carries the passing count, the gaps, the dissents, the cases and the
  external fixtures;
* on a copy, a wrong digit in any sentence is caught and rewritten, and a file
  without a date stops the script rather than being guessed at.

``tests/test_public_numbers.py`` holds the snapshot to the tree, so the chain
from pytest's collection to the pasted sentence has no typed link.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
from pathlib import Path

import pytest

from evals import refresh_public_sentences as sentences

RELATIVE = sentences.SENTENCES_PATH.relative_to(sentences.ROOT).as_posix()
SNAPSHOT_RELATIVE = sentences.SNAPSHOT_PATH.relative_to(sentences.ROOT).as_posix()


@pytest.fixture(scope="module")
def snapshot() -> sentences.Numbers:
    return sentences.read_snapshot()


@pytest.fixture(scope="module")
def as_of() -> str:
    return sentences.read_as_of()


@pytest.fixture()
def tree_copy(tmp_path: Path) -> Path:
    """The sentences file and the snapshot, copied where a test may corrupt them."""
    for relative in (RELATIVE, SNAPSHOT_RELATIVE):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sentences.ROOT / relative, target)
    return tmp_path


def test_the_file_is_what_the_snapshot_renders(snapshot: sentences.Numbers, as_of: str) -> None:
    current, rendered = sentences.compare(snapshot, as_of)
    assert current == rendered, (
        f"{RELATIVE} no longer matches {SNAPSHOT_RELATIVE}. "
        "Run: python evals/refresh_public_sentences.py --write --as-of <the landing's date>"
    )


def test_every_sentence_carries_the_snapshot_numbers(snapshot: sentences.Numbers, as_of: str) -> None:
    text = sentences.SENTENCES_PATH.read_text(encoding="utf-8")
    found = sentences.sections(text)
    assert sorted(found) == [1, 2, 3, 4, 5]
    tests = f"{snapshot['tests']:,} tests"
    for number, sentence in found.items():
        assert tests in sentence, f"sentence {number} does not say {tests!r}"
    record = found[3]
    assert record.startswith(f"On the record as of {as_of}: ")
    assert f"({snapshot['tests'] - snapshot['expected_failures']:,} passing, " in record
    assert f"{snapshot['documented_gaps']} documented gaps" in record
    assert f"{snapshot['recorded_dissents']} recorded dissents" in record
    assert f"{snapshot['cases']} evaluation cases" in record
    assert f"{snapshot['external_fixtures']} of them fixtures" in record


def test_the_passing_count_is_collected_minus_expected_failures(snapshot: sentences.Numbers) -> None:
    assert sentences.passing(snapshot) == snapshot["tests"] - snapshot["expected_failures"]
    assert sentences.passing({"tests": 3637, "expected_failures": 178}) == 3459


def test_the_date_is_the_profile_form_without_a_leading_zero() -> None:
    assert sentences.long_date(dt.date(2026, 10, 7)) == "7 October 2026"
    assert sentences.long_date(dt.date(2026, 11, 23)) == "23 November 2026"
    assert sentences.parse_as_of("2026-10-07") == "7 October 2026"
    with pytest.raises(Exception, match="YYYY-MM-DD"):
        sentences.parse_as_of("7 October 2026")


def test_a_wrong_digit_in_any_sentence_is_caught_and_rewritten(
    snapshot: sentences.Numbers, as_of: str, tree_copy: Path
) -> None:
    """Mutation proof, on the copy: corrupt one digit of each sentence in turn."""
    page = tree_copy / RELATIVE
    original = page.read_text(encoding="utf-8")
    for number, sentence in sentences.sections(original).items():
        corrupted = re.sub(r"\d", lambda m: str((int(m.group()) + 1) % 10), sentence, count=1)
        assert corrupted != sentence, number
        page.write_text(original.replace(sentence, corrupted, 1), encoding="utf-8")

        current, rendered = sentences.compare(snapshot, as_of, tree_copy)
        assert current != rendered, f"corrupting sentence {number} was not noticed"
        stale = [n for n, s in sentences.sections(current).items() if s != sentences.sections(rendered)[n]]
        assert stale == [number], f"corrupting sentence {number} was reported as {stale}"

        assert sentences.write(snapshot, as_of, tree_copy) is True
        assert page.read_text(encoding="utf-8") == original, f"sentence {number} was not restored byte for byte"
    assert sentences.write(snapshot, as_of, tree_copy) is False


def test_moved_numbers_make_the_file_stale(as_of: str, tree_copy: Path) -> None:
    moved = dict(sentences.read_snapshot(tree_copy))
    moved["tests"] += 1
    current, rendered = sentences.compare(moved, as_of, tree_copy)
    stale = [n for n, s in sentences.sections(current).items() if s != sentences.sections(rendered)[n]]
    assert stale == [1, 2, 3, 4, 5]


def test_a_file_without_a_date_stops_the_script_instead_of_being_guessed(tree_copy: Path) -> None:
    page = tree_copy / RELATIVE
    page.write_text(page.read_text(encoding="utf-8").replace("As of: ", "From: ", 1), encoding="utf-8")
    with pytest.raises(LookupError, match="pass --as-of"):
        sentences.read_as_of(tree_copy)
    page.unlink()
    with pytest.raises(LookupError, match="does not exist yet"):
        sentences.read_as_of(tree_copy)
