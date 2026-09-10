# Stalls and recovery: a proposal filed, one line of it adopted

**Status:** labelled proposal, not canon. The packet summarised here was
produced by ChatGPT-6 Astra (Ultra) on 9 September 2026 at the operator's
request and returned as `ss_stall.zip`; it is model-generated and is filed
under the project's rule that nothing enters the suite from a model directly.
On 10 September the operator adopted its one-line recommendation and nothing
else: instrument first, deterministic guardrails second, and no recovery
model unless production evidence proves it has a recurring job. The eight
test cases it carried are kept as deferred-plane fixtures
(`evals/cases/deferred/stall_recovery_cases.json`), marked model-generated,
on the orchestration plane, and are not run against the gate.

## What the packet is

Two arguments written against each other (for and against a stall-and-
recovery layer), a recommendation, a candidate state machine, a retry policy,
a JSON schema for an incident row, eight test cases and a five-test pytest
sketch. Its architectural boundary, stated in its own README, is the part
this project agrees with without reservation: a worker never watches itself.
A timeout or a watchdog lives outside the call it supervises, because a hung
call never gets the turn it would need to report that it hung.

## The one line adopted, and why

This repository is a policy layer with no generation layer behind it. There
is nothing to recover yet, so a recovery controller would be a component with
no job, and a second model supervising every call would add latency and cost
to a path that has no measured stall rate. The packet's own recommendation
is to measure before building, to keep recovery deterministic inside the
orchestrator, and to add a reasoning component only if labelled cases show a
recurring class that rules cannot express. That is the line the operator
took.

## What the project takes from it now

- **The retry taxonomy shapes the one automatic retry** the operator ruled
  for the intake failure rule (ADR-0022, the clause rewritten on 10
  September). A transient class (rate limit, transient network, provider
  timeout, provider 5xx) earns one retry with no change; a non-retryable
  class (invalid authorization, permission denied, unsupported or invalid
  input, a safety refusal, a user cancellation, a context limit) goes
  straight to the failure path. Nothing is retried blind more than once.
- **The failure states get the diner rule's words.** The packet's state
  names are engineering names; the person sees none of them. When a
  generation layer exists, the proposed person-facing wording is: working
  on it (RUNNING); waiting on something outside this conversation
  (WAITING_ON_TOOL and BLOCKED_EXTERNAL_SYSTEM); trying again (RECOVERING);
  "This message ran into a problem. Press here to try again." (STALLED and
  FAILED_SAFELY, the house's failure line, ruled 10 September); part of this
  finished, and here is what did (PARTIAL_SUCCESS); one thing is needed from
  you to continue (BLOCKED_USER_INPUT); stopped, as you asked (CANCELLED).
  These are proposed words, not house lines, and the operator approves them
  before any of them is shown to a person.
- **The incident row** (task, goal, failed action, attempts, strategies
  tried, last error, artifacts preserved, safe to retry, recommended
  disposition) is the shape a stall log would take if the project ever logs
  one; it is kept as the schema in the deferred fixture file.

## What is not adopted

A recovery-controller model; a watchdog service; circuit breakers by
dependency; idempotency keys; durable checkpoints. Every one of these
belongs to an orchestration layer this repository does not contain. They are
listed so the packet's contents are on the record and so nobody rebuilds the
argument from scratch when that layer exists.

## Provenance

Family: OpenAI. Doorway: chat. Model and tier as the operator saved it:
ChatGPT 6 Astra Ultra. Date: 9 September 2026. Returned in the operator's
review-round-two folder beside the round's reviews; not part of the round
and not a review of any record. The operator's own note on the folder is
that none of it was canon on arrival, and this note is where its status is
decided.
