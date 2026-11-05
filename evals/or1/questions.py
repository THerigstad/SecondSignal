"""Load the fixed, reviewable measurement questions without policy imports."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
QUESTIONS_PATH = DATA_DIR / "questions.json"
TREE_COMMIT = "6795de2c6b835d1cc72e731a951874b05bf9f42b"


def load_questions(path: Path = QUESTIONS_PATH) -> list[dict[str, Any]]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("question set requires schema_version 1")
    questions = document.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("question set requires a nonempty questions list")
    seen: set[str] = set()
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("each question must be an object")
        identifier = question.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError("question ids must be nonempty and unique")
        seen.add(identifier)
        if not isinstance(question.get("text"), str) or not question["text"].strip():
            raise ValueError(f"{identifier}: question text is required")
        kind = question.get("type")
        values = question.get("allowed_values")
        if kind not in {"yes-or-no", "choice", "score"}:
            raise ValueError(f"{identifier}: unsupported question type")
        if not isinstance(values, list) or not values:
            raise ValueError(f"{identifier}: allowed values must be nonempty")
        if kind == "yes-or-no" and values != ["yes", "no"]:
            raise ValueError(f"{identifier}: yes-or-no options must be ordered yes, no")
        if kind in {"yes-or-no", "choice"}:
            if any(not isinstance(value, str) or not value for value in values):
                raise ValueError(f"{identifier}: choice values must be nonempty strings")
            if len(values) != len(set(values)):
                raise ValueError(f"{identifier}: duplicate allowed value")
        else:
            if any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) for value in values):
                raise ValueError(f"{identifier}: score values must be finite numbers")
        source = question.get("label_source")
        if source is not None:
            if (not isinstance(source, dict) or not isinstance(source.get("field"), str)
                    or not isinstance(source.get("mapping"), dict)):
                raise ValueError(f"{identifier}: invalid label source")
            if any(value not in values for value in source["mapping"].values()):
                raise ValueError(f"{identifier}: label mapping is outside allowed values")
    return questions


def question_set_hash(path: Path = QUESTIONS_PATH) -> str:
    """Hash exact data bytes, including option order and clinical review notes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
