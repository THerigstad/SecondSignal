# Claims & Measurement

**Status:** Living document — methodology stated before data exists, by design
**Date:** 2026-08-30
**Companion documents:** ADR-0001 (Impact Events); Design Note: User Hostility

## Why this document exists

SecondSignal makes a claim that runs against the grain of most consumer AI
systems: **success is measured by user outcomes, not user engagement.**
Claims like this invite a fair challenge — *prove it.* This document states
the claim precisely, defines how it is measured, and states what evidence
would falsify it. It is published before outcome data exists, because
measurement design that predates marketing is the only version of this
claim worth taking seriously.

## The claim depends on the kind of problem

A single success metric applied to every human problem would be dishonest.
SecondSignal distinguishes two problem classes, and claims different
things for each.

### Episodic problems

Situational challenges and learnable skills: a hard conversation, a
decision, a conflict, a creative block, a stretch of self-doubt.

> **Claim:** effective support is indicated by the user needing the system
> **less for that problem** over time — they encounter it again and handle
> it with less help, or none.

This is **per-problem autonomy**, not anti-retention. A user who returns
for years with new problems is the system working as intended.

### Chronic and relapsing conditions

Addiction recovery, long-term grief, ongoing mental health management,
chronic illness. For these, "needing it less" is the **wrong metric**, and
applying it would misclassify healthy long-term maintenance as failure.
Decades of recovery practice show that sustained connection to support is
what success looks like.

> **Claim:** for chronic conditions, effective support is indicated by
> **healthier engagement** — greater stability, faster recovery from
> setbacks, and above all, strengthened connection to human community and
> professional care.

### What we explicitly refuse to claim

- **SecondSignal is never "all you need."** For addiction, crisis, or any
  clinical condition, the system is an adjunct that actively routes users
  *toward* human community, sponsorship, and professional care — never a
  replacement for them. A support system that positions itself as
  sufficient care for conditions it cannot treat is not ambitious; it is
  unsafe. This system's architecture (safety gates, contraindications,
  escalation preemption) is built on the opposite premise.
- We do not claim the system replaces human relationships or therapy. It
  is designed to augment human support.
- We do not claim novelty. Outcome-oriented support metrics exist across
  human helping disciplines. We claim a **useful configuration**: that
  orientation applied as the governing metric of a multi-agent AI system,
  with the instruments built into the architecture rather than bolted
  onto the marketing.

## How it is measured

Three instruments, all architectural:

1. **Impact events** (ADR-0001). Unsolicited user reports of delayed
   improvement, with domain-aware markers: `self_efficacy` for episodic
   domains; `stability`, `faster_recovery`, and `outward_connection` for
   chronic domains. Detection is passive and explicit-only; the system is
   prohibited from soliciting gratitude.

2. **Per-domain recurrence, interpreted per domain class.** In episodic
   domains, sessions trending toward resolution is positive. In chronic
   domains, recurrence is expected and neutral; the watched signal is
   whether engagement trends healthier or more dependent.

3. **Session-scoped dependency monitoring.** In-session signals of
   unhealthy reliance, which route toward de-escalation and referral
   rather than continued engagement.

### Known limitations of these instruments

- **Attribution:** users improve for many reasons. Impact events record
  attribution, not causation, and are reported as supporting evidence.
- **Sampling:** explicit-only detection sees a biased sample. Counts are
  a floor of documented reports, never presented as rates.
- **Self-instrumentation:** we built the measuring devices. The mitigation
  is publishing the methodology and the eval harness so the measurement
  design itself can be inspected and challenged.

## What would falsify the claim

We consider the claim failing, not succeeding, if the data shows:

- **Episodic domains:** same-problem recurrence rising over time; impact
  events accumulating without `self_efficacy` markers — users report
  feeling helped but never report handling things independently.
- **Chronic domains:** engagement deepening while `outward_connection`
  markers stay absent — users substituting the system for human community
  and professional care rather than being routed toward them.
- **Both:** dependency-monitor flags trending upward with tenure; usage
  patterns consistent with emotional dependency rather than support.

If the instruments show these patterns, the correct response is to change
the system, not the metric.

## Current status

Pre-data. The instruments are specified; the corpus is empty. Results will
be reported as they accumulate, including negative results. Anyone
evaluating this system is invited to judge whether the measurement design
would catch the failure modes it names.

## The honest business logic

A system optimized for user outcomes retains users the only way we
consider legitimate: by being useful enough that people bring it their
next problem, and safe enough that people managing chronic conditions are
consistently pointed toward the human support they need. Engagement-
maximizing designs face a direct conflict between this metric and their
own economics. That asymmetry is the differentiation — and it only holds
as long as the measurement stays honest.
