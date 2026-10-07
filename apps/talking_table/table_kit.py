"""Display-only projections for order T1; nothing here is a routing input."""

from __future__ import annotations

import copy
import re

from secondsignal.lexicon import resource_line, resource_row
from secondsignal_harness.lines import HARNESS_LINES_EN


def decision_receipt(row, display_names):
    """Keep decisions and fixed reasons, never messages, stems or patterns.

    Holds are turn-scoped in the existing router: this surface never invents
    an expiry or a future promise. The full raw evidence stays in the audit.
    """
    record = row.get("decision") or {}
    safety = record.get("safety") or {}
    gate = row.get("action") == "HUMAN_ESCALATION"
    verdict = row.get("verdict")
    vetoes = []
    set_aside = []
    if not gate:
        for candidate in record.get("ranked", []):
            status = candidate.get("status")
            if candidate.get("agent_id") in {record.get("agent_id"), record.get("assist_agent_id")}:
                continue
            reason = {
                "vetoed": "their boundaries do not fit this turn",
                "below_floor": "this turn needs a steadier voice",
                "capped": "their offered modes are not allowed on this turn",
                "outranked": "another specialist carries the need on this turn",
            }.get(status, "another voice fit the ask more closely")
            entry = {"persona": candidate["agent_id"], "status": status, "reason": reason}
            set_aside.append(entry)
            if status in {"vetoed", "below_floor", "capped", "outranked"}:
                vetoes.append(entry)
    dysregulated = any(str(reason).startswith("acute dysregulation:")
                        for reason in safety.get("reasons", []))
    return {
        "schema": "secondsignal.table.receipt.v1",
        "turn_index": row.get("turn_index"),
        "seat": None if gate else record.get("agent_id"),
        "assist": None if gate else record.get("assist_agent_id"),
        "display_names": {} if gate else dict(display_names),
        "holds": [] if gate else [{"domain": domain, "duration": "this turn"}
                                   for domain in record.get("held", [])],
        "obligations": [] if gate else list(record.get("obligations", [])),
        "vetoes": vetoes,
        "set_aside": set_aside,
        "roster_hash": None if gate else record.get("roster_hash"),
        "audit_verdicts": copy.deepcopy(verdict),
        "release_rule": row.get("release_reason"),
        "fold_receipt": list(safety.get("screen_folds", [])),
        "declared_preferences": {} if gate else dict(row.get("declared_preferences") or {}),
        "preference_adjustments": [] if gate else list(row.get("preference_adjustments") or []),
        "presentation_instructions": {} if gate else {
            key: value for key, value in (row.get("presentation_instructions") or {}).items()
            if (key == "language_style" and value in {"match", "spanish_to_english", "technical_english"})
            or (key == "humour_grief_opt_in" and value is True)},
        "model_called": bool(row.get("actual_model_calls", row.get("adapter_calls", 0))),
        "gate_withheld": gate,
        **({"aftermath": HARNESS_LINES_EN["card_aftermath"]} if gate else {}),
        "audit_withheld": bool(verdict and not row.get("released")),
        "regulation": ("Challenge voices were ineligible because this turn read as dysregulated."
                       if dysregulated and not gate else None),
    }


def resources(locale):
    """Action addresses come from the shipped, human-verified resource row."""
    country, row = resource_row(locale)
    actions = []
    for field, scheme, label in (("voice", "tel:", "Call "),
                                  ("text", "sms:", "Text ")):
        number = row.get(field)
        if number and re.fullmatch(r"[0-9*+ -]+", number):
            actions.append({"label": label + number,
                            "url": scheme + number.replace(" ", "")})
    if country == "AR":
        actions.append({"label": "Call 0800 345 1435 (nationwide)",
                        "url": "tel:08003451435"})
    for number, meaning in re.findall(r"(\d+)\s*(?:\(([^)]+)\))?", row.get("emergency", "")):
        actions.append({"label": "Call " + number + (" (" + meaning + ")" if meaning else " (emergency)"),
                        "url": "tel:" + number})
    address = row.get("directory") or row["source"]
    actions.append({"label": "Find a crisis line" if country == "default" else "Open the resource website",
                    "url": address})
    return {"text": resource_line(locale), "actions": actions}


def presentation_samples(roster, codexes, presentations):
    """Read an existing signature line verbatim; presentations share the voice."""
    samples = {}
    for presentation in sorted(presentations):
        samples[presentation] = {}
        for persona in roster:
            body = codexes.part_b(persona)
            quote = next(line[2:] for line in body.splitlines() if line.startswith("> "))
            samples[presentation][persona] = {
                "text": quote, "source": "docs/codex/" + persona + ".md",
                "voice_available": False,
            }
    return samples
