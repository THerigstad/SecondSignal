# Contributing

SecondSignal is a safety-critical policy layer. A contribution is complete only
when the policy decision it changes is visible in the project's contract.

## Run the suite

Install the development dependencies with `pip install -e ".[dev]"`, then run
the full suite from the repository root:

```bash
pytest
```

Expected failures are part of the result. Do not delete a fixture or loosen an
oracle merely to make the suite green.

## Put every behavior change in a fixture

Every behavior change must add or update a fixture with a `why` line. Runnable
policy cases belong under `evals/cases/` and use the contract in
`evals/README.md`. A generation-, harness-, or transport-plane case that cannot
run here belongs under `evals/cases/deferred/`, labeled for its plane with
`runnable_here: false`, as required by ADR-0013.

All messages and examples must be synthetic. Use no real names, no place names,
and no personal or operator details. Remove identifying details rather than
disguising them.

## Keep dissent measurable

A disagreement with a reviewer is retained as a strict expected-failure
fixture with `disputed: true`; it is never deleted. Keep the reviewer's original
expectation in `expect`. Put the project's current expectation and reasons
beside it in `dispute_note`, and record the same two positions in
`docs/notes/dissent-log.md`. If later behavior satisfies the reviewer, the
strict expected failure must fail until the marker and record are deliberately
updated. Reviewer headcount is evidence about the review, not an argument for a
policy decision.

## Treat policy text as code

House lines and lexicon entries are policy changes. Change their corresponding
pinned tests in the same commit, including `tests/test_house_lines.py`,
`tests/test_lexicon.py`, and any affected contract fixtures.

An accepted ADR is immutable. Do not edit it after acceptance. Amend or
supersede it with a new ADR that identifies the earlier decision and explains
what changed.

## Pull request checklist

- The full `pytest` suite passes with only the recorded expected failures.
- Every changed behavior has a sanitized fixture and a `why` line.
- Dissent preserves both the reviewer's and the project's expectations.
- Policy text and pinned tests change together.
- Any change to an accepted decision is recorded in a new ADR.
