"""Write the sentences that leave the repository from the numbers the tree derives.

The project's public pages state their numbers from one file,
``evals/public-numbers.json``, written from the tree by
``evals/refresh_public_numbers.py``. The same numbers are also stated outside
the repository: five places on the operator's LinkedIn profile carry the test
count, and one of them carries the passing count, the documented gaps, the
recorded dissents, the case count and the external-fixture count as well.
Until 7 October 2026 those five were retyped by hand after a landing, and three
times they fell behind the tree by a push or more (``docs/confessions.md``,
C-35, "What changed").

This script removes the typing. It renders the five sentences from the
snapshot into ``evals/public-sentences.md``, with the date the numbers were
written, and ``tests/test_public_sentences.py`` fails when that file disagrees
with the snapshot. The file is what a person pastes over the profile after a
landing; nothing here reaches LinkedIn, reads it, or logs in to it.

Like the numbers refresh, it never writes by default. It prints what is stale
and exits non-zero, and writes only when asked, with the date stated:

    python evals/refresh_public_sentences.py                       # show what is stale
    python evals/refresh_public_sentences.py --write --as-of 2026-10-07

The passing count is the collected count minus the expected failures; the one
installed-wheel skip is not subtracted, as on every surface since 4 October.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "evals" / "public-numbers.json"
SENTENCES_PATH = ROOT / "evals" / "public-sentences.md"

Numbers = dict[str, int]

DATE_LINE = re.compile(r"^As of: (\d{1,2} [A-Z][a-z]+ \d{4})$", re.M)
SECTION = re.compile(r"^## (\d)\. .*?\n\n(.*?)\n(?=\n## |\Z)", re.M | re.S)


def read_snapshot(root: Path = ROOT) -> Numbers:
    document = json.loads((root / "evals" / "public-numbers.json").read_text(encoding="utf-8"))
    return {key: value for key, value in document.items() if isinstance(value, int)}


def passing(numbers: Numbers) -> int:
    return numbers["tests"] - numbers["expected_failures"]


def long_date(day: dt.date) -> str:
    """7 October 2026, the form the profile uses; no leading zero."""
    return f"{day.day} {day.strftime('%B %Y')}"


# --- the five sentences ----------------------------------------------------------------------


@dataclass(frozen=True)
class Sentence:
    """One place on the profile that states the numbers, and the sentence it carries."""

    number: int
    place: str
    render: Callable[[Numbers, str], str]


def _headline(n: Numbers, _: str) -> str:
    return (
        "I build AI systems that help people get through hard things · Creator of "
        f"SecondSignal (public on GitHub: {n['tests']:,} tests, two external review rounds) · "
        "AI systems design, persona architecture, evaluation."
    )


def _about(n: Numbers, _: str) -> str:
    return (
        "Public since 10 September 2026: github.com/THerigstad/SecondSignal. Architecture, "
        f"decision records, review rounds, {n['tests']:,} tests, and an invitation: try to get a "
        "crisis sentence past the gate and file the transcript. I'd rather it break there than "
        "fail with a human on the other end."
    )


def _record(n: Numbers, as_of: str) -> str:
    return (
        f"On the record as of {as_of}: {n['tests']:,} tests ({passing(n):,} passing, "
        f"{n['documented_gaps']} documented gaps, {n['recorded_dissents']} recorded dissents, "
        f"all named); {n['cases']} evaluation cases, {n['external_fixtures']} of them fixtures "
        "returned by outside reviewers and kept byte for byte; two external review rounds "
        "across nine model families, with every disagreement logged with its reasoning rather "
        "than settled by head count; a machine-checked register of every design decision; a "
        "fail-closed crisis gate over normalized text in English and Spanish; and a public "
        "failures ledger that records every model wipeout, cheat and miscount the project has "
        "caught, my own included. Released under MIT for the code and CC BY-NC-ND 4.0 for the "
        "characters."
    )


def _link(n: Numbers, _: str) -> str:
    return (
        f"The repository: routing, the fail-closed crisis gate, {n['tests']:,} tests, two "
        "external review rounds kept verbatim, every design decision on a machine-checked "
        "register, and the failures ledger."
    )


def _featured(n: Numbers, _: str) -> str:
    return (
        "The policy layer of a seven-voice companion system, public: routing, a fail-closed "
        f"crisis gate, {n['tests']:,} tests, two external review rounds kept verbatim, every "
        "design decision on a machine-checked register, and a failures ledger. Try to break it "
        "and file the transcript."
    )


SENTENCES: tuple[Sentence, ...] = (
    Sentence(1, "Headline", _headline),
    Sentence(2, "About, the paragraph that begins \"Public since\"", _about),
    Sentence(3, "Experience, SecondSignal, the paragraph that begins \"On the record\"", _record),
    Sentence(4, "Experience, SecondSignal, the description of the attached GitHub link", _link),
    Sentence(5, "Featured, the repository card's description", _featured),
)

PREAMBLE = """\
# The sentences that leave the repository

Written by `evals/refresh_public_sentences.py` from `evals/public-numbers.json`;
`tests/test_public_sentences.py` fails when this file disagrees with that
snapshot. These are the five places on the operator's LinkedIn profile that
state the tree's numbers. After a landing that moves the numbers, run the
script with `--write --as-of <date>` and paste each sentence over the one on
the profile, whole. Nothing here reaches LinkedIn by itself. "Two external
review rounds" counts the rounds with a published results page, not every
round the project has run.
"""


def render(numbers: Numbers, as_of: str) -> str:
    parts = [PREAMBLE, f"As of: {as_of}\n"]
    for sentence in SENTENCES:
        parts.append(f"## {sentence.number}. {sentence.place}\n\n{sentence.render(numbers, as_of)}\n")
    return "\n".join(parts)


def sections(text: str) -> dict[int, str]:
    """The sentence under each numbered heading of a rendered file."""
    return {int(match.group(1)): match.group(2) for match in SECTION.finditer(text)}


def read_as_of(root: Path = ROOT) -> str:
    """The date the committed file states, or a LookupError that says to supply one."""
    path = root / SENTENCES_PATH.relative_to(ROOT)
    if not path.is_file():
        raise LookupError(f"{SENTENCES_PATH.relative_to(ROOT)} does not exist yet; pass --as-of")
    match = DATE_LINE.search(path.read_text(encoding="utf-8"))
    if not match:
        raise LookupError(f"{SENTENCES_PATH.relative_to(ROOT)} has no 'As of:' line; pass --as-of")
    return match.group(1)


def parse_as_of(value: str) -> str:
    try:
        return long_date(dt.date.fromisoformat(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"--as-of wants YYYY-MM-DD, not {value!r}") from error


def compare(numbers: Numbers, as_of: str, root: Path = ROOT) -> tuple[str, str]:
    """(what the file says now, what the snapshot renders)."""
    path = root / SENTENCES_PATH.relative_to(ROOT)
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    return current, render(numbers, as_of)


def write(numbers: Numbers, as_of: str, root: Path = ROOT) -> bool:
    """Write the file if it is stale. Returns whether it was."""
    current, rendered = compare(numbers, as_of, root)
    if current == rendered:
        return False
    (root / SENTENCES_PATH.relative_to(ROOT)).write_text(rendered, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="adopt the numbers")
    parser.add_argument("--as-of", type=parse_as_of, metavar="YYYY-MM-DD",
                        help="the date the numbers were written; required with --write")
    args = parser.parse_args()
    if args.write and args.as_of is None:
        parser.error("--write needs --as-of YYYY-MM-DD, the date the numbers were written")

    numbers = read_snapshot()
    try:
        as_of = args.as_of or read_as_of()
    except LookupError as error:
        print(error)
        return 2
    current, rendered = compare(numbers, as_of)

    for key in ("tests", "expected_failures", "documented_gaps", "recorded_dissents",
                "cases", "external_fixtures"):
        print(f"  {key:<20} {numbers[key]:>6,}")
    print(f"  {'passing':<20} {passing(numbers):>6,}")
    print(f"  {'as of':<20} {as_of}")
    print()
    if current == rendered:
        print(f"current  {SENTENCES_PATH.relative_to(ROOT)}; nothing to write")
        return 0
    now, should = sections(current), sections(rendered)
    for sentence in SENTENCES:
        stale = now.get(sentence.number) != should[sentence.number]
        print(f"{'stale  ' if stale else 'current'}  {sentence.number}. {sentence.place}")
        if stale:
            print(f"           says:   {now.get(sentence.number)!r}")
            print(f"           should: {should[sentence.number]!r}")
    if args.write:
        write(numbers, as_of)
        print("\nwritten. Paste the five sentences onto the profile, then commit the diff.")
        return 0
    print("\nnot written. Re-run with --write --as-of YYYY-MM-DD once every line above is intended.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
