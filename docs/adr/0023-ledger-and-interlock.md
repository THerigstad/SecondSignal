# ADR-0023: The ledger and the interlock are two named things bound by one invariant, and nothing weakens a restriction without a clearance row

- **Status:** Proposed — none; drafted 2026-09-08 from the rulings on review round 1; read by eight model families in review round 2 (8 to 10 September 2026) and amended in place on 2026-09-10 with their findings (the revision history at the end); under the standing rule it stays Proposed until a further round has read the amended text, and the flip is the operator's act
- **Date:** 2026-09-08
- **Evidence:** the Security Division document v1.1 (`docs/notes/security-division-2026-09-08.md`, §5); review round 1 (Grok 2.2, 4.a and tests 5.1, 5.4; ChatGPT 2.4, 4a, attacks A2, A4, F6 and test 5.1; GrokBot 4a and D1; Qwen 2.3, 2.4, 4a and tests 5.1, 5.8; DeepSeek 4a and disagreement 5); review round 2 (every family on the conditional append, the soft tier's expiry and the card's path; Grok open items 2 to 4 and fixtures `r2-ledger-scope-001`, `r2-ledger-cas-001`; ChatGPT 2.4, 2.5, 4.a.3, 4.a.4, 4.a.7; Kimi's genesis-versus-wiped and the typed "substantive" field; GLM's provenance of sanctioned weakenings; Gemini's incomparable-transition attack; Nemotron's row schema; Sonar's stale head; DeepSeek's attestation caveat), filed verbatim under `evals/cases/deferred/round2_persistence_cases.json`; the 31 August audits (ChatGPT threat model §14.5, the five-stage separation; the Grok harvest's "append-only, hash-chained ledger"); what exists in the tree today (`tests/test_latch.py`, `tests/test_guards.py::test_dependency_latch_is_session_scoped_and_unresettable_by_text`, `tests/test_danger_lane.py` for the aftermath count)
- **Depends on:** ADR-0015 (the two-tier latch); ADR-0005 (safety state is separate from personal memory); ADR-0010 (the gate fails closed)
- **Amends:** ADR-0019 (carries the contract for its object four, which that record only names); ADR-0015 (the visibility clause for the hard tier: once when the latch sets, again only as a refusal's reason; the cap itself is unchanged)
- **Related:** ADR-0022 (intake writes the provenance the ledger's rows carry)

## Context

The 7 September document said "Orrin's ledger and Orrin's stop-and-clearance
are one object seen from two sides." All five reviewing families refused
the sentence, each in its own vocabulary and for the same reason: a record
and the rule that reads it have different failure modes, and one noun hides
a missing module. The same round found a contract conflict already in the
tree: the house block says a safety inference "latches until an operator
clears it", the research paper permits expiry, and the built code does
neither consistently. The soft tier decays by published policy after five
clean substantive turns, the hard tier never expires inside a session, and
session state lives in memory only, so today a hard latch dies with the
session, which is the opposite of what ADR-0015 promises.

## Decision

### Two named things

**The ledger** is the record. Append-only rows, each carrying an
identifier, a writer, a reason, the digest of the previous row, and the
digest of the decision it describes. After every decision the house appends
one row: turn, action, latch state and tier, holds, caps, the dependency
counter, and any clearance with its reason. Nothing is edited or deleted; a
clearance is a new row, never the removal of an old one. The ledger never
sets a latch (the gate does) and never clears one (an operator does). It
never describes the person.

**The interlock** is the rule. A pure function from the ledger's current
state plus a proposed transition to `OK` or `WITHHOLD`. It checks the
expected head, so a decision computed against a stale ledger can never
release a reply. It is the only reader that can admit a turn.

**The invariant that binds them.** A restriction ceases in exactly two
ways: through the declared, recorded policy lifetime it was written with,
or through an exact, authorized clearance row for that occurrence. Nothing
else weakens it. A hard latch has no lifetime. An expiry is a distinct
recorded event with a machine reason code, written by the monitor, never a
minted operator clearance. (Round 1 wrote the invariant as "nothing weakens
a restriction unless a clearance row already exists"; five families in
round 2 pointed out that the sentence forbade the soft tier's published
decay that ADR-0015 permits, so the exception is stated inside the
invariant rather than beside it.) The interlock rules on restrictions
only: it can withhold a turn the gate would have admitted and can never
admit a turn the gate withheld. Withhold wins every composition of
restrictions; it never withholds the house's own safety response (the
card's path, below).

**"Weaker than", defined per occurrence.** Round 2 (Kimi, GLM, Gemini)
found that the word presupposed an order over latches, caps, holds and
scopes that the record never gave, so a transition that drops one cap and
adds one hold was incomparable, and a renamed scope was a different
restriction under exact matching; Gemini built the attack, a seat proposing
empty caps while the evaluator checked latch state only. The order is per
occurrence: a transition is a weakening if any restriction occurrence
present at the head is absent, narrowed, or shortened in the proposal,
whatever else the proposal adds; the effective caps after a transition must
be a superset of the head's caps for every occurrence that has not ceased
by lifetime or clearance; and an occurrence identifier is assigned once at
write time and can never be re-created by a later row.

**Sanctioned weakenings carry provenance too (GLM).** A weakening by policy
lifetime names the published policy and its version; the record says where
published policies live and how the interlock verifies that a policy is
published, and a policy the interlock cannot verify is not a policy.

### Five rules the reviewers' attacks added

1. A clearance row names the exact occurrence it clears by identifier and
   carries a reason, a scope, an expiry and a host-attested writer. Message
   text and model output can never be that writer. The scope may not be
   wider than the occurrence named: a row whose scope is "session" or "all
   hard" is rejected, because a wider scope is a second occurrence being
   cleared for free (Grok, open item 2, fixture `r2-ledger-scope-001`). A
   clearance carries an expiry, and an expired clearance is absent at
   admission time (Kimi). The row's expiry means one thing, an
   authorization that ends, never a temporary exemption that resumes
   (ChatGPT 4.a.4).
2. Decide, append conditionally, then release. The append is a
   compare-and-append: the head must equal the expected head at the commit
   point, not only at decision time, and a commit point binds the decision,
   the policy version, the input digest, the head and the delivery
   identity. Two turns that read one head and both append are a fork, and a
   fork is `WITHHOLD` for both (Grok, ChatGPT's delivery race, Kimi's
   single-writer question, GLM's cross-session case, Sonar's stale head;
   fixture `r2-ledger-cas-001`). A stale head is any head other than the
   current one; a valid historical head is stale. After a crash the turn is
   re-evaluated from the ledger, never released from memory. A crash after
   an escalation is committed but before it is presented is neither a new
   decision nor a new escalation: revalidation reuses the committed
   decision with an idempotent delivery receipt, a duplicate delivery
   creates no second event and consumes no aftermath turn, and re-routing
   never happens (ChatGPT 4.a.4).
3. A ledger the interlock cannot read (a broken chain, a malformed row, a
   missing head) is `WITHHOLD` for persona output and for every
   permission-bearing transition, never proceed. An empty ledger after a
   known non-empty history is a wiped ledger, not a genesis, and is
   `WITHHOLD`; telling the two apart needs the head checkpoint outside the
   operator's reach (Kimi). Rows are validated against a schema before they
   are read, and "durably" means a named persistence format, not a word
   (Nemotron).
4. Interpretation rows are evidence, not power. A model's proposed
   interpretation is appended and ignored for admission; only a clearance
   row moves a restriction. The disposition writer is a deterministic
   function of observed events with a stated predicate, so that a row
   reading "minor, confidence 0.81" can never feed the writer of a hard
   latch and appear to the interlock as a new restriction rather than a
   weakening (Grok, open item 3). Appeals are inert: an appeal row has no
   effect on the restriction projection in either direction, carries no
   outcome field (a reader that treated one as a lever would be the bug
   Nemotron named), still advances the head so that pending decisions
   revalidate, and untrusted appends are bounded so that a flood exhausts
   neither storage nor a lock while "appeal present" never becomes a safety
   decision (ChatGPT 2.13, 4.a.7).
5. Every restriction carries its own lifetime, subject, scope, creating
   policy version and expiry predicate, bound to the occurrence at write
   time; a later policy version cannot reinterpret an existing occurrence
   (ChatGPT, trace A4-3). Lifetime is classified by its own predicate at
   write time, so a hard latch can never be tagged turn-local and end with
   the turn under this rule (Grok, open item 4). A turn-local hold ending
   is not a weakening, and a persistent latch never expires by a set
   comparison.

**"Substantive" is a ledger field.** The soft tier's expiry is computed
from observation and disposition rows only, and whether a turn was
substantive is written on the observation row with a machine reason code,
because whoever labels a turn substantive is the expiry's real writer
(Grok, Kimi). Round 2 reproduced exactly this lever in the tree: the clock
counted tokens, so five turns of "ok ok ok" cleared a declared adult's
soft latch; fixed on 10 September (a substantive turn is new content beyond
an acknowledgement list, `tests/test_latch.py`).

### The three events, kept apart

- **Correction.** A correction offered by the person, or by anyone else, is
  recorded as an evidence event with a visible line and clears nothing. An
  affirmation is never a key; message text never clears a latch.
- **Expiry.** Only a published policy can set an expiry. The soft tier's
  five-clean-turns decay is such a policy and stays. None exists for a hard
  latch, and this record does not create one: the hard latch is
  operator-only, with no clock.
- **Clearance.** An operator's act, with a reason, scoped and time-bound,
  always decided outside the function that created the restriction.
  Selective clear is exact: clearing one reason clears that reason and no
  other; an absent or already-cleared reason is a no-op or a rejection,
  never a fall-through to clear-all.

An appeal is recorded, decided by a human outside the function, and never
read by the interlock for admission. It is inert on disposition in both
directions (rule 4 says what inert means). The person has no visibility
today that an appeal is pending (GLM); when the ledger exists, the pending
state is shown in the house's words, not the function's.

### Persistence, and the duty it creates

Restrictions persist across sessions. The ledger is the store that carries a
hard latch past the session boundary (the elapsed-time rule of ADR-0022's
stamp starts a new session; it does not clear anything). Because the only
exit from a hard latch is a human, a deployment that persists restrictions
takes on a staffing duty: someone must be able to read a clearance request
and write a clearance row within a published time. The capability manifest
declares whether that person exists. Until the ledger is built, the
limitation is stated in `docs/known-limitations.md`, not hidden.

### The five stages

Every safety event walks five separate records, never collapsed into one
and never converted into a psychological description of the person: the
observed structural event; the interpretation (with a confidence, when a
model proposes it); the disposition (the cap or latch applied); the appeal;
the clearance or correction. The ledger coordinates these records. It may
not decide an appeal against its own interpretation.

### The card's independent path

The house's safety response has a delivery path of its own. When the gate
requires a card, the card is committed before intake is invoked and before
the ledger is consulted for admission; the interlock withholds persona
output and permission-bearing transitions, never a gate-required card; an
unreadable ledger while the gate requires a card degrades to a card with an
explicitly unresolved audit status and a degraded receipt, never to
silence and never to a bypass of the interlock for anything but the card
(ChatGPT 2.1, 5.2; Grok's aftermath case, a person who just received the
card silenced next turn by an unreadable ledger). The fixed crisis card is
exempt from the ledger writer, the narrator, the harness token in the
house block's Review paragraph, and intake alike: nothing that can fail
stands between the gate's verdict and the person.

### After the card: bounded aftermath as presentation state

A capability manifest declares whether a deployment is resource-only or has
staffed operator review. An escalation event is created from the action, not
from the crisis read, so the unscreened-language path is never relabeled as
detected clinical risk. Receipts (adapter accepted, render reported,
operator acknowledged, resource open requested, person reports connection,
operationally complete, unresolved) are evidence and never mean "safe".

Bounded aftermath is presentation state, not latch state: a finite count
of substantive turns after any card (the fixture value is two) during
which humour is off and the resources stay reachable. There is one clock,
substantive turns as the ledger field above defines them, and this record
is the clock's home; the Security Division note's "committed turns" is
superseded by this sentence (ChatGPT 2.5). The card's own turn does not
consume a count; an acknowledgement after the card does not consume a
count; a failed presentation does not consume a count. The count is renewed
by any new card, can never clear a cap or declare anyone safe, and is never
an "awaiting human" loop when no human exists. A persona seated on the
turn after a card carries `no_joke` for those turns. Delivery rules: one
committed escalation per event; retries reuse the committed decision and
never call `route` again; duplicate deliveries do not decrement the count;
a failed presentation stays explicitly unresolved. An acknowledgment field
exists on the event only when the manifest declares staffed review; a
resource-only deployment has no such field to leave empty. The count and
the `no_joke` obligation are built in the gate and the router since 10
September (`tests/test_danger_lane.py`); the receipts, the manifest and
the event are not.

### The fail-closed class list

The gate implements detection; this record owns the list of classes that
must fail closed. Two were added on the record of 2026-09-08 and built on
10 September 2026 (`tests/test_danger_lane.py`, `evals/cases/p0_lane_2026-09-10.json`):
weapon-free danger from another person (present confinement, prior
violence, fear for dependents, and, from review round 2's addendum, an
explicit threat to life; any two of the four in one message escalates with
the danger card and the verified domestic-violence line), and the
post-separation window, which got its verified resource line after the
operator's own verification pass over every row on 8 September. The
other-person-danger lane never seats recovery.

### Where a model may enter

The interpretation stage only, and only as a proposal the ledger records as
an interpretation with a confidence, never as a disposition. Everything else
is deterministic. An interpretation engine runs on a family different from
the seat's and from the intake backend's in the same turn.

### The narrator

`orrin_persona` reads rows that already exist and explains them, offline, to
an operator. It writes nothing, clears nothing, and never speaks to a user.

### The single-operator common mode

While one person can edit the rules, the evidence and the key, and is the
only appeal reviewer, no independence claim is made for this function. That
is a deployment limitation, recorded as such. When a second human exists,
policy editing, appeal review and key holding are separated, and the
ledger's head digest is checkpointed with an external witness the operator
cannot silently rewrite. Round 2 (Grok, GLM) refused the earlier example,
"the commit history", because the operator is the only pusher of this
repository, and named a fourth common mode: the same hand writes the gold
labels. Both are in `docs/known-limitations.md`. DeepSeek's caveat stands
beside them: the interlock trusts a host attestation it cannot verify, and
a hash chain detects corruption, not a compromised key.

## Dissent kept as data

Qwen 3.8 Max Thinking wanted the interlock also to require the absence of
any conflicting unresolved appeal before permitting a weakening. Declined:
the moment an appeal can block or unblock anything, filing appeals becomes
a lever, which is the appeal-weaponization hole (T58) by another door.
Settling tests if the position returns: an open appeal plus a valid
clearance row must still admit exactly the scoped weakening; an open appeal
with no clearance row must still withhold; if either fixture can be made to
fail only by the appeal's presence, the appeal has become a lever. Qwen's
operator-unavailability fallback (test 5.8) is kept as a live dissent, not
boxed; the answer today is the staffing duty above. Round 2 confirmed the
ruling from every family that tried to move a restriction with an appeal
(none could); GLM accepted it and asked that its cost stand next to it,
which it does: a wrongly issued clearance proceeds while an appeal is open,
and the remedy is a second clearance row, never a blocked one.

## Consequences

- The house block's Memory sentence reads, from v1.1: "A safety inference
  latches until an operator clears it with a reason; a correction you or
  the person offer is recorded as evidence and clears nothing; only a
  published policy can set an expiry, and none does for a hard latch."
- ADR-0015's visibility clause for the hard tier changes: the inferred line
  is shown once when the latch sets, goes quiet while the cap persists, and
  is shown again only when a capped ask is refused, as the refusal's reason,
  or when the person offers a correction, as the answer to it. The cap never
  changes with the line. Built 10 September 2026 (`tests/test_house_lines.py`,
  `tests/test_latch.py`); until then the code attached the line to every
  reply of a hard-latched session.
- `docs/known-limitations.md` states the lifetime contradiction (a hard
  latch dies with the session today, and round 2 named the three deaths of
  one latch: a second device, a process restart, an elapsed-time boundary,
  which the documents had described as one), the staffing duty with its
  published time as a manifest field that has no default, the external
  witness, and the two common modes.
- The careful-side line's session honesty: until persistence exists, the
  restriction the line describes is session-scoped in fact, and the line
  may not promise more than the tree keeps (Kimi's dissent 5.1, recorded
  in `docs/known-limitations.md`; the copy decision is the operator's).
- Settling tests on record: Grok 5.1 and 5.4, ChatGPT 5.1, GrokBot D1,
  Qwen 5.1, DeepSeek disagreement 5, plus the two appeal fixtures above,
  written when the ledger exists; and from round 2, verbatim in
  `evals/cases/deferred/round2_persistence_cases.json`: Grok's scope and
  compare-and-append fixtures, Sonar's stale head, and the session-boundary
  fixtures from GLM, Nemotron and Kimi that fail today and are expected to
  until persistence lands.

## Relationship to the current implementation

Not built. What exists is session state inside the gate: a hard latch that
does not expire within a session (`test_strong_signal_sets_a_hard_latch_that_does_not_expire`),
a soft tier that decays by policy on substantive turns as defined above, an
operator clear by reason that names who cleared
(`test_operator_clears_by_reason_and_the_record_says_who`), selective clear
(`test_clearing_one_reason_leaves_the_other_in_force`), the rule that
message text never clears a latch, the correction event as a latch-history
row, and the bounded aftermath count with its `no_joke` obligation
(`tests/test_danger_lane.py`). There is no append-only row, no hash chain,
no interlock function, no clearance row, no persistence across sessions, no
capability manifest, no receipts, no escalation event and no narrator.
Those are promises this record makes and the code has not.

## Test that would falsify this ADR

A turn whose restrictions are weaker than the previous row is released with
no clearance row and no recorded policy expiry between them; a clearance row
is written by message text or by a model, or clears a scope wider than the
occurrence it names; a decision computed against a stale head releases a
reply, or two turns append on one head; an unreadable or wiped ledger
proceeds, or withholds a gate-required card; an interpretation row moves a
restriction; an appeal's presence changes what the interlock admits; a hard
latch expires by a clock or ends with a turn; a turn is labelled
substantive by anything but the recorded reason code; the aftermath count
clears a cap, marks anyone safe, or is consumed by an acknowledgement, a
duplicate delivery or the card's own turn.

## Revision history

- **2026-09-10.** Amended in place with review round 2's findings, in the
  families' words where they wrote the rule: the invariant restated with
  the policy-lifetime exception inside it and the expiry as a recorded
  event; "weaker than" defined per occurrence; sanctioned weakenings with
  provenance; rule 1 rejecting scopes wider than the occurrence, with
  clearance expiry; rule 2 as a conditional append with a commit point, a
  fork rule, the stale-head definition and the crash-after-commit case;
  rule 3 with genesis versus wiped, schema validation and a named
  persistence format; rule 4 with the disposition predicate and appeals
  defined as inert; rule 5 binding lifetime, subject, scope, policy version
  and expiry predicate at write time; "substantive" as a ledger field; the
  card's independent path; one aftermath clock, with what does and does not
  consume it; the class list as built; the external witness and the fourth
  common mode; the round-2 fixtures as settling tests. The 8 September text
  is in the repository's history; nothing it decided was reversed.
