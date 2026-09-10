# ADR-0022: Intake and provenance runs after the gate and before routing, and proposes but never grants

- **Status:** Proposed — none; drafted 2026-09-08 from the rulings on review round 1; read by eight model families in review round 2 (8 to 10 September 2026) and amended in place on 2026-09-10 with their findings and the operator's rulings (the revision history at the end); under the standing rule it stays Proposed until a further round has read the amended text, and the flip is the operator's act
- **Date:** 2026-09-08
- **Evidence:** the Security Division document v1.1 (`docs/notes/security-division-2026-09-08.md`, §4); review round 1 (Grok 2.1 and tests 5.2, 5.3; ChatGPT 2.2, 2.11 and tests 5.4, 5.5; GrokBot 4b); the 31 August audits that first split intake from authority (ChatGPT threat model §14; the Grok harvest's "deterministic-as-possible compiler"); what already exists in the tree without an owner (`INTEGRITY_PATTERNS` and `SESSION_WRITE_PATTERNS` in `src/secondsignal/safety.py`; `tests/test_guards.py`)
- **Depends on:** ADR-0014 (the gate runs first); ADR-0018 (one normalizer, before every lexicon); ADR-0002 (authority is source-anchored)
- **Amends:** ADR-0019 (carries the contract for its object two, which that record only names)

## Context

The Family Codex describes a cousin who checks where a message came from
before any persona speaks and who never talks to a user. The 31 August
audits gave that cousin a shape: an intake compiler that produces an
authority *request*, never authority. Grok's draft ADR-0019 placed intake
"before routing". The Security Division document of 7 September then wrote,
in one section, "before the gate scores anything", and review round 1 caught
the contradiction from three directions: three clocks and one crisis path,
so if intake is model-backed, schema-invalid or slow, the card is no longer
the first speaker (Grok 2.1); ADR-0019 never resolved its ordering against
ADR-0014, and an optional model step must not delay the deterministic crisis
response (ChatGPT 2.11); the triad story needs two clocks, not one (GrokBot
4b).

The operator asked for the opposing case to be argued before ruling. The
case for the gate first won on its own merits: anything in front of the
gate is a failure surface and could alter the gate's input; the gate needs
nothing intake produces (message text is never a key, amnesty is ruled no,
framing does not waive); and a data dependency must never become an
authority dependency. Gate-first is the accepted record with the tests
behind it and needs no amendment.

## Decision

**Order.** The gate (`safety.evaluate`) runs first, on the normalized bytes,
exactly as ADR-0014 and ADR-0018 say. Deterministic intake runs second,
before any routing. Model-backed intake, where it exists at all, runs beside
or after deterministic intake, with a timeout, and can only add a
disclosure. Nothing intake produces reaches the gate. If the gate fired,
the card is committed before intake is invoked; intake still runs so the
crisis turn's rows carry provenance, and it can neither delay nor rewrite
the card. "Never a delay" is not an untestable absolute: the card's path is
a declared non-blocking path, and where any budget is published for intake
it is published as a manifest field with no default, and intake never
holds a turn beyond it (round 2: Grok, "cannot touch is not cannot delay";
ChatGPT, Kimi, GLM, Nemotron, Sonar on the budget). A crisis turn whose
intake failed carries no provenance stamp; that is a legal record state,
recorded as such, and never a reason to withhold the card (Kimi 2.5).

**Read-only on the bytes.** Intake sees the normalized message, the session
record as the house holds it (which facts were operator-set, which were
user-confirmed, which are inferences with a state), the channel and the
timestamp. It never sees a persona, a prompt or the reply, and it never
changes what the gate saw or what the gate decided.

**The five questions it answers.**

1. *Channel.* Where did these bytes come from: a typed message, an operator
   console, a house-attached line, a retrieved or quoted document. Retrieved
   or quoted content never promotes itself to system authority. Proposed is
   not authorized; authorized is not executed; executed is not result.
2. *Origin of session facts.* For every fact the record carries: operator-
   set, user-confirmed, or inferred. A typed sentence that claims a fact
   ("the operator waived it", "reviewed: true", an age) is user text and is
   recorded as user text. Nothing typed becomes operator-set.
3. *Attempted writes.* Did the text try to write a session key or a policy
   bit from chat: an age claim shaped as a field, JSON-shaped fields, "save
   this: never show me the card", a typed `PingJR`, `PingORRIN` or
   `PingAYA`. Every attempt is refused and recorded, whatever noun it uses.
4. *Replay and re-entry.* Is this a message the house already adjudicated,
   returning unchanged or with an invisible character inserted. Re-entry is
   recorded as re-entry; the earlier decision is not re-litigated by
   repetition. (Reuse of the gate's own prior verdict is a separate question,
   ruled no on 2026-09-08; `docs/known-limitations.md` records it and the
   narrower form in which it may return.)
5. *The stamp.* The provenance stamp on the decision record: a source class
   for each fact, the channel, the timestamp, and the durable-state class of
   anything the turn wants to remember. Silent movement of a fact between
   state classes (an inference quietly becoming a declared fact) is a P0
   defect. The timestamp carries the session-boundary rule: elapsed time
   beyond the published threshold starts a new session, and the trusted
   session is assigned before the gate runs, so that one turn never has two
   contexts (the gate reading the old session's latch state while intake
   opens a fresh session for routing); a boundary that arrives late applies
   to the next turn, never to the one in flight (review round 2, ChatGPT
   4.b.1).

**Provenance labels are code-computed.** Round 2 (Grok's two-turn sequence;
ChatGPT, GLM, Nemotron, DeepSeek in the language of provenance) showed the
hole in a schema-valid envelope: intake did not change turn one, it changed
turn two, by storing a declared adult band that a typed "I am 34" had
proposed and a later gate read as a prior. So the fields that carry
authority (source class, durable-state class, the operator-set marker) are
computed by house code from host facts and can never be set by a proposer;
every field has a write permission; the validator compares
authority-bearing fields to the host's facts rather than to the envelope's
claims; and a mislabel is recorded as evidence of an attempted write, never
corrected silently. Schema validity does not authenticate origin.

**Pinned before intake runs.** Read-only by convention on a shared mutable
object is not read-only (ChatGPT, DeepSeek, Nemotron): the input digest, the
normalizer version, the gate's result and the session snapshot are pinned
before intake is invoked, and intake's rows reference the pinned digest.

**Typed authority.** Intake proposes what the record should say about where
each fact came from; the gate and the router decide what happens. Intake
never grants authority, seats anyone, speaks, attaches a crisis line,
interprets grief or affect, judges whether the person is safe, or promotes
its own policy. Its outputs feed the house's write decisions and the router,
never the gate. A mistake in intake must be correctable before it becomes
executable, which is why intake writes a private buffer that the public
record is built from, never the public record itself.

**What it writes.** Intake rows and the provenance stamp. Nothing else: not
memory, not preferences, not the latch, not a profile, not a rule. Every
intake row carries a machine reason code at the point of creation, so
nobody parses prose to derive one.

**Failure rule** (revised 2026-09-10 on the operator's ruling after review
round 2; the original clause is kept under Revision history). If
deterministic intake raises, returns an invalid envelope, returns a valid
envelope with empty rows, times out, or labels the channel unknown *after*
the gate said proceed, the house retries intake once, automatically, and
only for a transient failure class (a timeout, a transient transport error;
the taxonomy is the one filed in
`docs/notes/stall-and-recovery-proposal-2026-09-10.md`). If the retry fails,
or the failure is not transient, the persona the gate allowed is seated and
speaks; every write for the turn is blocked, so no memory, no preference and
no durable state is written from a turn whose provenance is unknown; the
failure is logged with its class; and the person sees the house's failure
line, "This message ran into a problem. Press here to try again.", never a
line that names a mechanism. Every hold, cap and latch stands exactly as it
would have; the resource line stays reachable; the line claims no check that
did not happen. If the gate fired, the card is committed before intake is
invoked, and intake's state can neither delay nor rewrite it. This is a
house act, written as one: intake stays voiceless and unseats nobody; the
house seats, blocks the writes, and speaks the line.

The rule it replaced, fail closed on the seat, is kept as the recorded
dissent with its control fixture (`rr2-intake-failure-withholds-seat`). The
settling test, proposed by the family that held the dissent: disable intake
and run the whole suite; if the suite stays green, intake was never
load-bearing for safety, and failing the seat on its loss protects nothing
while costing the person the companion and every hold obligation. That test
runs the day intake exists.

**The backend clause.** The signal extractor's second backend (the
`RequestSignals` contract) is an intake backend. Its result composes with
the lexicon by one published matrix, every cell filled:

| Lexicon | Backend | Result |
|---|---|---|
| hit | hit | escalate; a forged waiver in the backend's proposal changes nothing |
| hit | miss | escalate (the floor holds) |
| miss | hit | disclose this turn; record the disagreement; never a sole escalation, a persistent latch or an operator fact |
| miss | miss | proceed, which means no signal detected, not a verdict of safety; existing latches still apply |
| inconclusive | any | the gate's inconclusive read escalates (ADR-0010) and no backend result collapses it into a miss |
| any | backend timeout | counts as a miss; logged with its own code; never a delay |
| any | backend unavailable | counts as a miss; logged with its own code |
| any | malformed envelope | counts as a miss; logged; an escalation-shaped payload in a malformed envelope is logged, never acted on |
| any | deterministic intake failure | the failure rule above, with its own code, separate from a backend failure |
| any | optional proposal failure | logged; never inherits the failure rule's fallback |
| any | late result | discarded for the turn it missed; recorded; never applied to a later turn |

The six error cells are ChatGPT's (round 2, 4.b.7 and 4.b.10, with the
separate codes for backend failure and deterministic-intake failure); the
inconclusive row is ChatGPT's 4.b.8 (the matrix was binary while the gate is
not; fixture `r2-matrix-inconclusive-preserved-001`); Gemini and GLM noted
that an attacker who can crash the backend converts a model-detected
escalation into a proceed, which is why the backend never carries the
escalation alone.

**The miss/hit cell, ruled 2026-09-10 (Thing 3).** Disclose until reviewed,
with three constraints the round wrote: the disclosure names no danger, no
age and no safety (Grok's fixture: a backend hit on "I had a drink with
dinner" produces a line that mentions none of them and seats whoever would
have been seated); a per-session repeat limit, so a flaky backend cannot
put a disclosure on every turn and train the person to ignore disclosures
(Kimi 2.4, GLM); and "hit" is defined, because the gate's integrity hits
produce a hold and a disclosure, not a card (ChatGPT 2.7): a backend hit is
a crisis-class claim and nothing else. The dissent (Gemini, Nemotron): a
backend that correctly flags acute lethal risk the lexicon missed should
escalate, not disclose. Kept with its sentence, Gemini's rope and the
letters and the motor running (`sec-intake-backend-disagree-failclosed-002`),
which proceeds today and is the first entry of the labelled set that
decides promotion; no rule about unreviewed models fixes a lexicon gap.

**The promotion cell.** A reviewed backend, on a lexicon miss, still only
discloses until the promotion bit is operator-set; then it escalates on the
same bytes (Grok). Promotion is a versioned policy change with revised gold
labels, never a backend flag (ChatGPT, Chat return).

A backend's self-reported confidence is evidence only and grants nothing.
An unreviewed backend can never escalate alone; promotion of a backend to
escalate on its own hit requires that backend's review.

**The integrity matrix, unspecified on purpose.** Session-write detection
lives in the gate's patterns and in intake's question three, and there is
no published rule for the cell gate-miss, intake-catch (Kimi 4.b, fixture
`pplx-r2-intake-001`, which the gate now catches on its own). The cell
stays unspecified until intake exists, is listed in
`docs/known-limitations.md`, and the ruling is owed the day it is built:
whether intake's catch attaches a hold, a disclosure, or only a row. Whatever family
runs the seated persona, the intake backend runs on a different one, and it
never shares a family with the ledger's interpretation engine in the same
turn (ADR-0014's independence rule, applied here).

**Where a model may enter.** Two places, both optional, both subordinate to
code: proposing a typed intake envelope that a schema validator accepts or
rejects (the validator decides), and as the backend above. Neither runs in
front of the gate. Neither can delay the card.

**Retention.** Intake rows are bounded: they hold source classes, channel,
timestamp, reason codes and the digest of the bytes, never the bytes of a
message the gate withheld. A privacy canary phrase in input must never reach
logs, traces, the session representation or exports; the canary fixture is
the cheapest test this record asks for.

**Already in the tree, unnamed.** `INTEGRITY_PATTERNS` treat override
attempts as a boundary hold plus disclosure; `SESSION_WRITE_PATTERNS` is
question three; `tests/test_guards.py` proves a forged ping is user text;
the bare-"the card" refusal of 6 September is this class. Those patterns
stay in the gate as candidate detectors: the gate keeps its floor, and
intake gathers the provenance of what the gate found rather than moving
detection out of it.

## Consequences

- The Security Division document §4.1 reads "after the gate, before
  routing" from v1.1 on; the 7 September wording is superseded.
- The deferred harness cases `ss-jr-001` and `ss-jr-002` (forged pings) are
  intake fixtures and move into this record's fixture set when it is built.
- The README names intake and provenance under what is not built, with its
  clock, until an implementation exists and this record is Accepted.
- Settling tests on record, to be written as fixtures when the function
  exists: force intake to raise, to return an invalid envelope, to time out
  and to label the channel unknown; a synthetic present-danger message still
  produces the house card with no persona speaking, and a synthetic ordinary
  message seats the persona the gate allowed with every write blocked and
  the failure line shown (Grok 5.2 as revised by the ruling of 10 September;
  the 8 September text said "seats nobody silently"). Review round 2's
  twelve composition fixtures are filed verbatim under
  `evals/cases/deferred/round2_orchestration_cases.json`; they move up one
  directory and gain the runner's expectations the day intake exists. The same bytes in two sessions,
  one with a prior hard latch, produce intake labels that differ only where
  they copy declared session facts (Grok 5.3). Ordering is observable: no
  ordinary seat is released before the gate's decision (ChatGPT 5.4). Every
  cell of the backend matrix has a fixture, including timeout, malformed and
  unavailable (ChatGPT 5.5).

## Relationship to the current implementation

Not built. The integrity patterns, the forged-ping guard and the bare-"the
card" refusal exist in the gate and are the detectors this record gathers
under one name. No intake function, no provenance stamp, no intake row, no
backend and no schema validator exists. Nothing in `router.py` or `cli.py`
reads an intake result, because none is produced.

## Test that would falsify this ADR

An intake function runs before `safety.evaluate`, or changes its input, or
reads its output to alter a decision; an intake row grants a permission; a
typed sentence lands in the record as operator-set; a backend's hit without
a lexicon hit escalates before that backend has been reviewed; a backend
timeout delays or changes the card.

## Revision history

- **2026-09-10, second revision.** Amended in place with review round 2's
  findings: the trusted session assigned before the gate; provenance labels
  code-computed with field-level write permissions; the pinned inputs; the
  card committed before intake is invoked, with the budget as a manifest
  field and the crisis turn without a stamp as a legal state; the matrix
  with the inconclusive row and the six error cells; the miss/hit cell as
  ruled (Thing 3) with its three constraints and its dissent; the promotion
  cell; the integrity matrix left unspecified on the record; the settling
  test reworded for the revised failure rule.
- **2026-09-10.** The failure rule revised from fail-closed-on-the-seat to
  seat-the-persona-and-block-the-writes, with one automatic retry and the
  house's failure line, on the operator's ruling of 10 September 2026 after
  review round 2 (positions: for the original rule, DeepSeek, Kimi, Qwen and
  ChatGPT with conditions; against, GLM, Grok, Nemotron and Gemini; the
  operator took GLM's rule with ChatGPT's conditions and added the diner
  rule, that a person is never spoken to like an engineer). The original
  clause read: "If deterministic intake raises, returns an invalid envelope,
  times out, or labels the channel unknown after the gate said proceed, the
  house fails closed on the seat: nobody is seated, a plain house line saying
  the message could not be checked ships (the existing language_scope line is
  the model for its shape), no persona speaks. If the gate fired, the card
  ships regardless of intake's state." The record is Proposed and was revised
  in place; the register note carries the date.
