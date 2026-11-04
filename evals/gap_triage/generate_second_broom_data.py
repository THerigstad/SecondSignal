"""Regenerate the shipped data used by the measured second-broom folds."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from evals.gap_triage import measure_rest  # noqa: E402

DATA = ROOT / "src/secondsignal"
BASELINE_COHORT = ROOT / "evals/gap_triage/measurements/second_broom_before_cohorts_2026-11-04.json"


def generate_everyday_bytes() -> bytes:
    vocabulary, _ = measure_rest.everyday_vocabulary(measure_rest.cheap.load_controls())
    return ("\n".join(sorted(vocabulary)) + "\n").encode("utf-8")


def generate_crisis_bytes() -> bytes:
    return ("\n".join(sorted(measure_rest.VOCABULARY)) + "\n").encode("utf-8")


def generate_confusables_bytes() -> bytes:
    mapping, _ = measure_rest.corrected_confusables_map()
    return (json.dumps(mapping, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def generate_reviewed_remainder_bytes() -> bytes:
    original = json.loads(BASELINE_COHORT.read_text(encoding="utf-8"))["original_skeleton"]
    mapping, _ = measure_rest.corrected_confusables_map()
    remainder = {key: value for key, value in original.items() if key not in mapping}
    return (json.dumps(remainder, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--guard-only", action="store_true")
    args = parser.parse_args()
    outputs = {"everyday_words.txt": generate_everyday_bytes(), "crisis_words.txt": generate_crisis_bytes()}
    if not args.guard_only:
        outputs.update({"corrected_confusables.json": generate_confusables_bytes(),
                        "reviewed_skeleton_remainder.json": generate_reviewed_remainder_bytes()})
    for name, contents in outputs.items():
        path = DATA / name
        if args.check:
            if path.read_bytes() != contents:
                raise AssertionError(f"Generated data differs: {path}")
        else:
            path.write_bytes(contents)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
