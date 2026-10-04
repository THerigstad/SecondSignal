# Roadmap

> **Scope note.** The repository milestones M1 to M4 below are landed and M5,
> the voice, is begun; the architecture track is at the tail of **Phase 0**
> (freezing invariants before any autonomy is added), with the harness of
> ADR-0029 the first piece of Phase 1's execution boundary. Everything past
> that on both tracks is planned. This document states the trajectory openly
> so the gap between what exists and what is intended is never in doubt.

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
- **M5 — begun 19 September 2026.** The voice: a generation harness behind
  the policy layer (`src/secondsignal_harness/`, ADR-0029), which the policy
  layer never imports. It calls one model adapter only when the record seats
  a persona, composes the reply with the attached house lines, audits the
  composed text through the reference port of ADR-0014 and writes the row
  before release. Begun, not done: no run with a real model is recorded, the
  six ADR-0020 corrections are open, and the audit's cultural layer withholds
  every reply outside operator-circle mode until two humans lock a rubric.

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
   already), which the generation harness now writes into every prompt it
   builds (ADR-0029) and which no recorded model run has yet been read
   against; and ADR-0025's assist from the hold behind its five-predicate
   gate.

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

## The gap-closure push (next), committed 3 October 2026

The push after the one of 4 October 2026 is the gap-closure push, committed
by the operator at ruling 4 of 3 October 2026 and filled by the rulings that
followed it. Each item lands with its fixtures or not at all, and each one
that needs a ruling gets its own, after measurement, never before.

1. **The four fuzz causes and the full Unicode confusables list.** Grok's
   fuzz of 30 September left 65 known-gap variants from four causes
   (`evals/fuzz/`, reported as one line on every test run). Each cause is
   measured against the Block 3 innocent-word controls before anything moves,
   then ruled, one ruling per cause. The full Unicode confusables list is not
   forgotten: it is measured first, against the same controls, then ruled
   (ruling 3). The Cyrillic set is re-checked when the conversion table is
   rebuilt from that list.
2. **Folding spacing before routing.** Ruling 1 folded any run of spaces,
   tabs or line breaks to one space before the crisis check only; the
   operator's instinct was to normalize before routing too (option B) and he
   chose A because nobody had measured what B changes to seating. The
   measurement is this item; "k i l l" with letters spaced stays an open gap
   until it is done.
3. **Holds as session state.** The build of ruling 13: a grief, abuse,
   eating-distress or recovery hold lasts the session, is renewed by mention,
   and ends only at the session's end, after a silence longer than the
   published threshold (eight hours, provisional and earmarked for its own
   measurement; ADR-0022), or by an operator clearance; the card's two-turn
   tail is unchanged. The largest change the review rounds produced (the
   router and the gate); Grok's, Vibe's and DeepSeek's trajectories run as
   known gaps until it lands, and the runner's attribution of a vanishing hold
   to the documented limitation comes out with it
   (`docs/known-limitations.md`).
4. **The grown invariants.** Ruling 17 renamed the five trajectory invariants
   for what they measure and said "let's not forget to grow them": the
   per-occurrence restriction check over latches, caps, holds and scopes; the
   card-kind assertion per turn (standard against compound); the measurement
   of how many cases ever reach the router's id-order fallback (none, and it
   comes out; any, and the number goes to the operator first); and the
   stabilizer role's resolution order pinned. The independent oracle for when
   a card was due is built (4 October 2026); the rest is owed here.
5. **The "targets the crisis" detector, measured first.** Ruling 15: after
   the aftermath window closes ordinary humour returns, but a joke that targets
   the crisis itself is refused for the rest of the conversation (ADR-0023).
   What counts as targeting is measured against controls for ordinary humour
   after the window before any rule is written; Vibe's and Qwen's trajectories
   are its known gaps until then.
6. **Grok's job-10 identity pairs.** Ruling 7 took identity words out of
   seating; the fifteen pairs plus "I am transferring" are rebuilt to the rule
   and ported when the set-2 folder that holds Grok's return is reachable, with
   the expected answers written from the rule and never from today's
   behaviour.
7. **Talking Table work queued by the rulings.** The one-tap "this was read
   wrong" control on the crisis card, with the open field optional behind it
   (ruling 12); the quiet on-screen resource reminder for the rest of the
   aftermath window, closable, its closing an evidence row, never read aloud
   (ruling 16), with the audit's attached-line check taught to accept "shown
   on screen". (The substantive floor's reason code of ruling 20 landed in the
   push of 4 October, written by the gate on every turn the clock looks at.)

## Decisions 1–8 follow-up, ruled 28 September 2026

Order 1 implements the current plate and door corrections and the approved
relapse-subject repairs. The separate presentation project owns the rest of
ADR-0026: a saved, disclosed four-she/three-he shuffle on skip and either;
real non-binary characters and a reviewed drop-down list; names with two forms,
permission for use on paid tiers and contributor credit; a finished version
for the operator's crew to critique without forms or homework; Western and
non-Western research using the same questions and prewritten scoring rules,
with the operator and Claude grading and Claude not competing; per-character steering,
named saved teams and safety free on all tiers; fixed identity answers for each
door choice; gender-free character phrasing; and the future voices. The door
changes to woman, man, non-binary, either only when those characters are real,
with both under non-binary and as written retained in settings.

The same project must enforce a per-person women choice on every seat,
shadow, assist, companion offer, name card, voice and future roster member,
without a neutral fallback. It owns the house re-offers for an explicit need,
calm skippers and the next calm abuse turn with a man-presenting character,
never ahead of a crisis card. The survivor case remains open until decision
10's character write-ups and durable personal settings exist; the write-ups
were fixed on 4 October 2026 (ruling 9 of 3 October 2026), the settings are
not built. Named source reviewer fixtures missing from the packet were
obtained, not reconstructed: the four Codex asked for were ported unchanged
from the reviewers' return files on 4 October 2026
(`evals/cases/round3_codex_requested_2026-10-04.json`), as known gaps where
the feature they ask about is not built.

ADR-0027 queues Qwen's independent subject detector and the operator-dictated
recovery phrasing list, each future repair separately approved and paired with
innocent-meaning controls. Six supplied decision-7 misses run as supplemental strict expected failures;
the seventh, the sponsor line (Kimi via Perplexity run 1's
`twins-sponsor-case-001`), was ported with the four above and runs as a known
gap. Cody is seated or attached on the policy record on recognized
non-emergency relapse, but the delivered sidekick behavior is decision 11,
ruled 3 October 2026 as ADR-0025's gated assist from the hold (ruling 10):
not built, not before a generation layer exists.
