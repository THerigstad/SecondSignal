"""The public current-state claims are a fact the tree can check.

On 13 September 2026 a pre-launch audit of the public tree at commit 4b77258
found the README saying the demonstration page was live while
``docs/known-limitations.md`` said there was no demonstration page; the
evaluation document's scope note saying there was no automated runner while
its own addendum described one; one file saying review round 2 had eight
model families and, forty lines later, nine; and the README's "actual output
on the current tree" carrying a roster hash from before the push-3 renames.
None of those lines was a lie when it was written. Each went stale because a
headline fact was repeated by hand in prose and nothing compared the copies.

This module is the audit's remedy: it derives each fact from a committed
structured source or from the package itself and compares only the
deliberately authoritative surfaces. It does not lint historical notes; a
dated record may carry the number that was true on its date.

* the demonstration page: ``demo/index.html`` exists, so the README and the
  limitations page must name it and neither may say it does not exist;
* the runner: ``tests/test_eval_cases.py`` exists, so the evaluation document
  may not say there is none;
* the release identity: ``pyproject.toml``, the newest ``CHANGELOG.md``
  release heading and ``CITATION.cff`` must agree on one version;
* the review-family count: derived from the round-2 fixture documents; every
  sentence on an authoritative page that states round 2's total must carry
  that number (a sentence counting the families that raised a point is not a
  total and is not read);
* the test totals: the README's count must equal what pytest collects, and
  its expected-failure breakdown must equal the case manifest's dispositions;
* the README's sample decision: the block it calls the actual output of
  ``python -m secondsignal`` on the current tree must be that, byte for byte.

What this does not guarantee: that a claim written without the words this
module looks for is caught, or that a number is right anywhere this module
does not look. It looks where the audit found drift.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
LIMITATIONS = (ROOT / "docs" / "known-limitations.md").read_text(encoding="utf-8")
EVALUATION = (ROOT / "docs" / "evaluation.md").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
CITATION = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

DEMO_URL = "https://therigstad.github.io/SecondSignal/"
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}
NUM = r"(" + "|".join(NUMBER_WORDS) + r"|\d+)"
# The phrasings that state round 2's total. "five families raised this point
# in round 2" is a count of something else and is deliberately not matched.
ROUND_TWO_TOTALS = tuple(re.compile(pattern, re.I) for pattern in (
    r"round[ -](?:2|two) \(" + NUM + r" (?:model )?families",          # "review round 2 (nine model families)"
    r"round[ -](?:2|two), all " + NUM + r" (?:model )?families",        # "review round 2, all nine families"
    r"all " + NUM + r" (?:model )?families (?:of|in) (?:review )?round[ -](?:2|two)",
    r"ten returns from " + NUM + r" (?:model )?families",              # the README's own sentence about round 2
))


# --- the demonstration page and the runner exist, so the pages may not say otherwise ----


def test_the_demonstration_page_is_named_where_it_is_live() -> None:
    assert (ROOT / "demo" / "index.html").is_file(), "the demonstration page source is gone; every claim below is void"
    assert DEMO_URL in README, "README no longer links the demonstration page"
    assert DEMO_URL in LIMITATIONS, "the limitations page must say what the demonstration page is and is not"
    for page, name in ((README, "README.md"), (LIMITATIONS, "docs/known-limitations.md"), (EVALUATION, "docs/evaluation.md")):
        assert not re.search(r"\bno demo(nstration)? page yet\b", page, re.I), f"{name} says there is no demonstration page while demo/index.html exists"


def test_the_evaluation_document_does_not_deny_the_runner() -> None:
    assert (ROOT / "tests" / "test_eval_cases.py").is_file()
    assert not re.search(r"\bthere is no automated runner yet\b", EVALUATION, re.I), (
        "docs/evaluation.md says there is no automated runner while tests/test_eval_cases.py exists"
    )


# --- one version, stated in three places ------------------------------------------------


def _pyproject_version() -> str:
    match = re.search(r'^version = "([^"]+)"', PYPROJECT, re.M)
    assert match, "pyproject.toml has no version line"
    return match.group(1)


def _newest_changelog_release() -> str:
    match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", CHANGELOG, re.M)
    assert match, "CHANGELOG.md has no versioned release heading"
    return match.group(1)


def _citation_version() -> str:
    match = re.search(r"^version: (\S+)$", CITATION, re.M)
    assert match, "CITATION.cff has no version line"
    return match.group(1)


def test_the_release_identity_agrees_across_package_changelog_and_citation() -> None:
    package = _pyproject_version()
    assert _newest_changelog_release() == package, (
        f"pyproject.toml says {package} but the newest CHANGELOG release heading says {_newest_changelog_release()}"
    )
    assert _citation_version() == package, f"CITATION.cff says {_citation_version()} but the package says {package}"


# --- the review-family count is derived from the fixtures, never typed ------------------------


def _round_two_families() -> int:
    families = set()
    for path in sorted((ROOT / "evals" / "cases" / "round2_2026-09-08").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document.get("reviewer"), f"{path.name} names no reviewer"
        families.add(document["reviewer"])
    assert families, "no round-2 fixture documents found"
    return len(families)


def test_every_round_two_family_total_on_an_authoritative_page_matches_the_fixtures() -> None:
    derived = _round_two_families()
    problems: list[str] = []
    found = 0
    for text, name in ((README, "README.md"), (LIMITATIONS, "docs/known-limitations.md"), (EVALUATION, "docs/evaluation.md")):
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern in ROUND_TWO_TOTALS:
                for match in pattern.finditer(line):
                    found += 1
                    word = match.group(1).lower()
                    stated = NUMBER_WORDS.get(word) or int(word)
                    if stated != derived:
                        problems.append(f"{name}:{lineno} says {match.group(0)!r}; the round-2 fixtures say {derived}")
    assert found, "no page states round 2's family total any more; if that is deliberate, retire this check on purpose"
    assert not problems, "\n".join(problems)


# --- the test totals on the front page are what pytest collects -----------------------------------


def _collected_tests() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    match = re.search(r"(\d+) tests? collected", result.stdout)
    assert match, f"could not read the collection count:\n{result.stdout[-500:]}\n{result.stderr[-500:]}"
    return int(match.group(1))


def _manifest_dispositions() -> Counter:
    manifest = json.loads((ROOT / "evals" / "case-manifest.json").read_text(encoding="utf-8"))
    return Counter(entry["disposition"] for entry in manifest["cases"])


def test_the_readme_test_count_is_what_pytest_collects() -> None:
    collected = _collected_tests()
    stated = {int(m.replace(",", "")) for m in re.findall(r"\b(\d{1,3}(?:,\d{3})*) tests\b", README)}
    assert stated == {collected}, f"README states {sorted(stated)} tests; pytest collects {collected}"


def test_the_readme_expected_failure_breakdown_is_the_manifest() -> None:
    dispositions = _manifest_dispositions()
    gaps, dissents = dispositions["known_gap"], dispositions["disputed"]
    match = re.search(r"(\d+) expected failures \((\d+) documented gaps, (\d+) recorded dissents\)", README)
    assert match, "README no longer states the expected-failure breakdown in its usual words"
    total, stated_gaps, stated_dissents = (int(m) for m in match.groups())
    assert (stated_gaps, stated_dissents) == (gaps, dissents), (
        f"README says {stated_gaps} gaps and {stated_dissents} dissents; the manifest says {gaps} and {dissents}"
    )
    assert total == gaps + dissents


def test_the_evaluation_page_numbers_paragraph_is_current() -> None:
    """The evaluation page keeps dated "Numbers" paragraphs as history and one
    undated current-numbers paragraph, written by
    ``evals/refresh_public_numbers.py``. The current one is a current-state
    claim and must match the collection count; the dated ones keep the numbers
    that were true on their dates and are not read."""
    match = re.search(r"\*\*Numbers, current\.\*\* (\d{1,3}(?:,\d{3})*) tests", EVALUATION)
    assert match, "docs/evaluation.md has no current-numbers paragraph"
    stated = int(match.group(1).replace(",", ""))
    assert stated == _collected_tests(), (
        f"docs/evaluation.md's current-numbers paragraph says {stated} tests; pytest collects {_collected_tests()}"
    )


# --- the Status table's case counts are the case tree ------------------------------------------------


def _case_tree_counts() -> tuple[int, int, int]:
    """(policy cases, external policy cases, deferred or non-policy cases), from the files."""
    policy = external = deferred = 0
    for path in sorted((ROOT / "evals" / "cases").rglob("*.json")):
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


def test_the_status_table_case_counts_are_the_case_tree() -> None:
    policy, external, deferred = _case_tree_counts()
    manifest_total = sum(_manifest_dispositions().values())
    assert manifest_total == policy, f"the manifest inventories {manifest_total} cases; the tree holds {policy}"
    match = re.search(
        r"(\d+) inventoried in a case manifest, (\d+) of them external reviewer fixtures kept verbatim, "
        r"(\d+) documented gaps and (\d+) recorded dissents;.*?(\d+) deferred fixtures stored and not run",
        README, re.S,
    )
    assert match, "README's Status table no longer states the case counts in its usual words"
    stated = tuple(int(m) for m in match.groups())
    dispositions = _manifest_dispositions()
    derived = (policy, external, dispositions["known_gap"], dispositions["disputed"], deferred)
    assert stated == derived, f"README's Status table says {stated}; the tree says {derived} (inventoried, external, gaps, dissents, deferred)"


# --- the README's sample decision is the actual output, byte for byte ------------------------------


def _readme_sample_block() -> str:
    marker = "This is the actual output of `python -m secondsignal` on the current tree:"
    assert marker in README, "README no longer carries the sample-decision block"
    after = README.split(marker, 1)[1]
    match = re.search(r"\n```\n(.*?)\n```", after, re.S)
    assert match, "README's sample-decision block is not fenced as expected"
    return match.group(1)


def test_the_readme_sample_decision_is_the_actual_output_of_the_current_tree() -> None:
    block = _readme_sample_block()
    first = block.splitlines()[0]
    assert first.startswith("> "), "the sample block must open with the prompt it shows"
    prompt = first[2:]
    result = subprocess.run(
        [sys.executable, "-m", "secondsignal", prompt],
        cwd=ROOT, capture_output=True, text=True, check=True,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "", "PYTHONIOENCODING": "utf-8"},
    )
    lines = result.stdout.splitlines()
    assert lines and lines[0].startswith("--- turn 1 "), result.stdout[:200]
    actual = "\n".join(lines[1:]).rstrip("\n")
    assert actual == block, (
        "README's sample decision is not the current tree's output. Regenerate the block: "
        "run python -m secondsignal with the block's prompt and paste everything after the "
        "turn header. Lines that differ:\n" + "\n".join(
            f"  README: {a!r}\n  actual: {b!r}" for a, b in zip(block.splitlines(), actual.splitlines()) if a != b
        )
    )


# --- the tests badge is the same number as the prose, decoded -------------------------------------


def _readme_tests_badge() -> str:
    """The decoded label of the README's tests badge."""
    match = re.search(r"img\.shields\.io/badge/tests-(.+?)-brightgreen", README)
    assert match, "README no longer carries the tests badge in its usual form"
    return unquote(match.group(1))


def test_the_readme_tests_badge_is_what_pytest_collects() -> None:
    """The badge is the most visible number on the page. It drifted once and the
    prose-only check missed it, because the badge encodes its comma as %2C and
    puts the word 'tests' before the number. Decode it and hold it to the same
    sources as the prose."""
    decoded = _readme_tests_badge()
    match = re.search(r"(\d{1,3}(?:,\d{3})*)\D+(\d+) known gaps\D+(\d+) recorded dissents", decoded)
    assert match, f"the tests badge does not state count, gaps and dissents in its usual words: {decoded!r}"
    count = int(match.group(1).replace(",", ""))
    gaps, dissents = int(match.group(2)), int(match.group(3))
    assert count == _collected_tests(), f"the tests badge says {count} tests; pytest collects {_collected_tests()}"
    dispositions = _manifest_dispositions()
    assert (gaps, dissents) == (dispositions["known_gap"], dispositions["disputed"]), (
        f"the tests badge says {gaps} documented gaps and {dissents} recorded dissents; "
        f"the manifest says {dispositions['known_gap']} and {dispositions['disputed']}"
    )


# --- the release date is stated twice and the two must agree --------------------------------------


def _changelog_newest_release_date() -> str:
    match = re.search(r"^## \[\d+\.\d+\.\d+\] \u2014 (\d{4}-\d{2}-\d{2})", CHANGELOG, re.M)
    assert match, "CHANGELOG.md's newest release heading has no date in its usual form"
    return match.group(1)


def _citation_date_released() -> str:
    match = re.search(r"^date-released: (\d{4}-\d{2}-\d{2})", CITATION, re.M)
    assert match, "CITATION.cff has no date-released line"
    return match.group(1)


def test_the_release_date_agrees_between_changelog_and_citation() -> None:
    """docs/notes/model-provenance.md says repository dates are UTC. The release
    date is stated in the changelog heading and in the citation; the two must
    agree so a hand-edit cannot leave them apart."""
    changelog_date = _changelog_newest_release_date()
    citation_date = _citation_date_released()
    assert changelog_date == citation_date, (
        f"the newest CHANGELOG release is dated {changelog_date} but CITATION.cff's "
        f"date-released is {citation_date}"
    )
