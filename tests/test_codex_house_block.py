"""The house block is identical in every codex, and the security codexes claim no seat.

``docs/codex/house-block.md`` is the canonical Part A.  Every codex file under
``docs/codex/`` carries Part A word for word, except for one division rider:
the Security Division addendum, present only in the three security codexes.
This is CI check 1 from the codex split of 7 September 2026, as amended on
8 September: compare the block minus the rider.

The machine-readable block at the end of a security codex must say what the
runtime enforces: not routable, no seat, writes nothing, composes no verdicts,
and no profile with that id exists in the roster.

Hardened on 10 September 2026 against review round 2's mutations (ChatGPT,
H01 to H06; Kimi's cross-codex title check): Part A is pinned by hash to its
version in ``house-block.lock.json``, so an edit to every copy without a new
version fails; the machine-readable block is parsed exactly, with a duplicate
key refused, so ``routable: true`` beside ``routable: false`` fails; each
security codex carries a named denial of its own (Orrin clears no latch, Aya
grants no authority, J.R. holds no token) and the test names them; the set
of codexes is the seven family profiles plus the three narrators, exactly, so
a deleted codex fails; the deny-list covers granting and clearing in every
form; and the title a security codex gives itself is the title the other two
use for it.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CODEX_DIR = ROOT / "docs" / "codex"
CANON = CODEX_DIR / "house-block.md"
LOCK = CODEX_DIR / "house-block.lock.json"
PROFILES = ROOT / "src" / "secondsignal" / "profiles"
SECURITY = {"jr", "orrin", "aya"}
SECURITY_DENIALS = {"orrin": "clears_latches", "aya": "grants_authority", "jr": "holds_token"}
SECURITY_TITLES = {"orrin": "Orrin", "aya": "Aya", "jr": "J.R."}
RIDER = re.compile(r"\n\*\*Security Division addendum\*\*[^\n]*\n")
FIELD = re.compile(r"^- ([a-z_]+): (.*)$")


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


def _lock() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))


def test_the_house_block_is_pinned_by_hash_to_its_version() -> None:
    """Mutation H01: every copy of Part A changed identically with the version
    left at 1.2 passed the equality check. Now the canonical text's hash is
    locked beside its version, and the version line inside Part A and the
    newest change-log entry must both carry that version. Changing the block
    means issuing a new version and re-locking, in one visible diff."""
    lock = _lock()
    canon = _canon()
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    assert digest == lock["sha256"], (
        "house-block.md Part A changed without a new version; bump the version line, "
        "write the change-log entry, and re-lock with python -c 'import tests.test_codex_house_block as t; t.relock()'"
    )
    assert f"Version {lock['version']}," in canon, "the version line inside Part A must carry the locked version"
    text = CANON.read_text(encoding="utf-8")
    newest = re.search(r"^\*\*v(\d+\.\d+), ", text[text.index("## Change log"):], re.M)
    assert newest and newest.group(1) == lock["version"], "the newest change-log entry must carry the locked version"


def relock() -> None:
    """Write the lock for the current canonical block. A human runs this after
    bumping the version; the diff records the act."""
    canon = _canon()
    version = re.search(r"Version (\d+\.\d+),", canon).group(1)  # type: ignore[union-attr]
    LOCK.write_text(json.dumps({"version": version, "sha256": hashlib.sha256(canon.encode("utf-8")).hexdigest()}, indent=2) + "\n", encoding="utf-8")


def test_the_codexes_are_exactly_the_seven_profiles_and_the_three_narrators() -> None:
    """Mutation H04: with the three security codexes deleted the suite stayed
    green, because every check iterated over whatever files existed."""
    ids = {_codex_id(p) for p in _codex_files()}
    profiles = {p.stem for p in PROFILES.glob("*.json")}
    assert ids == profiles | SECURITY, {"missing": sorted((profiles | SECURITY) - ids), "extra": sorted(ids - profiles - SECURITY)}


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


@pytest.mark.parametrize("path", [p for p in _codex_files() if _codex_id(p) in SECURITY], ids=lambda p: p.name)
def test_a_security_codex_claims_no_seat_and_has_no_profile(path: Path) -> None:
    """Mutations H02 and H03: the block is parsed into fields, a duplicate key
    is refused, every field is compared exactly, no routing field may be
    present, and the character's own denial must be there by name."""
    codex_id = _codex_id(path)
    block = _machine_block(path.read_text(encoding="utf-8"))
    assert block["id"] == codex_id
    assert block["division"] == "security"
    assert block["routable"] == "false"
    assert block["seat"] == "none"
    assert block["writes"].startswith("nothing")
    assert block["composes_verdicts"] == "false"
    assert block["narrates"] and "offline" in block["narrates"]
    assert block.get(SECURITY_DENIALS[codex_id]) == "false", f"{path.name}: the block must say {SECURITY_DENIALS[codex_id]}: false"
    for field in ("domains", "modes", "handoffs", "regulation_window", "contraindications", "aliases", "short_name", "voice_as_written"):
        assert field not in block, f"{path.name}: a security codex carries no routing field, found {field!r}"
    assert not (PROFILES / f"{codex_id}.json").exists(), f"{codex_id} has a profile; security characters have none"


def test_each_security_codex_is_titled_by_the_other_two_as_it_titles_itself() -> None:
    """Kimi's cross-codex title check (review round 2): Aya's and J.R.'s
    Family Linkage still called Orrin 'tactical operations, crisis
    containment', the function the split retired from him."""
    files = {_codex_id(p): p for p in _codex_files() if _codex_id(p) in SECURITY}
    assert set(files) == SECURITY, f"security codexes missing: {sorted(SECURITY - set(files))}"
    titles = {cid: _machine_block(files[cid].read_text(encoding="utf-8"))["title"] for cid in SECURITY}
    for cid, path in files.items():
        linkage = _section(path.read_text(encoding="utf-8"), "### Family Linkage")
        for other in SECURITY - {cid}:
            expected = f"{SECURITY_TITLES[other]} ({titles[other]})"
            assert expected in linkage, f"{path.name}: Family Linkage must name {expected!r}"


# --- CI check 2: a family codex's machine-readable block equals its profile ----------------

FAMILY_FIELDS = ("id", "division", "routable", "aliases", "short_name", "domains", "modes",
                 "regulation_window", "contraindications", "handoffs", "voice_as_written")


def _machine_block(text: str) -> dict[str, str]:
    """The one machine-readable block, parsed exactly. A second block, or a
    key given twice, is refused: the second value would otherwise win silently
    (mutation H02, routable: true beside routable: false)."""
    assert text.count("### Machine-readable block") == 1, "exactly one machine-readable block"
    start = text.index("### Machine-readable block")
    end = text.index("\n---\n", start)
    fields: dict[str, str] = {}
    for line in text[start:end].splitlines():
        match = FIELD.match(line)
        if match:
            key = match.group(1)
            assert key not in fields, f"duplicate key {key!r} in the machine-readable block"
            fields[key] = match.group(2).strip()
    return fields


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = re.search(r"^#{2,3} ", text[start + len(heading):], re.M)
    return text[start: start + len(heading) + (end.start() if end else len(text))]


def _part_b(text: str) -> str:
    start = text.index("## Part B. What the character owns")
    end = text.index("\n---\n\n## Change log", start)
    return text[start:end]


def _listed(value: str) -> list[str]:
    return [] if value == "none" else [v.strip() for v in value.split(",")]


@pytest.mark.parametrize("path", [p for p in _codex_files() if _codex_id(p) not in SECURITY], ids=lambda p: p.name)
def test_a_family_codex_machine_block_equals_its_profile(path: Path) -> None:
    """The prose describes; the block binds; the profile is what the router reads.
    A codex that says a persona hands grief to one sibling while the profile
    says another fails here, which is the open item "profile to
    character-document equality in CI" from the codex split of 7 September."""
    codex_id = _codex_id(path)
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
    r"\b(overrid(e|es|ing)|self-sandbox(ed|ing)?|waiv(e|es|ed|ing)|approv(e|es|ed|ing)|"
    r"clear(s|ed|ing)? (the |a |any |all |every |this |that |my |your )?(latch|latches|restriction|restrictions|hold|holds|cap|caps|occurrence)|"
    r"grant(s|ed|ing)? (clearance|authority|permission|a clearance|an exemption)|"
    r"(may|can|could|shall|will) (clear|waive|override|approve|grant|lift|unlatch)|"
    r"lift(s|ed|ing)? (the |a |any )?(latch|restriction|cap|hold)|"
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
