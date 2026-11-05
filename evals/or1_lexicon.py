"""Read the existing lexicon into evaluation data, without loading the router."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.machinery
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Direct execution must resolve this checkout's evaluation package.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.or1.corpus import load_corpus  # noqa: E402
from evals.or1.provenance import (  # noqa: E402
    ABSENT_SPECIFICATION,
    result_document,
    write_json_result,
)
from evals.or1.questions import TREE_COMMIT, load_questions, question_set_hash  # noqa: E402

_POLICY_NAMESPACE = "_or1_policy"


def load_policy_modules(root: Path = ROOT) -> tuple[types.ModuleType, types.ModuleType]:
    """Load only the existing signals/safety leaves and their relative dependencies.

    The normal package initializer eagerly imports the router. A private package
    namespace supplies only the existing source directory, so Python resolves
    these leaves' relative imports without running that initializer. The source
    files and their adjacent data stay untouched; this namespace is evaluation-only.
    """
    source = str((Path(root) / "src/secondsignal").resolve())
    package = sys.modules.get(_POLICY_NAMESPACE)
    if package is None:
        package = types.ModuleType(_POLICY_NAMESPACE)
        package.__path__ = [source]
        package.__package__ = _POLICY_NAMESPACE
        package.__spec__ = importlib.machinery.ModuleSpec(
            _POLICY_NAMESPACE, loader=None, is_package=True)
        package.__spec__.submodule_search_locations = [source]
        sys.modules[_POLICY_NAMESPACE] = package
    elif getattr(package, "__path__", None) != [source]:
        raise RuntimeError("lexicon namespace already belongs to a different source tree")
    signals = importlib.import_module(_POLICY_NAMESPACE + ".signals")
    safety = importlib.import_module(_POLICY_NAMESPACE + ".safety")
    if _POLICY_NAMESPACE + ".router" in sys.modules:
        raise RuntimeError("the lexicon pass must never load the router")
    return signals, safety


def measure_text(
    text: str, questions: list[dict[str, Any]], *, root: Path = ROOT,
) -> dict[str, Any]:
    signals_module, safety_module = load_policy_modules(root)
    signals = signals_module.extract(text)
    crisis, evidence = safety_module.crisis_read(text)
    domains = sorted(signals.domains)
    readings: dict[str, dict[str, Any]] = {}
    for question in questions:
        identifier = question["id"]
        reading: dict[str, Any] = {
            "status": "unavailable", "answer": None,
            "reason": "The existing lexicon has no declared answer to this probe.",
        }
        if identifier.startswith("domain_present:"):
            domain = identifier.split(":", 1)[1]
            if domain not in signals_module.HOLD_DOMAINS:
                raise ValueError("domain presence question is not an existing hold domain")
            reading = {"status": "answered", "answer": "yes" if domain in domains else "no",
                       "reason": "Membership in the existing extracted domain set."}
        elif identifier == "domain":
            expected = set(signals_module.DOMAIN_LEXICON) | {"none"}
            if set(question["allowed_values"]) != expected:
                raise ValueError("domain options differ from the existing lexicon")
            if len(domains) <= 1:
                reading = {"status": "answered", "answer": domains[0] if domains else "none",
                           "reason": "The extracted set is empty or has one domain."}
            else:
                reading["reason"] = "The lexicon emits several domains and declares no primary one."
        elif identifier == "crisis_read":
            if crisis in {"HIT", "MISS"}:
                reading = {"status": "answered", "answer": "yes" if crisis == "HIT" else "no",
                           "reason": "The existing current-text crisis read."}
            else:
                reading["reason"] = "INCONCLUSIVE is preserved, never converted into a negative."
        readings[identifier] = reading
    return {"questions": readings, "observed": {
        "domains": domains, "crisis_read": crisis,
        "crisis_evidence": [list(item) for item in evidence],
        "scope": "Current-text extraction and crisis screen; no routing or session decision.",
    }}


def build_lexicon(
    *, root: Path = ROOT, questions_path: Path | None = None,
    provenance_path: Path | None = None, output_path: Path | None = None,
) -> dict[str, Any]:
    root = Path(root)
    questions_path = Path(questions_path or root / "evals/or1/data/questions.json")
    provenance_path = Path(provenance_path or root / "evals/or1/data/corpus-provenance.json")
    output_path = Path(output_path or root / "evals/or1/data/lexicon-verdicts.json")
    questions = load_questions(questions_path)
    corpus = load_corpus(root, provenance_path, questions)
    timestamp = datetime.now(timezone.utc).isoformat()
    verdicts = [
        {"case_id": case["case_id"], "source_file": case["source_file"],
         "input_text_sha256": hashlib.sha256(case["text"].encode("utf-8")).hexdigest(),
         **measure_text(case["text"], questions, root=root), "run_timestamp": timestamp}
        for case in corpus["cases"]
    ]
    document = result_document({
        "schema_version": 1, "kind": "or1_lexicon", "verdicts": verdicts,
        "excluded": corpus["excluded"], "exclusion_status": corpus["exclusion_status"],
        "out_of_scope": corpus["out_of_scope"], "coverage": corpus["coverage"],
    }, specification_hash=ABSENT_SPECIFICATION)
    document["header"].update({
        "tree_commit": TREE_COMMIT, "question_set_sha256": question_set_hash(questions_path),
        "corpus_provenance_sha256": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
        "run_timestamp": timestamp,
    })
    write_json_result(output_path, document)
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    document = build_lexicon(output_path=args.output)
    print(f"Wrote {len(document['verdicts'])} lexicon rows; "
          f"{len(document['excluded'])} provenance exclusions.")


if __name__ == "__main__":
    main()
