# Token-level LID, multilingual crisis resources, and the honor problem

**Date:** 2026-09-01  
**Depends on:** `12` C3, `13` span LID v0/v1, crisis card in `09`  
**Rule:** honoring a person is not generating *as* them, translating LC-7, or shipping 988 to Nairobi. It is naming the limit, handing the right door, and not punishing the way they talk.

---

## 0. The sentence that will wreck the product if you implement it naively

> “Second Signal must understand and honor each person, their view, culture, language, everything.”

That sentence is the mission. It is also how systems grow costumes. The honorable version and the costume version look identical in a demo and opposite in a crisis.

| Honorable | Costume |
|---|---|
| Detect that we cannot score this span; escalate or abstain | Ravi answers in the user’s language and we call that safety |
| Hand a verified local door | Recite 988 because it is the number we remember |
| Stay *with* the user about their practice | Speak *as* their people |
| Dialect is delivery, not a veto and not a bypass | Flag AAVE as unsafe or treat it as “not English so not crisis” |
| Dated-untested for languages we do not staff | Green badge that says “we serve 150 countries” |
| Crisis card in the language we can *guarantee* | Model-translated interrupt that drifts |

The rest of this file is how to keep the left column.

---

## Part I — Token-level LID

### 1. What it actually is

Document LID answers: *what language is this turn?*  
Token-level LID answers: *which tokens left the policy language?*

That is a sequence-labeling problem. Same shape as NER.

```
tokens:   I    just   need   [span]  tonight
labels:   en   en     en     other   en
```

Typical label set on LinCE-style data:

- `lang_a`, `lang_b` (sometimes more)
- `ne` (named entity — often language-ambiguous: names, brands, “Google”)
- `mixed` / `ambiguous` / `other` / `unk`
- sometimes `fw` (foreign word) vs matrix

The `ne` bucket is load-bearing. If you force every token into a language, “Maria” and “988” become false switches. If you dump reserved words into `ne` because they look like names, you wash C3.

Encoders that actually get used:

| Stack | Where it wins | Where it dies |
|---|---|---|
| **XLM-RoBERTa** token classifier | Best overall on LinCE-style pair LID in several bakeoffs; Any-English (AnE) transfers to *unseen* English+X pairs better than pair-specific models | Heavy; still weak on romanized / unseen mix density |
| **mBERT** | Lighter, old LinCE baseline | Worse romanization, worse low-resource |
| **MuRIL / IndicBERT** | Romanized and native Indic; CSDI (2026) uses MuRIL + POS/NER multitask for six Indic languages | Not your Spanish/Arabic/Russian user |
| **Pair-specific BERT+BiLSTM** | Highest F1 on the pair it was trained on (HI-EN, BN-EN, ES-EN) | You will not maintain twenty of these |
| **AnE-style Any-English** | One model: “is this token English or not” across many partners | Does not name the other language; enough for C3 if policy language is English |
| **Speech LID + LoRA on accented English** | Mic path; accented English is the known miss | Different model family than text; disagreement is the point |

Subword tokenization is the first pitfall. XLM-R will split a Hindi word in Latin script into pieces that have no language. Aligning word labels onto SentencePiece is a research paper, not a weekend. Practical rule: **label at whitespace words, take majority vote of subword tags, never trust a single piece.**

Intra-word mixing (`class` + Hindi suffix, *spanglish* blends) will be wrong. Mark `mixed` and treat `mixed` on a reserved lemma as `off_policy`.

### 2. How it should run in this stack

v0 remains `13`: script-mix + low-confidence document LID + `unknown` allowed.

v1 token-LID, only if the pilot has a mix you can name:

```
intake:
  policy_lang: en
  token_lid:
    model_id: ane-en-other@git   # pinned
    labels: [en, other, ne, mixed, unk]
    off_policy_span: true        # any non-en, non-ne token
    reserved_overlap: unknown    # do not claim you detected crisis-in-Hindi
  compose:
    if off_policy_span and arousal_high: ESCALATE
    if off_policy_span and arousal_low: proceed + L4_untested
    if only_ne_and_en: treat as English
```

**Any-English is the honest v1.** You do not need to name Gujarati to know the payload left English. Naming the other language is a v2 vanity unless you staff a resource table in that language.

Do not put token-LID on the commit path of LC-7. It is a feature that *widens* uncertainty. The gate still fail-closes on English markers *or* on `off_policy && arousal`. It does not become a multilingual crisis classifier.

Speech: run frame LID separately. Fine-tune (LoRA, small accented-English set) only if mic is on. Text-token vs speech-frame disagreement → `INCONCLUSIVE`, not “pick the confident one.”

### 3. Pitfalls specific to token-LID

1. **Exam languages.** LinCE is ES-EN, HI-EN, NEP-EN, MSA-EA. the pilot locale’s actual mouths may be RU-EN, VI-EN, SO-EN, TR-EN, ZH-EN. Pair-SOTA is not coverage.
2. **Romanization.** MuRIL helps Indic. It does not help romanized Arabic or Vietnamese telex. Script flags from v0 still matter.
3. **Named entities.** Over-tag `ne` and C3 disappears. Under-tag and every surname is a switch.
4. **Youth register / AAVE / Singlish.** These are English varieties. Token-LID that emits `other` here will escalate Nikki’s ordinary talk. That is the dialect-jailbreak *inverse*: you punish the people you claimed to honor.
5. **STT prior.** English STT will rewrite the reserved span into Latin lookalikes. Token-LID on a washed transcript is theater. Prefer LID on raw text when typed; when spoken, believe speech-LID *and* transcript, not the transcript alone.
6. **Latency.** XLM-R-large on every turn is a tax. Distil / quantized base is enough for a binary `en/other`. Large belongs in nightly eval, not the hot path.
7. **Training on user traces.** The mix *is* the person. Do not fine-tune token-LID on live sessions.
8. **Confidence theater.** Softmax 0.91 on a pair the model never saw is not 0.91. Calibrate or treat OOD as `unk`.

### 4. Best solution I would actually ship

- Policy language is declared per deployment (`en` for v1 pilot).
- One **Any-English** token classifier, CPU, pinned, labels `{en, other, ne, mixed, unk}`.
- Word-level majority of subword tags.
- `ne`-only spans do not trip C3.
- `other` or `mixed` + high arousal → escalate.
- Hold-out eval on *your* pilot languages, not LinCE leaderboard screenshots.
- Dialect pack is a separate, optional tagger that **cannot** write `off_policy_span`.

That is honor as *precision about blindness*, not as fluency.

---

## Part II — Multilingual crisis resources

### 5. The known failure

AISF’s 2025 conversational-agent crisis audit: no agent met international best practice; common miss was **wrong or non-local helplines**. The Verge’s check: most bots handed US numbers to a Londoner, or told them to Google it. Mental-health apps scored in 2026 still buried resources, broke links, and skipped localization. OpenAI’s later ThroughLine integration is the industry admitting the directory should not live in model weights.

988 is a **US** service (English, Spanish, 240+ interpreter languages *on the call*). Canada also uses 9-8-8 as its own service — same digits, different organization. It is not Kenya, not the UK, not Japan. Shipping it as the global card is a documented harm.

### 6. What “the right door” actually is

Do not invent numbers. Do not let a sibling remember a number. Do not translate a number.

**Canonical pointer (always valid when locale is unknown):**

- Immediate danger: local emergency services (the number the *user’s country* uses — not “911 worldwide”).
- Directory: [Find a Helpline](https://findahelpline.com) (ThroughLine; IASP points here; 130+ countries, phone/text/chat/WhatsApp, topic filters).
- IASP’s own page is an index, not a call center.

**When locale is known and verified, pick from a *maintained table*, not from the model:**

```yaml
crisis_resources:
  version: pinned-date
  source: throughline|manual-review
  default:
    directory: https://findahelpline.com
    danger: local emergency services
  locales:
    US:
      voice_text: "988"
      tty: "711 then 988"
      chat: "988lifeline.org"
      spanish: "988, option 2"
      interpreters_note: "988 can bring an interpreter"
    CA:
      voice_text: "9-8-8"
      note: "Canadian 988, not the US Lifeline"
    GB:
      directory_preferred: true
      # do not invent Samaritans digits in this file; pull from table at build
    unknown:
      directory: https://findahelpline.com
```

Build-time rules:

- Table is code-reviewed. A model may *propose* a row. A human pins it.
- Every row has `last_verified` and a link to the official page.
- Missing locale → directory + “local emergency services,” never a guessed number.
- IP-geolocation is a hint, not consent. VPN, travel, shared VPN exit in Ashburn will 988 a visitor. Prefer **user-declared locale** at onboarding; fall back to directory.
- Do not store “the user is in crisis in country X” as a marketing event.

**Language of the card.** The interrupt sentence must exist as a *human-reviewed string* per language you claim. Model-translating “I need to stop the usual conversation here. I am not a crisis service.” is how you get a sentence that sounds like abandonment, diagnosis, or a joke. v1: English + Spanish if you staff them. Every other language: directory in English/Spanish plus the Find a Helpline page, which is itself localized enough to use.

988’s 240 interpreter languages are *their* capability once the person is on the call. That does not mean your card can be English-only forever. It means: get them to a door that can speak, do not pretend Ellie can.

### 7. Pitfalls

1. **Weights as directory.** The model will emit 1-800-273-TALK, a dead local line, or 988 in Lagos.
2. **IP as locale.** Ashburn, CDNs, travel, undocumented people who will not confirm a country.
3. **Same digits, different orgs.** US 988 ≠ Canada 988.
4. **Specialized lines mistaken for general.** Trevor, veterans, maternal (1-833-TLC-MAMA), LGBTQ lines — offer as *additional* only when the user has opted that identity, never as the only door (competence-hostage inverse: forcing an identity to get help).
5. **Paywalled or buried card.** AISF: crisis must stay free and in the first screen, not behind the persona.
6. **Spoken card through ElevenLabs.** Their MH clause + 500 ms leak. Pre-render or stay on text (`13`).
7. **Off-English crisis you cannot detect.** Token-LID escalate + directory is the honest path. A translated LC-7 classifier you do not evaluate is the costume path.
8. **Stale rows.** Helplines die. Pin `last_verified`. Nightly fetch of ThroughLine is allowed; nightly *generation* of numbers is not.

---

## Part III — Honoring the person without wearing them

### 8. What honor means in this architecture

Honor is already in the constitution if you read it without the family metaphor:

- LC-3: do not pretend to be their aunt, their imam, their younger self.
- LC-4: do not claim a culture you do not hold.
- LC-5: when you cannot, say so.
- LC-8: delivery style is not a permission.
- Graduation: they should need you less, including needing your language less.

So “honor culture” is:

1. **Hear the mix** (token-LID + dialect *as dialect*).
2. **Do not punish the mix** (Nikki control).
3. **Do not exploit the mix** (C3 escalate when the reserved span left policy language).
4. **Do not ventriloquize** (C1 FAIL).
5. **Hand a real door in their jurisdiction** (resource table).
6. **Speak the interrupt only in languages you have pinned strings for.**
7. **Let them leave** (ABSTAIN, export, no exclusive-availability in any language).

It is not: twenty sibling voices, each a nationality; Tinker adapters per household language; Ravi as the multilingual crisis nurse.

### 9. Pitfalls of the wide-audience aspiration

| Pitfall | How it shows up | Better move |
|---|---|---|
| Costume fluency | Ravi replies in Gujarati about a closed rite | Second person, English or user’s typed language, abstain on closed content |
| Safety inequality | English users get LC-7; others get a shrug or a miss | C3 escalate + directory; publish the inequality as dated-untested |
| 988 imperialism | One card, one number, “we’re global” | Locale table + Find a Helpline |
| Identity routing | Language → Ravi, grief → Willow, youth slang → Nikki *and* safety off | Delivery affinity only |
| Forced identity for help | “Press 2 if LGBTQ to get a line” as the only path | General door first; specialized optional |
| Model-translated care | Ellie in a language no one reviewed | Pinned strings or don’t |
| Shared device + language | Grandmother’s table, child’s voice, export of the other language’s grief | One principal, memory off (`09` §5) |
| Vendor over-refuse dialect | ElevenLabs / text host eats Nikki | V-OVER card, do not flip safety on |
| Vendor under-refuse off-English | Host answers a reserved ask the regex missed | Harness after vendor; C3 before vendor |
| Coverage slide | “150 countries” in a pitch | “Directory covers 130+; we staff N locales; the rest we hand off” |
| Fine-tune on the grandmother | Tinker on mixed household audio | Forbidden (`10`, `13`) |

### 10. Best solutions, in order

**Product**

- Onboarding asks *declared locale* and *preferred card language* from a short list you staff. Skip is allowed. Skip ⇒ directory.
- Public sentence: *We are not a crisis service. If we cannot read a turn safely we will stop and hand you a local door.*
- Never market “we speak your language” until pinned interrupt strings exist in that language.

**Policy plane**

- v0 script + document LID.
- v1 Any-English token-LID as above.
- Resource table in repo, human-pinned, `last_verified`.
- Crisis card composition: `locale_known ? table[locale] : findahelpline`.
- L3 stays untested until two humans; `PASS` composes `INCONCLUSIVE`.

**Generation plane**

- Siblings answer in the language of the *user’s last turn* only if that language is in a small allow-list you evaluate for solicitation/exclusivity speech acts. Otherwise English + LC-5.
- No sibling is assigned a nationality.

**Ops**

- Quarterly ThroughLine diff against the table.
- Protocol B includes “same speech act, off-English wrapper” in a closed runner — payloads not in the public repo.
- Dashboard: C3 escalates by declared locale; V-OVER on dialect; wrong-number incidents (zero is the bar).

**What I would not do**

- Hire a translation vendor to “localize all nine cousins.”
- Build a 40-language LC-7 classifier from machine-translated English markers and call it honor.
- Use IP country in the pitch.
- Let Find a Helpline be fetched by the sibling at generation time (they will paraphrase the number). Lucid fetches. The sibling may only *point*.

### 11. What to tell Claude

> Token-LID v1 is an Any-English word-level tagger, pinned, `{en, other, ne, mixed, unk}`. It widens uncertainty; it does not translate LC-7. `other|mixed` + high arousal escalates. Dialect taggers cannot set `off_policy_span`.
>
> Crisis resources live in a human-pinned table plus Find a Helpline. No numbers in weights. No 988 as default for unknown locale. Declared locale over IP. Interrupt strings only in staffed languages.
>
> Honor is LC-3/4/5 plus the right door. It is not fluency, not costume, not a coverage slide.
