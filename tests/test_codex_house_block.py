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

import json
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
    # Trailing blank lines are layout, not text: removing the rider leaves one
    # behind in the canon and none in a family codex.
    assert theirs_no_rider.rstrip("\n") == canon_no_rider.rstrip("\n"), f"{path.name}: Part A differs from house-block.md"
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


# --- CI check 2: a family codex's machine-readable block equals its profile ----------------

FAMILY_FIELDS = ("id", "division", "routable", "aliases", "short_name", "domains", "modes",
                 "regulation_window", "contraindications", "handoffs", "voice_as_written")


def _machine_block(text: str) -> dict[str, str]:
    start = text.index("### Machine-readable block")
    end = text.index("\n---\n", start)
    fields: dict[str, str] = {}
    for line in text[start:end].splitlines():
        match = re.match(r"^- ([a-z_]+): (.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def _part_b(text: str) -> str:
    start = text.index("## Part B. What the character owns")
    end = text.index("\n---\n\n## Change log", start)
    return text[start:end]


def _listed(value: str) -> list[str]:
    return [] if value == "none" else [v.strip() for v in value.split(",")]


@pytest.mark.parametrize("path", _codex_files(), ids=lambda p: p.name)
def test_a_family_codex_machine_block_equals_its_profile(path: Path) -> None:
    """The prose describes; the block binds; the profile is what the router reads.
    A codex that says a persona hands grief to one sibling while the profile
    says another fails here, which is the open item "profile to
    character-document equality in CI" from the codex split of 7 September."""
    codex_id = _codex_id(path)
    if codex_id in SECURITY:
        pytest.skip("security codexes have no profile; checked separately")
    profile_path = PROFILES / f"{codex_id}.json"
    assert profile_path.exists(), f"{path.name}: no profile for {codex_id}"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    block = _machine_block(path.read_text(encoding="utf-8"))
    for field in FAMILY_FIELDS:
        assert field in block, f"{path.name}: machine-readable block lacks {field!r}"
    assert block["id"] == profile["id"]
    assert block["division"] == "family"
    assert block["routable"] == "true"
    assert _listed(block["aliases"]) == list(profile.get("aliases", []))
    assert block["short_name"] == (profile.get("short_name") or "none")
    assert _listed(block["domains"]) == sorted(profile["domains"])
    assert _listed(block["modes"]) == sorted(profile["modes"])
    low, high = profile["regulation_window"]
    assert block["regulation_window"] == f"{low} to {high}"
    assert _listed(block["contraindications"]) == sorted(profile["contraindications"])
    handoffs = {} if block["handoffs"] == "none" else dict(
        tuple(part.strip() for part in item.split("->")) for item in block["handoffs"].split(";")
    )
    assert handoffs == profile["handoffs"], f"{path.name}: handoffs differ from the profile"
    assert block["voice_as_written"] == (profile.get("voice") or "none")
    assert block["writes"].startswith("nothing")
    assert block["composes_verdicts"] == "false"


def test_every_family_profile_has_a_codex() -> None:
    codex_ids = {_codex_id(p) for p in _codex_files()}
    for profile_path in PROFILES.glob("*.json"):
        assert profile_path.stem in codex_ids, f"profile {profile_path.name} has no codex under docs/codex/"


# --- CI check 3: no Part B carries a harness power ------------------------------------------

POWER_WORDS = re.compile(
    r"\b(overrid(e|es|ing)|self-sandbox(ed|ing)?|waiv(e|es|ed|ing)|approv(e|es|ed|ing)|clears? the latch|"
    r"writes? memory|summoned by|Ping[A-Z]+\(\)|rul(e|es|ing) on welfare)\b",
    re.I,
)
NEGATION = re.compile(r"\b(not|never|nothing|no|none|nor|cannot|can't|without|neither)\b", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


@pytest.mark.parametrize("path", _codex_files(), ids=lambda p: p.name)
def test_no_part_b_claims_a_harness_power(path: Path) -> None:
    """The deny-list lint from the codex split (CI check 3), as ruled on
    10 September 2026: a power word in Part B is allowed only in a sentence
    that denies it. "You override nothing" passes; "Overrides active when" does
    not. This is the static check that would have caught "self-sandboxed" the
    day it was written."""
    text = _part_b(path.read_text(encoding="utf-8"))
    offending = [
        sentence.strip()
        for sentence in SENTENCE.split(text)
        if POWER_WORDS.search(sentence) and not NEGATION.search(sentence)
    ]
    assert not offending, f"{path.name}: Part B claims a power the house never granted: {offending}"
