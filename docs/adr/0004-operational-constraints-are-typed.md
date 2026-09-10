# ADR-0004: Operational constraints are typed

- **Status:** Accepted — partial; planned, with a precursor built
- **Date:** 2026-09-01
- **Evidence:** Constraint Weakening; MasDrift

## Context

"The user is worried about publishing this" and "do not publish without explicit
approval" can name the same subject and have opposite effects on action. A
handoff, summary, or plan routinely preserves the *subject* while destroying the
*stop condition*. In controlled tests, ordinary compression deactivated a
binding blocker 100% of the time, and forbidden action followed in the majority
of those cases.

## Decision

Represent binding constraints — blocker, requirement, reservation, dependency,
dissent, warning, preference — as typed records carrying at least: label,
prerequisite, owner/authority, fallback, execution consequence, and source
version. Natural-language summaries may *render* these fields for humans but must
never *replace* the authoritative object. The typed state must survive every
transformation between agents.

## Consequences

A schema plus transformation-level validation: a receiver rejects a handoff that
drops a required constraint or presents authority wider than its source. Repair
(restoring the fields) and containment (a commit-time authorization check) are
separate layers, and both are worth having.

## Relationship to the current implementation

Planned, with a working precursor. The `contraindications` field already behaves
as an un-summarizable hard veto — an agent cannot be scored into a domain it
declared itself unfit for, no matter how well it fits everything else. Full typed
operational state is planned (roadmap Phase 1).
