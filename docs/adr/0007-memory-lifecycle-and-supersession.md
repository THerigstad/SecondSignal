# ADR-0007: Memory is episodic, versioned, and lifecycle-governed

- **Status:** Accepted — planned (not yet implemented)
- **Date:** 2026-09-01
- **Evidence:** SCALE-QA / TSIM; PAST-Bench; Reversible Forgetting

## Context

"In memory" must not mean "eligible to steer every answer forever." The research
catalogs distinct memory failures: retrieving a similar-but-wrong episode,
leaving obsolete state active, treating a generic rule as stronger than a local
exception, and recalling a fact while losing its authority, sensitivity, or
present applicability. A better answer is also not proof that memory *caused* it.

## Decision

Memory records carry class, content, provenance, temporal validity, current
applicability, sensitivity, supersession links, and a lifecycle state — active,
dormant, retired, or deleted. Retrieval reconstructs the *episode* that makes a
constraint operative (semantic/causal segmentation, evidence-first ranking, a
supersession check before use), not just a similar sentence. Agent inference
defaults to unconfirmed and never becomes a durable sensitive personal fact
without user confirmation. Deletion is a separate legal/technical process, not a
side effect of dormancy.

## Consequences

Richer than a vector store, and a claim that the system "learned" must be backed
by a matched persistence-on/off comparison. No automatic process retires or
deletes high-sensitivity personal memory on a model's prediction of irrelevance
alone.

## Relationship to the current implementation

Not built. The current layer holds only session-scoped state — turn count,
accumulated dependency signals, conservative mode (`SessionState`) — and no
persistent cross-session memory. This ADR governs memory when it is built
(roadmap Phase 2).
