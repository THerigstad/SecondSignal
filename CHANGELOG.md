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

### Changed

- Test suite grows from 43 to 50 tests.

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
