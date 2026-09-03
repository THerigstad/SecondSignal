# ADR-0011: No-signal routing is a policy, not an accident

- **Status:** Accepted — built; amended 2026-09-03 (see the end of this record)
- **Date:** 2026-09-02
- **Evidence:** External red-team review (Grok 4.6, 2026-09-01), docs 02, 03, 07, 09, 17, 18; live-router measurement (11 of 25 fixtures extracted no topic; four "passes" were alphabetical accidents)

## Context

When the extractor found no topic and no mode, every agent scored the same
neutral value, the candidates were sorted by id, and Calder won because "c"
sorts first. Eleven of the review's twenty-five fixtures took that path. Six
of them failed for it — "a shop, a funnel, and a launch date" never reached
the strategist; "we're not speaking" never reached the rupture specialist —
and four *passed* for it: "chest is tight", "can't feel my feet", a forged
cousin ping, and "I need the floor" all landed on the right agent without the
router having detected anything. A test that asserts only the winner cannot
tell those apart.

The reviewer put the deeper point plainly: winning by sort key is not
grounding; it is a silent specialist on unknown state. And whoever greets
ambiguity most often becomes the default relationship, which is a product
decision about the family, not a property of Python's sort order.

## Decision

Three rules, all named in the trace.

**An empty extract is a first-class state.** `RequestSignals.is_empty` is
true when there is no topic, no mode and no regulation evidence either way.
Distress without a topic is not empty: the caller's state is a signal the
router acts on, preferring the stabilizer because there is no topic to weigh.

**Nobody is seated by alphabet.** On the first empty turn of a session the
outcome is `UNRESOLVED`: no agent is seated, the reason reads
"no routable signal; nobody seated; ask for one more sentence", and the
surface asks. From the second consecutive empty turn the **named seat**
receives the caller — `NO_SIGNAL_SEAT = "calder"` — with the trace reading
"stabilizer=calder by policy". The seat is one constant, reviewable and
reversible in one line, and it must name an agent that profile loading
certifies as a stabilizer (safe at full dysregulation, no contraindications).
When a held boundary or a required disclosure has to be delivered and there
is no topic to route on, the named seat delivers it.

The operator delegated the choice of seat with the instruction to take the
safest option. This is it: the house asks before any persona is seated, and
the persona that is seated is the only one in the roster that can never be
handed a request it vetoes. The reviewer's stated preference — do not
hard-code a seat while the crisis lexicon is unreviewed — is honored on the
first turn and overridden, deliberately, on the second, because asking twice
is a phone tree and a person who could not say what they needed is better met
by the steadiest voice than by a second form. The one seat this record argues
against is the warmest generalist: an empty turn plus the agent with the
strongest attachment surface is how "I'm always here" gets trained.

**Every decision names the rule that produced it.** `RoutingDecision.reason`
carries it: the specialist signal, the mode signal, the regulation window, a
tie broken by specialist precision, a tie broken by the wider safe window, or
— last resort, and named as such — id order. A labeled case may never
resolve by id order; the eval runner asserts it. Zero has three meanings and
the trace says which: a candidate is `vetoed`, `below_floor`, or `no_signal`,
never a bare 0.0 that looks like a score.

**Failures cannot hide in the seat.** A case that should have hit a topic
class and lands on the stabilizer instead is a lexicon failure, and the runner
reports it as one, because the case's expected reason is "specialist signal",
not "by policy".

**On a gated turn, the router still computes the seat it would have taken**
and records it as `shadow_agent_id`, never in `agent_id`. It costs nothing on
the reply path and produces, over time, a record of which persona is the
attractor when language is mixed — without anyone being seated.

## Consequences

The four accidental passes are now passes on merit: somatic distress is
detected and the stabilizer wins with the humor and challenge agents vetoed.
The six failures reach their specialists on merit. Two remaining fixtures are
handled honestly rather than forced: the gate's negative control ("I don't
feel anything about it") is `UNRESOLVED` because numbness has no topic in the
reference lexicon and the house asks; the funeral-plus-investor-deck case
accepts either Calder or Willow, because that gold is an operator's or a
clinician's call, while the invariant that matters — the strategist must lose
— is asserted.

## Relationship to the current implementation

Built. `router.py` carries `Outcome`, the reason on every decision, the named
tie-break chain, the candidate statuses, the no-signal policy with its single
constant, and the shadow seat. `tests/test_guards.py` pins each rule;
`tests/test_eval_cases.py` refuses winner-only cases and id-order resolutions.
A later "no route — ask the person" outcome as a first-class surface behavior
is `UNRESOLVED` already; what the surface says on it is product copy.

## Amendment, 2026-09-03 (round 2)

Three changes, all measured against the round-1 reviewer fixtures.

**The seat is a role, not a literal.** `NO_SIGNAL_SEAT = "calder"` is gone.
The router asks the loaded roster for the agent filling the `stabilizer`
role (`NO_SIGNAL_SEAT_ROLE`, resolved by `no_signal_seat(roster)`), and
profile loading guarantees the role is filled by an agent that is safe at
full dysregulation with no contraindications. No agent id is written into
`router.py`. The trace reads "stabilizer=<id> by role (ADR-0011)". A
different roster gets a different stabilizer without a code change, and the
policy is the same sentence.

**Three more empties seat the stabilizer, each named.** The reviewer
fixtures showed three ways a request can be empty *after* policy is applied
while the raw extract is not: every requested mode is vetoed this turn (a
roast asked for under a register cap), a mode is requested with no topic
("I keep doing the same pattern"), and a topic is present that no eligible
agent carries (eating distress and abuse in the shipped roster). Each of
those had been landing on whoever listed the fewest domains, or on id order.
Each now seats the stabilizer with the rule in the reason: "requested modes
vetoed this turn (...) and no topic; stabilizer preferred", "mode-only signal
(...); no topic to weigh; stabilizer preferred", "no eligible agent carries
the topic (...); stabilizer preferred".

**Fury is a state.** "I swear to God, if this app crashes one more time I
will lose my mind" carried no topic and no regulation evidence, so the house
asked for one more sentence. Work-fury markers now count as dysregulation
evidence in `signals.py`; the message proceeds through the crisis gate (no
stem) and routes to the stabilizer on the regulation-only rule instead of a
form. The crisis screen keeps its own frustration markers; these never touch
a verdict.

Under a hold (ADR-0016) the tie-break chain gains two named steps before
precision: the agent that carries the ask, then the agent that also carries
the held domain. `tests/test_holds.py` pins that no case in the suite and no
labeled fixture resolves by id order.
