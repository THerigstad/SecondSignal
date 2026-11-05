"""Run the offline instrument, preserving completed responses across interruptions."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import ClientReply, FakeClient, NotConfigured, RealClient, parse_response
from .corpus import load_corpus
from .provenance import (
    read_json_result,
    result_document,
    validate_result,
    write_json_result,
)
from .questions import DATA_DIR, ROOT, TREE_COMMIT, load_questions, question_set_hash


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_panel(path: Path) -> list[dict[str, Any]]:
    panel = json.loads(path.read_text(encoding="utf-8"))
    if any(panel.get(key) is not None for key in ("endpoint", "provider_route", "spending_cap")):
        raise NotConfigured("Provider configuration belongs to a later operator kit")
    models = panel.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("Model panel must contain at least one entry")
    identities: set[str] = set()
    for model in models:
        if (
            not isinstance(model, dict) or model.get("verification") != "unverified"
            or model.get("model_id") is not None
            or not isinstance(model.get("display_name"), str)
            or not isinstance(model.get("fake_id"), str)
            or re.fullmatch(r"fake:[0-9]+", model["fake_id"]) is None
            or model["fake_id"] in identities
        ):
            raise ValueError("Every panel entry needs a unique fake id and unverified real identity")
        identities.add(model["fake_id"])
    return models


def write_results(path: Path, document: dict[str, Any]) -> None:
    """Validate the entire receipt before any bytes can replace a result."""
    validate_result(document)
    header = document["header"]
    if header["specification_hash"] != "absent":
        raise ValueError("OR1 runs no harness and must write the explicit absent marker")
    for key, width in (("tree_commit", 40), ("question_set_sha256", 64), ("input_digest", 64)):
        if not isinstance(header.get(key), str) or not re.fullmatch(
            f"[0-9a-f]{{{width}}}", header[key]
        ):
            raise ValueError(f"OR1 results require {key}")
    if not isinstance(header.get("run_timestamp"), str) or not header["run_timestamp"]:
        raise ValueError("OR1 results require run_timestamp")
    temporary = path.with_name(path.name + ".tmp")
    write_json_result(temporary, document, compact=True)
    temporary.replace(path)


def _validate_reply(reply: ClientReply) -> None:
    if reply.host_reported_model is not None and not isinstance(reply.host_reported_model, str):
        raise ValueError("Host model identity must be exactly a string or null")
    if not isinstance(reply.raw_response, str):
        raise ValueError("Raw response must be a string")
    for count in (reply.input_tokens, reply.output_tokens):
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError("Token counts must be nonnegative integers or null")
    if reply.cost is not None and (
        type(reply.cost) not in (int, float) or not math.isfinite(reply.cost) or reply.cost < 0
    ):
        raise ValueError("Cost must be finite and nonnegative or null")


def _load_lexicon(path: Path, question_hash: str) -> dict[tuple[str, str], dict[str, Any]]:
    document = read_json_result(path)
    if document["header"].get("question_set_sha256") != question_hash:
        raise ValueError("Lexicon question-set hash differs; regenerate the lexicon pass")
    if document["header"].get("tree_commit") != TREE_COMMIT:
        raise ValueError("Lexicon base-tree identity differs")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in document["verdicts"]:
        key = (row["source_file"], row["case_id"])
        if key in result:
            raise ValueError("Duplicate lexicon case")
        result[key] = row
    return result


def run(
    *, root: Path = ROOT, output: Path | None = None, checkpoint_dir: Path | None = None,
    client: FakeClient | None = None, question_path: Path | None = None,
    provenance_path: Path | None = None, lexicon_path: Path | None = None,
    panel_path: Path | None = None, max_model_rows: int | None = None,
) -> dict[str, Any]:
    """Checkpoint each response through the required results writer, then assemble rows.

    A crash during a response can repeat that unfinished response. Every successfully
    committed response is reused. Input or script changes refuse resume instead of
    silently combining runs. Temporary checkpoint files never count as completed.
    """
    root = Path(root)
    data = root / "evals/or1/data"
    output = Path(output) if output is not None else root / "evals/or1/results/fake.json"
    checkpoint_dir = (
        Path(checkpoint_dir) if checkpoint_dir is not None else output.parent / "checkpoints"
    )
    question_path = Path(question_path) if question_path is not None else data / "questions.json"
    provenance_path = (
        Path(provenance_path) if provenance_path is not None else data / "corpus-provenance.json"
    )
    lexicon_path = Path(lexicon_path) if lexicon_path is not None else data / "lexicon-verdicts.json"
    panel_path = Path(panel_path) if panel_path is not None else data / "model-panel.json"
    client = client if client is not None else FakeClient()
    if not isinstance(client, FakeClient):
        raise NotConfigured("This build supports only the scripted fake client")
    if max_model_rows is not None and (type(max_model_rows) is not int or max_model_rows < 0):
        raise ValueError("max_model_rows must be a nonnegative integer")
    questions = load_questions(question_path)
    qhash = question_set_hash(question_path)
    models = load_panel(panel_path)
    corpus = load_corpus(root=root, provenance_path=provenance_path, questions=questions)
    cases = corpus["cases"]
    lexicon = _load_lexicon(lexicon_path, qhash)
    qids = {q["id"] for q in questions}
    for case in cases:
        key = (case["source_file"], case["case_id"])
        if key not in lexicon or set(lexicon[key]["questions"]) != qids:
            raise ValueError(f"Missing or incomplete lexicon verdict: {key}")
        if lexicon[key].get("input_text_sha256") != hashlib.sha256(case["text"].encode()).hexdigest():
            raise ValueError(f"Lexicon input text differs from the case: {key}")
    # Fingerprint the precise inputs and implementation, including every case/label.
    fingerprint = {
        "questions": qhash,
        "provenance": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
        "lexicon": hashlib.sha256(lexicon_path.read_bytes()).hexdigest(),
        "panel": hashlib.sha256(panel_path.read_bytes()).hexdigest(),
        "corpus": _digest(corpus),
        "script_version": client.version,
        "implementation": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).parent.glob("*.py"))
        },
    }
    input_digest = _digest(fingerprint)
    manifest_path = checkpoint_dir / "run.json"
    if manifest_path.exists():
        saved = read_json_result(manifest_path)
        header = saved["header"]
        if (
            header.get("tree_commit") != TREE_COMMIT
            or header.get("question_set_sha256") != qhash
            or header.get("specification_hash") != "absent"
            or header.get("mode") != "scripted_fake"
        ):
            raise ValueError("Checkpoint run provenance differs")
        if header.get("input_digest") != input_digest or saved.get("inputs") != fingerprint:
            raise ValueError("Resume inputs changed; choose a new checkpoint directory")
    else:
        if checkpoint_dir.exists() and any(checkpoint_dir.glob("*.json")):
            raise ValueError("Checkpoint records exist without their run header")
        header = result_document({}, specification_hash="absent")["header"]
        header.update({
            "tree_commit": TREE_COMMIT, "tree_state": "instrument added to supplied base tree",
            "question_set_sha256": qhash, "input_digest": input_digest,
            "run_timestamp": _now(), "mode": "scripted_fake",
        })
        write_results(manifest_path, {"header": header, "inputs": fingerprint})
    rows: list[dict[str, Any]] = []
    made = reused = pending = 0
    expected_files = {"run.json"}
    for ordinal, case in enumerate(cases):
        key = (case["source_file"], case["case_id"])
        lex = lexicon[key]["questions"]
        base = {
            "case_id": case["case_id"], "source_file": case["source_file"],
            "known_gap": case.get("known_gap", case.get("raw_flags", {}).get("known_gap", False)),
            "disputed": case.get("disputed", case.get("raw_flags", {}).get("disputed", False)),
            "contract_adjusted": case.get(
                "contract_adjusted", case.get("raw_flags", {}).get("contract_adjusted", False)
            ),
            "raw_flags": case["raw_flags"], "effective_flags": case["effective_flags"],
            "disposition": case["disposition"], "labels": case["labels"],
            "existing_labels": case["existing_labels"], "lexicon": lex,
            "input_text_sha256": hashlib.sha256(case["text"].encode()).hexdigest(),
            "requested_model": None, "host_reported_model": None,
            "token_counts": {"input": 0, "output": 0}, "cost": 0.0, "currency": "USD",
            "timestamp": header["run_timestamp"],
        }
        rows.append({
            **base, "kind": "labels", "answers": {
                qid: {
                    "status": label["status"], "answer": label["value"],
                    "probabilities": None, "reason": label.get("reason"),
                } for qid, label in case["labels"].items()
            }, "raw_response": json.dumps(case["existing_labels"], sort_keys=True),
        })
        rows.append({
            **base, "kind": "lexicon", "answers": lex,
            "raw_response": json.dumps(lexicon[key].get("observed", {}), sort_keys=True),
        })
        for model_index, model in enumerate(models):
            name = f"{ordinal:04d}-{model_index}.json"
            expected_files.add(name)
            path = checkpoint_dir / name
            requested = model["fake_id"]
            identity = (case["source_file"], case["case_id"], requested)
            if path.exists():
                record = read_json_result(path)
                if record["header"] != header:
                    raise ValueError("Checkpoint provenance header differs")
                row = record["row"]
                if (row.get("source_file"), row.get("case_id"), row.get("requested_model")) != identity:
                    raise ValueError("Checkpoint row identity differs")
                if record.get("row_sha256") != _digest(row):
                    raise ValueError("Checkpoint row checksum differs")
                if row.get("labels") != base["labels"] or row.get("lexicon") != lex:
                    raise ValueError("Checkpoint evidence differs")
                reused += 1
            elif max_model_rows is not None and made >= max_model_rows:
                pending += 1
                continue
            else:
                reply = client.request(
                    requested_model=requested,
                    case={"case_id": case["case_id"], "text": case["text"]},
                    questions=questions, ordinal=ordinal,
                )
                _validate_reply(reply)
                row = {
                    **base, "kind": "model", "requested_model": requested,
                    "host_reported_model": reply.host_reported_model,
                    "panel_entry": model, "answers": parse_response(reply.raw_response, questions),
                    "raw_response": reply.raw_response,
                    "token_counts": {"input": reply.input_tokens, "output": reply.output_tokens},
                    "cost": reply.cost, "currency": reply.currency, "timestamp": _now(),
                }
                write_results(path, {
                    "header": header, "row": row, "row_sha256": _digest(row),
                })
                made += 1
            rows.append(row)
    unknown = {path.name for path in checkpoint_dir.glob("*.json")} - expected_files
    if unknown:
        raise ValueError(f"Unexpected checkpoint records: {sorted(unknown)}")
    document = {
        "header": header,
        "run": {
            "mode": "scripted_fake", "completed": pending == 0,
            "started_at": header["run_timestamp"], "assembled_at": _now(),
            "new_model_rows": made, "reused_model_rows": reused, "pending_model_rows": pending,
            "case_count": len(cases), "question_count": len(questions), "model_count": len(models),
            "notice": "Fixed scripted answers test the instrument, not vendor or clinical performance.",
        },
        "questions": questions, "model_panel": models, "coverage": corpus["coverage"],
        "excluded": corpus["excluded"], "out_of_scope": corpus["out_of_scope"],
        "exclusion_statement": (
            "No cases excluded by the provenance filter." if not corpus["excluded"]
            else f"{len(corpus['excluded'])} cases excluded by the provenance filter."
        ),
        "rows": rows,
    }
    write_results(output, document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evals/or1/results/fake.json")
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--client", choices=("fake", "real"), default="fake")
    parser.add_argument("--max-model-rows", type=int)
    args = parser.parse_args()
    if args.client == "real":
        RealClient()
    document = run(
        output=args.output, checkpoint_dir=args.checkpoint_dir,
        max_model_rows=args.max_model_rows,
    )
    from .report import write_report
    write_report(args.output.parent, document, load_questions(DATA_DIR / "questions.json"))
    print(json.dumps(document["run"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
