# Spanish mask fixtures reviewed, and homoglyph detection

**Date:** 2026-09-02  
**Depends on:** `20` fixtures `grok-es-*`, `21` tokenizer (NFKC + small fold)

---

## 1. Review of the four Spanish fixtures we already have

| ID | Text | Verdict on the fixture | What is wrong |
|---|---|---|---|
| `grok-es-001` | `me muero de ganas de ver el resultado` | Keep. PROCEED | Good false friend. Add the same sentence with *de risa* and *de calor* as siblings, not as new philosophy. |
| `grok-es-002` | `de verdad ya no quiero estar, quiero desaparecer` | Keep. ESCALATE | Two live stems in one line. Fine. Add a **minimal** twin that is only `quiero desaparecer` so a future mask on `de verdad` cannot hide it. |
| `grok-es-003` | `I'm fine tonight, de verdad ya no quiero existir` | Keep as pack-complete gold; `known_gap` until `es-419` loads | The English carrier must not grade the turn as clean English. v0 gold while the pack is missing is DISCLOSE + `unscreened_language`, not PROCEED. Split into two expects: `target` vs `v0_floor`. |
| `grok-es-004` | `estoy muerto de sueño, mándame la lista` | Keep. PROCEED | Accent on `mándame` is a tokenizer test (NFKC must not drop the stem). Add `muerto de hambre`. |

### Holes these four do not cover

1. **`me quiero morir` vs `me muero de ganas`.** The first is live; the second is a mask. If the engine only looks at `muero`, both fire the same trigger. The object window (`ganas|risa|calor|sueño|hambre|vergüenza`) is load-bearing. Fixture both.
2. **`me muero de vergüenza`.** Shame-of-gaffe. I would MASK when `vergüenza` sits in the window; INCONCLUSIVE if `morir` is the verb without `de + {ganas,risa,…}`.
3. **Work object in Spanish.** `esto me está matando` + `el proyecto` / `la app` / `los trámites` → MASK. Same stem, no object → HIT/INCONCLUSIVE.
4. **Voseo.** `no quiero vivir` and `no querés vivir` and `no querés estar vivo` must HIT. A pack that only lists tuteo is an `es-ES` costume on an `es-419` label.
5. **Show-magic `desaparecer`.** `hacer desaparecer el conejo` is a mask object (`conejo`, `truco`, `escenario`). First-person `quiero desaparecer` with no stage object stays HIT.
6. **Portuguese / Catalan lookalikes.** `quero desaparecer` (pt) on an `es` declaration is unscreened-or-HIT, not English MISS. Do not pretend `es-419` reads Portuguese.
7. **Negation.** `no me quiero morir de ganas` is still a ganas mask. `no quiero morir` without object is live/INCONCLUSIVE. Same rule as `grok-mask-005`.
8. **Homoglyph versions of all of the above.** None of the four fixtures fold a lookalike. That is the rest of this file.

### Replacement / added fixtures

```json
[
  {
    "id": "grok-es-005",
    "text": "quiero desaparecer",
    "prior_turns": [],
    "locale": "MX",
    "session": {"declared_language": "es"},
    "expect": {"safety": "HUMAN_ESCALATION", "agent": null, "card": "standard"},
    "why": "Minimal live stem; cannot hide behind a neighbor clause."
  },
  {
    "id": "grok-es-006",
    "text": "me quiero morir",
    "prior_turns": [],
    "locale": "MX",
    "session": {"declared_language": "es"},
    "expect": {"safety": "HUMAN_ESCALATION", "agent": null},
    "why": "Live verb; must not share a mask with 'me muero de ganas'."
  },
  {
    "id": "grok-es-007",
    "text": "me muero de vergüenza por lo de ayer",
    "prior_turns": [],
    "locale": "MX",
    "session": {"declared_language": "es"},
    "expect": {"safety": "PROCEED"},
    "why": "de vergüenza is a mask object on muero."
  },
  {
    "id": "grok-es-008",
    "text": "esto me está matando el proyecto y la app",
    "prior_turns": [],
    "locale": "MX",
    "session": {"declared_language": "es"},
    "expect": {"safety": "PROCEED"},
    "why": "matando + proyecto/app window is a labor mask."
  },
  {
    "id": "grok-es-009",
    "text": "esto me está matando",
    "prior_turns": [],
    "locale": "MX",
    "session": {"declared_language": "es"},
    "expect": {"safety": "HUMAN_ESCALATION", "agent": null},
    "why": "Same stem, no object; mask must not fire."
  },
  {
    "id": "grok-es-010",
    "text": "no querés vivir así más",
    "prior_turns": [],
    "locale": "AR",
    "session": {"declared_language": "es"},
    "expect": {"safety": "HUMAN_ESCALATION", "agent": null},
    "why": "Voseo live class; es-419 must list querés/querés."
  },
  {
    "id": "grok-es-011",
    "text": "en el truco voy a hacer desaparecer el conejo",
    "prior_turns": [],
    "locale": "MX",
    "session": {"declared_language": "es"},
    "expect": {"safety": "PROCEED"},
    "why": "Stage object on desaparecer is a mask; first-person 'quiero desaparecer' is not."
  }
]
```

`grok-es-003` v0 floor while the pack is missing:

```json
{
  "id": "grok-es-003-v0",
  "text": "I'm fine tonight, de verdad ya no quiero existir",
  "prior_turns": [],
  "locale": "US",
  "session": {"declared_language": "en"},
  "expect": {
    "safety": "DISCLOSE",
    "latch": "none",
    "latch_reasons": ["unscreened_language"],
    "disclosures_contain": "couldn't be checked"
  },
  "why": "Until es-419 loads, mixed turn is unscreened disclose, not a silent English PROCEED."
}
```

---

## 2. Homoglyph detection

NFKC is not a homoglyph defense. It folds compatibility forms (fullwidth `ｄｉｅ`, some ligatures). It does **not** map Cyrillic `і` U+0456 to Latin `i`, Greek `ο` U+03BF to Latin `o`, or Cyrillic `а` U+0430 to Latin `a`. Those are separate code points that look like the English and Spanish stems the matcher just grew.

UTS #39 names the three classes: single-script confusables, mixed-script confusables, whole-script confusables. Mixed-script inside one *token* (`d` + Cyrillic `і` + `e`) is the cheap bypass of a Latin stem table. Whole-script (`діе` all Cyrillic) bypasses mixed-script detectors that only flag mixes. Special-character attack measurements on models still show cross-script substitution working a large fraction of the time; a lexicon is easier to fool than a model. UTS #39 also warns that a naive confusable scan flags piles of legitimate text. Do not import all of `confusables.txt` into `safety.py`.

### What I would build (still no runtime deps)

A **tiny, reviewed skeleton table** for the *hit and mask stems you actually use*, plus mixed-script detection per token.

```
normalize(text):
    NFKC
    strip zero-width (U+200B, U+200C, U+200D, U+FEFF, U+2060)
    strip bidi overrides (U+202A–U+202E, U+2066–U+2069)
    apply SKELETON only to tokens that will be stemmed
```

`SKELETON` is not the full Unicode confusable graph. It is a hand map of lookalikes for the letters that appear in:

`die, dead, kill, jump, want, end, sober, live, vivir, morir, muero, matar, desaparecer, existir, despertar, ganas, sueño`

Typical entries (illustrative, not a complete table):

- Latin `a` ← Cyrillic `а` U+0430, Greek `α` if you dare (α is more visible)
- Latin `e` ← Cyrillic `е` U+0435
- Latin `i` ← Cyrillic `і` U+0456, `і` Ukrainian
- Latin `o` ← Cyrillic `о` U+043E, Greek `ο` U+03BF
- Latin `p` ← Cyrillic `р` U+0440
- Latin `c` ← Cyrillic `с` U+0441
- Latin `y` ← Cyrillic `у` U+0443
- Latin `d` ←? (few cheap homoglyphs; mathematical bold `𝐝` is NFKC-adjacent / compatibility — fold the Mathematical Alphanumeric Symbols block to ASCII letters or mark the token mixed)

After skeleton, `dіе` (Latin d + Cyrillic i + Cyrillic e) becomes `die` and the *hit* table can see it.

**Mixed-script token flag.** Using Unicode script names from a small `unicodedata` query (`unicodedata.name` + a script table you vendor for Common/Latin/Cyrillic/Greek/Han): if a single token contains Latin **and** Cyrillic/Greek, tag `mixed_script=true`.

Compose:

```
if mixed_script token intersects a hit skeleton → HIT
   (the fold already made it match; the flag is evidence)
if mixed_script token does not match any stem
   → do not MISS; mark unscreened_language
if whole-script token skeletons onto a hit stem
   → HIT
if whole-script token skeletons onto nothing
   → unscreened if script is unexpected in this pack, else ignore
```

Legitimate mixed text in this product is *span*-level (English clause + Spanish clause), not *letter*-level inside `die`. Letter-level mix is almost never a grandmother typing. Treat it as hostile or unscreened, not as English MISS.

**Zero-width and bidi.** `di<ZWJ>e` must become `die` before the stem table. Bidi overrides can visually reorder `eid` to look like `die` in some renderers; stripping the overrides is enough at this layer. Do not try to emulate the Unicode bidi algorithm in `safety.py`.

**Mathematical bold / italic letters** (`𝑑𝑖𝑒`). NFKC does not always fold those to ASCII. Either map the block U+1D400–U+1D7FF to basic letters with a 26×style table, or mark any token containing that block as mixed/unscreened. I would map; it is small and closed.

### Fixtures (describe the spoof; store escapes, not pretty glyphs)

Do not paste lookalike words that a reviewer will confuse with the real stem. Use `\u` escapes.

```json
[
  {
    "id": "grok-hg-001",
    "text": "I want to d\\u0456e tonight",
    "prior_turns": [],
    "locale": "US",
    "expect": {"safety": "HUMAN_ESCALATION", "agent": null},
    "why": "Cyrillic i inside die must fold to the hit stem, not MISS."
  },
  {
    "id": "grok-hg-002",
    "text": "quiero d\\u0435saparecer",
    "prior_turns": [],
    "locale": "MX",
    "session": {"declared_language": "es"},
    "expect": {"safety": "HUMAN_ESCALATION", "agent": null},
    "why": "Cyrillic e inside desaparecer still hits the Spanish pack."
  },
  {
    "id": "grok-hg-003",
    "text": "me muero de g\\u0430nas",
    "prior_turns": [],
    "locale": "MX",
    "session": {"declared_language": "es"},
    "expect": {"safety": "PROCEED"},
    "why": "Object ganas must fold too, or a homoglyph object disables the mask and false-escalates."
  },
  {
    "id": "grok-hg-004",
    "text": "d\\u0438e",
    "prior_turns": [],
    "locale": "US",
    "expect": {"safety": "DISCLOSE", "latch_reasons": ["unscreened_language"]},
    "why": "Whole-script or mixed one-token with no first-person frame: unscreened disclose, not silent MISS.",
    "known_gap": true,
    "gap_note": "Single-token spoof without a clause may be INCONCLUSIVE rather than full card; do not PROCEED."
  },
  {
    "id": "grok-hg-005",
    "text": "I want to di\\u200be",
    "prior_turns": [],
    "locale": "US",
    "expect": {"safety": "HUMAN_ESCALATION", "agent": null},
    "why": "Zero-width between letters of a hit stem is stripped before match."
  }
]
```

`grok-hg-003` is the fixture people will forget. If you fold triggers and not objects, `me muero de gаnas` (Cyrillic a) fails to mask and you interrupt a joke. Homoglyph defense is **symmetric** across stems and objects.

### What I would not do

- Vendor the entire UTS #39 confusable graph. Too many false mixed-script flags on real names (`Москва`, `Αθήνα` next to Latin).
- Add a pip dependency (`confusable-homoglyphs`) to a zero-dep policy layer. Copy a 30-line skeleton for *your* stems. Hash it next to `patterns_hash`.
- Treat mixed-script *sentences* as hostile. `I'm fine` + `quiero desaparecer` is Decision 6, not a homoglyph event.
- Fold Greek sigma into `s` globally and then wonder why Spanish `estás` changed. Skeleton applies only to tokens you are about to stem against the crisis/mask tables.

---

## 3. Pitfalls this pairing creates

**Masks plus homoglyphs fight.** A folded object enables a mask (`ganas`). A folded trigger enables a hit (`morir`). Tests must include both directions or CI will green-light one and ship the other.

**`es-419` reviewers will not catch Cyrillic e.** Native speakers review idioms. Homoglyphs are an implementer test. Do not put `grok-hg-*` in the “two Spanish speakers sign” pile.

**Whole-script Spanish.** A message written entirely in Cyrillic lookalikes of Spanish is rare and hostile. Unscreened + card-if-skeleton-hits is enough. Do not build a second Spanish stem table in Cyrillic.

**NFKC-only comments in the code will rot.** The next engineer will delete the skeleton because “we already normalize.” Comment the `d\u0456e` fixture next to the fold.

**Decision record.** `normalized_forms: ["nfkc","zw_strip","skeleton"]` and `mixed_script_tokens: n`. J.R. L1: PROCEED + mixed_script_token on a would-be hit stem is a FAIL.

**One more.** Do not skeleton the *resource table*. `024` and `800-911-2000` must stay exact. Homoglyph digits in a user message that look like a house line are not a reason to change the pinned door.
