# ADR-0005: Safety state is separate from personal memory

- **Status:** Accepted — partially realized
- **Date:** 2026-09-01
- **Evidence:** Safety Does Not Compose; Reversible Forgetting; Human-Centered Proactive Agents

## Context

Two failures pull in opposite directions. Cross-loop attacks hide by splitting
decisive evidence across iterations, so a monitor that only sees one iteration
cannot catch them — some structural risk must persist and latch. But blindly
retaining a permanent risk score creates the opposite harm: one false alarm
becomes indefinite restriction, or a quiet, unappealable judgment about the
person.

## Decision

Keep a separate, tamper-evident **safety ledger** for *verifiable structural
events* (invalid authorization, rejected re-entry, provenance failure, memory
integrity failure), with review, appeal, expiry, and clearance. Latch structural
facts — never vague suspicion or an emotional interpretation. Personal memory and
safety state cannot silently contaminate each other, and security state must
never be converted into a diagnosis, personality judgment, or permanent profile
entry.

## Consequences

Two stores with different lifecycles and a due-process path. Trust may be
downgraded automatically but requires signed authority to upgrade; a rollback of
ordinary state must not reset the safety counters.

## Relationship to the current implementation

Partially realized. The safety gate is already a distinct layer that runs
*before* routing and holds precedence over it (`safety.py`), and session risk
signals (dependency accumulation, conservative mode) are kept apart from routing
scores. The persistent cross-loop ledger and the clearance/appeal process are
planned (roadmap Phase 3).
