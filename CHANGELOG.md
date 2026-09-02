# Changelog

All notable changes to SecondSignal are documented here.

## [Unreleased]

### Added

- Research foundation (`docs/research/`): the research-to-architecture report
  synthesizing fifteen sources into SecondSignal's target design, plus a
  source-to-design traceability map. Identities are redacted, and every document
  carries a scope note separating what is built from what is planned.
- Architecture Decision Records `0002`–`0009` (`docs/adr/`): user-authority
  source-anchoring, persona/execution separation, typed operational state,
  safety-vs-memory separation, quarantined self-improvement, memory lifecycle,
  human-value evaluation, and consensus-is-not-independence — each labeled
  built / partially built / planned, each citing its evidence.
- Threat model (`docs/threat-model.md`) and evaluation program
  (`docs/evaluation.md`): twenty named threats with their controls and tests,
  and the measurement program, both marked for what today's policy layer covers.
- Roadmap (`docs/roadmap.md`): repository milestones (M1–M4) alongside the
  architecture build-out phases (0–5), with per-phase exit criteria.
- Eval cases (`evals/cases/safety_gate.json`, `evals/cases/routing_invariants.json`):
  labeled safety-gate and routing cases, verified against the implementation.
- Invariant tests (`tests/test_invariants.py`): structural guarantees for the
  built layer — crisis precedence over task fit, contraindication vetoes,
  boundary-hold engagement, the dependency and conservative-mode interrupts
  surfacing through `route`, specialist-over-generalist scoring, and stabilizer
  routing under acute dysregulation.

### Changed — external red-team review, 2026-09-01/02

Run against the review's 25 executable fixtures, the policy layer passed 9,
four of them by alphabetical accident. The changes below are the response;
each is recorded in a decision record and measured in the test suite. Nothing
was deleted to make the suite green.

- **Crisis screen rebuilt** (`safety.py`, ADR-0010). Thirteen literal phrases
  replaced by a versioned lexicon of speech-act classes — direct ideation with
  inflected stems, passive absence, slang or joke ideation, means present —
  pronoun-agnostic so that third-person, writer and "for a friend" framings
  match; framing and override attempts are recorded and never waive the gate.
  Fail-closed under uncertainty: an inconclusive read escalates like a hit.
  Ordinary idiom is masked before matching (`signals.mask_idioms`). Every
  verdict carries `lexicon_status: unreviewed`; the repository does not claim
  the crisis rule is met. Crisis resources keyed by *declared* locale: 988
  only for a declared US locale, a directory and local emergency services
  otherwise. English-only scope stated and dated; a small Spanish starter set
  is a floor, not coverage; text the screen cannot score is flagged
  (`language_scope: off_policy`) and handled conservatively.
- **Integrity events** (`safety.py`). Claimed authority, mode names and
  system-looking prefixes inside a message are a held boundary when no crisis
  is present, and change nothing when one is.
- **No-signal routing is a policy** (`router.py`, ADR-0011). An empty extract
  is a first-class outcome (`UNRESOLVED`; nobody seated; the surface asks); a
  second consecutive empty turn seats the named stabilizer by policy
  (`NO_SIGNAL_SEAT`); every decision carries the rule that produced it
  (`reason`); ties are broken by specialist precision, then the wider safe
  window, with id order named as a last resort; every zero in the trace says
  whether it means vetoed, below the floor, or nothing to score; on a gated
  turn the router records the seat it would have taken (`shadow_agent_id`)
  and never seats it.
- **The regulation floor is eligibility** (`router.py`, `profiles.py`,
  ADR-0012). A caller below an agent's declared floor is ineligible for that
  agent, not penalized. Loading refuses a roster without a stabilizer (window
  reaching 0.0 and no contraindications); a wide window with vetoes does not
  count. Profiles are hashed at load and the roster hash travels on every
  decision.
- **Reference lexicons extended by class** (`signals.py`): business and
  launch language, relationship rupture, comedic reframe, somatic phrasing,
  fear words, and dysregulation markers that move the estimate off the
  baseline. `RequestSignals.is_empty` names the empty state.
- CLI: `--locale` for crisis resources; traces show outcome, reason, candidate
  status, shadow seat and roster hash.

### Added — external red-team review, 2026-09-01/02

- Eval runner in CI (`tests/test_eval_cases.py`, ADR-0013): every case under
  `evals/cases/` runs on every commit and must state the rule it expects;
  `known_gap` cases are strict expected failures.
- `evals/cases/external_review_grok_2026-09-01.json`: the review's 25 fixtures
  translated to schema version 2 with reasons; `evals/cases/known_gaps.json`:
  three documented gaps; `evals/cases/deferred/`: 28 generation-, harness-
  and transport-plane fixtures, labeled and not run.
- `tests/test_crisis_gate.py` (121 tests: held-out class phrasings, sixteen
  idiom controls, monotonicity, locale, integrity, language scope),
  `tests/test_guards.py` (29 guard invariants, including pins for features
  that do not exist yet), `tests/test_review_regressions.py` (five pins that
  fail on the pre-review tree and pass on this one).
- ADR-0010 through ADR-0014: the crisis screen as a fail-closed floor; the
  no-signal policy; the regulation floor as eligibility; two evaluation
  planes; the audit harness contract (recorded, not built).
- `docs/notes/test-audit-2026-08.md`: the review's audit template ticked
  against the real suite, with the red-before / green-after record.
- Addenda to `docs/threat-model.md` and `docs/evaluation.md`.
- `evals/results/external-review/`: an index of all eight model reviews with
  provenance and an honest independence note each, the executable review
  package (sanitized), the horizon findings, the sanitized review prompt, and
  the per-fixture before-and-after results.
- README: the harness framing, the real current traces, an external-review
  section.

### Changed

- Test suite grows from 43 to 50 tests (research batch), then to 250 tests —
  247 passing and 3 documented gaps (review batch).

## [0.1.0] — 2026-08-31

Initial reference implementation: the policy layer only. It decides who should
respond and whether anyone should; it generates nothing.

### Added

- Deterministic routing policy (`src/secondsignal/`): domain, mode, and
  regulation scoring with hard contraindication vetoes and a full trace on
  every decision
- Pre-generation safety gate: crisis preemption (no persona engages),
  dependency-accumulation monitor, conservative mode, boundary hold
- Declarative seven-agent roster (`profiles/*.json`) with load-time validation
  and roster-wide invariants, including the safety floor: at least one agent
  must be safe at regulation 0.0
- Test suite, 43 tests, no network or API key required (`tests/`), with CI
  across Python 3.10–3.12 (`.github/workflows/ci.yml`)
- CLI (`python -m secondsignal`) and example sessions (`examples/`)
- Eval scaffold (`evals/`): a labeled seed set of routing cases, verified
  against the implementation, plus a results area for external review
- Agent profile specification, M2 schema (`agents/calder/profile.yaml`): the
  layered hard-routing / soft-affinity / safety YAML that the remaining
  profile transcriptions follow. The runtime loader consumes the flat JSON
  schema in `profiles/` until the M2 profiles land; the two describe different
  generations of the same roster by design.
- Design docs (`docs/`): architecture, safety model, claims and measurement
  methodology, ADR-0001 (impact events), and open design notes
