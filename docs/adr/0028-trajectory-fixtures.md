# ADR-0028: Trajectory fixtures, or which turn the gate fires on

- **Status:** Proposed — partial; the format is written, one model-authored trajectory exists and has been run once against the tree (2026-09-17, classified contract-adjusted), the shape validator and the directory guard are in the tree with their tests, the runner is not built; not to be cited from code as anything but Proposed, and under the standing rule a record prepared by the project's own assistant becomes canon only after a second model family has read it (review round 3)
- **Date:** 2026-09-14; first run and renumbering 2026-09-17
- **Evidence:** the single-case contract's `prior_turns` field and the runner's silent replay of it (`tests/test_eval_cases.py`, ADR-0013); the seven-turn latch case in the demo's acceptance set; the aftermath count and no-joke carry in ADR-0019 as amended; the interlock rules in ADR-0023; the operator's stated differentiator recorded 2026-09-14 (the personas do not make the routing decision); `tests/test_trajectory_format.py` for the validator, the provenance computation and the directory guard
- **Depends on:** ADR-0011 (the no-signal policy), ADR-0013 (two planes, one runner), ADR-0018 (one card), ADR-0019 (aftermath), ADR-0022 (intake and provenance), ADR-0023 (the ledger and the interlock)
- **Number:** drafted as 0027 on 14 September without reading the register; 0027 was already the relative's-return record. Renumbered 0028 on 17 September; 0021 and 0024 stay reserved

## Context

Every labelled case in the suite asserts one decision: the last one. A case may
carry prior turns, and the runner replays them through a session before the
message under test, so the suite can already say that a latch set early is
still there late. What it cannot say is anything about the turns in between. It
cannot assert that five ordinary turns stayed ordinary, that the sixth
escalated, that the seventh's "I'm fine" lowered nothing, or that the aftermath
counter walked down across the substantive turns that followed. Distress rarely
arrives in one message. The slope is the case, and the suite has no way to
write the slope down.

This is the eval-plane consequence of the project's central claim. If the
personas do not make the decision, then the decision is a function of the
session and the message, and a function of the session can be tested across
the session. A project that only tested single messages would be leaving its
own claim half-tested.

A separate pressure arrived the same day from outside: the argument that the
expert's job is shifting from reviewing outputs to shaping what a system
practices on. That framing fits this suite, whose fixtures are exactly the
practice conditions. It also carries a warning the project already knew from
the sim-to-real literature: a simulated person in crisis is a model performing
distress. Practice against that alone and the gate learns how a model imagines
despair, not how people sound.

Three days later the same conclusion arrived from a third direction. The
research briefs of 17 September 2026 read four new preprints (Compositional
Policy Violations; Symbolic Temporal Supervision of LLM Agents Using Contracts;
BLINDSPOT; Emergence World) and each says, in its own vocabulary, that a
per-step check cannot see a per-trajectory failure: authority creeps, a
threshold is laundered, a refusal decays, a contaminated memory acts hours
later. BLINDSPOT's five outcomes (safe completion, correct refusal, unsafe
completion, over-refusal, indeterminate) map onto this plane as a seated
PROCEED, a card delivered when due, a MISS on a real crisis, a card on an
idiom, and UNRESOLVED; its "post-refusal failure" and "first divergence turn"
are the two figures a trajectory runner should report per file. None of that
changes the decision below; it is recorded because three independent lines
reaching one format is the kind of evidence this project keeps.

## Decision

**A trajectory fixture is one session, many turns, and expectations on
both.** The format is specified in `evals/cases/trajectories/README.md`. Each
turn may carry any subset of the existing single-case expectations, so nothing
in the current contract changes meaning. Two turn-level fields are added,
`aftermath` (the session's count after the turn) and `no_joke` (on the decision
record). One trajectory-level block is added: `first_escalation_turn`, which
asserts both when the gate fires and that it did not fire earlier;
`escalation_turns` and `cards_total` for exactness; and `invariants`, a list of
named checks applied to every consecutive pair of turns.

**The invariants are the ADRs, restated as checks.** Restrictions never weaken
without a clearance row (ADR-0023). The aftermath counts down on substantive
turns only, is not consumed by the card's own turn or by the turn that
immediately follows it, and is renewed by any new card (ADR-0019 as amended,
ADR-0023). Message text never clears (ADR-0022, ADR-0023). One card per event
(ADR-0018). No seat resolves by id order (ADR-0013). A trajectory names the
invariants it wants; the runner refuses a name it does not know. When a later
ADR adds a rule that holds across turns, it adds an invariant here.

**Provenance is a schema field the runner reads.** Every trajectory says
whether its words were written by a person or a model. Only human-authored,
human-reviewed trajectories count toward the recall figure; the runner computes
that flag and overwrites any hand-set value. Model-authored trajectories run in
CI, can fail the build, and are reported in their own column. A model draft
rewritten by a person in their own words is human-authored. A model draft a
person read and approved is not.

**Policy plane, runnable today.** Every oracle is exact and the real pipeline
is the system under test, so the directory is `evals/cases/trajectories/`, not
`deferred/`. The single-case runner asserts it never runs a file carrying
`kind: trajectory`; the trajectory runner asserts it never runs one without it.

**Same three markers, same rule.** `known_gap`, `disputed` and
`contract_adjusted` apply to the whole trajectory with the semantics the suite
already has: a known gap names its failing turn in `gap_note`; a disputed
trajectory carries `dispute_note`; a contract-adjusted trajectory carries
`adjust_note` and keeps every moved expectation beside the new one as
`original_expect` on that turn. Nothing is deleted to make the suite green.

## Consequences

One trajectory exists: `evals/cases/trajectories/slow-slope-001.json`, nine
turns, the gate expected on turn six. It is labelled model-authored and does
not count toward recall until the operator rewrites its turns in his own words
and marks it reviewed.

It was run once, by hand, against the public tree on 17 September 2026 (head
4b77258 plus the lexicon repair of that day). Turn six fired as expected: the
passive-absence phrasing is in the English pack, so the soft spot the 14
September record feared is not a gap. Seven of nine turns matched exactly.
Turns seven and eight did not, on two fields each, and both times the tree
was reading ADR-0023 correctly and the draft was not. The draft expected the
aftermath count to read 1 after turn seven and 0 after turn eight; the tree
reads 2 and 1, because the record says the card's own turn and the turn that
follows it consume no count, and the code does exactly that. The draft also
expected PROCEED on both turns; the tree returns DISCLOSE, because the record
says the resources stay reachable through the aftermath, so the gate restates
them once on the turn after the card and keeps them within reach while the
count is live. The draft had written the verdict from the crisis read (MISS)
rather than from the action. The trajectory is therefore classified
**contract-adjusted**, the four original values are kept on their turns, and
the invariant above now says what the record says. One wording note owed to
ADR-0023: its sentence exempts "an acknowledgement after the card", and the
implementation exempts whichever turn comes first after the card,
acknowledgement or not; the two agree on every case in the suite and the
record should say what the code does.

The README names this record under what is not built, per the register rule,
and `docs/adr/index.json` carries its row: decision Proposed, implementation
partial (the format, the fixture, the validator and the directory guard; not
the runner). ADR-0021 and ADR-0024 remain reserved; this record does not take
either number.

The runner is a small build: one test module, the single-case assertion helpers
reused, five invariant functions, and the refusals listed in the README. It
lands with the operator's rewrite of the first trajectory and the two
trajectories the 14 September record ranked next (a re-escalation with a second
card; a soft-latch decay across five clean turns), plus four the 17 September
research briefs make policy-plane today: a constraint carried unchanged through
many turns; a twenty-turn refusal-decay continuation after a card; a turn that
claims prior approval or a rule change; and the statement that repeated runs
are trivially identical for a deterministic layer, written down so that the
day a generator sits in the loop it stops being trivial.

## What this record does not decide

It does not build a simulator. A generative user model that produces
trajectories is a later question with its own ADR, and this record's
provenance rule is written so that such a model's output can be run the day it
exists without contaminating the recall figure.

It does not touch Protocol B. Protocol B is the evaluation protocol for the
audit harness (ADR-0014, ADR-0020) and concerns what a seated persona said.
Trajectory fixtures concern the policy layer and never read a reply. The two
are complementary and neither substitutes for the other.

It does not add a confidence value to the routing decision. That idea arrived
on 17 September from the same brainstorm that examined a decision-only model
(the "System One" framing), is proposed and undecided, and if adopted gets its
own record; a slow-slope trajectory is where such a value would prove itself.

## Relationship to the current implementation

Partial. What exists today already satisfies part of this record by
construction: the pipeline is deterministic, sessions carry latch and aftermath
state, and prior turns already replay through a session. The shape validator
(`evals/cases/trajectories/validate_trajectory.py`) enforces the format's
refusal rules and computes the recall flag from provenance; the single-case
runner refuses trajectory files; `tests/test_trajectory_format.py` pins both.
The runner, the two new turn fields as assertions, the trajectory block as
assertions and the invariant functions are promises the code has not yet made.

## Test that would falsify this ADR

A trajectory passes with no `first_escalation_turn`, no invariants and no
per-turn expectation; a turn with an expectation and no `why` is accepted; an
unknown invariant name is accepted; a model-authored trajectory's result enters
the recall figure; a file carrying `kind: trajectory` runs through the
single-case runner; a trajectory whose seventh turn is "I'm fine" lowers the
latch or zeros the aftermath and the suite stays green.
