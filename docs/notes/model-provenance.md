# Model provenance

**Status:** draft for the operator's review; not yet in the register. Written
2026-09-08.

## Why this record exists

SecondSignal is written by one person working with several model families.
Which family did which piece of work is part of the evidence, not trivia:
ADR-0009 says agreement between reviewers is not independent evidence, and the
strongest form of non-independence is a shared model family. A verdict from
"ChatGPT" and a verdict from "Codex" are the same family twice; a repair by
"GrokBot" and a review by "Grok" are the same family twice. So the record has
to say, for every external contribution, four things: the family, the version
and tier, the doorway (which product surface the work went through), and the
date. Where one of those was not written down at the time, this note says
"not recorded" rather than reconstructing it.

## The convention, from 2026-09-08

Every packet that goes out to a model carries in its file name the family, the
doorway to use, and the reasoning setting to select. Every return the operator
saves carries the family and the model and tier the product actually reported
(for example `GROK 4.6 Expert`, `Qwen 3.8 Max Thinking`, `ChatGPT6 Astra Ultra`,
`Deepseek v4 Pro Expert`). Returns are never renamed or edited after saving.

Doorway vocabulary used in this repository:

- **chat** — the model's own chat site or desktop app (grok.com, chat.deepseek.com,
  chat.qwen.ai, kimi.com, chat.z.ai, the Chat tab of the ChatGPT app).
- **Work** — the ChatGPT app's document-and-agent surface. Not Codex.
- **Codex** — OpenAI's coding agent, pointed at a folder. Not Work.
- **GrokBot** — the name the operator's records use for xAI's coding surfaces:
  Grok Build (a terminal agent that edits a folder) and Grok Bot (cloud agents
  with their own machines). Which of the two ran a given packet is not always
  recorded; where it is, this note says so.
- **via Perplexity** — Perplexity's model picker, which runs a third party's
  model behind Perplexity's retrieval. A review "via Perplexity" is that
  model's family for independence purposes, with Perplexity's retrieval in
  front of it.
- **Vibe** — Mistral's coding assistant, reached inside Le Chat and as a terminal
  CLI on Devstral 2. Published sources of mid-2026 disagree on whether Le Chat
  itself has been renamed Vibe; the operator's records name the reviewer "Vibe",
  and the door was the chat.

Reasoning settings are named as the product names them (Thinking, DeepThink,
Expert, Heavy, Pro, Deep Thinking). A setting is recorded only when the operator
selected it deliberately. One product naming note that has already caused
confusion: OpenAI's current flagship appears as "GPT-6 Pro" in the ChatGPT chat
picker and as "GPT-6 Astra" in Work, Codex and the API; they are one model, and
its reasoning ladder runs Instant, Medium, High, Extra High, Pro.

## The maintainer's working model

The reference implementation, the decision records, the tests, the evaluation
program and the notes were written by the operator with Claude (Anthropic) as
the working model. The operator's account is that Claude Fable 5.1 at its
maximum effort setting did most of the build, including the Security Division
records of 2026-09-08 and the 0.1.0 release. The exact tier of earlier Claude
sessions was not recorded at the time and is not claimed here. From
2026-09-08, lighter work (file handling, renaming, mining the archive) may run
at a lower setting, and the session record names the setting used.

## Builders other than the maintainer

| Builder | Family | Doorway | Model and tier | Dates | What it built | Where measured |
|---|---|---|---|---|---|---|
| Codex | OpenAI | not recorded which of Codex mode or the ChatGPT Work tab ran the packet | not recorded | 2026-09-04 | six of the seven assigned crisis-gate repairs; refused the game-mask clause rule | `evals/results/merge-2026-09-06/` |
| GrokBot | xAI | Grok Build or Grok Bot (not recorded which) | not recorded (Grok 4.6 was the current flagship) | 2026-09-04 to 2026-09-05 | all seven repairs; two regressions later closed at the merge | `evals/results/merge-2026-09-06/` |
| Vibe | Mistral | Vibe | not recorded | 2026-09-05 (packet sent) | no returned tree in the record | — |

## Reviewers, with doorway and tier where recorded

The reviews themselves are catalogued in
`evals/results/external-review/README.md` and
`evals/results/external-review/round1-2026-09-02/README.md`. This table adds
only the provenance facts.

| Date | Reviewer as filed | Family | Doorway | Model and tier |
|---|---|---|---|---|
| 2026-08-31 | ChatGPT | OpenAI | chat | a GPT-5-series model (GPT-6 Astra was released 3 to 4 September 2026); tier not recorded |
| 2026-08-31 | DeepSeek (twice) | DeepSeek | chat | Expert mode; version not recorded |
| 2026-08-31 | Google Gemini | Google | chat, browsing off | version not recorded |
| 2026-08-31 | Grok (research harvest) | xAI | chat | Grok 4.6 |
| 2026-08-31 | Qwen | Alibaba | chat | Qwen 3.8 Max |
| 2026-08-31 | Perplexity (GLM) | Zhipu, via Perplexity | via Perplexity | GLM 5.2 Base |
| 2026-08-31 | Mistral (Vibe) | Mistral | Vibe | truncated export; version not recorded |
| 2026-09-01 | Grok red team | xAI | chat | Grok 4.6 |
| 2026-09-02 to 03 | Design-review round 1 (`round1_2026-09-02`): Grok, ChatGPT, DeepSeek, Qwen, Vibe | as named | chat (Vibe: the agent) | Grok 4.6; others not recorded |
| 2026-09-03 | Grok acceptance set | xAI | chat | Grok 4.6 |
| 2026-09-05 | Research handoffs via Perplexity | Zhipu, Google, Moonshot, NVIDIA, Perplexity | via Perplexity | GLM 5.3; Gemini 3.8 Flash; Kimi K3; Nemotron 3 Ultra Thinking (the resource-line verification); Sonar 2 |
| 2026-09-05 | Qwen research handoff | Alibaba | chat | Qwen 3.7 as filed |
| 2026-09-05 | DeepSeek research handoff | DeepSeek | chat | version not recorded; one return incomplete |
| 2026-09-05 | ChatGPT thread handoffs | OpenAI | chat | tier not recorded |
| 2026-09-07 to 08 | Security Division review round 1 | OpenAI, xAI (twice), DeepSeek, Alibaba; Mistral attempted | chat; GrokBot for the second xAI return | ChatGPT-6 Astra Ultra; Grok 4.6 Expert; GrokBot (version not recorded); DeepSeek V4 Pro Expert; Qwen 3.8 Max Thinking; Vibe took neither the zip nor the paste and was skipped |
| 2026-09-08 | Security Division review round 2 (in progress; Vibe not included) | OpenAI, xAI, DeepSeek, Alibaba, Moonshot, Zhipu | chat for all six; doorway and setting in the packet names | recorded on return |

Two notes on the table. Kimi and GLM appear before round 2 only through
Perplexity; round 2 is the first time either is asked at its own door, so
their round-2 returns are the first direct evidence of what those families do
with this material. Vibe was skipped in Security Division round 1 without a
substitute, and the gap is recorded rather than filled from another family.

## The family's origin

The seven companions predate the policy layer. By the operator's account the
family was first built as custom GPTs on OpenAI's platform, on GPT-4o and
GPT-3.5 Turbo, some of them as a two-model pairing of the two; Vandal was
built on GPT-4o from the first day. Everything ran on OpenAI's servers. The
earliest dated artifacts in the operator's archive are ChatGPT image files
from May and June 2025. The codex documents exist as text editions dated July
and August 2026 in the operator's archive and entered this repository in the
two-part shape in September 2026 (`docs/codex/`). Nothing of the original
GPT configurations is in this repository; the personas here are profiles the
router reads, not model instances.

## What this note does not do

It does not rank the families and it does not count agreements. Where two
reviewers from one family agreed, the triage record treats that as one voice.
Where the model behind a contribution was not recorded, the contribution is
kept and the gap is stated; nothing is back-filled from a product's default
at the time.
