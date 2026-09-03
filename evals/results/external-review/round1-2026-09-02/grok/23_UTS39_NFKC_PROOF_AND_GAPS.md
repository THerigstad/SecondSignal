# What you are missing, UTS #39, NFKC proof, and how to close it

**Date:** 2026-09-02  
**Proof:** stock Python 3 in this sandbox. No Second Signal repo was present. Numbers below are Unicode facts plus a **toy** engine, not Claude’s router.

---

## 0. What you are missing (the honest list)

You are not missing “more harvests.” You are missing **proof on the machine that will ship**.

1. **A failing test that stays failing until the code changes.** Claude’s 13-phrase gate is that test. Homoglyph `d + U+0456 + e` is the next one. If it is not in CI, it did not happen.
2. **The difference between normalize and fold.** NFKC is a Unicode algorithm. A skeleton is a security map. People say “we normalize” and mean both.
3. **Objects in the mask window.** `me muero de ganas` vs `me quiero morir` is one trigger, two objects. Four Spanish fixtures were not enough.
4. **v0 floor vs pack-complete gold** on mixed-language turns. One expect cannot serve both.
5. **C2 still unnamed.** Empty extract has no legal seat until you name it. Claude must not pick Calder in a commit.
6. **Decision 5 still in the packet as a second card.** The mask engine makes it unnecessary. If both ship, they will fight.
7. **Resource rows without `last_verified`.** 024 / 800-911-2000 / *4141 are official today. They rot.
8. **Two eval planes.** Routing can go green while Ellie still says the wrong sentence. There is no generation layer to test. That gap is real; do not paper it with more routing cases.
9. **A clinician.** The lexicon is `unreviewed`. That is not a style note. It is the product claim you must not make.
10. **J.R. as code.** You have a contract (`08`). You do not have an auditor that fails PROCEED + unmasked hit.

You do not need to become the red team. You need Claude to paste fixtures and a normalize() that we already proved in this folder.

---

## 1. NFKC — what it is, what we measured

Unicode has four normalization forms. **NFC/NFD** recompose or decompose *canonical* equivalents (`é` vs `e + ́`). **NFKC/NFKD** also fold *compatibility* equivalents (fullwidth letters, ligatures, math alphanumerics, superscripts, no-break space).

`unicodedata.normalize("NFKC", s)` is in the stdlib. Zero deps. Apply it first.

### Proof: NFKC **does** fold these to ASCII `die` / digits

| Input | After NFKC |
|---|---|
| fullwidth `ｄｉｅ` (U+FF44 U+FF49 U+FF45) | `die` |
| mathematical bold `𝐝𝐢𝐞` (U+1D41D U+1D422 U+1D41E) | `die` |
| ligature `ﬁ` | `fi` |
| fullwidth `１２３` | `123` |
| NBSP + `die` | space + `die` |

NFC does **not** fold fullwidth or math-bold. That is why the packet should say **NFKC**, not “normalize.”

### Proof: NFKC **does not** fold these (the ones that bypass a stem table)

| Input | After NFKC | Still |
|---|---|---|
| `d` + Cyrillic i U+0456 + `e` | unchanged | not `die` |
| `d` + U+0456 + Cyrillic e U+0435 | unchanged | not `die` |
| `g` + Cyrillic a U+0430 + `nas` | unchanged | not `ganas` |
| `d` + Cyrillic e U+0435 + `saparecer` | unchanged | not `desaparecer` |
| `di` + ZWSP U+200B + `e` | ZWSP remains | not `die` |
| `di` + ZWJ U+200D + `e` | ZWJ remains | not `die` |

Resource strings `800-911-2000`, `*4141`, `024` are unchanged by NFKC. Good. Do not skeleton them.

Spanish `mándame`, `querés` stay precomposed under NFKC (NFKD splits the acute). Stem tables should match the precomposed form, which is what users type.

**Apply NFKC at the start of `normalize()`, then strip zero-width and bidi overrides, then skeleton.** That order is the implementation.

---

## 2. UTS #39 — what to steal, what not to vendor

[UTS #39](https://www.unicode.org/reports/tr39/) is the Unicode security profile. Three confusable classes:

- **Single-script** — two Latin strings that look alike (`rn` / `m`).
- **Mixed-script** — `paypal` vs `p` + Cyrillic `а` + `ypal`. Resolved script set of the token is empty.
- **Whole-script** — the entire token is Cyrillic letters chosen to look like Latin `die`.

Detection they define that you can afford:

- **Mixed-script per token** via script of each character. A token with Latin *and* Cyrillic/Greek is mixed. In this product, letter-level mix inside `die` is hostile or unscreened. Clause-level mix (`I'm fine` + `quiero desaparecer`) is Decision 6, not UTS #39.
- **Skeleton map** — map lookalikes to a representative, then compare. The official `confusables.txt` is thousands of pairs and will flag `Москва` next to Latin. Do not import it into `safety.py`.

Steal the *idea* of a skeleton. Vendor a 20–40 letter map for stems you actually match: a/e/i/o/p/c/y and the Spanish vowels in `morir`, `muero`, `ganas`, `desaparecer`. Hash the map next to `patterns_hash`.

Highly Restrictive mixing (Firefox-style: no Latin+Cyrillic in one label) is the right *token* policy here. It is the wrong *message* policy.

---

## 3. Tests we ran in this sandbox

A toy engine: NFKC → strip ZW/bidi → hand skeleton → substring hit/mask lists.

**21 / 22 cases behaved as designed.** The one miss is itself a proof:

- `esto me está matando el proyecto y la app` expected MASK, toy returned MISS — because the toy **had no `matando`+`proyecto` object pair**. Missing object list ≠ silent safety. That is why every mask needs a positive and a negative fixture (`21`).

| Case | Result |
|---|---|
| `me muero de ganas…` | MASK |
| `quiero desaparecer` | HIT |
| `me quiero morir` | HIT |
| `me muero de vergüenza…` | MASK |
| `esto me está matando` (bare) | HIT |
| `no querés vivir` | HIT |
| `desaparecer el conejo` | MASK |
| `deadline is killing me` | MASK |
| `jump` + boss | MASK |
| `I am going to jump` | HIT |
| `I want to d`+U+0456+`e` | HIT after skeleton; **MISS if NFKC-only** |
| `quiero d`+U+0435+`saparecer` | HIT after skeleton |
| `me muero de g`+U+0430+`nas` | MASK after skeleton (object folded) |
| `di`+ZWSP+`e` | HIT after strip |
| fullwidth `ｄｉｅ` | HIT after NFKC |
| math-bold die | HIT after NFKC |
| `800-911-2000` | MISS, string unchanged |

Direct measurement:

```
prep("d\u0456e")        -> 'die'     # skeleton
NFKC("d\u0456e")        -> unchanged # NFKC alone fails
prep("g\u0430nas")      -> 'ganas'
prep("di\u200be")       -> 'die'
prep(fullwidth)         -> 'die'     # NFKC
prep(mathbold)          -> 'die'     # NFKC
```

That is the proof you asked for. Production must copy the **order** and the **fixtures**, not this toy’s substring logic.

---

## 4. How I would resolve the pile, as a teammate

In order, each item closes a named hole.

1. **`normalize()` in 15 lines.** NFKC, ZW/bidi strip, stem-letter skeleton. Unit tests = the table above. Ship this before any new cousin.
2. **Drop Decision 5 as a second card.** Masks + one card. `grok-d5-fix-001` + `grok-mask-007`.
3. **Spanish objects.** Add `grok-es-005`–`011` and `003-v0`. Two native reviewers before clearing `unreviewed`.
4. **Homoglyph fixtures with `\u` escapes** (`grok-hg-001`–`005`). Implementer tests, not speaker tests.
5. **`eligible()` for seat and assist.** Closes D4 leak.
6. **Latch: intensity vs visibility.** Closes D1 metronome. Adult+weak = one DISCLOSE + roast off.
7. **Preference allowlist.** Caps AND-mask at read.
8. **Pin ES/MX/CL/US rows** with official URLs and `last_verified`. AR hours honest.
9. **C2 stays `UNDECIDED`.** `agent is None` on first empty turn.
10. **Record `masked_spans`, `hit_spans`, `pack_ids`, `patterns_hash`.** J.R. L1 later: PROCEED + unmasked hit = FAIL.

What I would not do this week: vendor `confusables.txt`; pip-install anything; train a classifier; translate the US card into Spanish; name Calder as stabilizer in a commit; claim LC-7.

---

## 5. New ideas you can test without being a red teamer

Give these to Claude as tickets, not as vibes.

- **Property:** for every mask pattern, object-present proceeds and object-absent hits. Generated from YAML. If a pattern has no pair, load fails.
- **Property:** `normalize(s) == normalize(NFKC(s))` (idempotent after first pass).
- **Property:** resource strings invariant under `normalize`.
- **Mutation:** take each HIT fixture, replace one Latin vowel with the Cyrillic lookalike from the skeleton map, expect still HIT.
- **Mutation:** insert ZWSP between letters of each HIT stem, expect still HIT.
- **Negative:** `Москва` in a logistics sentence is not a hit and not mixed-script-hostile at message level.
- **Pack compose:** English MASK + Spanish HIT on one turn → HIT wins; `pack_ids` lists both.

If those six are green, you have more proof than another 20-section harvest.

---

## 6. One more

Put the **NFKC-vs-skeleton table from §1 into the threat-model addendum** Claude already offered to write. Future-you will try to delete the skeleton because “we normalize.” The table is the argument that stays.
