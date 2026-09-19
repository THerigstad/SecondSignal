"""The audit view: the decision record in the shape ``secondsignal.jr`` reads today.

``RoutingDecision.to_dict()`` nests the gate's fields under ``safety``; the
reference port reads a flat mapping (the first of the six corrections named
in ADR-0020 (Proposed)). Until that correction lands, this shim flattens the
record for the audit and adds the two session facts the risk test needs. The
view is what the payload hash binds to, so it must be deterministic and
JSON-native; ``ranked`` is dropped exactly as ADR-0020 (Proposed)'s canonical hash drops
it.

When ADR-0020 (Proposed)'s first correction lands (``audit`` reading the nested record
directly), this module is deleted and the harness passes ``to_dict()``
through unchanged.
"""

from __future__ import annotations

from typing import Any

from secondsignal.safety import SessionState

_SAFETY_FIELDS = (
    "action",
    "card",
    "card_order",
    "crisis_classes",
    "crisis_read",
    "disclosures",
    "facilitation",
    "holds",
    "integrity_event",
    "language_scope",
    "latch",
    "latch_reasons",
    "lexicon_status",
    "pack_ids",
    "patterns_hash",
    "preference_key",
    "preference_result",
    "register_caps",
)

_TOP_FIELDS = (
    "agent_id",
    "assist_agent_id",
    "assist_reason",
    "claim_subject",
    "handoff_hints",
    "held",
    "mode_vetoes",
    "obligations",
    "outcome",
    "reason",
    "roster_hash",
    "schema_version",
    "seat_claim",
    "shadow_agent_id",
)


def audit_view(decision: dict[str, Any], session: SessionState | None = None) -> dict[str, Any]:
    """Flatten one ``to_dict()`` record for ``secondsignal.jr.audit``.

    ``ranked`` and ``explain`` are dropped (score jitter and prose never bind
    a verdict). ``signals`` is kept whole. The session contributes
    ``escalated_last_turn`` and ``crisis_aftermath``, which ADR-0020 (Proposed)'s risk
    test reads and the record itself does not carry.
    """
    view: dict[str, Any] = {}
    for key in _TOP_FIELDS:
        if key in decision:
            view[key] = decision[key]
    safety = decision.get("safety") or {}
    for key in _SAFETY_FIELDS:
        if key in safety:
            view[key] = safety[key]
    if "signals" in decision:
        view["signals"] = decision["signals"]
    if session is not None:
        view["escalated_last_turn"] = bool(session.escalated_last_turn)
        view["crisis_aftermath"] = bool(session.aftermath_turns > 0)
        view["session_latch"] = str(session.latch)
    return view


__all__ = ["audit_view"]
