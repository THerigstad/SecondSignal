"""Calibration of separate model records; unknown labels never become negatives."""
from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SET_MEASURES = (
    "exact_match", "jaccard", "micro_f1", "macro_f1", "micro_recall", "macro_recall",
)


def authorship_key(authorship: Mapping[str, Any] | None) -> str:
    """Preserve declared authorship without inferring a human from a role."""
    value = authorship or {}
    return json.dumps(
        {key: value.get(key) for key in ("role", "kind", "author", "model_authored")},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )


def authorship_counts(authorships: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(authorship_key(value) for value in authorships).items()))


def _metric(
    value: float | None, authorships: Sequence[Mapping[str, Any]], *,
    n: int | None = None,
) -> dict[str, Any]:
    return {
        "value": value,
        "n": len(authorships) if n is None else n,
        "labelled_pairs": len(authorships),
        "by_authorship": authorship_counts(authorships),
    }


def _probability(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("probabilities must be finite numbers")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("probabilities must be finite and between zero and one")
    return float(value)


def binary_calibration(
    probabilities: Sequence[float], outcomes: Sequence[int],
    authorships: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Positive-class Brier, ten fixed bins, and weighted absolute bin gaps."""
    if len(probabilities) != len(outcomes):
        raise ValueError("probability and outcome lengths differ")
    authors = list(authorships) if authorships is not None else [{} for _ in outcomes]
    if len(authors) != len(outcomes):
        raise ValueError("authorship and outcome lengths differ")
    pairs = [(_probability(p), y, author) for p, y, author in zip(
        probabilities, outcomes, authors, strict=True,
    )]
    if any(type(y) is not int or y not in (0, 1) for _, y, _ in pairs):
        raise ValueError("binary outcomes must be integer zero or one")
    bins: list[dict[str, Any]] = []
    weighted_gap = 0.0
    for index in range(10):
        members = [(p, y, a) for p, y, a in pairs if min(int(p * 10), 9) == index]
        count = len(members)
        predicted = sum(p for p, _, _ in members) / count if count else None
        observed = sum(y for _, y, _ in members) / count if count else None
        gap = abs(predicted - observed) if count else None
        if gap is not None:
            weighted_gap += count * gap
        bins.append({
            "lower": index / 10, "upper": (index + 1) / 10,
            "upper_inclusive": index == 9, "n": count,
            "by_authorship": authorship_counts([a for _, _, a in members]),
            "mean_probability": predicted, "observed_frequency": observed, "gap": gap,
        })
    size = len(pairs)
    return {
        "status": "computed" if size else "not-computable",
        "n": size, "by_authorship": authorship_counts(authors),
        "brier": _metric(sum((p - y) ** 2 for p, y, _ in pairs) / size if size else None, authors),
        "expected_calibration_error": _metric(weighted_gap / size if size else None, authors),
        "calibration_curve": bins,
    }


def set_measures(
    expected: Sequence[set[str]], predicted: Sequence[set[str]], *,
    labels: Iterable[str] | None = None,
    authorships: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Six set measures for one model, with explicit empty-set conventions.

    Authorship counts refer to labelled question pairs; n refers to cases.
    An empty/empty case has Jaccard one. Undefined precision/recall ratios
    are zero. With no cases every measure is null, never a perfect score.
    """
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted set lengths differ")
    authors = list(authorships) if authorships is not None else [{} for _ in expected]
    count = len(expected)
    universe = set(labels or ())
    for truth, guess in zip(expected, predicted, strict=True):
        universe.update(truth | guess)
    totals = Counter()
    f1_values = []
    recall_values = []
    for label in sorted(universe):
        tp = sum(label in truth and label in guess for truth, guess in zip(expected, predicted))
        fp = sum(label not in truth and label in guess for truth, guess in zip(expected, predicted))
        fn = sum(label in truth and label not in guess for truth, guess in zip(expected, predicted))
        totals.update(tp=tp, fp=fp, fn=fn)
        f1_values.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
        recall_values.append(tp / (tp + fn) if tp + fn else 0.0)
    if count:
        exact = sum(a == b for a, b in zip(expected, predicted)) / count
        jaccard = sum(len(a & b) / len(a | b) if a | b else 1.0
                      for a, b in zip(expected, predicted)) / count
        tp, fp, fn = totals["tp"], totals["fp"], totals["fn"]
        values = (
            exact, jaccard,
            2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            sum(f1_values) / len(f1_values) if f1_values else 0.0,
            tp / (tp + fn) if tp + fn else 0.0,
            sum(recall_values) / len(recall_values) if recall_values else 0.0,
        )
    else:
        values = (None,) * len(SET_MEASURES)
    return {
        "status": "computed" if count else "not-computable",
        "n": count, "labelled_pairs": len(authors),
        "by_authorship": authorship_counts(authors),
        "label_universe": sorted(universe),
        "convention": "empty/empty Jaccard=1; zero-denominator F1/recall=0; no cases=null",
        **{name: _metric(value, authors, n=count) for name, value in zip(SET_MEASURES, values)},
    }


def categorical_agreement(
    left: Sequence[str], right: Sequence[str], *, categories: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Nominal Cohen kappa and Gwet AC1 from paired label records, not predictions."""
    if len(left) != len(right):
        raise ValueError("paired label lengths differ")
    values = set(categories or ()) | set(left) | set(right)
    count = len(left)
    if not count:
        return {"status": "not-computable", "n": 0, "categories": sorted(values),
                "observed_agreement": None, "cohen_kappa": None, "gwet_ac1": None,
                "reason": "No paired second-labeller records are present."}
    if len(values) < 2:
        return {"status": "not-computable", "n": count, "categories": sorted(values),
                "observed_agreement": 1.0, "cohen_kappa": None, "gwet_ac1": None,
                "reason": "At least two declared response categories are required."}
    a, b = Counter(left), Counter(right)
    observed = sum(x == y for x, y in zip(left, right)) / count
    kappa_chance = sum(a[value] * b[value] for value in values) / count ** 2
    pooled = [(a[value] + b[value]) / (2 * count) for value in values]
    ac1_chance = sum(p * (1 - p) for p in pooled) / (len(values) - 1)
    kappa = (observed - kappa_chance) / (1 - kappa_chance) if kappa_chance < 1 else None
    ac1 = (observed - ac1_chance) / (1 - ac1_chance) if ac1_chance < 1 else None
    return {
        "status": "computed" if kappa is not None and ac1 is not None else "partly-computable",
        "n": count, "categories": sorted(values), "observed_agreement": observed,
        "cohen_kappa": kappa, "gwet_ac1": ac1,
        "kappa_chance_agreement": kappa_chance, "ac1_chance_agreement": ac1_chance,
        "reason": "Kappa is undefined for constant matching marginals." if kappa is None else None,
    }


def _label(record: Mapping[str, Any], question: Mapping[str, Any]) -> bool:
    if record.get("status") == "unlabelled":
        return False
    if record.get("status") != "labelled":
        raise ValueError(f"missing or invalid label status for {question['id']}")
    if record.get("value") not in question["allowed_values"]:
        raise ValueError(f"label outside allowed values for {question['id']}")
    return True


def _answer(record: Mapping[str, Any], question: Mapping[str, Any]) -> bool:
    status = record.get("status")
    if status in {"refusal", "malformed"}:
        return False
    if status != "ok" or record.get("answer") not in question["allowed_values"]:
        raise ValueError(f"invalid answer for {question['id']}")
    probabilities = record.get("probabilities")
    if probabilities is not None:
        if not isinstance(probabilities, dict) or set(probabilities) != set(question["allowed_values"]):
            raise ValueError(f"probability options differ for {question['id']}")
        if not math.isclose(sum(_probability(p) for p in probabilities.values()), 1.0,
                            rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"probabilities do not sum to one for {question['id']}")
    return True


def summarize_question(
    rows: Sequence[Mapping[str, Any]], question: Mapping[str, Any],
) -> dict[str, Any]:
    """Question summary; rows must already belong to one requested/reported model."""
    _single_model(rows)
    question_id = question["id"]
    labelled = []
    usable = []
    answer_only = 0
    refusals = malformed = unlabelled = 0
    reasons: Counter[str] = Counter()
    for row in rows:
        label = row["labels"][question_id]
        answer = row["answers"][question_id]
        has_label = _label(label, question)
        valid_answer = _answer(answer, question)
        if has_label:
            labelled.append(label.get("authorship") or {})
        else:
            unlabelled += 1
        if answer["status"] == "refusal":
            refusals += 1
            reasons[str(answer.get("reason") or "reason not supplied")] += 1
        elif answer["status"] == "malformed":
            malformed += 1
        if has_label and valid_answer:
            if answer.get("probabilities") is None:
                answer_only += 1
            else:
                usable.append((label, answer))
    authors = [label.get("authorship") or {} for label, _ in usable]
    summary: dict[str, Any] = {
        "question_id": question_id, "question_type": question["type"],
        "case_count": len(rows), "labelled_pairs": len(labelled),
        "labelled_by_authorship": authorship_counts(labelled), "unlabelled_pairs": unlabelled,
        "calibration_pairs": len(usable), "calibration_by_authorship": authorship_counts(authors),
        "answer_only_pairs": answer_only,
        "refusals": {"count": refusals, "reasons": dict(sorted(reasons.items()))},
        "malformed": malformed,
    }
    if question["type"] == "score":
        empty = binary_calibration([], [])
        summary.update(empty)
        summary["reason"] = "No score calibration scale is specified; score metrics are not computable."
        return summary
    if question["type"] == "yes-or-no":
        positive = question.get("positive_value", "yes")
        if positive not in question["allowed_values"]:
            raise ValueError("yes-or-no question needs its declared positive value")
        summary.update(binary_calibration(
            [answer["probabilities"][positive] for _, answer in usable],
            [int(label["value"] == positive) for label, _ in usable], authors,
        ))
        summary["positive_value"] = positive
        summary["convention"] = "positive-class probability against yes=1, no=0"
    elif question["type"] == "choice":
        options = {
            option: binary_calibration(
                [answer["probabilities"][option] for _, answer in usable],
                [int(label["value"] == option) for label, _ in usable], authors,
            ) for option in question["allowed_values"]
        }
        summary.update({
            "status": "computed" if usable else "not-computable",
            "n": len(usable), "by_authorship": authorship_counts(authors),
            "options": options,
            "convention": "normalized multiclass Brier: mean squared error over all options; "
                          "ECE: mean of optionwise one-vs-rest ECEs",
            "brier": _metric(sum(item["brier"]["value"] for item in options.values()) / len(options)
                             if usable else None, authors),
            "expected_calibration_error": _metric(
                sum(item["expected_calibration_error"]["value"] for item in options.values()) / len(options)
                if usable else None, authors,
            ),
        })
    else:
        raise ValueError(f"unknown question type {question['type']}")
    if not labelled:
        summary["reason"] = "No labels exist for this question; all pairs are excluded from metrics."
    elif not usable:
        summary["reason"] = "No labelled pair has a usable stated probability."
    return summary


def _single_model(rows: Sequence[Mapping[str, Any]]) -> tuple[Any, Any] | None:
    identities = {(row.get("requested_model"), row.get("host_reported_model")) for row in rows}
    if len(identities) > 1:
        raise ValueError("metrics cannot pool requested or host-reported model identities")
    return next(iter(identities)) if identities else None


def _tags(question: Mapping[str, Any], value: Any) -> set[str]:
    question_id = question["id"]
    if question["type"] == "yes-or-no":
        return {question_id} if value == question.get("positive_value", "yes") else set()
    return {question_id + "=" + json.dumps(value, ensure_ascii=False, sort_keys=True)}


def _set_summary(
    rows: Sequence[Mapping[str, Any]], questions: Sequence[Mapping[str, Any]], *, complete: bool,
) -> dict[str, Any]:
    truths, guesses, authors = [], [], []
    universe: set[str] = set()
    for row in rows:
        paired = []
        for question in questions:
            label, answer = row["labels"][question["id"]], row["answers"][question["id"]]
            if question["type"] != "score" and _label(label, question) and _answer(answer, question):
                paired.append((question, label, answer))
        if not paired or (complete and len(paired) != len(questions)):
            continue
        truth: set[str] = set()
        guess: set[str] = set()
        for question, label, answer in paired:
            truth.update(_tags(question, label["value"]))
            guess.update(_tags(question, answer["answer"]))
            for option in question["allowed_values"]:
                universe.update(_tags(question, option))
            authors.append(label.get("authorship") or {})
        truths.append(truth)
        guesses.append(guess)
    result = set_measures(truths, guesses, labels=universe, authorships=authors)
    result["scope"] = "all questions labelled and answered" if complete else "comparable labelled question subset only"
    result["warning"] = None if complete else (
        "Partial annotation changes the measured set. These scores are not full-question-set "
        "performance and must not be compared to a fully labelled benchmark."
    )
    return result


def summarize_model(
    rows: Sequence[Mapping[str, Any]], questions: Sequence[Mapping[str, Any]], requested_model: str,
) -> dict[str, Any]:
    """No averaging across models: reject mixed identities before any computation."""
    identity = _single_model(rows)
    if identity is not None and identity[0] != requested_model:
        raise ValueError("requested model does not match the supplied rows")
    if any(row.get("kind") != "model" for row in rows):
        raise ValueError("model metrics require model rows only")
    keys = [(row["source_file"], row["case_id"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate case/model row would count a case twice")
    question_ids = [question["id"] for question in questions]
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("duplicate question id")
    return {
        "requested_model": requested_model,
        "host_reported_model": identity[1] if identity else None,
        "case_count": len(rows),
        "questions": [summarize_question(rows, question) for question in questions],
        "complete_sets": _set_summary(rows, questions, complete=True),
        "partial_sets": _set_summary(rows, questions, complete=False),
    }


def corpus_agreement(
    label_rows: Sequence[Mapping[str, Any]], questions: Sequence[Mapping[str, Any]], *,
    question_id: str = "crisis_read",
) -> dict[str, Any]:
    """Once for the corpus on one declared scale, never mixed question scales.

    Crisis-read is the default because its imbalance motivates reporting both
    coefficients. Other paired records are counted as outside this declared
    scope; adding a domain label cannot change the crisis agreement statistic.
    """
    left, right, left_authors, right_authors = [], [], [], []
    selected = [question for question in questions if question["id"] == question_id]
    if len(selected) > 1:
        raise ValueError("duplicate agreement question id")
    if selected and selected[0]["type"] == "score":
        raise ValueError("categorical agreement requires a declared categorical scale")
    categories = {json.dumps(value, sort_keys=True)
                  for question in selected for value in question["allowed_values"]}
    by_question: Counter[str] = Counter()
    excluded: Counter[str] = Counter()
    seen = set()
    for row in label_rows:
        if row.get("kind") != "labels":
            raise ValueError("agreement reads label rows, never model predictions")
        key = (row["source_file"], row["case_id"])
        if key in seen:
            raise ValueError("duplicate corpus label row")
        seen.add(key)
        for question in questions:
            a = row["labels"][question["id"]]
            b = row.get("second_labels", {}).get(question["id"])
            if b is None or not _label(a, question) or not _label(b, question):
                continue
            if question["id"] != question_id:
                excluded[question["id"]] += 1
                continue
            left.append(json.dumps(a["value"], sort_keys=True))
            right.append(json.dumps(b["value"], sort_keys=True))
            left_authors.append(a.get("authorship") or {})
            right_authors.append(b.get("authorship") or {})
            by_question[question["id"]] += 1
    result = categorical_agreement(left, right, categories=categories)
    result.update({
        "scope": f"supplied {question_id} label-record agreement, once for the corpus on its declared scale",
        "scope_question_id": question_id,
        "scope_question_present": bool(selected),
        "paired_by_question": dict(sorted(by_question.items())),
        "excluded_by_scope": sum(excluded.values()),
        "excluded_pairs_by_question": dict(sorted(excluded.items())),
        "left_by_authorship": authorship_counts(left_authors),
        "right_by_authorship": authorship_counts(right_authors),
        "both_labellers_explicitly_human": bool(left) and all(
            author.get("kind") == "human" and author.get("model_authored") is False
            for author in [*left_authors, *right_authors]
        ),
        "why_both": "Kappa is unstable under the severe imbalance of crisis labels; report AC1 alongside it.",
        "independence": "Authorship is recorded, not independently verified by this instrument.",
    })
    if not selected:
        result["reason"] = f"The declared agreement question {question_id} is absent from this question set."
    return result
