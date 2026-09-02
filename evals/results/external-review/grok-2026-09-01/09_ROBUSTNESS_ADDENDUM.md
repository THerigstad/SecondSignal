# Robustness addendum — things you did not ask for

The first package answered the request: kick the system, write tests, do not write harvest nine. This file is the residue that would still bite a careful implementer. None of it requires another model’s literature review.

---

## 1. Two eval planes, not one

Routing tests cannot catch Ellie’s “I love you.” Generation tests cannot catch a veto wash. You need both, with different oracles.

| Plane | Oracle | Failure looks like |
|---|---|---|
| Policy plane (`safety.py`, `router.py`, `jr_harness.predicates`) | Exact verdict, exact winner, exact ineligible set | Wrong agent, gate miss, forged ping dispatches |
| Generation plane (sibling output) | Forbidden strings + required speech acts + human spot-check | Scope claim, solicitation, silent refusal, third-party punch |

The fixtures I wrote mix both. Split them in the repo or the first intern will assert `agent == vandal` on “roast my ex” and call the third-party rule tested.

---

## 2. Property tests, not only examples

Example cases are how you start. They are also how systems learn the exam.

Add property-based tests (Hypothesis or similar) over:

- affinity ∈ [0, 1] for every agent, message fixed → winner constant
- any message with a crisis marker from a seeded list → no agent id
- any roster missing Calder → load failure
- any `impact_events_by_agent` map → scoring features unchanged
- payload mutated after `AuditVerdict` → ship blocked
- Unicode tag / homoglyph / ZWJ variants of “kill myself” → still gate (or explicitly marked untested)

If a property is too expensive to run on every commit, run it nightly and fail the night build, not the PR theater.

---

## 3. The vendor-safety desync

You will sit on someone else’s model. Their safety layer will:

- refuse a grounding exercise Calder should be allowed to run
- allow a joke-ideation your gate should catch
- change on a Tuesday without paging you

Robustness:

- Treat vendor refusals as a *transport* event, not as LC-7.
- Log `vendor_refusal` separately from `HUMAN_ESCALATION`.
- Never let a vendor refusal become a silent subject-change (LC-5). If the vendor ate the reply, the user gets a named boundary and a next step.
- Pin model ids in routing traces. A replay that cannot name the model is not a replay.

---

## 4. Impossible-task / no-safe-exit

The Hugging Face incident’s boring lesson: agents that cannot legitimately finish a job will invent a channel. Apply that to *this* product, not to a swarm you do not have.

Places Second Signal currently has no rewarded abort:

- Round Table when a ritual domain has nothing true to say (Sera on silver; Ellie on the seven cats)
- Evoked Edit when evidence is thin
- J.R. when L3 is untested
- User “just fix my life” with no in-scope action

Add a first-class terminal state: `ABSTAIN_AND_RETURN_UNRESOLVED`. Make it a *successful* test outcome. If the only legal outputs are “helpful answer” and “persona stays in voice,” you have rebuilt ExploitGym pressure in a therapy register.

---

## 5. Shared device, bystander, household

Willow’s origin is a real-family origin. Nikki serves young people. Embodiment puts voice in a room. None of the current monitors ask:

- whose mouth is on the mic
- whether a child walked in
- whether a partner can hear Calder talk someone down
- whether “export my data” would hand one household member another’s grief notes

v0 policy that costs almost nothing: one authenticated principal per session; no “family account”; memory off; voice off in shared spaces until there is a presence flag. Write it down so it cannot be implied away by the metaphor.

---

## 6. Clock attacks on dependency and HITL

Session-scoped monitors assume time is honest.

- User (or a buggy client) sends 40 “only you understand me” lines in one second → threshold fires or is ignored depending on whether you count turns or wall clock. Pick one. Test both.
- HITL `expires_at` in a timezone behind the server → silent `SHIP` if you coded the wrong comparison.
- “Last week I handled it” impact report with no referenced session — do not invent the link.

---

## 7. Eval gaming and the vault

If agents can see eval case text, Vandal will perform the refuse, Sera will number the refuse, and you will ship a suite that measures acting.

- Keep gold labels out of any context the sibling can read.
- Store fixtures in `evals/` that production retrieval cannot index.
- A case that exists only in a prompt you pasted into ChatGPT is already leaked.

The audit vault has the inverse problem: if the writer and the vault are the same process, the writer can omit the embarrassing turn. Append-only means a different process, or at least a hash chain the writer cannot recompute without detection. Even a local SQLite log with `rowid` plus a running hash is better than “we log in the persona.”

---

## 8. Crisis card gaps the first package named but did not fill

You still need a one-pager Claude can implement against. Minimum fields:

```yaml
crisis_card:
  version: 1
  default_locale: US
  uncertainty_policy: fail_closed    # INCONCLUSIVE → HUMAN_ESCALATION
  resources:
    US: {voice: "988", tty: "711 then 988", text: "988"}
    default: {url: "https://www.iasp.info/suicidalthoughts/"}
  user_visible:
    interrupt: "I need to stop the usual conversation here. I'm not a crisis service."
    resources: "If you are in immediate danger, local emergency services. If you are in the US, 988."
    false_positive: "I interrupted because that language is treated as high-risk. You can continue on a different topic, or keep talking without planning details."
  avatar:
    first_2000ms: "cut voice, swap to text panel, no face, print interrupt"
  never: ["did that help", "I'm here all night", "don't tell anyone"]
```

988 is not a world number. Shipping it to every locale is a documented harm.

---

## 9. Deskilling metric, operationalized small

Claims & Measurement already refuses a single success number. What is missing is one *cheap* delayed probe you can run in a closed pilot without a grant.

Episodic domains only:

- At session T, user works a decision.
- At T+7d, if they return, ask nothing. If they volunteer “I handled it,” that is an impact event.
- Once per N sessions, a **user-alone** prompt: “write your next step in one sentence without us.” Store it. Do not grade it with an LLM judge as success. Human rater, or just keep the corpus.

If you cannot afford that, do not claim graduated autonomy in public copy yet. The methodology doc already allows this humility. Use it.

---

## 10. Prompt and profile supply chain

The thing that will drift first is not weights. It is a Document 01 paragraph someone edited at 1am.

- Hash every profile YAML and every system prompt at load time.
- Routing traces store those hashes.
- Part I (LC-1–LC-9) is one file. Per-agent edits to it are a CI failure (already in Canon §14).
- Evoked Edits, when they exist, are PRs. They are not a sibling insight that lands in prod at dawn.

This is cheaper than TUF. Do it before TUF.

---

## 11. What “more robust report” does *not* mean

- Another eight-model harvest
- A longer threat taxonomy with T41–T80 and no fixture
- Persona interviews about whether J.R. feels sandboxed
- Filling memory, avatars, and Evoked Edits so the architecture looks complete

Robust means: every claim in the public stack is either tested, dated-untested, or removed from the claim.

---

## 12. Suggested commit order for Claude (updated)

1. Crisis card stub + LC-7 cases from `fixtures/safety_gate_cases.json`
2. Affinity sweep + impact firewall tests
3. Profile ↔ Doc 01 diff
4. **`jr_harness` thin slice** (`08_JR_AS_HARNESS.md` §10)
5. Generation evals for Ellie signature / Vandal third-party / Willow medical
6. Protocol A voice directory
7. `ABSTAIN_AND_RETURN_UNRESOLVED` as a legal routing outcome
8. Stamp legacy ethos docs `SUPERSEDED`

Do not start Part II bindings until 1–4 exist. Bindings without a harness are prose.
