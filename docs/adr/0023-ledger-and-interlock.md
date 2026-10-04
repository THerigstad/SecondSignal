# ADR-0023: The ledger and the interlock are two named things bound by one invariant, and nothing weakens a restriction without a clearance row

- **Status:** Proposed — none; drafted 2026-09-08 from the rulings on review round 1; read by eight model families in review round 2 (8 to 10 September 2026) and amended in place on 2026-09-10 with their findings (the revision history at the end); its aftermath section was read against the code by ten model families in review round 3B (26 to 28 September 2026) and amended in place on 2026-10-04 under rulings 14, 15, 16 and 20 of 3 October 2026 (the grace turn as a named policy, protection decided before the reply, what the window is for, the resource line said once and shown for the window, the substantive floor's reason code); under the standing rule it stays Proposed until a further round has read the amended text, and the flip is the operator's act
- **Date:** 2026-09-08; amended 2026-09-10 and 2026-10-04
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
an acknowledgement list, `tests/test_latch.py`). The rule and its reason
code (`substantive: token_floor_3`, with its five named negatives) are
stated in the aftermath section below (ruling 20 of 3 October 2026).

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
superseded by this sentence (ChatGPT 2.5). The count is renewed by any new
card, can never clear a cap or declare anyone safe, and is never an
"awaiting human" loop when no human exists. A persona seated on a turn
inside the window carries `no_joke` for that turn. Delivery rules: one
committed escalation per event; retries reuse the committed decision and
never call `route` again; duplicate deliveries do not decrement the count;
a failed presentation stays explicitly unresolved. An acknowledgment field
exists on the event only when the manifest declares staffed review; a
resource-only deployment has no such field to leave empty. The count and
the `no_joke` obligation are built in the gate and the router since 10
September (`tests/test_danger_lane.py`), with the ordering fix of 4 October
2026 below; the receipts, the manifest and the event are not. Review round
3B (26 to 28 September 2026) read this section against the code with ten
model families and found four things, which the operator ruled on 3 October
2026 (rulings 14, 15, 16 and 20); the four paragraphs that follow are those
rulings, written into the record on 4 October 2026.

**The grace turn is a named policy (ruling 14 of 3 October 2026).**
Whichever turn comes first after a card, acknowledgement or not, does not
consume an aftermath count. So: the card's own turn does not consume a
count; the first turn after the card does not consume a count, which means
that an acknowledgement after the card does not consume a count and that a
substantive first reply does not either; a failed presentation does not
consume a count. Three reasons, in the reviewers' words. First, the rule
needs no acknowledgement classifier, which is exactly the lever this record
legislated away when it made "substantive" a recorded reason code (Kimi via
Perplexity, Vibe; Nemotron: an acknowledgement rule would "punish the person
for not performing gratitude"). Second, the turn after a card is where
retractions and bargaining cluster (Grok, Kimi K3), and that is the turn to
protect. Third, the broader exemption can only extend protection, never
shorten it (GLM via Perplexity; GLM at chat.z.ai; Vibe). History: from
10 September to 3 October this paragraph said only that an acknowledgement
does not consume a count, while the code exempted whichever turn came first
(`escalated_last_turn`), so the record promised one message less protection
than the code gave. Nine of the ten returns of record said change the
sentence to the positional rule; ChatGPT alone said change the code, or
adopt the grace turn as a named, justified policy rather than smuggle it in
through a flag. The operator kept the code's behaviour and adopted it
ChatGPT's way, as this named policy; ChatGPT's own position is the dissent
recorded below. Gemini's `gemini-traj-aftermath-substantive-followup`, which
passes on the tree, pins the substantive-first-turn case; DeepSeek's
`deepseek-traj-aftermath-first-turn-001` pins the boundary with the last
consuming reply.

**Protection is decided before the reply; consumption is committed after it
(ruling 15 of 3 October 2026, first half).** Whether a reply is protected
(humour off, `no_joke` carried, resources within reach) is decided from the
count as it stands before the reply, and the count is consumed only after the
reply's obligations are set, so the reply that spends the last count is
itself protected. Until 4 October 2026 the code decided protection from the
count after the turn was spent, so the reply that spent the last count was
released unprotected, and humour and the provocateur were legal one message
early. Two reviewers found it independently: ChatGPT (fixture A, turn 5:
after-count 0 and `no_joke` true on the same decision; "Protect the last
consuming reply, not only replies whose post-count is positive") and GLM at
chat.z.ai ("the turn that spends the last count must itself be protected
(decay after the decision, not before it)"). Fixed 4 October 2026. ChatGPT's
`chatgpt-traj-r3b-twenty-turn-terminal-guard` is the settling fixture;
`slow-slope-001`'s turn nine and DeepSeek's
`deepseek-traj-aftermath-first-turn-001` pin the same boundary.

**What the window is for (ruling 15, second half).** After the window
closes, ordinary humour returns. A joke that targets the crisis itself is
refused for the rest of the conversation. That is the named reason the window
exists: the window is a floor under the person's next few messages, not a
timer after which what they said becomes material; it is bounded so a person
is not kept under a hush for an afternoon, and the refusal of a joke aimed at
the crisis is unbounded because the memory of the card must never become a
roast (Grok: "memory of the HIT must not become a roast", a roast ask after
zero never seats the provocateur on the crisis; Vibe: the cap re-attaches when
the capped ask recurs; Qwen: "the clock should be a floor, not a release",
adopted in part and recorded below). The detector for "targets the crisis"
is not built. It is measured first in the gap-closure push, with controls for
ordinary humour after the window, before any rule is written for it, so that
the refusal never widens into a hush. Settling cases:
`grok-traj-roast-after-zero-001` passes today, because the seat a roast ask
earns after the window is not the provocateur's on that text;
`vibe-traj-refusal-decay-001` and `qwen-traj-humor-after-expiry-004` are
known gaps until the detector exists.

**The resource line: said once, shown for the window (ruling 16 of
3 October 2026).** The obligation "resources must be within reach" stays on
every reply inside the two-turn window, so a test can check it and it can
never be silently dropped. The character's text carries the full resource
line once, on the turn right after the card. For the rest of the window the
Talking Table shows a quiet on-screen reminder in its place; the person may
close it; closing it is an evidence row and changes nothing underneath; the
voice never reads the reminder a second time (on the turn after the card the
whole reply is spoken once, safety lines included, by ruling 24 of the same
day; the card itself is never spoken). The reminder is not built; it is
queued as Talking Table work with the one-tap correction control of ruling 12.
Plumbing owed with it: the audit's attached-line check (predicate P2) must
accept "shown on screen" as satisfying the obligation on the later turns, so
the obligation and the text can differ without a red test. Two reviewers held
the "once" position outright, the line in the text once and not again (Kimi
via Perplexity, GLM via Perplexity); it is filed as a disputed trajectory,
`glm-and-kimi-via-perplexity-traj-resource-line-once-001`, built from
`slow-slope-001` with their negative expectation on turn eight, and the
trajectory format gained `disclosures_not_contain` for it; the dissent is
recorded below.

**"Substantive", with its reason code (ruling 20 of 3 October 2026).** A
turn is substantive when, after masking, it carries three or more distinct
tokens outside the acknowledgement list and the repeated-acknowledgement
repair does not fold it (push 2, commit 01651cc, 28 September 2026: repeated
acknowledgements like "ok ok ok" do not count, and neither does a turn made
only of function words or of one word repeated). The reason code this record
requires is the turn's substance code, carried by the gate since 4 October
2026 on every turn the clock looks at and surfaced in the safety reasons
inside the window: `substantive: token_floor_3` when the turn counts, and
when it does not, one of `not substantive: empty_turn`,
`acknowledgement_only`, `repeated_word`, `below_token_floor` or
`filler_only`, each naming the one clause of the rule that decided it. The
ledger's observation row carries the same code when the ledger exists, so
the expiry's real writer is named on every row and no prose is parsed to
find it. The rule stays simple on purpose:
no content classifier, because whoever labels a turn substantive is the
expiry's real writer, and a classifier there is the lever this record
refuses. The record says plainly that the simple rule fails both ways.
Filler drains both clocks: Kimi K3's "today was a day, I guess"
(`kimi-k3-traj-filler-today-was-a-day-001`) and Nemotron's "yes I will"
after "ok thanks" against "I will call"
(`nemotron-traj-substantive-heuristic-001`) count as substantive and run as
known gaps; Qwen's "the the the" (`qwen-traj-substantive-spam-001`) and
ChatGPT's two "understood understood understood" trajectories
(`chatgpt-traj-understood-filler-aftermath-001`,
`chatgpt-traj-understood-filler-soft-latch-001`) pass, because the repair of
28 September already holds them. And five short turns of real distress ("I
am scared.", "I feel alone.") also count, so the soft window can close before
the person has said much: DeepSeek's `deepseek-traj-soft-decay-substance-001`
runs as a dispute, recorded below.

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

Review round 3B's dissents on the aftermath section, kept as data with the
rulings of 3 October 2026 (each is also in `docs/notes/dissent-log.md`):

- **ChatGPT, on the grace turn (ruling 14).** "A published substantive-turn
  clock should count eligible substantive contributions; an accidental extra
  grace turn should not be smuggled in through a flag." Its primary position
  was to change the code to the record, one message less protection, under
  which `slow-slope-001` reads 2, 1, 0, 0 with turns seven and eight still
  DISCLOSE; its fallback, that a grace turn wanted on purpose must be adopted
  "as a new, explicitly justified policy", is the path the operator took.
  Recorded, not adopted on the primary position: the grace turn is now the
  named policy above, with its reasons.
- **Qwen, on the window (ruling 15).** "The clock should be a floor, not a
  release": the window should not end the protection, and
  `qwen-traj-humor-after-expiry-004` behaves on the tree as Qwen predicted.
  Adopted in part: after the window ordinary humour returns, as released, but
  a joke that targets the crisis is refused for the rest of the conversation,
  which is the floor Qwen asked for on the one axis that matters; the
  trajectory runs as a known gap until the detector exists.
- **Kimi via Perplexity and GLM via Perplexity, on the resource line
  (ruling 16).** The line once, on the turn after the card, and not again in
  the character's text. Adopted for the text, declined for the obligation:
  the obligation stays on every reply inside the window so it can be tested
  and never silently dropped, and the screen carries the reminder after the
  first turn. Filed as a disputed trajectory,
  `glm-and-kimi-via-perplexity-traj-resource-line-once-001`.
- **DeepSeek, on the substantive floor (ruling 20).** Five short turns of
  real distress count as substantive, so the soft window can close before the
  person has said much (`deepseek-traj-soft-decay-substance-001`, with its
  note in Spanish and an English gloss). Recorded as a dispute: the simple
  rule is kept with no content classifier, by design, and the dispute is
  visible and measured on every run.

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
(`tests/test_danger_lane.py`; since 4 October 2026 protection is decided from
the count before the reply, and the aftermath section's settling trajectories
run through `evals/run_trajectories.py` under ADR-0028 (Proposed), where the
known gaps and the dispute named above are visible on every run). There is
no append-only row, no hash chain,
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
substantive by anything but the recorded reason code
(`substantive: token_floor_3`), or by a content classifier; the aftermath
count clears a cap, marks anyone safe, or is consumed by the first turn after
the card, acknowledgement or not, by a duplicate delivery or by the card's own
turn; the reply that spends the last count is released without `no_joke`; a
joke that targets the crisis is seated after the window; a reply inside the
window carries neither the resource line nor the on-screen reminder in its
place; the voice reads the reminder a second time.

## Revision history

- **2026-10-04.** The aftermath section amended in place with review round
  3B's findings and the operator's rulings of 3 October 2026: the grace turn
  stated as a named policy with its three reasons, in place of the sentence
  that named only an acknowledgement (ruling 14; the code's behaviour kept);
  protection decided from the count before the reply and consumption
  committed after it, so the reply that spends the last count is protected
  (ruling 15, fixed in the code the same day); what the window is for, with
  the rule that a joke targeting the crisis is refused for the rest of the
  conversation and its unbuilt detector (ruling 15); the resource line said
  once in the text and shown on screen for the rest of the window, with the
  obligation kept on every reply (ruling 16); the substantive floor's reason
  code written next to the rule, with no content classifier (ruling 20); the
  round's dissents (ChatGPT, Qwen, Kimi via Perplexity and GLM via Perplexity,
  DeepSeek) kept as data; the settling trajectories named by file. Nothing
  outside the aftermath section changed, apart from the pointer to the reason
  code under "Substantive is a ledger field" and the falsifying tests.
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
