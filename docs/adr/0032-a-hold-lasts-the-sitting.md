# ADR-0032: A hold lasts the sitting

- **Status:** Proposed — built; the session, gate and router carry holds until the sitting ends or an operator clears one with a reason; under the standing rule of 7 September 2026, a record written for the operator by the project's own assistants becomes canon only after a second model family has read it
- **Date:** 2026-10-10
- **Evidence:** `tests/test_p3_holds.py` (persistence, renewal, clearance, text cannot clear, recovery claim masking, unchanged gate and first turns, the three trajectories and H1 first-turn proof); `tests/test_h1_replay.py::test_h1_every_labelled_turn_keeps_its_policy_house_lines_and_release` (the regenerated replay); `tests/test_trajectory_runner.py::test_every_trajectory_runs_as_marked` (every trajectory); order P3 and ruling 13 of 3 October 2026, reaffirmed 8 and 9 October
- **Depends on:** ADR-0016 (seat versus hold), ADR-0027 (Proposed) (a relative's return to use is a hold), ADR-0022 (Proposed) (intake and provenance), ADR-0023 (Proposed) (ledger and interlock)

## Context

Review rounds 3 and 3B found that a hold was recomputed from each message.
A death named on one turn could be followed by a roast seat on the next.
Five reviewers found the hole; none defended that lifetime as the intended
design. The operator's ruling 13 is quoted verbatim from the dated account
in `docs/known-limitations.md`:

> a hold lasts the session: mentioning the subject again renews it; it ends only when the session ends, after a silence longer than the published elapsed-time threshold (eight hours, provisional, ADR-0022), or by an operator clearance; no message text ends it early; the crisis card's two-turn tail is a separate thing and is unchanged.

The record named in that quotation is ADR-0022 (Proposed). The operator
reaffirmed the build on 8 October and defined the sitting on 9 October,
ruling A: Reset, the server's end, or eight quiet hours; never a browser
closing. The elapsed-time threshold remains provisional. The surface
owns those boundaries; this record builds the policy's session state.

## Decision

1. A hold set by a message lasts the session. `SessionState.holds` stores
   each domain and the turn that set or last renewed it, and `active_holds`
   reports the domains in the fixed `HOLD_DOMAINS` order.
2. Naming the subject again renews its turn and appends a `renew` history
   row. First detection appends `set`; message and post-separation sources
   are recorded separately.
3. A hold ends when the session ends, which the surface decides through
   Reset, the server's end, or the published elapsed-time threshold of
   ADR-0022 (Proposed), eight hours provisional. An operator may end one
   early with `clear_hold(domain, reason, actor=...)`, recording exactly
   that domain, reason, actor and turn, following ADR-0023 (Proposed).
   A blank reason is refused; clearing an absent hold records nothing.
4. No message text ends a hold. Retractions, apologies, reassurance and
   text naming the clearing method cannot invoke the operator control.
5. A seat-claim masks its domain for this turn's seating and leaves the
   session hold intact. Subsequent turns carry it again. The existing
   scoring, eligibility, obligations and mode vetoes read the resulting
   hold tuple without new routing rules.
6. The crisis card's two-turn tail is separate and unchanged. The gate's
   carried hold list and its explanatory reasons do not change screening,
   action, cards, disclosures, latch state or aftermath arithmetic.
7. The policy layer never reads a clock. A new `SessionState` has no holds;
   no wall time or elapsed-time field is added to it.

## Consequences

A subject need not be repeated to keep the seat's obligations and the
humour and challenge vetoes. A later mention renews the history without
resetting the sitting. The explanation names holds carried from earlier
turns; fresh-session decisions keep their supplied bytes.

The trajectory runner's old per-message-expiry attribution is removed: an unexplained loss of session
state fails the causal invariant. Reviewer expectations remain intact;
the three hold trajectories lose only their now-obsolete known-gap key
once their required turns pass.

The Table's sitting clock and Reset belong to Table kit four. Its operator
clearance control is owed to the next Table order. This build changes no
Table or harness files and provides no persistence beyond the lifetime of
the session object. Independent review of this record is still required.
