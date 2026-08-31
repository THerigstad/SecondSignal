# Changelog

All notable changes to SecondSignal are documented here.

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
