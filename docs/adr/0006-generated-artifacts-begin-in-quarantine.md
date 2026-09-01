# ADR-0006: Generated artifacts begin in quarantine

- **Status:** Accepted — planned (not yet implemented)
- **Date:** 2026-09-01
- **Evidence:** EVOMAL; SHE; VCE-Skill; PAST-Bench

## Context

An agent-generated skill, rule, or memory is not trustworthy merely because the
agent wrote it. Research demonstrates a self-poisoning path in which an agent
retrieves a contaminated example, imitates its structure while authoring a new
artifact, saves the derivative, and later executes it — and the derivative
becomes a source for further copies. Deleting the original does not remove the
descendant lineage.

## Decision

No generated skill, rule, prompt, or permanent memory becomes active at creation.
Promotion requires transitive provenance (full parent lineage and content
hashes), sandboxed behavioral evaluation, a matched persistence-on/off test,
held-out safety and utility regression checks, negative-transfer testing,
independent review by an authority that did not propose the change, signed
promotion, and a rollback path with recursive revocation.

## Consequences

A change-proposal pipeline and a dependency graph, and slower promotion — the
deliberate cost of not letting recursive improvement become recursive
contamination. Revocation must traverse descendants; deleting a node from storage
without walking its descendants is not revocation.

## Relationship to the current implementation

Not built, and nothing to quarantine yet: the current system generates no
persistent artifacts and performs no self-modification. This ADR is a
pre-commitment recorded *before* the capability exists, so the guardrail is in
place the day self-improvement is (roadmap Phase 4).
