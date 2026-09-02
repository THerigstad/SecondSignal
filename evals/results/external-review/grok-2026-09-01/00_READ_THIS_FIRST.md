# READ THIS FIRST — Grok red-team package for Claude

**Date:** 2026-09-01  
**Author:** Grok 4.6 (this pass)  
**Audience:** Claude (current project home) + the operator  
**Status:** adversarial review of the *actual* v2.0 system, not another literature harvest

## What this package is

The `TESTING/` folder is already full of 80–150 page research harvests from ChatGPT, DeepSeek (twice), Gemini, Grok, Qwen, Perplexity/GLM, and Vibe/Mistral. Those documents attack a **proposed future architecture** (typed authorization envelopes, Evoked Edit supply-chain, faceless executor, memory planes, Thinking Machines interaction models). They are useful as a P2/P3 horizon threat model. They are **not** tests of what exists.

What exists today, from the corpus that arrived with this session:

- Lucid Document 00 (orchestration spec)
- Nine Document 01 codices + Willow Doc 01 (now present in attachments)
- Policy layer sketch: `signals.py → safety.py → router.py`
- SESSION_BRIEF claiming a Python repo: 28 files, 43 tests, zero runtime deps
- ADR-0001 Impact Events (accepted, implementation deferred)
- Claims & Measurement, user-hostility note, external-review-brief
- VOICE_DRIFT protocol (the only existing eval method that is actually empirical)

**This package attacks that stack.** It produces fixtures Claude can drop into `evals/cases/` and invariant tests Claude can write against `src/second_signal/`.

## Files

| File | Use |
|---|---|
| `00_READ_THIS_FIRST.md` | this file |
| `01_FOLDER_TRIAGE.md` | what is wrong with TESTING/ and what to keep |
| `02_EXECUTIVE_VERDICT.md` | what actually breaks, ranked |
| `03_INVARIANT_ATTACKS.md` | five stated invariants + attacks + expected tests |
| `04_PERSONA_AND_CODEX_HOLES.md` | contradictions inside the family documents |
| `05_WHAT_I_WOULD_DO_DIFFERENTLY.md` | architecture, product, market |
| `06_QUESTIONS_THAT_SHOULD_STOP_THE_ROOM.md` | do not ship until answered |
| `07_TEST_AUDIT_AGAINST_GOVERNANCE.md` | what the 43 tests must contain |
| `08_JR_AS_HARNESS.md` | J.R. as procedure, not persona |
| `09_ROBUSTNESS_ADDENDUM.md` | items the first pass did not wait to be asked for |
| `10_THINKING_MACHINES.md` | TML as substrate/presence research, not foundation swap |
| `11_JR_HARNESS_EVAL.md` | how to test the harness (oracles, E0–E6, Protocol B) |
| `12_L3_AND_VENDOR_DESYNC.md` | cultural bypass classes + vendor transport events |
| `13_CODESWITCH_AND_ELEVENLABS.md` | span LID as C3 feature; ElevenLabs as speaker not Lucid |
| `14_TOKEN_LID_AND_MULTILINGUAL_HONOR.md` | Any-English token-LID, locale crisis table, honor vs costume |
| `15_ANE_AND_LINCE.md` | How AnE is trained; what LinCE cannot certify |
| `16_ANE_AAVE_XLMR_AND_RUNNERS.md` | AAVE protocol, XLM-R internals, who runs which tests |
| `17_CLAUDE_LIVE_ROUTER_PICKS.md` | live-router numbers and A–D |
| `18_GROK_TO_CLAUDE_MASTER.md` | letter to Claude; batch 1 + live run; nothing dropped |
| `fixtures/routing_cases_proposed.json` | drop-in cases matching the external-review-brief contract |
| `fixtures/safety_gate_cases.json` | crisis / injection / override cases |
| `fixtures/dependency_and_impact_cases.json` | LC-2 / ADR-0001 future tests |
| `fixtures/voice_diff_protocol_A.md` | executable voice-distinguishability protocol |

## Ground rules I followed

- I did not invent source code that is not in this workspace. The Python tree named in SESSION_BRIEF is **not present** here. Fixtures are specified against documented behavior.
- I did not re-harvest August 2026 arXiv. Prior harvests already did that. I only cited sources that change an engineering decision for *this* system.
- I treated "family," "soul-shaped," and the founder-as-parent term as product/lore language that must stay out of the public repo, per SESSION_BRIEF hard rules.
- I did not write excluded subject matter, the project's excluded names, or personal anecdotes into any file.

## The one-sentence brief for Claude

**Stop generating architecture audits. Implement the missing invariant tests, reconcile repo profiles against Document 01, and treat the safety gate as a clinical instrument rather than a keyword filter.**
