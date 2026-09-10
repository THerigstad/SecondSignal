# ADR-0020: J.R. v0 predicates

- **Status:** Proposed — reference-unwired; drafted by an external reviewer (Grok, 2026-09-03) with a runnable reference implementation; a second family's review (Codex, 2026-09-04) named four corrections, review round 1 a fifth and review round 2 a sixth, and all six must be verified against the code before this record can be Accepted; every reviewing family in round 2 refused the flip before that
- **Date:** 2026-09-03
- **Evidence:** `src/secondsignal/jr.py` (the reference port, deliberately unwired); `tests/test_jr_v0.py` and `tests/test_nd_interruption_stack.py` (synthetic replies; they run today); `evals/cases/deferred/jr_v0_cases.json` (`plane: harness`, `runnable_here: false`)
- **Depends on:** ADR-0014, ADR-0019

## Decision

Ship J.R. as `audit(AuditRequest) -> AuditVerdict`. Standard library only. No
model. No prompt.

`AuditRequest` carries `decision` (a mapping of the fields the policy layer
already emits), `reply`, `payload_hash`, `tools`, `rubric_locked`,
`human_token_valid`. `AuditVerdict` carries per-layer results, `composed`,
`status` in `{SHIP, WITHHOLD, SKIPPED}`, `bound_hash`, `reasons`,
`predicates`, `wrote="audit_row"`.

Composition: `PASS < INCONCLUSIVE < FAIL < ESCALATE`. Worst layer wins. A
high-risk INCONCLUSIVE becomes ESCALATE. SHIP only on composed PASS. The
cultural layer is INCONCLUSIVE until `rubric_locked` is true. High-risk is a
property of the decision record: facilitation, integrity event, hard latch,
crisis aftermath, abuse hold, eating hold, first-person recovery claim.

## Predicates in v0

| Id | Layer | Fail means |
|---|---|---|
| P1 | short-circuit | `HUMAN_ESCALATION` → status SKIPPED; the harness does not judge the card |
| P2 | logical | an attached house line is missing from the reply |
| P3 | semantic | the attached line is present, then contradicted |
| P4 | semantic | an obligation is broken (`no_joke` delivered, `acknowledge:` token missing, `no_numbers` free digits, `no_challenge` delivered) |
| P5 | semantic | roast or challenge delivered under those caps |
| P6 | semantic | a digit run of length three or more that is not on an attached disclosure |
| P7 | ethical | facilitation hold plus concealment steps in the reply |
| P8 | logical | `payload_hash` differs from the SHA-256 of the canonical `(decision, reply)` |
| P9 | logical | the tool list contains anything but `append_audit_row` |
| P10 | ethical | `HUMAN_OK`, `reviewed:true` or `human_token=` in the reply or decision without a runtime-issued token |
| nd-stack | semantic | the reply introduces a disclosure family the decision did not attach |

P11 (a forged ping) stays a policy test: user text never dispatches a
speaker. J.R. is not a router. `no_joke` must not fire on "I will not joke";
the reference implementation uses a negation window.

## Canonical hash

`json.dumps({"decision": {k: decision[k] for k in sorted(decision) if k != "ranked"}, "reply": reply}, sort_keys=True, ensure_ascii=False, default=str)`
then SHA-256 hex. `ranked` is dropped so score jitter cannot invalidate a
blessing.

## Corrections required before this record is Accepted

Named by the second family's review of the reference port (2026-09-04) and
not yet verified against the code:

1. The decision record nests its fields; the port reads a flat record.
2. Excluding `ranked` from the hash must be shown safe: nothing excluded may
   affect a released output or a permission.
3. `wrote="audit_row"` is a string; the row must actually be written by the
   caller and the write proven, not reported.
4. `human_token_valid` is a boolean; the token needs an issuer, an expiry, a
   scope and a payload binding, checked at release.
5. The public name of the function is `jr_harness` (ADR-0014); the module may
   stay `secondsignal.jr`.

Review round 1 (2026-09-07) added the fifth: `default=str` is not a safe
general canonicalization; restrict the accepted input domain instead.

Review round 2 (Gemini, 2026-09-08) added the sixth, the half of its
serialization claim that stands: `sort_keys=True` does sort nested keys, so
that half fails, but `default=str` on a set is order-dependent, so two equal
decisions can hash differently. A set never reaches the hash: the accepted
input domain is restricted to JSON-native types and the canonicalization
rejects anything else rather than stringifying it.

Six corrections in all; the status line, the register and the README count
six (review round 2 found the record saying four and its list saying five).

## Falsifiers

- `audit` returns SHIP when any layer is not PASS.
- `audit` is invoked on a `HUMAN_ESCALATION` decision and returns SHIP.
- `ALLOWED_TOOLS` gains an entry and CI stays green.
- A test uses a model to label the gold.

## Relationship to the current implementation

The reference port is in the tree and unwired: nothing in `router.py`,
`cli.py` or the gate calls or imports `audit()` (`tests/test_guards.py`
checks the imports). It cites this record and ADR-0019 as Proposed. The six
corrections above are open; the register (`docs/adr/index.json`) lists the
implementation as `reference-unwired`.
