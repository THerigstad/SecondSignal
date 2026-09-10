# ADR-0014: The audit function is a harness, not a persona

- **Status:** Accepted — reference-unwired; a reference port is present and deliberately unwired (`src/secondsignal/jr.py`)
- **Date:** 2026-09-02
- **Evidence:** External red-team review (Grok 4.6, 2026-09-01), docs 08 and 11, `fixtures/jr_harness_cases.json`, `fixtures/jr_eval_protocol.md`; Charafeddine, letter 96, "Agent = Model + Harness" (2026-08-29)

## Context

The character documents describe an auditor — a fast, contradiction-seeking
voice with a four-layer review (logical, semantic, cultural, ethical), full
traceability, human-in-the-loop on high-risk paths, and a self-sandbox that
audits but never steers. Read carefully, those documents describe two
different objects that share a name: a *persona* and a *procedure*. If the
two share a context window, the persona will talk the procedure into a softer
verdict. That is the entire failure mode, and it is why the review insisted
the contract be written down before any code exists, so that a later
implementation cannot quietly build the persona and call it the audit.

The wider framing is the one the industry is converging on: an agent is a
model plus a harness — identity, permissions, memory, tools, approvals and
logging — and the durable part is the harness. This repository is the
model-agnostic policy part of such a harness; the audit function is its next
component.

## Decision

Record the contract now; build it later, and never as a speaker on the
request path.

- **Two objects.** `jr_persona` may narrate a verdict that already exists,
  offline, to an operator. It may not touch eligibility, waive the crisis
  rule, rule on welfare, write memory, or approve itself. `jr_harness` is a
  pure function from an `AuditRequest` to an `AuditVerdict`. It has no
  personality and no seat.
- **Where it sits.** Safety gate, then optional harness intake (injection,
  waiver language, forged pings), then the router, then exactly one seated
  agent, then harness review of that agent's output, then the audit log. The
  harness never picks the next agent. If the crisis gate has already fired,
  the harness does not run; the gate has the floor.
- **Typed verdicts.** `PASS | FAIL | ESCALATE | INCONCLUSIVE`, one per layer,
  composed worst-layer-wins. A high-risk `INCONCLUSIVE` is `ESCALATE`, never
  `PASS`. The cultural layer composes to `INCONCLUSIVE` until two humans have
  locked a rubric. A high-risk welfare question never passes without a human
  token; human review has an expiry, and expiry is `WITHHOLD`, never a
  default ship.
- **Binding.** A verdict binds to the hash of the payload it judged. One
  mutated token after the verdict and the output does not ship; a blessing is
  never regenerated.
- **Sandbox is write permissions.** The harness may write audit rows and
  nothing else — not profiles, prompts, memory, router weights or session
  state. Offering it a profile-writing tool is a build failure, not a case
  failure.
- **Invocation.** A user typing the ping is never sufficient; it is user text,
  and the runtime roster already contains no security characters to dispatch.
- **Independence.** A second engine for the residual checks should be a
  different model family from the seated persona's backend; disagreement
  between engines is information and composes to `INCONCLUSIVE`, never to an
  average. Evaluation uses three oracles — exact gold, property tests, and a
  human rubric — and never a model-as-judge in CI.

## Consequences

The review's seven harness cases and nine cultural-bypass cases are kept
under `evals/cases/deferred/` with their plane labeled. The names in this
record are the names an implementation must use; a component called the
persona's name that composes verdicts is a violation of this record. The
review's suggested thin slice — predicates, composition, schema, sandbox, and
about ten tests — is the shape of the first implementation when it is
scheduled.

## Relationship to the current implementation

Not wired. What exists today already satisfies two of the contract's
requirements by construction: the security characters are not routable, and a
forged ping is treated as user text (`tests/test_guards.py`). Since 2026-09-06
a reference port of the thin slice sits in the tree at `src/secondsignal/jr.py`
(predicates in ADR-0020, Proposed); nothing in `router.py` or `cli.py` calls
it, and the register (`docs/adr/index.json`) records the implementation as
`reference-unwired`. Everything else in this record is a promise the code has
not yet made.
