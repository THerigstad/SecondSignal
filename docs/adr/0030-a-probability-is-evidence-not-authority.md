# ADR-0030: A probability is evidence, not authority

- **Status:** Proposed — partial; the reserved fields and proofs that routing and safety logic never read them are built; no probabilistic extractor exists, so the abstention table has nothing to act on yet; under the standing rule of 7 September 2026, a record written for the operator by the project's own assistants becomes canon only after a second model family has read it
- **Date:** 2026-10-09
- **Evidence:** `tests/test_signals_contract.py` (empty lexicon fields, immutable records, unchanged labelled decisions and trajectories, static reporting-only reads, serialization, the contract example and explanation); `tests/test_h1_replay.py::test_h1_every_labelled_turn_keeps_its_policy_house_lines_and_release` (the unchanged before/after replay); roadmap block 1 and the operator's ruling of 8 October 2026, implemented by order J1 with the reporting-boundary clarification of 9 October
- **Depends on:** ADR-0003 (persona and execution are separated), ADR-0010 (the crisis screen is a floor and fails closed), ADR-0011 (no-signal routing is a policy), ADR-0015 (the two-tier latch), ADR-0016 (seat versus hold), ADR-0029 (Proposed) (the voice is a harness behind the policy layer)

## Context

The [signal contract](../signals-contract.md) separates understanding a
message from deciding who may answer. A backend can provide yes-or-no
answers, choices and scores, with confidence separate from their labels.
That interface does not give it authority over safety or over the policy.

Three independent reads of TypeSafe's Jev on 8 October 2026 converged on the
same verdict: the shape is worth having; the model is not a brain and gets
no vote on the card, the latch or the seat. This record adopts no dependency
and names no destination backend.

The crisis gate is not behind the seam this order describes.
`safety.evaluate` reads the raw message; nothing in this order gives an
extractor, a confidence value or a distribution any path to the gate, the
latch, the register caps, a contraindication or a hold.

## Decision

The following are rules for a future probabilistic integration. This order
reserves and reports evidence; it does not implement abstention or change a
label, score, seat, hold, card, house line or release.

1. **Evidence has no safety authority.** A confidence value or distribution
   is evidence in the record. It is never an input to the gate, latch,
   register caps, contraindications or holds, and never lowers a verdict.
   The gate screens the raw message itself, as it does today.
2. **An unsure label earns no specialist seat.** A domain or mode label
   whose confidence is below the threshold its extractor declares is
   treated by the router as absent for seating. It earns no specialist
   seat; the existing no-signal policy supplies the house's ask and the
   stabilizer as today for an empty extract. The threshold is the
   extractor's declared number recorded on the row, never a router-owned
   constant or a universal value such as 0.5. The future abstention table
   below is not active on the current tree.
3. **Evidence cannot clear a restriction.** No confidence value clears a
   latch or lifts a hold. Only an operator with a reason clears a latch
   (ADR-0015); holds end as the policy says they end.
4. **Contraindications remain vetoes.** They ignore confidence entirely.
   An agent vetoed on a contraindication remains vetoed at any confidence.
5. **A float must carry its receipt.** Whenever a probabilistic extractor
   is used, the row records the distribution, question text, option list
   in the order asked, declared threshold and extractor version. Record
   the question, ordered options, threshold and version under
   `evidence`, beside the two probability maps, so a float can be
   appealed and option-order effects measured.
6. **Promotion is measured.** Two labellers must label every set in roadmap
   block 1: single-signal danger, compound messages, lexicon misses, adult
   false-positive corpora for the hard latch, and family relapse. A
   candidate must beat the lexicon on misses without worsening those
   false-positive corpora, and its stated probabilities must be reliable
   on those sets: a signal marked 0.8 should be right about 80 percent of
   the time. Promotion is this calibration test, never a demonstration.

| Future condition | Seating rule | Restrictions |
|---|---|---|
| A domain or mode is below its extractor-declared threshold | Treat that label as absent; no specialist seat on it | No gate, latch, cap, contraindication or hold is weakened |
| No routable label remains | Existing empty-extract policy: first and second vague turns ask with no seat; from the third, the stabilizer by role with an ask | Governing safety verdict still takes precedence |
| Confidence reaches the declared threshold | The label may be considered by the ordinary policy, never as a command to seat | All vetoes and other eligibility checks still apply |

The lexicon's empty maps mean it makes no probabilistic claim; they do not
mean zero-confidence labels and do not trigger this future table. On
today's tree, even injected zero-confidence labels route exactly like
their unchanged labels. The table has nothing to act on because no
probabilistic extractor exists.

## Consequences

`RequestSignals` carries immutable, defensively copied probability maps.
Their field names and option order are inspectable, and reporting is
conditional: empty maps do not alter existing serialized decisions.
Only the bodies of `_signals_to_dict` and `explain` in the router
may read these fields for reporting. An AST test rejects attribute accesses
and exact-name string literals elsewhere in the router, including function
signatures, and anywhere in the safety module.

The behavioural proof runs every manifested labelled case with empty,
arbitrary and zero-valued confidence, including prior turns and session
state. The trajectory proof compares house lines, text and release with a
pretend adapter. Existing recorded dissents and known gaps remain as they
are. The second labeller does not exist; no probabilistic extractor, shadow
run, bake-off, calibration result or promotion is claimed. A future builder
must implement and test the abstention rules without making evidence an
input to a safety restriction, then pass the promotion gate and independent
record review before adoption.
