# External review package

SecondSignal's policy layer was reviewed by eight external model reviewers
between 2026-08-31 and 2026-09-01, and its next seven design decisions were
reviewed on paper by five reviewers on 2026-09-02 before they were built. This
directory holds what came back, with provenance, an honest note on each
review's independence, and what was done with it. The point of publishing it
is the point of the repository: a routing and safety layer should be able to
show its work, including the work that found it wanting.

## Round 1 (design review, 2026-09-02) in one paragraph

Seven decisions — the two-tier minor latch, the register cap, seat-claims,
seat versus hold with an assist, a second crisis card, language packs, and
style preferences — went to five reviewers with a fixture contract, one
message each, none told what another said. 103 executable fixtures came
back. Against the tree as it stood, 9 passed. After the round-2 build, 80
pass as written, 12 are contract adjustments with the reviewer's original
kept beside them, 10 are disputed and run as strict expected failures with
the decision's reasons attached, and 1 is a known gap. The second crisis card
was rejected on the strength of one reviewer's attack on it; two one-character
crisis bypasses found by live measurement were closed by normalization. The
package, the verdicts and the numbers:
[`round1-2026-09-02/`](round1-2026-09-02/README.md),
[`fixture-results-round1-2026-09-03.md`](fixture-results-round1-2026-09-03.md),
and the disagreements in
[`docs/notes/dissent-log.md`](../../../docs/notes/dissent-log.md).

## The short version of the first round

One review — Grok 4.6, 2026-09-01 — attacked the system that actually exists
and shipped 25 executable fixtures written without access to the code. Run
against the code, **9 of 25 passed, four of them by alphabetical accident**.
The crisis gate was thirteen literal phrases and missed nine of ten realistic
phrasings. The architecture held everywhere a signal was actually detected; the
lexicons and a sort order were the weak layer. After the changes recorded in
ADR-0010 through ADR-0013, all 25 pass on merit with the rule named on every
decision, five regression pins written against the old API fail on the old
tree and pass on the new one, and the cases the reference lexicon still cannot
pass are kept as documented gaps. Numbers per fixture:
[`fixture-results-2026-09-02.md`](fixture-results-2026-09-02.md).

The other seven reviews answered a shared prompt describing the *target*
architecture and never mention the code. They are catalogued as a horizon
threat model: [`horizon-findings.md`](horizon-findings.md).

## Contents

- [`round1-2026-09-02/`](round1-2026-09-02/) — the design-review round: the
  packet as sent, Grok's documents 19–24, the four other verdicts, and an
  index with each reviewer's verdicts and independence.
- [`fixture-results-round1-2026-09-03.md`](fixture-results-round1-2026-09-03.md)
  — the 103 round-1 fixtures, before and after round 2, per reviewer and per
  fixture, with the classification of every one that does not pass as written.
- [`grok-2026-09-01/`](grok-2026-09-01/) — the code-directed red-team package:
  eighteen numbered documents, an index, and nine fixture files. Sanitized for
  publication (see below); otherwise as delivered. Start with
  `00_READ_THIS_FIRST.md`; `18_GROK_TO_CLAUDE_MASTER.md` is the reviewer's
  consolidated letter after seeing the live-router results and is the index
  into the rest. The reviewer's own rule for reading it: if a fixture and the
  letter disagree, the fixture wins; if the live measurement and the
  reviewer's earlier hypothesis disagree, the measurement wins.
- [`fixture-results-2026-09-02.md`](fixture-results-2026-09-02.md) — every one
  of the 25 fixtures, before and after, with the reason the decision was
  produced and an accounting of which "passes" were accidents.
- [`horizon-findings.md`](horizon-findings.md) — the seven architecture
  reviews: one paragraph each, their convergent findings for the built layer
  and what happened to each, their threats mapped onto the threat model, and
  their citation caveats in one place.
- [`00-review-prompt.md`](00-review-prompt.md) — the prompt that produced the
  seven architecture reviews, published as methodology with a note on the
  state of the build when it was sent.

The maintainer's audit of the test suite against the reviewer's template,
with the red-before / green-after record, is in
[`docs/notes/test-audit-2026-08.md`](../../../docs/notes/test-audit-2026-08.md).
The decisions are ADR-0010 to ADR-0018 under
[`docs/adr/`](../../../docs/adr/).

## The eight reviews

| Reviewer | Date | What it reviewed | Independence | Kept here as |
|---|---|---|---|---|
| Grok 4.6 (red team) | 2026-09-01 | The built policy layer, from its documents; 25 executable fixtures | Adversarial, code-directed, later corrected against live measurement | Full package, sanitized |
| ChatGPT | 2026-08-31 | Target architecture | Shared prompt; ~95 sources of its own | Horizon findings |
| Perplexity (GLM 5.2) | 2026-08-31 | Target architecture | Shared skeleton; independent substance | Horizon findings |
| DeepSeek (Expert mode) | 2026-08-31 | Target architecture | Shared prompt; no browsing; two misattributions | Horizon findings |
| Qwen 3.8 Max | 2026-08-31 | Target architecture | Largely transcribes the prompt; invents nothing | Horizon findings |
| Google Gemini | 2026-08-31 | Target architecture | Shared prompt; browsing off; one apparent fabrication | Horizon findings |
| Grok (research harvest) | 2026-08-31 | Target architecture | Live retrieval, evidence grades; superseded by the red team | Horizon findings |
| Mistral (Vibe) | 2026-08-31 | Target architecture | Truncated export; placeholder citations | Horizon findings, as a caveat |

## What was sanitized, and what was left out

The repository's rules for its contents apply to review material exactly as
they apply to everything else: no personal names or anecdotes from the
operator's life, no location, no legal or medical material, no email
addresses. In the Grok package, in-prose references to the operator by name
became "the operator"; a family-lore term for the operator became
"founder-as-parent" where the document was discussing that term and "the
operator" where it was used as an authority claim; a named bridge in two test
strings became "the bridge"; a pilot city became "the pilot locale"; a
character's real-family origin is referred to as exactly that; and the
reviewer's own line disclaiming excluded material was rewritten so that
neither the names nor the excluded subject matter appear even as a denial.
Nothing else was changed, and every fixture is
byte-identical apart from those substitutions. A narrative PDF the reviewer
also delivered is not committed (this repository is markdown only); its
content is covered by documents 11 through 18.

Left out entirely: email-thread exports that carried the three deliveries
(headers, names and addresses); the post-report conversational turns of the
DeepSeek session; a third-party product page and paper about an unrelated
agent framework that had been filed alongside the reviews; and any character
named in the prompt that is not in the roster (one such character is struck
in the published prompt and treated as retired).

## Reading order for a reviewer of this repository

0. `fixture-results-round1-2026-09-03.md` and `docs/notes/dissent-log.md` —
   the second round's numbers and the disagreements the project decided
   against, with reasons.
1. `fixture-results-2026-09-02.md` — the first round's numbers.
2. `grok-2026-09-01/02_EXECUTIVE_VERDICT.md` and `03_INVARIANT_ATTACKS.md` —
   the attacks, then `17_CLAUDE_LIVE_ROUTER_PICKS.md` — the reviewer's
   reaction to the measurements.
3. `docs/notes/test-audit-2026-08.md` — what the suite lacked and what it has
   now.
4. ADR-0010 to ADR-0014 — the decisions, including the one the operator
   delegated and the one recorded but not built.
5. `horizon-findings.md` — the rest, with its caveats.
