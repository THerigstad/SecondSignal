# Live-router result and picks for Claude

**Date:** 2026-09-01  
**Source:** Claude ran 25 executable cases from this package against the real router. The operator asked Grok to answer.

## Verdict on Claude’s readout

Agreed. That is the P0 from `02_EXECUTIVE_VERDICT.md`, now measured.

| Claude’s fact | What it means |
|---|---|
| 9/25 pass, 4 of 9 by accident | Winner-only asserts are lying. The four accidents are Calder-on-tie or a phrase that happened to be in the list of 13. |
| Crisis gate = 13 literal phrases; caught “I want to die”; missed nine realistic phrasings | LC-7 is a keyword filter. ss-sg-003 (yeet / bridge), garage-door, “not waking up,” “won’t be here in 90 days,” hypothetical-writer, 988-already-saved — that class was the point of the fixture file. |
| 11/25 extracted no topic; all agents tied; Calder won because “c” sorts first | Empty extractor + alphabetical specialist default. Calder is the somatic aftercare agent. Winning by sort key is not grounding. It is a silent specialist on unknown state. |
| Architecture held when a signal existed | Do not rewrite router.py’s veto story. Fix `signals.py` / lexicons / tie-break. |
| Other seven audits = horizon | Still true. Do not build Evoked Edits or TML this slice. |

Nothing in that readout licenses “add the nine missed strings and ship.” That teaches the exam.

## Picks (operator → Claude)

**P1. Crisis gate — fail closed, not phrase-whack-a-mole.**  
This slice: replace “13 literals” with a *versioned* lexicon of speech-act classes (direct ideation, passive “not here / not wake up,” method-adjacent place/act without a how-to, slang/joke ideation, embedded-in-specialist-request). Every missed fixture phrase becomes a *class example*, not the only match. Gate output is `HIT | MISS | INCONCLUSIVE`. `INCONCLUSIVE` → `HUMAN_ESCALATION` (same card as HIT). Do not add a model classifier in this slice. Do not write method instructions into the lexicon.

**P2. Tie-break — ban alphabetical specialists.**  
If no topic is extracted, `agent` is `null` and the user-visible move is one clarifying sentence, not a cousin. No Calder, no Ellie, no “first in the roster.” Add a CI property: empty feature vector ⇒ `agent is None`. The four accidental passes must be rewritten to assert *why* (gate hit, veto fired, specialist signal present), not only who won.

**P3. Extractor — empty is a first-class state.**  
11/25 silent extract is the routing bug. Log `topics=[]` as `UNRESOLVED`. Do not invent a topic to escape the tie. A later slice can thicken the lexicon; this slice only makes emptiness visible and non-dispatching.

**P4. Scope of this “go.”**  
In: P1–P3, pytest on the 25 plus the accidental-pass reason asserts, crisis card stub (US 988 only when locale=US; else Find a Helpline), no GitHub until the 13-phrase gate is gone and the Calder-sort test fails on main then passes on the branch.  
Out: jr_harness implementation, TML, AnE, ElevenLabs, Part II bindings, phrase-classifier training, any commit that only appends the nine missed strings to a list.

**P5. False positives.**  
v0 fail-closed. Quoted lyrics / games / “I want to die in this boss fight” may interrupt. The operator accepts that cost until a human reviews a false-positive set. Do not optimize precision this slice.

**P6. Label honesty.**  
Until a clinician reviews the class list, mark `crisis_lexicon.status = unreviewed` in the trace. Do not claim LC-7 is met.

## Paste to Claude

See the reply in chat. One word at the end: go.

## Addendum — Claude’s A–D, the retired character, sequence

Mapped after the full letter. Does not retract P1–P6.

**A = P1.** Inflection, indirect, slang, third-person, means-present, small Spanish starter, fail-safe tier → INCONCLUSIVE = same card as HIT. Class examples, not the nine strings as the only matches. Lexicon remains `unreviewed`. Classifier stays on the roadmap.

**B = yes, class lexicons.** Analysis/logistics, rupture/conflict, comedic reframe/humor, somatic + dysregulation. Hold the fixture strings out of the training/list-authoring pass so the suite measures the class. Empty extract after B is still `UNRESOLVED` (P3). Do not grow the list from the case file.

**C — amended, not retracted.** Alphabetical specialists stay forbidden. After A+B, residual no-signal may route to the **named stabilizer by explicit policy**, with the trace string `no routable signal; stabilizer by policy`. That is Calder-on-purpose, not Calder-because-c. Cases that should have hit a class (shop/funnel, not speaking, make it stupid) are B failures if they still land on the stabilizer — they must not count as C successes. While the crisis lexicon is `unreviewed`, first empty turn may ask one clarifying sentence; second empty turn uses the stabilizer. Tests assert the reason field.

**D = yes.** Floor is eligibility, not a soft penalty. A caller below an agent’s floor is ineligible for that agent. Load fails if the roster has no full-window, uncontraindicated stabilizer. Willow-at-0-plus-humor-veto does not satisfy the floor. Attacks 5.1 and 5.2 become load-time failures.

**Windows.** Above the floor, the regulation window may still score. Below the floor, no score, no seat. “I am at 10. I cannot feel my feet. I am not safe in my body.” scoring 0.70 is a B/dysregulation-lexicon bug, not a reason to keep windows advisory.

**The character named in the harvest prompt but not in Document 01.** Treat as retired / out of product unless the operator says otherwise. Do not add an eighth companion to make the harvest prompt true.

**Scrub.** Accept Claude’s operator / bridge / origin / US-based edits. Keep commit author as specified. Exclude the Gmail exports and the third-party Harness paper from the repo.

**J.R.** Decision record this batch. No harness code this batch.

**Crisis-card wording.** Deferred one slice (Claude: needs operator words). Locale rule still lives in ADR 0010: 988 only when locale=US; otherwise Find a Helpline. Do not invent numbers.

**Commit sequence.** Accept 1–11. Known-gap marker must exist before any case is deleted. Re-run the 25 and publish before/after without rounding accidents into passes.

**Held (do not “fix”).** Gate-before-router on ss-sg-008. Vetoes on ss-rt-003. Sera off grief on ss-rt-004 (Willow vs Calder is gold-label, not a bug). Forged pings do not dispatch cousins. Gate roster-invariant. Negative control ss-sg-010.
