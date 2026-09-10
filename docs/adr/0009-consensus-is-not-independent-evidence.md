# ADR-0009: Multi-agent consensus is not independent evidence

- **Status:** Accepted — not-code; a principle in force
- **Date:** 2026-09-01
- **Evidence:** Patterns and Problems in Emerging Multiagent Systems; MasDrift; Safety Does Not Compose

## Context

Agents built on the same base model make correlated choices, repeat the same
ideas, converge prematurely, and share blind spots — observed as identical branch
names, synchronized strategies, and correlated failures. A majority of same-model
personas agreeing is therefore not independent confirmation, and coordination can
manufacture collusion, groupthink, and consensus traps.

## Decision

Same-model persona agreement cannot satisfy independent review. Consequential
consensus requires at least one of: **epistemic diversity** (genuinely different
evidence, methods, models, or priors), **governance independence** (enforcement a
deliberating agent cannot rewrite), or **adversarial independence** (reviewers
that do not share the same vulnerable context). "The agents agreed" is a process
observation, never proof.

## Consequences

Review and red-teaming deliberately draw on different model families and external
systems rather than a panel of one model wearing several hats. Dissent and
pivotal minority evidence are surfaced before consensus, not averaged away.

## Relationship to the current implementation

In force as a principle. It already shapes how SecondSignal is evaluated:
adversarial review is run across independent external systems from multiple labs,
not a chorus of one model. The roster **safety-floor** invariant is a built cousin
of the idea — a structural guarantee (at least one agent safe at full
dysregulation) that holds regardless of any agent's judgment, enforced by a test
rather than by agreement.
