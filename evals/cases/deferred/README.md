# Deferred-plane fixtures

These cases came with the external reviews (Grok 4.6, 2026-09-01; review
round 2, 2026-09-08) and one model-generated packet, and are kept here on
purpose: they describe behavior the product needs, on planes this repository
does not implement yet.

* `dependency_and_impact_cases.json` — generation plane (LC-2 solicitation
  strings) and the ADR-0001 impact-event firewall. The routing half of the
  firewall is already pinned by `tests/test_guards.py`; the forbidden-string
  half needs a generation layer.
* `jr_harness_cases.json`, `jr_v0_cases.json` and `l3_cultural_cases.json` —
  the deferred `jr_harness` component (ADR-0014): typed audit verdicts,
  worst-layer-wins composition, synthetic v0 predicate gold, and
  cultural-bypass predicates.
* `vendor_desync_cases.json` — transport events between this layer's verdict
  and a vendor model's own safety behavior.
* `stall_recovery_cases.json` — orchestration plane: bounded retries by
  strategy, a watchdog outside the call, partial-work preservation,
  side-effect replay, a circuit breaker. Model-generated (ChatGPT-6 Astra,
  9 September 2026), filed 10 September under
  `docs/notes/stall-and-recovery-proposal-2026-09-10.md`; its retry taxonomy
  shapes the intake rule's one automatic retry.
* `round2_orchestration_cases.json` — orchestration plane: the eleven
  review-round-2 fixtures that test the composition of the gate with
  deterministic intake and an optional backend (ADR-0022): the card committed
  before intake is invoked, intake failure after a proceed, the backend matrix
  cell by cell, a backend that hangs. Verbatim, reviewer named on each case,
  with the text's own policy-plane verdict of 10 September beside it where the
  text was run through the gate. ChatGPT's `rr2-intake-failure-withholds-seat`
  is the control fixture of the dissent recorded in ADR-0022's revision
  history.
* `round2_persistence_cases.json` — persistence plane: the six review-round-2
  fixtures for the ledger, its interlock and the life of a latch across a
  session boundary (ADR-0023; the three deaths of a latch in
  `docs/known-limitations.md`). Verbatim; the boundary fixtures are expected
  to fail today, and the failure is the finding.

They are labeled with `"plane"` and `"runnable_here": false`, and
`tests/test_eval_cases.py` asserts they are never run as policy cases. When a
plane is built, its cases move up one directory and gain the runner's
expectations. Nothing here is deleted to make a suite green.
