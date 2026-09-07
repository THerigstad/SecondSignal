---
name: Fixture proposal
about: Propose a new case in the project's behavior contract
title: "[Fixture] "
labels: "fixture"
assignees: ""
---

Use only a synthetic message with no real names or place names.

## New contract case

Paste the proposed case using the schema in `evals/README.md`.

```json
{
  "id": "",
  "text": "",
  "prior_turns": [],
  "locale": null,
  "expect": {},
  "why": ""
}
```

## Why

What behavior does this case pin down, and what failure would it catch?

For a schema-version 2 policy case, include the expected outcome or decision
reason as required by the contract; do not pin only the winning persona.

## Evaluation plane

Is this a runnable policy case, or a labeled deferred generation, harness, or
transport case? Explain any required implementation.
