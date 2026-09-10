# ADR-0025: The assist from the hold, and an affinity that can trade seats

- **Status:** Proposed — none; the operator's design intent, recorded 2026-09-08 with its target case and its gate; not adopted, not built, and not to be built before a generation layer exists. Amended 2026-09-10 by ADR-0026: proposal 2 (the affinity that can trade seats) is withdrawn; proposal 1 (the assist from the hold) stands, with the five gate predicates review round 2 asked for stated in the record the same day
- **Date:** 2026-09-08
- **Evidence:** the dissent log entry D3 (`docs/notes/dissent-log.md`), decided-with-dissent on 2026-09-08; the round-1 assist-leak fixtures under `evals/cases/round1_2026-09-02/`; the both-ways measurement of 3 September recorded in the same log; the operator's standing rule that anything recovery-related leans to the recovery persona (ADR-0016)
- **Depends on:** ADR-0016 (seat versus hold; the assist passes the same gate as the seat)
- **Would amend, if Accepted:** ADR-0016 (the assist's source; the seat-claim change that proposal 2 would have made is withdrawn)
- **Amended by:** ADR-0026 (twins: two presentations, one routing contract), 2026-09-10

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
seats the recovery persona by the seat-claim rule, and an affinity is a
tie-break and an assist source, never a seat-claim.

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
amendment and its fixtures. The assist intent was filed here so it keeps a name and a test instead
of living in a chat.

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

1. **The assist from the hold.** When a hold is carried and its specialist
   is not seated, the specialist's protocol may be emitted as an assist to
   the seated persona: the recovery persona's protocol beside a strategist
   who is planning a calm conversation, for example. The assist passes the
   same gate as the seat (ADR-0016); a hold-source assist is subordinate to
   the seat and never becomes the speaker.
2. **An affinity that can trade seats, first person only** (withdrawn 2026-09-10; see the amendment note above). When the person
   carries a first-person seat-claim and a declared affinity names a
   different, eligible sibling, the affinity may take the seat with the
   claimed specialist's protocol carried as an assist, so the person hears
   the protocol in the voice they asked for. The claimed specialist stays
   offered as a companion (`offer_companion`) on every such reply. Third-
   person claims never trade; a relative's recovery is a hold the seat
   carries, not a preference the person can route around.

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
conversation with the recovery protocol beside it.

## Gate

This record is built only when all of the following hold:

- A generation layer exists that consumes the assist field, so the change
  has visible behaviour to measure.
- The round-1 assist-leak fixtures stay green under the new source: no
  persona vetoed on a hold can arrive by the assist channel, from an
  affinity or from a hold (Grok's round-2 fixture `r2-0025-hold-assist-leak-001`
  pins the hold as a source; it runs today against the affinity source).
- A labeled set of first-person recovery messages with declared affinities,
  labeled by two people before any code, fixes the expected seat and assist
  for each. The precondition this sentence hides is stated (GLM, round 2):
  the second labeller does not exist yet; the single-operator limitation in
  `docs/known-limitations.md` names it, and no label written by one hand
  satisfies this gate.
- The both-ways measurement is repeated: every D3 sentence in the dissent
  log is run before and after, and any change in seat, hold or obligations
  is listed in the record before the flip to Accepted.

### The five predicates the gate checks (added 2026-09-10)

Review round 2 found the gate strong on the leak it was written for and
thin on the door it opens, and named the missing predicate five ways (Grok
5.6, DeepSeek, Kimi 5.2, Nemotron disagreement 4, ChatGPT 4.g). Stated
here so the day the assist is built the test is already written:

1. **Eligibility against the claimed domain.** The persona that carries a
   hold-source assist, and the persona it is emitted beside, each pass
   `eligible()` against the held domain and every other hold on the turn,
   not only against the residual ask.
2. **Content provenance.** The gate checks what the assist field carries,
   not only which channel it arrived by: a versioned protocol with exact
   bindings to the specialist's profile, never free text, so a
   humour-capable sibling never carries a recovery protocol it was not
   vetted for (GLM).
3. **Subject classification.** A third-person claim ("my sister") never
   enters this path; `claim_subject` is checked before any assist is
   considered, so a misclassified subject cannot route a relative's case
   into a first-person rule (Kimi).
4. **Every source, every hold.** The assist-leak fixtures run for every
   source (affinity, hold) and for turns with more than one hold; a persona
   vetoed on any one of them may not arrive by any channel (ChatGPT's
   release list).
5. **One visible speaker, no narrator in any channel.** The seated persona
   is the only speaker; the assist is never spoken as a second voice; no
   security narrator can appear in the assist field; and after review, a
   mutation of any of the five is a red test (ChatGPT).

Kimi's second predicate, that an unconfirmed affinity is enough for a
tie-break and never for a seat, no longer applies to this record: the seat
trade is withdrawn, and under ADR-0026 a voice choice is a presentation
under ADR-0017's confirmed-or-declared rule, never a seat.

## Consequences if Accepted

ADR-0016 is amended, not superseded: the assist gains the hold as a second
source. (Before the amendment of 2026-09-10 this paragraph also gave the
seat-claim rule a first-person trade; that consequence is withdrawn with
proposal 2.) The
dissent-log entry D3 is re-opened for the sentences whose seat changes. The
README says what the assist can do only after the generation layer shows it.

## Relationship to the current implementation

Not built, and not adopted. `router.py`'s `_assist` takes declared
affinities only, and its docstring says so ("Nothing is inferred: no
affinity, no assist"). The `offer_companion` obligation, emitted when a
hold's specialist is not the seat, is the only door to a specialist's voice
the tree has today.

## Test that would falsify this ADR

A hold-source assist is emitted with no generation layer to consume it; a
persona vetoed on a hold arrives by the assist channel from either source; a
third-person claim trades seats; a trade changes a hold, a cap or the card.
