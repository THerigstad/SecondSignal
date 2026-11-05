"""Results and per-question tables; the comparison table never pools models."""
from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .metrics import SET_MEASURES, corpus_agreement, summarize_model
from .provenance import result_document, validate_result, write_json_result, write_markdown_result


def build_report(
    document: Mapping[str, Any], questions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_result(document)
    grouped: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    label_rows = []
    for row in document["rows"]:
        if row["kind"] == "model":
            grouped[(row["requested_model"], row["host_reported_model"])].append(row)
        elif row["kind"] == "labels":
            label_rows.append(row)
    comparison_table = [
        summarize_model(rows, questions, requested)
        for (requested, _), rows in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][1] or ""),
        )
    ]
    payload = {
        "schema_version": 1,
        "mode": document.get("run", {}).get("mode"),
        "completed": document.get("run", {}).get("completed", False),
        "scope": "Each requested/host-reported identity is separate; no vote or pooled model score.",
        "excluded": document.get("excluded", []),
        "out_of_scope": document.get("out_of_scope", []),
        "corpus_agreement": corpus_agreement(label_rows, questions),
        "comparison_table": comparison_table,
    }
    report = result_document(payload, specification_hash="absent")
    report["header"] = dict(document["header"])
    validate_result(report)
    return report


def _cell(value: Any) -> str:
    if value is None:
        return "not computable"
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _authors(counts: Mapping[str, int]) -> str:
    return _cell(json.dumps(counts, ensure_ascii=False, sort_keys=True))


def _curve(lines: list[str], curve: Sequence[Mapping[str, Any]]) -> None:
    lines.extend([
        "", "| Probability bin | n | Mean probability | Observed frequency | Authorship counts |",
        "|---|---:|---:|---:|---|",
    ])
    for item in curve:
        interval = f"[{item['lower']:.1f}, {item['upper']:.1f}{']' if item['upper_inclusive'] else ')'}"
        lines.append(
            f"| {interval} | {item['n']} | {_cell(item['mean_probability'])} | "
            f"{_cell(item['observed_frequency'])} | {_authors(item['by_authorship'])} |"
        )


def render_report(report: Mapping[str, Any]) -> str:
    """Render numbers beside their sample counts and recorded authorship."""
    validate_result(report)
    lines = ["# Calibration measurement tables", ""]
    if report.get("mode") == "scripted_fake":
        lines.append("These scripted fake responses test the instrument. They are not measurements of vendor model quality.")
    lines.extend([
        "", report["scope"], "",
        "Unlabelled pairs, refusals and malformed responses are excluded from calibration. "
        "An answer without probabilities can enter set measures but never gains an invented probability.",
        "", "Complete-set measures require every question to be labelled and answered. "
        "Partial-set measures describe only comparable labelled questions and are not full benchmark scores.",
        "", f"Cases excluded by provenance: {len(report['excluded'])}. "
        + ("None were excluded." if not report["excluded"] else "See the exclusion list in calibration.json."),
    ])
    agreement = report["corpus_agreement"]
    lines.extend([
        "", "## Label-record agreement", "", agreement["why_both"], "",
        f"Scope: {agreement['scope']}. Paired labels: {agreement['n']}.",
        f"Paired records excluded from this scope: {agreement['excluded_by_scope']}; "
        f"by question: {_cell(json.dumps(agreement['excluded_pairs_by_question'], sort_keys=True))}.",
        f"Cohen's kappa: {_cell(agreement['cohen_kappa'])}; Gwet's AC1: {_cell(agreement['gwet_ac1'])}.",
        f"Left authorship counts: {_authors(agreement['left_by_authorship'])}.",
        f"Right authorship counts: {_authors(agreement['right_by_authorship'])}.",
        "Both labellers explicitly recorded as human: " + str(agreement["both_labellers_explicitly_human"]).lower() + ".",
    ])
    if agreement.get("reason"):
        lines.append(agreement["reason"])
    lines.extend(["", agreement["independence"]])
    for model in report["comparison_table"]:
        lines.extend([
            "", f"## Requested model: {_cell(model['requested_model'])}", "",
            f"Host-reported identity: {_cell(model['host_reported_model'])}. Cases: {model['case_count']}.",
        ])
        for name in ("complete_sets", "partial_sets"):
            result = model[name]
            lines.extend([
                "", f"### {'Complete' if name == 'complete_sets' else 'Partial'} set measures", "",
                f"Scope: {result['scope']}. {result['convention']}.",
            ])
            if result["warning"]:
                lines.append(result["warning"])
            lines.extend([
                "", "| Measure | Value | Cases n | Labelled pairs n | Authorship counts |",
                "|---|---:|---:|---:|---|",
            ])
            for metric_name in SET_MEASURES:
                item = result[metric_name]
                lines.append(
                    f"| {metric_name} | {_cell(item['value'])} | {item['n']} | "
                    f"{item['labelled_pairs']} | {_authors(item['by_authorship'])} |"
                )
        for question in model["questions"]:
            lines.extend([
                "", f"### Question: {_cell(question['question_id'])}", "",
                f"Labelled pairs: {question['labelled_pairs']}; unlabelled pairs: {question['unlabelled_pairs']}. "
                f"Label authorship counts: {_authors(question['labelled_by_authorship'])}.",
                f"Answer-only labelled pairs: {question['answer_only_pairs']}.",
                f"Refusals: {question['refusals']['count']} of {question['case_count']}; "
                f"malformed responses: {question['malformed']} of {question['case_count']}. "
                f"Refusal reasons: {_cell(json.dumps(question['refusals']['reasons'], ensure_ascii=False))}.",
            ])
            if question.get("convention"):
                lines.append(question["convention"])
            if question.get("reason"):
                lines.append(question["reason"])
            lines.extend([
                "", "| Metric | Value | Labelled probability pairs n | Authorship counts |",
                "|---|---:|---:|---|",
            ])
            for metric_name in ("brier", "expected_calibration_error"):
                item = question[metric_name]
                lines.append(
                    f"| {metric_name} | {_cell(item['value'])} | {item['n']} | {_authors(item['by_authorship'])} |"
                )
            if "options" in question:
                for option, values in question["options"].items():
                    lines.extend(["", f"Option: {_cell(option)} (one versus rest)."])
                    _curve(lines, values["calibration_curve"])
            elif "calibration_curve" in question:
                _curve(lines, question["calibration_curve"])
    return "\n".join(lines) + "\n"


def write_report(
    output_dir: Path, document: Mapping[str, Any], questions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    report = build_report(document, questions)
    write_json_result(output_dir / "calibration.json", report)
    write_markdown_result(output_dir / "calibration.md", render_report(report), header=report["header"])
    return report
