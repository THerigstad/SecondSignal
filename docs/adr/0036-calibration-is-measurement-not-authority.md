# ADR-0036: Calibration is measurement, not authority

- **Status:** Proposed — built; the instrument is tested with a scripted fake client only; no real model run, promotion or adoption is claimed
- **Date:** 2026-11-04
- **Evidence:** the boundary and runner tests below.

```text
tests/test_or1_guards.py
tests/test_or1_runner.py
```

- **Depends on:** ADR-0009, ADR-0030 (Proposed), ADR-0035 (Proposed)

## Context

A probability is evidence. Agreement among models does not make it independent
evidence. The calibration instrument records fixed questions, labels, the
lexicon verdict and separate model answers before any real trial.

## Decision

The evaluation plane has two parts. A separate lexicon pass reads the existing
signal and safety leaves, never the router, and writes data. The instrument
reads those verdicts as data and imports no policy module. Its only harness
import is the existing results module, loaded without the parent package's
runtime imports.

```text
evals/or1_lexicon.py
evals/or1/
src/secondsignal_harness/results.py
```

Questions and the model panel are data. Every model entry is unverified. The
real client raises an error before reading a key or making a call. A scripted
fake client tests answers, refusals and malformed responses. Refusal and
malformed output are not negative answers.

Every source file is covered by one corpus provenance record. The operator
declares these cases synthetic public fixtures written for testing, not
messages collected from people. Unknown files are excluded and listed.
Existing case files are unchanged. Labels retain their source and authorship;
model-authored labels are never human labels, and authorship that is not
settled is unconfirmed. Missing labels are unlabelled. Most questions remain
unlabelled until two human labellers finish. The intent-to-act question is
the first label a reviewing clinician should check.

Measurements use labelled pairs only and state their counts by question and
authorship. Each model keeps its own results. There is no average or vote
across models; the comparison table preserves disagreement. A second label
is required before agreement can be measured.

Each results row carries source, fixture flags, requested and reported model
identity, raw response, answers, usage, cost and timestamp. Resume retains
completed rows and rejects changed inputs. Every output goes through the
existing results writer with the explicit absent specification marker and its
not-reproducible label, plus the tree commit and question data hash.

## Consequences

This instrument changes no behavior. No result reaches a decision, gate,
latch, hold, register cap, contraindication, seat, card, house line or release.
Nothing on the router, safety, harness turn path or Table may import the
instrument or lexicon pass. The codexes, house block, rules, patterns, latch,
holds, router, personas, profiles, harness turn path, Table and demo are
unchanged. The future abstention table in ADR-0030 (Proposed) is not adopted
here.

A real run sends each case's text to the third-party decision models named
in that run. The cases are synthetic, and no person's message is ever sent.
The operator runs that later, after labels and model checks. The fake run
makes no vendor call, reads no key and provides no evidence of real model
calibration.

## Falsifiers

A policy import, a request-path import of the instrument, a missing provenance
header, an invented label, a hidden exclusion, a refusal counted as negative,
an averaged model answer or an unexplained changed result fails the tests.
Independent review and the two human labellers remain future work.
