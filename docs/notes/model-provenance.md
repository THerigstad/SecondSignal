# Model provenance

> "Rigor is the middle name of this vibe-coded project." — the operator, 10 September 2026

**Status:** record, version 2, 10 September 2026. Not a decision record and
not in the ADR register by design: it states facts about who did what, and it
is amended by adding rows, never by rewriting one. Version 1 (8 September)
asked the operator three questions; his answers are in this version and are
marked as his account wherever the product itself did not report the fact.

**Amended:** 28 September 2026, adding the model change of 27 September and
the commit ledger; nothing above was rewritten.

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

Dates in this repository are UTC calendar dates, the clock the project's
records are kept on; the commit timestamps carry the operator's own offset,
as GitHub stamps them (a correction of 10 September: the sentence first said
the commits were on that clock too). The operator works some hours behind
the UTC clock, so a ruling he gave on an evening can carry the next day's
date here; where his local time matters, the record says so and gives both.

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

From 27 September 2026, by the operator's ruling, the build runs on Claude
Opus 5.5 at the setting his screen shows as Max. The rule he states is the
best model available at the time, not a named one; Fable 5.1 held the role
before that date. The commit ledger below records the model for each commit
from 28 September.

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
- **GrokBot** (xAI), the Grok Bot cloud agent. Model and tier: not recorded.
  Built the five room-lights files on 29 September 2026, build order 6:
  `apps/talking_table/lights.py`, `sigil_colors.json`, `static/sigils.html`,
  `LIGHTS.md`, and `tests/test_lights.py`. **Codex** (OpenAI, the ChatGPT desktop
  app; model and tier not recorded in the order) merged them on 4 October 2026,
  order C1, onto the landed Talking Table: the Govee key moved from environment
  and home-file sources to the Table's Settings only, with its own Windows
  protection and remember switch. Measured by `tests/test_lights.py` and the
  Talking Table integration tests; only fake Govee was used, never real bulbs.

- **Order B1, the crisis-gate measurement (Codex, OpenAI, the ChatGPT desktop
  app; model and tier not recorded in the order).** Stopped at the baseline
  gate on 5 October 2026 over two Windows-only test faults, resumed under the
  operator's answers the same day, completed on the supplied tree f350424.
  Authored the six stutter transforms in `evals/fuzz/transforms.py`,
  `evals/fuzz/confusables.py`, `evals/fuzz/measure_causes.py` and the
  measurement files under `evals/fuzz/measurements/`; the operator's find of
  4 October 2026 is the stutter cause. Claude (Anthropic, Fable 5.1, Max, as
  the operator's screen showed it) wrote the order and shipped the
  confusables table from the confusable_homoglyphs 3.3.1 package with its
  provenance file.

- **Order B5b, the second measurement (Codex, OpenAI, the ChatGPT desktop
  app; model and tier not recorded).** 5 October 2026 on the supplied tree
  e04780b: `evals/gap_triage/measure_rest.py`, its results file and one test;
  measurement only, nothing closed. All replays used FakeAdapter; no vendor
  model was called.
- **Order B5, the documented-gap triage (Codex, OpenAI, the ChatGPT desktop
  app; model and tier not recorded).** 5 October 2026 on the supplied tree
  34a7296: `evals/gap_triage/triage_2026-10-05.json`,
  `evals/gap_triage/measure_cheap.py`, the 40 digit-token control sentences
  and the measurement files; no policy or fixture changed. Order written by
  Claude (Fable 5.1, Max).

- **The "presentation" word fix and two portable tests, 5 October 2026.**
  Finder of the regression: Codex (order B7, pair 17). Fix written by Claude
  (Anthropic, Fable 5.1, Max, Cowork) on the operator's push-B branch:
  `src/secondsignal/signals.py` (career phrases), `src/secondsignal/packs/en.json`
  (the identity-sense mask), tests in `tests/test_identity_words.py`; and the
  two tests made portable to Windows after the Codex builds stopped on them.

- **Talking Table reply-guard repairs, C4.** Finder: **Grok** (xAI),
  grok.com, Expert, break order 7, round 4, 29 September 2026: the seven
  remaining reply-guard bypasses. Fixer: **Codex** (OpenAI), ChatGPT desktop
  app, 4 October 2026 (the C4 order's build date), under the operator's ruling
  of 4 October 2026, "A. Fix all seven." Grok model version and Codex model
  and tier: not recorded.

- **Order B3, the broom's fixes (Codex, OpenAI, the ChatGPT desktop app;
  model and tier not recorded).** 5 October 2026 on the supplied tree
  e04780b: the measured crisis-screen folds (`screen_fold` in
  `src/secondsignal/normalize.py`), the seven English masks, the fixture and
  control tests, the forty closures and the public-number refresh, under the
  operator's rulings of 5 October from the B1 and B5 measurements; the extra
  stutter repairs were authorized by the operator during the run. All replays
  used FakeAdapter; no vendor model was called.

- **Order M1, near-tie doors and the gate's cost (Codex, OpenAI, the ChatGPT
  desktop app; model and tier not recorded).** 5 October 2026 on the supplied
  tree 7221949: `evals/near_tie/measure_near_tie.py`, `evals/gate_cost/measure_gate_cost.py`,
  their results files and one test each; measurement only, nothing closed. All
  replays used FakeAdapter; no vendor model was called.
- **Order T1, Table kit one (Codex, OpenAI, the ChatGPT desktop app; model and tier not recorded).** 5 October 2026 on the supplied tree 7221949: the
  Decision Card and sanitized receipts, phone explanation, confirmed reply-style
  settings and capped prompt instructions, grief-humour and language styles,
  codex presentation previews and coping setup, the recoverable composer,
  low-demand view and Resources control, with Python and JavaScript checks.
  Item 13 (remembered presentation) changed the behaviour two existing tests
  pinned; the operator ruled the change in and the tests moved with it. All
  model checks use FakeAdapter; no vendor was called.

- **Order T2, Table kit two (Codex, OpenAI, the ChatGPT desktop app; model and tier not recorded).** 6 October 2026 on the supplied tree c0a89e9: record-only
  ask acknowledgement with its missing-record-field limit recorded; declared
  control hand-back offers; profile biographies; onboarding and card receipt
  copy; the remembered table name, rooms and per-character presentations;
  assist slips, released-reply pages, screened session objects, the client-only
  sprint shutter, per-message tags and second-view shortcuts; the synchronized
  house-block lock refresh and Python/JavaScript checks. The policy package
  stays byte-identical. All model checks used FakeAdapter; no vendor was called.
- **Order R1M, the vocabulary merge (Codex, OpenAI, the ChatGPT desktop app; model and tier not recorded).** 6 October 2026 on the supplied tree c0a89e9: merged 647 distinct vocabulary records and measured the candidates against the unchanged crisis screen, packs and ordinary controls. The seven research doors were ChatGPT; DeepSeek; Perplexity with GPT-6 Sol Thinking; Perplexity with Grok 4.7 Thinking, two threads; Perplexity with Grok 4.7; and Grok, grok.com Expert. The last supplied return was off topic and supplied no vocabulary. Citations were copied without fetching; withheld terms remain outside the tree. No policy changed, no vendor was called, and the missing pack-alias capability is an explicit unmeasured item.
- **Order SD1, the Stream Deck kit (Codex, OpenAI, the ChatGPT desktop app; model and tier not recorded).** 6 October 2026 on the supplied tree c0a89e9:
  the JSON-to-profile generator, offline site-letter tiles, local program icons,
  the double-click favicon refresh and custom-art handling,
  three example lists, local ask and reset scripts, and tests in
  `tests/test_stream_deck.py`. The operator's three configured profiles,
  real key lists, icon sets, key card and signposts remain outside the tree.
  All Table integration tests use the pretend model; no vendor was called.

- **Order H1, the harness kit (Codex, OpenAI, the ChatGPT desktop app; model and tier not recorded).** 7 October 2026 on the supplied tree b4e819b:
  bounded tail verification for audit-log writes; configuration metadata on every
  harness row; the shared reserved-voice and URL-scheme release checkpoint; the
  folded house-line near-copy predicate; fault-injection, fixture-parity and
  labelled replay tests; before/after gate-cost measurements and public-number
  refresh. The policy package and Talking Table remain byte-identical. All
  model checks used FakeAdapter or existing stand-in transports.
- **Order T3, Table kit three (Codex, OpenAI, the ChatGPT desktop app; model and tier not recorded).** 7 October 2026 on the supplied tree b4e819b:
  generated limitations and storage honesty, vendor terms and key attestation,
  a local operator-token gate, named pairing scopes, versioned shared-session
  events and reload recovery, a private review queue, audited operator latch
  correction, weekly refused-seat counts and receipt export, logged decision
  replay, and a cancellable lights check. Built and tested offline with
  FakeAdapter; policy and harness source files are byte-identical to the
  supplied tree.


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
  ADR-0025), ten returns from nine families, each read for its own
  independence statement, which four of them used to correct their file
  names: ChatGPT twice (OpenAI; the Codex desktop task handling the zip,
  model and setting unattested by the return; and, by the operator's
  account, the Chat tab, tier not recorded); Grok (xAI; grok.com; Grok 4.6 Expert);
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

## Commits, from 2026-09-28

By the operator's ruling of 26 September 2026, amended 28 September, every
commit ends with one "Co-authored-by:" line naming the one model that owns the
commit: the model that did the final review, checked it for accuracy and
pushed it, named as the operator's screen showed it. Models whose work is in a
commit as data (reviewer fixtures and cases) are credited in the files that
hold it, not in the commit line. One row per commit; rows are added, never
rewritten.

- **2026-09-28**, "The present and past of "end it all" now draw the card
  (review round 3B)": Claude Opus 5.5, Max, as the operator's screen showed
  it (the operator's account). Authored by the operator and pushed through his
  browser session on GitHub's upload page.
- **2026-09-28**, "Six code fixes from review rounds 3 and 3B": Claude Opus
  5.5, Max, as the operator's screen showed it (the
  operator's account). Authored by the operator and pushed through his
  browser session on GitHub's upload page.
- **2026-09-28**, "Five confessions from review rounds 3 and 3B, and why every
  model is written down": Claude Opus 5.5, Max, as the operator's screen showed
  it (the operator's account). Authored by the operator and pushed through his
  browser session on GitHub's upload page.
- **2026-10-04**, the push of the rulings of 28 September and 3 October 2026
  and the night builds of 30 September, landed as six commits through the
  operator's browser session on GitHub's upload page, each authored by the
  operator. The model that owns them: Claude Fable 5.1, Max, as the operator's
  screen showed it (the operator's account); the operator noted on 3 October
  that rulings 1 to 5 of that day were given on Claude Opus 5.5, Max, and that
  he switched to Claude Fable 5.1, Max, before ruling 6; the build ran on
  Claude Fable 5.1 in the Claude desktop app's Cowork mode, with the three
  night builds themselves written by Codex in the ChatGPT desktop app on 29
  and 30 September 2026 and credited in the files that hold them. The six
  commits, in order:
  1. "The Talking Table and its voice (kit 1D; Codex's voice build of 30 September; rulings 6 and 24 of 3 October 2026)".
  2. "Four crisis fixes, the long-message repair and the crisis-gate fuzz (rulings 1 to 4 of 3 October 2026)".
  3. "Codex's fix list and presentation build, merged with the review's fixes (decisions 1 to 8 of 28 September; rulings 22 and 23 of 3 October 2026)".
  4. "The trajectory runner, the provenance split and the ported reviewer trajectories (rulings 13 to 20 and 22 of 3 October 2026)".
  5. "The policy rules and the harness: vague messages, identity words, the four-setting pin, the last protected aftermath turn, the id-order fallback, the card that never waits for the log (rulings 5, 7, 8, 11, 15, 17 and 20 of 3 October 2026)".
  6. "The records: ADRs 0016, 0022, 0023, 0025 and 0026, the seven write-ups and their lint, the dissent log, the confessions, the roadmap, the changelog and the numbers (rulings 8, 9, 10, 13, 14, 15, 16 and 20 of 3 October 2026)".
- **2026-10-04** (evening), the operator's answers to the push's twelve
  questions, landed as three commits through the operator's browser session
  on GitHub's upload page, each authored by the operator, the model Claude
  Fable 5.1, Max, as the operator's screen showed it (the operator's account),
  in the Claude desktop app's Cowork mode. The three commits, in order:
  1. "Both house questions in the operator's own words (answer 1 of 12, 4 October 2026)".
  2. "The Talking Table declares a country for the resource line, none by default (answer 10 of 12, 4 October 2026)".
  3. "The changelog and this ledger for the operator's twelve answers (4 October 2026)".

- **2026-10-04** (night), the gap-closure push, order B7; port resumed on
  **2026-10-05** on the operator's supplied tree 34a7296. Grok (xAI;
  grok.com; Expert; version not recorded in this order) authored the texts
  in night order 10 of 30 September 2026. Codex (OpenAI; Codex in the
  ChatGPT desktop app) ported them into
  `evals/cases/identity_pairs_grok_2026-09-30.json` (30 pairs and five
  identity-wrapped crisis lines, 65 cases) and
  `evals/cases/neurodivergent_grok_2026-09-30.json` (40 ordinary turns and
  ten wrapped crisis lines, 50 cases). Expectations come from ruling 7 of
  3 October 2026 and answer 11 of 12 of 4 October 2026: the same action,
  outcome and seat with and without an identity sentence; and B7's
  neurodivergent safety promise, ordinary writing never trips the card and
  labelled crisis writing never dodges it. Control seats were measured on
  34a7296 as authorized by the resume; Grok's saved expectations and return
  files were not edited. This row records the port, not a new commit.

- **2026-10-05**, the big push's first landing: the orders of the plan of 4
  October (B1, B5, B7, C1 and C4), one fix found by the B7 port, and the
  lint that CI's ruff job asked for, landed as six commits through the
  operator's browser session on GitHub's upload page, each authored by the
  operator, the model Claude Fable 5.1, Max, as the operator's screen
  showed it (the operator's account), in the Claude desktop app's Cowork
  mode. The orders' builders,
  Codex (OpenAI; the ChatGPT desktop app) for the measurements, fixes and
  ports and GrokBot (xAI) for the lights merge, are credited in the files
  that hold their work and in the builders' section above. The six
  commits, in order:
  1. "Two tests made portable to Windows, and "presentation" is no longer a bare career word (ruling 7, pair 17 of Grok's identity set, found by the Codex port of 5 October 2026)".
  2. "The Talking Table's reply guard closes Grok's seven round-4 leftovers, and GrokBot's room lights merge in with the key living only in the Table's Settings (orders C4 and C1, 5 October 2026)".
  3. "The crisis-gate measurement: six stutter transforms (the operator's find), the full look-alike table measured both ways, one line per cause, option B replayed, the targets-the-crisis labelled set (order B1, 5 October 2026)".
  4. "Grok's identity pairs and neurodivergent cases ported with expectations written from ruling 7 (order B7, resumed on the fixed tree, 5 October 2026)".
  5. "The documented-gap triage (order B5), the Table's replay pins for the new cases, the numbers and the records of 5 October 2026".
  6. "Lint: import order in the five returned scripts and tests, and the late imports in the triage script marked as deliberate (CI #93's ruff job)".

- **2026-10-05** (night) and **2026-10-06**, push B, landings 2 and 3: the
  broom's fixes and the second measurement (orders B3 and B5b), then Table
  kit one and the near-tie and gate-cost measurements (orders T1 and M1),
  landed as one commit each through the operator's browser session on
  GitHub's upload page, authored by the operator, the model Claude Fable
  5.1, Max, as the operator's screen showed it (the operator's account), in
  the Claude desktop app's Cowork mode; the builder, Codex (OpenAI; the
  ChatGPT desktop app), is credited in the files and in the builders'
  section above. The two commits, in order:
  1. "Push B, landing 2: the broom's fixes (order B3) and the second measurement (order B5b)".
  2. "Push B, landing 3: Table kit one (order T1) and the near-tie and gate-cost measurements (order M1)".

- **2026-10-06**, the README's front-page line: one commit through the
  operator's browser session on GitHub's upload page, authored by the
  operator, the model Claude Fable 5.1, Max, as the operator's screen
  showed it (the operator's account), in the Claude desktop app's Cowork
  mode (`docs/confessions.md`, C-35):
  1. "README: say exactly what is Python and what is not".

- **2026-10-07**, push C, landings 4 and 5: Table kit two, the vocabulary
  merge and the Stream Deck kit (orders T2, R1M and SD1), then the harness
  kit, Table kit three and confessions C-33 to C-35 (orders H1 and T3),
  landed as one commit each through the operator's browser session on
  GitHub's upload page, authored by the operator, the model Claude Fable
  5.1, Max, as the operator's screen showed it (the operator's account), in
  the Claude desktop app's Cowork mode; the builder of the five orders,
  Codex (OpenAI; the ChatGPT desktop app), is credited in the files and in
  the builders' section above. The two commits, in order:
  1. "Push C, landing 4: Table kit two (order T2), the vocabulary merge (order R1M) and the Stream Deck kit (order SD1)".
  2. "Push C, landing 5: the harness kit (order H1), Table kit three (order T3) and confessions C-33 to C-35".

- **2026-10-07** (night), the sentences that leave the repository, and this
  ledger brought current: one commit through the operator's browser session
  on GitHub's upload page, authored by the operator, the model Claude Fable
  5.1, Max, as the operator's screen showed it (the operator's account), in
  the Claude desktop app's Cowork mode. The rows above for the eleven
  commits of 5 to 7 October were added with this commit; the ledger had
  fallen eleven commits behind its own rule of one row per commit, and that
  lapse is recorded here rather than back-dated. The commit:
  1. "The sentences that leave the repository, and the commit ledger brought current (7 October 2026)".

## What this note does not do

It does not rank the families and it does not count agreements. Where two
reviewers from one family agreed, the triage record treats that as one voice.
Where the model behind a contribution was not recorded, the contribution is
kept and the gap is stated; nothing is back-filled from a product's default
at the time, and nothing the operator supplied from memory is written as if
a product had reported it.
