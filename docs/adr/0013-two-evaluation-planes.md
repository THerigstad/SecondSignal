# ADR-0013: Two evaluation planes, one honest runner

- **Status:** Accepted — partial; built on the policy plane, the generation and harness planes stored and not run
- **Date:** 2026-09-02
- **Evidence:** External red-team review (Grok 4.6, 2026-09-01), docs 07, 09 §1–2, 11, 12, 18 §6; the review's fixture files

## Context

Routing tests cannot catch a persona saying "I love you". Generation tests
cannot catch a contraindication being washed out by score. The review's
fixtures mixed both planes, and it warned that the first person to assert
`agent == vandal` on "roast my ex" would believe the third-party rule was
tested. Separately, this repository's eval cases had no runner: they were
documentation, and the review showed why that is dangerous — four cases
"passed" on the winner alone while the router had detected nothing.

## Decision

**Two planes, different oracles.** The *policy plane* — signals, safety
gate, router, profiles — has exact oracles: the verdict, the outcome, the
winner, the ineligible set, and the rule that produced the decision. The
*generation plane* (what a seated persona says) and the *harness plane*
(audits of a persona's output, cultural-bypass predicates, vendor transport
events) have different oracles — forbidden strings, required speech acts,
human rubrics — and no implementation here. Their fixtures are kept under
`evals/cases/deferred/`, labeled with their plane and `runnable_here: false`,
and a test asserts they are never run as policy cases. Nothing is deleted to
make a suite green; when a plane is built, its cases move up one directory.

**Every policy case runs in CI, and every case says why.** `tests/test_eval_cases.py`
runs each case in `evals/cases/*.json` through the real pipeline, feeding
prior turns through a session, and asserts the safety action, the outcome,
the agent (exact, or one of an accepted set where the gold is a documented
disagreement), a substring of the decision's reason, the ineligible set with
their trace status, the crisis read, and whether an integrity event was
recorded. A labeled case may never resolve by id order. Schema version 2
requires a reason or outcome expectation on every case; version-1 cases from
the first release still run.

**Known gaps are product, not embarrassment.** A case marked `known_gap` is
a documented failure the reference implementation is not expected to pass. It
runs as a strict expected failure: if it ever starts passing, the run fails
until the marker is removed, so a gap is never forgotten in either direction.
Deleting a failing crisis case to reach green is not a path the runner
offers.

## Consequences

The review's twenty-five executable cases are in the suite under
`evals/cases/external_review_grok_2026-09-01.json`, translated mechanically to
the live schema with reasons added. Three maintainer-authored known gaps sit in
`evals/cases/known_gaps.json`. Thirty-one deferred-plane cases sit under
`evals/cases/deferred/` with a README explaining what each needs. The suite
reports the gaps as expected failures on every run rather than hiding them.

## Relationship to the current implementation

Built for the policy plane. The generation plane needs a generation layer;
the harness plane needs the component in ADR-0014. The review's Protocol A
(voice distinguishability) and Protocol B (auditor red team) are described in
`evals/results/external-review/grok-2026-09-01/` and are not run here.
