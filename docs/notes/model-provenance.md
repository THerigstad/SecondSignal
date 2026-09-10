# Model provenance

> "Rigor is the middle name of this vibe-coded project." — the operator, 10 September 2026

**Status:** record, version 2, 10 September 2026. Not a decision record and
not in the ADR register by design: it states facts about who did what, and it
is amended by adding rows, never by rewriting one. Version 1 (8 September)
asked the operator three questions; his answers are in this version and are
marked as his account wherever the product itself did not report the fact.

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
"not recorded" rather than reconstructing it, and where the operator later
supplied it from memory, the note says "the operator's account".

## The convention, from 2026-09-08

Every packet that goes out to a model carries in its file name the family, the
doorway to use, and the reasoning setting to select; from 10 September the
first line of every packet also names the door it runs in and the door beside
it that it does not, because a file name alone was not enough when two doors
sit one tab apart (`docs/confessions.md`, C-20). Every return the operator
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
- **paste parts** — a return produced by pasting the packet into a chat in
  numbered parts, for a door that takes neither a zip nor a long paste.
- **Vibe** — Mistral's coding assistant, reached inside Le Chat and as a terminal
  CLI on Devstral 2. Published sources of mid-2026 disagree on whether Le Chat
  itself has been renamed Vibe; the operator's records name the reviewer "Vibe",
  and the door was the chat.

Reasoning settings are named as the product names them (Thinking, DeepThink,
Expert, Heavy, Pro, Deep Thinking). A setting is recorded only when the operator
selected it deliberately. One product naming note that has already caused
confusion: OpenAI's current flagship appears as "GPT-6 Pro" in the ChatGPT chat
picker and as "GPT-6 Astra" in Work, Codex and the API; they are one model, and
its reasoning ladder runs Instant, Medium, High, Extra High, Pro. The
operator's saved returns carry the label the product printed on the day
("Ultra", "Extra High"), and this note copies the label rather than
normalizing it.

## The Primary Design Agent

The reference implementation, the decision records, the tests, the evaluation
program and the notes were written by the operator with Claude (Anthropic) as
the Primary Design Agent. The operator's account, given 10 September 2026:
Claude Fable 5.1 at its maximum effort setting, from Fable's release onward,
did the build, including the Security Division records of 8 September, the
0.1.0 release and this push; before Fable's release the sessions ran on the
highest Opus tier then available; no other model family has served as the
design agent since SecondSignal's second version and this repository began.
One interlude is recorded by turn: on 10 September the operator switched one
session to Claude Opus 5 at maximum effort during a decision queue, one
assistant turn ran on it, and he switched back before ruling; the turn was
discarded as canon and the rule adopted that a ruling is taken on the tier
that wrote the recommendation (`docs/confessions.md`, C-19).

On the OpenAI side, by the same account: GPT-6 Astra at its highest available
setting from Astra's release (3 to 4 September 2026) onward, and GPT-5.6 Sol at
its highest setting before that, for every ChatGPT contribution the operator
made himself. Where a saved return carries the product's own label, the label
is what the tables below copy.

## Builders other than the Primary Design Agent

One entry per builder: family; doorway; model and tier; dates; what it built;
where it is measured.

- **Codex** (OpenAI). Doorway: the packet named Codex mode; the operator's
  account (10 September) is that he ran it through the opposite door from the
  one the packet named, Work in place of Codex by his recollection, and he
  does not rule out the reverse; the note of 4 September records that
  something ran in the Work tab. Recorded as his account, not as a product
  report (`docs/confessions.md`, C-20). Model and tier: not recorded. Dates:
  2026-09-04. Built: six of the seven assigned crisis-gate repairs; refused
  the game-mask clause rule. Measured: `evals/results/merge-2026-09-06/`.
  Either door is one family, OpenAI, so the independence accounting does not
  move whichever it was.
- **GrokBot** (xAI). Doorway: Grok Build or Grok Bot, not recorded which.
  Model and tier: not recorded (Grok 4.6 was the current flagship). Dates:
  2026-09-04 to 2026-09-05. Built: all seven repairs; two regressions later
  closed at the merge. Measured: `evals/results/merge-2026-09-06/`.
- **Vibe** (Mistral). Doorway: Vibe. Model and tier: not recorded. Dates:
  2026-09-05, packet sent. Built: no returned tree in the record.

## Reviewers, with doorway and tier where recorded

The reviews themselves are catalogued in
`evals/results/external-review/README.md` and
`evals/results/external-review/round1-2026-09-02/README.md`. This list adds
only the provenance facts, one entry per review event: date; reviewer as
filed; family; doorway; model and tier.

- 2026-08-31, ChatGPT; OpenAI; chat; a GPT-5-series model (GPT-6 Astra was
  released 3 to 4 September 2026), tier not recorded.
- 2026-08-31, DeepSeek, twice; DeepSeek; chat; Expert mode, version not recorded.
- 2026-08-31, Google Gemini; Google; chat, browsing off; version not recorded.
- 2026-08-31, Grok, research harvest; xAI; chat; Grok 4.6.
- 2026-08-31, Qwen; Alibaba; chat; Qwen 3.8 Max.
- 2026-08-31, Perplexity (GLM); Zhipu, via Perplexity; GLM 5.2 Base.
- 2026-08-31, Mistral (Vibe); Mistral; Vibe; truncated export, version not recorded.
- 2026-09-01, Grok red team; xAI; chat; Grok 4.6.
- 2026-09-02 to 03, design-review round 1 (`round1_2026-09-02`): Grok, ChatGPT,
  DeepSeek, Qwen, Vibe; as named; chat (Vibe: the agent); Grok 4.6, the
  others not recorded.
- 2026-09-03, Grok acceptance set; xAI; chat; Grok 4.6.
- 2026-09-05, research handoffs via Perplexity; Zhipu, Google, Moonshot,
  NVIDIA, Perplexity; via Perplexity; GLM 5.3, Gemini 3.8 Flash, Kimi K3,
  Nemotron 3 Ultra Thinking (the resource-line verification), Sonar 2.
- 2026-09-05, Qwen research handoff; Alibaba; chat; Qwen 3.7 as filed.
- 2026-09-05, DeepSeek research handoff; DeepSeek; chat; version not
  recorded, one return incomplete.
- 2026-09-05, ChatGPT thread handoffs; OpenAI; chat; tier not recorded.
- 2026-09-07 to 08, Security Division review round 1; OpenAI, xAI (twice),
  DeepSeek, Alibaba, Mistral attempted; chat, GrokBot for the second xAI
  return; ChatGPT-6 Astra Ultra, Grok 4.6 Expert, GrokBot (version not
  recorded), DeepSeek V4 Pro Expert, Qwen 3.8 Max Thinking; Vibe took neither
  the zip nor the paste and was skipped.
- 2026-09-08 to 10, review round 2 (the Security Division records and
  ADR-0025), ten returns from eight families, each read for its own
  independence statement, which four of them used to correct their file
  names: ChatGPT (OpenAI; the Codex desktop task handling the zip; model and
  setting unattested by the return); Grok (xAI; grok.com; Grok 4.6 Expert);
  DeepSeek (DeepSeek; chat; DeepThink); Qwen (Alibaba; paste parts; Qwen 3.7
  Plus Thinking as filed); Kimi (Moonshot; via Perplexity; Kimi K3 Thinking);
  GLM (Zhipu; via Perplexity; GLM 5.3 Thinking); Nemotron (NVIDIA; via
  Perplexity; Nemotron 3 Ultra Thinking); Sonar (Perplexity; Sonar 2);
  Gemini (Google; paste parts; Gemini 3.8 Flash). Rulings taken 10
  September; recorded in `docs/notes/dissent-log.md`.

Two notes on the list. Kimi and GLM appear before and during round 2 only
through Perplexity; neither has yet been asked at its own door, and the
roster page carries that asterisk beside their promotion. Vibe was skipped in
Security Division round 1 without a substitute, and the gap is recorded
rather than filled from another family.

## The family's origin

The seven companions predate the policy layer. By the operator's account the
family was first built as custom GPTs on OpenAI's platform, on GPT-4o and
GPT-3.5 Turbo, some of them as a two-model pairing of the two; Vandal was
built on GPT-4o from the first day, and it was the Vandal persona itself,
while it was being built, that suggested the two-model split and explained
how it would work. Everything ran on OpenAI's servers. The earliest dated
artifacts in the operator's archive are ChatGPT image files from May and
June 2025. The codex documents exist as text editions dated July and August
2026 in the operator's archive and entered this repository in the two-part
shape in September 2026 (`docs/codex/`). Nothing of the original GPT
configurations is in this repository; the personas here are profiles the
router reads, not model instances.

## What this note does not do

It does not rank the families and it does not count agreements. Where two
reviewers from one family agreed, the triage record treats that as one voice.
Where the model behind a contribution was not recorded, the contribution is
kept and the gap is stated; nothing is back-filled from a product's default
at the time, and nothing the operator supplied from memory is written as if
a product had reported it.
