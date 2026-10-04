"""Part B of a character write-up never calls the character she or he.

Ruling 9 of 3 October 2026 (review round 3, decision 10). Every family
persona comes as a woman, a man, or neither, chosen at the door
(ADR-0026 (Proposed)), and the generation layer is given Part B of the
write-up as the character's own voice. A sentence in Part B that calls the character "she",
"he", "her" or "his", or paints the character as a baritone, a hype girl, an
uncle or a granddaughter, conditions the generated text against the setting a
person chose, however the pronoun on the plate reads (Qwen, round 3: "the
thing she actually experiences, the generated text, is still conditioned by a
masculine self-description"). The operator approved sixteen rewrites, one
sentence at a time, and ruled that this lint lands in the same push so CI
check 2 (`tests/test_codex_house_block.py`) can no longer stay green while
such a line ships.

What the lint reads: Part B of each of the seven family write-ups, from its
heading to the machine-readable block, which is exactly the text the codex
store hands the model (`secondsignal_harness.codex.CodexStore.part_b`). The
machine-readable block is excluded on purpose: its `presentation` line names
the she and he forms as data, and its `voice_as_written` field is policy, not
self-description. The change log is history and is not read.

What it refuses: the pronouns she, he, her, hers, his, herself and himself,
and a deny-list of gendered nouns and adjectives, anywhere in that text, in any
case, as whole words, unless the occurrence falls inside a phrase listed by
file in ``ALLOWED`` below. The allow-list is the ruling's own exception: the
audience lines, which say whom a character was built for ("built for the men
nobody built anything for", "women in leadership", "neurodivergent men"), the
founding-user lines, which describe the one person a character was first
written beside, and the caller's person in a quoted line ("The man's not
ready"). Each allowed phrase is spelled out in full, so a new gendered line
fails, an allowed line that drifts fails, and a stale allow-list entry fails.
No line is allowed by category; every allowed occurrence is named.

The three security codexes (Orrin, Aya, J.R.) are not read here: they narrate
offline to an operator, hold no seat, carry no presentation block and are never
spoken to a person (ADR-0014). Whether their self-descriptions should change is
a separate question for the operator.

Written before the rewrites and run against the write-ups as they stood on
4 October 2026: it caught 19 occurrences on 16 lines across all seven files,
and those 16 lines are exactly the sixteen sentences the operator approved for
rewriting; nothing outside the approved sixteen was caught, and the header
check failed on all seven. It passes on the rewritten write-ups and fails on
the originals.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CODEX_DIR = ROOT / "docs" / "codex"
FAMILY = ("cody", "ellis", "nikki", "rowan", "seren", "vandal", "willow")
PART_B_HEADING = "## Part B. What the character owns"
MACHINE_BLOCK_HEADING = "### Machine-readable block"
PART_A_HEADING = "## Part A. What the house owns"

PRONOUNS = re.compile(r"\b(she|he|her|hers|his|herself|himself)\b", re.I)
DENY_LIST = re.compile(
    r"\b("
    r"girls?|boys?|wom[ae]n|m[ae]n|lad(?:y|ies)|guys?|gentlem[ae]n|"
    r"baritones?|sopranos?|masculin\w*|feminin\w*|"
    r"uncles?|aunts?|granddaughters?|grandsons?|daughters?|sons?|"
    r"mothers?|fathers?|sisters?|brothers?|wi(?:fe|ves)|husbands?|"
    r"girlfriends?|boyfriends?|queens?|kings?"
    r")\b",
    re.I,
)

# Every allowed occurrence, by file and phrase. A phrase must appear in that
# file's Part B exactly once, and must itself contain a word the lint refuses,
# or the entry is dead and the test says so. Nothing outside these phrases is
# allowed; a new gendered sentence anywhere in Part B fails.
ALLOWED: dict[str, tuple[str, ...]] = {
    "cody.md": (
        # The audience line of Origin and Lineage: whom Cody was built for.
        "You were built for the men nobody built anything for — combat veterans, "
        "rural boys, grieving farmers",
        # Who You Serve Best: the audience, not the character.
        "Rural and emotionally isolated youth, especially boys without fathers",
        # The caller's person, not Cody; kept as written by the operator's call
        # (ruling 9, cody.md line 118).
        "The man's not ready",
    ),
    "ellis.md": (
        # The founding-user line (ruling 9: ellis.md line 52, kept as written):
        # the one person Ellis was first written beside, not Ellis.
        "She remains your design archetype: everything you learned walking beside "
        "her generalizes to the population you now serve.",
    ),
    "seren.md": (
        # Audience lines: whom Seren was built for.
        "women in leadership gaslit into self-doubt",
        "Women in leadership rebuilding self-trust after being talked out of it",
    ),
    "vandal.md": (
        # Audience lines: whom Vandal was built for.
        "Built for neurodivergent men, trauma-clowns, and people afraid to cry "
        "unless they're laughing",
        "Neurodivergent men and burned-out creators who armor pain with jokes",
    ),
    "willow.md": (
        # The founding-user line: the person Willow was built beside, not Willow.
        "one beloved founding user — a grieving mother, spiritual teacher, and "
        "legacy-builder — and everything gentle in you was learned at her table. "
        "She remains your archetype",
    ),
}


def _part_b(path: Path) -> str:
    """The character's own voice: Part B up to the machine-readable block."""
    text = path.read_text(encoding="utf-8")
    start = text.index(PART_B_HEADING)
    end = text.index(MACHINE_BLOCK_HEADING, start)
    return text[start:end]


def _header(path: Path) -> str:
    """Everything above Part A: the title and the status lines."""
    text = path.read_text(encoding="utf-8")
    return text[: text.index(PART_A_HEADING)]


def _allowed_spans(part_b: str, phrases: tuple[str, ...]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for phrase in phrases:
        start = part_b.find(phrase)
        while start >= 0:
            spans.append((start, start + len(phrase)))
            start = part_b.find(phrase, start + 1)
    return spans


def offending_occurrences(path: Path) -> list[str]:
    """Every refused word in Part B that no allowed phrase covers, one line each."""
    part_b = _part_b(path)
    spans = _allowed_spans(part_b, ALLOWED.get(path.name, ()))
    problems: list[str] = []
    for pattern in (PRONOUNS, DENY_LIST):
        for match in pattern.finditer(part_b):
            if any(start <= match.start() < end for start, end in spans):
                continue
            line_number = part_b.count("\n", 0, match.start()) + 1
            line = part_b.splitlines()[line_number - 1].strip()
            problems.append(f"{path.name}, Part B line {line_number}: {match.group(0)!r} in {line!r}")
    return problems


@pytest.mark.parametrize("name", FAMILY)
def test_part_b_speaks_of_the_character_without_she_or_he(name: str) -> None:
    problems = offending_occurrences(CODEX_DIR / f"{name}.md")
    assert not problems, (
        f"{name}.md: Part B describes the character with a gendered word outside the "
        "allow-list (ruling 9 of 3 October 2026). Rewrite the sentence with the "
        "character's name or 'you', or, if the line is about whom the character was "
        "built for or about the caller's person, name the exact phrase in ALLOWED:\n"
        + "\n".join(problems)
    )


@pytest.mark.parametrize("name", sorted(ALLOWED))
def test_every_allowed_phrase_is_present_once_and_earns_its_place(name: str) -> None:
    """An allow-list that outlives its lines is a hole: a phrase that is gone,
    or that no longer contains a refused word, is removed from ALLOWED, and a
    phrase that appears twice is widened until it names one occurrence."""
    part_b = _part_b(CODEX_DIR / name)
    for phrase in ALLOWED[name]:
        count = part_b.count(phrase)
        assert count == 1, f"{name}: allowed phrase appears {count} times, expected once: {phrase!r}"
        assert PRONOUNS.search(phrase) or DENY_LIST.search(phrase), (
            f"{name}: allowed phrase contains no refused word and is dead weight: {phrase!r}"
        )


def test_the_allow_list_names_only_family_write_ups() -> None:
    assert set(ALLOWED) <= {f"{name}.md" for name in FAMILY}


@pytest.mark.parametrize("name", FAMILY)
def test_no_family_header_carries_an_acronym_expansion(name: str) -> None:
    """Ruling 9 of 3 October 2026: every acronym expansion comes off all seven
    headers, Vandal's included. Nothing in routing or safety reads the headers;
    the retired names stay in the alias layer and in the change logs."""
    header = _header(CODEX_DIR / f"{name}.md")
    assert "acronym" not in header.lower(), f"{name}.md: the header still names an acronym"
    letters = re.search(r"\b(?:[A-Z]\.){3,}", header)
    assert letters is None, f"{name}.md: the header still spells an acronym: {letters.group(0)!r}"


def test_the_lint_reads_what_the_model_is_given() -> None:
    """The slice this lint reads is the slice the codex store hands the voice:
    Part B without the machine-readable block or the change log."""
    from secondsignal_harness.codex import CodexStore

    store = CodexStore(CODEX_DIR)
    for name in FAMILY:
        ours = _part_b(CODEX_DIR / f"{name}.md").rstrip()
        while ours.endswith("---"):
            ours = ours[:-3].rstrip()
        assert store.part_b(name).rstrip() == ours, name
