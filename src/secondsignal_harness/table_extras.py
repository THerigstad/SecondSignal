"""Order T2: read-only Table manners from an already-made decision.

The supplied policy record has no asked-character field. Consequently live
records produce no acknowledgement: no message parser fills that gap here.
The explicit ``asked_agent_id`` contract is accepted only if a future policy
record supplies it. The Table can separately remember a control declaration,
without adding anything to a decision or pretending the message said it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from secondsignal.profiles import AgentProfile

from .lines import ASK_REASON_CLAUSES, HARNESS_LINES_EN


def asked_agent(
    record: Mapping[str, Any], roster: Mapping[str, AgentProfile],
) -> str | None:
    """Read an explicit identity only; names mentioned in evidence are not asks."""
    asked = record.get("asked_agent_id")
    if not isinstance(asked, str):
        return None
    return asked if asked in roster else None


def eligible_agents(record: Mapping[str, Any]) -> tuple[str, ...]:
    """Other eligible chairs in the record's ranking order, never a fresh score."""
    safety = record.get("safety") or {}
    if safety.get("action") == "HUMAN_ESCALATION" or record.get("outcome") == "PREEMPTED":
        return ()
    return tuple(
        entry["agent_id"] for entry in record.get("ranked", ())
        if isinstance(entry, Mapping) and isinstance(entry.get("agent_id"), str)
        and entry["agent_id"] != record.get("agent_id")
        and entry.get("status") == "scored" and not entry.get("vetoed")
    )


def ask_acknowledgement(
    record: Mapping[str, Any],
    *,
    roster: Mapping[str, AgentProfile],
    presentation: Mapping[str, str] | None = None,
    chosen_names: Mapping[str, str] | None = None,
) -> str | None:
    """The exact house line, only when the record supplies ask, seat and reason."""
    safety = record.get("safety") or {}
    if safety.get("action") == "HUMAN_ESCALATION" or record.get("outcome") != "ROUTED":
        return None
    asked = asked_agent(record, roster)
    seated = record.get("agent_id")
    if asked is None or not isinstance(seated, str) or seated not in roster or asked == seated:
        return None
    if not isinstance(record.get("reason"), str) or not record["reason"].strip():
        return None
    candidate = next((
        entry for entry in record.get("ranked", ())
        if isinstance(entry, Mapping) and entry.get("agent_id") == asked
    ), None)
    if candidate is None or candidate.get("status") not in {
        "scored", "vetoed", "capped", "below_floor", "outranked", "no_signal",
    }:
        return None
    # A carried hold is not necessarily why the asked chair lost. Read the
    # asked candidate's own returned explanation, so an unrelated grief hold
    # cannot relabel a score on work as a grief-driven substitution.
    held = set(record.get("held") or ())
    blocked_holds: set[str] = set()
    for rationale in candidate.get("rationale") or ():
        if isinstance(rationale, str) and "cannot honor hold: " in rationale:
            tokens = rationale.split("cannot honor hold: ", 1)[1].split(")", 1)[0]
            blocked_holds.update(token.strip() for token in tokens.split(","))
    blocked_holds &= held
    if candidate.get("status") == "vetoed" and blocked_holds & {"grief", "loss"}:
        kind = "hold_grief"
    elif candidate.get("status") == "vetoed" and blocked_holds & {"addiction_recovery", "recovery"}:
        kind = "hold_recovery"
    elif candidate.get("status") == "vetoed" and blocked_holds & {"abuse", "conflict"}:
        kind = "hold_conflict"
    elif candidate.get("status") in {"vetoed", "capped"}:
        kind = "steadiness"
    elif candidate.get("status") == "scored":
        kind = "outscored"
    else:
        kind = "other"

    def name(agent_id: str) -> str:
        return roster[agent_id].name_for(
            (presentation or {}).get(agent_id, "as_written"),
            (chosen_names or {}).get(agent_id),
        )[0]

    names = {"Asked": name(asked), "Seated": name(seated)}
    reason = ASK_REASON_CLAUSES[kind].format(**names)
    return HARNESS_LINES_EN["ask_acknowledgement"].format(**names, reason=reason)


__all__ = ["ask_acknowledgement", "asked_agent", "eligible_agents"]
