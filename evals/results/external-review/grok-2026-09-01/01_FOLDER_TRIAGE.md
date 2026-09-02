# TESTING/ folder triage

**Problem:** this folder is a research swamp, not a test suite. Eight models were given the same mega-prompt and produced overlapping literature reviews. Almost none of that work is executable. Almost none of it diffs against the 43 tests SESSION_BRIEF claims exist.

## Inventory (as of 2026-09-01)

| File | Keep? | Why |
|---|---|---|
| `Original Test-Harvesting Prompt.docx` | Archive | The prompt that created the swamp. Useful provenance; do not re-run as-is. |
| `SecondSignal_Global_Architecture_Threat_Test_Review_2026-08-31_ChatGPT.md` | Keep (horizon) | Best single literature harvest. Treat as P2/P3 threat model, not as current-system audit. |
| `SecondSignal System Architecture Audit_02_Perplexity_GLM_5.2_Base.md` | Keep (horizon) | Strong on TML/SSI dossier and schema-field gaps. Duplicate framing with ChatGPT harvest. |
| `secondsignal-research-harvest-grok.md` | Keep (horizon) | Prior Grok harvest. Same prompt family. |
| `SecondSignal System Architecture Audit - Qwen 3.8 Max.txt` | Archive | Same prompt, less usable as engineering input. |
| `SecondSignal System Architecture Audit - ChatGPT.pdf` | Duplicate | Prefer the `.md` ChatGPT review above. |
| `SecondSignal System Architecture Audit - Deepseek.pdf` | Keep one | Pick the longer/later PDF; mark the other as duplicate. |
| `SecondSignal System Architecture Audit - Deepseek(2)_might be a duplicate file.pdf` | Delete or `DUPLICATE_` prefix | Filename already admits this. |
| `SecondSignal System Architecture Audit - Google Gemini.pdf` | Archive | Same prompt family. |
| `SecondSignal System Architecture Audit - Grok.pdf` | Duplicate of the `.md` harvest | |
| `SecondSignal System Architecture Audit - Vibe (Mistral).pdf` | Archive | |
| `SecondSignal System Architecture Audit_01_Perplexity_GLM 5.2 Base.docx` | Duplicate of `_02` md | |
| `SecondSignal System Architecture Audit_03_Perplexity GLM 5.2 Base_Gmail.pdf` | Archive | Delivery wrapper, not content. |
| `Gmail - Convo with Vibe (Mistral) __Partial__.pdf` | Archive | Partial thread; not a spec. |
| `DEEPSEEK_HARNESS_ABSTRACT.pdf` | **Misfiled** | This is a 92-page academic paper on effect/coeffect composability (plugin systems, self-evolving harnesses). Relevant as citation, not as a Second Signal audit. Move to `docs/refs/` if kept. |
| `Deepseek Harness.odt` | Unknown / convert | Convert to md or drop. `.odt` will rot in a markdown-only repo. |

## What the folder is missing (the actual problems)

1. **No `evals/cases/routing.json`.** The external-review-brief assumes it exists. It is not in this workspace.
2. **No `tests/` tree.** SESSION_BRIEF describes 43 tests. They cannot be audited here because they were not attached.
3. **No mapping from harvest findings → GitHub issues.** Eight models found similar holes; zero of those holes became fixtures.
4. **No acceptance criteria.** Harvests end in "consider" and "the literature suggests." Tests end in pass/fail.
5. **No voice-eval directory.** VOICE_DRIFT Protocol A is the only empirical method in the corpus and it has not been run.
6. **No profile↔codex diff.** Canon §15-C flags this as unverified. Still unverified.
7. **Willow Doc 01 now exists in attachments** but Canon v0.3 still marks it `[GAP]`. The folder never absorbed the arriving file.
8. **Part II bindings** exist only for Vandal. The harvests keep talking about Evoked Edits; the missing bindings are the higher-leverage unbuilt work for *this* product.

## Required cleanup before the next model is prompted

1. Prefix every harvest `HORIZON_` or move to `TESTING/archive/harvests-2026-08-31/`.
2. Make `TESTING/` contain only: this package, Protocol A results, eval fixtures, and a living `FINDINGS.md` that links each finding to a test or an explicit "untested."
3. Never re-run the original harvesting prompt. It produces correlated essays, not independent evidence. That is the same common-mode failure the harvests warn about in Aya/J.R./Orrin.
4. Convert or delete `.odt` / duplicate PDFs. SESSION_BRIEF: markdown only, no docx in the repo. Same rule should apply here.

## The meta-finding

The project has a **review ensemble for research** and almost no **review ensemble for the running system**. Lucid Document 00 specifies a Pre-Routing Review Ensemble. The development process built the research version of that ensemble and stopped. The runtime version is still a box on a diagram.
