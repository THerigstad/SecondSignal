# Round-1 external design review, 2026-09-02

Before round 2 was built, its seven design decisions were sent on paper to
five model reviewers, each separately, none told what another said, with a
fixture contract so that every attack could be run against the code once it
existed. This directory holds what went out, what came back, and what was
done with it. The numbers are in
[`../fixture-results-round1-2026-09-03.md`](../fixture-results-round1-2026-09-03.md);
the disagreements the project decided against are in
[`docs/notes/dissent-log.md`](../../../../docs/notes/dissent-log.md).

## Contents

- [`00-review-packet.md`](00-review-packet.md) — the packet as sent: what
  existed, the seven decisions with the questions asked of each, the house
  lines under review, and the fixture contract.
- [`grok/`](grok/) — the code-directed reviewer's round-1 documents 19–24:
  its verdict and fixtures (19), the idiom-mask and Spanish-pack design
  (20–22), the NFKC-versus-skeleton measurement (23), and the week's ticket
  list with its do-not-push checklist (24). Documents 00–18 are the earlier
  red-team package under [`../grok-2026-09-01/`](../grok-2026-09-01/).
- [`verdicts/`](verdicts/) — the four other reviewers' replies, transcribed
  with the transport headers removed and nothing else edited: ChatGPT,
  DeepSeek, Qwen, Vibe (Mistral).
- The 103 fixtures, ingested with their round-2 classification, live in
  [`evals/cases/round1_2026-09-02/`](../../../cases/round1_2026-09-02/) and
  run in CI. The Unicode vectors from document 23 live in
  [`evals/vectors/unicode_normalize_vectors.json`](../../../vectors/unicode_normalize_vectors.json).

## The five reviews

- **Grok 4.6** — 45 fixtures. Accept-with-change on Decisions 1–4 and 6; reject on 5 (the second card). Wrote the mask engine, the Spanish pack design, the NFKC measurement and the week's ticket list. Adversarial, with the earlier package's live-router measurements in hand; no code.
- **ChatGPT** — 15 fixtures. Accept-with-change on 1–5 and 7; reject on 6 (a substantial unscreened span should escalate). Packet only. Its attack on the second card decided Decision 5.
- **DeepSeek** — 14 fixtures. Accept-with-change throughout, including 5 (keep a variant, never softer wording). Packet only.
- **Qwen** — 15 fixtures. Accept-with-change throughout; strongest on the minor cap's record and on third-person recovery. Packet only; its fixtures arrived blank in one export and were re-sent.
- **Vibe (Mistral)** — 14 fixtures. Reject on 1 (the shared-account hole, later closed); accept on 5 on a misreading of when the card fires. Packet only; truncated export.

Agreement between reviewers is not treated as evidence. Where they split,
the triage record names the measurement that decided it; where a reviewer
lost, the fixture stays.

## What happened to the fixtures

Before round 2: 9 of 103 passed, all Grok's, most because they asserted
fields the tree already had. After round 2: 80 pass as the reviewers wrote
them; 12 are contract adjustments (the reviewer's expectation was written
against a contract that has since moved — a Spanish pack that now exists,
"ineligible" where "not seated" was meant, a stricter verdict — and the
original is kept beside the adjusted one); 10 are disputed and run as strict
expected failures with the decision's reasons attached; 1 is a known gap.
Nothing was deleted.

## Sanitization

The repository's rules apply: no personal names or anecdotes from the
operator's life, no location, no legal or medical material, no email
addresses. The packet was written under those rules and is published as
sent. The four verdict transcripts had their email transport headers
removed and were otherwise not edited. Grok's documents 19–24 needed no
changes. Two ChatGPT fixture ids collided with DeepSeek's prefix and were
renamed (`gpt-`, `ds-`); Vibe's prefix was normalized (`vibe-`); whitespace
artifacts from a PDF export were stripped. Fixture text is byte-identical
otherwise.
