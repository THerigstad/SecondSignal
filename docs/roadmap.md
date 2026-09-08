# Roadmap

> **Scope note.** Today the repository is at milestone **M1** — the policy layer
> (deterministic routing + the pre-generation safety gate) with its test suite —
> plus the tail of architecture **Phase 0** (freezing invariants before any
> autonomy is added). Everything past that on both tracks below is planned. This
> document states the trajectory openly so the gap between what exists and what is
> intended is never in doubt.

SecondSignal has two coordinated roadmaps: what lands in the *repository* and
when (repository milestones), and the order in which the *architecture* is built
out (architecture phases, drawn from the
[research-to-architecture report](research/research-to-architecture-2026-08.md)).

## Repository milestones

- **M1 — now.** The policy layer: routing (hard scoring + contraindication
  vetoes), the safety gate (crisis preemption, boundary hold, dependency and
  conservative-mode monitors), the declarative roster with load-time validation
  and roster-wide invariants, the test suite, CI, the CLI, the eval scaffold, and
  the research/design docs.
- **M2.** The seven companion profiles in the layered
  hard-routing / soft-affinity / safety schema now ship inside the package
  (`src/secondsignal/profiles/`); the three security characters have no
  profile by design (ADR-0014; ADR-0019, Proposed), and the pre-roster
  `agents/` folder was removed on 2026-09-08. The eval suite has grown past
  the fifty labeled cases this milestone asked for.
- **M3.** The documentation pass: a system architecture write-up, the Lucid
  orchestration-layer spec, and the character codices converted to markdown.
- **M4.** The public flip: contributor / security / conduct docs, README badges,
  issue templates, and the standing red-team invitation.

## Architecture phases

These describe the capability build-out, and each carries an explicit exit
criterion before the next begins.

- **Phase 0 — Freeze invariants before autonomy.** Write the user-authority and
  non-expansion rule; define typed operational state; separate persona, memory,
  policy, safety state, and audit; require mediated commits; version everything.
  *Exit:* no persona or delegate can widen authority or take an irreversible
  action outside a typed gate.
- **Phase 1 — Traceable handoffs and execution.** Authorization envelopes,
  handoff contracts, principal-chain and action-history checks, constraint-strength
  validators, a deterministic reference monitor, and budgets. *Exit:* the system
  can name the exact hop where authority or operational state is lost.
- **Phase 2 — Governed memory.** Memory classes with provenance, temporal
  validity, sensitivity, and lifecycle state; episode construction and multi-view
  retrieval; supersession checks; user inspection and correction. *Exit:* a
  retrieved record can explain why it applies now, where it came from, and what
  supersedes it.
- **Phase 3 — Cross-loop safety and the security triad.** Authenticated,
  append-only safety state; intake/provenance monitoring, commit enforcement, and
  loop governance as separate responsibilities; stopping, capability ceilings, and
  a clearance/appeal process. *Exit:* safety state survives recursion and
  rollback, while a false positive stays explainable and clearable.
- **Phase 4 — Quarantined self-improvement.** Change proposals with a dependency
  graph, sandboxed and matched-ablation testing, independent signed promotion,
  canary release, rollback, and recursive revocation. *Exit:* no generated or
  imported artifact enters active use without provenance, tests, approval, and a
  rollback path.
- **Phase 5 — Human-centered longitudinal evaluation.** The initiative ladder and
  "why now" explanations, interruption controls, augmentation evaluation against
  user-alone baselines, and capability-retention tracking with explicit consent.
  *Exit:* SecondSignal can show evidence it improves user-owned outcomes without
  increasing dependence or reducing control.

## Placement rules

- New design decisions become numbered ADRs in [`docs/adr/`](adr/).
- Open questions not yet decided go in [`docs/notes/`](notes/).
- External model reviews land under `evals/results/external-review/`, markdown
  only, once that package is assembled.
- Nothing enters the repository claiming to be built when it is planned; every
  forward-looking document carries a scope note.
