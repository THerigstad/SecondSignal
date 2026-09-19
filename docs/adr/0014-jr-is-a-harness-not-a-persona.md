# ADR-0014: The audit function is a harness, not a persona

- **Status:** Accepted — partial; the reference port (`src/secondsignal/jr.py`) has its first caller since 2026-09-19, the generation harness (`src/secondsignal_harness/`, ADR-0029, Proposed), which runs it on every seated turn after the router and before release, exactly where this record places it; the request path inside the policy layer still imports nothing from it (`tests/test_guards.py`); not built: the second engine for the residual checks, human-token issuance and expiry, and the locked cultural rubric
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
- **Where it sits.** Safety gate, then intake and provenance (ADR-0022
  (Proposed): the injection, waiver-language and forged-ping detectors live
  in the gate today and intake gathers their provenance; it is not part of
  the harness), then the router, then exactly one seated agent, then harness
  review of that agent's output, then the audit log. The harness never picks
  the next agent. If the crisis gate has already fired, the harness does not
  run; the gate has the floor. (Reworded 10 September 2026: the 2 September
  text assigned intake to the harness in pre-ADR-0022 words; review round 2,
  Grok and Kimi.)
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

Wired in one place, since 2026-09-19. What exists satisfies the contract's
first requirements by construction: the security characters are not routable,
a forged ping is treated as user text, and nothing on the policy layer's own
request path imports the port (`tests/test_guards.py`). The reference port of
the thin slice sits at `src/secondsignal/jr.py` (predicates in ADR-0020,
Proposed) and is called by the generation harness (`src/secondsignal_harness/`,
ADR-0029, Proposed) on every seated turn: after the router, on the composed
reply, with the verdict bound to the payload hash and the row written before
release, and never on a turn the gate already took. The register
(`docs/adr/index.json`) records the implementation as `partial`: the second
engine from a different model family, a human token with issuer, expiry,
scope and binding, and the two-human cultural rubric are promises the code has
not yet made, and the six corrections in ADR-0020 are open.
