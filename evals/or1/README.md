# Calibration measurement instrument

This package measures responses with a scripted fake client. It does not change
routing, safety, a gate, a latch, a hold, register caps, contraindications, or
persona eligibility. Nothing here is on the request path. The future abstention
rules of ADR-0030 (Proposed) are not implemented or adopted by this instrument.

A real run sends each case's text to the third-party decision models named in
that run. These cases are synthetic public fixtures written for testing, not
collected from people. No person's message is ever sent. This build makes no
real model call, reads no key, and spends nothing. RealClient raises NotConfigured;
endpoint, actual model ids, provider route and spending cap await a later kit.
The five historical panel display names remain explicitly unverified.

## Reproduce the fake run

From the repository root, using an existing Python environment with the project's
development tools (no new dependency is required):

    python evals/or1_lexicon.py
    python -m evals.or1.runner --checkpoint-dir ../c --output evals/or1/results/fake.json

The first command reads the existing signal extractor and crisis screen through
an isolated module namespace that does not execute the policy package initializer.
It never loads the router. It writes a static lexicon verdict data file. The
instrument reads that file; it imports no policy module. Its only harness source
is the unmodified results leaf, loaded directly so the eager harness initializer
cannot load request-path code.

The second command writes fake.json, calibration.json and calibration.md into
`evals/or1/results/`. That folder is kept out of the repository (it is listed in
`.gitignore`): the fake run's outputs are rebuilt by the command, about 33 MB of
scripted answers, and published results will live under `evals/results/`. Every
results artifact carries the required specification-hash header with the explicit
absent marker and not-reproducible label. The header records the supplied base
commit and the exact question-data hash. Input and implementation hashes bind
resume checkpoints. The fixed scripts test the instrument, not vendor quality.

Use the same command and checkpoint directory to resume. Each completed model
response is atomically committed through the provenance writer before the next
call. An interrupted, uncommitted call may be repeated; committed calls are
reused. A changed corpus, label record, lexicon, panel, question set or instrument
implementation refuses resume. A custom test subclass must change its declared
client version when its response script changes. Use a new directory for a
deliberately new run.
Checkpoint checksums detect accidental changes; they are not protection against
a writer that can rewrite both the records and receipts. Keep the default one
writer per checkpoint directory; concurrent writers are not supported.

On this Windows order, keep the source tree in work/s and tests at
python -m pytest --basetemp=../t. Keep scratch paths below 250 characters. The
returned archive names the built source tree SecondSignal-6795de2.

## Questions and labels

questions.json fixes nine questions, their text, types and option order: presence
of the four hold domains; a choice among all thirteen domains plus none; crisis
read; ongoing risk; intent to act; and most severe risk. The intent question is
explicitly the most clinically loaded label and the first clinician review
priority. The supplied kit does not identify the benchmark publication or a
verified severity taxonomy. These probes and provisional severity options do not
claim benchmark equivalence or a clinical ordering.

No regulation question is supplied: docs/signals-contract.md and signals.py
declare a continuous score and thresholds, not regulation bands.

The corpus record inventories every case JSON file and binds the original bytes
by SHA-256. Only the 693 existing single-case policy fixtures are measured.
Deferred files and trajectories are listed separately, never flattened. Missing
provenance excludes and lists a case; changed fixture bytes reject the stale
record. Original fixture files are not edited. Raw flags and the validated
manifest disposition are both retained, including authorized historical gap
closures. Current labels and original reviewer labels remain distinguishable.

Only explicit expect.crisis_read HIT and MISS labels map to yes and no. Six
INCONCLUSIVE labels are not a binary negative. Safety actions, outcomes, agents,
held-domain assertions and crisis_category are preserved as source labels and
never used to guess labels for different questions. The eight other questions
remain unlabelled until the two human labellers finish. Authorship comes only
from the corpus record: model-written, human, and unconfirmed are distinct.
Project-manager role does not imply human authorship.

## Reading the report

Every model and host-reported identity is separate. There is no model average,
vote, consensus score, or promotion decision. A comparison table preserves
disagreement. Refusals retain their reasons and malformed responses retain their
raw text; neither becomes a negative answer.

Calibration uses only labelled, answered pairs with a complete probability map.
Binary Brier score uses p(yes); choice scores and curves use declared one-versus-
rest options. Answer-only responses can enter classification measures but never
acquire invented probabilities. Counts and authorship accompany metrics.
Ten bins include p=1 in the final bin. Exact Match, Jaccard, micro/macro F1 and
micro/macro recall are all reported. Partial-label results name their restricted
scope; complete-set metrics remain unavailable without complete labels.
The lexicon does not state probabilities, so its deterministic verdicts are not
presented as calibrated confidence.

Cohen's kappa and Gwet's AC1 are reported once for the corpus on the declared
crisis_read question; unrelated question scales are excluded from that scope.
Kappa is unstable under severe crisis-label imbalance. There is no second
labeller in this corpus, so agreement is not computable with zero paired labels.
A future second_labels map uses the same explicit label and authorship schema;
pairing a human label with an old model-authored fixture is not two-human
agreement. No clinical validity or real-model performance is established here.
