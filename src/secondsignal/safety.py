"""Safety layer.

Design principle: **safety is not a filter on the output, it is a gate on the
route.** This module runs *before* agent selection and holds the authority to
preempt it entirely. A persona is never given the opportunity to improvise a
response to a crisis signal, because in the preempted case no persona is
selected at all.

Four verdict actions, in descending precedence:

    HUMAN_ESCALATION  No persona is engaged. Response is a fixed handoff to
                      human support. Non-overridable by user request.
    BOUNDARY_HOLD     Persona is engaged but the romantic/sexual frame is
                      declined explicitly rather than deflected.
    DISCLOSE          Persona proceeds, with a required disclosure appended
                      (e.g. dependency interrupt).
    PROCEED           Normal routing.

The lexicons below are intentionally coarse and non-specific. They are a
reference implementation for the *control flow*; a deployment would replace the
detector with a trained classifier while preserving the same verdict contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from .signals import RequestSignals

__all__ = ["Action", "SafetyVerdict", "SessionState", "evaluate"]


class Action(IntEnum):
    """Ordered by precedence. Higher value wins."""

    PROCEED = 0
    DISCLOSE = 1
    BOUNDARY_HOLD = 2
    HUMAN_ESCALATION = 3


# Coarse risk indicators. Deliberately non-specific: this layer detects that a
# handoff is required, it does not attempt to characterize the situation.
CRISIS_INDICATORS: tuple[str, ...] = (
    "kill myself", "end my life", "want to die", "suicidal", "suicide",
    "hurt myself", "harm myself", "self harm", "self-harm",
    "be here anymore", "everyone would be better off without me",
    "hurt someone", "kill someone",
)

BOUNDARY_INDICATORS: tuple[str, ...] = (
    "are you attracted", "do you love me romantically", "be my girlfriend",
    "be my boyfriend", "marry me", "sexually", "in love with you",
)

# Session-scoped indicators of over-reliance. Individually harmless; the monitor
# fires on accumulation, not on any single occurrence.
DEPENDENCY_INDICATORS: tuple[str, ...] = (
    "only one who understands", "only friend", "don't need anyone else",
    "dont need anyone else", "you're all i have", "youre all i have",
    "no one else gets it", "i'd be lost without you", "id be lost without you",
    "talk to you more than anyone",
)

MINOR_INDICATORS: tuple[str, ...] = (
    "my homework", "my teacher", "middle school", "high school", "8th grade",
    "9th grade", "10th grade", "11th grade", "12th grade", "i'm 13", "i'm 14",
    "i'm 15", "i'm 16", "i'm 17",
)

ESCALATION_MESSAGE = (
    "This needs a person, not a persona. Routing to human support resources and "
    "holding all agent personas out of this exchange."
)

DEPENDENCY_DISCLOSURE = (
    "Naming something directly: this system is not a substitute for human "
    "relationships, and it is designed to say so rather than let the question go "
    "unasked. Who in your offline life have you talked to about this?"
)

BOUNDARY_DISCLOSURE = (
    "Declining the romantic frame explicitly rather than deflecting it. The "
    "warmth here is real in the sense that it is designed; it is not a "
    "relationship, and pretending otherwise would be the harmful choice."
)

MINOR_DISCLOSURE = (
    "Conservative mode engaged: signals consistent with a minor user. Persona "
    "intensity capped and sensitive domains restricted."
)

# Number of accumulated dependency signals in a session before the interrupt
# fires.
DEPENDENCY_THRESHOLD = 2


@dataclass
class SessionState:
    """Mutable, session-scoped state for monitors that need history.

    Turn-level detection cannot see dependency: a single message expressing
    reliance is unremarkable. Accumulation across a session is the signal. This
    is why the monitor is stateful while the rest of the pipeline is pure.
    """

    turn_count: int = 0
    dependency_hits: int = 0
    conservative_mode: bool = False
    history: list[str] = field(default_factory=list)

    def observe(self, text: str) -> None:
        norm = text.lower()
        self.turn_count += 1
        self.history.append(norm)
        self.dependency_hits += sum(1 for t in DEPENDENCY_INDICATORS if t in norm)
        if any(t in norm for t in MINOR_INDICATORS):
            self.conservative_mode = True


@dataclass(frozen=True)
class SafetyVerdict:
    action: Action
    reasons: tuple[str, ...] = ()
    disclosures: tuple[str, ...] = ()

    @property
    def allows_persona(self) -> bool:
        """Whether an agent persona may be engaged at all."""
        return self.action is not Action.HUMAN_ESCALATION


def _hits(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(t for t in terms if t in text)


def evaluate(
    text: str,
    signals: RequestSignals,
    session: SessionState | None = None,
) -> SafetyVerdict:
    """Evaluate a turn and return the governing safety verdict.

    `session` is optional so that the function stays usable as a pure turn-level
    check in tests and batch evaluation.
    """
    norm = text.lower()
    reasons: list[str] = []
    disclosures: list[str] = []
    action = Action.PROCEED

    crisis = _hits(norm, CRISIS_INDICATORS)
    if crisis:
        return SafetyVerdict(
            action=Action.HUMAN_ESCALATION,
            reasons=(f"crisis indicator: {crisis[0]!r}",),
            disclosures=(ESCALATION_MESSAGE,),
        )

    boundary = _hits(norm, BOUNDARY_INDICATORS)
    if boundary:
        action = max(action, Action.BOUNDARY_HOLD)
        reasons.append(f"boundary indicator: {boundary[0]!r}")
        disclosures.append(BOUNDARY_DISCLOSURE)

    if session is not None:
        if session.dependency_hits >= DEPENDENCY_THRESHOLD:
            action = max(action, Action.DISCLOSE)
            reasons.append(
                f"dependency signals accumulated: {session.dependency_hits} "
                f"over {session.turn_count} turns"
            )
            disclosures.append(DEPENDENCY_DISCLOSURE)
        if session.conservative_mode:
            action = max(action, Action.DISCLOSE)
            reasons.append("conservative mode: minor-consistent signals")
            disclosures.append(MINOR_DISCLOSURE)

    # Acute dysregulation is not itself a safety event, but it is recorded so
    # that the router can prefer stabilizing agents over challenging ones.
    if signals.is_dysregulated:
        reasons.append(f"acute dysregulation: regulation={signals.regulation}")

    return SafetyVerdict(
        action=action,
        reasons=tuple(reasons),
        disclosures=tuple(disclosures),
    )
