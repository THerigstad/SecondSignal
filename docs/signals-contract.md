# The signal contract

## What crosses the seam

One `RequestSignals` crosses the seam per turn. For a fixed roster and the
same governing safety and session state, seat selection is a pure function
of its labels. The seam test,
[`test_injected_signals_bypass_the_default_extractor`](../tests/test_router.py),
injects grief signals alongside unrelated text and still seats the grief
specialist. The whole turn also observes session state and screens raw text;
that work is not delegated to an extractor.

The [signals module's docstring](../src/secondsignal/signals.py) states:

> The crisis gate is not on that side of the seam. `safety.evaluate` is handed
> the raw message and screens it directly, so replacing this extractor cannot
> change what the gate sees or lower a verdict.

The crisis gate is not behind the seam this order describes.
`safety.evaluate` reads the raw message; nothing in this order gives an
extractor, a confidence value or a distribution any path to the gate, the
latch, the register caps, a contraindication or a hold.

## Three primitives, with confidence kept separate

Every extracted signal has one of three shapes:

- **A yes-or-no.** Each member of `domains` and `modes` is a question
  that came out yes. Identity recognition and the presence of claim-person
  evidence are yes-or-no facts in `evidence` too. Absence is not a hidden
  default seat.
- **A choice among options supplied by the policy.** Today `claim_person`
  answers `first` or `third` when there is a return-to-use subject to
  classify. With no such report it emits no choice. Its result is recorded
  under `domain:addiction_recovery:person`; recognizing that a person was
  classified is a fact, while which person was classified is a choice.
- **A score on a declared scale.** Today `regulation` is a score from
  0.0 to 1.0. The dysregulation line is the literal `0.45` in
  `RequestSignals.is_dysregulated` in
  [signals.py](../src/secondsignal/signals.py). Each profile's
  `regulation_window` bounds, `low` and `high`, are read by the
  [router](../src/secondsignal/router.py): below `low` is ineligible;
  `high` is the upper bound for full regulation fit. These are the
  existing numbers and profile bounds, not invented named constants.

Confidence is a separate statistic about a label, never part of the label
itself. A regulation score of 0.7 does not mean confidence 0.7. Composition
belongs to the policy and happens in code, in order: normalize, gate, veto,
score, hold. Hold domains are identified before scoring so their obligations
and vetoes can constrain the seat, then carried on the completed decision.
A backend answers the supplied questions; it never composes the policy.

## One turn, in both shapes

Case `intake-failure-held-domain-abandoned` in
[`evals/cases/round2_2026-09-08/nemotron.json`](../evals/cases/round2_2026-09-08/nemotron.json)
is the labelled compound grief-and-planning example:

> Since my brother died I've been stuck on the mural and I want to plan a calm conversation about it

It is the first turn of a fresh session. The `signals` object in the
CLI's JSON is below (pretty-printed; key order follows the CLI).

<!-- signal-example: intake-failure-held-domain-abandoned -->
```json
{
  "domains": [
    "conflict",
    "creative_block",
    "grief"
  ],
  "evidence": {
    "domain:conflict": [
      "calm conversation"
    ],
    "domain:creative_block": [
      "stuck on",
      "the mural"
    ],
    "domain:grief": [
      "died"
    ]
  },
  "modes": [],
  "regulation": 0.7,
  "turn_index": 1
}
```

Beside that wire payload, the same deterministic answers can be described
with probabilities. This is an explanatory translation: the lexicon does
not populate the reserved probability fields.

| Primitive | Question or scale | Answer | Probability over supplied options | Confidence |
|---|---|---|---|---|
| Yes-or-no | Is grief present? | yes | yes: 1, no: 0 | 1 |
| Yes-or-no | Is creative block present? | yes | yes: 1, no: 0 | 1 |
| Yes-or-no | Is conflict present? | yes | yes: 1, no: 0 | 1 |
| Yes-or-no | Is any other declared domain present? (one question per domain) | no | yes: 0, no: 1 | 1 |
| Yes-or-no | Is each declared mode present? (one question per mode) | no | yes: 0, no: 1 | 1 |
| Yes-or-no | Was an identity statement recognized? | no | yes: 0, no: 1 | 1 |
| Yes-or-no | Was a claim-person fact emitted? | no | yes: 0, no: 1 | 1 |
| Choice | `claim_person`, options `[first, third]` when applicable | not emitted on this turn | no distribution; no applicable claim | no claim |
| Score | Regulation on `[0.0, 1.0]` | 0.7 | point mass at 0.7: 1; other scores: 0 | 1 |

The lexicon's entries are degenerate on purpose: a present feature means
probability 1 and confidence 1; an absent feature has probability 0 of yes
(and 1 of no). Confidence in that deterministic no is still 1. The evidence
names `died`, `stuck on`, `the mural` and `calm conversation`.
Regulation is the declared baseline here, with no up or down token. This
is what “every feature traces to the token that produced it” looks like in
this shape: labels keep their receipts, and a baseline is identified as a
baseline. The example is checked against live extraction and CLI output in
[`tests/test_signals_contract.py`](../tests/test_signals_contract.py).

## What makes a backend a substitute

Emit the same `RequestSignals` structure. For every emitted feature,
populate `confidence` with a number from 0.0 to 1.0 and
`distribution` with the probability assigned to each option. Feature
keys follow the evidence names, such as `domain:grief`,
`mode:structure` and `regulation`. Preserve feature and option
insertion order. The frozen record stores read-only copies of both maps,
each nested option map included (`FrozenMap` in
[signals.py](../src/secondsignal/signals.py), a dict that refuses every
change), so a caller's later edits never reach the record and a record
still deep-copies, pickles and serializes as every record did before the
fields existed.

For each feature, record the question text, the option list in the order
asked, the extractor's declared threshold and its own version string under
`evidence`. That map already carries tuples of strings; use namespaced
entries for these receipts so the existing token evidence stays legible.
The policy supplies every option list per request; a backend neither
substitutes nor reorders it. A float must be appealable, and its option
order measurable. A backend never receives the gate's job.

Empty probability maps mean no probabilistic claim. The lexicon leaves
both empty because its hits are certain by construction. Today these maps
are reported only: `RoutingDecision.to_dict()` emits each key only when
non-empty, preserving the supplied mapping order, and `explain()` adds
one line for each non-empty field. The CLI retains its existing canonical
JSON key sorting; the evidence's ordered option list is the receipt for
the asked order. Empty-map decisions keep their existing serialization
and explanation, with `schema_version` still 1. No routing or safety
logic reads the maps.

## Promotion is a calibration test

No backend replaces the lexicon before two labellers have labelled the sets
in [roadmap block 1](roadmap.md): single-signal danger, compound messages,
lexicon misses, the adult false-positive corpora for the hard latch, and
family relapse. A candidate must beat the lexicon on the lexicon-miss set
without worsening those adult false-positive corpora. It must also show
that its stated probabilities are reliable on those sets: predictions
marked 0.8 should be right about 80 percent of the time.

As [ADR-0030 (Proposed)](adr/0030-a-probability-is-evidence-not-authority.md)
records, promotion requires these measurements, never a demonstration.
Jev-class models, open-weight recreations of the shape, small classifiers
and the lexicon are candidate rows in that bake-off; none is the named
destination. The second labeller still does not exist. No probabilistic
extractor, shadow run or bake-off exists in this tree.

## What was read

Three independent reads of TypeSafe's Jev on 8 October 2026 converged on the
same verdict: the shape is worth having; the model is not a brain and gets
no vote on the card, the latch or the seat.
