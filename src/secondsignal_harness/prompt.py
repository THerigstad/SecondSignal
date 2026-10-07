"""The prompt: the codex verbatim, then the house's block for this turn (ADR-0029 (Proposed), rule 3).

Everything the model is told is either a codex the operator wrote or a line
generated here from the decision record by a fixed rule. The generated block
is deterministic; ``tests/test_harness_prompt.py`` pins it for one fixture so
any change to what the model is told is a visible diff.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from secondsignal.preferences import effective_preferences
from secondsignal.profiles import AgentProfile

from .adapters import Message
from .lines import HARNESS_LINES_EN, ROOM_LINES

Presentation = Mapping[str, str]  # agent_id -> "as_written" | "women" | "men" | "neither"
ChosenNames = Mapping[str, str]  # agent_id -> the name form chosen under "neither"
DRAFT_TAGS = ("plan", "letter", "verse", "list", "unsent")


# These finite settings belong to the voice; the policy's ask-once flow is unchanged.
STYLE_VALUES: dict[str, tuple[str, ...]] = {
    "pace": ("one_step", "steady"),
    "verbosity": ("short", "standard", "detailed"),
    "directness": ("plain", "gentle", "direct", "blunt"),
    "delivery_order": ("summary_first", "details_first"),
    "format": ("prose", "bullets", "numbered"),
    "humor_tolerance": ("none", "light", "gallows"),
}
LANGUAGE_STYLES: dict[str, str] = {
    "match": "answer in the language the person just used",
    "spanish_to_english": "give the English for what the person wrote in Spanish",
    "technical_english": "answer in the language the person just used, keeping technical words in English",
}
_CAPPED_STYLE = {
    "pace": "one_step", "verbosity": "short", "directness": "plain",
    "delivery_order": "summary_first", "format": "prose", "humor_tolerance": "none",
}
_STYLE_LABELS = {
    "pace": "pace", "verbosity": "length", "directness": "wording",
    "delivery_order": "delivery order", "format": "format", "humor_tolerance": "humour",
}
_STYLE_WORDS = {
    "one_step": "one step at a time", "steady": "steady pace", "short": "short replies",
    "standard": "usual length", "detailed": "more detail", "plain": "plain wording first",
    "gentle": "gentle", "direct": "direct", "blunt": "blunt",
    "summary_first": "summary first", "details_first": "details first",
    "prose": "prose", "bullets": "bullet points", "numbered": "numbered steps",
    "none": "none", "light": "light", "gallows": "gallows, only within the seated voice's protocols",
}


def applied_preferences(
    decision: Mapping[str, Any], declared: Mapping[str, str] | None,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Read confirmed style through the policy mask, then constrain its shape.

    A register cap binds every presentation key. This voice-only shape never
    writes policy preferences, lifts an obligation, or changes its decision.
    Unknown values cannot become prompt text.
    """
    selected = {
        key: value for key, value in (declared or {}).items()
        if key in STYLE_VALUES and value in STYLE_VALUES[key]
    }
    safety = decision.get("safety") or {}
    caps = tuple(str(cap) for cap in (safety.get("register_caps") or ()))
    effective: dict[str, str] = effective_preferences(selected, caps)
    adjustments: list[str] = []
    if caps:
        effective = {key: _CAPPED_STYLE[key] for key in effective}
        if any(effective[key] != selected[key] for key in effective if key != "humor_tolerance"):
            adjustments.append("Presentation was simplified because the active register caps bind this turn.")
        if "humor_tolerance" in selected and selected["humor_tolerance"] != "none":
            adjustments.append("Humour was lowered to none because the active register caps bind this turn.")
    if "no_joke" in (decision.get("obligations") or ()) and "humor_tolerance" in effective:
        if effective["humor_tolerance"] != "none":
            adjustments.append("Humour was lowered to none because this turn carries the no-humour obligation.")
        effective["humor_tolerance"] = "none"
    return effective, tuple(adjustments)

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
    elif obligation == "ask_question":
        # Ruling 5 of 3 October 2026: the stabilizer seats on the third vague
        # message in a row with a question attached, not a plan.
        words = (
            "you were seated after three vague messages in a row: ask one plain "
            "question about what is going on, and offer no plan yet"
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
    declared_preferences: Mapping[str, str] | None = None,
    humour_grief: bool = False,
    language_style: str | None = None,
    room: str | None = None,
    object_text: str = "",
    draft_tag: str = "",
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
    # These are declared presentation inputs, used only after routing. The
    # Table screens the object separately before accepting it, never by
    # appending it to the message the policy decides on.
    if room:
        if room not in ROOM_LINES:
            raise ValueError("unknown room")
        lines.append(ROOM_LINES[room])
    if object_text:
        if not isinstance(object_text, str) or len(object_text) > 60 or any(
            ord(char) < 32 or char in "\u007f\u0085\u2028\u2029" for char in object_text
        ):
            raise ValueError("object must be one line of at most 60 characters")
        lines.append(HARNESS_LINES_EN["object_line"].format(object=object_text))
    if draft_tag:
        if draft_tag not in DRAFT_TAGS:
            raise ValueError("unknown draft tag")
        lines.append(HARNESS_LINES_EN["draft_tag_line"].format(tag=draft_tag))
    applied, _ = applied_preferences(decision, declared_preferences)
    if applied:
        lines.append("Declared preferences: " + "; ".join(
            f"{_STYLE_LABELS[key]}: {_STYLE_WORDS[applied[key]]}" for key in STYLE_VALUES if key in applied
        ) + ". All hold obligations, register caps and house lines still bind.")
    if applied.get("pace") == "one_step":
        lines.append(
            'Effort contract: give one next action in the first paragraph; put any remaining detail '
            'in later paragraphs for "Show the rest". House lines, hold obligations and the crisis '
            'card stay outside this budget and must never be delayed, folded or omitted. '
            'If an obligation permits no plan, ask its required question instead of giving an action.'
        )
    if humour_grief:
        lines.append(
            "Humour helps me grieve: on a grief turn, humour may come only through the seated "
            "specialist's own voice, inside that specialist's protocols. This never seats the humorist; "
            "a no-humour obligation or register cap still forbids humour."
        )
    if language_style is not None:
        if language_style not in LANGUAGE_STYLES:
            raise ValueError("unknown language style")
        lines.append(f"Language style: {LANGUAGE_STYLES[language_style]}; never translate or restate house lines.")
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
    "DRAFT_TAGS",
    "LANGUAGE_STYLES",
    "STYLE_VALUES",
    "applied_preferences",
    "PRESENTATION_WORDS",
    "build_prompt",
    "build_turn_block",
    "cap_words",
    "obligation_words",
]
