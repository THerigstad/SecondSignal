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

The decision tree, top to bottom (ADR-0016):

1. Acute danger -> the crisis card. No exceptions; the router never sees it.
2. Seat-claiming domains -> the named expert. A first-person return to use
   claims the recovery persona whatever else is in the message; somatic
   distress claims the stabilizer. Everyone else is set aside as
   ``outranked``: they did nothing wrong, and the trace says so.
3. Hold domains -> an obligation on whatever seat wins. Grief, abuse,
   eating distress and recovery status are carried, not necessarily spoken
   to first. ``held`` and ``obligations`` travel on the decision so the
   generation layer knows what it owes and a harness can check that it paid.
4. Ask fit -> the score (domain, mode, regulation).
5. Dysregulation -> the stabilizer is preferred and challenge is penalized.
6. Declared affinities -> tie-breaks and the advisory assist, never
   overriding 1 or 2, never rehabilitating a vetoed persona.
7. Shadow seat recorded; assist emitted.

Seat, shadow and assist all pass through the same ``eligible`` gate:
contraindications (including on every held domain), the regulation floor,
and the register caps. The assist channel was the leak every reviewer of
this design found; one function closes it.

Three things a decision must never do (ADR-0011, ADR-0012):

* resolve a tie by accident. When candidates tie, the trace names the rule
  that broke the tie (specialist precision, then the wider safe window). Id
  order is the last resort and is named as such.
* seat an agent on an empty extract by default. No topic, no mode and no
  regulation evidence is a first-class outcome (``UNRESOLVED``), not a tie.
  The seat that takes the second consecutive empty turn is the roster's
  stabilizer, resolved by role at load, never a literal id in this file.
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

from .lexicon import Span
from .profiles import AgentProfile, find_stabilizers, roster_hash
from .safety import CAPPED_MODES, Action, SafetyVerdict, SessionState, evaluate
from .signals import HOLD_DOMAINS, SEAT_CLAIM_TERMS, RequestSignals, extract

__all__ = [
    "Outcome",
    "RoutingDecision",
    "ScoredAgent",
    "route",
    "score_agent",
    "eligible",
    "claim_subject",
    "no_signal_seat",
    "NO_SIGNAL_SEAT_ROLE",
    "NO_SIGNAL_SEAT_AFTER_TURNS",
    "SEAT_CLAIMING_DOMAINS",
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
# From the second consecutive empty turn the roster's stabilizer receives the
# caller, by policy and with the policy named in the trace. The seat is a
# *role*, resolved from the loaded roster; profile loading guarantees the role
# is filled. No agent id is written into this file.
NO_SIGNAL_SEAT_ROLE = "stabilizer"
NO_SIGNAL_SEAT_AFTER_TURNS = 2

# Domains that claim the seat when present (tree layer 2). ``somatic_distress``
# is claimed by whoever carries it -- in the shipped roster, the stabilizer.
# ``addiction_recovery`` claims only when the evidence is present use or a
# return to use (``SEAT_CLAIM_TERMS``); recovery status alone is a hold.
SEAT_CLAIMING_DOMAINS: tuple[str, ...] = ("somatic_distress", "addiction_recovery")

# What a seat owes on a held domain. Recorded, and checked later by the
# harness; the policy layer cannot enforce a sentence it never writes.
HOLD_OBLIGATIONS: dict[str, tuple[str, ...]] = {
    "grief": ("acknowledge", "no_joke", "offer_companion"),
    "abuse": ("acknowledge", "no_joke", "no_challenge", "offer_human_help"),
    "eating_distress": ("acknowledge", "no_joke", "no_numbers", "offer_companion"),
    "addiction_recovery": ("acknowledge", "no_joke", "offer_companion"),
}


def no_signal_seat(roster: dict[str, AgentProfile]) -> str | None:
    """The agent that fills the stabilizer role in this roster, or None."""
    ids = find_stabilizers(roster)
    return ids[0] if ids else None


class Outcome(str, Enum):
    ROUTED = "ROUTED"          # exactly one agent seated on merit or by named policy
    PREEMPTED = "PREEMPTED"    # safety gate held the floor; no persona
    UNRESOLVED = "UNRESOLVED"  # no routable signal; nobody seated; ask for one more sentence


@dataclass(frozen=True)
class ScoredAgent:
    """One candidate's score and status. Zero has five meanings, and the
    status says which: ``vetoed`` (a contraindication matched, on the request
    or on a held domain), ``below_floor`` (the caller is under the agent's
    regulation floor), ``capped`` (every mode the agent offers is vetoed by
    the register caps or a hold), ``outranked`` (a seat-claiming domain is
    present and the agent does not carry it), or ``no_signal`` (nothing to
    score). A ``scored`` agent with score 0.0 simply matched nothing."""

    agent_id: str
    score: float
    rationale: tuple[str, ...]
    vetoed: bool = False
    status: str = "scored"

    @property
    def eligible(self) -> bool:
        return self.status == "scored"


def _span_to_dict(span: Span) -> dict[str, object]:
    """Serialize one lexicon span without relying on dataclass internals."""
    return {
        "text": span.text,
        "pattern_id": span.pattern_id,
        "start": span.start,
        "end": span.end,
        "kind": span.kind,
        "pack": span.pack,
        "domain": span.domain,
    }


def _signals_to_dict(signals: RequestSignals) -> dict[str, object]:
    """Serialize the signal boundary, sorting its unordered collections."""
    return {
        "regulation": signals.regulation,
        "domains": sorted(signals.domains),
        "modes": sorted(signals.modes),
        "evidence": {
            key: list(signals.evidence[key])
            for key in sorted(signals.evidence)
        },
        "turn_index": signals.turn_index,
    }


def _safety_to_dict(verdict: SafetyVerdict) -> dict[str, object]:
    """Serialize every stored field on a safety verdict."""
    return {
        "action": verdict.action.name,
        "reasons": list(verdict.reasons),
        "disclosures": list(verdict.disclosures),
        "crisis_read": verdict.crisis_read,
        "crisis_classes": list(verdict.crisis_classes),
        "lexicon_status": verdict.lexicon_status,
        "integrity_event": verdict.integrity_event,
        "language_scope": verdict.language_scope,
        "card": verdict.card,
        "card_order": list(verdict.card_order),
        "latch": verdict.latch,
        "latch_reasons": list(verdict.latch_reasons),
        "register_caps": list(verdict.register_caps),
        "holds": list(verdict.holds),
        "masked_spans": [_span_to_dict(span) for span in verdict.masked_spans],
        "hit_spans": [_span_to_dict(span) for span in verdict.hit_spans],
        "pack_ids": list(verdict.pack_ids),
        "patterns_hash": verdict.patterns_hash,
        "normalized_forms": list(verdict.normalized_forms),
        "mixed_script_tokens": verdict.mixed_script_tokens,
        "frustration_frame": verdict.frustration_frame,
        "preference_result": verdict.preference_result,
        "preference_key": verdict.preference_key,
        "facilitation": verdict.facilitation,
    }


def _scored_agent_to_dict(scored: ScoredAgent) -> dict[str, object]:
    """Serialize every stored field on a ranked candidate."""
    return {
        "agent_id": scored.agent_id,
        "score": scored.score,
        "rationale": list(scored.rationale),
        "vetoed": scored.vetoed,
        "status": scored.status,
    }


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
    seat_claim: str | None = None
    claim_subject: str | None = None   # "self" | "other" for a recovery claim
    held: tuple[str, ...] = ()
    obligations: tuple[str, ...] = ()
    assist_agent_id: str | None = None
    assist_reason: str = ""
    mode_vetoes: tuple[str, ...] = ()

    @property
    def preempted(self) -> bool:
        """True when the safety layer prevented any persona from engaging."""
        return self.outcome is Outcome.PREEMPTED

    @property
    def would_have_seated(self) -> str | None:
        """On a gated turn, the seat the ask would have produced. Never seated."""
        return self.shadow_agent_id if self.preempted else None

    @property
    def register_caps(self) -> tuple[str, ...]:
        return self.safety.register_caps

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, standard-library JSON-ready record.

        The schema is written field by field so adding a decision, signal,
        verdict, candidate, or span field requires an explicit schema choice.
        Enums use their names, unordered signal sets are sorted, and every
        mapping key is a string.
        """
        return {
            "schema_version": 1,
            "agent_id": self.agent_id,
            "signals": _signals_to_dict(self.signals),
            "safety": _safety_to_dict(self.safety),
            "ranked": [_scored_agent_to_dict(scored) for scored in self.ranked],
            "handoff_hints": [list(hint) for hint in self.handoff_hints],
            "outcome": self.outcome.name,
            "reason": self.reason,
            "shadow_agent_id": self.shadow_agent_id,
            "roster_hash": self.roster_hash,
            "seat_claim": self.seat_claim,
            "claim_subject": self.claim_subject,
            "held": list(self.held),
            "obligations": list(self.obligations),
            "assist_agent_id": self.assist_agent_id,
            "assist_reason": self.assist_reason,
            "mode_vetoes": list(self.mode_vetoes),
            "explain": self.explain(),
        }

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
        if self.safety.masked_spans:
            lines.append("masked     = " + ", ".join(f"{s.pattern_id}:{s.text!r}" for s in self.safety.masked_spans))
        if self.safety.hit_spans:
            lines.append("hit spans  = " + ", ".join(f"{s.pattern_id}:{s.text!r}" for s in self.safety.hit_spans))
        lines.append(f"patterns   = {self.safety.patterns_hash} packs={','.join(self.safety.pack_ids)}")
        if self.safety.latch != "none":
            lines.append(f"latch      = {self.safety.latch} ({', '.join(self.safety.latch_reasons)}) caps={','.join(self.safety.register_caps)}")

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
        if self.seat_claim:
            lines.append(f"seat claim = {self.seat_claim}" + (f" (subject: {self.claim_subject})" if self.claim_subject else ""))
        if self.held:
            lines.append(f"held       = {', '.join(self.held)}")
        if self.obligations:
            # P-11: obligations are printed independently of held domains. A
            # relative's relapse carries family-impact obligations with an
            # empty held list, so nesting this line under held made the
            # requirements of that decision invisible in the trace.
            lines.append(f"obligations = {', '.join(self.obligations)}")
        if self.assist_agent_id:
            lines.append(f"assist     = {self.assist_agent_id} ({self.assist_reason})")
        if self.mode_vetoes:
            lines.append(f"mode veto  = {', '.join(self.mode_vetoes)}")
        for scored in self.ranked:
            marker = {
                "vetoed": "VETO",
                "below_floor": "FLOOR",
                "no_signal": "EMPTY",
                "capped": "CAPPED",
                "outranked": "OUTRANK",
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

# Under a hold, the seat is scored on the ask; an agent that also carries the
# held domain gets this much on top of its ask fit. It outweighs the precision
# term (at most 0.30 of a fraction) and never a domain of the ask (0.70 each).
HOLD_CARRY_BONUS = 0.10


def _domain_fit(requested: frozenset[str], offered: frozenset[str]) -> float:
    """Coverage of the request, discounted by how diffuse the agent's scope is."""
    if not requested:
        return 0.5
    recall = len(requested & offered) / len(requested)
    if not offered:
        return recall * (1.0 - PRECISION_WEIGHT)
    precision = len(requested & offered) / len(offered)
    return (1.0 - PRECISION_WEIGHT) * recall + PRECISION_WEIGHT * precision


def seat_claims(signals: RequestSignals) -> tuple[str, ...]:
    """Domains in this request that claim the seat (tree layer 2)."""
    claims: list[str] = []
    if "somatic_distress" in signals.domains:
        claims.append("somatic_distress")
    if "addiction_recovery" in signals.domains:
        terms = set(signals.evidence.get("domain:addiction_recovery", ()))
        # A first-person return to use claims the seat. A relative's return to
        # use is a hold, not a seat-claim (D3, decided with dissent on
        # 8 September 2026; built 10 September; ADR-0027 (Proposed) amends
        # ADR-0016): the bare report still seats the recovery persona as the
        # hold's specialist, and an ask seats the ask with the recovery hold
        # carried and the recovery persona offered as a companion. Whose it
        # is travels on the decision as ``claim_subject`` either way.
        person = signals.evidence.get("domain:addiction_recovery:person", ("first",))
        if terms & SEAT_CLAIM_TERMS and person != ("third",):
            claims.append("addiction_recovery")
    return tuple(claims)


def claim_subject(signals: RequestSignals, claims: tuple[str, ...]) -> str | None:
    """``self`` or ``other`` for a return to use, whether it claimed the seat
    (first person) or is carried as a hold (a relative's); None otherwise."""
    if "addiction_recovery" not in signals.domains:
        return None
    terms = set(signals.evidence.get("domain:addiction_recovery", ()))
    if not terms & SEAT_CLAIM_TERMS:
        return None
    person = signals.evidence.get("domain:addiction_recovery:person", ("first",))
    return "other" if person == ("third",) else "self"


def holds_for(signals: RequestSignals, claims: tuple[str, ...]) -> tuple[str, ...]:
    """Domains this request obliges the seat to carry (tree layer 3)."""
    return tuple(d for d in HOLD_DOMAINS if d in signals.domains and d not in claims)


def eligible(
    profile: AgentProfile,
    signals: RequestSignals,
    *,
    holds: tuple[str, ...] = (),
    claims: tuple[str, ...] = (),
    mode_vetoes: frozenset[str] = frozenset(),
) -> tuple[str, tuple[str, ...]]:
    """One gate for seat, shadow and assist. Returns (status, rationale).

    ``scored`` means eligible. Anything else names why not: a contraindication
    on the request or on a held domain, the regulation floor, the register
    caps leaving the agent no mode to speak in, or a seat-claiming domain the
    agent does not carry.
    """
    # Contraindications are checked against the request *as spoken*. A mode
    # the turn vetoes for everyone (humor under a grief hold, challenge under
    # a register cap) still counts against an agent contraindicated on it:
    # the ask was made, and the seat has to hold that ask without honoring
    # its framing. The alternative -- exempting vetoed modes -- was measured
    # during round 2 and rejected: it let the grief specialist sit on "make
    # my grandmother's death funny" and produced id-order ties on capped
    # turns (docs/notes/dissent-log.md, ADR-0016).
    blocked = (signals.domains | signals.modes | frozenset(holds)) & profile.contraindications
    if blocked:
        held_block = frozenset(holds) & profile.contraindications
        why = f"contraindicated for: {', '.join(sorted(blocked))}"
        if held_block:
            why += f" (cannot honor hold: {', '.join(sorted(held_block))})"
        return "vetoed", (why,)

    low, high = profile.regulation_window
    if signals.regulation < low:
        # The floor is eligibility, not a penalty (ADR-0012).
        return "below_floor", (f"below regulation floor {low}: caller at {signals.regulation}",)

    if mode_vetoes and profile.modes and not (profile.modes - mode_vetoes):
        return "capped", (f"every offered mode is vetoed this turn ({', '.join(sorted(profile.modes))})",)

    for claim in claims:
        if claim not in profile.domains:
            return "outranked", (f"seat-claiming domain {claim!r} present; agent does not carry it",)

    return "scored", ()


def score_agent(
    profile: AgentProfile,
    signals: RequestSignals,
    *,
    holds: tuple[str, ...] = (),
    claims: tuple[str, ...] = (),
    mode_vetoes: frozenset[str] = frozenset(),
) -> ScoredAgent:
    """Score one agent against one set of signals."""
    status, why = eligible(profile, signals, holds=holds, claims=claims, mode_vetoes=mode_vetoes)
    if status != "scored":
        return ScoredAgent(
            agent_id=profile.id,
            score=0.0,
            rationale=why,
            vetoed=(status == "vetoed"),
            status=status,
        )

    if signals.is_empty:
        return ScoredAgent(
            agent_id=profile.id,
            score=0.0,
            rationale=("no routable signal",),
            status="no_signal",
        )

    rationale: list[str] = []
    low, high = profile.regulation_window
    offered_modes = profile.modes - mode_vetoes
    requested_modes = signals.modes - mode_vetoes

    # Under a hold the seat is scored on the *ask* -- the request minus the
    # held domains -- because the held domain is carried by whoever sits, not
    # seated (tree layer 3 before layer 4). When the request is nothing but
    # the held domain, the held domain is the ask and its specialist sits.
    held = frozenset(holds)
    ask = signals.domains - held
    topic = ask if ask else signals.domains
    domain_fit = _domain_fit(topic, profile.domains)
    matched_domains = topic & profile.domains
    carried = (held & profile.domains) if (held and ask) else frozenset()
    if carried:
        # An agent that carries the hold as well as the ask keeps the person
        # with one voice; that is worth more than a precision decimal and
        # less than a domain of the ask (HOLD_CARRY_BONUS sits between).
        domain_fit = min(1.0, domain_fit + HOLD_CARRY_BONUS * len(carried) / len(held))
    rationale.append(
        f"domain fit {domain_fit:.2f}"
        + (f" ({', '.join(sorted(matched_domains))})" if matched_domains else " (no topic signal)")
        + (f" incl. hold carry +{HOLD_CARRY_BONUS * len(carried) / len(held):.2f}" if carried else "")
    )
    if held and ask:
        rationale.append(
            f"held {', '.join(sorted(held))} carried, not scored; fit taken on the ask ({', '.join(sorted(ask))})"
            + (f"; carries the hold ({', '.join(sorted(carried))})" if carried else "")
        )

    mode_fit = _overlap(requested_modes, offered_modes)
    matched_modes = requested_modes & offered_modes
    rationale.append(
        f"mode fit {mode_fit:.2f}"
        + (f" ({', '.join(sorted(matched_modes))})" if matched_modes else " (no mode signal)")
    )
    if mode_vetoes & profile.modes:
        rationale.append(f"modes vetoed this turn: {', '.join(sorted(mode_vetoes & profile.modes))}")

    if signals.regulation <= high:
        regulation_fit = 1.0
        rationale.append(f"inside regulation window [{low}, {high}]")
    else:
        distance = signals.regulation - high
        regulation_fit = max(0.0, 1.0 - distance * 2.0)
        rationale.append(f"above regulation window [{low}, {high}] by {distance:.2f}")

    score = W_DOMAIN * domain_fit + W_MODE * mode_fit + W_REGULATION * regulation_fit

    if signals.is_dysregulated and (offered_modes & PENALIZED_MODES):
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
    claims: tuple[str, ...] = (),
    holds: tuple[str, ...] = (),
    mode_vetoes: frozenset[str] = frozenset(),
) -> tuple[ScoredAgent | None, str]:
    """Pick the winner among eligible candidates and name the rule that did it.

    Order of rules: a seat-claiming domain narrows the field first; then the
    highest score; then, under a hold, the agent that carries the *ask* (the
    held domain is carried by whoever sits, not seated), then the one that
    also carries the hold; then the more focused agent (fewer declared
    domains); then the wider safe window (lower regulation floor); then id
    order, which is named explicitly so it can be seen and tested against.
    """
    eligible_agents = [s for s in scored if s.eligible]
    if not eligible_agents:
        return None, "no eligible agent"
    top = max(s.score for s in eligible_agents)
    tied = [s for s in eligible_agents if s.score == top]
    prefix = f"seat-claiming domain {claims[0]!r}; " if claims else ""

    live_modes = signals.modes - mode_vetoes
    if not signals.domains and not live_modes:
        # Nothing routable is left once the vetoes are applied: either the
        # only signal is the caller's state, or every requested mode is vetoed
        # this turn (a roast asked for under a register cap). The stabilizer
        # (safe at any state, never vetoed) takes precedence over topic
        # precision, which would otherwise seat whoever lists the fewest
        # domains. Named so it can be seen and tested.
        stabilizers = [s for s in tied if roster[s.agent_id].is_stabilizer]
        if stabilizers:
            winner = sorted(stabilizers, key=lambda s: s.agent_id)[0]
            if signals.modes:
                return winner, prefix + (
                    f"requested modes vetoed this turn ({', '.join(sorted(signals.modes & mode_vetoes))}) "
                    "and no topic; stabilizer preferred"
                )
            return winner, prefix + "regulation-only signal; stabilizer preferred (no topic to weigh)"

    stabilizers = [s for s in tied if roster[s.agent_id].is_stabilizer]
    if not signals.domains and stabilizers and len(tied) > 1:
        # A mode with no topic ("just listen", "help me make sense of this")
        # ties every agent that offers the mode. The stabilizer is the
        # roster's designated seat for a caller with no topic (ADR-0011).
        winner = sorted(stabilizers, key=lambda s: s.agent_id)[0]
        return winner, prefix + (
            f"mode-only signal ({', '.join(sorted(live_modes))}); no topic to weigh; stabilizer preferred"
        )
    if signals.domains and stabilizers and len(tied) > 1 and not any(
        signals.domains & roster[s.agent_id].domains for s in tied
    ):
        # A topic nobody eligible carries (abuse and eating distress in the
        # shipped roster; anything the vetoes emptied out). The obligations
        # still attach; the stabilizer delivers them.
        winner = sorted(stabilizers, key=lambda s: s.agent_id)[0]
        return winner, prefix + (
            f"no eligible agent carries the topic ({', '.join(sorted(signals.domains))}); stabilizer preferred"
        )

    if len(tied) == 1:
        winner = tied[0]
        carried = signals.domains & roster[winner.agent_id].domains
        basis = f"specialist signal: {', '.join(sorted(carried))}" if carried else (
            f"mode signal: {', '.join(sorted(live_modes & roster[winner.agent_id].modes))}"
            if (live_modes & roster[winner.agent_id].modes) else "regulation window"
        )
        return winner, prefix + f"highest score ({basis})"

    if holds:
        ask = signals.domains - frozenset(holds)
        carries_ask = [s for s in tied if ask & roster[s.agent_id].domains]
        if carries_ask and len(carries_ask) < len(tied):
            tied = carries_ask
            if len(tied) == 1:
                return tied[0], prefix + (
                    f"tie on score {top:.3f} broken by the ask ({', '.join(sorted(ask))}); "
                    f"held domain {', '.join(holds)} is carried, not seated"
                )
        carries_hold = [s for s in tied if frozenset(holds) & roster[s.agent_id].domains]
        if carries_hold and len(carries_hold) < len(tied):
            tied = carries_hold
            if len(tied) == 1:
                return tied[0], prefix + (
                    f"tie on score {top:.3f} broken by carrying the held domain ({', '.join(holds)})"
                )

    by_precision = sorted(tied, key=lambda s: len(roster[s.agent_id].domains))
    if len(roster[by_precision[0].agent_id].domains) < len(roster[by_precision[1].agent_id].domains):
        return by_precision[0], prefix + f"tie on score {top:.3f} broken by specialist precision"

    by_floor = sorted(tied, key=lambda s: roster[s.agent_id].regulation_window[0])
    if roster[by_floor[0].agent_id].regulation_window[0] < roster[by_floor[1].agent_id].regulation_window[0]:
        return by_floor[0], prefix + f"tie on score {top:.3f} broken by wider safe window"

    by_id = sorted(tied, key=lambda s: s.agent_id)
    return by_id[0], prefix + f"tie on score {top:.3f} unresolved by policy; id order ({', '.join(s.agent_id for s in by_id)})"


def _obligations(
    holds: tuple[str, ...],
    roster: dict[str, AgentProfile],
    seated: str | None,
    subject: str | None = None,
    aftermath: bool = False,
) -> tuple[str, ...]:
    out: list[str] = []
    if aftermath:
        out.append("no_joke")
    if subject == "other":
        # A relative's relapse claims the recovery seat and still owes the
        # family-impact acknowledgement a hold would have carried.
        out += ["affected_person:other", "acknowledge:addiction_recovery", "no_joke"]
    for hold in holds:
        for ob in HOLD_OBLIGATIONS.get(hold, ("acknowledge",)):
            if ob == "offer_companion":
                carriers = sorted(
                    (p for p in roster.values() if hold in p.domains and p.id != seated),
                    key=lambda p: (len(p.domains), p.id),
                )
                if carriers:
                    out.append(f"offer_companion:{carriers[0].id}")
                continue
            out.append(f"{ob}:{hold}" if ob == "acknowledge" else ob)
    # de-duplicate, order preserved
    seen: set[str] = set()
    unique: list[str] = []
    for obligation in out:
        if obligation not in seen:
            seen.add(obligation)
            unique.append(obligation)
    return tuple(unique)


def _assist(
    session: SessionState | None,
    roster: dict[str, AgentProfile],
    signals: RequestSignals,
    seated: str | None,
    holds: tuple[str, ...],
    claims: tuple[str, ...],
    mode_vetoes: frozenset[str],
) -> tuple[str | None, str]:
    """Advisory second voice from a declared affinity. Passes the same gate as
    the seat (minus the seat-claim, which the assist cannot take), and can
    never be the seated agent. Nothing is inferred: no affinity, no assist."""
    if session is None or not session.affinities or seated is None:
        return None, ""
    if signals.is_dysregulated or "somatic_distress" in claims:
        return None, "no assist while the caller is acutely dysregulated; one voice speaks"
    candidates: list[tuple[str, AgentProfile]] = []
    excluded: list[str] = []
    for affinity in session.affinities:
        for profile in roster.values():
            if profile.id == seated:
                continue
            matches = (
                (affinity == "prefers_female_voice" and profile.voice == "f")
                or (affinity == "prefers_male_voice" and profile.voice == "m")
                or (affinity == "prefers_challenge" and "challenge" in profile.modes)
                or affinity in {f"prefers_{name}" for name in profile.names}
            )
            if not matches:
                continue
            status, why = eligible(profile, signals, holds=holds, claims=(), mode_vetoes=mode_vetoes)
            if status != "scored":
                # Named, so the record shows the affinity was heard and why
                # it could not be honored by this persona on this turn.
                label = "contraindication" if status == "vetoed" else status
                excluded.append(f"{profile.id} excluded ({label}: {'; '.join(why)})")
                continue
            if affinity == "prefers_challenge" and "challenge" in mode_vetoes:
                excluded.append(f"{profile.id} excluded (challenge vetoed this turn)")
                continue
            candidates.append((affinity, profile))
    if not candidates:
        reasons = "no eligible assist for declared affinities " + ", ".join(session.affinities)
        if holds:
            reasons += f" under hold {', '.join(holds)}"
        if excluded:
            reasons += "; " + "; ".join(excluded)
        return None, reasons
    # Prefer the candidate that carries the most of the request, then precision, then id.
    affinity, best = sorted(
        candidates,
        key=lambda ap: (-len(signals.domains & ap[1].domains), len(ap[1].domains), ap[1].id),
    )[0]
    reason = f"declared affinity {affinity}; eligible under holds {', '.join(holds) or 'none'}"
    if excluded:
        reason += "; " + "; ".join(excluded)
    return best.id, reason


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
        session: Optional session state. Required for dependency monitoring,
            the latch, affinities and the no-signal policy's turn count; when
            supplied it is updated in place.
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
    stabilizer = no_signal_seat(roster)

    if session is not None:
        session.note_extract(sig.is_empty)

    claims = seat_claims(sig)
    subject = claim_subject(sig, claims)
    holds = holds_for(sig, claims)
    mode_vetoes: set[str] = set()
    if verdict.register_caps:
        mode_vetoes |= set(CAPPED_MODES)
    if holds:
        mode_vetoes |= {"challenge", "humor"}
    # Bounded aftermath (C3): humour is off for a fixed count of substantive
    # turns after any card; the verdict's reasons say how many remain.
    aftermath = bool(session is not None and session.aftermath_turns > 0 and not session.escalated_last_turn)
    if aftermath:
        mode_vetoes.add("humor")
    vetoes = frozenset(mode_vetoes)

    scored = sorted(
        (score_agent(p, sig, holds=holds, claims=claims, mode_vetoes=vetoes) for p in roster.values()),
        key=lambda s: (-s.score, s.agent_id),
    )

    if verdict.action is Action.HUMAN_ESCALATION:
        # Compute the shadow seat for the record; never seat it.
        shadow, _ = _select(scored, roster, sig, claims, holds, vetoes) if not sig.is_empty else (None, "")
        # ``ranked`` stays empty on a gated turn: nothing is scored for
        # seating once the gate holds the floor. The shadow is the only
        # routing fact recorded, and it is never seated.
        return RoutingDecision(
            agent_id=None,
            signals=sig,
            safety=verdict,
            outcome=Outcome.PREEMPTED,
            reason="safety gate holds the floor",
            shadow_agent_id=shadow.agent_id if shadow else None,
            roster_hash=rhash,
            seat_claim=claims[0] if claims else None,
            claim_subject=subject,
            held=holds,
            obligations=_obligations(holds, roster, None, subject, aftermath),
            mode_vetoes=tuple(sorted(vetoes)),
        )

    if sig.is_empty:
        streak = session.empty_streak if session is not None else 1
        if verdict.action is not Action.PROCEED and stabilizer is not None:
            # A held boundary or a required disclosure must be delivered by a
            # persona; with no topic to route on, the stabilizer delivers it.
            return RoutingDecision(
                agent_id=stabilizer,
                signals=sig,
                safety=verdict,
                ranked=tuple(scored),
                outcome=Outcome.ROUTED,
                reason=(
                    f"no routable topic, but the safety verdict ({verdict.action.name}) "
                    f"carries a required disclosure; stabilizer={stabilizer} by role (ADR-0011)"
                ),
                roster_hash=rhash,
                held=holds,
                obligations=_obligations(holds, roster, stabilizer, subject, aftermath),
                mode_vetoes=tuple(sorted(vetoes)),
            )
        if streak >= NO_SIGNAL_SEAT_AFTER_TURNS and stabilizer is not None:
            return RoutingDecision(
                agent_id=stabilizer,
                signals=sig,
                safety=verdict,
                ranked=tuple(scored),
                outcome=Outcome.ROUTED,
                reason=(
                    f"no routable signal; stabilizer={stabilizer} by role "
                    f"(empty turn {streak} of a session; ADR-0011)"
                ),
                roster_hash=rhash,
                held=holds,
                obligations=_obligations(holds, roster, stabilizer, subject, aftermath),
                mode_vetoes=tuple(sorted(vetoes)),
            )
        return RoutingDecision(
            agent_id=None,
            signals=sig,
            safety=verdict,
            ranked=tuple(scored),
            outcome=Outcome.UNRESOLVED,
            reason="no routable signal; nobody seated; ask for one more sentence (ADR-0011)",
            roster_hash=rhash,
            mode_vetoes=tuple(sorted(vetoes)),
        )

    selected, rule = _select(scored, roster, sig, claims, holds, vetoes)
    if holds:
        # The reason names what the seat owes, so a reader of the log never
        # has to cross-reference ``held`` to see that a hold was in force.
        rule += f"; hold on {', '.join(holds)} carried by the seat"

    if selected is None:
        # Every agent is contraindicated, capped, outranked or below its floor.
        # Profile loading guarantees a full-window, uncontraindicated stabilizer
        # exists, so this is only reachable with a roster that bypassed
        # validation or with caps that emptied it; fall back to the stabilizer
        # by role and say so.
        fallback = stabilizer or max(
            roster.values(),
            key=lambda p: (p.regulation_window[1] - p.regulation_window[0], p.id),
        ).id
        return RoutingDecision(
            agent_id=fallback,
            signals=sig,
            safety=verdict,
            ranked=tuple(scored),
            outcome=Outcome.ROUTED,
            reason=f"no eligible agent; fallback to the stabilizer role ({fallback})",
            roster_hash=rhash,
            seat_claim=claims[0] if claims else None,
            claim_subject=subject,
            held=holds,
            obligations=_obligations(holds, roster, fallback, subject, aftermath),
            mode_vetoes=tuple(sorted(vetoes)),
        )

    profile = roster[selected.agent_id]
    hints = tuple(
        (condition, target)
        for condition, target in sorted(profile.handoffs.items())
        if condition in sig.domains or condition in sig.modes
    )
    shadow_agent_id = next(
        (s.agent_id for s in scored if s.eligible and s.agent_id != selected.agent_id),
        None,
    )
    assist_id, assist_reason = _assist(session, roster, sig, selected.agent_id, holds, claims, vetoes)

    return RoutingDecision(
        agent_id=selected.agent_id,
        signals=sig,
        safety=verdict,
        ranked=tuple(scored),
        handoff_hints=hints,
        outcome=Outcome.ROUTED,
        reason=rule,
        shadow_agent_id=shadow_agent_id,
        roster_hash=rhash,
        seat_claim=claims[0] if claims else None,
        claim_subject=subject,
        held=holds,
        obligations=_obligations(holds, roster, selected.agent_id, subject, aftermath),
        assist_agent_id=assist_id,
        assist_reason=assist_reason,
        mode_vetoes=tuple(sorted(vetoes)),
    )
