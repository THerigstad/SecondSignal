"""The headline numbers on the public pages are written from the tree, and this holds them there.

Release 0.3.0 shipped with the README's tests badge still reading 1,299 while
the page beside it read 1,346. The public-claims test compared the prose to
pytest's collection and never decoded the badge, so the contradiction passed a
green suite and was found a day and a half later by an external cross-check.
0.3.1 decoded the badge in a test. This module goes one step further: the
numbers are no longer typed anywhere. ``evals/refresh_public_numbers.py``
derives them from pytest's collection, the case manifest and the case tree,
writes them to ``evals/public-numbers.json``, and writes that snapshot onto the
README's badge, Quickstart line and Status table and onto the evaluation
page's current-numbers paragraph.

Three things are held here:

* the snapshot is what the tree derives right now;
* every surface says what the snapshot renders, byte for byte;
* on a copy of the pages, a wrong digit on any surface is caught and rewritten,
  and a surface whose wording has been changed stops the script rather than
  being guessed at.

``tests/test_public_claims.py`` keeps its own, independently written reading of
the same surfaces against the same sources. The two derivations are kept apart
on purpose: a mistake in one is a red test in the other.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from evals import refresh_public_numbers as numbers

PAGES = sorted({surface.path for surface in numbers.SURFACES})


@pytest.fixture(scope="module")
def derived() -> numbers.Numbers:
    return numbers.derive()


@pytest.fixture()
def tree_copy(tmp_path: Path) -> Path:
    """The pages and the snapshot, copied where a test may corrupt them."""
    for relative in PAGES + [numbers.SNAPSHOT_PATH.relative_to(numbers.ROOT).as_posix()]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(numbers.ROOT / relative, target)
    return tmp_path


def test_the_snapshot_is_what_the_tree_derives(derived: numbers.Numbers) -> None:
    assert numbers.read_snapshot() == derived, (
        f"evals/public-numbers.json says {numbers.read_snapshot()}; the tree derives {derived}. "
        "Run: python evals/refresh_public_numbers.py --write"
    )


def test_every_public_surface_says_what_the_snapshot_renders(derived: numbers.Numbers) -> None:
    stale = [finding for finding in numbers.compare(derived) if finding.stale]
    assert not stale, "\n".join(
        f"{finding.surface.name} says {finding.current!r}; the tree says {finding.rendered!r}"
        for finding in stale
    ) + "\nRun: python evals/refresh_public_numbers.py --write"


def test_a_wrong_digit_on_any_surface_is_caught_and_rewritten(
    derived: numbers.Numbers, tree_copy: Path
) -> None:
    """Mutation proof, on the copy: corrupt one digit of each surface in turn."""
    for surface in numbers.SURFACES:
        page = tree_copy / surface.path
        original = page.read_text(encoding="utf-8")
        current = surface.pattern.search(original)
        assert current, surface.name
        corrupted = re.sub(r"\d", lambda m: str((int(m.group()) + 1) % 10), current.group(0), count=1)
        assert corrupted != current.group(0)
        page.write_text(original.replace(current.group(0), corrupted, 1), encoding="utf-8")

        stale = [finding.surface.name for finding in numbers.compare(derived, tree_copy) if finding.stale]
        assert stale == [surface.name], f"corrupting {surface.name} was reported as {stale}"

        written = [finding.surface.name for finding in numbers.write(derived, tree_copy)]
        assert written == [surface.name]
        assert page.read_text(encoding="utf-8") == original, f"{surface.name} was not restored byte for byte"


def test_a_reworded_surface_stops_the_script_instead_of_being_guessed(
    derived: numbers.Numbers, tree_copy: Path
) -> None:
    readme = tree_copy / "README.md"
    text = readme.read_text(encoding="utf-8")
    reworded = text.replace("inventoried in a case manifest", "listed in a case manifest", 1)
    assert reworded != text
    readme.write_text(reworded, encoding="utf-8")
    with pytest.raises(LookupError, match="Status table, cases"):
        numbers.compare(derived, tree_copy)
