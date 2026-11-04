# ADR-0033: Every veto has a kind

- **Status:** Proposed — built; independent review remains open under the standing rule of 7 September 2026
- **Date:** 2026-10-13
- **Evidence:** `tests/test_v1_veto_kinds.py`; `tests/test_p2_ask_wins.py`; `evals/cases/p2_v1_round2_asks_2026-10-13.json`
- **Depends on:** ADR-0016 (seat versus hold), ADR-0017 (preferences never touch the envelope), ADR-0032 (Proposed) (a hold lasts the sitting)

## Context

The roster used one untyped list for every contraindication. A refusal was
hard, but its record could not distinguish a safety boundary from a fit
boundary. Review round R2 asked for that distinction before preferences,
favourites or teams gained any way to affect the seat.

The operator ruled on 11 October 2026, ruling 4, **A**: label the kinds;
do not build a fit-veto override. Order P2V1 builds that floor before the
ask is allowed to move a seat.

## Decision

Every contraindication has exactly one `veto_kinds` entry: `safety` or
`fit`. The loaded mapping is immutable. A safety veto names a hold domain
(grief, abuse, eating distress or addiction recovery) or somatic distress;
a mode cannot become a safety rule by changing its label. A veto on one
of those protected domains cannot be labelled fit. Other domains and modes
may carry fit vetoes. This is the first labelling, open to the operator's
review of the table in the build log, within those invariants.

No preference, team, favourite or declared ask clears a veto of either
kind. The kinds exist so that the record can name the rule that refused
a seat, and so a future preference layer has a boundary it cannot cross.
Seat, shadow and assist still use the existing eligibility gate. Its
rationale names each blocked tag and kind, and retains the carried-hold
explanation. The gate, latch, register caps and hold lifetime are unchanged.

The JSON loader requires the field whenever contraindications are declared,
even when their list is empty. By the operator's amendment of 13 October,
a minimal payload omitting both fields is the empty case. It does not waive
validation of a supplied list or mapping.

## Dissent retained

The Grok-laptop door proposed relaxing a fit veto through an explicit
preference, while still refusing to seat the humorist under a grief hold.
That override outside holds was rejected. DeepSeek went further: a
preference that humour helps in grief should relax the fit veto and seat
Vandal under the grief hold, with this proposed line:

> Vandal is taking this one because you said humour helps you grieve. If it stops helping, say so.

Ruling 4 rejects that position. DeepSeek's `r2d-veto-001` could not be run:
it contains declared facts and an expectation but no literal message text
or prior turn to establish its grief hold. Its `r2d-veto-003` likewise has
no literal message. Both remain quoted in the build log, unported by the
operator's amendment of 13 October; no replacement sentence is written
under that door's name.

Nemotron's `R2-P2-001` does supply literal text and expects Vandal under
grief. It is the executable dissent for this position, kept verbatim with
its original declared facts and expectation, as a strict expected failure
on the seat alone. The manifest quotes the door's reasoning and cites
ruling 4. Neither the expectation nor the safety assertion is relaxed.

## What holds this decision

The three permanent tests in `tests/test_v1_veto_kinds.py` cover both veto
kinds across the case corpus and same-sitting prior holds, plus every
shipped veto on a plain lexicon example under all seven asks. Carded turns
keep their existing empty ranked record and no seat. The third test holds
the schema, immutable mapping and roster invariants. These tests are safety
assertions and may never be skipped or marked as expected failures.

Preferences beyond the single ask, favourites and teams have no new seat
controls in this order. The permanent proof covers the declared ask today;
those later controls must join it when they exist.
