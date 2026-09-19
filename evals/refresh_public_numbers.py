"""Write the headline numbers onto the public pages from the sources they claim.

The README's tests badge, its Quickstart line and its Status table, and the
evaluation page's current-numbers paragraph, all state how many tests the tree
collects and how many labeled cases, documented gaps, recorded dissents and
deferred fixtures it holds. Until 0.3.1 each of those copies was typed by hand
and a test compared them to the sources afterwards; the badge drifted anyway,
because it was the one copy the test did not read.

This script removes the typing. It derives the numbers from the tree -- what
pytest collects, the case manifest's dispositions, the case files themselves --
writes them to ``evals/public-numbers.json``, and writes that snapshot onto
every surface that states them. A surface is found by its own fixed wording,
so a page that is reworded stops being found and the script says so instead
of guessing.

Like the case-manifest refresh, it never writes by default. It prints what is
stale and exits non-zero, and writes only when asked, so the change is
something a person read and a diff records. ``tests/test_public_numbers.py``
runs the same comparison in CI, so a stale number on any of these surfaces
fails the suite.

    python evals/refresh_public_numbers.py            # show what is stale
    python evals/refresh_public_numbers.py --write    # adopt the numbers
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import textwrap
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "evals" / "public-numbers.json"
MANIFEST_PATH = ROOT / "evals" / "case-manifest.json"
CASES_DIR = ROOT / "evals" / "cases"

Numbers = dict[str, int]

SNAPSHOT_NOTE = (
    "The headline numbers stated on the public pages, derived from the tree by "
    "evals/refresh_public_numbers.py: the test count from pytest's own collection, the "
    "dispositions from evals/case-manifest.json, the case and fixture counts from the "
    "files under evals/cases/. Regenerate with `python evals/refresh_public_numbers.py "
    "--write`. tests/test_public_numbers.py fails when this file, or any page written "
    "from it, no longer matches the tree."
)


# --- the numbers, from the tree --------------------------------------------------------


def collected_tests() -> int:
    """How many tests pytest collects on this tree, asked of pytest itself."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    match = re.search(r"(\d+) tests? collected", result.stdout)
    if not match:
        raise RuntimeError(
            "could not read pytest's collection count:\n"
            + result.stdout[-500:] + "\n" + result.stderr[-500:]
        )
    return int(match.group(1))


def manifest_dispositions() -> Counter[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return Counter(entry["disposition"] for entry in manifest["cases"])


def case_tree_counts() -> tuple[int, int, int]:
    """(policy cases, external reviewer fixtures among them, deferred fixtures), from the files.

    A trajectory file is one session, not a set of cases, and is not counted here.
    A file under ``deferred/`` or on a plane other than policy is stored, not run.
    """
    policy = external = deferred = 0
    for path in sorted(CASES_DIR.rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("kind") == "trajectory":
            continue
        count = len(document.get("cases", []))
        if "deferred" in path.parts or document.get("plane", "policy") != "policy":
            deferred += count
            continue
        policy += count
        if document.get("external") is True:
            external += count
    return policy, external, deferred


def derive() -> Numbers:
    """Every number the public pages state, in the order the pages state them."""
    dispositions = manifest_dispositions()
    policy, external, deferred = case_tree_counts()
    if sum(dispositions.values()) != policy:
        raise RuntimeError(
            f"the manifest inventories {sum(dispositions.values())} cases but the case tree "
            f"holds {policy}; refresh the manifest before the numbers"
        )
    gaps, dissents = dispositions["known_gap"], dispositions["disputed"]
    return {
        "tests": collected_tests(),
        "expected_failures": gaps + dissents,
        "documented_gaps": gaps,
        "recorded_dissents": dissents,
        "cases": policy,
        "external_fixtures": external,
        "deferred_fixtures": deferred,
    }


# --- the surfaces that state them ----------------------------------------------------------


@dataclass(frozen=True)
class Surface:
    """One place on a public page that states the numbers.

    ``pattern`` must match that place exactly once, by its own fixed wording, and
    ``render`` writes the whole match afresh from the numbers.
    """

    name: str
    path: str
    pattern: re.Pattern[str]
    render: Callable[[Numbers], str]


def _badge(n: Numbers) -> str:
    label = f"{n['tests']:,} · {n['documented_gaps']} known gaps · {n['recorded_dissents']} recorded dissents"
    return "img.shields.io/badge/tests-" + quote(label, safe="") + "-brightgreen"


def _quickstart(n: Numbers) -> str:
    return (
        f"# {n['tests']:,} tests: {n['expected_failures']} expected failures "
        f"({n['documented_gaps']} documented gaps, {n['recorded_dissents']} recorded dissents), "
        "the rest pass"
    )


def _status_cases(n: Numbers) -> str:
    return (
        f"{n['cases']} inventoried in a case manifest, {n['external_fixtures']} of them external "
        f"reviewer fixtures kept verbatim, {n['documented_gaps']} documented gaps and "
        f"{n['recorded_dissents']} recorded dissents"
    )


def _status_deferred(n: Numbers) -> str:
    return f"{n['deferred_fixtures']} deferred fixtures stored and not run"


def _status_tests(n: Numbers) -> str:
    return f"{n['tests']:,} tests, no network or API key required"


def _evaluation_current(n: Numbers) -> str:
    body = (
        f"**Numbers, current.** {n['tests']:,} tests: {n['expected_failures']} expected "
        f"failures ({n['documented_gaps']} documented gaps, {n['recorded_dissents']} recorded "
        f"dissents), the rest pass. {n['cases']} labeled cases in the manifest, "
        f"{n['external_fixtures']} of them external reviewer fixtures kept verbatim; "
        f"{n['deferred_fixtures']} deferred fixtures stored and not run. This paragraph, the "
        "README's tests badge, its Quickstart line and its Status table are written by "
        "`evals/refresh_public_numbers.py` from pytest's collection, the case manifest and "
        "the case tree, and `tests/test_public_numbers.py` fails when any of them differs "
        "from those sources. The dated Numbers paragraphs on this page are history and keep "
        "the numbers that were true on their dates."
    )
    return textwrap.fill(body, width=80, break_long_words=False, break_on_hyphens=False)


SURFACES: tuple[Surface, ...] = (
    Surface(
        "README.md: the tests badge",
        "README.md",
        re.compile(r"img\.shields\.io/badge/tests-[^\s()]+-brightgreen"),
        _badge,
    ),
    Surface(
        "README.md: the Quickstart pytest line",
        "README.md",
        re.compile(
            r"# \d[\d,]* tests: \d+ expected failures \(\d+ documented gaps, \d+ recorded dissents\), "
            r"the rest pass"
        ),
        _quickstart,
    ),
    Surface(
        "README.md: the Status table, cases",
        "README.md",
        re.compile(
            r"\d+ inventoried in a case manifest, \d+ of them external reviewer fixtures kept "
            r"verbatim, \d+ documented gaps and \d+ recorded dissents"
        ),
        _status_cases,
    ),
    Surface(
        "README.md: the Status table, deferred fixtures",
        "README.md",
        re.compile(r"\d+ deferred fixtures stored and not run"),
        _status_deferred,
    ),
    Surface(
        "README.md: the Status table, tests",
        "README.md",
        re.compile(r"\d[\d,]* tests, no network or API key required"),
        _status_tests,
    ),
    Surface(
        "docs/evaluation.md: the current-numbers paragraph",
        "docs/evaluation.md",
        re.compile(r"\*\*Numbers, current\.\*\*.*?(?=\n\n)", re.S),
        _evaluation_current,
    ),
)


def snapshot_document(numbers: Numbers) -> dict[str, object]:
    return {
        "note": SNAPSHOT_NOTE,
        **numbers,
        "written_to": sorted({surface.name for surface in SURFACES}),
    }


def read_snapshot() -> Numbers:
    document = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    return {key: value for key, value in document.items() if isinstance(value, int)}


@dataclass(frozen=True)
class Finding:
    """One surface compared to the numbers: what it says now and what it should say."""

    surface: Surface
    current: str
    rendered: str

    @property
    def stale(self) -> bool:
        return self.current != self.rendered


def compare(numbers: Numbers, root: Path = ROOT) -> list[Finding]:
    """Every surface, as it is on disk beside what the numbers render.

    Raises if a surface's wording is not found exactly once, because a surface that
    was reworded is not current or stale; it is lost, and that must not pass quietly.
    """
    findings = []
    for surface in SURFACES:
        text = (root / surface.path).read_text(encoding="utf-8")
        matches = list(surface.pattern.finditer(text))
        if len(matches) != 1:
            raise LookupError(
                f"{surface.name}: expected exactly one match for its wording, found "
                f"{len(matches)}; restore the wording or teach the script the new one"
            )
        findings.append(Finding(surface, matches[0].group(0), surface.render(numbers)))
    return findings


def write(numbers: Numbers, root: Path = ROOT) -> list[Finding]:
    """Write the snapshot and every stale surface. Returns what was stale."""
    (root / SNAPSHOT_PATH.relative_to(ROOT)).write_text(
        json.dumps(snapshot_document(numbers), ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    stale = [finding for finding in compare(numbers, root) if finding.stale]
    for finding in stale:
        path = root / finding.surface.path
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(finding.current, finding.rendered, 1), encoding="utf-8")
    return stale


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="adopt the numbers")
    args = parser.parse_args()

    numbers = derive()
    snapshot_stale = not SNAPSHOT_PATH.is_file() or read_snapshot() != numbers
    findings = compare(numbers)
    stale = [finding for finding in findings if finding.stale]

    for key, value in numbers.items():
        print(f"  {key:<20} {value:>6,}")
    print()
    print(f"{'stale  ' if snapshot_stale else 'current'}  {SNAPSHOT_PATH.relative_to(ROOT)}")
    for finding in findings:
        print(f"{'stale  ' if finding.stale else 'current'}  {finding.surface.name}")
        if finding.stale:
            print(f"           says:   {finding.current!r}")
            print(f"           should: {finding.rendered!r}")

    if not (snapshot_stale or stale):
        print("\nevery surface is current; nothing to write")
        return 0
    if args.write:
        write(numbers)
        print("\nwritten. Commit the diff with the change that moved the numbers.")
        return 0
    print("\nnot written. Re-run with --write once every line above is intended.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
