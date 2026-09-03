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
