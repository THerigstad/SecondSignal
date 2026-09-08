"""The architecture-decision register is a fact the tree can check.

``docs/adr/index.json`` lists every record with two separate statuses: the
decision (Proposed, Accepted, Superseded) and the implementation (not-code,
none, partial, reference-unwired, built).  These tests refuse the states a
hand-maintained status line cannot notice on its own:

* a record file that is not registered, or a register entry with no file;
* a status line inside a record that disagrees with the register;
* an Accepted record with code behind it that names no evidence test, or a
  test or module that does not exist;
* a citation from code to a record that does not exist, a citation of a
  Proposed record without the marker ``(Proposed)`` beside it, or a stale
  marker on a record that has since been accepted;
* a relationship (amends, supersedes) that does not point both ways;
* a Proposed record, or one whose implementation is none or reference-unwired,
  that the README does not name;
* a reserved number (held for a record not yet written) that has a file, an
  entry, or a citation from code.

Flipping a status is a human act.  The register makes the flip inspectable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = ROOT / "docs" / "adr"
INDEX_PATH = ADR_DIR / "index.json"
README = ROOT / "README.md"

RECORD_FILE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*\.md$")
CITATION = re.compile(r"ADR-(\d{4})")
CODE_ROOTS = ("src", "tests", "evals")
CODE_WITH_IMPLEMENTATION = {"partial", "reference-unwired", "built"}
UNBUILT = {"none", "reference-unwired"}


def _load_index() -> dict:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _records() -> dict[str, dict]:
    index = _load_index()
    records = {r["number"]: r for r in index["records"]}
    assert len(records) == len(index["records"]), "duplicate record numbers in index.json"
    return records


def _status_line(text: str) -> str:
    for line in text.splitlines():
        if "Status" in line and ":" in line:
            return line
    return ""


def _code_files() -> list[Path]:
    files: list[Path] = []
    for root in CODE_ROOTS:
        files.extend(p for p in (ROOT / root).rglob("*.py") if p.name != Path(__file__).name)
    return files


def _evidence_exists(entry: str) -> bool:
    path, _, name = entry.partition("::")
    file = ROOT / path
    if not file.is_file():
        return False
    if not name:
        return True
    return re.search(rf"^\s*def {re.escape(name)}\b", file.read_text(encoding="utf-8"), re.M) is not None


def test_index_uses_only_the_declared_vocabularies() -> None:
    index = _load_index()
    for record in index["records"]:
        assert record["decision"] in index["decision_values"], record["number"]
        assert record["implementation"] in index["implementation_values"], record["number"]
        for key in ("number", "file", "title", "evidence", "modules"):
            assert key in record, f"{record.get('number')}: missing {key}"


def test_every_record_file_is_registered_and_every_entry_has_a_file() -> None:
    on_disk = {p.name for p in ADR_DIR.iterdir() if RECORD_FILE.match(p.name)}
    registered = {r["file"] for r in _records().values()}
    assert on_disk == registered, {
        "unregistered files": sorted(on_disk - registered),
        "entries without a file": sorted(registered - on_disk),
    }
    for number, record in _records().items():
        assert record["file"].startswith(number + "-"), f"{number}: file name does not carry the number"


def test_the_status_line_inside_each_record_agrees_with_the_register() -> None:
    for number, record in _records().items():
        text = (ADR_DIR / record["file"]).read_text(encoding="utf-8")
        line = _status_line(text)
        assert line, f"ADR-{number}: no Status line"
        declared = line.split(":", 1)[1].strip().lstrip("*").strip()
        assert declared.startswith(record["decision"]), (
            f"ADR-{number}: record says {declared!r}, register says {record['decision']!r}"
        )


def test_accepted_records_with_code_name_evidence_and_modules_that_exist() -> None:
    for number, record in _records().items():
        if record["implementation"] in CODE_WITH_IMPLEMENTATION:
            assert record["evidence"], f"ADR-{number}: implementation {record['implementation']} but no evidence test named"
            assert record["modules"], f"ADR-{number}: implementation {record['implementation']} but no module named"
        for entry in record["evidence"]:
            assert _evidence_exists(entry), f"ADR-{number}: evidence {entry!r} does not exist"
        for module in record["modules"]:
            assert (ROOT / module).is_file(), f"ADR-{number}: module {module!r} does not exist"
        if record["implementation"] in {"none", "not-code"}:
            assert not record["modules"], f"ADR-{number}: implementation {record['implementation']} names a module"


def test_every_citation_from_code_resolves_and_carries_the_right_marker() -> None:
    records = _records()
    problems: list[str] = []
    for file in _code_files():
        for lineno, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            for match in CITATION.finditer(line):
                number = match.group(1)
                where = f"{file.relative_to(ROOT)}:{lineno}"
                record = records.get(number)
                if record is None:
                    problems.append(f"{where}: ADR-{number} is not in the register")
                    continue
                marked = re.search(rf"ADR-{number}\s*\(Proposed\)", line) is not None
                if record["decision"] == "Proposed" and not marked:
                    problems.append(f"{where}: ADR-{number} is Proposed but the citation does not say so")
                if record["decision"] != "Proposed" and marked:
                    problems.append(f"{where}: ADR-{number} is {record['decision']} but the citation still says Proposed")
    assert not problems, "\n".join(problems)


def test_relationships_point_both_ways() -> None:
    records = _records()
    for number, record in records.items():
        for target in record.get("amends", []):
            assert target in records, f"ADR-{number} amends ADR-{target}, which is not registered"
            assert number in records[target].get("amended_by", []), (
                f"ADR-{number} amends ADR-{target} but ADR-{target} does not list it under amended_by"
            )
        for target in record.get("supersedes", []):
            assert target in records, f"ADR-{number} supersedes ADR-{target}, which is not registered"
            assert records[target]["decision"] == "Superseded", f"ADR-{target} is superseded by ADR-{number} but is not marked Superseded"
            assert number in records[target].get("superseded_by", []), (
                f"ADR-{number} supersedes ADR-{target} but ADR-{target} does not list it under superseded_by"
            )
        for source in record.get("amended_by", []):
            assert number in records[source].get("amends", []), f"ADR-{number} lists ADR-{source} under amended_by, but ADR-{source} does not amend it"
        for source in record.get("superseded_by", []):
            assert number in records[source].get("supersedes", []), f"ADR-{number} lists ADR-{source} under superseded_by, but ADR-{source} does not supersede it"


def test_the_readme_names_every_proposed_or_unbuilt_record() -> None:
    readme = README.read_text(encoding="utf-8")
    missing = [
        number
        for number, record in _records().items()
        if (record["decision"] == "Proposed" or record["implementation"] in UNBUILT)
        and f"ADR-{number}" not in readme
    ]
    assert not missing, f"README does not name these Proposed or unbuilt records: {missing}"


def test_reserved_numbers_have_no_file_no_entry_and_no_citation() -> None:
    index = _load_index()
    reserved = {r["number"] for r in index.get("reserved", [])}
    records = _records()
    for number in sorted(reserved):
        assert number not in records, f"ADR-{number} is reserved and registered at the same time"
        on_disk = [p.name for p in ADR_DIR.iterdir() if p.name.startswith(number + "-")]
        assert not on_disk, f"ADR-{number} is reserved but a file exists: {on_disk}"
    cited: list[str] = []
    for file in _code_files():
        for lineno, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            for match in CITATION.finditer(line):
                if match.group(1) in reserved:
                    cited.append(f"{file.relative_to(ROOT)}:{lineno}: ADR-{match.group(1)} is reserved, not written")
    assert not cited, "\n".join(cited)


@pytest.mark.parametrize("number", sorted(_records()))
def test_each_record_has_a_title_that_matches_its_heading(number: str) -> None:
    record = _records()[number]
    text = (ADR_DIR / record["file"]).read_text(encoding="utf-8")
    heading = next((line for line in text.splitlines() if line.startswith("# ")), "")
    assert heading.startswith(f"# ADR-{number}:"), f"ADR-{number}: heading {heading!r} does not carry its number"
