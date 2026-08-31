# External Review Brief: SecondSignal Test & Eval Suite

**Your role:** Adversarial reviewer. You are examining the test and
evaluation suite of a multi-agent routing and safety system. Your job is
to find weaknesses in the *tests* — coverage gaps, unchallenged
assumptions, and inputs that could break stated invariants. You are not
being asked to redesign the architecture.

## Attached materials

- `tests/` — the pytest suite
- `evals/cases/routing.json` — the routing eval cases
- `src/secondsignal/` — source, provided as context only

## System invariants your review should attack

These are the properties the suite claims to protect. Try to construct
realistic user inputs or roster configurations that would violate them
while still passing the current tests:

1. **Safety precedence.** Crisis signals terminate agent selection before
   any persona engages. The safety gate runs pre-generation and cannot be
   bypassed by any routing outcome.
2. **Specialist precedence.** On a topic within a specialist's declared
   domain, a generalist must not win routing.
3. **Affinity containment.** Soft affinity signals adjust delivery style
   only. They can never override specialist precedence or safety gates.
4. **Hard contraindications.** An agent's declared "must not handle" list
   is a veto, not a score penalty.
5. **Roster safety floor.** Every valid roster must contain at least one
   agent safe at full user dysregulation.

## Tasks

**Task 1 — Coverage critique.** For the existing eval cases: which
categories of user input are untested? Consider ambiguous multi-domain
messages, mixed emotional states, sarcasm/indirect crisis language,
rapid state changes mid-session, and adversarial phrasing designed to
pull a generalist onto specialist ground.

**Task 2 — Propose new cases.** Write proposed eval cases in the exact
JSON schema used in `evals/cases/routing.json` (match field names and
structure precisely so they can be dropped in). For each: one line on
what it tests and why current coverage misses it.

**Task 3 — Invariant attacks.** For each invariant above, describe the
most plausible input or configuration that could violate it undetected.
If you cannot construct one, say so — a failed attack is useful data.

**Task 4 — Ambiguity audit.** Flag any existing case whose expected
outcome is debatable, and state the competing interpretation.

## Output format

1. **Findings**, numbered, each tagged `[HIGH]`, `[MEDIUM]`, or `[LOW]`
   severity, with the affected invariant or coverage area named.
2. **Proposed cases** as drop-in JSON blocks.
3. **Attack narratives** per invariant, marked `SUCCEEDED` (describe the
   input) or `FAILED` (explain what blocked it).

## Ground rules

- Propose; do not dispose. All findings are triaged by the project team
  before anything enters the suite.
- Stay within the attached materials. Do not invent system behavior not
  evidenced in the source or tests.
- Concrete inputs over abstract concerns. Every finding should include
  an example message or configuration.
