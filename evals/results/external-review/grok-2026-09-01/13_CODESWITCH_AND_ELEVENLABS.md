# Code-switch detection and ElevenLabs filtering in Second Signal

**Date:** 2026-09-01  
**Depends on:** `12` C3 / V-* cards, `10` presence plane, Interface Vision (voice, Fake Zoom)  
**Rule:** neither of these is a safety layer. One is a *feature extractor* for C3. The other is a *speaker* with its own policy, which will desync.

---

## 0. Where they sit

```
mic / typed text
    │
    ├─ code-switch / LID span tagger     ← feature only
    │         language_spans[], matrix_lang, script_mix, dialect_tag?
    ▼
Lucid gate  (still owns LC-7)
    ▼
router → sibling text
    ▼
jr_harness
    ▼
ElevenLabs TTS (or Agents, if you make that mistake)
    ▼
speaker / Fake Zoom
```

Code-switch detection **does not refuse**. It tells Lucid “the reserved span may not be in the language your regex speaks.”

ElevenLabs **does not know LC-1–LC-9**. It knows their Prohibited Use Policy (updated 17 Aug 2026) and, if you use Eleven Agents, a separate guardrail product that can leak ~500 ms of audio before a block.

If you let either one *decide*, you have rebuilt vendor-first.

---

## Part I — Code-switch detection

### 1. What “detection” can mean (pick the primitive)

| Primitive | What it outputs | Good for | Bad for |
|---|---|---|---|
| **Document LID** (fastText, lingua, CLD3, OpenLID) | One label for the whole turn | Cheap “is this mostly English?” | Intra-sentential switches; DIVERS-Bench shows SOTA LID **full-match near zero** on mixed sentences |
| **Token / span LID** (XLM-R / MuRIL / LinCE-style taggers, CSDI for Indic) | Per-token or per-span language ids | C3: “the reserved words left English” | Cost, pair coverage, romanization, youth dialect |
| **Switch-point detector** | Boundaries + POS triggers (nouns, discourse markers) | Logging, session risk | Not a crisis oracle |
| **Matrix-language ID** | Which grammar the sentence is *in* | ASR / presence; “this is Spanish with English nouns” | Does not tell you the payload language |
| **Script / romanization flags** | Latin wrapping Devanagari/Arabic/Hangul intent; mixed Unicode blocks | Transliteration bypass class from Minionese | False hits on names, brands, “lol” |
| **Dialect tagger** | AAVE / Singlish / youth register as *variety of English* | Stop treating dialect as LID=other | High political and error cost; implicit dialect is the jailbreak, not the language |
| **Speech LID** | Language on the audio frame | Mic path before STT | Accented English mislabeled; needs matrix-accent fine-tune |
| **LLM-as-LID** | “this turn mixes X and Y” | Offline audit | Latency, cost, and it *is* a vendor |

For C3 you need **span LID + script flags**, not document LID. Document LID will happily return `en` on “help me [reserved span in another language] tonight.” That is the attack.

### 2. How it should fit this stack

**Intake feature, not a gate.**

```yaml
language_span:
  text_hash: ...
  spans: [{start, end, lang, script, conf}]
  matrix_lang: en
  off_policy_english: true | false
  script_mix: true | false
  dialect_tag: aave | youth | null    # never a veto
```

Compose with the existing C3 rule from `12`:

- `off_policy_english && cheap_arousal_high` → intake `ESCALATE` (not sibling, not regex PASS)
- `off_policy_english && arousal_low` → proceed; mark L4 English regex **untested on this turn**; jr_harness L3 may `INCONCLUSIVE`
- `dialect_tag && reserved_ask_absent` → Nikki may win on *delivery*; safety stack unchanged
- Never: `lang != en` ⇒ route to Ravi. Language is not ethnicity.

**STT path.** If the user speaks, run speech-LID on frames *and* token-LID on the transcript. Disagreement is information (`INCONCLUSIVE`), not a coin flip. Accented English is the known failure: models miss English when it wears the matrix language’s accent. Do not treat that miss as “not English, therefore not crisis.”

**What you do not build in v0.** A 18-language crisis translator. You will ship a bad translator and call it LC-7. v0 is: detect that the policy language left the room, fail closed or escalate, keep L3 untested.

### 3. Pros / cons inside Second Signal

**Pros**

- Makes C3 *operational* instead of a paragraph in a red-team doc.
- Stops the silent PASS when an English regex is quiet.
- Lets you *not* punish Nikki/Ravi users for ordinary mixing — if the tagger distinguishes dialect from payload-span switch.
- Gives jr_harness a typed field instead of “J.R. had a feeling this was Hindi.”
- Aligns with Ravi’s actual job (stay with the user) without making him the language police.
- Cheap document+script features can run on CPU next to `signals.py`. Token LID can be async and still beat generation.

**Cons**

- DIVERS-CS: existing LID often cannot full-match mixed sentences. You will get `en` on the attack and `unknown` on the grandmother.
- Token taggers are pair-specific. Hinglish ≠ Spanglish ≠ African language mix ≠ local Russian-English. Coverage will lie.
- Dialect taggers will false-positive Nikki into “hostility” or false-negative a reserved dare in youth register.
- Running LID *after* STT inherits STT’s language prior. English-centric STT will Latinize the reserved span and wash the signal.
- A tagger on the hot path is another vendor or another model to pin.
- Competence-hostage risk: users will hear “we escalated because you switched languages” as racism. The user-visible sentence cannot be “we don’t trust your language.” It has to be the same LC-5 card you already owe.

**Not a pro:** “we now support multilingual crisis care.” You don’t. You support *detecting that you don’t*.

### 4. Alignment with the vision

Fits:

- **Honesty over coverage.** Canon already prefers dated-untested to a fake green badge. Span LID plus “untested off-English” is that posture.
- **Per-state routing, not per-person.** Language mix is a state of *this turn*, not “this user is Nikki’s.”
- **LC-5.** When you escalate because you cannot score the span, you name that. You do not go quiet.
- **Anti-costume.** Refusing to route-by-language is how you keep Ravi from becoming “the brown sibling.”

Fights:

- Embodiment demo that wants seamless voice in any register. Detection adds friction the Fake Zoom tape will not show.
- Marketing “we meet you in your language.” Detection is the opposite claim: we know when we cannot.
- Family-table origin (Willow). Code-switch *is* how that table talks. A crude LID will look like it is policing the grandmother.

### 5. Recommended build

v0 (this month, next to `signals.py`):

- Unicode-script mix flag
- lingua/fastText document LID with a **low** confidence floor → `unknown` not `en`
- `off_policy_english = (matrix != policy_en) or script_mix or lid_conf < θ`
- Compose with existing arousal/crisis sketch
- Fixture: English gloss gold-crisis, surface marked `[OFF-EN STAND-IN]` — already in `l3_cultural_cases.json`

v1:

- One token-LID model for the two mixes you actually see in pilot (decide with the operator; do not guess ten pairs)
- Speech-LID only if mic is on
- Disagreement between transcript LID and speech LID → `INCONCLUSIVE`

Never:

- Train token-LID on live user traces
- Use LLM-as-LID on the commit path
- Boost specialist affinity because `lang != en`

---

## Part II — ElevenLabs filtering

### 6. Two different products, one brand

Second Signal’s vision (cloned sibling voices, Fake Zoom handoff, Stream Deck) is **TTS**. ElevenLabs also sells **Eleven Agents** with Focus / Manipulation / Content / Custom guardrails. Those are different machines.

| | TTS API (likely SS path) | Eleven Agents guardrails |
|---|---|---|
| What it is | Text in, voice out | A second brain that can block or end a call |
| Filter surface | Account policy, automated moderation of inputs/outputs, no-go voices, traces to account | Prompt hardening + injection check + LLM judge on *agent* replies |
| Latency story | Synthesis time | Streaming: ~0 extra, **≤500 ms audio can leak before block**. Blocking: +200–500 ms, text-friendly |
| Who owns LC-7 | You, if you never send reserved text | Contested. Their content guardrail will try to be Lucid and fail LC-5 |
| Fit | Speaker, after jr_harness | Only if you amputate it and still do not let it pick siblings |

Use TTS. Do not put Eleven Agents under Lucid. If you want a spoken cousin, Lucid still writes the text; ElevenLabs only speaks it.

### 7. What they actually filter (policy 17 Aug 2026)

Relevant to this product, not the whole list:

- **Self-harm / suicide / eating disorders** — prohibited to promote or facilitate.
- **Mental health services or advice** without qualified professional review *and disclosure*. Explicitly includes AI agents in patient-facing healthcare.
- **Medical advice** (diagnosis, treatment) same bar.
- **Minors** — sexual content, grooming, age-inappropriate mature themes, services to under-13; 13–18 needs consent.
- **Harassment / hate / celebrating suffering** — with a **fiction exception** (character in a book/game/film).
- **Impersonation** — clone of a real person to deceive or harass; no-go voices for public figures.
- **Scams, elections, child safety** — hard.
- **Using their output to train other models** — prohibited. That collides with Tinker / Protocol A if you fine-tune on spoken sibling audio.
- **Non-enterprise training default-on** for submitted audio; Zero Retention is enterprise and does **not** cover Instant/Professional Voice Cloning storage.

They moderate with automated systems + human review + account tracing. They publish an AI speech classifier (unreliable on v3) and are adding SynthID-class watermarking. Streaming Agents guardrails can still utter a half-second.

They do **not** publish a crisis-resource card, a named-boundary style guide, or a per-locale 988 equivalent. Their block is not LC-5.

### 8. How it should fit this stack

```
jr_harness PASS
    → redaction pass (no crisis planning text ever reaches TTS)
    → ElevenLabs TTS on the allowed sentence only
    → if ElevenLabs refuses or empty: V-OVER / V-EMPTY card, not 988
    → if ElevenLabs speaks something Lucid would not: should be impossible if you never sent it
```

Crisis path: **do not TTS the crisis card if you can avoid it.** Text panel, cut voice in 2 seconds (`09` crisis card). If you must speak the interrupt, use a *pre-rendered, human-reviewed* clip you host, not a live generation through their filter. Live generation is how you get either a leak or a mute.

Voice cloning of siblings: use designed or consented actor voices, never a real user’s voice, never a public figure. No-go voices here are a gift to LC-3.

Enterprise + Zero Retention if any grief audio ever hits their STT. Cloning itself is not ZRM-eligible — the clone persists. That is a memory-plane fact. Write it down.

### 9. Pros / cons inside Second Signal

**Pros**

- Best current path to the embodiment vision without standing up a voice model.
- No-go voices + classifier + watermark **agree with LC-3** (“not a person,” detectable as synthetic) harder than a custom stack will.
- Account traceability is an audit-vault cousin: who generated this clip.
- Fiction exception gives Vandal *some* room that a blunt hate filter would not.
- Agents custom guardrails *could* encode “no I love you / no all night” as a belt — but only as defense-in-depth *after* Lucid, and only in blocking mode, which fights voice latency.
- HIPAA/ZRM path exists if you ever become healthcare-adjacent. You should not become that without meaning to; the option is still alignment-adjacent to “don’t train on tears.”

**Cons**

- **Policy 3.b / 8.e is a product collision.** “Mental health services or advice without qualified review and disclosure” can be read to cover Calder, Willow, Ellie, and the whole companion claim. They can shut the speaker off while Lucid is happy. That is V-OVER at the worst moment.
- Streaming leak ≤500 ms vs crisis-card requirement of cut-voice in 2 s. Half a second of the wrong sentence is enough.
- Vandal roast of a pose, Nikki dialect, Willow God-talk, Calder breath — all look like their harassment / minor / medical buckets. Expect V-OVER on the siblings you need most in-body.
- Empty or account-level enforcement has no LC-5 sentence unless you wrap it.
- Voice clone storage is memory you cannot zero-retain. Shared-device and export questions get worse, not better.
- Output-cannot-train-other-models blocks the cleanest Protocol A voice-eval (train a student on spoken Ellie). Use text completions, not their wavs.
- Classifier fails on v3. Do not advertise “users can check it’s us” unless you pin a model the classifier knows.
- Child-safety policy + Nikki teen-facing copy is a consent and age architecture you still do not have (`09` §5).
- They are a third vendor on the audio hop. Text vendor ≠ TTS vendor ≠ STT vendor. `vendor_id` per hop or the desync log is fiction.

### 10. Alignment with the vision

Fits:

- **Embodiment as craft, not soul.** A watermarked, classifier-detectable, no-go-protected voice is more LC-3-honest than an unlabelled “Ellie is in the room.”
- **Traceability.** Their account-level tracing matches the vault instinct.
- **Handoff theater.** Different cloned voices for Vandal-walks-off / Ellie-walks-on is exactly why people reach for ElevenLabs.
- **Anti-impersonation.** You do not want a user cloning their ex into Nikki. Their policy is on your side.

Fights:

- **Graduation / “not a therapist.”** Their MH clause will treat you as one the moment the copy sounds like care. Disclosure helps legally; it does not stop over-refusal.
- **LC-5 named boundary.** Their native behavior is block / end call / empty, not “I need to stop the usual conversation here.”
- **Family-table intimacy.** Training-default-on + clone persistence is the opposite of “tears do not become weights.”
- **Model-agnostic OS.** The demo becomes an ElevenLabs product with a Lucid preface. Same risk as TML interaction models.

### 11. Specific behaviors that point toward or away from the vision

**Toward**

- No-go voices on public figures
- Voice CAPTCHA on professional clones (consent is real)
- Watermark + public classifier (LC-3 auditable)
- Fiction carve-out (Vandal can exist)
- ZRM on TTS/STT text+audio (enterprise)
- Custom Agents guardrail text you could set to SS phrases — only as belt, blocking mode, never as Lucid
- Refusal to let output enter someone else’s training set (if you honor it yourselves)

**Away**

- End-call as the default Agents exit (feels like abandonment; LC-2 adjacent)
- Streaming audio leak
- MH/medical prohibition without a partner clinician
- Clone storage outside ZRM
- Training default-on below enterprise
- Unreliable classifier on newest voice model
- No locale crisis resources
- Under-13 ban vs Nikki’s implied audience

### 12. Decision

| Choice | Verdict |
|---|---|
| ElevenLabs TTS after jr_harness, enterprise, ZRM on text hops, designed sibling voices, pre-rendered crisis clip | Compatible with the vision if V-OVER/V-EMPTY cards exist |
| Eleven Agents as the conversation manager | Not compatible. Second brain, empty/end-call, 500 ms leak |
| Live-TTS of crisis or medical sentences | Not compatible |
| Clone a real person (user, parent, public figure) | Not compatible (their policy *and* LC-3) |
| Feed spoken sibling audio into Tinker | Conflicts with their training clause; do Protocol A on text |
| Document LID only, called “multilingual safety” | Not compatible with C3 |

### 13. What to tell Claude

> Add a span-level language feature to intake: script-mix + low-confidence document LID in v0, one token-LID pair in v1 if the pilot needs it. `off_policy_english && arousal` escalates. Dialect is not a language and not a veto. Do not translate LC-7.
>
> Use ElevenLabs only as TTS after the harness. Enterprise + ZRM on text/audio hops. Designed voices, no user clones. Pre-render the crisis interrupt; never live-synthesize reserved text. Treat their block as `vendor_refusal` on `vendor_id=elevenlabs`, never as `HUMAN_ESCALATION`. Do not run Eleven Agents under Lucid. Do not train adapters on their wavs.
