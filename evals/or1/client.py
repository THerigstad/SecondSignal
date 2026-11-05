"""A fixed offline client and a deliberately unconfigured real client."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


class NotConfigured(RuntimeError):
    """A later operator kit must configure any real model call."""


@dataclass(frozen=True)
class ClientReply:
    host_reported_model: str | None
    raw_response: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost: float | None = None
    currency: str | None = None


class RealClient:
    def __init__(self) -> None:
        raise NotConfigured(
            "Real calls are not configured. Endpoint, model ids, provider route and "
            "spending cap await the operator's later kit. No credential has been read."
        )


class FakeClient:
    """Fixed scripts keyed by model and case position, never by fixture labels."""

    version = "scripted-fake-v1"

    def request(
        self, *, requested_model: str, case: dict[str, Any],
        questions: list[dict[str, Any]], ordinal: int,
    ) -> ClientReply:
        if not requested_model.startswith("fake:"):
            raise NotConfigured("The scripted client accepts only explicit fake identities")
        model_number = int(requested_model.split(":")[1])
        host = f"scripted/fixed-v1/{model_number}"
        if ordinal % 53 == 1:
            return ClientReply(host, "{scripted malformed response", 0, 0, 0.0, "USD")
        answers: dict[str, Any] = {}
        for question in questions:
            qid = question["id"]
            options = question["allowed_values"]
            if qid == "crisis_read" and ordinal % 37 == 0:
                answers[qid] = {
                    "status": "refusal",
                    "reason": "Scripted refusal for refusal-accounting verification.",
                }
                continue
            if question["type"] == "yes-or-no":
                p = (0.1, 0.3, 0.6, 0.8, 0.9)[(ordinal + model_number) % 5]
                distribution = {"yes": p, "no": 1.0 - p}
                answer = "yes" if p >= 0.5 else "no"
            elif question["type"] == "choice":
                chosen = (ordinal + model_number) % len(options)
                distribution = {value: 0.2 / (len(options) - 1) for value in options}
                distribution[options[chosen]] = 0.8
                answer = options[chosen]
            else:
                answers[qid] = {"status": "refusal", "reason": "No score script is supplied."}
                continue
            answers[qid] = {"status": "ok", "answer": answer, "probabilities": distribution}
        return ClientReply(host, json.dumps({"answers": answers}, sort_keys=True), 0, 0, 0.0, "USD")


def _bad(reason: str) -> dict[str, Any]:
    return {"status": "malformed", "answer": None, "probabilities": None, "reason": reason}


def parse_response(raw: str, questions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Do not turn absent, refused, invalid, or non-finite values into negatives."""
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return {q["id"]: _bad("Response is not valid JSON") for q in questions}
    if not isinstance(payload, dict) or not isinstance(payload.get("answers"), dict):
        return {q["id"]: _bad("Response must contain an answers object") for q in questions}
    supplied = payload["answers"]
    if set(supplied) - {q["id"] for q in questions}:
        return {q["id"]: _bad("Response contains an unknown question") for q in questions}
    output: dict[str, dict[str, Any]] = {}
    for question in questions:
        qid = question["id"]
        item = supplied.get(qid)
        if not isinstance(item, dict):
            output[qid] = _bad("Missing answer object")
            continue
        status = item.get("status")
        if status == "refusal":
            reason = item.get("reason")
            output[qid] = (
                {"status": "refusal", "answer": None, "probabilities": None, "reason": reason}
                if isinstance(reason, str) and reason.strip()
                else _bad("Refusal has no reason")
            )
            continue
        if status != "ok":
            output[qid] = _bad("Unknown answer status")
            continue
        answer = item.get("answer")
        options = question["allowed_values"]
        if answer not in options or isinstance(answer, bool):
            output[qid] = _bad("Answer is outside allowed values")
            continue
        probabilities = item.get("probabilities")
        if probabilities is not None:
            valid = (
                isinstance(probabilities, dict)
                and set(probabilities) == set(options)
                and all(
                    type(v) in (float, int) and math.isfinite(v) and 0 <= v <= 1
                    for v in probabilities.values()
                )
                and abs(sum(probabilities.values()) - 1.0) <= 1e-9
            )
            if not valid:
                output[qid] = _bad("Probability map must be finite, complete and sum to one")
                continue
        output[qid] = {
            "status": "ok", "answer": answer, "probabilities": probabilities, "reason": None,
        }
    return output
