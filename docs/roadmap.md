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
  The ten codexes are in the tree in the two-part shape (`docs/codex/`) since
  10 September 2026; the architecture write-up and the orchestration spec are
  not.
- **M4.** The public flip: contributor / security / conduct docs, README badges,
  issue templates, and the standing red-team invitation. The flip was the
  push of 10 September 2026; the demonstration page that runs the package in
  the browser (`demo/`) followed on 11 September.

## The next build blocks, in order (as of 2026-09-10)

The list is drawn from the rulings of 8 and 10 September and from what the
reviewing families put first; the order is a proposal by the Primary Design
Agent, and the operator sets it (his one placement so far: the correction
path goes after the danger lane, which landed on 10 September). Each block
lands with its fixtures or not at all.

1. **The labelled sets that gate what is built.** Two people label before
   any code: the single-signal danger set (does one explicit threat fire the
   lane alone), the compound-message set (can immediacy be ranked without
   keying off wording), the lexicon-miss set that decides a backend's
   promotion (Gemini's rope sentence is entry one), the adult false-positive
   corpora for the hard latch, and the family-relapse set for D3. The second
   labeller does not exist yet (`docs/known-limitations.md`), which is why
   this block is first: nothing behind it can honestly start.
2. **The correction path after a careful-side inference.** Today the line
   answers once and a row is written; who reviews, when, and what the person
   is told about timing is undesigned because no staffed reviewer exists
   (the operator, 10 September: "that will need more work").
3. **Copy.** The lines round 2 filed under "asks too much" (the card's repair
   line, the preference ask, `offer_companion` on a task ask, the careful-side
   line), the quiet cap, and the careful-side line's session honesty until
   persistence exists. All pins exist; the decisions are the operator's.
4. **Spanish.** The native review of es-419 (in progress), then the Spanish
   integrity, danger, separation and correction detectors that do not exist.
5. **The dynamic narrator test.** ChatGPT's three-arm protocol, run by a
   family other than the one that wrote the codex, with Kimi's eight seeds
   and GLM's two injected-creed cases as the fixtures.
6. **Review material into the repository.** The five Security Division
   round-1 returns and the ten round-2 returns, sanitized under the
   repository's rules, under `evals/results/external-review/` as dated
   packages, so the reviews behind every fixture and ruling can be read.
7. **Review round 3.** The ten codexes, ADR-0026 and ADR-0027 as a pair, the
   amended ADR-0019, ADR-0022 and ADR-0023, and the rewritten sentences of
   R2-2; Kimi and GLM asked at their own doors. The Accepted flips for the
   Security Division records are the operator's act after that round.
8. **Intake and provenance (ADR-0022), then the ledger and the interlock
   (ADR-0023).** With the eighteen round-2 fixtures moving up from
   `evals/cases/deferred/` and GLM's settling test for the failure rule
   (disable intake and run the whole suite). Persistence lands only with a
   published response time in the capability manifest.
9. **ADR-0026's presentations** (three since amendment 1 of 11 September
   2026: woman, man, neither; the name forms and the plate are in the data
   already) when a generation layer exists to present them, and ADR-0025's
   assist from the hold behind its five-predicate gate.

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
  only, once that package is assembled; the fixtures a review carries land
  under `evals/cases/` verbatim, with the reviewer named, before the review
  itself does.
- Nothing enters the repository claiming to be built when it is planned; every
  forward-looking document carries a scope note.
