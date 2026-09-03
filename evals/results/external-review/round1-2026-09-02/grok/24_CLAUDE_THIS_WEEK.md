# Claude — this week, before GitHub

You have the repo. Grok does not. This file is the work ticket. Do not reopen the harvest prompt. Do not name a stabilizer. Do not add a runtime dependency.

Operator intent: a public repo that looks like a builder shipped a measured policy layer, not a persona demo. Unicode correctness is table stakes. The product claim is Lucid-first, seat vs hold, known gaps that stay in CI, crisis doors that are not 988-everywhere.

---

## Do not push until

- [ ] `normalize()` exists and the vectors in `fixtures/unicode_normalize_vectors.json` pass
- [ ] The 13-literal crisis instrument is gone
- [ ] Calder-by-`c` fails on main and does not return as an unnamed default
- [ ] The four accidental routing passes assert `reason`, not winner
- [ ] Decision 5 is **not** a second card object
- [ ] C2 (who sits on empty extract) is `UNDECIDED` in an ADR; first empty turn is `agent is None`
- [ ] No operator personal data, no place-name fixtures, no third-party papers
- [ ] README does not claim LC-7 or multilingual crisis care

---

## Ticket 1 — `normalize()` (half day)

File: `src/second_signal/normalize.py` (or wherever text enters the gate).

```
NFKC
→ strip {U+200B,U+200C,U+200D,U+FEFF,U+2060,U+00AD, bidi U+202A–202E, U+2066–2069}
→ skeleton only letters that appear in hit/mask stems (map in normalize.py, hashed)
→ casefold  (default; do not use a Turkish locale)
```

Proof already measured in this package (`23`):

- NFKC folds fullwidth and math-bold `die`
- NFKC does **not** fold `d`+U+0456+`e`, `g`+U+0430+`nas`, ZWSP, soft hyphen
- After skeleton + strip, those become `die` / `ganas`

Do **not** skeleton resource strings. Do **not** pip install `confusable-homoglyphs` or `homoglyphs_fork`. Those libraries pull UTS #39 graphs and will flag real names. Vendor a 30-line map. If you want their *data* later, generate the map offline and commit the map, not the package.

Tests: load `unicode_normalize_vectors.json`. Property: `normalize(normalize(s)) == normalize(s)`. Property: resource strings invariant.

## Ticket 2 — Mask engine + kill the second card (one day)

`21` and `20`. YAML patterns, ±4 object window, HIT wins if trigger index not covered. Record `masked_spans`, `hit_spans`, `patterns_hash`, `pack_ids`.

Every mask pattern: object-present PROCEED fixture + object-absent HIT fixture or load fails.

One crisis card. Frustration markers without a live stem → PROCEED (`grok-d5-fix-001`). Live stem → standard card even if “I swear / one more time” is present (`grok-frust-001`). Next turn is a new screen, not a key.

## Ticket 3 — Spanish pack as `unreviewed` data (half day)

`es-419` HIT/MASK lists from `20`/`22`. Do not translate the English 13. Do not clear `unreviewed`. Resource rows:

| locale | voice | emergency | hours | source |
|---|---|---|---|---|
| ES | 024 | 112 | 24/7 | sanidad.gob.es/linea024 |
| MX | 800-911-2000 | 911 | 24/7 | gob.mx/conasama |
| CL | *4141 | 131/133 | 24/7 | minsal.cl *4141 |
| US + es | 988 option 2 | 911 | 24/7 | SAMHSA |
| AR | 135 | 911 | limited | pin only with honest hours |
| unknown | directory | local emergency | — | Find a Helpline |

Lucid attaches the line. Sibling never sees digits. Fixture: MX card must contain `800-911-2000`, not bare `911`.

v0 mixed EN+ES without pack: DISCLOSE + `unscreened_language` (`grok-es-003-v0`). Pack-complete gold stays a known_gap until reviewers sign.

## Ticket 4 — Router honesty (one day)

- `eligible(agent, holds, floors, caps)` for **seat and assist**. `grok-hold-003` must pass.
- Empty extract: `reason=no_routable_signal`, `agent is None` on first empty turn.
- Class lexicons for B (shop/funnel, not-speaking, make-it-stupid, can’t-feel-my) with fixture strings held out.
- Floor at load. Attacks 5.1 / 5.2 fail the load.
- `would_have_seated` on gated turns.

## Ticket 5 — Latch and prefs (half day)

Soft: visibility can decay; roast-off does not auto-return. Second weak hit → sticky. Declared-adult + weak → one DISCLOSE + roast off. Message text cannot write session keys (`grok-latch-004`).

Prefs: six-key allowlist. Envelope verbs refused. Caps AND-mask at read. Ask-once per key per session.

## Ticket 6 — Docs that make a builder look like a builder

- ADR 0010 crisis floor + INCONCLUSIVE=card + English-only dated + locale resources
- ADR 0011 no-signal policy, C2 UNDECIDED
- ADR 0012 windows = eligibility, load-time stabilizer *existence* (not identity)
- ADR 0013 two eval planes; generation fixtures marked untestable
- Threat-model addendum: paste the NFKC-vs-skeleton table from `23` so nobody deletes the skeleton
- README: Agent = Model + Harness. `jr_harness` named and deferred. Test count. Known-gap count. No LC-7 claim.
- External-review index with quality notes. Sanitize per Claude’s scrub list.

`jr_harness` code is **not** this push. The contract in `08` is the ADR appendix.

---

## Libraries — official opinion

| Library | Use here? |
|---|---|
| `unicodedata` (stdlib) | Yes. NFKC, names, combining. |
| Hand skeleton + mixed-script token flag | Yes. Commit the map. |
| `confusable-homoglyphs` | No runtime. Offline you may dump a subset of confusables for *your stems only* and commit that subset. |
| `homoglyphs` / `homoglyphs_fork` | No. Combination generator is an attacker toy, not a gate. |
| `ftfy` | No. Different problem (mojibake). |
| Full `confusables.txt` in-process | No. Over-flags `Москва`. |

UTS #39 Highly Restrictive is the *token* policy (no Latin+Cyrillic inside one stem). It is not the *message* policy.

---

## What a16z actually sits up for

Not NFKC. Every serious safety repo will have some of that next year.

They sit up if the GitHub shows:

1. A policy layer that decides *before* a model speaks, with a typed decision record (`held`, `assist`, `masked_spans`, `reason`, roster hash).
2. Tests that failed on the old tree and pass on the new, plus cases that still fail and are marked `known_gap` instead of deleted.
3. Seat vs hold — the generation layer is obligated, the roast cousin does not steal grief.
4. “The user should need us less” as an implemented metric path (ADR-0001 firewall already exists — keep it).
5. Honest scope: English screen, Spanish pack unreviewed, 988 not a world number.
6. No cousin demo in the README hero. No “we honor every culture.” No fabricated citations.

If the README leads with nine fictional personalities and a Stream Deck, they will smirk and close the tab. If it leads with the decision record and the before/after table of the 25, they might stay.

Using models to *write the cousins* is expected. Using models as the safety gate, the gold label, and the attacker is the wrong way. This week is the right way: you specify, Claude implements against fixtures, the suite says what is still false.

---

## Suggested commit messages (boring on purpose)

1. `test: add unicode normalize vectors and known-gap runner`
2. `feat: NFKC + zw strip + stem skeleton before lexicons`
3. `feat: crisis class patterns and idiom masks; remove 13-literal list`
4. `feat: eligible() for seat and assist; named no-signal reason`
5. `docs: ADR 0010-0013 and threat-model NFKC table`

Then the 25 + `19` + `20` + unicode vectors, before/after in CHANGELOG. Private until that table exists.

---

## Still not this push

J.R. code, Part II bindings, ElevenLabs, TML, AnE in `signals.py`, crisis-card *prose* from the operator (locale rule *is* this push), C2 identity, clinician sign-off, a16z cold email.

When the table is real, Grok will kick the next hole. Send the pytest output, not a narrative.
