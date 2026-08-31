"""Routing policy.

The thesis of this repository is that in a multi-agent system, *which agent
responds* is a policy decision, and policy decisions should be explicit,
scored, logged, and testable -- not an emergent property of a prompt telling a
model to "pick whichever persona fits."

`route()` is therefore deterministic and pure. Given the same signals and the
same roster it returns the same decision, with a rationale that names every
term that contributed to the score. That property is what makes the behavior of
the system auditable after the fact, which is the difference between a system
you can operate and a system you can only demo.
"""

from __future__ import annotations

from dataclasses import dataclass

from .profiles import AgentProfile
from .safety import Action, SafetyVerdict, SessionState, evaluate
from .signals import RequestSignals, extract

__all__ = ["RoutingDecision", "ScoredAgent", "route", "score_agent"]

W_DOMAIN = 0.45
W_MODE = 0.30
W_REGULATION = 0.25

# When the caller is acutely dysregulated, agents whose value is challenge or
# humor are penalized even if they are inside their declared window. Comedy as
# a reframe tool requires a floor of regulation to land as relief rather than
# as dismissal.
DYSREGULATION_PENALTY = 0.35
PENALIZED_MODES = frozenset({"challenge", "humor"})


@dataclass(frozen=True)
class ScoredAgent:
    agent_id: str
    score: float
    rationale: tuple[str, ...]
    vetoed: bool = False


@dataclass(frozen=True)
class RoutingDecision:
    """The full, loggable record of one routing decision."""

    agent_id: str | None
    signals: RequestSignals
    safety: SafetyVerdict
    ranked: tuple[ScoredAgent, ...] = ()
    handoff_hints: tuple[tuple[str, str], ...] = ()

    @property
    def preempted(self) -> bool:
        """True when the safety layer prevented any persona from engaging."""
        return self.agent_id is None

    def explain(self) -> str:
        """Human-readable trace of why this decision was made."""
        lines: list[str] = []
        lines.append(f"regulation = {self.signals.regulation}")
        if self.signals.domains:
            lines.append(f"domains    = {', '.join(sorted(self.signals.domains))}")
        if self.signals.modes:
            lines.append(f"modes      = {', '.join(sorted(self.signals.modes))}")

        lines.append(f"safety     = {self.safety.action.name}")
        for reason in self.safety.reasons:
            lines.append(f"             - {reason}")

        if self.preempted:
            lines.append("route      = PREEMPTED (no persona engaged)")
            return "\n".join(lines)

        lines.append(f"route      = {self.agent_id}")
        for scored in self.ranked:
            marker = "VETO" if scored.vetoed else f"{scored.score:.3f}"
            lines.append(f"             {marker:>7}  {scored.agent_id}")
            for reason in scored.rationale:
                lines.append(f"                      · {reason}")

        for condition, target in self.handoff_hints:
            lines.append(f"handoff    = on '{condition}' -> {target}")

        return "\n".join(lines)


def _overlap(requested: frozenset[str], offered: frozenset[str]) -> float:
    """Fraction of requested tags the agent covers. Neutral when nothing asked."""
    if not requested:
        return 0.5
    return len(requested & offered) / len(requested)


# Coverage alone lets a generalist tie or beat a specialist on the specialist's
# own topic: an agent listing six domains "covers" grief exactly as well as the
# grief agent does. Blending in precision -- how much of the agent's declared
# competence the request actually occupies -- breaks that tie in favor of focus.
PRECISION_WEIGHT = 0.30


def _domain_fit(requested: frozenset[str], offered: frozenset[str]) -> float:
    """Coverage of the request, discounted by how diffuse the agent's scope is."""
    if not requested:
        return 0.5
    recall = len(requested & offered) / len(requested)
    if not offered:
        return recall * (1.0 - PRECISION_WEIGHT)
    precision = len(requested & offered) / len(offered)
    return (1.0 - PRECISION_WEIGHT) * recall + PRECISION_WEIGHT * precision


def score_agent(profile: AgentProfile, signals: RequestSignals) -> ScoredAgent:
    """Score one agent against one set of signals."""
    rationale: list[str] = []

    blocked = (signals.domains | signals.modes) & profile.contraindications
    if blocked:
        return ScoredAgent(
            agent_id=profile.id,
            score=0.0,
            rationale=(f"contraindicated for: {', '.join(sorted(blocked))}",),
            vetoed=True,
        )

    domain_fit = _domain_fit(signals.domains, profile.domains)
    matched_domains = signals.domains & profile.domains
    rationale.append(
        f"domain fit {domain_fit:.2f}"
        + (f" ({', '.join(sorted(matched_domains))})" if matched_domains else " (no topic signal)")
    )

    mode_fit = _overlap(signals.modes, profile.modes)
    matched_modes = signals.modes & profile.modes
    rationale.append(
        f"mode fit {mode_fit:.2f}"
        + (f" ({', '.join(sorted(matched_modes))})" if matched_modes else " (no mode signal)")
    )

    low, high = profile.regulation_window
    if profile.accepts(signals.regulation):
        regulation_fit = 1.0
        rationale.append(f"inside regulation window [{low}, {high}]")
    else:
        distance = low - signals.regulation if signals.regulation < low else signals.regulation - high
        regulation_fit = max(0.0, 1.0 - distance * 2.0)
        rationale.append(
            f"outside regulation window [{low}, {high}] by {distance:.2f}"
        )

    score = W_DOMAIN * domain_fit + W_MODE * mode_fit + W_REGULATION * regulation_fit

    if signals.is_dysregulated and (profile.modes & PENALIZED_MODES):
        score -= DYSREGULATION_PENALTY
        rationale.append(
            f"penalty {DYSREGULATION_PENALTY}: challenge/humor agent while caller is dysregulated"
        )

    return ScoredAgent(
        agent_id=profile.id,
        score=round(max(0.0, score), 4),
        rationale=tuple(rationale),
    )


def route(
    text: str,
    roster: dict[str, AgentProfile],
    *,
    session: SessionState | None = None,
    signals: RequestSignals | None = None,
) -> RoutingDecision:
    """Select an agent for one turn of input.

    Args:
        text: The raw user turn.
        roster: id -> profile, as returned by `profiles.load_roster`.
        session: Optional session state. Required for dependency monitoring;
            when supplied it is updated in place.
        signals: Optional pre-extracted signals, allowing a different signal
            extractor (a classifier, an embedding model) to be substituted
            without touching the policy layer.

    Returns:
        A `RoutingDecision`. When the safety layer escalates, `agent_id` is
        None and no agent is consulted.
    """
    if not roster:
        raise ValueError("roster is empty; load profiles before routing")

    if session is not None:
        session.observe(text)

    sig = signals if signals is not None else extract(
        text, turn_index=session.turn_count if session else 0
    )
    verdict = evaluate(text, sig, session)

    if verdict.action is Action.HUMAN_ESCALATION:
        return RoutingDecision(agent_id=None, signals=sig, safety=verdict)

    scored = sorted(
        (score_agent(p, sig) for p in roster.values()),
        key=lambda s: (-s.score, s.agent_id),
    )
    eligible = [s for s in scored if not s.vetoed]

    if not eligible:
        # Every agent is contraindicated. Rather than force a bad route, fall
        # back to the agent with the widest safe regulation window -- by
        # construction the roster's stabilizer.
        widest = max(
            roster.values(),
            key=lambda p: (p.regulation_window[1] - p.regulation_window[0], p.id),
        )
        return RoutingDecision(
            agent_id=widest.id,
            signals=sig,
            safety=verdict,
            ranked=tuple(scored),
        )

    selected = eligible[0]
    profile = roster[selected.agent_id]
    hints = tuple(
        (condition, target)
        for condition, target in sorted(profile.handoffs.items())
        if condition in sig.domains or condition in sig.modes
    )

    return RoutingDecision(
        agent_id=selected.agent_id,
        signals=sig,
        safety=verdict,
        ranked=tuple(scored),
        handoff_hints=hints,
    )
