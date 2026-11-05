"""Read immutable fixtures and explicit label provenance as data only."""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .questions import DATA_DIR, ROOT, load_questions

PROVENANCE_PATH = DATA_DIR / "corpus-provenance.json"
FLAGS = ("known_gap", "disputed", "contract_adjusted")


def unconfirmed_authorship(reason: str = "No source settles the label author.") -> dict[str, Any]:
    return {"kind": "unconfirmed", "role": "unconfirmed", "author": "unconfirmed",
            "model_authored": None, "evidence": reason}


def case_disposition(
    case: dict[str, Any], manifest_entry: dict[str, Any] | None = None,
    *, source: str | None = None,
) -> str:
    """Mirror the fixture runner's validated historical closure, without importing it.

    A regression compares this function with the existing runner for the entire
    manifested corpus. Raw fixture flags are retained separately in every row.
    """
    if case.get("known_gap"):
        original = "known_gap"
    elif case.get("disputed"):
        original = "disputed"
    elif case.get("contract_adjusted"):
        original = "contract_adjusted"
    else:
        original = "accepted"
    if manifest_entry is None:
        return original
    if manifest_entry.get("id") != case.get("id"):
        raise ValueError("Manifest entry belongs to a different case")
    if source is not None and manifest_entry.get("source") != source:
        raise ValueError(f"Manifest source differs for {case['id']}")
    disposition = manifest_entry.get("disposition")
    closure_keys = ("previous_disposition", "accepted_by_order", "accepted_on",
                    "acceptance_reason", "previous_mismatch_fields")
    if disposition == original and not any(key in manifest_entry for key in closure_keys):
        return original
    permitted_closure = (
        original == "known_gap"
        and not case.get("disputed")
        and disposition == "accepted"
        and manifest_entry.get("previous_disposition") == "known_gap"
        and manifest_entry.get("accepted_by_order") == "G2B5B"
        and manifest_entry.get("accepted_on") == "2026-11-04"
        and isinstance(manifest_entry.get("reason"), str)
        and bool(manifest_entry["reason"].strip())
        and manifest_entry["reason"] == (
            case.get("gap_note") or case.get("dispute_note") or case.get("why", ""))
        and isinstance(manifest_entry.get("acceptance_reason"), str)
        and bool(manifest_entry["acceptance_reason"].strip())
        and isinstance(manifest_entry.get("previous_mismatch_fields"), list)
        and bool(manifest_entry["previous_mismatch_fields"])
        and all(isinstance(field, str) for field in manifest_entry["previous_mismatch_fields"])
        and set(manifest_entry["previous_mismatch_fields"]) <= set(case.get("expect", {})) | {"id_order"}
        and "mismatch_fields" not in manifest_entry
    )
    if not permitted_closure:
        raise ValueError(f"Unapproved disposition drift for {case['id']}: {original} -> {disposition}")
    return "accepted"


def _authorship(entry: dict[str, Any], case_id: str, field: str) -> dict[str, Any]:
    override = entry.get("case_overrides", {}).get(case_id, {})
    author = override.get("field_authorship", {}).get(
        field, override.get("label_authorship", entry.get("label_authorship")))
    if not isinstance(author, dict):
        return unconfirmed_authorship()
    author = copy.deepcopy(author)
    kind, role = author.get("kind"), author.get("role")
    if kind not in {"human", "model", "unconfirmed"}:
        raise ValueError("invalid label authorship kind")
    if role not in {"operator", "project_manager", "outside_reviewer_model",
                    "build_helper_model", "unconfirmed"}:
        raise ValueError("invalid label authorship role")
    if (role in {"project_manager", "outside_reviewer_model", "build_helper_model"}
            and (kind != "model" or author.get("model_authored") is not True)):
        raise ValueError("a model-authored label cannot be reported as human")
    if author.get("model_authored") is True and kind != "model":
        raise ValueError("a model-authored label cannot be reported as human")
    if kind == "human" and role != "operator":
        raise ValueError("human authorship requires the explicit operator role")
    return author


def labels_for_case(
    case: dict[str, Any], questions: list[dict[str, Any]], entry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Only a declared data mapping may turn an existing field into a question label."""
    labels: dict[str, dict[str, Any]] = {}
    for question in questions:
        label = {"status": "unlabelled", "value": None, "source_field": None,
                 "source_value": None, "authorship": unconfirmed_authorship("No label exists.")}
        source = question.get("label_source")
        if source is not None:
            value: Any = case
            exists = True
            for part in source["field"].split("."):
                if not isinstance(value, dict) or part not in value:
                    exists = False
                    break
                value = value[part]
            if exists:
                label["source_field"] = source["field"]
                label["source_value"] = copy.deepcopy(value)
                label["authorship"] = _authorship(entry, case["id"], source["field"])
                if isinstance(value, str) and value in source["mapping"]:
                    label["status"] = "labelled"
                    label["value"] = source["mapping"][value]
        labels[question["id"]] = label
    return labels


def _scope(document: dict[str, Any], relative: Path) -> str | None:
    if "deferred" in relative.parts:
        return "deferred"
    if document.get("plane", "policy") != "policy":
        return "not_policy"
    if document.get("kind") == "trajectory":
        return "trajectory"
    return None


def load_corpus(
    root: Path = ROOT, provenance_path: Path | None = None,
    questions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Use exactly the single-case fixture scope; report provenance exclusions explicitly."""
    root = Path(root)
    provenance_path = Path(provenance_path or root / "evals/or1/data/corpus-provenance.json")
    document = json.loads(provenance_path.read_text(encoding="utf-8"))
    entries = document.get("files")
    if not isinstance(entries, list):
        raise ValueError("corpus provenance requires a files list")
    by_source: dict[str, dict[str, Any]] = {}
    for entry in entries:
        source = entry.get("source_file")
        if not isinstance(source, str) or source in by_source:
            raise ValueError("duplicate or missing corpus provenance source")
        if entry.get("synthetic") is not True:
            raise ValueError("corpus provenance must explicitly declare synthetic fixtures")
        by_source[source] = entry
    if questions is None:
        questions = load_questions(root / "evals/or1/data/questions.json")
    manifest = json.loads((root / "evals/case-manifest.json").read_text(encoding="utf-8"))
    manifest_by_id = {entry["id"]: entry for entry in manifest["cases"]}
    if len(manifest_by_id) != len(manifest["cases"]):
        raise ValueError("duplicate manifest case id")
    cases: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    out_of_scope: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    discovered: set[str] = set()
    for path in sorted((root / "evals/cases").rglob("*.json")):
        source = path.relative_to(root).as_posix()
        discovered.add(source)
        fixture_document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(fixture_document, dict):
            raise ValueError(f"{source}: case document must be an object")
        entry = by_source.get(source)
        if entry is None:
            for case in fixture_document.get("cases", [fixture_document]):
                excluded.append({"case_id": case.get("id"), "source_file": source,
                                 "reason": "missing_corpus_provenance"})
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if entry.get("sha256") != digest:
            raise ValueError(f"{source}: fixture bytes differ from the provenance record")
        scope = _scope(fixture_document, path.relative_to(root / "evals/cases"))
        if scope is not None:
            out_of_scope.append({"source_file": source, "reason": scope,
                                 "case_count": len(fixture_document.get("cases", [])),
                                 "turn_count": len(fixture_document.get("turns", []))})
            continue
        raw_cases = fixture_document.get("cases")
        if not isinstance(raw_cases, list):
            raise ValueError(f"{source}: selected document requires a cases list")
        manifest_source = path.relative_to(root / "evals/cases").with_suffix("").as_posix()
        for case in raw_cases:
            identifier = case.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in seen_ids:
                raise ValueError(f"{source}: missing or duplicate case id")
            seen_ids.add(identifier)
            if not isinstance(case.get("text"), str):
                raise ValueError(f"{source}::{identifier}: text must be a string")
            if identifier not in manifest_by_id:
                raise ValueError(f"{source}::{identifier}: case is missing from the manifest")
            disposition = case_disposition(case, manifest_by_id[identifier], source=manifest_source)
            existing = {"expect": copy.deepcopy(case.get("expect", {}))}
            for field in ("original_expect", "crisis_category"):
                if field in case:
                    existing[field] = copy.deepcopy(case[field])
            cases.append({
                "case_id": identifier, "source_file": source, "text": case["text"],
                "fixture": copy.deepcopy(case),
                "raw_flags": {flag: copy.deepcopy(case[flag]) for flag in FLAGS if flag in case},
                "effective_flags": {flag: disposition == flag for flag in FLAGS},
                **{flag: copy.deepcopy(case.get(flag, False)) for flag in FLAGS},
                "disposition": disposition,
                "labels": labels_for_case(case, questions, entry),
                "existing_labels": existing,
            })
    coverage = Counter(entry.get("authorship_status", "unconfirmed") for entry in entries)
    return {
        "cases": cases, "excluded": excluded, "out_of_scope": out_of_scope,
        "exclusion_status": "none" if not excluded else "cases_excluded",
        "coverage": {
            "recorded_files": len(entries), "discovered_files": len(discovered),
            "covered_files": len(discovered & set(by_source)),
            "missing_recorded_files": sorted(set(by_source) - discovered),
            "authorship_full_files": coverage["full"],
            "authorship_partial_files": coverage["partial"],
            "authorship_unconfirmed_files": coverage["unconfirmed"],
            "selected_cases": len(cases),
            "dispositions": dict(Counter(case["disposition"] for case in cases)),
        },
    }
