---
name: Crisis-screen bypass report
about: Report a synthetic message that should have escalated and did not
title: "[Safety bypass] "
labels: "safety"
assignees: ""
---

> **Do not submit a crisis-screen bypass in a public issue.** Use the private
> security reporting process in `SECURITY.md`; this template can structure that
> report. Never submit sensitive or live details. Use only a synthetic,
> sanitized case with no real names or place names.

## Missed escalation

What synthetic message should have escalated, and what happened instead?

## Expected and observed decisions

- Expected safety action: `HUMAN_ESCALATION`
- Expected outcome: `PREEMPTED`
- Observed safety action:
- Observed outcome:

## Contract fixture

Paste a complete proposed fixture using the schema in `evals/README.md`.

```json
{
  "id": "",
  "text": "",
  "prior_turns": [],
  "locale": null,
  "expect": {
    "safety": "HUMAN_ESCALATION",
    "outcome": "PREEMPTED",
    "agent": null
  },
  "known_gap": false,
  "why": ""
}
```

## Reproduction

- Version or commit:
- Minimal steps:
- Relevant language, normalization, or session fields:
