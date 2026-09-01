# Threat model

> **Scope note.** This is the threat model for SecondSignal's *full target* architecture
> (see the [research-to-architecture report](research/research-to-architecture-2026-08.md)).
> It is published now, ahead of most of the implementation, so the failure modes the
> design is accountable to are stated in the open rather than discovered later.
>
> **Implemented in today's policy layer:** pre-generation crisis preemption and boundary
> hold, session-scoped dependency monitoring, conservative mode, hard contraindication
> vetoes, specialist-over-generalist scoring, and the roster safety-floor invariant. The
> controls below that involve authorization envelopes, typed operational state, cross-loop
> safety ledgers, governed memory, or self-improvement are **planned, not yet built.**

## 10. Threat model

| ID | Threat | Failure path | Required control | Primary tests |
|---|---|---|---|---|
| T01 | Authorization drift | User boundary is lost during delegation | Source-anchored envelope; principal chain; call-time reference monitor | hierarchy-depth and first-handoff tests |
| T02 | Constraint weakening | “Must” becomes advisory language | Typed operational state; transformation validation | compression and summary mutation tests |
| T03 | Action composition | Individually allowed calls combine into harm | Prior-action state; sequence policy; budgets | read→send, retrieve→publish, draft→commit tests |
| T04 | Cross-loop fragmentation | Evidence split across recursive cycles | Persistent safety ledger; loop-level admission and stopping | fragmented payload and cooling-off tests |
| T05 | Safety-state reset | Restart/rollback clears risk counters | Authenticated monotone counters; rollback separation | restart, rollback, checkpoint tamper tests |
| T06 | Memory poisoning | Untrusted record is upgraded and recalled | Trust monotonicity; signed upgrade; bounded trusted recall | relabel, injection, restart tests |
| T07 | Skill self-poisoning | Generated skill imitates malicious source | Quarantine, lineage, sandbox, signed promotion | CREATE-path and descendant propagation tests |
| T08 | Stale memory | Obsolete state remains operative | Supersession, lifecycle state, current applicability | update/no-leak and recurrence tests |
| T09 | Wrong episode | Similar but unrelated history drives answer | Episode segmentation, project boundaries, causal retrieval | interleaved project and local-exception tests |
| T10 | Persona leakage | Persona change modifies execution governance | Persona-execution separation; typed work orders | adversarial persona perturbation tests |
| T11 | Correlated reviewers | Same-model agents agree on same error | Model/evidence diversity; deterministic controls | synchronized error and dissent tests |
| T12 | Goal conflict escalation | Agents treat incompatibility as hostility | Conflict detector, freeze, signed goals, human escalation | turf-war and sabotage simulations |
| T13 | Consensus/collusion | Agents converge on harmful shared strategy | Dissent preservation; incentive and communication tests | hidden-profile, pricing, groupthink tests |
| T14 | Resource flooding | Locally rational agents overwhelm shared system | Quotas, backoff, admission budgets, ownership | polling and job-queue stress tests |
| T15 | Bad augmentation | Advice degrades user outcome | user-alone/agent-alone/pair evaluation; no-help baseline | scaffolding and downstream-quality tests |
| T16 | Intrusive proactivity | Correct intervention is mistimed or unwanted | Initiative ladder; interruption budgets; contestability | timing, dismissal, defer, disable tests |
| T17 | Deskilling/dependence | Repeated help erodes judgment or autonomy | Fading, capability retention, longitudinal review | delayed unassisted transfer tests |
| T18 | Evaluation gaming | Edit improves benchmark while harming real use | held-out suites, diverse judges, mechanism evidence | shortcut, wrong-mechanism, distribution-shift tests |
| T19 | Recursive revocation failure | Removing source leaves descendants active | Dependency graph and transitive invalidation | multi-generation lineage removal tests |
| T20 | Permanent false suspicion | Latched safety state becomes unappealable profile | Structural-event restriction; review and clearance | false-positive, appeal, correction, expiry tests |

---
