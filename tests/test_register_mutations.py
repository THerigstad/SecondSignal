"""Review round 2's mutations, kept as red regressions.

ChatGPT (round 2, the Codex return and the Chat return) copied the three
guard tests into a synthetic repository and mutated the documents under them:
twenty-six mutations against the register (R01 to R14), the house block and
the codex checks (H01 to H06), and the no-handoff scan (G01 to G08). Twenty
passed the suite as it stood on 8 September; six controls were caught. Every
one is reproduced here against a disposable copy of this tree, and the
hardened checks must catch all twenty-six. A mutation that stops being caught
is a regression in the guard, not in the document it was applied to.

The copy is the real tree (docs, README, src, tests, evals) minus the
virtual environment and the caches, so each probe mutates exactly what the
guards read.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest
import test_adr_index as register
import test_codex_house_block as house
import test_no_security_handoffs as handoff

ROOT = Path(__file__).resolve().parents[1]
IGNORE = shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "*.egg-info", "out")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    copy = tmp_path / "tree"
    for part in ("docs", "src", "tests", "evals"):
        shutil.copytree(ROOT / part, copy / part, ignore=IGNORE)
    shutil.copy(ROOT / "README.md", copy / "README.md")
    return copy


def record(root: Path, number: str) -> Path:
    return next((root / "docs" / "adr").glob(f"{number}-*.md"))


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{path.name}: {old!r} not found"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def mutate_index(root: Path, number: str, **fields: object) -> None:
    index_path = root / "docs" / "adr" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for entry in index["records"]:
        if entry["number"] == number:
            entry.update(fields)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def register_problems(root: Path) -> list[str]:
    return [p for found in register.all_problems(root).values() for p in found]


def house_problems(root: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Run the codex checks against the copy by pointing the module at it."""
    monkeypatch.setattr(house, "ROOT", root)
    monkeypatch.setattr(house, "CODEX_DIR", root / "docs" / "codex")
    monkeypatch.setattr(house, "CANON", root / "docs" / "codex" / "house-block.md")
    monkeypatch.setattr(house, "LOCK", root / "docs" / "codex" / "house-block.lock.json")
    monkeypatch.setattr(house, "PROFILES", root / "src" / "secondsignal" / "profiles")
    problems: list[str] = []
    checks = [
        house.test_the_canonical_block_carries_the_rider_once,
        house.test_the_house_block_is_pinned_by_hash_to_its_version,
        house.test_the_codexes_are_exactly_the_seven_profiles_and_the_three_narrators,
        house.test_each_security_codex_is_titled_by_the_other_two_as_it_titles_itself,
    ]
    per_file = [
        house.test_every_codex_carries_the_house_block_word_for_word,
        house.test_no_part_b_claims_a_harness_power,
    ]
    security_only = [house.test_a_security_codex_claims_no_seat_and_has_no_profile]
    family_only = [house.test_a_family_codex_machine_block_equals_its_profile]
    for check in checks:
        try:
            check()
        except AssertionError as exc:
            problems.append(f"{check.__name__}: {exc}")
    for path in house._codex_files():
        try:
            codex_id = house._codex_id(path)
        except AssertionError as exc:
            problems.append(f"{path.name}: {exc}")
            continue
        for check in per_file + (security_only if codex_id in house.SECURITY else family_only):
            try:
                check(path)
            except AssertionError as exc:
                problems.append(f"{check.__name__}[{path.name}]: {exc}")
    return problems


def assert_baseline_clean(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not register_problems(root)
    assert not house_problems(root, monkeypatch)
    assert not handoff.problems(root)


# --------------------------------------------------------------------------- the register, R01 to R14


def test_the_copy_is_clean_before_any_mutation(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert_baseline_clean(tree, monkeypatch)


def test_r01_relabelling_unwired_as_built_without_the_status_suffix_is_caught(tree: Path) -> None:
    mutate_index(tree, "0014", implementation="built")
    assert any("ADR-0014: record says implementation 'reference-unwired', register says 'built'" in p for p in register.check_status_lines(tree))


def test_r02_implementation_suffix_drift_is_caught(tree: Path) -> None:
    replace(record(tree, "0015"), "**Status:** Accepted — built", "**Status:** Accepted — implementation absent")
    assert any("ADR-0015: record says implementation 'implementation absent'" in p for p in register.check_status_lines(tree))


def test_r03_a_readme_sentence_claiming_acceptance_and_deployment_is_caught(tree: Path) -> None:
    readme = tree / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\nAll Security Division functions are Accepted, built, and deployed.\n", encoding="utf-8")
    assert any("status claim outside the generated block" in p for p in register.check_readme(tree))


def test_r04_a_wrong_title_after_the_right_number_is_caught(tree: Path) -> None:
    path = record(tree, "0023")
    heading = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("# "))
    replace(path, heading, "# ADR-0023: Unrelated title")
    assert any("ADR-0023: heading" in p for p in register.check_titles(tree))


def test_r05_an_unmarked_proposed_citation_in_a_json_fixture_is_caught(tree: Path) -> None:
    (tree / "evals" / "cases" / "claim.json").write_text('{"note": "ADR-0023"}\n', encoding="utf-8")
    assert any("claim.json: ADR-0023 is Proposed but the citation does not say so" in p for p in register.check_fixture_citations(tree))


def test_r06_a_marked_citation_does_not_mask_an_unmarked_one_on_the_same_line(tree: Path) -> None:
    (tree / "src" / "citation_probe.py").write_text("# ADR-0023 unmarked here; ADR-0023 (Proposed) marked there\n", encoding="utf-8")
    assert any("citation_probe.py:1: ADR-0023 is Proposed but the citation does not say so" in p for p in register.check_code_citations(tree))


def test_r07_the_index_cannot_widen_its_own_vocabulary(tree: Path) -> None:
    index_path = tree / "docs" / "adr" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["decision_values"].append("Imaginary")
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mutate_index(tree, "0015", decision="Imaginary")
    replace(record(tree, "0015"), "**Status:** Accepted — built", "**Status:** Imaginary — built")
    assert any("redefines the decision vocabulary" in p for p in register.check_vocabularies(tree))


def test_r08_evidence_names_that_live_only_in_docstrings_are_caught(tree: Path) -> None:
    index = json.loads((tree / "docs" / "adr" / "index.json").read_text(encoding="utf-8"))
    entry = next(r for r in index["records"] if r["number"] == "0015")
    path, _, name = entry["evidence"][0].partition("::")
    module = tree / path
    text = module.read_text(encoding="utf-8")
    text = re.sub(rf"^def {name}\b", f"def renamed_{name}", text, count=1, flags=re.M)
    module.write_text(f'"""{name} is mentioned here and defined nowhere."""\n' + text, encoding="utf-8")
    assert any("a name in a docstring is not a test" in p for p in register.check_evidence(tree))


def test_r09_superseded_with_no_successor_is_caught(tree: Path) -> None:
    mutate_index(tree, "0014", decision="Superseded")
    replace(record(tree, "0014"), "**Status:** Accepted — reference-unwired", "**Status:** Superseded — reference-unwired")
    assert any("ADR-0014 is Superseded with no successor" in p for p in register.check_relationships(tree))


def test_r10_a_prose_pointer_removed_while_the_index_links_remain_is_caught(tree: Path) -> None:
    path = record(tree, "0015")
    text = path.read_text(encoding="utf-8")
    without = "\n".join(line for line in text.splitlines() if "ADR-0023" not in line) + "\n"
    path.write_text(without, encoding="utf-8")
    assert any("ADR-0015 is amended by ADR-0023 in the register but its prose never names ADR-0023" in p for p in register.check_relationships(tree))


def test_r11_accepted_but_not_adopted_is_not_accepted(tree: Path) -> None:
    replace(record(tree, "0015"), "**Status:** Accepted — built", "**Status:** Accepted-but-not-adopted — built")
    assert any("ADR-0015: record says decision 'Accepted-but-not-adopted'" in p for p in register.check_status_lines(tree))


def test_r12_control_a_mismatched_decision_is_caught(tree: Path) -> None:
    replace(record(tree, "0015"), "**Status:** Accepted", "**Status:** Proposed")
    assert any("ADR-0015: record says decision 'Proposed', register says 'Accepted'" in p for p in register.check_status_lines(tree))


def test_r13_control_a_single_unmarked_python_citation_is_caught(tree: Path) -> None:
    (tree / "src" / "citation_probe.py").write_text("# ADR-0023\n", encoding="utf-8")
    assert any("citation_probe.py:1: ADR-0023 is Proposed" in p for p in register.check_code_citations(tree))


def test_r14_control_a_missing_named_module_is_caught(tree: Path) -> None:
    (tree / "src" / "secondsignal" / "jr.py").unlink()
    assert any("module 'src/secondsignal/jr.py' does not exist" in p for p in register.check_evidence(tree))


def test_a_stale_status_claim_in_a_note_under_docs_is_caught(tree: Path) -> None:
    """The live case: the Security Division note said a Proposed record was
    Accepted for two days. Not one of ChatGPT's numbered mutations; the scan
    the families asked for."""
    note = tree / "docs" / "notes" / "probe.md"
    note.write_text("ADR-0019 is Accepted and deployed.\n", encoding="utf-8")
    assert any("probe.md:1" in p and "says ['Accepted']" in p for p in register.check_docs_status_claims(tree))


def test_a_conditional_sentence_about_a_status_is_not_a_claim(tree: Path) -> None:
    note = tree / "docs" / "notes" / "probe.md"
    note.write_text("ADR-0019 flips to Accepted after review round 3 reads it.\n", encoding="utf-8")
    assert not [p for p in register.check_docs_status_claims(tree) if "probe.md" in p]


# --------------------------------------------------------------------------- the house block and the codexes, H01 to H06


def _every_codex(root: Path) -> list[Path]:
    return [p for p in (root / "docs" / "codex").glob("*.md") if p.name != "README.md"]


def test_h01_every_copy_of_part_a_changed_without_a_version_bump_is_caught(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for path in _every_codex(tree):
        replace(path, "You are one voice in a routed household.", "You are one voice in a routed house.")
    problems = house_problems(tree, monkeypatch)
    assert any("changed without a new version" in p for p in problems)


def test_h02_routable_true_beside_routable_false_is_caught(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    replace(tree / "docs" / "codex" / "orrin.md", "- routable: false\n", "- routable: false\n- routable: true\n- domains: grief\n")
    problems = house_problems(tree, monkeypatch)
    assert any("duplicate key 'routable'" in p for p in problems)


def test_h02b_a_routing_field_on_a_security_codex_is_caught_even_without_a_duplicate(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    replace(tree / "docs" / "codex" / "orrin.md", "- routable: false\n", "- routable: false\n- domains: grief\n")
    problems = house_problems(tree, monkeypatch)
    assert any("carries no routing field, found 'domains'" in p for p in problems)


def test_h03_removing_a_characters_own_denial_is_caught(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    replace(tree / "docs" / "codex" / "orrin.md", "- clears_latches: false\n", "")
    replace(tree / "docs" / "codex" / "aya.md", "- grants_authority: false\n", "")
    problems = house_problems(tree, monkeypatch)
    assert any("clears_latches: false" in p for p in problems)
    assert any("grants_authority: false" in p for p in problems)


def test_h04_deleting_the_three_security_codexes_is_caught(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("orrin", "aya", "jr"):
        (tree / "docs" / "codex" / f"{name}.md").unlink()
    problems = house_problems(tree, monkeypatch)
    assert any("test_the_codexes_are_exactly_the_seven_profiles_and_the_three_narrators" in p for p in problems)


def test_h05_a_sentence_granting_clearance_authority_is_caught(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    replace(tree / "docs" / "codex" / "orrin.md", "### What you do", "You may clear latches on operator request.\n\n### What you do")
    problems = house_problems(tree, monkeypatch)
    assert any("claims a power the house never granted" in p and "clear latches" in p for p in problems)


def test_h06_control_editing_one_part_a_is_caught(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    replace(tree / "docs" / "codex" / "orrin.md", "You are one voice in a routed household.", "You are one voice in a routed house.")
    problems = house_problems(tree, monkeypatch)
    assert any("Part A differs from house-block.md" in p for p in problems)


# --------------------------------------------------------------------------- the no-handoff scan, G01 to G08


def _profile(tree: Path, name: str, content: str) -> None:
    (tree / "src" / "secondsignal" / "profiles" / name).write_text(content, encoding="utf-8")


def test_g01_a_yaml_target_with_a_comment_is_caught(tree: Path) -> None:
    _profile(tree, "profile.yaml", "handoffs:\n  - to: orrin # legitimate YAML comment\n")
    assert any("profile.yaml: a YAML profile" in p for p in handoff.problems(tree))


def test_g02_yaml_flow_syntax_is_caught(tree: Path) -> None:
    _profile(tree, "profile.yaml", "handoffs: [{to: orrin}]\n")
    assert any("profile.yaml: a YAML profile" in p for p in handoff.problems(tree))


def test_g03_a_quoted_yaml_key_is_caught(tree: Path) -> None:
    _profile(tree, "profile.yaml", 'handoffs:\n  - "to": "orrin"\n')
    assert any("profile.yaml: a YAML profile" in p for p in handoff.problems(tree))


def test_g04_a_nested_json_target_is_caught(tree: Path) -> None:
    _profile(tree, "profile.json", '{"id": "probe", "handoffs": {"danger": {"to": "orrin"}}}')
    assert any("profile.json: handoff to 'orrin'" in p for p in handoff.problems(tree))


def test_g05_a_security_id_under_an_ordinary_file_name_is_caught(tree: Path) -> None:
    _profile(tree, "profile.json", '{"id": "orrin", "handoffs": []}')
    assert any("profile.json: id is the security id 'orrin'" in p for p in handoff.problems(tree))


def test_g06_an_uppercase_yaml_extension_is_caught(tree: Path) -> None:
    _profile(tree, "profile.YAML", "handoffs:\n  - to: orrin\n")
    assert any("profile.YAML: a YAML profile" in p for p in handoff.problems(tree))


def test_g07_control_an_ordinary_yaml_target_is_caught(tree: Path) -> None:
    _profile(tree, "profile.yaml", "handoffs:\n  - to: orrin\n")
    assert any("profile.yaml" in p for p in handoff.problems(tree))


def test_g08_control_an_ordinary_json_list_target_is_caught(tree: Path) -> None:
    _profile(tree, "profile.json", '{"id": "probe", "handoffs": [{"to": "orrin"}]}')
    assert any("profile.json: handoff to 'orrin'" in p for p in handoff.problems(tree))


def test_an_emptied_profile_root_is_not_a_vacuous_pass(tree: Path) -> None:
    for path in (tree / "src" / "secondsignal" / "profiles").glob("*.json"):
        path.unlink()
    assert any("missing or empty" in p for p in handoff.problems(tree))


def test_the_old_root_level_profiles_directory_may_not_return(tree: Path) -> None:
    (tree / "profiles").mkdir()
    _profile_root = tree / "profiles" / "orrin.json"
    _profile_root.write_text('{"id": "orrin", "handoffs": []}', encoding="utf-8")
    problems = handoff.problems(tree)
    assert any("root-level profiles/ directory is back" in p for p in problems)
