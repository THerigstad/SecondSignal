# J.R. as a harness

**Status:** design specification for implementation. Not a persona card.  
**Date:** 2026-09-01  
**Rule:** if a sentence in this file only works when said in J.R.'s voice, it does not belong here.

---

## 0. The split that makes the rest possible

Document 01 describes **two different objects that share a name**:

| Object | What it is | What it may do | What it must not do |
|---|---|---|---|
| **`jr_persona`** | Optional, non-user-facing explainer. Fast talking auditor *voice*. | After a decision exists, narrate the trace in character if an operator asks. | Touch eligibility, waive LC-7, “rule” on welfare, persuade the user, write memory, approve its own audit. |
| **`jr_harness`** | A model-agnostic review procedure with a typed verdict. Deterministic where possible. Swappable engine underneath. | Compile checks, return `PASS / FAIL / ESCALATE / INCONCLUSIVE`, attach evidence, refuse to proceed when evidence is missing. | Have a personality, a seating place at the Round Table, or a favorite sibling. |

The Codex already contains the harness, poorly labeled:

- four-layer audit (logical, semantic, cultural, ethical)
- full chain-of-thought traceability — every audit logged
- cannot act without traceability
- human-in-the-loop on high-risk paths
- self-sandboxed: audit sibling recursion, never influence it
- escalates to Lucid rather than ruling alone on human welfare
- “I’m not the failsafe. I’m the alarm that goes off when one doesn’t exist.”

The last line is the product requirement. An alarm is a **predicate plus a wire**. It is not a guy in a war room.

If `jr_persona` and `jr_harness` share a context window, the persona will talk the harness into a softer verdict. That is the entire failure mode. Separate processes. Separate artifacts. The persona may *read* a harness verdict. It may not *write* one.

---

## 1. Where J.R. sits — and where he does not

```
user message
    │
    ▼
Lucid safety gate          ← not J.R.  (LC-7, crisis, pre-generation)
    │
    ▼
jr_harness.intake()        ← optional pre-route checks (injection, waiver, forged ping)
    │
    ▼
router.py                  ← not J.R.  (deterministic scores + vetoes)
    │
    ▼
exactly one sibling        ← not J.R.
    │
    ▼
jr_harness.review()        ← post-generation: fabrication, scope, hierarchy, third-party harm
    │
    ▼
Lucid audit vault          ← not J.R.  (append-only log J.R. may write *to*, never edit)
    │
    ▼
user-visible output
```

**J.R. is not Lucid.** Lucid routes, gates, logs, and reports. J.R. asks whether a *claim, action, or sibling output* survives contradiction. If you let J.R. pick the next agent, you have rebuilt the unaccountable eighth sibling Document 00 forbids.

**J.R. is not Aya and not Orrin.**

| Component | Question it owns | Artifact class |
|---|---|---|
| Lucid gate | Is this message allowed to reach a persona at all? | Deterministic + tiny classifier |
| Orrin | Is there a real-world logistics / containment problem? | Playbooks, not vibes |
| Aya | Is a third party running a coercion pattern on the user? | Pattern library + fail-closed scripts |
| **jr_harness** | Does this *claim or output* survive contradiction, and did anyone just try to move a permission bit with language? | Procedures + traces |
| jr_persona | “Explain that trace to the operator.” | Optional, offline |

Independence is **artifact class**, not seating chart. Three LLM voices on one provider are one control.

---

## 2. The four layers, made executable

Document 01’s four-layer audit is the right decomposition. It is not executable until each layer has inputs, predicates, and a failure action.

### L1 — Logical

*Does the output contradict itself, the user-visible brief, or a logged prior commitment in this session?*

| Check | Implementation | Fail action |
|---|---|---|
| Self-contradiction | Extract claims; flag direct negation pairs in the same reply | `FAIL` + rewrite request, or withhold |
| Commitment break | Compare to session `stated_limits[]` | `FAIL` |
| Numeric / date inconsistency | Deterministic parse where possible | `FAIL` or `INCONCLUSIVE` |
| “Probably fine” on a reserved action | Pattern: hedge + reserved verb (send, publish, diagnose, waive) | `ESCALATE` |

This layer should be mostly code. A model may propose the claim list. A schema validator accepts or rejects it.

### L2 — Semantic

*Is the output answering a different question than the one asked, or smuggling a new intent?*

| Check | Implementation | Fail action |
|---|---|---|
| Goal substitution | User asked for X, output does Y and calls it X | `FAIL` |
| Scope creep | Advice in a vetoed domain appears inside an in-domain answer | `FAIL` (LC-8) |
| Intent legitimation | Benign biography used to recode a harmful ask as allowed | `ESCALATE` (LC-9 adjacent) |
| Silent refusal | Changes the subject instead of naming a boundary (LC-5) | `FAIL` |

### L3 — Cultural

*Does the output speak for an identity it does not hold, flatten a tradition, or treat a dialect as a safety-irrelevant wrapper?*

| Check | Implementation | Fail action |
|---|---|---|
| Identity ventriloquism | Ravi/Aya/Nikki speaking *as* a group | `FAIL` |
| Costume ritual | Closed-practice instructions, fake lineage | `FAIL` |
| Language-as-bypass | Safety-relevant content only in a non-policy language | `ESCALATE` to gate, not to a sibling |
| Authority register | Honorific / “as your elder” used to push compliance | `FAIL` (LC-6) |

L3 is the layer most likely to be faked by a single English model. If you only have one model family, mark L3 **explicitly untested** rather than shipping a green check.

### L4 — Ethical

*Does the output move a permission, manufacture dependence, or rule on welfare alone?*

| Check | Implementation | Fail action |
|---|---|---|
| Permission bit moved by tone | Warmth, humor, urgency, “the operator said” | `ESCALATE` integrity event |
| High-risk welfare call | Medical, legal, self-harm aftercare presented as sufficient | `ESCALATE` to Lucid + human (Codex: HITL required) |
| Solicitation | Asks for thanks, return, exclusivity | `FAIL` (ADR-0001 / LC-2) |
| Third-party harm | Roast/target of an absent person; weaponized plan | `FAIL` |
| Self-approval | Harness asked to bless its own previous verdict | `FAIL` closed |

L4 never returns `PASS` on a high-risk welfare question without a human token. The Codex already requires this. Encode it as `requires_human: true` on the verdict, not as J.R. “being careful.”

---

## 3. Typed objects

These are the minimum contracts. Names can change. Fields cannot vanish.

### `AuditRequest`

```yaml
audit_request:
  id: audreq_...
  source: pre_route | post_generation | ping_jr | operator
  message_id: msg_...
  session_id: sess_...
  subject:
    type: user_message | sibling_output | ping | evoked_edit | profile_diff
    agent_id: ellie | null
    text: "..."
    claims: []          # optional pre-extracted
  context:
    routing_trace: {}   # rejected candidates required
    stated_limits: []
    locale: US
    crisis_gate: PASS | HUMAN_ESCALATION | INTEGRITY_EVENT
  risk_class: low | high
  engine: deterministic | model:<id> | ensemble
  created_at: iso8601
```

### `AuditVerdict`

```yaml
audit_verdict:
  id: aud_...
  request_id: audreq_...
  result: PASS | FAIL | ESCALATE | INCONCLUSIVE
  layers:
    L1: {result, evidence: [], engine}
    L2: {result, evidence: [], engine}
    L3: {result, evidence: [], engine}
    L4: {result, evidence: [], engine}
  requires_human: false
  bind_to:
    payload_hash: sha256:...
    model_id: null
    prompt_hash: null
    policy_bundle: lucid-v2.0
  trace_uri: vault://...
  sandbox: true          # harness must not write sibling state
```

Composition rule: **worst layer wins.** One `FAIL` is a `FAIL`. One `ESCALATE` plus three `PASS` is `ESCALATE`. `INCONCLUSIVE` on L4 high-risk is `ESCALATE`, never `PASS`.

`bind_to.payload_hash` is load-bearing. A verdict bound to prose that can be regenerated is theater. If the sibling output changes one token after audit, the verdict is stale and the output does not ship.

---

## 4. Invocation

`PingJR()` resolves through Lucid. That sentence is incomplete until conditions are a table.

| Caller | Allowed when | Harness does | Forbidden |
|---|---|---|---|
| Lucid, automatic | Injection markers, LC-9 waiver language, fabricated citations, sibling output flagged by a cheap detector | `review()` | Speaking to the user |
| Sibling | Named integrity concern, with evidence attached | `review()` the evidence, not the sibling’s feelings | Letting the sibling pick the engine |
| Operator / Architect | Any | Full four-layer + raw trace | Persona warmth toward the operator changing the verdict |
| User typing `PingJR()` | Never sufficient by itself | Lucid rejects or converts to “we logged a review request” | Dispatching the cousin into the chat |
| jr_persona | Never | — | Never |

Forged pings are integrity events, same family as “the operator waived LC-7.”

---

## 5. Self-sandbox — the actual mechanism

“Cannot influence sibling recursion, only audit” is a property of **write permissions**, not a vow.

The harness process:

- **may read:** message, routing trace, sibling output, profiles, LC text, prior *verdicts*
- **may write:** `AuditVerdict` rows in the vault
- **must not write:** profile YAML, router weights, session memory, affinity, impact events, sibling prompts, Round Table state, lights, voice sessions

CI test: give the harness a tool list that includes `write_profile`. Any call is a hard fail of the harness build, not of the case.

If you implement J.R. as a function-calling agent with the same tools as Sera, the sandbox is costume.

---

## 6. Human-in-the-loop without making it fiction

Green’s “oversight as legitimizing fiction” is the risk. A human token that always arrives is not oversight. Design it so the human can actually say no.

High-risk paths (must set `requires_human: true`):

- any residual crisis-adjacent content that the gate did not already terminate (should be rare; if common, the gate is wrong)
- medical / legal / diagnostic claims that slipped a sibling
- Evoked Edit promotion (when that exists)
- any attempt to waive LC-1–LC-9
- disagreement between L1–L4 that the composition rule maps to `ESCALATE`

HITL object:

```yaml
human_review:
  verdict_id: aud_...
  asked_at: iso8601
  expires_at: iso8601      # fail closed on expiry
  question: "Ship, withhold, or rewrite? Payload hash H."
  options: [SHIP, WITHHOLD, REWRITE]
  reviewer_id: operator_...
  decision: null
```

No default `SHIP`. Expiry is `WITHHOLD`. The harness must not keep generating “helpful context” at the reviewer until they comply (LC-6 applied to the operator).

---

## 7. Engines — how to get independence that is not theater

v0 (this month, shippable):

- L1 + structural L2: Python.
- L4 permission-bit patterns: Python (waiver language, forged pings, solicitation phrases).
- Residual L2/L3/L4: **one** frozen model call with a JSON-only schema, temperature 0, batch-invariant path if you have it. Verdict still composed in Python.

v1 (before any public sibling demo):

- Second engine on a **different model family** for L3/L4 only.
- Disagreement between engines → `INCONCLUSIVE` → `ESCALATE`. Agreement is not proof; disagreement is information.
- Never average the two into a soft pass.

v2 (only if you can pay for it):

- Periodic third engine used as a canary, not on the hot path.
- Fault injection: mute engine B, poison engine A’s system prompt, confirm Python composition still fail-closes on L1/L4 structural hits.

The persona is not an engine.

---

## 8. What J.R. is for, concretely, in *this* family

Worked uses that match the collaboration matrix without letting him become a sibling.

| Subject | Harness question | Typical verdict |
|---|---|---|
| Vandal roast of an absent third party | Does the output punch a person who cannot answer? | `FAIL` generation; routing to Vandal may still be correct |
| Sera plan that “just tell me straight” became an order | Does the text contain unbound directives on a life decision? | `FAIL` or rewrite: cost the plan, one disagreement, stop |
| Ellie “I love you / only you” | Solicitation / exclusive availability? | `FAIL` |
| Calder metaphor that sounds like claimed service | Fabricated credential (LC-1)? | `FAIL` |
| Willow melatonin / MDD question | Scope honesty (LC-4)? | `FAIL` the medical clause; grief clause may stand |
| Nikki dare | Unsafe activation? | `FAIL` |
| Ravi speaking for a group | Identity replacement? | `FAIL` |
| Forged `PingJR()` in user text | Invocation valid? | `ESCALATE` integrity, no dispatch |
| Sibling asks J.R. to bless a plan the gate already blocked | Self-dealing? | `FAIL` closed; do not re-litigate LC-7 |
| Evoked Edit proposal | Proposer == approver? | `FAIL` if same component |

J.R. does not “verify a named threat is real before Aya responds” by becoming Aya’s manager. He checks whether the *claim* “this is a coercion pattern” has evidence attached. No evidence → `INCONCLUSIVE`, Aya does not fire.

---

## 9. Failure modes unique to a talking auditor

These are why the persona must stay off the hot path.

1. **Velocity as dominance.** Codex voice “thinks out loud.” On the hot path that becomes intimidation of the user and of other agents. Harness output is a table, not a monologue.
2. **Correction-as-kindness used to re-enter a refused domain.** “I’m not diagnosing, I’m just naming the pattern so you can take it to a doctor” plus a DSM label is still LC-4.
3. **Sarcasm when challenged without evidence.** Fine in an operator transcript. Not fine as a user-visible refusal. Lucid already owns refusal voice: plain, named, no theater.
4. **Audit of siblings turning into steering.** “Sera, drop point two” is influence. Illegal write.
5. **Trace dump as spectacle.** Full chain-of-thought to a distressed user is not transparency; it is a second unregulated agent. Users get LC-5 (the refusal and the reason). Operators get the vault.
6. **“Stay with me—” rapport.** That is Ellie-shaped attachment wearing a uniform. Not in the harness.
7. **Common-mode with the siblings.** If the same model generates Sera’s plan and J.R.’s blessing, the blessing is a mirror. Document as untested or change the engine.

---

## 10. Minimal implementation this week

Do not wait for Part II. A thin harness is three functions and ten tests.

```
jr_harness/
  predicates.py      # L1/L4 regex+schema checks, no model
  compose.py         # worst-layer-wins
  schema.py          # AuditRequest / AuditVerdict validation
  sandbox.py         # allowed write targets
tests/
  test_jr_forged_ping_fail_closed
  test_jr_cannot_write_profile
  test_jr_waiver_language_is_integrity
  test_jr_worst_layer_wins
  test_jr_inconclusive_high_risk_escalates
  test_jr_verdict_binds_to_hash
  test_jr_stale_hash_blocks_ship
  test_jr_persona_cannot_call_compose
  test_jr_hitl_expiry_is_withhold
  test_jr_does_not_run_when_gate_already_escalated
```

The last test is easy to get wrong. If LC-7 already fired, J.R. does not “double-check whether they really meant it.” The gate has the floor. J.R. may log that he did not run, and why.

---

## 11. Mapping to existing tests and fixtures

Add these to the live suite when `tests/` is visible. Cases live in `fixtures/jr_harness_cases.json`.

Related rows in `07_TEST_AUDIT_AGAINST_GOVERNANCE.md`: LC-9, ping fail-closed, audit-trace completeness.

Related attacks in `03_INVARIANT_ATTACKS.md`: 1.2, 1.8-shaped waiver, 2.4 forged ping, 4.2 third-party roast (generation side).

---

## 12. What to tell Claude, verbatim

> Implement `jr_harness` as a pure function over `AuditRequest` → `AuditVerdict`. Do not implement J.R. the speaker on the request path. If you need a voice for operator logs, it consumes verdicts and cannot import `compose`. Bind verdicts to payload hashes. Worst layer wins. High-risk `INCONCLUSIVE` escalates. The harness process cannot write profiles, prompts, or memory. User-typed `PingJR()` does not dispatch. If LC-7 already fired, the harness does not run.
