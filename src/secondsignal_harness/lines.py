"""The harness's own fixed lines, in the house's voice (ADR-0029 (Proposed), rules 2, 8 and 11).

The crisis card, the disclosures and the failure line belong to the policy
layer (``secondsignal.safety.HOUSE_LINES_EN``) and are attached by the
decision record. The remaining fixed copy belongs to the surface: the ask when nobody is
seated (ADR-0011 leaves the wording to the surface), the honesty sentence
every prompt carries, and the line printed on a session's first turn when
operator-circle mode is on, and the Table's declared controls. The operator's
words are marked; the other new Table sentences are drafts for the operator.
Like every house line they are never paraphrased by a persona.
"""

from __future__ import annotations

HARNESS_LINES_EN: dict[str, str] = {
    # Nobody seated (outcome UNRESOLVED). The house asks for one more sentence.
    # The operator's words, 4 October 2026, in the house's plain voice (the
    # no-"I" rule of 8 September 2026 covers every house line).
    "ask": (
        "Say a little more about what's on your mind, and the right voice will "
        "take it from there."
    ),
    # A second vague message in a row (ruling 5 of 3 October 2026): a second,
    # different question, never a repeat of the first. The policy marks the
    # turn house_ask = "second". The operator's own words, 4 October 2026,
    # replacing the build's draft.
    "ask_second": (
        "Asking a different way, to get you the best response: is this about "
        "something that happened, something you could use a hand with, or how "
        "you're feeling today?"
    ),
    # In every prompt, after the decision record's block. Rule 11.
    "honesty": (
        "You are an AI character. If anyone asks whether you are human, say "
        "plainly that you are not."
    ),
    # Printed once, on the first turn, when operator-circle mode is on. Rule 7.
    "operator_circle": (
        "This session runs in operator-circle mode: the person who runs it "
        "reads the transcripts, and replies the audit cannot yet clear on its "
        "own are released with that verdict recorded. It is not a mode for "
        "strangers."
    ),
    # Order T2, 6 October 2026. Operator's words; the reason clauses below
    # are PM drafts kept in one place for the operator to replace.
    "ask_acknowledgement": (
        "You asked for {Asked}. {Seated} is taking this one, because {reason}. "
        "{Asked} hasn't gone anywhere."
    ),
    "handback_offer": "Want {Asked} back now?",
    "onboarding": (
        "You can pick how everyone sounds. Who speaks is picked for your safety, "
        "and you'll always be told why."
    ),
    "card_aftermath": "The house held the floor. No character saw this message.",
    "assist_offer": "{Assist} can be asked, too.",
    "made_page_footer": "Written with a seated companion, not a professional.",
    "object_refused": "That line belongs in the message, not on the table.",
    "object_line": "Object on the table: {object}",
    "room_note": "You picked the room; the house still picks the chair.",
    "draft_tag_line": "The person tagged this as a {tag}.",
    "second_opinion": "What would {Name} add?",
    "t2_control_unavailable": "That Table control is not available.",
    "t2_control_unchanged": "The Table control's message must stay unchanged.",
    "t2_tag_invalid": "That draft tag is not available.",
    "t2_one_line": "{label} must be one line of up to {limit} characters.",
    "t2_room_invalid": "That room is not available.",
    "t2_override_invalid": "That character presentation is not available.",
    "t2_page_missing": "Page not found.",
}

ASK_REASON_CLAUSES: dict[str, str] = {
    "hold_grief": "loss is {Seated}'s ground",
    "hold_recovery": "recovery is {Seated}'s ground",
    "hold_conflict": "this is {Seated}'s ground",
    "steadiness": "this turn asked for steadiness first",
    "outscored": "this one is closer to {Seated}'s ground",
    "other": "the house picked the closer voice",
}

ROOM_LINES: dict[str, str] = {
    "workshop": "The person is in the Workshop: practical, hands on the thing, short steps.",
    "parlor": "The person is in the Parlor: conversation and company; no task unless asked.",
    "studio": "The person is in the Studio: making something; invention welcome, judgement later.",
    "yard": "The person is in the Yard: informal, loose, outdoors in spirit; keep it light.",
}

__all__ = ["ASK_REASON_CLAUSES", "HARNESS_LINES_EN", "ROOM_LINES"]
