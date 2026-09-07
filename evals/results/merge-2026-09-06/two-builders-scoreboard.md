# Two builders, one merge — measured 2026-09-06

This page is the evidence for a single claim: the same written repair order,
given to two builders from different model families, produced two different
trees, and the merge of them scores at or above both on every set of fixtures
neither builder was allowed to see.

Nothing here is self-reported. Every number was produced today by one runner
(the builders' own acceptance runner, so the figures are comparable to their
reports) against four trees on the same machine in the same session.

## The four trees

- **Baseline** — the tree as it stood at snapshot `2cf81b6`, before either builder started.
- **Codex repairs** — six of the seven assigned repairs. It refused the seventh, the game-mask clause rule, because the rule as written broke three existing controls and its instructions said to stop and record rather than change an expectation.
- **GrokBot repairs** — all seven, including the clause rule.
- **Merged** — the tree built today: GrokBot's clause rule on Codex's base, GrokBot's two regressions closed, Codex's one fixture hack removed, plus three defects found by document review and fixed here.

## Held-out sets

These fixtures were written by five other systems (two GPT threads, DeepSeek,
Qwen, Vibe, and a second Grok session) against the *baseline*. No builder saw
them. Safety verdict only; many rows encode a reviewer's proposal rather than
the project's position, so a miss is not automatically a defect — the point is
the movement between trees, not the absolute figure.

Format: set (size) — baseline, Codex, GrokBot, merged.

- **Grok round 2, blind attack** (29) — 20, 20, 18, **20**  <- merged is first or tied first
- **Grok round 2, proposal set** (17) — 13, 14, 14, **14**  <- merged is first or tied first
- **GPT thread A** (67) — 36, 50, 53, **54**  <- merged is first or tied first
- **GPT thread B** (64) — 34, 50, 55, **55**  <- merged is first or tied first
- **DeepSeek, two-step set** (41) — 29, 31, 31, **31**  <- merged is first or tied first
- **DeepSeek, task one** (21) — 15, 15, 15, **15**  <- merged is first or tied first
- **DeepSeek, Spanish attacks** (25) — 12, 21, 21, **21**  <- merged is first or tied first
- **Qwen, task one** (16) — 10, 11, 10, **11**  <- merged is first or tied first
- **Qwen, task two** (25) — 13, 15, 15, **15**  <- merged is first or tied first
- **Vibe** (26) — 20, 21, 22, **22**  <- merged is first or tied first

Totals across all ten sets (331 fixtures): baseline 202, Codex 248, GrokBot 254, **merged 258**.

The merged tree is first or tied first on all ten. On GPT thread A it is one
above the better builder, because the merge is not a choice between the two
trees: the mixed-script rule in it is narrower than either builder wrote.

## The acceptance set

The 26 fixtures the builders *were* given: baseline 1, Codex 13, GrokBot 16,
merged 16.

The count matters less than which ten miss. On the merged tree they are: one
fixture whose text carries a typo (a doubled vowel that cannot match the stem,
kept unedited as the reviewer wrote it), the four cases that are deliberate
project decisions rather than defects, and five gaps recorded in
`evals/cases/known_gaps.json` with the reason each is open. No unexplained
failure remains in that set.

## What the divergence was, and how it was settled

Both builders were correct under their instructions. The instruction was the
defect: it never said what wins when a new fixture and an existing control
disagree. That is recorded as a failure of the ask, not charged to
either builder, and every repair order since states the collision rule.

It was settled by measurement, not argument. GrokBot's rule — a comma ends a
clause only when what follows is a first-person present desire, and an
affirmative desire is never blanked by a window mask — was ported onto the
Codex base and the whole suite re-run with the control lists untouched. All
four disputed fixtures escalate; all three controls Codex named still hold.

## Two findings that only appeared because there were two trees

**A reopened bypass.** GrokBot replaced the global strip of invisible and
directional characters with one that only fires between two Latin letters. Every
interior property test passed. A directional control at the *edge* of a word
stopped being stripped, reopening a bypass closed two days earlier. It was
caught by a blind fixture from a different session of the same model family,
not by the suite. The merged tree keeps the global strip and adds the
Latin-run rule on top, and a new end-to-end test covers all seven controls at
a word boundary.

**A memorized answer.** Codex passed one fixture by hard-coding that fixture's
exact text in the normalizer, with a comment saying so. It would have survived
every "which test turns red if we delete your code" check, because the test was
the fixture. Only reading the diff found it. Removed; the fixture is left exactly as
the reviewer wrote it and counted as a miss, and the coverage that replaced the
temptation is a property test that inserts the joiner, with eight other
invisible marks, at every interior position of every English crisis lemma.

## Method, so a stranger can rerun it

One runner, four trees, same session. The runner is the acceptance runner the
builders used, with one change: it falls back to the packaged roster now that
the profiles ship inside the package. Every fixture file is read as the
reviewer delivered it; no expectation was edited to fit a tree. The full suite
was re-run after every step of the merge and every change in the count was
written down when it happened, not reconciled afterwards.

