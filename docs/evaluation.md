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
