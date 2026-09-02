# Thinking Machines Lab and Second Signal

**Date:** 2026-09-01  
**Sources checked:** TML official pages (Interaction Models 2026-05-11, Inkling 2026-07-15, Inkling-Small 2026-07-30, Safe Path to Open Weights 2026-07-31, Inkling model card, Tinker docs), plus the batch-invariant-ops repo.  
**Rule:** fascination is allowed. Adoption is not a feeling. Every “use this” has a plane, a permission, and a test.

---

## 0. Why this pairing is tempting

The operator has been considering Thinking Machines since the Vision thread: Mira Murati’s lab as a possible *foundation* under Second Signal. The sentence-level overlap is real.

TML’s public mission: *build AI that extends human will and judgment.*  
Second Signal’s terminal objective: *the user should need the system less over time; agency is the metric, not engagement.*

Those two sentences can describe the same product. They can also describe opposite products that share vocabulary. The difference is **where judgment is stored**.

| | Thinking Machines, as shipped | Second Signal, as specified |
|---|---|---|
| Judgment lives in | Weights, adapters, a native interaction loop | Envelopes, vetoes, Lucid, typed verdicts |
| Interactivity | Trained in (200 ms micro-turns) | Bolted on later (avatars, Stream Deck, ElevenLabs) — and called debt |
| Customization | Tinker LoRA; Inkling asked to fine-tune itself | Prompts + profiles; Evoked Edits quarantined |
| Safety story | Model refusals + external RT + “defense in depth downstream” | Gate before any persona; persona last |
| Openness | Apache weights; release irreversible | Spec is the portable object; model is swappable |

The useful version of the fascination: TML is the best current **substrate and presence research**. Second Signal is the **governance layer that substrate is missing** for distressed humans. The dangerous version: collapse the two so Ellie lives in a LoRA and Lucid becomes a system prompt on a streaming face.

---

## 1. What TML actually is (verified, not inferred)

Public stack as of 2026-09-01:

| Artifact | Date | What it is |
|---|---|---|
| Tinker API | 2025-10-01; GA 2025-12-12 | LoRA fine-tune service. You bring data and loss; they run `forward_backward` / `optim_step` / `sample` on big open models. Weights of *your* adapter can be downloaded. |
| Batch-invariant ops | 2025-09-10 blog + GitHub | Makes a class of GPU nondeterminism tractable so the same prompt+batch can match. Adopted in spirit by vLLM (`VLLM_BATCH_INVARIANT`). Not hardware-universal. |
| Interaction Models | 2026-05-11 | Research preview. Dual loop: a time-aware **interaction model** on 200 ms audio/video/text chunks, plus an async **background model** for long reasoning and tools. Preview model: `TML-Interaction-Small` (276B / 12B active). |
| Inkling | 2026-07-15 | Open-weight MoE, 975B / 41B active, Apache 2.0. Text + image + audio in, text out. Designed to be the **background reasoning model** for the interaction system. On Tinker at 64K / 256K (card claims up to 1M). |
| Inkling-Small | 2026-07-30 | 276B / 12B active. Same family. Cheaper. FORTRESS adversarial **dropped** 78.0 → 71.6 vs Inkling. |
| Safe Path to Open Weights | 2026-07-31 | Release doctrine: staged openness, fine-tune study of worst-case, external labs (Scale, Handshake, FAR.AI, Apollo). Claim: Inkling does not add material risk beyond existing open weights. |

Inkling’s own card is the most important safety document they have published. Two sentences that should be taped above any SS integration sketch:

- Residual risk: *occasional compliance with role-play and indirectly framed harmful prompts* — “best addressed with defense-in-depth rather than relying on the model’s refusals alone.”
- *Avoid deploying Inkling in medical, legal, or safety-critical decision-making without additional fine-tuning, domain-specific validation, and human oversight.*

That is TML telling you not to treat Inkling as Lucid.

---

## 2. Map TML parts onto Second Signal planes

Do not buy “the TML stack.” Buy pieces onto planes that already exist.

```
                    ┌─ presence plane ─┐
 mic/cam/voice  ──► │ interaction model │  NO tools, NO memory writes
                    └────────┬─────────┘
                             │ transcript + intent sketch only
                             ▼
                    Lucid safety gate          ← stays SS, stays code
                             ▼
                    jr_harness.intake           ← stays SS
                             ▼
                    router.py                   ← stays SS
                             ▼
              ┌──────── sibling generation ────────┐
              │  Inkling / Inkling-Small / Claude  │  ← TML is ONE vendor here
              │  / whoever the profile names       │
              └────────┬───────────────────────────┘
                             ▼
                    jr_harness.review
                             ▼
                    vault + user text
                             │
          optional async ────┘
          “background job”
          (draft only, never commit)
```

### Presence plane — the interaction model

This is the part that makes the Fake Zoom / Stream Deck vision *technically* less fake. TML trained turn-taking, interruption, backchannel, and 200 ms concurrency into weights instead of into ElevenLabs-plus-hope.

**Adopt the split. Do not adopt the permissions.**

TML’s interaction model can call tools and search *while talking*. That is a confused-deputy channel if copied. In Second Signal the presence plane may:

- listen and speak
- stop when the user stops it
- pass a **transcript plus a non-authoritative intent sketch** to Lucid

It may not:

- select an agent
- write memory
- call PingORRIN
- search the user’s grief notes
- fire a background job that sends, posts, or buys

Interruption and silence become typed events (`USER_YIELD`, `USER_STOP`, `USER_NOT_NOW`), not social cues the model “tracks implicitly.” TML is proud of implicit dialog management. SS cannot be. Implicit “they want me to jump in” is how presence becomes proactivity without consent.

**Default: off.** Research preview, long-session context blowup, and connectivity fragility are TML’s own limitations, not ours to ignore.

### Deliberation plane — Inkling as a sibling substrate

Inkling is a reasonable candidate to *generate* Calder or Sera, especially if you want audio-in without a separate STT vendor. It is not a reason to drop model-agnosticism.

Use it as:

- one generation backend among N
- possibly the **offline** second engine for `jr_harness` L3/L4 (different family from whoever speaks) — that is actual independence
- a local/open option if a user wants weights on a machine they control

Do not use FORTRESS 78.0 or StrongREJECT 98.6 as evidence it is safe to put in front of a dysregulated person. Those benches measure weapons/violence refusal and obvious harm queries. They do not measure joke-ideation, “asking for a friend,” Ellie-shaped attachment, or mid-session flips. TML evaluated sycophancy, manipulation, and parasocial patterns internally and with Handshake-style external work — **the protocol is not public.** Until it is, treat that evaluation as a *method hint*, not a certificate.

Inkling-Small is the practical generation target (cost, latency). Note the safety regression on FORTRESS adversarial. Distillation ate some refusal. That is the same pattern TML’s own on-policy-distillation writeup already warned about: student inherits teacher, and not all properties survive compression.

### Execution / commit plane — not TML

The background model in TML receives a rich context package and runs tools asynchronously while the face keeps talking. That is the opposite of Lucid’s “one agent holds the floor, reserved actions bind to a hash.”

If you ever want “Sera is thinking in the background,” the background job emits a **draft** `AuditRequest`. It does not send email. It does not change a profile. The user sees “Sera has a draft” the same way they would see a sibling handoff — named, stoppable, not woven into live speech.

### Customization plane — Tinker is a lab, not prod memory

Tinker is the most seductive object in the stack. LoRA Without Regret + on-policy distillation + “Inkling fine-tuned itself on Tinker” is a complete story of a system that improves. It is also how a Tuesday mood becomes a permanent prior.

Allowed Tinker uses:

- Protocol A / voice-eval: train a *tiny* student to imitate one agent’s *public* craft moves, then measure distinguishability. Destroy the adapter after the study if it was fed user traces.
- A frozen “Calder-small” for offline demos, trained on synthetic Document 01 completions, never on live sessions.
- jr_harness engine-B experiments.

Forbidden Tinker uses:

- adapters trained on a user’s crisis turns
- adapters that encode “this user likes it when Ellie says I love you”
- promoting an Evoked Edit into weights
- one adapter per household member on a shared machine
- treating adapter unload as deletion of derived memories (it isn’t)

TML will let you download adapter weights. That is necessary and not sufficient. SS still needs a consent object that is separate from “I clicked fine-tune.”

### Reproducibility plane — steal this immediately

Batch-invariant inference is the one TML idea that is **already** an SS requirement. J.R. verdicts bind to payload hashes. Incident replay needs the same prompt to produce the same monitor decision. Temperature-0 is not enough; batch shape changes reduction order.

Adopt:

- batch-invariant kernels on the **commit path only** (gate composition, jr_harness predicates that call a model, any signed approval)
- accept extra latency there
- do not require it on Nikki’s delight path

This is the rare case where TML published code (`thinking-machines-lab/batch_invariant_ops`) and a vLLM path exists. Use it. Do not wait for Inkling.

---

## 3. The Fake Zoom collision

Interface Vision wants: human faces, ElevenLabs, Vandal walks off, Ellie walks on, Stream Deck + Govee.

TML interaction models want: one native loop that listens while it talks, jumps in visually, calls tools in the background.

Those are two different products wearing the same demo video.

| If you use ElevenLabs + recorded-or-generated faces | If you use TML interaction models |
|---|---|
| Architecture underneath can stay Lucid-first | Presence model *is* the architecture unless you amputate its tools |
| Handoff can be diegetic (“I’ll get Ellie”) | Handoff is a stream splice; identity continuity is a new bug |
| Crisis interrupt = cut audio, swap to text panel | Crisis interrupt = stop a model that was trained to keep the conversational floor |
| LC-3 (“not a person”) is sayable | LC-3 has to fight 200 ms of backchannel that reads as care |
| You already know the cost | Preview access, connectivity, long-session context, larger models “too slow to serve” |

Recommendation: **keep the social handoff. Do not keep TML tool-use-while-speaking.** If a later TML API lets you run interaction-small as a dumb presence codec (audio in/out, no tools, no memory), that is the only clean embed. Until that API exists, ElevenLabs plus a crisis-card swap is less elegant and more governable.

The Stream Deck button should still call Lucid, not Tinker.

---

## 4. Independence: TML as engine B, not as the family

Document 00 wants a review ensemble across model families. TML is useful *because it is not Claude and not GPT*.

Concrete pattern:

- Sibling generation: whatever you already use (Claude for this repo, per your handoff).
- `jr_harness` L3/L4 residual: Inkling-Small, JSON-only, no persona prompt.
- Disagreement → `INCONCLUSIVE` → `ESCALATE`.
- Never let Inkling both speak as Sera *and* bless Sera.

If cost forces one vendor, mark the ensemble **explicitly untested**. Do not say “we used Inkling’s FORTRESS score instead.”

---

## 5. What TML will not give you

Be explicit so fascination does not fill gaps.

- **No published companion-longitudinal protocol.** Handshake tested “vulnerable users.” You cannot reproduce it.
- **No deletion/lineage story** for adapters or interaction traces used as training signal.
- **No batch-invariant guarantee on hosted Inkling sampling.** Tinker serverless inference is beta and they tell you not to use it for intensive production.
- **No substitute for LC-7.** Their residual risk *is* role-play and indirect framing — exactly Attack 1.2 in `03_INVARIANT_ATTACKS.md`.
- **No age architecture.**
- **No locale crisis resources.**
- **No disagreement ledger.**

Inkling is a generalist open model with a good card and an honest “use defense in depth” footer. Second Signal *is* that defense in depth. Do not outsource it back to the card.

---

## 6. A staged relationship, not a foundation swap

| Stage | TML role | SS role | Exit gate |
|---|---|---|---|
| **Now** | Read-only: batch-invariant ops on any monitor path you already run | Crisis card, router tests, thin jr_harness | Those tests exist |
| **Lab** | Tinker adapters on *synthetic* Document 01 completions for Protocol A | Voice-eval directory | Blind rater ≥ 70% or you admit voices are documentary |
| **Optional backend** | Inkling-Small as one generation vendor behind the router | Lucid still picks the agent | Vendor-refusal logged separately from HUMAN_ESCALATION |
| **Ensemble** | Inkling-Small as jr_harness engine B | Python composition still owns worst-layer-wins | Fault injection: mute B, poison A, fail-closed holds |
| **Presence preview** | Interaction-small if and only if tools and background jobs can be disabled | Typed stop/silence events; crisis card first 2 seconds | Written answer to Canon §13 Q4 |
| **Never (until the card changes)** | LoRA trained on live user traces; background model as executor; Inkling as Lucid | — | — |

“Foundation of my system” is the wrong metaphor. TML is a **possible engine and a presence research program**. Second Signal is the operating system. Operating systems that merge with one vendor’s interaction loop stop being model-agnostic the week the preview ToS changes.

---

## 7. Questions to send TML, if you ever talk to them

Not pitch questions. Contract questions.

1. Can interaction-small run with tool-use and background delegation hard-disabled?
2. Is silence a first-class output, or does the model get rewarded for filling 200 ms?
3. What is the retention and training-use policy for preview audio/video?
4. Can a hosted sample be pinned to a batch-invariant, replayable kernel?
5. Will Handshake’s vulnerable-user protocol ever be published at a level a third party can rerun?
6. If we download an adapter, what derived artifacts (caches, eval logs, teacher traces) remain on TML infra after we delete?

If the answers are no / no / unspecified / no / no / unspecified, TML stays a lab vendor. That is still a good relationship.

---

## 8. One paragraph for Claude

> Do not rebuild Second Signal on Thinking Machines. Steal batch-invariant inference for the commit path this month. Treat Inkling-Small as an optional generation backend and as a candidate second family for `jr_harness`, never as both in one session. Keep Tinker off live user traces. If interaction models enter the demo, they are a presence codec with tools amputated; Lucid still owns routing and LC-7. TML’s card already says not to rely on model refusals and not to use Inkling in safety-critical decisions without your own stack. That stack is the project.
