# ADR-0031: A declared ask is a fact on the record

- **Status:** Proposed — built; the declared ask is recorded and explained without changing policy; the rule for letting an ask win the seat remains open; under the standing rule of 7 September 2026, a record written for the operator by the project's own assistants becomes canon only after a second model family has read it
- **Date:** 2026-10-10
- **Evidence:** `tests/test_p1_declared_ask.py` (all labelled cases and prior turns, all seven asks, unchanged decisions and sessions, boundary validation, static guards with negative cases, serialization, exact explanation, the real harness acknowledgement and audit, typed-name non-inference, and unchanged trajectories); `tests/test_h1_replay.py::test_h1_every_labelled_turn_keeps_its_policy_house_lines_and_release` (the unchanged historical replay); the deck test and the operator's ruling of 9 October 2026, built by order P1
- **Depends on:** ADR-0011 (no-signal routing is a policy), ADR-0016 (seat versus hold), ADR-0025 (Proposed) (the assist from the hold and an affinity that can trade seats), ADR-0029 (Proposed) (the voice is a harness behind the policy layer), ADR-0030 (Proposed) (a probability is evidence, not authority)

## Context

Table kit two built the house's explanation line and left the field out:
the policy record had no asked-character identity, and the Table could not
pretend a message had declared one. The line and its six reason clauses
were approved by the operator on 9 October 2026 ("copy all yes").

In the deck test of 9 October 2026, pressing a character's key seated
nobody: the policy never learned that anyone had asked for that character.
The operator ruled that leaving a known future hole is irresponsible and
that people need an explanation of why they cannot have their way.

A declaration and the rule for honoring it are separate facts. This order
records the declaration and explains the existing seat. Research has not
yet resolved when a declared ask should be allowed to win that seat.

## Decision

1. **A control declares the ask.** The surface supplies `asked`, a roster
   id declared by a control it owns, such as a deck key or phone button.
   Nothing reads an ask from message text. A typed "Could I talk to Willow?"
   without a declared control is text and produces no asked-character field.
2. **The ask travels on the record.** `RoutingDecision.asked_agent_id`
   records who was asked for, or None when nobody was asked. Every receipt
   and replay that carries the decision carries its declaration with it.
   Serialization includes the key only when present; `schema_version`
   remains 1 and the existing no-ask records keep their bytes.
3. **Recording an ask changes no policy.** It moves no seat, verdict,
   hold, latch, cap or contraindication. Every ranked candidate, score,
   obligation, hint, house ask and presentation fact remains identical.
   The crisis gate still screens the raw message. Apart from rejecting an
   invalid id at the boundary, `route` only copies the ask into the record.
4. **The house explains a different seat.** When the seated character
   differs from the declared ask, the existing harness acknowledgement uses
   the operator's approved line with a true reason from the record. Its
   reason names the asked candidate's own rationale; an unrelated held
   domain cannot masquerade as the reason. Existing release rules still
   apply, and a crisis card has no character acknowledgement.
5. **An unknown id is a caller error.** An ask naming no character on the
   supplied roster is refused with ValueError before observing the session.
   The declaration is never silently dropped or replaced by text inference.
   A known alias or case variant is recorded as the canonical id, through the
   roster's own resolver when the roster has one (landing fix of 10 October
   2026), so a record never carries two spellings of one character; a plain
   mapping without a resolver accepts exact ids only.
6. **The seating rule remains OPEN.** By the operator's word of 9 October
   2026, three candidates are recorded and none is adopted: the ask wins
   whenever the asked character is eligible; the ask only breaks ties; or
   the ask wins when the asked character is eligible and carries the
   message's topic. The operator will rule after research R2, and the chosen
   rule will be built under its own order, P2.

## Consequences

The harness accepts the declared ask and forwards it to `route`. Its
existing record reader attaches the approved acknowledgement by itself;
the audit row keeps the same complete record it always kept. No house-line
wording changes. A same-seat ask remains recorded without an acknowledgement.

The static guard permits only the keyword-only parameter, the exact
boundary validation, the one canonicalizing statement that follows it, the
field declaration, the eight constructor forwardings, and the two reporting
bodies. It rejects planted policy reads,
string keys elsewhere and changed forwarding. Behavioural proofs compare
every labelled case and prior turn against every roster ask, including
complete session state. Separate proofs pin the serializer, explanation,
no-ask audit bytes, and trajectory house lines, text and release.

The Table's keys and buttons are wired to this parameter by the next Table
order; nothing under `apps/` changes here. No inference from names, new
dependency, probabilistic extractor, real-model call or seating preference
is introduced. The open P2 rule and independent record review remain owed.
