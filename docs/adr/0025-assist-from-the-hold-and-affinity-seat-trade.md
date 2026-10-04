# ADR-0025: The assist from the hold, and an affinity that can trade seats

- **Status:** Proposed — none; the operator's design intent, recorded 2026-09-08 with its target case and its gate; not adopted, not built, and not to be built before a generation layer exists. Amended 2026-09-10 by ADR-0026: proposal 2 (the affinity that can trade seats) is withdrawn; proposal 1 (the assist from the hold) stands, with the five gate predicates review round 2 asked for stated in the record the same day. Amended in place 2026-10-04 under ruling 10 of 3 October 2026 (review round 3, decision 11): proposal 2 carries the marker WITHDRAWN, do not build, where it stands; the operative rule sits above the history; the gate's predicates are rewritten in the reruns' words and three are added; the gate cannot be checked today, the second labeller does not exist, and acceptance is void until a generation layer exists
- **Date:** 2026-09-08; amended 2026-09-10 and 2026-10-04
- **Evidence:** the dissent log entry D3 (`docs/notes/dissent-log.md`), decided-with-dissent on 2026-09-08; the round-1 assist-leak fixtures under `evals/cases/round1_2026-09-02/`; the both-ways measurement of 3 September recorded in the same log; the operator's standing rule that anything recovery-related leans to the recovery persona (ADR-0016); review round 3's reading of this record (every family that read item 4h, first pass and reruns, 26 to 28 September 2026) and the operator's ruling 10 of 3 October 2026
- **Depends on:** ADR-0016 (seat versus hold; the assist passes the same gate as the seat)
- **Would amend, if Accepted:** ADR-0016 (the assist's source; the seat-claim change that proposal 2 would have made is withdrawn)
- **Amended by:** ADR-0026 (twins: two presentations, one routing contract), 2026-09-10

## The operative rule

**No affinity or presentation preference trades the seat. Only the proposed,
separately gated hold-source advisory protocol remains.** (ChatGPT's words,
review round 3, adopted by ruling 10 of 3 October 2026.)

Everything under the Proposal heading below is history and a gate. Proposal 2,
the affinity that can trade seats, is **WITHDRAWN, do not build**; it is kept
in place, with its mechanics, because the operator wants the record of the idea
and the reasons it was set aside ("I like having the data, and record of the
idea"), and because a reader should be able to see what was proposed. Nothing
is built from it. Proposal 1, the assist from the hold, is proposed and unbuilt,
and is built only when every predicate of the gate below holds; today the gate
cannot be checked, because the generation layer that would consume the assist
does not exist, the labelled set it needs has no second labeller, and the
fixtures predicate 4 names are not written. Acceptance of this record is void
until a generation layer exists (GLM via Perplexity, round 3: with no
generation layer, acceptance "reinstates exactly what the operator refused —
untestable policy"; that condition is, in substance, the record's own gate).

Review round 3 split on whether a withdrawn proposal left inside a live record
is a safeguard or a hazard. A safeguard, on conditions: ChatGPT (the notice is
the safeguard; the hazard is the operative remnants), both Kimi via Perplexity
runs (run 2: it needs a machine-visible WITHDRAWN marker the register test
recognises), Vibe, Qwen ("a tombstone"), Gemini Pro ("Keeping it explains why
the seat-trade was rejected"), GLM via Perplexity. A hazard: Grok (proposal 2
"still sits in the numbered list with its full mechanics", and "A reader who
builds from the list builds the trade"), Gemini Flash, and Nemotron, which
reversed its first answer ("Keeping both in one record blurs which is live").
Both: Kimi K3 High and DeepSeek. The convergent remedy is this section and the
marker below. The marker the register can see: this record's row in
`docs/adr/index.json` carries WITHDRAWN for proposal 2 in its notes, the
README's generated register block renders that row, so the marker is published
on the front page and a row edited without re-rendering fails
`tests/test_adr_index.py`; the status line above carries the same word. The
register's decision and implementation vocabularies are frozen by that test
(Proposed, Accepted, Superseded; not-code, none, partial, reference-unwired,
built) and were not widened for a half-record: a record with a withdrawn
proposal inside it is still a Proposed, unbuilt record, and the marker lives
in the notes the register renders rather than in a new status word.

## Context

ADR-0016 seats the ask and carries the hold. The advisory assist comes from
declared affinities only, passes the same eligibility gate as the seat, and
is never the seated agent; nothing is inferred, and no affinity means no
assist. That closed the round-1 leak, in which a persona vetoed on grief was
pulled into a grief-held decision by a declared preference for a female
voice.

The operator's intent since 2 September has been one step further: a person
should be able to have the recovery persona's knowledge in the room while a
different sibling speaks, and in particular a woman in her own recovery who
prefers a female voice should be able to hear the recovery protocol in a
female voice. Today that case cannot happen. A first-person recovery claim
seats the recovery persona by the seat-claim rule, and an affinity is an
assist source, never a seat-claim and never a tie-break (ruling 8 of
3 October 2026 corrected the records on the tie-break).

On 8 September the question was whether to amend ADR-0016 now so the assist
could also come from the hold. The operator asked what the objection was and
accepted it: an amendment now would reopen the assist leak for a field
nothing consumes, because no generation layer exists and every affected
sentence's visible behaviour would be identical before and after; it would
not deliver the first-person case, because the recovery claim still seats
the recovery persona and an affinity cannot take a seat-claim; and it would
add a record field, a fixture family and a review target for no visible
change. D3 was therefore decided on the seat question alone: the bare
report seats the recovery persona; an ask seats the ask, with the recovery
hold carried and the recovery persona offered as a companion. That second
half is a change to ADR-0016's third-person claim (the tree seated the
recovery persona on every relative sentence until 2026-09-10, measured
2026-09-08) and was built on 2026-09-10 as ADR-0027, with ADR-0016's
amendment and its fixtures. The assist intent was filed here so it keeps a
name and a test instead of living in a chat.

## Proposal

> **Amendment of 2026-09-10.** Proposal 2 below is withdrawn in favour of
> [ADR-0026](0026-twins-two-presentations-one-routing-contract.md), which
> meets the target case without moving the seat: every persona gains two
> presentations with one routing contract, so the recovery protocol is heard
> in the voice the person asked for while the recovery persona keeps its
> seat. Review round 2's objection to the principle of a trade (preference
> outranking domain safety) is answered by that construction. Proposal 1
> stands as written, with the gate below. The withdrawn text is kept so the
> record shows what was proposed and why it was set aside.

Two changes, originally taken together, when a generation layer exists to consume them:

1. **The assist from the hold** (proposed; unbuilt; gated below). When a hold
   is carried and its specialist is not seated, the specialist's protocol may
   be emitted as an assist to the seated persona: the recovery persona's
   protocol beside a strategist who is planning a calm conversation, for
   example. The assist passes the same gate as the seat (ADR-0016); a
   hold-source assist is subordinate to the seat and never becomes the
   speaker.
2. **WITHDRAWN 2026-09-10, do not build.** *An affinity that can trade seats,
   first person only.* Kept as history under the amendment note above and the
   operative rule; nothing is built from it, and a reader who builds from this
   list builds proposal 1 alone. As proposed: when the person carries a
   first-person seat-claim and a declared affinity names a different, eligible
   sibling, the affinity may take the seat with the claimed specialist's
   protocol carried as an assist, so the person hears the protocol in the
   voice they asked for. The claimed specialist stays offered as a companion
   (`offer_companion`) on every such reply. Third-person claims never trade;
   a relative's recovery is a hold the seat carries, not a preference the
   person can route around. Why it was set aside: review round 2's objection
   that once an affinity can outrank a seat claim, preference outranks domain
   safety (Gemini 3.8 Flash; dissent log R2-5), answered by construction in
   ADR-0026, where the specialist keeps the seat and only the presentation
   changes.

Neither change touches the crisis card, the latch, the caps or any hold. A
weapon or a person in danger is a crisis lane, not a seat, exactly as today.

## Target case

The first-person case, stated by the operator on 2 September and again on 8
September: a woman in her own recovery, with a declared preference for a
female voice, hears the recovery protocol in a female voice, with the
recovery persona offered beside it. Working name: SiblingAssist. Since
2026-09-10 the case is met by ADR-0026 (the recovery persona's own
presentation, not a sibling's seat); what remains of this record is the
assist from the hold, whose target case is the strategist planning a calm
conversation with the recovery protocol beside it, that is, a relative's
relapse with an ask beside it (ADR-0027: a hold, `claim_subject` other).

## Gate

This record is built only when all of the following hold:

- A generation layer exists that consumes the assist field, so the change
  has visible behaviour to measure. Until it does, acceptance is void: there
  is nothing to accept but untestable policy.
- The round-1 assist-leak fixtures stay green under the new source: no
  persona vetoed on a hold can arrive by the assist channel, from an
  affinity or from a hold (Grok's round-2 fixture `r2-0025-hold-assist-leak-001`
  pins the hold as a source; it runs today against the affinity source).
- A labeled set of first-person recovery messages with declared affinities,
  labeled by two people before any code, fixes the expected seat and assist
  for each. The precondition this sentence hides is stated (GLM, round 2;
  Vibe, Grok and ChatGPT, round 3): the second labeller does not exist; the
  single-operator limitation in `docs/known-limitations.md` names it, and no
  label written by one hand satisfies this gate. The gate's two-people
  precondition is therefore unsatisfiable today, and the record says so
  rather than letting the sentence imply otherwise.
- The both-ways measurement is repeated: every D3 sentence in the dissent
  log is run before and after, and any change in hold or obligations is
  listed in the record before the flip to Accepted. (No seat changes under
  proposal 1; a seat change would be the withdrawn proposal.)

### The predicates the gate checks (added 2026-09-10; rewritten and extended 2026-10-04)

Review round 2 found the gate strong on the leak it was written for and
thin on the door it opens, and named the missing predicate five ways (Grok
5.6, DeepSeek, Kimi 5.2, Nemotron disagreement 4, ChatGPT 4.g). Review round 3
read the five predicates as written and found that none of them could be
checked on the tree today; the reruns rewrote two of them and asked for three
more, which ruling 10 of 3 October 2026 adopted. Stated here so the day the
assist is built the test is already written:

0. **Predicate zero: a case the presentation design does not already cover.**
   ADR-0026 met the motivating case without an assist, so before anything is
   built from this record, the record must name a case ADR-0026 does not
   cover and show that the `offer_companion` obligation ADR-0016 already
   attaches does not cover it either. The case on record is the one in the
   target case above: a relative's relapse with an ask beside it, where the
   strategist is seated and the recovery protocol is wanted beside the plan.
   The day a generation layer exists, that case is run with the companion
   offer alone first; if the offer covers it, proposal 1 dies behind its
   gate. (GLM, round 3, who named the predicate; GLM's second run: "proposal
   1 should die behind its gate"; Kimi via Perplexity run 1, on what an
   ungated assist becomes otherwise: "an unasked sermon riding on a creative
   seat".)
1. **Not contraindicated on the held domain.** The persona that carries a
   hold-source assist, and the persona it is emitted beside, each is not
   contraindicated on the held domain and on every other hold on the turn,
   not only on the residual ask. The predicate says "is not contraindicated
   on the held domain", not "passes `eligible()` against it", because
   `eligible()` bundles scoring that a carrier legitimately fails (Qwen's
   rerun). The 10 September wording said the latter.
2. **Content provenance.** The gate checks what the assist field carries,
   not only which channel it arrived by: a versioned protocol with exact
   bindings to the specialist's profile, never free text, so a
   humour-capable sibling never carries a recovery protocol it was not
   vetted for (GLM, round 2). Round 3's finding stands beside it: no such
   protocol object exists in the repository (Qwen), the profiles are hashed
   precisely so a silent edit is visible and a protocol bound to an id would
   survive an edit that should void it (GLM via Perplexity), and the
   versioning chain would be signed by the single operator (Qwen). Nemotron:
   "This predicate is a paper gate." It stays as the requirement the
   generation layer must meet, and is unfirable until then.
3. **Subject classification, failing toward the hold.** `claim_subject` is
   read before any assist is considered. A relative's case ("my sister
   relapsed") is a hold the seat carries (ADR-0027), which is exactly the
   case this assist is for; a first-person claim seats the specialist and
   needs no assist. An unrecognised subject defaults to the hold, never to
   the first-person rule (GLM via Perplexity's rerun; ADR-0027's rule 4), so
   a misread subject can only add obligations and can never revive the
   seat-take ADR-0027 removed. (As written on 10 September this predicate
   excluded the surviving motivating case, because ADR-0027 classifies it
   `claim_subject` other: ChatGPT, "As written, reject this predicate"; Kimi
   K3 High, "stale or contradictory"; Kimi via Perplexity run 2 and Vibe on
   mixed subjects. Qwen's rerun adds that `claim_subject` comes from an
   unreviewed lexicon, so a real defence needs the second, independent
   subject detector ADR-0027 queues.)
4. **Every source, every hold.** The assist-leak fixtures run for every
   source (affinity, hold) and for turns with more than one hold; a persona
   vetoed on any one of them may not arrive by any channel (ChatGPT's
   release list). Those fixtures are not written; the predicate is a snapshot,
   not an invariant, until a third source added later (a handoff, a companion
   acceptance, a per-persona override) is covered too (Qwen's rerun), and the
   arbitration among competing holds is stated (Gemini Flash).
5. **One visible speaker, no narrator in any channel.** The seated persona
   is the only speaker; the assist is never spoken as a second voice; no
   security narrator can appear in the assist field; and after review, a
   mutation of any of these predicates is a red test (ChatGPT). This cannot
   be checked from a decision field (DeepSeek, Kimi K3 High, Vibe; Grok: "If
   it can be spoken, there are two voices"); it is checked on the rendered
   reply, where GLM via Perplexity placed the failure ("an assist rendered as
   a second block in the same reply is two voices in one message with the
   gate green"), and it must say how an accepted companion differs from a
   forbidden second voice (Qwen), which predicate 7 does.
6. **No assist while the person is acutely dysregulated or under a somatic
   claim.** ADR-0016's one-voice rule applies to a hold-source assist exactly
   as it applies to an affinity assist: one voice speaks, and the assist is
   suppressed while the stabilizer has the floor (Vibe; GLM). The rule
   already lives in `eligible()` for the affinity source; the hold source
   gets no exception.
7. **One owner per reply.** `offer_companion` and a hold-source assist are two
   channels with two audiences: the companion offer is a line the person
   hears and may take up; the assist is advice to the seated persona and is
   never heard. When both would fire on one turn, the seated persona owns the
   reply, the companion offer is carried on it as the obligation ADR-0016
   already attaches, and the assist may shape the seated persona's words but
   never adds a block, a second voice or a second offer. The specialist is
   never spoken for; it is offered. Accepting the offer is a request the
   router hears on the next turn like any other, under Part A's rule that
   nothing typed seats anyone by name. This is the rule Vibe, DeepSeek, Kimi
   via Perplexity run 2 and GLM's second run asked for; it is drawn from
   ADR-0016's contract (the companion is an obligation to offer; the assist is
   subordinate to the seat) and not from a new design choice, and the operator
   may rule otherwise before anything is built.

Kimi's round-2 predicate, that an unconfirmed affinity is enough for a
tie-break and never for a seat, no longer applies to this record: the seat
trade is withdrawn, and under ADR-0026 a voice choice is a presentation
under ADR-0017's confirmed-or-declared rule, never a seat; and since ruling 8
of 3 October 2026 the records no longer say an affinity breaks a tie, because
the code never did.

## Consequences if Accepted

ADR-0016 is amended, not superseded: the assist gains the hold as a second
source. (Before the amendment of 2026-09-10 this paragraph also gave the
seat-claim rule a first-person trade; that consequence is withdrawn with
proposal 2.) No seat changes under proposal 1, so the dissent-log entry D3 is
not re-opened by it; the both-ways measurement in the gate lists any change
in hold or obligations instead. (Until 4 October 2026 this paragraph said D3
"is re-opened for the sentences whose seat changes", which was proposal-2
text left standing; Kimi via Perplexity run 1 and ChatGPT found it.) The
README says what the assist can do only after the generation layer shows it.

## Dissent kept as data

Gemini Pro (review round 3, after a follow-up) attacked the gate from the
other side: too strict, and contradictory. Predicate 1 "creates an immediate
routing paradox", because a seated persona is either already eligible, so the
assist is redundant, or vetoed; predicate 3 is "an arbitrary restriction",
because a person in distress about a relative's crisis needs the specialist as
much as a person in their own; predicate 4 "guarantees a combinatorial
explosion of tests"; and predicate 5 contradicts predicate 2, because a single
speaker must either rewrite the protocol, breaking the exact bindings, or
append it, sounding "exactly like the narrator this predicate expressly
forbids". Recorded, not adopted (ruling 10 of 3 October 2026): the gate stays
as strict as the reviewers who found it thin left it, and predicates 1 and 3
are rewritten in the reruns' words rather than loosened. What would change it:
a generation layer on which the paradox can be shown, and a labelled set,
labelled by two people, in which the stricter gate withholds an assist a
person needed. The entry is also in `docs/notes/dissent-log.md` (R3-11).

## Relationship to the current implementation

Not built, and not adopted; proposal 2 is withdrawn. `router.py`'s `_assist`
takes declared affinities only, and its docstring says so ("Nothing is
inferred: no affinity, no assist"). The `offer_companion` obligation, emitted
when a hold's specialist is not the seat, is the only door to a specialist's
voice the tree has today, and it is an obligation on the decision record that
nothing renders or enforces until the generation layer and the harness read
it.

## Test that would falsify this ADR

A hold-source assist is emitted with no generation layer to consume it; a
persona vetoed on a hold arrives by the assist channel from either source; a
third-person claim trades seats; any affinity or presentation preference
trades a seat; a trade changes a hold, a cap or the card; an assist is spoken
as a second voice or appears beside a companion offer as a second owner of one
reply; an assist is emitted while the person is acutely dysregulated.
