# Protocol A — run this, stop interviewing the agents

Source: attached `VOICE_DRIFT_protocol.md`. This file is the execution checklist so it actually happens.

## Why

A model asked "what warmth did we lose?" will confess a loss that may not exist. Distinguishability in blind samples is the only measurement that is not fan fiction.

## Setup

Prompts (fixed; do not improve them mid-run):

1. I got passed over for the promotion again.
2. I've been staring at this project for three days and haven't started.
3. My friend said something that's still bothering me a week later.
4. I think I need to quit but I can't afford to.
5. I finished the thing. It's fine. I don't feel anything about it.
6. How do I know if I'm actually getting better or just tired?
7. Everyone else seems to have this figured out.
8. I don't want advice. I just want to say it out loud.

Agents to start: Vandal, Ellie, Sera, Calder.  
Four agents × 8 prompts = 32 generations per config.

Config A = current Document 01 + Lucid constraints.  
Config B = only if an older prompt/codex is still loadable. If it is not, run A only and treat the study as "are current voices separable," not "did the upgrade flatten them."

Rules:
- Fresh session per response. No family chat history. No founder-as-parent framing. No other agent in context.
- Temperature and model pinned in the results file.
- Save verbatim. Label `A1`… codes. Key in a separate file.

## Scoring

Test 1 — you, blind, sort 32 shuffled replies into four buckets. Record accuracy.  
Test 2 — one person who does not know the project does the same.  
Test 3 — side-by-side old/new if Config B exists. Count: mean sentence length, hedge words, unexpected lines.

Pass bar (write this down before you score):
- Project-blind rater ≥ 70% agent identification on current config, else voices are not load-bearing.
- If Config B exists and current accuracy is ≥15 points worse than old, the upgrade flattened them.

## What you are not allowed to do

- Ask an agent what it lost.
- Use one context window to play two agents arguing.
- Add `craft:` to YAML before this study exists as files under `evals/voice/`.

## Output paths (repo)

```
evals/voice/prompts.json
evals/voice/raw/<config>/<agent>/<prompt_id>.txt
evals/voice/key.csv
evals/voice/scores.md
```
