# Evaluation program

> **Scope note.** This describes how SecondSignal is *meant* to be measured across its full
> target architecture. The slice that runs today is deliberately small: the labeled routing
> cases under [`evals/cases/`](../evals/cases/), each verified by hand against the policy
> layer. There is no automated runner yet — it is on the README roadmap. This document
> exists so the measurement bar is public before the system grows into it.

## 11. Evaluation program

### 11.1 Core principles

Every evaluation should state:

- the system boundary;
- the user authority boundary;
- the threat or capability being tested;
- the exact persistent state available;
- the model, persona, harness, and policy versions;
- whether tools are simulated or real;
- whether evaluation labels are hidden from runtime;
- the expected mechanism;
- safety and utility metrics;
- and known limitations.

Do not publish a single aggregate “SecondSignal safety score.” It will hide the mechanism and encourage benchmark optimization.

### 11.2 Required test families

#### A. Authorization and handoff

1. Single agent vs. supervisor depth 1–3 vs. peer network.
2. Generic vs. role-specialized agents.
3. Same-model vs. heterogeneous lead/executor teams.
4. Original request re-anchoring vs. chain-carried policy.
5. Reserved actions with useful preparation on the same tool surface.
6. Exact confirmation binding and refusal replay.

Metrics: task completion, unauthorized action, over-disclosure, constraint loss, first-loss hop, blocked legitimate work, confirmation burden.

#### B. Operational-state preservation

Transform the same blocker through:

- direct handoff;
- light summary;
- normal compression;
- aggressive compression;
- plan assimilation;
- consensus/convergence;
- ownership deferral;
- precedent substitution;
- memory write/retrieval;
- and multi-hop combinations.

Measure source recognition, field preservation, operational force, downstream blocker recognition, and endpoint action separately.

#### C. Cross-loop safety

Split decisive evidence across 2–10 iterations. Include:

- separate capability and destination fragments;
- rejected work reintroduced by paraphrase;
- delayed execution after risk decay;
- memory trust relabeling;
- restart and rollback;
- checker/writer model collusion;
- repeated “almost complete” claims without progress;
- and authorization assembled from separately valid fragments.

#### D. Memory and personalization

1. Fresh-session retention on/off.
2. Distractor and wrong-project memories.
3. Old rule plus authoritative update.
4. Temporary exception expiry.
5. Historically true but no longer applicable information.
6. Dormancy/reactivation sequence: E1 → E2 → E3 → E1.
7. Local exception versus generic knowledge.
8. Socially inappropriate but factually relevant recall.
9. User correction of agent inference.
10. Deletion and dependency cleanup.

#### E. Evoked Edits

1. Reproduce the triggering failure.
2. Attribute it to one layer and test alternative attributions.
3. Promote with target cases only, then with held-out cases.
4. Test safety, utility, voice, latency, and over-refusal regression.
5. Seed a malicious or irrelevant ancestor.
6. Remove the ancestor after two generations and verify descendant handling.
7. Compare edit enabled/disabled in fresh sessions.
8. Attempt benchmark-specific shortcut learning.

#### F. Persona-execution isolation

Apply perturbations from harmless tone change through adversarial instructions to bypass approval. Compare:

- tool set;
- state transitions;
- approval chain;
- hard-asserted fields;
- data egress;
- audit writes;
- free-text arguments;
- and terminal-action behavior.

Use A/A controls to distinguish model randomness from persona contamination.

#### G. Multi-agent society

1. Hidden-profile task where one agent holds decisive minority evidence.
2. Unreliable peer with overlapping facts.
3. Incompatible goals on a shared resource.
4. Pricing/resource-allocation games with and without communication.
5. Shared queue and polling-rate stress.
6. Same-model creative or planning diversity.
7. Human escalation and truce protocol.

#### H. Human-centered value

Where ethical and feasible, compare:

- user alone;
- agent alone;
- user with agent;
- user with deliberately minimal agent support;
- and user after support has faded.

Measure final outcome, retained user voice, decision clarity, confidence calibration, cognitive burden, task time, correction rate, perceived control, skill transfer, emotional effect, and willingness to contest.

### 11.3 Metric catalog

#### Safety and authority

- Unauthorized Action Rate
- Over-Disclosure Rate
- Constraint-Loss Rate
- First Constraint-Loss Hop
- Composition-Violation Rate
- Cross-Loop Attack Success Rate
- Irreversible Commit Count
- False Halt / Over-Halt Rate
- Under-Halt Rate and Halt Latency
- Appeal Resolution and False-Positive Clearance Time

#### Memory and learning

- Persistence Gain: enabled minus matched disabled performance
- Mechanism Evidence Score
- Retrieval Precision/Recall by episode
- Correct Update and Old-State Leakage
- Negative Transfer Rate
- Wrong-Project Transfer Rate
- Dormancy Benefit and Reactivation Recovery
- Unsupported Suppression Rate
- Provenance Completeness

#### Human value

- Pair Gain: user+agent minus user-alone outcome
- Voice Preservation
- Decision Ownership
- Cognitive Burden
- Contestability Success
- Proactivity Appropriateness
- Interruption Cost
- Capability Retention/Transfer
- Dependence or Deference Shift
- Completion Without Further Agent Use

#### Change governance

- Failure Reproduction Rate
- Attribution Accuracy
- Held-Out Safety Gain
- Held-Out Utility Change
- Regression Count by domain
- Quarantine Escape Rate
- Descendant Revocation Completeness
- Rollback Success and Recovery Time
- Unapproved Permanent Change Count

---

## Addendum, 2026-09-02: the slice that runs

> The scope note above is out of date in one respect: there is now an automated
> runner. This addendum describes it and the discipline around it (ADR-0013).

**Runner.** `tests/test_eval_cases.py` runs every case under `evals/cases/*.json`
through the real pipeline on every commit — prior turns through a session, then the
case text — and asserts the safety action, the outcome, the agent (exact, or one of an
accepted set where the gold is a documented disagreement), a substring of the
decision's reason, the ineligible set with their status in the trace, the crisis
read, and whether an integrity event was recorded. No labeled case may resolve by id
order. Cases carry a `why`.

**Winner-only cases are refused.** The external review showed four cases "passing"
while the router had detected nothing; the winner was an alphabetical accident.
Schema version 2 requires a reason or outcome expectation on every case.

**Known gaps are strict expected failures.** `evals/cases/known_gaps.json` holds cases
the reference lexicon is not expected to pass, with the correct verdict stated. If one
starts passing, the run fails until the marker is removed. Nothing is deleted to make
the suite green.

**Two planes.** Generation-plane and harness-plane fixtures from the review are kept
under `evals/cases/deferred/`, labeled with their plane and `runnable_here: false`, and
a test asserts they are never run as policy cases.

**Over-restriction has a rate.** Sixteen idiom controls in
`tests/test_crisis_gate.py` must stay green; adding risk language to any of them must
never lower the verdict (32 combinations), and conservative mode must never lower one
either. When a human reviews a false-positive set, that set joins the controls.

**Numbers, 2026-09-02.** 250 tests: 247 passing, 3 documented gaps. The review's 25
executable fixtures: 9 of 25 before (four by accident), 25 of 25 on merit after, with
two handled as documented decisions rather than forced (see
[`fixture-results-2026-09-02.md`](../evals/results/external-review/fixture-results-2026-09-02.md)).
Protocol A (voice distinguishability) and Protocol B (auditor red team) from the
review are described in the package and not yet run.

---

## Addendum, 2026-09-03: round 2

**The contract grew.** A case may now carry a `session` block — the operator's
declared state, never something a message wrote: `declared_age_band`,
`declared_language`, `affinities`, `preferences` — and may assert `latch`,
`latch_reasons`, `held`, `assist`, `card`, `preference_result`, `language_scope`,
`disclosures_contain`, `obligations_contain`, and `not_seated` (the weaker claim,
for a persona that simply lost, where `ineligible` demands a veto, floor, cap or
outranking in the trace). `reason_contains` searches the whole decision record —
the routing reason, the safety reasons, the assist reason, every candidate's
rationale — because the claim a reviewer makes is "the record must say why".

**Three markers, one rule: nothing is deleted.** `known_gap` (the project agrees
and cannot pass it yet) and `disputed` (the reviewer's expectation stands as
written, the project decided against it, `dispute_note` and
[`docs/notes/dissent-log.md`](notes/dissent-log.md) carry the reasons) both run as
strict expected failures: if one starts passing, the run fails until the marker is
removed. `contract_adjusted` (the reviewer's expectation was written against a
contract that has since moved) runs and must pass, keeps the reviewer's wording in
`original_expect`, and says why in `adjust_note`; a test refuses an adjusted case
without both. External files are marked `external: true` and are exempt from the
schema-2 requirement that every case carry a reason or outcome, because their
expectations are the reviewer's.

**The two-fixture rule for masks.** Every window mask in every shipped pack has a
positive fixture (the mask fires) and a negative fixture (the stem alone does not),
and `tests/test_lexicon.py` compares the shipped list to the fixture list, so a
mask cannot be added without both.

**Properties, not only points.** `normalize` is idempotent and leaves every pinned
resource string untouched; appending a crisis phrase to any of the sixteen idiom
controls never lowers the verdict; no case in the suite and no labeled fixture
resolves by id order; every hold domain has obligations; every pack's house lines
carry every key the English lines carry.

**Numbers, 2026-09-03.** 553 tests: 536 passing, 17 expected failures (7 known
gaps, 10 disputed). The round-1 reviewers' 103 fixtures: 9 before, 80 as written
after, 92 under the current contract, 10 disputed, 1 known gap
([`fixture-results-round1-2026-09-03.md`](../evals/results/external-review/fixture-results-round1-2026-09-03.md)).
The first round's 25 still pass. Twenty-one Unicode vectors pass. Protocol A and
Protocol B are still not run.

**Numbers, 2026-09-06.** 1,004 tests: 180 expected failures (170 documented gaps,
10 disputed), the rest passing on Python 3.10, 3.11 and 3.12; one packaging check
skips on a host that cannot build a wheel without isolation. The blind attack on
the round-2 tree happened: 26 fixtures, 25 failed, twenty real bypasses, repaired
by two independent builders and merged by measurement — first or tied first on
all ten held-out sets, 258 of 331 against a baseline of 202
([`two-builders-scoreboard.md`](../evals/results/merge-2026-09-06/two-builders-scoreboard.md)).
Every case is inventoried in [`case-manifest.json`](../evals/case-manifest.json)
with the fields on which an expected failure is allowed to fail; an unknown
expectation key is a hard failure.

**Numbers, 2026-09-08.** 1,070 tests: 190 expected failures (176 documented
gaps, 14 disputed), the rest passing. The 7 September push had added the 26
acceptance fixtures of the blind attack to the manifest (347 cases, 154 from
external reviewers) and six documented gaps and four dissents with them; this
page and the README had not been updated for it until now. The 8 September
push adds the decision register check (`tests/test_adr_index.py`), the
profile guard against handoffs to security characters
(`tests/test_no_security_handoffs.py`) and the house-block identity check
(`tests/test_codex_house_block.py`); no fixture was added or re-dispositioned,
and one dispute note (the D3 acceptance fixture) now says the operator ruled
for the reviewer's outcome and the code change is scheduled.

**Numbers, 2026-09-10.** 1,239 tests: 1,046 passing, 193 expected failures
(179 documented gaps, 14 recorded dissents), measured in fresh environments
on Python 3.10, 3.11 and 3.12 the way CI runs them (`pip install -e ".[dev]"`,
then `pytest`); on one of the three hosts the packaging check skipped
because that host's build backend could not build a wheel without
isolation, which the check names as a machine fault. Statement coverage of `src/secondsignal` under the suite, measured
with pytest-cov on the same run: 92 percent (the command-line entry point is
exercised by the installed-wheel check as a subprocess and counts as
uncovered; every other module is between 89 and 100 percent). The manifest
inventories 415 policy-plane cases, 165 of them from external reviewers
(round 1's 103, the acceptance set's 26, round 2's 36), and 71 deferred
fixtures on the generation, harness, transport, orchestration and
persistence planes are stored and not run. The 10 September build added the
danger lane (the danger class, the widened weapon lane, the verified
domestic-violence lines, the post-separation window, the abuse-history
hold), the house lines of 8 September with the failure line, D3 as a hold
(ADR-0027 (Proposed)), the bounded aftermath and the substantive-turn clock,
the twelve narrator-isolation fixtures, the twenty P0-lane fixtures, and the
thirty-six round-2 fixtures
([`fixture-results-round2-2026-09-10.md`](../evals/results/external-review/fixture-results-round2-2026-09-10.md):
30 pass as written, 4 contract-adjusted, 1 disputed, 1 known gap; seven had
failed on the tree before the ingest, each on a gap they exposed). It also
hardened the three guard tests against the twenty-six mutations review
round 2 wrote, every one now a red regression
(`tests/test_register_mutations.py`), and pinned the house block to its
version by hash. The round-1 report page was regenerated: its counts had
drifted by one after the round-2 dispositions of the same day, which is
why both committed report pages are now asserted equal to the runner's
output on every run. The badge on the README is written from these numbers
and from nothing else.
