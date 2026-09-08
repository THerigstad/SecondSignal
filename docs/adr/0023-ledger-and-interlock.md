# ADR-0023: The ledger and the interlock are two named things bound by one invariant, and nothing weakens a restriction without a clearance row

- **Status:** Proposed — drafted 2026-09-08 from the rulings on review round 1; not yet reviewed by a second model family, so it stays Proposed until review round 2 closes
- **Date:** 2026-09-08
- **Evidence:** the Security Division document v1.1 (`docs/notes/security-division-2026-09-08.md`, §5); review round 1 (Grok 2.2, 4.a and tests 5.1, 5.4; ChatGPT 2.4, 4a, attacks A2, A4, F6 and test 5.1; GrokBot 4a and D1; Qwen 2.3, 2.4, 4a and tests 5.1, 5.8; DeepSeek 4a and disagreement 5); the 31 August audits (ChatGPT threat model §14.5, the five-stage separation; the Grok harvest's "append-only, hash-chained ledger"); what exists in the tree today (`tests/test_latch.py`, `tests/test_guards.py::test_dependency_latch_is_session_scoped_and_unresettable_by_text`)
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

**The invariant that binds them.** Nothing weakens a restriction unless a
clearance row already exists for that exact occurrence. The interlock rules
on restrictions only: it can withhold a turn the gate would have admitted
and can never admit a turn the gate withheld. Withhold wins every
composition.

### Five rules the reviewers' attacks added

1. A clearance row names the exact occurrence it clears by identifier and
   carries a reason, a scope, an expiry and a host-attested writer. Message
   text and model output can never be that writer.
2. Decide, append durably, then release. After a crash the turn is
   re-evaluated from the ledger, never released from memory.
3. A ledger the interlock cannot read (a broken chain, a malformed row, a
   missing head) is `WITHHOLD`, never proceed.
4. Interpretation rows are evidence, not power. A model's proposed
   interpretation is appended and ignored for admission; only a clearance
   row moves a restriction.
5. Every restriction carries its own lifetime and scope. A turn-local hold
   ending is not a weakening, and a persistent latch never expires by a set
   comparison.

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
read by the interlock. It is inert on disposition in both directions.

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

### After the card: bounded aftermath as presentation state

A capability manifest declares whether a deployment is resource-only or has
staffed operator review. An escalation event is created from the action, not
from the crisis read, so the unscreened-language path is never relabeled as
detected clinical risk. Receipts (adapter accepted, render reported,
operator acknowledged, resource open requested, person reports connection,
operationally complete, unresolved) are evidence and never mean "safe".

Bounded aftermath is a finite count of substantive turns after any card
(fixture value: two) during which humour is off and the resources stay
reachable. It is renewed by any new card, can never clear a cap or declare
anyone safe, and is never an "awaiting human" loop when no human exists. A
persona seated on the turn after a card carries `no_joke` for those turns.
Delivery rules: one committed escalation per event; retries reuse the
committed decision and never call `route` again; duplicate deliveries do not
decrement the count; a failed presentation stays explicitly unresolved. An
acknowledgment field exists on the event only when the manifest declares
staffed review; a resource-only deployment has no such field to leave
empty.

### The fail-closed class list

The gate implements detection; this record owns the list of classes that
must fail closed. Two are added on the record of 2026-09-08 and built in the
lane after push 2: weapon-free danger from another person (present
confinement, prior violence, fear for dependents; any two of the three in
one message escalates with the card and the safety-first block), and the
post-separation window, which gets a verified resource line only after a
human verification pass. The other-person-danger lane never seats recovery.

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
ledger's head digest is checkpointed where the operator cannot silently
rewrite it (for example, the commit history).

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
boxed; the answer today is the staffing duty above.

## Consequences

- The house block's Memory sentence reads, from v1.1: "A safety inference
  latches until an operator clears it with a reason; a correction you or
  the person offer is recorded as evidence and clears nothing; only a
  published policy can set an expiry, and none does for a hard latch."
- ADR-0015's visibility clause for the hard tier changes: the inferred line
  is shown once when the latch sets, goes quiet while the cap persists, and
  is shown again only when a capped ask is refused, as the refusal's reason.
  The cap never changes with the line. (Today the code attaches the line to
  every reply of a hard-latched session; that is a defect to fix in the
  copy block after push 2, with a fixture pinning once-then-at-refusal.)
- `docs/known-limitations.md` states the lifetime contradiction (a hard
  latch dies with the session today), the staffing duty, and the
  single-operator common mode.
- Settling tests on record: Grok 5.1 and 5.4, ChatGPT 5.1, GrokBot D1,
  Qwen 5.1, DeepSeek disagreement 5, plus the two appeal fixtures above,
  written when the ledger exists.

## Relationship to the current implementation

Not built. What exists is session state inside the gate: a hard latch that
does not expire within a session (`test_strong_signal_sets_a_hard_latch_that_does_not_expire`),
a soft tier that decays by policy, an operator clear by reason that names
who cleared (`test_operator_clears_by_reason_and_the_record_says_who`),
selective clear (`test_clearing_one_reason_leaves_the_other_in_force`), and
the rule that message text never clears a latch. There is no append-only
row, no hash chain, no interlock function, no clearance row, no persistence
across sessions, no capability manifest, no aftermath counter and no
narrator. Those are promises this record makes and the code has not.

## Test that would falsify this ADR

A turn whose restrictions are weaker than the previous row is released with
no clearance row between them; a clearance row is written by message text
or by a model; a decision computed against a stale head releases a reply; an
unreadable ledger proceeds; an interpretation row moves a restriction; an
appeal's presence changes what the interlock admits; a hard latch expires by
a clock; the aftermath counter clears a cap or marks anyone safe.
