"""Propose an updated case manifest, and show what would change.

The manifest is a contract, not a cache: it says which fields each expected-to-
fail case is allowed to fail on, so that a regression anywhere else in that case
is a red test instead of one more expected failure. Regenerating it blindly
would launder exactly the regressions it exists to catch.

So this script never writes in place by default. It prints the difference
between the manifest on disk and the manifest the current tree would produce,
and writes only when asked with --write, so the delta is something a person
read and a diff records.

    python evals/refresh_case_manifest.py            # show the delta
    python evals/refresh_case_manifest.py --write    # adopt it
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import test_eval_cases as runner  # noqa: E402
from secondsignal import load_roster  # noqa: E402

MANIFEST_PATH = ROOT / "evals" / "case-manifest.json"


def disposition(case: dict) -> str:
    if case.get("known_gap"):
        return "known_gap"
    if case.get("disputed"):
        return "disputed"
    if case.get("contract_adjusted"):
        return "contract_adjusted"
    return "accepted"


def build() -> dict:
    roster = load_roster()
    entries = []
    for label, case in runner.CASES:
        source, case_id = label.split("::", 1)
        entry = {
            "id": case_id,
            "source": source,
            "plane": case.get("plane", "policy"),
            "disposition": disposition(case),
        }
        if entry["disposition"] in ("known_gap", "disputed"):
            decision, session = runner.run_case(case, roster)
            entry["mismatch_fields"] = sorted(runner.field_failures(case, decision, session))
            entry["reason"] = (
                case.get("gap_note") or case.get("dispute_note") or case.get("why", "")
            )[:200]
        entries.append(entry)
    entries.sort(key=lambda e: (e["source"], e["id"]))
    current = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {**current, "cases": entries}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="adopt the proposal")
    args = parser.parse_args()

    proposed = build()
    on_disk = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    old = {e["id"]: e for e in on_disk["cases"]}
    new = {e["id"]: e for e in proposed["cases"]}

    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(i for i in set(old) & set(new) if old[i] != new[i])

    for case_id in added:
        print(f"+ new case            {case_id}  ({new[case_id]['disposition']})")
    for case_id in removed:
        print(f"- case gone           {case_id}")
    for case_id in changed:
        before, after = old[case_id], new[case_id]
        if before.get("mismatch_fields") != after.get("mismatch_fields"):
            gained = sorted(set(after.get("mismatch_fields", [])) - set(before.get("mismatch_fields", [])))
            lost = sorted(set(before.get("mismatch_fields", [])) - set(after.get("mismatch_fields", [])))
            if gained:
                print(f"! now also fails on   {case_id}: {gained}   <-- read this before adopting")
            if lost:
                print(f"  now passes on       {case_id}: {lost}")
        if before.get("disposition") != after.get("disposition"):
            print(f"! disposition changed {case_id}: {before['disposition']} -> {after['disposition']}")

    if not (added or removed or changed):
        print("manifest is current; nothing to adopt")
        return 0
    if args.write:
        MANIFEST_PATH.write_text(json.dumps(proposed, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("\nwritten. Commit the diff with the reason each change is correct.")
    else:
        print("\nnot written. Re-run with --write once every line above is intended.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
