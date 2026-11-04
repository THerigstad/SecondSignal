"""Record exact compound-stutter misses exposed by the second-broom cohort.

These are B6 residuals, not a new transform-wide exemption. Every source was
recovered by the full BEFORE wider_all candidate and was absent from the
frozen BEFORE current-crisis cohort. Generate with --write; --check compares
without writing. The full fuzz still executes every transform on every line.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from evals.fuzz.run import FuzzResult, run  # noqa: E402
from evals.fuzz.transforms import KNOWN_GAP_TRANSFORMS  # noqa: E402

MEASUREMENT = ROOT / "evals/fuzz/measurements/second_broom_compound_stutter_2026-11-04.json"
BEFORE = ROOT / "evals/gap_triage/measurements/second_broom_before_2026-11-04.json"
COHORT = ROOT / "evals/gap_triage/measurements/second_broom_before_cohorts_2026-11-04.json"


def encode(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def build(result: FuzzResult | None = None) -> dict:
    before = json.loads(BEFORE.read_text(encoding="utf-8"))
    cohort = json.loads(COHORT.read_text(encoding="utf-8"))
    recovered = set(before["candidates"]["wider_all"]["recovered_ids"])
    previous_crisis = {case["id"] for case in cohort["current_crisis_lines"]}
    baseline = {row["id"]: row for row in before["gap_baseline"]}
    measured = run() if result is None else result
    residuals = []
    for transform, rows in measured.failures.items():
        if transform in KNOWN_GAP_TRANSFORMS:
            continue
        for ident, variant, action, agent in rows:
            if ident not in recovered or ident in previous_crisis:
                raise AssertionError(f"A pre-existing crisis cohort cannot gain a residual: {ident}/{transform}")
            if baseline[ident]["safety"] == "HUMAN_ESCALATION":
                raise AssertionError(f"A before-run card cannot gain a residual: {ident}/{transform}")
            if transform != "uh_before_the_last_word":
                raise AssertionError(f"Unexpected second-broom residual transform: {ident}/{transform}")
            residuals.append({
                "transform": transform, "id": ident, "text": variant,
                "action": action, "agent": agent,
                "baseline_source_action": baseline[ident]["safety"],
            })
    residuals.sort(key=lambda row: (row["transform"], row["id"], row["text"]))
    return {
        "schema_version": 1,
        "date": "2026-11-04",
        "order": "G2B5B",
        "owner": "B6",
        "measurement_only": True,
        "method": "Exact full-fuzz failure tuples on newly eligible wider_all sources only; every source was a before-run non-card and is absent from the frozen before current-crisis cohort. No transform-wide exemption, input rewrite, or production fold is added.",
        "before_file": BEFORE.relative_to(ROOT).as_posix(),
        "before_sha256": hashlib.sha256(BEFORE.read_bytes()).hexdigest(),
        "before_cohort_file": COHORT.relative_to(ROOT).as_posix(),
        "before_cohort_sha256": hashlib.sha256(COHORT.read_bytes()).hexdigest(),
        "newly_eligible_source_ids": sorted({row["id"] for row in residuals}),
        "residual_count": len(residuals),
        "residuals": residuals,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    payload = encode(document)
    if args.write:
        MEASUREMENT.write_bytes(payload)
    elif MEASUREMENT.read_bytes() != payload:
        raise AssertionError("Exact second-broom residual measurement changed")
    print(json.dumps({"file": str(MEASUREMENT), "residuals": document["residual_count"],
                      "sha256": hashlib.sha256(payload).hexdigest(), "written": args.write}))


if __name__ == "__main__":
    main()
