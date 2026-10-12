# ADR-0018: Normalize before every lexicon; masks are pre-filters with objects; languages are packs, and declaring one never exempts text

- **Status:** Accepted — built
- **Date:** 2026-09-03
- **Evidence:** Live-router measurement 2026-09-02 (two one-character crisis bypasses); Grok round-1 documents 19–24 (mask engine, Spanish pack, homoglyphs, NFKC proof) under `evals/results/external-review/round1-2026-09-02/grok/`; round-1 Decision 5 (Grok's position adopted) and Decision 6 (consensus with one split); `evals/vectors/unicode_normalize_vectors.json`; `tests/test_normalize.py`, `tests/test_lexicon.py`, `tests/test_house_lines.py`

## Context

Measured on the live router before round 2: "I want to dіe tonight" with a
Cyrillic і (U+0456) and "I want to di​e" with a zero-width space inside the
stem both walked through the crisis gate as `PROCEED`, crisis read `MISS`.
One character each. The lexicons matched on raw text.

Three more findings shaped the record. Ordinary English reuses death
vocabulary constantly ("this deadline is killing me", "I died in that boss
fight"), and the first idiom list was a flat set of phrases that could only
grow into a silencer. A frustration frame around a live stem ("if this app
crashes one more time I'm going to jump off the balcony") reached the card,
and the proposed fix — a second, softer card — was rejected by the reviewer
who attacked it hardest, because "if it's only the fury, say so" invites an
at-risk person to dismiss the card and makes message text a key off the
crisis path. And the language rule as first written — screen English, flag
the rest — meant that a person who declared Spanish would have been served
by a system whose safety only worked in English.

## Decision

**Normalize, in this order, before every lexicon.** NFKC (fullwidth,
mathematical alphanumerics, circled letters, ligatures, the no-break space);
strip the zero-width and bidirectional controls and the soft hyphen; fold a
small reviewed skeleton of look-alike letters (Cyrillic, Greek, a few Latin
variants) onto the Latin letters that spell the stems — NFKC does not do this
and it is the step the bypasses walked through; casefold, never in a Turkish
locale. Digits and punctuation are never touched, so resource strings such as
`800-911-2000` and `*4141` are invariant by construction and a test pins
that. The skeleton map is hashed and travels on every verdict. A token that
mixes Latin with Cyrillic or Greek letters is counted; if no mask or hit
explains it, it is an unscreened fragment (`DISCLOSE`), never a minor latch.
The map is deliberately not the full confusables table, which flags ordinary
non-Latin text.

**Masks are pre-filters with objects.** A pack carries regex masks (fixed
collocations) and window masks: a stem is blanked only when one of its
listed *objects* sits within the window ("kill" near "process", "sober" near
"look", "die" near "boss"), in the same clause — never across a sentence
break or a sincerity pivot such as "honestly". A mask without objects fails
the load. Every window mask has a positive and a negative fixture, enforced
by a test that compares the shipped list to the fixture list. Every mask
that fires is recorded on the verdict (`masked_spans`) beside every span
that hit (`hit_spans`), with the hash of every table consulted
(`patterns_hash`) and the packs that ran (`pack_ids`), so a reader can see
that the gate saw "killing me" and chose a mask, instead of seeing a silent
`PROCEED`.

**One crisis card.** The frustration markers are recorded as reasons and
never select softer wording. Fury with no live stem proceeds through the
gate — and, since round 2, seats the stabilizer, because an angry caller is
not a regulated one. Fury around a live stem gets the standard card. The card
itself was reworded: it never asks the person to declare the card
unnecessary; its repair line is "If this was read wrong, say so plainly.
Asking is better than guessing." The turn after an escalation is routed and
carries the resource line once more.

**Languages are packs; the English classes stay in code.** A pack is a JSON
file: regex masks, window masks, native hit classes, native inconclusive
patterns, negation and pivot words, and the house lines in that language,
written natively and never machine-translated. The English speech-act classes
stay in `safety.py` because they carry regression pins from the first
external review. The first pack is Spanish (es-419), status `unreviewed`
until native reviewers sign; it carries the idioms a translation would miss
(quiero desaparecer, ya no puedo más, no aguanto, me quiero morir, voseo
forms) and the masks that keep "me muero de ganas" and "este trabajo me está
matando" out of the gate. Resource lines are a table with an official source
and a verification date per row; a row that claims 24/7 without a source
fails the load, and Argentina's line says its hours.

**All installed packs run on every turn.** Declaring a language selects the
house lines and the resource line; it never exempts any text from any
screen. A Spanish clause inside an English message is screened by the
Spanish pack. Text no installed pack can read is `unscreened`: a substantial
span (a clause or more) is an inconclusive read and escalates by the
fail-closed rule with the cannot-check line and the region's resource line
on the card; a fragment or a loanword is `DISCLOSE`. The threshold is pinned
by fixtures. Four reviewers wanted `DISCLOSE` for a substantial span; the
measurement that decided it is in the triage record — "je n'en peux plus"
seated a persona with a footnote on the live router.

## Consequences

The two bypasses are pinned end to end in `tests/test_normalize.py` and
cannot return silently. Idiom is a data table with a two-fixture rule and a
receipt on every verdict, not a list in code. Three reviewer fixtures that
wanted the second card and one that wanted a stem-free fury message
escalated are kept as strict expected failures with the reasons attached.
Four language fixtures written before the Spanish pack existed are contract
adjustments with the original expectation kept. One Spanish exhaustion case
("ya no puedo más con esto") escalates when `DISCLOSE` would be right; it is
a documented gap of the same shape as the French one.

## Relationship to the current implementation

Built in `normalize.py`, `lexicon.py`, `packs/en.json`, `packs/es-419.json`,
`packs/resources.json`, and the corresponding parts of `safety.py`
(`crisis_screen`, `_unscreened`, `house_lines`, the card). Token-level
language identification is not built; the unscreened heuristic is a function
word list for Latin-script languages no pack covers plus a non-Latin script
check. The Spanish pack has not been reviewed by a native speaker and says so
on every verdict it touches.

## Amended in place 10 October 2026, order G1

A proximity mask yields to the gate. Every window mask and every regex mask
whose pack marks `yields_to_gate: true` leaves a matching gate hit, danger
signal, other-person weapon span or pack hit visible. The protected matches
are found on the original normalized copy before any mask runs. A negation
in the preceding three tokens retains the existing exception. A skipped
masking attempt is recorded as a `protected` span with its mask id, offsets,
pack and applicable domain; a mask still needs its object and clause context.

Exact idioms marked false keep their measured exemption. No mask is added or
removed, and no class, card, inconclusive pattern or exclusion changes.
Inconclusive reads are not protected because masks help resolve them and
those patterns carry their own exclusions. The field is mandatory and
boolean on every regex entry. A missing or non-boolean field fails loading,
with duplicate ids checked first.

Under the operator's follow-up ruling, `protect=None` retains landing-8
behavior completely; a tuple, including an empty tuple, enables caller and
pack-hit protection. The gate supplies its hit patterns. Session monitors
and extraction omit the parameter and keep their original bytes.

The stored measurement is `evals/fuzz/measurements/splice_2026-10-10.json`:
181 eligible single-message cards before, 182 after the known-gap closure.
Unspliced misses are counted separately, and cases with prior turns are not
single-message cases. Before/after flip counts are: suffix ` on my run` 71 → 11; suffix ` after my run` 16 → 1; suffix ` with the boss` 17 → 2; suffix ` at the plant` 12 → 1; suffix ` at my job` 2 → 2; suffix ` on the raid` 71 → 11; suffix ` at the deadline` 13 → 2; suffix ` in the app` 13 → 2; suffix ` on the server` 22 → 10; suffix ` in the tutorial` 16 → 1; suffix ` on the campaign` 71 → 11; suffix ` on this level` 71 → 11; suffix ` on my phone` 22 → 10; prefix `after my run, ` 12 → 1; prefix `at the plant, ` 9 → 0; prefix `boss fight done, ` 11 → 1; prefix `on my shift, ` 0 → 0.
No remaining flip erases an unnegated protected hit. The remaining exclusions
and maskable inconclusive reads are identified by case id and cause in the
measurement; they remain outside this amendment. The measured raid baseline
is 71 rather than the prototype's 68. `tests/test_g1_masks.py` guards the
splices, explicit opt-in, exact idioms, negation, pack hits and span receipts.
The decision remains Accepted and the implementation remains built.
