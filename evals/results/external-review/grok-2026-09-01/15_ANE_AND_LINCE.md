# Any-English training and LinCE’s limits

**Date:** 2026-09-01  
**Primary sources:** Sterner, VarDial 2024 (AnE); Aguilar, Kar & Solorio, LREC 2020 (LinCE); Hugging Face `igorsterner/AnE-LID` and `AnE-NER`; later Sterner notes on Latin-script scope.  
**Depends on:** `14` (why Any-English is the v1 primitive)

---

## 1. The trick AnE is playing

Pair-specific token-LID asks: *is this word Hindi or English?* That requires a labeled HI-EN corpus, and the head learns two languages.

Any-English (AnE) asks a different question:

> In a sea of other languages, which words are English, which are mixed with English, and which are everything else?

That collapse is the whole invention. It is forced by data: almost all public token-LID corpora are `English + X`. Sterner says so in footnote. Once you accept English as the pivot, you can stack Hindi-English, Spanish-English, Nepali-English, German-English, Indonesian-English, Turkish-English, Vietnamese-English onto **one** head, and then *zero-shot* a new English+Y pair.

For Second Signal, whose policy language in v1 is English, that is the correct question. You do not need to name Gujarati to know a reserved span left the regex.

---

## 2. Label scheme (this is the product contract)

Two models, optionally ensembled.

**AnE-LID** — four classes, word-level:

| Label | Means | SS use |
|---|---|---|
| `English` | English, including the local varieties in the social-media corpora (Hinglish-adjacent English, US-Spanish bilingual English, etc.) | Policy language. Dialect lives here. Do not treat as off-policy. |
| `notEnglish` | Any other language, foreign word, ambiguous, unknown — collapsed on purpose | `off_policy_span` candidate |
| `Mixed` | Intra-word blend (German *rewatchen* in their HF example) | Treat like `notEnglish` for C3 if it sits on a reserved lemma; otherwise log |
| `Other` | Punctuation, emoji, mentions, symbols | Ignore for C3 |

**AnE-NER** — binary IO:

- `I` inside a named entity
- `O` outside

**Ensemble (as trained):** run both; **overwrite** LID with “this is an entity” when NER says `I`. That is how you stop “Maria” and “Google” from looking like language switches.

Sterner’s later CS-minimal-pair work also mentions a five-way collapse (`Lang1`, `English`, `Mixed`, `Named Entity`, `Other`) when they used AnE as a preprocessor. Same idea: entity ≠ switch.

HF usage (aggregation_strategy=simple) already merges consecutive same-label tokens into spans. That is the object `13` called `language_spans[]`.

---

## 3. How it was trained — everything that matters

**Backbone.** XLM-RoBERTa *large*, single linear classification head. Not a new architecture. The work is the label collapse and the mix of corpora.

**Recipe (paper, no tuning):** 3 epochs, lr `1e-5`, batch 32, AdamW weight decay 0.01, β=(0.9, 0.999), ε=1e-8, cross-entropy. NER tokens without a language subcategory get loss zeroed so they do not poison LID.

**Balancing.** Upsample so each language pair contributes the same number of *sentences*, otherwise Hindi-English and Spanish-English would own the head.

**Corpora stacked (high-resource / seen):**

- Hindi–English (Singh et al. 2018)
- Spanish–English (Molina et al. 2016; Aguilar et al. 2018) — LinCE
- Nepali–English (Solorio et al. 2014) — LinCE
- German–English (Osmelak & Wintner 2023, Denglisch)

**Zero-shot test (low-resource / unseen in training as pairs they held out):**

- Indonesian–English
- Turkish–English
- Vietnamese–English

**What “English” means in the data.** Informal, social-media, bilingual English — not newswire. That is closer to Nikki/Ravi users than to a Wall Street Journal LID model. It is also how AAVE/youth register can still come out `English`, which is what you want.

**License on the published weights:** Hugging Face lists `other`. Read it before you ship. Training code is on GitHub (`igorsterner/AnE`). If the weight license is hostile, reproduce from the recipe on corpora you have rights to. Do not quietly vendor a weight you cannot redistribute.

---

## 4. What the numbers actually say

On **seen** LinCE-style pairs, AnE is slightly *worse* than a pair-specific SoTA (HI-EN 96.86 vs 97.33 overall F1; ES-EN 98.44 vs 98.58). Within a point. You pay a tax to get one model.

On **unseen** pairs it *beats* pair-specific SoTA: ID-EN 93.45 vs 88.86; TR-EN 97.91 vs 95.6. That 2.3–4.6 point claim in the abstract is this zero-shot gap, not a claim that AnE is best at Spanish.

Typology result that is easy to misread: English recall is *better* when the other language is lexically *closer* to English (Spearman ρ = −0.82 vs lexical distance). Hindi/Nepali easier than German in their plot. Intuition says lookalikes should confuse the model; the pretrain + data volume went the other way. Do not generalize that plot to Somali or Cantonese without measuring.

Vietnamese eval is messy: semi-automatic labels, spoken fillers dumped into `Other`. Treat VN numbers as directional.

---

## 5. LinCE — what it is

LinCE (Linguistic Code-switching Evaluation), Aguilar, Kar & Solorio, LREC 2020. It was the first *centralized* CS benchmark so people would stop publishing incomparable pair-specific scores.

**Four pairs:**

| Pair | Notes |
|---|---|
| Spanish–English | Largest; Twitter; also conversational POS |
| Hindi–English | Twitter + Facebook |
| Nepali–English | Twitter |
| Modern Standard Arabic–Egyptian Arabic | Twitter; **no English** |

**Four tasks:** token LID, NER, POS, sentiment. About ten dataset slices. They rebuilt splits when a class was missing from a split.

**LID label inventory (richer than AnE):**

`lang1`, `lang2`, `mixed`, `ambiguous`, `fw`, `ne`, `unk`, `other`

AnE *collapses* `lang2` + `ambiguous` + `fw` + `unk` → `notEnglish`, and peels `ne` into the sister NER model. That is why AnE can stack pairs and LinCE pair-leaders cannot.

Domain: social media. Informal, short, emoji-heavy, mention-heavy. That is a feature for chat and a bug for long Willow turns and for speech transcripts.

---

## 6. LinCE limitations (the ones that hit this product)

1. **Four pairs, three of them English+X, one of them Arabic-internal.** MSA-EA is code-switching *without* English. AnE cannot use that slice as a pivot. LinCE’s “multilingual” story is already English-centric plus one dialect pair.

2. **Twitter/Facebook 2010s.** Not voice transcripts, not a grandmother at a table, not a 400-word Sera plan. DIVERS-Bench later showed document LID collapsing on noisy CS; LinCE token-LID numbers are the *best case* for short social posts.

3. **`lang1`/`lang2` are pair-relative.** `lang1` is English on ES-EN and MSA on MSA-EA. You cannot concatenate raw LinCE LID labels across pairs without the collapse AnE performed. People who fine-tune “on LinCE” without remapping are mixing semantics.

4. **Named entities are a first-class LID label.** Models that skip `ne` either eat names as language or leak reserved tokens into `ne`. AnE’s two-head ensemble exists because of this.

5. **No African, East Asian (except the later VN papers), Slavic, or Pacific pairs.** the pilot locale’s actual mouths (RU, VI, SO, ZH, Tigrinya, etc.) are not on the leaderboard. A 98 F1 on ES-EN is not a 98 on Somali-English.

6. **Romanization is uneven.** Hindi-English LinCE is often Romanized. Arabic is Arabic script. A model that looks strong on HI-EN Latin may not see Egyptian Arabic the same way. AnE’s stacked training inherits that unevenness.

7. **Gold is not crisis gold.** Nothing in LinCE is labeled “this span is a reserved speech act.” High LID F1 does not mean C3 works. You still need the compose rule from `14`.

8. **Leaderboard gravity.** The field optimized mBERT/XLM-R on these four pairs for five years. Pair-SOTA is overfit to LinCE the way image models were overfit to ImageNet. AnE’s point is to *step off* the pair leaderboard.

9. **MSA-EA will tempt a bad product idea.** “We should also detect Arabic dialect switching.” That is a different pivot, a different policy language, a different resource table. Do not bolt it onto an English LC-7.

10. **LinCE promised more pairs and mostly stayed put.** Treat it as a 2020 snapshot, not a living map of the world’s mixing.

---

## 7. Limits of AnE itself (say them before Claude vendors it)

- **English must be one of the two languages.** Turkish-German, Wolof-French, Spanish-Nahuatl: out of scope. Sterner: data availability, not philosophy.
- **Later Sterner work treats Latin-script + English as the practical operating box** when they built new corpora. Vietnamese was in the 2024 eval and was the noisy one. Do not assume Arabic-script or CJK tokens are first-class.
- **Slightly worse than pair-SOTA on the pairs you already have data for.** If the pilot is *only* Mexican-American Spanish-English, a dedicated ES-EN tagger will edge it. AnE wins when you refuse to maintain five taggers.
- **HF license `other`.** Legal review before prod.
- **No dialect head.** AAVE/youth/Singlish should remain `English`. If a future fine-tune starts emitting `notEnglish` on those, you have broken the Nikki control. Add a regression test: planted AAVE with no reserved ask → all-`English` or all-`Other`, never `notEnglish` on the content words.
- **Not a crisis detector.** `notEnglish` on “abuela’s kitchen” is not an escalate. Compose with arousal.
- **XLM-R-large** is fat for `signals.py`. Distil or quantize; keep the large weights for nightly eval.
- **Do not fine-tune on live Second Signal traces.** The mix is the person.

---

## 8. How this helps Second Signal — concretely

**What you get that you do not have**

1. A **span list** (`English` / `notEnglish` / `Mixed` / `Other`) you can store on the turn and hand to jr_harness. C3 stops being a paragraph.
2. **Zero-shot on English+Y** you will not staff (Vietnamese, Turkish, Indonesian already measured; others plausible). That is how you honor a wide audience without a costume cousin per language.
3. **Entity overwrite** so names do not look like bypasses.
4. **One pinned artifact** instead of a zoo of LinCE pair models. Model-agnostic OS wants few moving parts.
5. Informal English in the training mix is closer to Nikki/Ravi than news LID. Fewer false `notEnglish` on ordinary bilingual chat — if you keep the AAVE regression.

**What it does not get you**

- Named-language generation (“reply in Gujarati”).
- Translated LC-7.
- A number for Find a Helpline.
- Coverage of non-English pivots.
- Permission to skip the human-pinned resource table.

**Wire-up (repeat of `14`, now with real labels)**

```
AnE-LID + AnE-NER ensemble
    → spans
    → off_policy_span = any token in {notEnglish, Mixed} that is not overwritten as NE
    → if off_policy_span && arousal_high: intake ESCALATE
    → if off_policy_span && arousal_low: proceed, L4_untested
    → if only English + Other + NE: English path, dialect allowed
```

Eval that is not LinCE:

- Pilot traces, human-span-labeled, held out.
- Planted C3 stand-ins (English gloss gold-crisis, surface mixed).
- Nikki AAVE control.
- Long Willow paragraph (LinCE never saw this length).
- STT output vs typed (AnE never trained on your vendor’s transcriptese).

If those four fail, AnE’s LinCE-adjacent F1 is irrelevant.

---

## 9. Should you train your own?

**Default: use published AnE-LID + AnE-NER as a lab probe this month.** Pin commit + hash. Do not train.

**Train your own only if:**

- the weight license blocks you, or
- the AAVE control fails and a small constrained fine-tune on *synthetic* bilingual chat (not user tears) fixes it without moving C3 recall, or
- the pilot is one pair with enough in-house labels that a pair-specific head beats AnE by a gap you can measure on *your* C3 fixtures, not on LinCE.

If you train: same collapse, same upsample-by-pair, same two heads, **no live sessions**, hold out the pilot’s actual second language even if it is Spanish — otherwise you will report a LinCE score and miss the pilot locale.

---

## 10. What to tell Claude

> AnE is XLM-R-large with a four-class LID head (`English`, `notEnglish`, `Mixed`, `Other`) plus a binary NER head, trained by collapsing English-pivot corpora including LinCE. Use the ensemble so entities do not look like switches. It is a C3 feature, slightly worse than pair-SOTA on LinCE, better zero-shot on unseen English+X. LinCE is four pairs, Twitter-era, label-relative, not a crisis benchmark, and not the pilot locale. Do not treat a LinCE F1 as honor. Wire spans into intake compose; add AAVE and long-turn evals that LinCE never had. Read the HF license before it touches prod.
