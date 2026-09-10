# ADR-0016: Seat versus hold — a seven-layer routing tree with one eligibility gate

- **Status:** Accepted — built; amended 2026-09-10 by ADR-0027 (a relative's return to use is a hold, not a seat-claim)
- **Date:** 2026-09-03
- **Amended by:** ADR-0027, 2026-09-10 (layer 2, the relative's clause; the consequences paragraph)
- **Evidence:** Round-1 external design review (2026-09-02): Decisions 3 and 4 accepted with change by all five reviewers; 31 reviewer fixtures on seats, holds and the assist under `evals/cases/round1_2026-09-02/`; `tests/test_holds.py`; the round-2 measurement recorded in `docs/notes/dissent-log.md`

## Context

Two failures drove this. "I relapsed last night and I'm so ashamed, I feel
completely alone and I don't know who I am anymore" seated the grief-and-
identity persona on coverage while the only persona built for recovery came
fourth. And "since my brother died I've been stuck on the mural" seated the
unblocking persona and the loss went unacknowledged, while the obvious fix —
force the grief companion into the seat — would have answered an "unstuck"
ask with grief work.

The review agreed on the shape and found the leak: the assist channel. A
persona vetoed on grief could be pulled into a grief-held decision by a
declared preference for a female voice, because the assist did not pass the
gate the seat passed.

## Decision

**Seat is who speaks; hold is what must be carried by whoever speaks.** The
tree, top to bottom:

1. Acute danger → the crisis card. The router never sees it.
2. Seat-claiming domains → the named expert. A return to use
   (`SEAT_CLAIM_TERMS`: "I relapsed", "used again", a bare "relapsed again
   last night") claims the recovery persona whatever else is in the message;
   somatic distress claims the stabilizer. Everyone who does not carry the
   claim is set aside as `outranked` — the trace says they did nothing
   wrong. A relative's return to use ("my sibling relapsed", "a parent
   relapsed") is a hold, not a seat-claim, since the amendment of 10
   September 2026 (ADR-0027): the bare report still seats the recovery
   persona as the hold's specialist; an ask seats the ask with the recovery
   hold carried and the recovery persona offered as a companion. Whose it is
   travels on the decision as `claim_subject` (`self` or `other`, from the
   subject in front of the term), and a relative's relapse carries the
   family-impact obligations (`affected_person:other`,
   `acknowledge:addiction_recovery`, `no_joke`). (Before the amendment this
   clause read that a relative's return to use also claimed the seat, by the
   operator's standing rule that anything recovery-related leans to the
   recovery persona; the decision that reversed it is D3 in the dissent log.)
   Recovery status alone ("ten years clean") is a hold, not a claim.
3. Hold domains → obligations on whatever seat wins. Grief, abuse, eating
   distress and recovery carry `held` and `obligations` on the decision
   (`acknowledge:<domain>`, `no_joke`, `no_challenge`, `no_numbers`,
   `offer_companion:<id>`, `offer_human_help`), and veto humor and challenge
   for the turn. A persona contraindicated on a held domain cannot sit,
   assist or shadow, however well it fits the rest.
4. Ask fit → the score, taken on the *ask* (the request minus the held
   domains) so the held domain is carried, not seated. When the request is
   nothing but the held domain, the held domain is the ask and its specialist
   sits. An agent that carries the hold as well as the ask gets a small,
   named bonus (`HOLD_CARRY_BONUS`, more than a precision decimal and less
   than a domain of the ask), because one voice is better than a handoff.
5. Dysregulation → the stabilizer is preferred and challenge is penalized
   (ADR-0012 unchanged).
6. Declared affinities → tie-breaks and the advisory assist. Declared by the
   person at the operator level, never inferred from text; they rank among
   already-eligible candidates and never rehabilitate a vetoed persona.
7. Shadow seat recorded; assist emitted with a reason that names every
   candidate the affinity reached and why each was excluded.

**One gate.** `eligible(profile, signals, holds, claims, mode_vetoes)` is the
only function that says no, and seat, shadow and assist all call it. Its
answers are named: `vetoed` (a contraindication on the request as spoken or
on a held domain), `below_floor`, `capped` (every mode the agent offers is
vetoed this turn), `outranked`. No assist while the caller is acutely
dysregulated or under a somatic claim: one voice speaks.

**Contraindications are read against the request as spoken.** A mode the
turn vetoes for everyone still counts against an agent contraindicated on
it: "my grandmother died and I want someone to make it funny" does not seat
the grief companion who is contraindicated on humor, because the ask was
made and the seat has to hold it without honoring it. The alternative —
exempting vetoed modes — was built and measured in round 2 and rejected: it
seated the grief specialist on that request and produced id-order ties on
every capped turn (dissent log, 2026-09-03).

**Ties and empties are policy** (ADR-0011, amended): under a hold, a tie
breaks first on who carries the ask, then on who also carries the hold; a
request whose only modes are vetoed this turn, a mode with no topic, and a
topic nobody eligible carries all seat the stabilizer by role, with the rule
in the reason.

## Consequences

The recovery persona is seated on every first-person return to use, and on a
relative's bare report, and never on the build that "relapsed" or the planner
the person is "using"; a relative's return to use with an ask beside it seats
the ask with the recovery hold carried (ADR-0027, 2026-09-10). The grief companion reaches a grief-held decision as an
obligation to offer, not by displacing the ask. The strategist cannot be
seated or assist on a grief-held turn however well she fits the deck. On a
relative's relapse the reviewers split three ways — a hold instead of a
claim (Grok, Vibe), the persona ineligible (Qwen), the seat (ChatGPT,
DeepSeek) — and the operator's rule decided it for the seat on 3 September
and for the hold on 8 September (D3, decided with dissent; built by
ADR-0027); the losing positions of each day are kept as strict expected
failures with the reasons in the dissent log.
Between two eligible grief carriers the router prefers the more focused
one; that choice is a gold-label disagreement, and fixtures that pinned one
of them accept either, with the original kept.

## Relationship to the current implementation

Built in `router.py` (`seat_claims`, `claim_subject`, `holds_for`,
`eligible`, `score_agent`, `_select`, `_obligations`, `_assist`) and
`signals.py` (`claim_person`, `THIRD_PERSON_SUBJECTS`, the `abuse` and
`eating_distress` domains). Holds are
recorded and enforced at the policy layer (vetoes, obligations, mode vetoes);
the obligations themselves are checked by a harness that does not yet exist
(ADR-0014). The roster carries no `abuse` specialist; that hold seats the
stabilizer with `offer_human_help` attached.
