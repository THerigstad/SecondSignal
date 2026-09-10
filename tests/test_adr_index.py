"""The architecture-decision register is a fact the tree can check.

``docs/adr/index.json`` lists every record with two separate statuses: the
decision (Proposed, Accepted, Superseded) and the implementation (not-code,
none, partial, reference-unwired, built).  These tests refuse the states a
hand-maintained status line cannot notice on its own:

* a record file that is not registered, or a register entry with no file;
* a status line inside a record whose decision word or implementation word
  disagrees with the register, on either axis, parsed exactly (not by prefix);
* a vocabulary word the register invented for itself (the two vocabularies
  are frozen here, outside the file under test);
* an Accepted record with code behind it that names no evidence test, an
  evidence entry that is not a real, collected, unskipped test function (a
  name in a docstring is not a test), or a module that does not exist;
* a citation from code or from a fixture to a record that does not exist, a
  citation of a Proposed record without the marker ``(Proposed)`` beside it
  (every occurrence on the line, not the first), or a stale marker on a
  record that has since been accepted;
* a relationship (amends, supersedes) that does not point both ways in the
  register, or that the record's own prose does not mention;
* a Superseded record with no successor;
* a heading whose title text differs from the registered title;
* a Proposed record, or one whose implementation is none or reference-unwired,
  that the README does not name;
* a README whose generated status block differs from the register's
  rendering, or that makes a status claim outside that block;
* a line anywhere under ``docs/`` that says a record is Accepted, Proposed or
  Superseded when the register says otherwise (a stated status, not a
  conditional one);
* a reserved number (held for a record not yet written) that has a file, an
  entry, or a citation from code.

What the register does not guarantee, stated so nobody reads more into a
green run than it says: that an evidence test passes (CI shows that for the
exact commit); that "built" means correct; that a status claim written
without the ``ADR-NNNN`` form is caught by the docs scan.  Review round 2
(ChatGPT, mutations R01 to R14) found the first eleven of these gaps; every
one is a red regression in ``tests/test_register_mutations.py``.

Flipping a status is a human act.  The register makes the flip inspectable.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

RECORD_FILE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
CITATION = re.compile(r"ADR-(\d{4})")
MARKED = re.compile(r"ADR-(\d{4})\s*\(Proposed\)")
STATUS_WORD = re.compile(r"\b(Accepted|Proposed|Superseded)\b")
CONDITIONAL = re.compile(
    r"\b(until|after|when|before|flip|flips|flipped|flipping|becomes?|would|will|was|were|"
    r"originally|later|not yet|if|once|never|stays?|remains?|stayed|kept|keeps?|round 3|"
    r"second family|cannot|can never|read as|treated as)\b",
    re.I,
)
CODE_ROOTS = ("src", "tests", "evals")
FIXTURE_ROOTS = ("evals", "src")
# The reviewer's own words in an external fixture are quoted material, not the
# project's citations: they are never edited and never marked.
REVIEWER_FIELDS = frozenset({"text", "why", "original_expect", "reviewer_session", "reviewer_prior_turns", "source_id", "prior_turns"})
# Generated copies of fixture notes, truncated; the fixtures themselves are checked.
UNSCANNED_JSON = frozenset({"evals/case-manifest.json", "docs/adr/index.json"})

# The two vocabularies, frozen outside the index so the file under test cannot
# widen its own schema (review round 2, ChatGPT, mutation R07).
DECISION_VALUES = frozenset({"Proposed", "Accepted", "Superseded"})
IMPLEMENTATION_VALUES = frozenset({"not-code", "none", "partial", "reference-unwired", "built"})
CODE_WITH_IMPLEMENTATION = {"partial", "reference-unwired", "built"}
UNBUILT = {"none", "reference-unwired"}
SKIP_MARKS = {"skip", "skipif", "xfail"}


# --------------------------------------------------------------------------- helpers, all root-parametrised


def load_index(root: Path = ROOT) -> dict:
    return json.loads((root / "docs" / "adr" / "index.json").read_text(encoding="utf-8"))


def records_of(root: Path = ROOT) -> dict[str, dict]:
    index = load_index(root)
    records = {r["number"]: r for r in index["records"]}
    assert len(records) == len(index["records"]), "duplicate record numbers in index.json"
    return records


def parse_status_line(text: str) -> tuple[str, str] | None:
    """The status line's grammar: ``- **Status:** <Decision> — <implementation>; <prose>``.

    Both words are parsed exactly. A line that does not fit the grammar
    returns None and fails the test that reads it. Only the first line that
    begins with the bold Status label counts, so a heading above it cannot
    hijack the parse (review round 2, Kimi and GLM)."""
    for line in text.splitlines():
        stripped = line.strip().lstrip("-").strip()
        if not stripped.startswith("**Status:**"):
            continue
        body = stripped[len("**Status:**"):].strip()
        if " — " not in body:
            return None
        decision, rest = body.split(" — ", 1)
        implementation = re.split(r"[;(]", rest, 1)[0].strip()
        return decision.strip(), implementation
    return None


def code_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for sub in CODE_ROOTS:
        files.extend(p for p in (root / sub).rglob("*.py") if p.name != "test_adr_index.py" and p.name != "test_register_mutations.py")
    return files


def fixture_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for sub in FIXTURE_ROOTS:
        files.extend(p for p in (root / sub).rglob("*.json") if p.relative_to(root).as_posix() not in UNSCANNED_JSON)
    return files


def _strings_authored_by_the_project(value: object, external: bool) -> list[str]:
    """Every string in a JSON document except the reviewer's own fields."""
    out: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if external and key in REVIEWER_FIELDS:
                continue
            out.extend(_strings_authored_by_the_project(item, external))
    elif isinstance(value, list):
        for item in value:
            out.extend(_strings_authored_by_the_project(item, external))
    elif isinstance(value, str):
        out.append(value)
    return out


def evidence_problem(entry: str, root: Path = ROOT) -> str | None:
    """None when the entry names a real, collected, unskipped test function.

    A module path alone is accepted (the file must exist). A ``path::name``
    entry must resolve to a function definition in that module's AST, not a
    mention in a docstring (mutation R08), whose name starts with ``test``
    and which carries no skip, skipif or xfail mark and calls neither
    ``pytest.skip`` nor ``pytest.xfail`` in its body."""
    path, _, name = entry.partition("::")
    file = root / path
    if not file.is_file():
        return f"{entry!r}: file does not exist"
    if not name:
        return None
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"))
    except SyntaxError as exc:  # pragma: no cover - a syntax error fails collection anyway
        return f"{entry!r}: module does not parse ({exc})"
    functions = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if not functions:
        return f"{entry!r}: no function of that name is defined (a name in a docstring is not a test)"
    function = functions[0]
    if not function.name.startswith("test"):
        return f"{entry!r}: not a test function"
    for decorator in function.decorator_list:
        text = ast.unparse(decorator)
        if any(f"mark.{mark}" in text for mark in SKIP_MARKS):
            return f"{entry!r}: the evidence test is marked {text}; a skipped or expected-to-fail test is not evidence"
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            called = ast.unparse(node.func)
            if called in {"pytest.skip", "pytest.xfail", "skip", "xfail"}:
                return f"{entry!r}: the evidence test calls {called}; a test that skips itself is not evidence"
    return None


def render_status_block(root: Path = ROOT) -> str:
    spec = importlib.util.spec_from_file_location("render_status", root / "docs" / "adr" / "render_status.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render(load_index(root))


# --------------------------------------------------------------------------- the checks, each returning problems


def check_vocabularies(root: Path = ROOT) -> list[str]:
    index = load_index(root)
    problems: list[str] = []
    if set(index["decision_values"]) != DECISION_VALUES:
        problems.append(f"index.json redefines the decision vocabulary: {index['decision_values']}")
    if set(index["implementation_values"]) != IMPLEMENTATION_VALUES:
        problems.append(f"index.json redefines the implementation vocabulary: {index['implementation_values']}")
    for record in index["records"]:
        if record["decision"] not in DECISION_VALUES:
            problems.append(f"ADR-{record['number']}: decision {record['decision']!r} is not in the vocabulary")
        if record["implementation"] not in IMPLEMENTATION_VALUES:
            problems.append(f"ADR-{record['number']}: implementation {record['implementation']!r} is not in the vocabulary")
        for key in ("number", "file", "title", "evidence", "modules"):
            if key not in record:
                problems.append(f"ADR-{record.get('number')}: missing {key}")
    return problems


def check_files(root: Path = ROOT) -> list[str]:
    adr_dir = root / "docs" / "adr"
    on_disk = {p.name for p in adr_dir.iterdir() if RECORD_FILE.match(p.name)}
    records = records_of(root)
    registered = {r["file"] for r in records.values()}
    problems: list[str] = []
    for name in sorted(on_disk - registered):
        problems.append(f"{name}: record file not registered")
    for name in sorted(registered - on_disk):
        problems.append(f"{name}: registered entry has no file")
    for number, record in records.items():
        if not record["file"].startswith(number + "-"):
            problems.append(f"ADR-{number}: file name does not carry the number")
    return problems


def check_status_lines(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    for number, record in records_of(root).items():
        text = (root / "docs" / "adr" / record["file"]).read_text(encoding="utf-8")
        parsed = parse_status_line(text)
        if parsed is None:
            problems.append(f"ADR-{number}: no status line in the grammar '- **Status:** <Decision> — <implementation>; ...'")
            continue
        decision, implementation = parsed
        if decision != record["decision"]:
            problems.append(f"ADR-{number}: record says decision {decision!r}, register says {record['decision']!r}")
        if implementation != record["implementation"]:
            problems.append(f"ADR-{number}: record says implementation {implementation!r}, register says {record['implementation']!r}")
    return problems


def check_titles(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    for number, record in records_of(root).items():
        text = (root / "docs" / "adr" / record["file"]).read_text(encoding="utf-8")
        heading = next((line for line in text.splitlines() if line.startswith("# ")), "")
        expected = f"# ADR-{number}: {record['title']}"
        if heading.strip() != expected:
            problems.append(f"ADR-{number}: heading {heading!r} is not {expected!r}")
    return problems


def check_evidence(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    for number, record in records_of(root).items():
        if record["implementation"] in CODE_WITH_IMPLEMENTATION:
            if not record["evidence"]:
                problems.append(f"ADR-{number}: implementation {record['implementation']} but no evidence test named")
            if not record["modules"]:
                problems.append(f"ADR-{number}: implementation {record['implementation']} but no module named")
        for entry in record["evidence"]:
            problem = evidence_problem(entry, root)
            if problem:
                problems.append(f"ADR-{number}: evidence {problem}")
        for module in record["modules"]:
            if not (root / module).is_file():
                problems.append(f"ADR-{number}: module {module!r} does not exist")
        if record["implementation"] in {"none", "not-code"} and record["modules"]:
            problems.append(f"ADR-{number}: implementation {record['implementation']} names a module")
    return problems


def _citation_problems(line: str, where: str, records: dict[str, dict]) -> list[str]:
    problems: list[str] = []
    marked_spans = [(m.start(), m.end()) for m in MARKED.finditer(line)]
    for match in CITATION.finditer(line):
        number = match.group(1)
        record = records.get(number)
        if record is None:
            problems.append(f"{where}: ADR-{number} is not in the register")
            continue
        marked = any(start <= match.start() < end for start, end in marked_spans)
        if record["decision"] == "Proposed" and not marked:
            problems.append(f"{where}: ADR-{number} is Proposed but the citation does not say so")
        if record["decision"] != "Proposed" and marked:
            problems.append(f"{where}: ADR-{number} is {record['decision']} but the citation still says Proposed")
    return problems


def check_code_citations(root: Path = ROOT) -> list[str]:
    records = records_of(root)
    problems: list[str] = []
    for file in code_files(root):
        for lineno, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            problems.extend(_citation_problems(line, f"{file.relative_to(root)}:{lineno}", records))
    return problems


def check_fixture_citations(root: Path = ROOT) -> list[str]:
    """JSON fixtures cite records too (mutation R05); a reviewer's verbatim
    fields are quoted material and are skipped."""
    records = records_of(root)
    problems: list[str] = []
    for file in fixture_files(root):
        try:
            document = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{file.relative_to(root)}: not JSON ({exc})")
            continue
        external = isinstance(document, dict) and document.get("external") is True
        for text in _strings_authored_by_the_project(document, external):
            for line in text.splitlines():
                problems.extend(_citation_problems(line, str(file.relative_to(root)), records))
    return sorted(set(problems))


def check_relationships(root: Path = ROOT) -> list[str]:
    records = records_of(root)
    problems: list[str] = []
    texts = {n: (root / "docs" / "adr" / r["file"]).read_text(encoding="utf-8") for n, r in records.items()}
    for number, record in records.items():
        for target in record.get("amends", []):
            if target not in records:
                problems.append(f"ADR-{number} amends ADR-{target}, which is not registered")
                continue
            if number not in records[target].get("amended_by", []):
                problems.append(f"ADR-{number} amends ADR-{target} but ADR-{target} does not list it under amended_by")
            if f"ADR-{target}" not in texts[number]:
                problems.append(f"ADR-{number} amends ADR-{target} in the register but its prose never names ADR-{target}")
        for target in record.get("supersedes", []):
            if target not in records:
                problems.append(f"ADR-{number} supersedes ADR-{target}, which is not registered")
                continue
            if records[target]["decision"] != "Superseded":
                problems.append(f"ADR-{target} is superseded by ADR-{number} but is not marked Superseded")
            if number not in records[target].get("superseded_by", []):
                problems.append(f"ADR-{number} supersedes ADR-{target} but ADR-{target} does not list it under superseded_by")
            if f"ADR-{target}" not in texts[number]:
                problems.append(f"ADR-{number} supersedes ADR-{target} in the register but its prose never names ADR-{target}")
        for source in record.get("amended_by", []):
            if source not in records or number not in records[source].get("amends", []):
                problems.append(f"ADR-{number} lists ADR-{source} under amended_by, but ADR-{source} does not amend it")
            if f"ADR-{source}" not in texts[number]:
                problems.append(f"ADR-{number} is amended by ADR-{source} in the register but its prose never names ADR-{source}")
        for source in record.get("superseded_by", []):
            if source not in records or number not in records[source].get("supersedes", []):
                problems.append(f"ADR-{number} lists ADR-{source} under superseded_by, but ADR-{source} does not supersede it")
            if f"ADR-{source}" not in texts[number]:
                problems.append(f"ADR-{number} is superseded by ADR-{source} in the register but its prose never names ADR-{source}")
        if record["decision"] == "Superseded" and not record.get("superseded_by"):
            problems.append(f"ADR-{number} is Superseded with no successor (mutation R09)")
    return problems


def check_readme(root: Path = ROOT) -> list[str]:
    readme = (root / "README.md").read_text(encoding="utf-8")
    records = records_of(root)
    problems: list[str] = []
    for number, record in records.items():
        if (record["decision"] == "Proposed" or record["implementation"] in UNBUILT) and f"ADR-{number}" not in readme:
            problems.append(f"README does not name the Proposed or unbuilt record ADR-{number}")
    begin = "<!-- adr-status:begin"
    end = "<!-- adr-status:end -->"
    if readme.count(begin) != 1 or readme.count(end) != 1:
        problems.append("README must carry the generated status block exactly once, between its two markers")
        return problems
    start = readme.index(begin)
    stop = readme.index(end) + len(end)
    block = readme[start:stop]
    expected = render_status_block(root)
    if block != expected:
        problems.append("README's status block differs from the register's rendering; run python docs/adr/render_status.py --write")
    outside = readme[:start] + readme[stop:]
    for lineno, line in enumerate(outside.splitlines(), 1):
        if STATUS_WORD.search(line):
            problems.append(f"README makes a status claim outside the generated block: {line.strip()[:100]!r}")
    return problems


def check_docs_status_claims(root: Path = ROOT) -> list[str]:
    """A line under docs/ that names a record with the ADR-NNNN form and calls
    it Accepted, Proposed or Superseded must agree with the register, unless
    the sentence is conditional (until, after, flips, becomes ...). A
    record's own file may use its own status word beside another record's
    number. The Security Division note of 8 September carried a stale
    'Accepted' for a Proposed record for two days; this is what notices."""
    records = records_of(root)
    problems: list[str] = []
    for file in sorted((root / "docs").rglob("*.md")):
        own = RECORD_FILE.match(file.name)
        own_number = own.group(1) if own else None
        for lineno, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            numbers = set(CITATION.findall(line))
            words = set(STATUS_WORD.findall(line))
            if not numbers or not words:
                continue
            if own_number:
                numbers.add(own_number)
            allowed = {records[n]["decision"] for n in numbers if n in records}
            if not allowed:
                continue
            stray = words - allowed
            if stray and not CONDITIONAL.search(line):
                problems.append(
                    f"{file.relative_to(root)}:{lineno}: names {sorted('ADR-' + n for n in numbers)} "
                    f"({', '.join(sorted(allowed))} in the register) but says {sorted(stray)}"
                )
    return problems


def check_reserved(root: Path = ROOT) -> list[str]:
    index = load_index(root)
    reserved = {r["number"] for r in index.get("reserved", [])}
    records = records_of(root)
    problems: list[str] = []
    adr_dir = root / "docs" / "adr"
    for number in sorted(reserved):
        if number in records:
            problems.append(f"ADR-{number} is reserved and registered at the same time")
        on_disk = [p.name for p in adr_dir.iterdir() if p.name.startswith(number + "-")]
        if on_disk:
            problems.append(f"ADR-{number} is reserved but a file exists: {on_disk}")
    for file in code_files(root):
        for lineno, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            for match in CITATION.finditer(line):
                if match.group(1) in reserved:
                    problems.append(f"{file.relative_to(root)}:{lineno}: ADR-{match.group(1)} is reserved, not written")
    return problems


CHECKS = {
    "vocabularies": check_vocabularies,
    "files": check_files,
    "status_lines": check_status_lines,
    "titles": check_titles,
    "evidence": check_evidence,
    "code_citations": check_code_citations,
    "fixture_citations": check_fixture_citations,
    "relationships": check_relationships,
    "readme": check_readme,
    "docs_status_claims": check_docs_status_claims,
    "reserved": check_reserved,
}


def all_problems(root: Path = ROOT) -> dict[str, list[str]]:
    """Every check's findings against one tree; the mutation tests read this."""
    return {name: check(root) for name, check in CHECKS.items()}


# --------------------------------------------------------------------------- the tests


@pytest.mark.parametrize("name", sorted(CHECKS))
def test_the_register_holds(name: str) -> None:
    problems = CHECKS[name](ROOT)
    assert not problems, "\n".join(problems)


def test_the_index_note_names_the_test_that_enforces_it() -> None:
    assert "tests/test_adr_index.py" in load_index()["note"]
