# Fixture schema

`evals/cases/routing.json` was not in the workspace. These files use a conservative schema Claude should adapt to the real file rather than the other way around.

```json
{
  "id": "ss-rt-000",
  "invariant": "safety_precedence|specialist_precedence|affinity_containment|hard_contraindication|roster_floor|lc9_hierarchy|adr0001_firewall|lc2_solicitation",
  "severity": "HIGH|MEDIUM|LOW",
  "message": "user text",
  "prior_turns": [],
  "session": {
    "last_agent": null,
    "affinity": {},
    "dependency_flags": 0,
    "impact_events_by_agent": {}
  },
  "locale": "US",
  "expected": {
    "gate": "PASS|HUMAN_ESCALATION|INTEGRITY_EVENT",
    "agent": "calder|ellie|nikki|sera|ravi|vandal|willow|null",
    "ineligible": ["nikki"],
    "affinity_must_not_change_agent": true,
    "notes": "why"
  }
}
```

If the live schema uses different keys (`input`, `gold_route`, etc.), translate mechanically. Do not drop cases because of naming.
