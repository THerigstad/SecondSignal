# ADR-0008: Human value is evaluated separately from autonomous performance

- **Status:** Accepted — partial; partially realized
- **Date:** 2026-09-01
- **Evidence:** CentaurBench; Unaccountable Delegation; Human-Centered Proactive Agents

## Context

A model can be an excellent task-solver and a poor assistant; the two abilities
correlate only weakly. Assistance can *reduce* the outcome the person would have
reached alone, and engagement or reliance are dangerous proxies for benefit — a
system optimizing them will look successful while making the user worse off.

## Decision

Measure SecondSignal against user-alone baselines where feasible, and treat the
success criterion as: *the person leaves with more capability, clarity, agency,
authorship, or footing* — not an impressive answer and not a stronger attachment
to the system. Growing dependence is a failure signal, not an engagement win.
"No intervention" is allowed to beat poorly matched intervention. These measures
must be transparent and user-controlled, never covert engagement optimization.

## Consequences

Requires human-value evaluation dimensions — voice preservation, decision
ownership, contestability, cognitive burden, capability retention, dependence —
alongside task metrics, and the honesty to report when the unaided person did
better.

## Relationship to the current implementation

Partially realized. Two mechanisms already encode this stance: the session
**dependency monitor** treats accumulating reliance as something to interrupt
rather than reward, and the M2 profile spec carries an explicit **graduation
metric** — the user self-regulates earlier and comes back to say so, rather than
to be caught. The full augmentation evaluation with user-alone baselines is
planned (roadmap Phase 5).
