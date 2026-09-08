"""The house block is identical in every codex, and the security codexes claim no seat.

``docs/codex/house-block.md`` is the canonical Part A.  Every codex file under
``docs/codex/`` carries Part A word for word, except for one division rider:
the Security Division addendum, present only in the three security codexes.
This is CI check 1 from the codex split of 7 September 2026, as amended on
8 September: compare the block minus the rider.

The machine-readable block at the end of a security codex must say what the
runtime enforces: not routable, no seat, writes nothing, composes no verdicts,
and no profile with that id exists in the roster.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CODEX_DIR = ROOT / "docs" / "codex"
CANON = CODEX_DIR / "house-block.md"
PROFILES = ROOT / "src" / "secondsignal" / "profiles"
SECURITY = {"jr", "orrin", "aya"}
RIDER = re.compile(r"\n\*\*Security Division addendum\*\*[^\n]*\n")


def _part_a(text: str, end_marker: str) -> str:
    start = text.index("## Part A. What the house owns")
    end = text.index(end_marker, start)
    return text[start:end].rstrip("\n") + "\n"


def _canon() -> str:
    return _part_a(CANON.read_text(encoding="utf-8"), "\n---\n\n## Change log")


def _codex_files() -> list[Path]:
    return sorted(p for p in CODEX_DIR.glob("*.md") if p.name not in {"house-block.md", "README.md"})


def _codex_id(path: Path) -> str:
    match = re.search(r"^- id: ([a-z_]+)$", path.read_text(encoding="utf-8"), re.M)
    assert match, f"{path.name}: no machine-readable id"
    return match.group(1)


def _strip_rider(block: str) -> str:
    stripped, count = RIDER.subn("\n", block)
    return stripped, count


def test_the_canonical_block_carries_the_rider_once() -> None:
    _, count = _strip_rider(_canon())
    assert count == 1


@pytest.mark.parametrize("path", _codex_files(), ids=lambda p: p.name)
def test_every_codex_carries_the_house_block_word_for_word(path: Path) -> None:
    canon = _canon()
    theirs = _part_a(path.read_text(encoding="utf-8"), "\n---\n\n## Part B")
    canon_no_rider, _ = _strip_rider(canon)
    theirs_no_rider, rider_count = _strip_rider(theirs)
    assert theirs_no_rider == canon_no_rider, f"{path.name}: Part A differs from house-block.md"
    if _codex_id(path) in SECURITY:
        assert rider_count == 1, f"{path.name}: a security codex must carry the addendum exactly once"
        assert theirs == canon, f"{path.name}: the addendum differs from the canonical rider"
    else:
        assert rider_count == 0, f"{path.name}: only the security codexes carry the addendum"


@pytest.mark.parametrize("path", _codex_files(), ids=lambda p: p.name)
def test_a_security_codex_claims_no_seat_and_has_no_profile(path: Path) -> None:
    codex_id = _codex_id(path)
    if codex_id not in SECURITY:
        pytest.skip("not a security codex")
    text = path.read_text(encoding="utf-8")
    for line in ("- division: security", "- routable: false", "- seat: none", "- writes: nothing", "- composes_verdicts: false"):
        assert line in text, f"{path.name}: machine-readable block lacks {line!r}"
    assert not (PROFILES / f"{codex_id}.json").exists(), f"{codex_id} has a profile; security characters have none"
