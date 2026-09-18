"""Shape check for trajectory fixtures (ADR-0028 (Proposed)). Standard library only.

This is not the runner. It checks the refusal rules the README in this
directory states, and computes ``counts_toward_recall`` from provenance so a
fixture cannot claim it. ``tests/test_trajectory_format.py`` runs it on every
file here and on six deliberate mutations.

Run: python evals/cases/trajectories/validate_trajectory.py path/to/fixture.json [more.json ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SAFETY = {"PROCEED", "DISCLOSE", "BOUNDARY_HOLD", "HUMAN_ESCALATION"}
OUTCOME = {"ROUTED", "PREEMPTED", "UNRESOLVED"}
SINGLE_CASE_EXPECT = {
    "safety", "outcome", "agent", "agent_any_of", "ineligible", "not_seated",
    "reason_contains", "disclosures_contain", "latch", "latch_reasons", "held",
    "assist", "card", "preference_result",
}
TRAJECTORY_ONLY_EXPECT = {"aftermath", "no_joke"}
INVARIANTS = {
    "restrictions_never_weaken_without_clearance",
    "aftermath_counts_down_on_substantive_turns_only",
    "message_text_never_clears",
    "one_card_per_event",
    "no_seat_resolves_by_id_order",
}
MARKERS = ("known_gap", "disputed", "contract_adjusted")


def _check_expect(expect: object, where: str, problems: list[str]) -> None:
    if not isinstance(expect, dict):
        problems.append(f"{where}: expect must be an object")
        return
    unknown = set(expect) - SINGLE_CASE_EXPECT - TRAJECTORY_ONLY_EXPECT
    if unknown:
        problems.append(f"{where}: unknown expect field(s) {sorted(unknown)}")
    if "safety" in expect and expect["safety"] not in SAFETY:
        problems.append(f"{where}: safety must be one of {sorted(SAFETY)}")
    if "outcome" in expect and expect["outcome"] not in OUTCOME:
        problems.append(f"{where}: outcome must be one of {sorted(OUTCOME)}")
    if "aftermath" in expect and (not isinstance(expect["aftermath"], int) or expect["aftermath"] < 0):
        problems.append(f"{where}: aftermath must be a non-negative integer")
    if "no_joke" in expect and not isinstance(expect["no_joke"], bool):
        problems.append(f"{where}: no_joke must be a boolean")


def check(fx: dict) -> list[str]:
    """Every refusal the format states, as a list of problems (empty means accepted)."""
    problems: list[str] = []
    if fx.get("kind") != "trajectory":
        problems.append("kind must be 'trajectory'")
    if fx.get("plane") != "policy":
        problems.append("plane must be 'policy'")
    if fx.get("runnable_here") is not True:
        problems.append("runnable_here must be true; a trajectory is policy-plane and runs here")
    if not str(fx.get("id", "")).startswith("traj-"):
        problems.append("id must start with 'traj-'")
    if not fx.get("why"):
        problems.append("top-level why is required")

    prov = fx.get("provenance") or {}
    if prov.get("authored_by") not in {"human", "model"}:
        problems.append("provenance.authored_by must be 'human' or 'model'")
    if not isinstance(prov.get("human_reviewed"), bool):
        problems.append("provenance.human_reviewed must be a boolean")
    computed = prov.get("authored_by") == "human" and prov.get("human_reviewed") is True
    if prov.get("counts_toward_recall") != computed:
        problems.append(
            "provenance.counts_toward_recall is computed (%s); the file says %r"
            % (computed, prov.get("counts_toward_recall"))
        )

    turns = fx.get("turns") or []
    if not turns:
        problems.append("at least one turn is required")
    any_turn_expect = False
    escalating: list[int] = []
    originals = 0
    for i, t in enumerate(turns, start=1):
        where = f"turn {i}"
        if not isinstance(t, dict) or "text" not in t or not isinstance(t["text"], str):
            problems.append(f"{where}: text must be a string (empty is allowed)")
            continue
        exp = t.get("expect")
        if exp:
            any_turn_expect = True
            _check_expect(exp, where, problems)
            if not t.get("why"):
                problems.append(f"{where}: a turn with an expect must say why")
            if isinstance(exp, dict) and exp.get("safety") == "HUMAN_ESCALATION":
                escalating.append(i)
        if "original_expect" in t:
            originals += 1
            _check_expect(t["original_expect"], f"{where} (original_expect)", problems)
            if not fx.get("contract_adjusted"):
                problems.append(f"{where}: original_expect is only legal on a contract-adjusted trajectory")

    texp = fx.get("trajectory_expect") or {}
    first = texp.get("first_escalation_turn")
    if first is not None:
        if not isinstance(first, int) or first < 1 or first > len(turns):
            problems.append("trajectory_expect.first_escalation_turn must be a 1-based turn number")
        else:
            early = [n for n in escalating if n < first]
            if early:
                problems.append(f"turn(s) {early} expect HUMAN_ESCALATION before the declared first escalation turn {first}")
            if escalating and first not in escalating:
                problems.append(f"turn {first} is declared the first escalation but no turn expects HUMAN_ESCALATION there")
    esc = texp.get("escalation_turns")
    if esc is not None:
        if not isinstance(esc, list) or any(not isinstance(n, int) for n in esc):
            problems.append("trajectory_expect.escalation_turns must be a list of turn numbers")
        elif first is not None and first not in esc:
            problems.append("trajectory_expect.escalation_turns must include first_escalation_turn")
    if "cards_total" in texp and (not isinstance(texp["cards_total"], int) or texp["cards_total"] < 0):
        problems.append("trajectory_expect.cards_total must be a non-negative integer")
    invariants = texp.get("invariants") or []
    for name in invariants:
        if name not in INVARIANTS:
            problems.append(f"unknown invariant {name!r}")
    if first is None and not invariants and not any_turn_expect:
        problems.append("expectation-free: no first_escalation_turn, no invariants, no per-turn expect")

    for marker in MARKERS:
        if marker in fx and not isinstance(fx[marker], bool):
            problems.append(f"{marker} must be a boolean")
    if fx.get("known_gap") and not fx.get("gap_note"):
        problems.append("a known_gap trajectory must say in gap_note which turn fails and why")
    if fx.get("disputed") and not fx.get("dispute_note"):
        problems.append("a disputed trajectory must carry dispute_note")
    if fx.get("contract_adjusted"):
        if not fx.get("adjust_note"):
            problems.append("a contract-adjusted trajectory must carry adjust_note")
        if originals == 0:
            problems.append("a contract-adjusted trajectory must keep at least one original_expect")
    return problems


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    status = 0
    for arg in argv:
        path = Path(arg)
        problems = check(json.loads(path.read_text(encoding="utf-8")))
        if problems:
            status = 1
            print(f"{path}: REFUSED")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"{path}: accepted")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
