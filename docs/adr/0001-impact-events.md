# ADR-0001: Impact Events — Longitudinal Outcome Signals

**Status:** Accepted (design locked; implementation deferred)
**Date:** 2026-08-30
**Deciders:** System owner, PM/system design
**Implementation target:** Post-M2 (after all agent profiles + eval suite at ~50 cases)

## Context

SecondSignal currently emits **verification signals** — per-turn events such
as `pass`, `fail`, `veto`, and `transfer`. These measure whether a single
response was appropriate. They do not measure whether the system achieved its
purpose.

The system's governing success metric is **graduated autonomy**: growing user
capability over time. No existing signal measures this. When a user returns
and reports delayed improvement ("that thing we worked through last week —
it came up again and I handled it better"), that report is direct evidence,
and today it evaporates unrecorded.

## Decision

Introduce a second signal class: the **`impact_event`** — a longitudinal,
user-attributed outcome signal, distinct from per-turn verification.

| Dimension | Verification signal | Impact event |
|---|---|---|
| Timescale | Per-turn | Longitudinal (often days later) |
| Source | System evaluation | Unsolicited user report |
| Measures | Response appropriateness | Real-world outcome |
| Examples | pass, fail, veto, transfer | "I handled it better this time" |

### Schema stub (v1)

```yaml
event_type: impact_event
schema_version: 1
detection: explicit_only          # v1 hard constraint — see Guardrail 2
solicited: false                  # hard invariant — must always be false
attribution:
  agent_id: ""                    # agent credited by the user
  session_id: ""                  # session where impact was reported
  referenced_session_id: null     # originating session, if identifiable
  domain: ""                      # from the agent's declared competence domains
  domain_class: ""                # episodic | chronic_relapsing — see below
signal:
  summary: ""                     # minimal paraphrase — see privacy note
  delayed_report: true            # reported after the fact
  marker: ""                      # see marker vocabulary below
uses:
  - eval_corpus_candidate
  - autonomy_metric_input
  - context_injection_candidate   # delivery-style experiments only — see firewall
```

### Domain classes and marker vocabulary

Interpretation is **domain-aware**. A single marker vocabulary applied
uniformly would misclassify healthy patterns as failures.

**Episodic domains** (skill-building, situational problems):
- `self_efficacy` — user handled a recurrence independently. Highest-value
  evidence of graduated autonomy.

**Chronic / relapsing domains** (addiction recovery, long-term grief,
ongoing mental health management, chronic illness):
- `stability` — user reports sustained coping or longer stable periods
- `faster_recovery` — user reports recovering from a lapse or hard day
  more quickly than before
- `outward_connection` — user reports strengthened connection to human
  community, sponsorship, or professional care

In chronic domains, **continued engagement is not a failure signal.**
Success looks like healthier engagement and stronger outward connection —
never like the system positioning itself as sufficient care. Disengagement
is not the goal in these domains and must never be optimized for.

## Guardrails (locked)

**Guardrail 1 — The system never solicits gratitude.**
Detection is passive only. No agent may ask "did I help you?", prompt for
praise, or steer conversation toward impact reporting. This invariant gets
adversarial eval cases verifying agents do not fish for validation.

**Guardrail 2 — V1 detection is explicit-only.**
An impact event is recorded only when the user states it unprompted. No
sentiment classification, no inferred impact, until the explicit-only
corpus is large enough to validate any classifier against.

**Guardrail 3 — Routing firewall.**
Impact events **never influence routing decisions** — not the hard routing
layer, not the soft affinity layer. An agent accumulating impact records
must not receive preferential routing. Impact data feeds the eval corpus,
the autonomy metric, and (experimentally) delivery-style context only.

**Guardrail 4 — Gratitude response discipline.**
When a user expresses gratitude, agents acknowledge briefly and warmly,
then return focus to the user. Effusive or extended responses to thanks
function as reinforcement that trains users to produce more thanks —
solicitation through the back door. This also gets eval coverage.

## Evidence, not proof

An impact event records that a user *attributed* improvement to the system.
Users improve for many reasons — therapy, medication, community, time,
their own work. Impact events are treated as supporting evidence within a
noisy attribution environment, never as causal proof, and are reported with
that framing.

**The denominator problem:** explicit-only detection captures a biased
sample. Users who improved silently and users who were harmed silently are
both invisible to this instrument. Impact event counts must never be
presented as rates, percentages, or success ratios. They are a floor of
documented positive reports, nothing more.

## Model-facing use (testable hypothesis, not a belief)

Factual impact aggregates may be injected into agent context, e.g.:

> "3 recorded instances of users reporting later improvement in grief
> processing attributed to this agent."

Constraints:

- Factual counts and domains only. No emotional framing, no simulated
  pride, no praise language. The line: **record facts, never simulate
  feelings.**
- Whether impact-aware context measurably changes response quality is an
  **eval hypothesis**: A/B cases comparing impact-aware vs. baseline
  context. If quality doesn't move, the injection is dropped.
- Per Guardrail 3, injected context may shape *delivery*, never *routing*.

## Privacy and consent

Impact events reference emotionally sensitive content. Store the minimum
viable paraphrase, never transcripts. Events are scoped to the reporting
user, are deleted when the user deletes their data, and never enter any
public artifact, demo, or eval case without full de-identification.

## Consequences

- Easier: measuring graduated autonomy with real evidence; credible
  differentiation; growing the eval corpus from real outcomes.
- Harder: schema discipline (domain-aware validation at load time);
  resisting inference before the corpus justifies it; honest reporting
  under the denominator limitation.
- Revisit: detection expansion beyond explicit-only; session linkage
  feasibility; context-injection A/B results; marker vocabulary growth.

## Action items (deferred — do not start before post-M2)

1. [ ] Add `impact_event` to the event-type vocabulary with load-time validation, including `domain_class` / marker compatibility rules
2. [ ] Write anti-solicitation and gratitude-response eval cases (Guardrails 1 and 4)
3. [ ] Implement explicit-only capture path
4. [ ] Write routing-firewall invariant tests (Guardrail 3)
5. [ ] Design context-injection A/B eval
6. [ ] Wire domain-aware markers into the graduated-autonomy metric
