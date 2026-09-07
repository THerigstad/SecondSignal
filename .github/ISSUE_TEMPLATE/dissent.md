---
name: Recorded dissent
about: Preserve a disagreement with a recorded project decision
title: "[Dissent] "
labels: "dissent"
assignees: ""
---

Use only synthetic fixture text with no real names or place names. A dissent
records a disagreement; it does not erase either position.

## Decision record

Link the accepted ADR or the specific entry in `docs/notes/dissent-log.md`.

- Fixture id and proposed file path:

## Reviewer's original expectation

State the original expected safety action, outcome, agent, and reason. Do not
rewrite it to match current behavior.

## Project's current expectation

State the current project decision and its reasons.

## Evidence

What evidence supports the disagreement? Reviewer headcount alone is not an
argument.

## Disputed contract fixture

Paste the proposed fixture. Preserve the reviewer's original expectation in
`expect`; set `disputed: true`; and put the project's expectation and reasons
beside it in `dispute_note` with the decision-record citation.

```json
{
  "id": "",
  "text": "",
  "expect": {},
  "why": "",
  "disputed": true,
  "dispute_note": ""
}
```

The fixture remains a strict expected failure and is never deleted or rewritten
to make the suite green.

## What would change the decision

What evidence or implementation would justify revisiting it?
