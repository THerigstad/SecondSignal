# ADR-0035: The harness is a versioned part of the system

- **Status:** Proposed — built; the record, audit stamps, material change chain and lifecycle integration are implemented; independent review and a human-readable rendering remain future work
- **Date:** 2026-11-04
- **Evidence:** the four regression modules listed below.

```text
tests/test_hm2_spec.py
tests/test_hm2_harness.py
tests/test_hm2_table.py
tests/test_hm2_results.py
```

- **Depends on:** ADR-0013, ADR-0014, ADR-0029 (Proposed), ADR-0030 (Proposed)

## Context

A model name alone cannot identify the system that produced a reply. Its
configuration also includes the routing boundary, guidance, permissions,
checks, retained state and runtime. H1 records configuration on individual
audit rows; a sitting needs a record of the configuration in force and the
changes made while it runs.

The source of the structure is Gertler, Novelli and Floridi, *Towards
Portable Specification of the Agent Harness*, Digital Ethics Center, Yale
University. This decision uses its model pairing, eight components and five
records. It does not adopt a new policy or add model authority.

## Decision

Treat the harness as a versioned part of the system. `spec.py` builds its
machine-readable record from H1 configuration, code constants and governing
file hashes. The fixed component order and required reasons are validated.
Release, declared changeable, run start, material changes and run end are
always present, including explicit empty records when appropriate.

Use the existing J.R. `payload_hash` operation for sorted JSON. Apart from
the hash's own field, its existing top-level `ranked` exclusion is retained;
no new timestamp exclusion is invented. Logical sitting-turn intervals make
identical configurations reproducible. Audit rows retain their existing
wall-clock timestamps. Requested model identity and host-reported identity
remain separate; an unknown report is null, and a first observation does not
claim the model was known before it answered.

The harness audit schema becomes v2. Every row binds its active specification
hash, sitting turn ordinal and material event id, including explicit null
when no event applies. A mismatched stamp raises. The policy record, its
schema, its digests and its decision rules do not change.

Material changes retain old and new values, requester, authorisation, turn
interval and reversal information. Their log is append-only through its
public interface, chained by SHA-256 and checked on read. A separate durable
head receipt detects a missing tail. Closing or reversing an interval adds
a record rather than editing an earlier event. The Table records successful
operator controls, retains one sitting through settings changes and records
an end on Reset, shutdown or the quiet boundary. Canceled jobs cannot commit
a new model identity. Crisis delivery does not wait for specification disk
writes; the Table queues that persistence and reports any failure.

New evaluation output has a required specification-hash header. An explicit
absent marker is allowed with a not-reproducible label. Historical result
files retain their exact bytes. No persona or model call gains an interface
to change the gate, latch, holds, predicates, guidance or version strings.

## Consequences and limits

The source record is JSON. This ADR explains the decision; it is not the
human-readable specification. A later order will generate that document
from JSON so that two separately maintained descriptions cannot drift.

The program that writes the event log can still rewrite the files. The chain
is tamper-evident, not tamper-proof, and a coordinated rewrite of both the
log and its local receipts needs an independently retained anchor to expose
it. The record is not self-enforcing. Runtime remains partial: reload
recovery, timeouts, retries and bounded Table concurrency exist; durable
full-transcript recovery and interrupted-call checkpoint/resume do not.

## Falsifiers

A missing or renamed component, an unexplained partial component, an unhashed
field, a conflated model identity, a missing or mismatched row stamp, a broken
event chain, a result without its required header, a model-granted control,
or a changed policy decision fails the corresponding tests. Existing replay
fixtures and package byte pins remain explicit evidence of the boundary.
