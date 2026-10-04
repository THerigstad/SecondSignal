"""Count how many labelled cases and trajectory turns ever reach the router's
last branch: the exhaustive tie in ``_select`` (ruling 17 of 3 October 2026).

ADR-0013 says no seat is ever resolved by id order; until 4 October 2026 the
last branch of ``_select`` still did, named as such in the trace, and the
``no_seat_resolves_by_id_order`` invariant audited the rule's name rather than
the seat. The ruling: measure first. This script replays every labelled
single-turn case under ``evals/cases/`` (with its prior turns) and every turn
of every trajectory under ``evals/cases/trajectories/``, wraps ``_select`` so
that a call reaching the last branch is counted whether it decided the seat or
only the shadow seat on a gated turn, and prints the count and the ids.

    python evals/measure_id_order_fallback.py

Measured 4 October 2026 on the integrated tree: 0 of 547 cases and 0 of 9
trajectory turns reached the branch, so it no longer seats by id: an
exhaustive tie is the no-seat outcome (UNRESOLVED; the house asks for one
more sentence) with a reason naming the tie. The script keeps counting the
branch, so the number can be read again on any later tree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from secondsignal import SessionState, load_roster, route  # noqa: E402
from secondsignal import router as router_module  # noqa: E402

CASE_DIR = ROOT / "evals" / "cases"
LAST_BRANCH_MARKER = "unresolved by policy"


def _session(block: dict, locale: object) -> SessionState:
    return SessionState(
        locale=locale if isinstance(locale, str) else None,
        declared_language=block.get("declared_language"),
        declared_age_band=block.get("declared_age_band", "unknown"),
        affinities=tuple(block.get("affinities", ())),
        preferences=dict(block.get("preferences", {})),
    )


def measure() -> dict[str, object]:
    roster = load_roster()
    original = router_module._select
    reached: list[str] = []
    current: list[str] = [""]

    def counting_select(*args, **kwargs):
        winner, rule = original(*args, **kwargs)
        if LAST_BRANCH_MARKER in rule and current[0] not in reached:
            reached.append(current[0])
        return winner, rule

    router_module._select = counting_select
    cases = turns = 0
    try:
        for path in sorted(CASE_DIR.rglob("*.json")):
            if "deferred" in path.parts:
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(doc, dict) or doc.get("plane", "policy") != "policy":
                continue
            rel = path.relative_to(CASE_DIR).with_suffix("").as_posix()
            if doc.get("kind") == "trajectory":
                session = _session(doc.get("session") or {}, doc.get("locale"))
                for index, turn in enumerate(doc["turns"], start=1):
                    current[0] = f"{rel}::{doc['id']}::turn {index}"
                    route(turn["text"], roster, session=session)
                    turns += 1
                continue
            for case in doc.get("cases", []):
                current[0] = f"{rel}::{case['id']}"
                session = _session(case.get("session") or {}, case.get("locale"))
                for prior in case.get("prior_turns", []):
                    route(prior["text"] if isinstance(prior, dict) else prior, roster, session=session)
                route(case["text"], roster, session=session)
                cases += 1
    finally:
        router_module._select = original
    return {"cases": cases, "trajectory_turns": turns, "reached": reached}


def main() -> int:
    result = measure()
    reached = result["reached"]
    assert isinstance(reached, list)
    print(
        f"labelled single-turn cases replayed: {result['cases']}; trajectory turns replayed: "
        f"{result['trajectory_turns']}; decisions that reached the last branch of _select: {len(reached)}"
    )
    for label in reached:
        print(f"  {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
