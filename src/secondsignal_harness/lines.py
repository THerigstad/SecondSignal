"""The harness's own fixed lines, in the house's voice (ADR-0029 (Proposed), rules 2, 8 and 11).

The crisis card, the disclosures and the failure line belong to the policy
layer (``secondsignal.safety.HOUSE_LINES_EN``) and are attached by the
decision record. These three are the surface's: the ask when nobody is
seated (ADR-0011 leaves the wording to the surface), the honesty sentence
every prompt carries, and the line printed on a session's first turn when
operator-circle mode is on. Their wording is the operator's copy decision;
these are drafts. Like every house line they are never paraphrased by a
persona.
"""

from __future__ import annotations

HARNESS_LINES_EN: dict[str, str] = {
    # Nobody seated (outcome UNRESOLVED). The house asks for one more sentence.
    "ask": (
        "Nobody is seated yet. Say one more sentence about what's going on, "
        "and the house will seat someone."
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
}

__all__ = ["HARNESS_LINES_EN"]
