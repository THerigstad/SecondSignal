"""Routing policy.

The thesis of this repository is that in a multi-agent system, *which agent
responds* is a policy decision, and policy decisions should be explicit,
scored, logged, and testable -- not an emergent property of a prompt telling a
model to "pick whichever persona fits."

`route()` is therefore deterministic and pure. Given the same signals and the
same roster it returns the same decision, with a rationale that names every
term that contributed to the score, the rule that produced the winner, and
the status of every candidate that did not win. That property is what makes
the behavior of the system auditable after the fact, which is the difference
between a system you can operate and a system you can only demo.

Three things a decision must never do (ADR-0011, ADR-0012):

* resolve a tie by accident. When candidates tie, the trace names the rule
  that broke the tie (specialist precision, then the wider safe window). Id
  order is the last resort and is named as such.
* seat an agent on an empty extract by default. No topic, no mode and no
  regulation evidence is a first-class outcome (``UNRESOLVED``), not a tie.
* hand a caller to an agent below that agent's declared regulation floor. The
  floor is eligibility, not a score penalty.

On a gated turn the router still computes the agent it *would* have seated and
records it as ``shadow_agent_id`` -- never in ``agent_id`` -- so that the
question "which persona is the attractor when language is mixed" has data
without anyone being seated.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .profiles import AgentProfile, roster_hash
from .safety import Action, SafetyVerdict, SessionState, evaluate
from .signals import RequestSignals, extract

__all__ = [
    "Outcome",
    "RoutingDecision",
    "ScoredAgent",
    "route",
    "score_agent",
    "NO_SIGNAL_SEAT",
    "NO_SIGNAL_SEAT_AFTER_TURNS",
]

W_DOMAIN = 0.45
W_MODE = 0.30
W_REGULATION = 0.25

# When the caller is acutely dysregulated, agents whose value is challenge or
# humor are penalized even if they are inside their declared window. Comedy as
# a reframe tool requires a floor of regulation to land as relief rather than
# as dismissal.
DYSREGULATION_PENALTY = 0.35
PENALIZED_MODES = frozenset({"challenge", "humor"})

# No-signal policy (ADR-0011). On the first empty extract in a session nobody
# is seated and the decision says so; the surface asks for one more sentence.
# From the second consecutive empty turn the named seat receives the caller,
# by policy and with the policy named in the trace. The seat is a single
# constant so the choice is reviewable and reversible in one line. It must
# name an agent that is safe at full dysregulation and carries no
# contraindications; profile loading guarantees such an agent exists.
NO_SIGNAL_SEAT = "calder"
NO_SIGNAL_SEAT_AFTER_TURNS = 2


class Outcome(str, Enum):
    ROUTED = "ROUTED"          # exactly one agent seated on merit or by named policy
    PREEMPTED = "PREEMPTED"    # safety gate held the floor; no persona
    UNRESOLVED = "UNRESOLVED"  # no routable signal; nobody seated; ask for one more sentence


@dataclass(frozen=True)
class ScoredAgent:
    """One candidate's score and status. Zero has three meanings, and the
    status says which: ``vetoed`` (a contraindication matched), ``below_floor``
    (the caller is under the agent's regulation floor), or ``no_signal``
    (nothing to score). A ``scored`` agent with score 0.0 simply matched
    nothing."""

    agent_id: str
    score: float
    rationale: tuple[str, ...]
    vetoed: bool = False
    status: str = "scored"

    @property
    def eligible(self) -> bool:
        return self.status == "scored"


@dataclass(frozen=True)
class RoutingDecision:
    """The full, loggable record of one routing decision."""

    agent_id: str | None
    signals: RequestSignals
    safety: SafetyVerdict
    ranked: tuple[ScoredAgent, ...] = ()
    handoff_hints: tuple[tuple[str, str], ...] = ()
    outcome: Outcome = Outcome.ROUTED
    reason: str = ""
    shadow_agent_id: str | None = None
    roster_hash: str = ""

    @property
    def preempted(self) -> bool:
        """True when the safety layer prevented any persona from engaging."""
        return self.outcome is Outcome.PREEMPTED

    def explain(self) -> str:
        """Human-readable trace of why this decision was made."""
        lines: list[str] = []
        lines.append(f"regulation = {self.signals.regulation}")
        if self.signals.domains:
            lines.append(f"domains    = {', '.join(sorted(self.signals.domains))}")
        if self.signals.modes:
            lines.append(f"modes      = {', '.join(sorted(self.signals.modes))}")
        if self.signals.is_empty:
            lines.append("extract    = EMPTY (no topic, no mode, no regulation evidence)")

        lines.append(f"safety     = {self.safety.action.name}  (crisis read: {self.safety.crisis_read}, lexicon: {self.safety.lexicon_status})")
        for reason in self.safety.reasons:
            lines.append(f"             - {reason}")

        if self.preempted:
            lines.append("route      = PREEMPTED (no persona engaged)")
            if self.shadow_agent_id:
                lines.append(f"shadow     = would have seated {self.shadow_agent_id} (recorded, never seated)")
            lines.append(f"reason     = {self.reason}")
            lines.append(f"roster     = {self.roster_hash}")
            return "\n".join(lines)

        if self.outcome is Outcome.UNRESOLVED:
            lines.append("route      = UNRESOLVED (no agent seated; ask for one more sentence)")
        else:
            lines.append(f"route      = {self.agent_id}")
        lines.append(f"reason     = {self.reason}")
        for scored in self.ranked:
            marker = {
                "vetoed": "VETO",
                "below_floor": "FLOOR",
                "no_signal": "EMPTY",
            }.get(scored.status, f"{scored.score:.3f}")
            lines.append(f"             {marker:>7}  {scored.agent_id}")
            for reason in scored.rationale:
                lines.append(f"                      · {reason}")

        for condition, target in self.handoff_hints:
            lines.append(f"handoff    = on '{condition}' -> {target}")
        lines.append(f"roster     = {self.roster_hash}")

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
            status="vetoed",
        )

    low, high = profile.regulation_window
    if signals.regulation < low:
        # The floor is eligibility, not a penalty (ADR-0012).
        return ScoredAgent(
            agent_id=profile.id,
            score=0.0,
            rationale=(f"below regulation floor {low}: caller at {signals.regulation}",),
            status="below_floor",
        )

    if signals.is_empty:
        return ScoredAgent(
            agent_id=profile.id,
            score=0.0,
            rationale=("no routable signal",),
            status="no_signal",
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

    if signals.regulation <= high:
        regulation_fit = 1.0
        rationale.append(f"inside regulation window [{low}, {high}]")
    else:
        distance = signals.regulation - high
        regulation_fit = max(0.0, 1.0 - distance * 2.0)
        rationale.append(f"above regulation window [{low}, {high}] by {distance:.2f}")

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


def _select(
    scored: list[ScoredAgent],
    roster: dict[str, AgentProfile],
    signals: RequestSignals,
) -> tuple[ScoredAgent | None, str]:
    """Pick the winner among eligible candidates and name the rule that did it.

    Order of rules: highest score; then the more focused agent (fewer declared
    domains); then the wider safe window (lower regulation floor); then id
    order, which is named explicitly so it can be seen and tested against.
    """
    eligible = [s for s in scored if s.eligible]
    if not eligible:
        return None, "no eligible agent"
    top = max(s.score for s in eligible)
    tied = [s for s in eligible if s.score == top]

    if not signals.domains and not signals.modes:
        # Regulation-only signal: the only thing known is the caller's state,
        # so the stabilizer (safe at any state, never vetoed) takes precedence
        # over topic precision. Named so it can be seen and tested.
        stabilizers = [s for s in tied if roster[s.agent_id].is_stabilizer]
        if stabilizers:
            winner = sorted(stabilizers, key=lambda s: s.agent_id)[0]
            return winner, "regulation-only signal; stabilizer preferred (no topic to weigh)"

    if len(tied) == 1:
        winner = tied[0]
        basis = "specialist signal" if (signals.domains & roster[winner.agent_id].domains) else (
            "mode signal" if (signals.modes & roster[winner.agent_id].modes) else "regulation window"
        )
        return winner, f"highest score ({basis})"

    by_precision = sorted(tied, key=lambda s: len(roster[s.agent_id].domains))
    if len(roster[by_precision[0].agent_id].domains) < len(roster[by_precision[1].agent_id].domains):
        return by_precision[0], f"tie on score {top:.3f} broken by specialist precision"

    by_floor = sorted(tied, key=lambda s: roster[s.agent_id].regulation_window[0])
    if roster[by_floor[0].agent_id].regulation_window[0] < roster[by_floor[1].agent_id].regulation_window[0]:
        return by_floor[0], f"tie on score {top:.3f} broken by wider safe window"

    by_id = sorted(tied, key=lambda s: s.agent_id)
    return by_id[0], f"tie on score {top:.3f} unresolved by policy; id order ({', '.join(s.agent_id for s in by_id)})"


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
        session: Optional session state. Required for dependency monitoring and
            for the no-signal policy's turn count; when supplied it is updated
            in place.
        signals: Optional pre-extracted signals, allowing a different signal
            extractor (a classifier, an embedding model) to be substituted
            without touching the policy layer.

    Returns:
        A `RoutingDecision`. When the safety layer escalates, `outcome` is
        PREEMPTED and `agent_id` is None; the agent that would have been
        seated is recorded in `shadow_agent_id` only. When nothing routable
        was extracted, `outcome` is UNRESOLVED on the first such turn.
    """
    if not roster:
        raise ValueError("roster is empty; load profiles before routing")

    if session is not None:
        session.observe(text)

    sig = signals if signals is not None else extract(
        text, turn_index=session.turn_count if session else 0
    )
    verdict = evaluate(text, sig, session)
    rhash = roster_hash(roster)

    if session is not None:
        session.note_extract(sig.is_empty)

    scored = sorted(
        (score_agent(p, sig) for p in roster.values()),
        key=lambda s: (-s.score, s.agent_id),
    )

    if verdict.action is Action.HUMAN_ESCALATION:
        # Compute the shadow seat for the record; never seat it.
        shadow, _ = _select(scored, roster, sig) if not sig.is_empty else (None, "")
        return RoutingDecision(
            agent_id=None,
            signals=sig,
            safety=verdict,
            outcome=Outcome.PREEMPTED,
            reason="safety gate holds the floor",
            shadow_agent_id=shadow.agent_id if shadow else None,
            roster_hash=rhash,
        )

    if sig.is_empty:
        streak = session.empty_streak if session is not None else 1
        if verdict.action is not Action.PROCEED and NO_SIGNAL_SEAT in roster:
            # A held boundary or a required disclosure must be delivered by a
            # persona; with no topic to route on, the named seat delivers it.
            return RoutingDecision(
                agent_id=NO_SIGNAL_SEAT,
                signals=sig,
                safety=verdict,
                ranked=tuple(scored),
                outcome=Outcome.ROUTED,
                reason=(
                    f"no routable topic, but the safety verdict ({verdict.action.name}) "
                    f"carries a required disclosure; stabilizer={NO_SIGNAL_SEAT} by policy (ADR-0011)"
                ),
                roster_hash=rhash,
            )
        if streak >= NO_SIGNAL_SEAT_AFTER_TURNS and NO_SIGNAL_SEAT in roster:
            return RoutingDecision(
                agent_id=NO_SIGNAL_SEAT,
                signals=sig,
                safety=verdict,
                ranked=tuple(scored),
                outcome=Outcome.ROUTED,
                reason=(
                    f"no routable signal; stabilizer={NO_SIGNAL_SEAT} by policy "
                    f"(empty turn {streak} of a session; ADR-0011)"
                ),
                roster_hash=rhash,
            )
        return RoutingDecision(
            agent_id=None,
            signals=sig,
            safety=verdict,
            ranked=tuple(scored),
            outcome=Outcome.UNRESOLVED,
            reason="no routable signal; nobody seated; ask for one more sentence (ADR-0011)",
            roster_hash=rhash,
        )

    selected, rule = _select(scored, roster, sig)

    if selected is None:
        # Every agent is contraindicated or below its floor. Profile loading
        # guarantees a full-window, uncontraindicated stabilizer exists, so this
        # is only reachable with a roster that bypassed validation; fall back
        # to the widest safe window and say so.
        widest = max(
            roster.values(),
            key=lambda p: (p.regulation_window[1] - p.regulation_window[0], p.id),
        )
        return RoutingDecision(
            agent_id=widest.id,
            signals=sig,
            safety=verdict,
            ranked=tuple(scored),
            outcome=Outcome.ROUTED,
            reason=f"no eligible agent; fallback to widest safe window ({widest.id})",
            roster_hash=rhash,
        )

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
        outcome=Outcome.ROUTED,
        reason=rule,
        roster_hash=rhash,
    )
