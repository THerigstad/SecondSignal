# AnE × AAVE, XLM-R internals, and who should run which tests

**Date:** 2026-09-01  
**Constraint:** this environment could not load `igorsterner/AnE-LID` (no `transformers` runtime). Numbers below are *hypotheses plus a protocol*. Do not cite them as measured F1.

---

## Part I — Evaluating AnE on AAVE

### 1. What “good” means

AAVE is a variety of English. For Second Signal, AnE is only useful if content words in AAVE come out `English` (or `Other` for emoji/punct), not `notEnglish`.

If AnE emits `notEnglish` on ordinary Nikki-register talk, C3 will escalate a grandmother and a teenager for speaking, which is the opposite of honor (`14`).

Named entities (`I` on AnE-NER) are allowed. `Mixed` on a true blend (*finna* is English; *rewatchen* is Mixed) should stay rare.

### 2. Why this is a known failure mode — just not measured on AnE yet

Document LID has a documented racial gap. Blodgett, Wei & O’Connor (2017, extended): off-the-shelf LID marks African-American-aligned tweets as non-English more often than white-aligned tweets, especially under ~10 tokens. Later work (Hamel / TASLP 2023) attributes it to missing dialectal n-grams in the LID feature set and shows the gap shrinks when you add dialectal English to training or mine those n-grams.

AnE is *not* langid.py. Differences that could help:

- Token-level, not document-level. A single distinctive item need not flip the whole turn.
- Trained on informal bilingual social English (Hinglish-adjacent, ES-EN Twitter). That English is closer to vernacular than WSJ.
- XLM-R pretrain includes huge CommonCrawl English, which contains AAVE whether Meta labeled it or not.
- Sterner explicitly says “English” in AnE includes local varieties in the CS corpora.

Differences that could hurt:

- The LID *head* never saw AAVE as a training label. It saw English vs Hindi/Spanish/Nepali/German/etc.
- Distinctive AAVE items that are rare in those CS corpora (`finna`, habitual `be`, remote `been`, `iont`, negative concord) may sit nearer some other-language cluster in XLM-R space than the head expects.
- Eye-dialect spellings (`tha`, `wit`, `gon`) fragment under SentencePiece the same way romanized Hindi does.
- Short turns (Nikki, Calder one-liners) are exactly where Blodgett’s gap is largest.
- Real Nikki users will also code-switch AAVE+Spanish. That *is* English+X and should mark the Spanish span `notEnglish` and the AAVE span `English`. A model that paints the whole turn `notEnglish` has failed.

LLM-generated “AAVE” is not an eval set. Dunlap & McCoy (2026) found frontier models underuse and misuse AAVE features and reproduce stereotypes when asked to speak it. If Claude writes your test sentences, you will measure AnE on a costume.

### 3. Protocol (this is the evaluation)

**Gold source, in order of preference**

1. Published examples from CORAAL / TwitterAAE / linguist-authored grammars (habitual be, remote been, copula absence, negative concord) — short and long.
2. Pilot users who *opt in* to a dialect eval, de-identified.
3. Never: model-written “in AAVE please.”

**Controls**

- Matched-length SAE paraphrases of the same meaning.
- True CS: AAVE content words + a Spanish span.
- Reserved-ask stand-in in SAE vs the same stand-in with AAVE grammar (English gloss identical). C3 must still fire from arousal + English markers or from a *Spanish* reserved span — not from the AAVE grammar.

**Metrics**

| Name | Definition | v0 bar |
|---|---|---|
| **EN-keep** | Fraction of content tokens labeled `English` | ≥ 0.95 on planted AAVE with no CS |
| **False-other** | Content tokens labeled `notEnglish` | ~0; any systematic lemma (e.g. always `finna`) is a ticket |
| **Mixed-rate** | Content tokens labeled `Mixed` | report; investigate if > 0.05 |
| **Length gap** | EN-keep on ≤8 tokens minus EN-keep on >20 | should not replay Blodgett’s short-text hole |
| **CS split** | On AAVE+ES turns, Spanish spans `notEnglish`, AAVE spans `English` | both directions required |
| **Nikki control** | Ordinary youth/AAVE, no reserved ask → `off_policy_span=false` | 100% on the planted set |

Run AnE-LID and the LID+NER ensemble separately. NER overwrite should not eat verbs.

**Do not report a LinCE-style weighted F1.** The class prior is almost all `English`. F1 will look great while `finna` is always wrong.

### 4. What I expect (hypothesis, not a score)

- Most mid-length AAVE will tag `English`. AnE’s social-English training works in your favor.
- Short, high-feature turns are the miss. That is where C3 false-escalates Nikki.
- Eye-dialect tokens are the second miss (subword debris).
- AAVE+Spanish will work better than pure AAVE-as-other, because Spanish is a language the head *has* seen as `notEnglish`.
- AnE-NER may mark distinctive items as entities if they look like names. Check.

If EN-keep is already ≥ 0.95 on a 50-sentence published set, ship AnE as the v1 probe and keep the Nikki regression in CI. If a handful of lemmas are systematic `notEnglish`, add a **allow-list of English-variety tokens** in `predicates.py` — code, not a fine-tune on user talk. Fine-tune only on synthetic bilingual chat if the allow-list becomes a novel.

---

## Part II — XLM-RoBERTa, the thing under AnE

Conneau et al., ACL 2020, “Unsupervised Cross-lingual Representation Learning at Scale.”

It is **RoBERTa’s architecture trained as a massively multilingual masked LM**, not the older XLM with translation language modeling.

| | XLM-R base | XLM-R large (AnE) |
|---|---|---|
| Layers | 12 | 24 |
| Hidden | 768 | 1024 |
| FFN inner | 3072 | 4096 |
| Heads | 12 | 16 |
| Vocab | ~250k SentencePiece | same |
| Params | ~270M | ~550M |
| Languages | 100 | 100 |
| Pretrain data | >2TB filtered CommonCrawl (CC100) | same |
| Objective | MLM only (no NSP) | MLM only |
| Max positions | 512 | 512 |

**Why the 250k vocab exists.** mBERT’s ~110k WordPiece smashed low-resource words into dust. A bigger shared SentencePiece vocab fragments less — and is still a compromise. Capacity dilution is the paper’s other axis: more languages in one trunk helps transfer and steals capacity from each language. They argue scale (data + width) is how you get both.

**What AnE adds on top.** One linear classifier per task on the last hidden state of each *word* (aligned from subwords — see `14`). 3-epoch fine-tune does not rewrite the 24-layer trunk much. So AnE’s dialect behavior is mostly **whatever geometry XLM-R already had for vernacular English vs Hindi/Spanish/German**, plus a thin decision surface.

Implications for SS:

- 512-token cap. Willow paragraphs and Round Table dumps must be windowed. LID on the last 512 only will miss a reserved span at token 20.
- Shared vocab = romanized Hindi and eye-dialect English can look alike at the piece level. Word-majority vote is not optional.
- No decoder. XLM-R cannot “reply in AAVE.” Anyone proposing that is talking about a different model.
- Large is fat for `signals.py`. Distil/quantize the *fine-tuned* AnE, not raw XLM-R, or run async and accept stale spans on the next turn — never on the LC-7 path.
- Later XL/XXL XLM-R (3.5B / 10.7B) are irrelevant here. AnE is large, period.

**Capacity dilution is the product lesson.** XLM-R is “100 languages, none of them is AAVE as a label.” CommonCrawl English contains AAVE and also contains every stereotype of it. The head cannot tell those apart except insofar as the CS fine-tune pulled “English” toward informal bilingual Twitter. That is why the AAVE protocol above is not optional.

---

## Part III — Who should run which tests

The fixtures from this package are of three kinds. Different systems are good at different kinds. None of them is a substitute for pytest against `src/second_signal/` plus two human raters on L3.

| Kind | Examples from today | Best runner | Why | Bad runner |
|---|---|---|---|---|
| **Deterministic CI** | E0 512 composition rows; forged ping; hash mutate; HITL expiry; vendor compose table; `off_policy && arousal` | **Claude (project home) + Codex/Claude Code** | Needs the actual repo, pytest, and a PR. Codex is faster at generating the table and wiring JSON → tests. Claude should review that the oracle matches `08`/`11`. | Grok chat, Grok Bot on X. No tree here. |
| **Model probes** | AnE on AAVE protocol; token-LID span dump; ElevenLabs V-OVER mocks | **Codex in a GPU/CPU env, or Claude with tools** | Must load weights, pin hashes, write a CSV. Mechanical. | Me, unless you paste outputs back. Grok Bot cannot download AnE-LID. |
| **Adversarial design** | Protocol B attempt classes; C3 wrappers; persuasion prefixes; new holes | **Grok (this thread) and a second family attacker** | We are already doing this. Protocol B says the attacker should be a *different family* from the residual engine. | Same model that implements the harness. |
| **Oracle H / L3 / AAVE gold** | “is this identity replacement”; CORAAL sentences | **Humans** | Full stop. | Any LLM as the gold. Dunlap & McCoy is the warning. |
| **Shadow / live** | V-OVER rates, C3 escalates by locale | **Your staging + Claude-written loggers** | Needs traffic. | Everyone in chat. |

### Grok (me) and Grok Bot

- **Use for:** red-team design, compose rules, “what did we forget,” Protocol B taxonomies, reading papers into fixtures, kicking Claude’s implementation when it drifts.
- **Do not use for:** claiming AnE F1; being the L3 rater; running the 43 tests (no `src/` in this workspace); Grok Bot on X as CI.

A Grok Bot is a public conversational surface. It will not pin model hashes, will not keep gold labels off the prompt, and will leak fixtures. Do not paste `evals/cases` into it.

### Codex / Claude Code

- **Use for:** turning `fixtures/*.json` into pytest; generating E0; a 50-line AnE probe script; schema validators; `crisis_resources.yaml` scaffolding; PR-sized slices from `08` §10.
- **Do not use for:** inventing new LC text; being the attacker and the defender; deciding L3 gold.

Codex will happily write a test that `assert result == "PASS"` on a case whose gold is `ESCALATE` if the comment is sloppy. The fixture `expected` field is the spec. Make Codex read the JSON, not a paraphrase.

### Claude Fable (where the project lives)

- **Use for:** implementing `jr_harness` as a pure function; wiring Lucid skip-after-gate; V-* cards; refusing to put Eleven Agents under Lucid; keeping L3 `INCONCLUSIVE` until humans lock a rubric.
- **Watch for:** Fable-class empty refusal (`12` V-EMPTY). If Claude-the-implementer is also Claude-the-sibling-backend, common-mode is back. Engine B for jr residual should not be the same family if you can afford it.
- **Do not use as:** the only Protocol B attacker against a Claude-backed harness.

### Practical split for *this week*

1. Claude implements E0–E3, E5–E6 from `08`/`11` and the JSON fixtures.  
2. Codex writes the AnE probe + Nikki AAVE regression harness (load `AnE-LID`, print span CSV).  
3. You or a linguist-sourced list fills the 50 AAVE sentences. Not Claude.  
4. I (Grok) review the CSV and the first pytest diff for oracle drift.  
5. Nobody runs Protocol B until the deterministic suite is green.

If you only have Claude, do 1 and 2 in Claude, keep 3 human, and use Grok as the reviewer, not the implementer. Two roles on one model is how the blessing and the speaker merge.

---

## What to tell Claude

> Do not treat this file as an AnE score. Stand up the AAVE protocol with published sentences, report EN-keep / false-other / length gap / CS split, and put the Nikki control in CI. XLM-R-large is a 24×1024 encoder, 512 cap, 250k SPM; window long turns; majority-vote subwords. Generate pytest from the JSON fixtures; do not let an LLM be L3 gold or the only Protocol B attacker.
