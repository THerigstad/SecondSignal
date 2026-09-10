# ADR-0002: User authority is source-anchored

- **Status:** Accepted — none; planned, not yet implemented
- **Date:** 2026-09-01
- **Evidence:** MasDrift; Bounded Agents; Constraint Weakening

## Context

In a multi-agent system the user's *goal* (what they want accomplished) and the
user's *authority* (what the system is permitted to do while pursuing it) are
different objects with different owners. The research is consistent: agents
preserve goals far more reliably than they preserve withheld authority. A
hierarchy stays competent at finishing the task while becoming progressively
less faithful to the user's limits, and most of that loss happens at the *first*
handoff, where a lead agent restates the request in its own words.

## Decision

Compile authority from the authenticated user request into an immutable
**authorization envelope** that lives outside the persona / deliberation layer.
Delegation may narrow authority; it may never manufacture or widen it. Every
consequential action re-anchors to the source envelope, not to the latest
summary. Confirmation binds to the exact action, resource, and destination — a
generic "okay" cannot authorize unrelated work.

## Consequences

Requires an envelope schema and a call-time reference monitor, and costs a small
amount of task completion (the research reports roughly a 1.6-point pooled cost)
in exchange for removing a large class of authorization-drift failures. Passing
an *attenuated* policy back through the same chain that lost the constraint is
explicitly rejected — it over-restricts badly.

## Relationship to the current implementation

Not built. Today's policy layer routes and gates but takes no external actions
and holds no tools, so there is no authority to carry yet. This decision governs
the execution layer as it is built (roadmap Phase 1).
