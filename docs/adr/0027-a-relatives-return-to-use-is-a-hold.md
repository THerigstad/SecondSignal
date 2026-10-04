# ADR-0027: A relative's return to use is a hold, not a seat-claim

- **Status:** Proposed — built; the operator's ruling of 2026-09-08 (D3, decided with dissent), built 2026-09-10 with its fixtures; under the standing rule a record prepared by the project's own assistant becomes canon only after a second model family has read it (review round 3)
- **Date:** 2026-09-10; decisions 6 and 7 ruled 2026-09-28
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

ChatGPT's and DeepSeek's round-1 position seats the recovery specialist even
when the ask resembles mediation. The implemented tree seats the ask with
Cody attached, so `gpt-d3-third-person` runs as a strict expected failure.
Decision 6 now explicitly accepts either answer and retains this fixture as
an honest dispute, not a verdict that the reviewer is wrong. Qwen's
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

## Decision 6, 28 September 2026: Cody is present on every relapse

The operator's rule: "anytime there's a relapse, it should have Cody as a sidekick, if not seat him." On each recognized, non-emergency addiction-relapse
message Cody is seated or attached on the decision record as
`offer_companion:cody`. The crisis card comes first and nobody takes a seat.
The invariant runs over every addiction-relapse message in the test set;
unknown recovery phrasing is separately retained as known gaps under decision 7.

`gpt-d3-third-person` stays disputed: the operator accepts Cody seated or Rowan
seated with Cody as sidekick. His words: "it should have clearly gone to Rowan, with Cody as a sidekick -- or Cody. Period. Full stop." This is an honest
disagreement between two defensible answers, not a changed reviewer oracle.
`qwn-d3-thirdperson-relapse-001` also stays disputed: its round-1 expectation
keeps Cody out and violates this rule. Qwen later changed its own position,
writing that keeping Cody out "leaves the user without specialized support,
which is a worse failure than seating them."

The disagreement history stays as data: Qwen changed from neither to both
fixtures disputed, Gemini Flash from gpt-d3 only to both, and Gemini Pro from
both to neither. GLM via Perplexity's alternative was to resolve qwn-d3 against
the reviewer with the dispute note retained; it was declined so the reviewer's
fixture remains unchanged and guarded as a strict expected failure. Gemini
Pro's neither-disputed position was also declined: the label preserves the
opposing expectation as data, not a majority vote. See the dissent log.

Related reviewer findings remain: Qwen's F run warned a bare-report relative
sent to the specialist "might alienate a non-addicted spouse or child";
Gemini Flash's `settle-d3-family-relapse-priority-001` concerns a 17-year-old
son's fentanyl relapse with a list-making ask and expects Cody instead of
Seren; Kimi via Perplexity run 1's `twins-sponsor-case-001` is a known gap.
Their absent original fixture text is not invented.

The 28 September baseline observation was Rowan plus `offer_companion:cody`
for the sibling/calm-conversation case, and Cody for the dad and first-person
bare reports. A generation harness now exists, but this obligation is still
not an implemented, verified sidekick experience. Whether the sidekick is an
offer to the person or an assist behind the seated voice belongs to decision
11. This push preserves the policy obligation without claiming that future
interaction is delivered.

## Decision 7, 28 September 2026: whose relapse, and what counts as an ask

A self mention anywhere, including first-person plural, makes a relapse the
person's own: "I relapsed", "we both relapsed", "and so did I". A named other
subject, whether a pronoun, relationship or name ("she", "my dad", "Jake"),
keeps it theirs unless the message also includes the person in the relapse.
When no subject is named ("relapsed again, feel awful"), it is the person's
own. Anything else unclear fails toward someone else's (the hold), never the
first-person claim. Cody is present either way under decision 6; a worried
family member must not be treated as the one who relapsed. The two diagnosed
misreads, "my dad relapsed last night and so did I" and "Jake relapsed again",
are regression tests, with the English word lists and subject logic approved
by the operator's A2 ruling.

A bare report means the person tells us about the relapse without requesting
help on another task or domain. It seats Cody as the recovery hold's specialist.
An ask means the person requests something to do, such as planning a calm
conversation: the ask can take the seat while recovery is held and Cody is
attached as companion. Expressing worry alone does not erase that hold, and
nobody's sentence automatically excludes Cody. Safety preempts both paths.

The required reviewer fixtures are Kimi via Perplexity run 1's
`d3-ambiguous-subject-001` and `d3-first-person-control-001`, run 2's
`r3-0027-mixed-subject-001`, and Vibe's `glm-d3-mixed-subject-001`. The ruling
provides exact message text for the first two and Vibe's; a ruling-sourced
projection is distinct from a port of absent reviewer JSON. The run-2 mixed
fixture and sponsor fixture require their original sources before a verbatim
port can be claimed.

Six supplied recovery-community phrasings run as strict expected failures,
not fixes: "I went back out last night", "I picked up again after 90 days",
"I had a slip this weekend", "I have to reset my date", "back to day one again",
and "my qualifier went back out and I'm a mess". They are the ruling-sourced
fixtures in `evals/cases/round3_rulings_2026-09-28.json` (ported by Codex on
30 September 2026, moved into the public case tree on 4 October 2026), run by
`tests/test_eval_cases.py` under the manifest's field-scoped strict failure rule:
each may fail on agent and outcome only, and fails the suite if it starts passing
before its marker is reviewed.
The seventh required gap, the original sponsor line in `twins-sponsor-case-001`,
is not runnable until its missing text is supplied; no sponsor line or passing
result is invented. Existing successful controls include "I drank again last night"
and "I lost my sobriety date". See `docs/known-limitations.md` for the distinction
between the unchanged public case-manifest breakdown and these six new gaps.

Qwen's second, independent subject detector is queued for later. The operator
will dictate relapse, wobble and family-side phrases; Claude runs each through
the code. Each miss becomes a fixture and an operator-approved word-list fix,
with innocent-meaning controls such as picking up the kids. This push does not
broaden the lexicon to close those seven gaps. Recovery programs' ideas may be
used, never their text or names, and SecondSignal must never imply program
endorsement. Recovery has many roads: medication such as buprenorphine or
methadone, SMART Recovery and harm reduction are included without judgment.
No decision-7 reviewer dissent was recorded.
