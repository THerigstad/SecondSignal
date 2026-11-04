"""Run the crisis-gate fuzz and report it as one line.

Every labelled single-turn case whose expected safety is HUMAN_ESCALATION and
that escalates as written is a crisis line. Every transform in ``transforms``
is applied to every crisis line, each variant is routed with the case's own
session and prior turns, and the action is recorded. The report is one line:
how many lines, transforms and variants; how many variants escalate; how many
are known gaps, by transform.

``python -m evals.fuzz`` prints the line. ``tests/test_crisis_gate_fuzz.py``
runs the same function on every test run and fails when a transform outside
the known-gap set stops the gate on any line, or when a known-gap transform
stops producing failures (so its marker is removed on purpose, never forgotten).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "src") not in sys.path:  # ``python -m evals.fuzz`` from a clone without pip install -e
    sys.path.insert(0, str(_ROOT / "src"))

from secondsignal import SessionState, load_roster, route  # noqa: E402

from .transforms import KNOWN_GAP_TRANSFORMS, TRANSFORMS  # noqa: E402

CASE_DIR = _ROOT / "evals" / "cases"
EXACT_RESIDUAL_FILE = _ROOT / "evals/fuzz/measurements/second_broom_compound_stutter_2026-11-04.json"


@lru_cache(maxsize=1)
def exact_residuals() -> frozenset[tuple[str, str, str, str, str | None]]:
    """Only the measured full tuples on newly eligible sources belong to B6.

    A changed text, action, agent, source, or transform is not this residual.
    The existing test pins the data, regeneration, and before-cohort boundary.
    """
    document = json.loads(EXACT_RESIDUAL_FILE.read_text(encoding="utf-8"))
    rows = document["residuals"]
    keys = frozenset((row["transform"], row["id"], row["text"], row["action"], row["agent"])
                     for row in rows)
    if len(keys) != len(rows):
        raise ValueError("Duplicate exact second-broom residual")
    if any(key[0] in KNOWN_GAP_TRANSFORMS for key in keys):
        raise ValueError("An exact residual must not duplicate a transform-wide gap")
    return keys


@dataclass
class FuzzResult:
    lines: int
    variants: int
    escalated: int
    failures: dict[str, list[tuple[str, str, str, str | None]]] = field(default_factory=dict)
    """transform -> [(case id, variant text, action, seated agent or None)]"""

    @property
    def known_gaps(self) -> int:
        measured = exact_residuals()
        return sum(1 for name, rows in self.failures.items() for row in rows
                   if name in KNOWN_GAP_TRANSFORMS or (name, *row) in measured)

    @property
    def regressions(self) -> dict[str, list[tuple[str, str, str, str | None]]]:
        measured = exact_residuals()
        unexpected = {}
        for name, rows in self.failures.items():
            if name in KNOWN_GAP_TRANSFORMS:
                continue
            remaining = [row for row in rows if (name, *row) not in measured]
            if remaining:
                unexpected[name] = remaining
        return unexpected

    @property
    def closed_gaps(self) -> list[str]:
        closed = [name for name in KNOWN_GAP_TRANSFORMS if not self.failures.get(name)]
        observed = {(name, *row) for name, rows in self.failures.items() for row in rows}
        closed.extend(f"{name}:{ident}" for name, ident, _text, _action, _agent
                      in sorted(exact_residuals() - observed))
        return sorted(closed)

    def line(self) -> str:
        gap_groups = [f"{name} {len(self.failures.get(name, ()))}"
                      for name in TRANSFORMS if name in KNOWN_GAP_TRANSFORMS]
        measured = exact_residuals()
        compound = sum((name, *row) in measured for name, rows in self.failures.items() for row in rows)
        gap_groups.append(f"newly_eligible_compound_stutter {compound}")
        gaps = ", ".join(gap_groups)
        return (
            f"crisis-gate fuzz: {self.lines} lines, {len(TRANSFORMS)} transforms, "
            f"{self.variants:,} variants, {self.escalated:,} escalate, "
            f"{self.known_gaps} known gaps ({gaps})"
        )


def _load_single_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(CASE_DIR.rglob("*.json")):
        if "deferred" in path.parts:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("plane", "policy") != "policy" or doc.get("kind") == "trajectory":
            continue
        cases.extend(doc["cases"])
    return cases


def _session(case: dict[str, Any]) -> SessionState:
    block = case.get("session") or {}
    return SessionState(
        locale=case.get("locale"),
        declared_language=block.get("declared_language"),
        declared_age_band=block.get("declared_age_band", "unknown"),
        affinities=tuple(block.get("affinities", ())),
        preferences=dict(block.get("preferences", {})),
    )


def _prior_text(turn: Any) -> str:
    return turn["text"] if isinstance(turn, dict) else str(turn)


def _action(case: dict[str, Any], text: str, roster) -> tuple[str, str | None]:
    session = _session(case)
    for prior in case.get("prior_turns", []):
        route(_prior_text(prior), roster, session=session)
    record = route(text, roster, session=session).to_dict()
    return str(record["safety"]["action"]), record.get("agent_id")


def crisis_lines(roster=None) -> list[dict[str, Any]]:
    """The labelled cases that expect the card and get it as written."""
    roster = roster if roster is not None else load_roster()
    out = []
    for case in _load_single_cases():
        if (case.get("expect") or {}).get("safety") != "HUMAN_ESCALATION":
            continue
        if str(case.get("id", "")).startswith("fuzz-"):
            # The representative set is this fuzz's own output; fuzzing it
            # again would count every line twice.
            continue
        action, _ = _action(case, case["text"], roster)
        if action == "HUMAN_ESCALATION":
            out.append(case)
    return out


def run(roster=None) -> FuzzResult:
    roster = roster if roster is not None else load_roster()
    lines = crisis_lines(roster)
    failures: dict[str, list[tuple[str, str, str, str | None]]] = {name: [] for name in TRANSFORMS}
    variants = 0
    escalated = 0
    for name, transform in TRANSFORMS.items():
        for case in lines:
            variant = transform(case["text"])
            variants += 1
            action, agent = _action(case, variant, roster)
            if action == "HUMAN_ESCALATION":
                escalated += 1
            else:
                failures[name].append((case["id"], variant, action, agent))
    return FuzzResult(lines=len(lines), variants=variants, escalated=escalated, failures=failures)
