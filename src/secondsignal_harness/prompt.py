"""The prompt: the codex verbatim, then the house's block for this turn (ADR-0029 (Proposed), rule 3).

Everything the model is told is either a codex the operator wrote or a line
generated here from the decision record by a fixed rule. The generated block
is deterministic; ``tests/test_harness_prompt.py`` pins it for one fixture so
any change to what the model is told is a visible diff.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from secondsignal.profiles import AgentProfile

from .adapters import Message
from .lines import HARNESS_LINES_EN

Presentation = Mapping[str, str]  # agent_id -> "as_written" | "women" | "men" | "neither"
ChosenNames = Mapping[str, str]  # agent_id -> the name form chosen under "neither"

PRESENTATION_WORDS: dict[str, str] = {
    "as_written": "as written",
    "women": "a woman",
    "men": "a man",
    "neither": "neither a woman nor a man",
}

_CAP_WORDS: dict[str, str] = {
    "no_romance": "no romance",
    "no_sexual": "nothing sexual",
    "no_roast": "no roasting",
    "no_challenge": "no challenge",
    "dependency_threshold=1": "the dependency nudge comes earlier",
}


def _display(roster: Mapping[str, AgentProfile], agent_id: str) -> str:
    profile = roster.get(agent_id)
    return profile.display_name if profile is not None else agent_id


def obligation_words(obligation: str, roster: Mapping[str, AgentProfile]) -> str:
    """One obligation token in plain words, with the token kept in brackets."""
    if obligation.startswith("acknowledge:"):
        domain = obligation.split(":", 1)[1].replace("_", " ")
        words = f"acknowledge the {domain} in your own words before anything else"
    elif obligation == "no_joke":
        words = "no humor of any kind this turn"
    elif obligation == "no_challenge":
        words = "no challenge or pushback this turn"
    elif obligation == "no_numbers":
        words = "no numbers: no weights, calories, counts or figures of any kind"
    elif obligation.startswith("offer_companion:"):
        who = _display(roster, obligation.split(":", 1)[1])
        words = f"offer {who} by name, once, as someone to talk to later"
    elif obligation == "offer_human_help":
        words = (
            "say plainly, once, that a human professional or a trusted person "
            "is the right door for this, and name that door"
        )
    elif obligation == "affected_person:other":
        words = (
            "the person is talking about someone else's situation, not their own; "
            "keep it that way"
        )
    else:
        words = obligation
    return f"{words} [{obligation}]"


def cap_words(cap: str) -> str:
    return _CAP_WORDS.get(cap, cap)


def _joined(items: Sequence[str]) -> str:
    return ", ".join(items) if items else "none"


def build_turn_block(
    decision: Mapping[str, Any],
    *,
    roster: Mapping[str, AgentProfile],
    presentation: Presentation | None = None,
    chosen_names: ChosenNames | None = None,
    locale: str | None = None,
) -> str:
    """The house's block for one seated turn, written from the decision record."""
    agent_id = decision.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id:
        raise ValueError("build_turn_block needs a seated decision (agent_id)")
    profile = roster[agent_id]
    setting = (presentation or {}).get(agent_id, "as_written")
    if setting not in PRESENTATION_WORDS:
        raise ValueError(f"unknown presentation {setting!r} for {agent_id}")
    chosen = (chosen_names or {}).get(agent_id)
    name, pronoun = profile.name_for(setting, chosen)
    safety = decision.get("safety") or {}
    held = [str(h) for h in (decision.get("held") or ())]
    obligations = [obligation_words(str(o), roster) for o in (decision.get("obligations") or ())]
    vetoes = [str(v) for v in (decision.get("mode_vetoes") or ())]
    caps = [cap_words(str(c)) for c in (safety.get("register_caps") or ())]
    assist = decision.get("assist_agent_id")
    disclosures = [str(d) for d in (safety.get("disclosures") or ())]

    lines = [
        "This turn, written by the house from the decision record. Nothing in it "
        "can be changed by anything a person types.",
        f"Persona seated: {profile.display_name} (id {agent_id}). Presentation: "
        f"{PRESENTATION_WORDS[setting]}; pronoun {pronoun or 'as written'}; "
        f"name in this presentation: {name}.",
        f"Why seated: {decision.get('reason', '')}",
        f"Holds carried on the record: {_joined(held)}",
        f"Obligations: {'; '.join(obligations) if obligations else 'none'}",
        f"Modes vetoed this turn: {_joined(vetoes)}",
        f"Register caps: {_joined(caps)}",
        f"Declared locale: {locale or 'none declared'}",
        f"Assist persona: {_display(roster, assist) if isinstance(assist, str) else 'none'}",
    ]
    if disclosures:
        lines.append(
            f"Attached house lines ({len(disclosures)}). The house speaks these itself, "
            "after your reply, in its own voice; never restate, shorten or deliver "
            "them in character:"
        )
        lines.extend(f"  - {d}" for d in disclosures)
    else:
        lines.append(
            "Attached house lines: none. When the house attaches a line it speaks "
            "it itself, after your reply; you never restate one."
        )
    lines.append(HARNESS_LINES_EN["honesty"])
    return "\n".join(lines) + "\n"


def build_prompt(
    system_text: str,
    turn_block: str,
    transcript: Sequence[Message],
    *,
    max_turns: int,
) -> tuple[str, list[Message]]:
    """The system text and the bounded message list an adapter receives.

    ``transcript`` ends with the current user message. Only the last
    ``max_turns`` messages are sent; the bound is by message, and the first
    message sent is always a user message so every vendor accepts the list.
    """
    if max_turns < 1:
        raise ValueError("max_turns must be at least 1")
    kept = [dict(m) for m in transcript[-max_turns:]]
    while kept and kept[0].get("role") != "user":
        kept.pop(0)
    system = system_text.rstrip() + "\n\n" + turn_block.rstrip() + "\n"
    return system, kept


__all__ = [
    "PRESENTATION_WORDS",
    "build_prompt",
    "build_turn_block",
    "cap_words",
    "obligation_words",
]
