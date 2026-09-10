# ADR-0027: A relative's return to use is a hold, not a seat-claim

- **Status:** Proposed — built; the operator's ruling of 2026-09-08 (D3, decided with dissent), built 2026-09-10 with its fixtures; under the standing rule a record prepared by the project's own assistant becomes canon only after a second model family has read it (review round 3)
- **Date:** 2026-09-10
- **Evidence:** `tests/test_holds.py::test_a_relatives_bare_report_seats_the_recovery_persona_as_the_holds_specialist`, `tests/test_holds.py::test_a_relatives_relapse_with_an_ask_seats_the_ask_and_offers_the_recovery_persona`; the D3 fixtures under `evals/cases/` (`grok-seat-004` and `grok-r2-hold-relapse-ask-001`, which now pass; `gpt-d3-third-person` and `qwn-d3-thirdperson-relapse-001`, which stay as the recorded dissents); the both-ways measurement of 3 September and the decision of 8 September in `docs/notes/dissent-log.md`, entry D3
- **Amends:** ADR-0016 (layer 2 of the tree: the relative's clause)

## Context

ADR-0016 seats a return to use, the caller's or a relative's, on the recovery
persona, by the operator's standing rule that anything recovery-related leans
to that persona. Five reviewing families split three ways on the relative's
case in round 1 (a hold: Grok, Vibe; the persona ineligible: Qwen; the seat:
ChatGPT, DeepSeek), and the operator's rule decided it, with the two losing
positions kept as strict expected failures.

On 8 September the operator asked for a second look and took it: the person
asking is the person to help; a relative's relapse is that person's
situation, not their seat-claim; and the recovery persona's knowledge must
be in the room either way. He ruled that the bare report keeps seating the
recovery persona, as the hold's specialist, and that an ask seats the ask
with the recovery hold carried and the recovery persona offered as a
companion in every such reply. The tree kept the old rule until this push;
review round 2 named that gap in three places (ADR-0016 stating the old rule
as law with no pointer, ADR-0025 saying "is built", the dissent log stating
the new rule in the present tense) and asked that a reader never again find
three instructions for one hard turn.

## Decision

A return to use whose subject is a third person (`he`, `my dad`, `a
parent`, `my sponsee`, the subjects listed in `signals.py`) does not claim
the seat. It is carried as a hold on `addiction_recovery`, with the hold's
obligations (acknowledge, no joke, offer the recovery persona as a companion
when it is not seated) and the family-impact obligations the seat-claim
carried before (`affected_person:other`, `acknowledge:addiction_recovery`,
`no_joke`). The record still says whose relapse it is: `claim_subject` is
`other` for the hold as it was for the claim, and `seat_claim` is empty.

Two consequences follow without a rule of their own. A bare report with no
other ask in the message still seats the recovery persona, because it is
the only carrier of the held domain and the router prefers the carrier of a
hold when nothing else is asked. An ask seats the ask: a calm conversation
to plan seats the bridge-builder, a mural that will not start seats the
creative companion, and in both the recovery persona is offered on the
record (`offer_companion:cody`).

The lexicon learns that a conversation to be planned with someone is
conflict work ("plan a calm conversation", "how to bring it up with",
"without shaming"), which is the one place the both-ways measurement of 3
September found the two rules differing for the wrong reason.

The first-person case is untouched: "I relapsed" claims the seat exactly as
ADR-0016 says, and a person in their own return to use always reaches the
recovery persona first.

## Dissent kept

ChatGPT's and DeepSeek's round-1 position, that the recovery specialist
should take the seat even when the ask resembles mediation, is now the
losing side, and ChatGPT's fixture `gpt-d3-third-person` runs as a strict
expected failure with the decision's reasons in its dispute note. Qwen's
position, that the recovery persona should be ineligible on a relative's
relapse, is still declined: the bare report seats it, because keeping the
one persona built for the conversation out of it is the worse failure.
Grok's and Vibe's fixtures, which asked for the hold, now pass and are
marked resolved with their history kept. Sonar's request in round 2 that the
old behaviour be pinned as the expectation was declined: the known-gap
marker pinned the tree until this change landed, which is what markers are
for.

## Consequences

ADR-0016 is amended, not superseded: layer 2 of the tree reads "a
first-person return to use claims the seat; a relative's is a hold" and
the consequences paragraph changes to match; the register lists the
amendment both ways. ADR-0025's context paragraph, which said the second
half "is built ... in the block after push 2", is corrected to say it is
built here. The dissent log's D3 entry moves from decided-with-dissent to
built, with the fixture attribution corrected as review round 2 asked.

## Test that would falsify this ADR

A relative's return to use claims the seat; a bare relative's report seats
anyone but the recovery persona; an ask about a relative's relapse seats
the ask without the recovery hold or without the recovery persona offered;
a first-person return to use fails to claim the seat; `claim_subject` stops
saying whose relapse it is.
