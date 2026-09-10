# ADR-0003: Persona and execution are separated

- **Status:** Accepted — partial; partially realized
- **Date:** 2026-09-01
- **Evidence:** Persona–Execution Separation; SHE; Bounded Agents

## Context

The characters must be free to evolve — warmer, sharper, funnier, more grounded
— without any of that changing tool permissions, audit requirements, data-egress
rules, or the definition of user consent. If persona text can reach execution
governance, a change in *tone* silently becomes a change in what the system is
*allowed to do*. That is a trust-domain violation.

## Decision

Keep the persona / deliberation domain and the execution domain in separate
trust domains, joined by a fail-closed, typed contract. A persona may interpret,
advise, dissent, and *propose* an action; a stable, faceless executor validates
that action against user authority, policy, current operational state, and
safety state before anything happens. Personas bind to capabilities by
identifier — capability logic is never copied into a persona prompt — and the
persona version used on every run is recorded so behavior can be reconstructed.

## Consequences

A contract bridge with schema validation and some overhead. Persona can still
shape the *phrasing* of allowed work, but not *whether* work is allowed. Social
engineering can still induce an allowed work order, so this is a boundary, not a
complete security story.

## Relationship to the current implementation

Partially realized, and narrowly. The decision of *who responds* already lives
outside the personas: agents are declarative data consumed by `router.py`, not
prompts that decide for themselves, and the safety gate outranks all of them.
The full governed execution runtime is planned (roadmap Phases 1–3).
