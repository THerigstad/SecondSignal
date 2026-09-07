# Deferred-plane fixtures

These cases came with the external review (Grok 4.6, 2026-09-01) and are kept
here on purpose: they describe behavior the product needs, on planes this
repository does not implement yet.

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

They are labeled with `"plane"` and `"runnable_here": false`, and
`tests/test_eval_cases.py` asserts they are never run as policy cases. When a
plane is built, its cases move up one directory and gain the runner's
expectations. Nothing here is deleted to make a suite green.
