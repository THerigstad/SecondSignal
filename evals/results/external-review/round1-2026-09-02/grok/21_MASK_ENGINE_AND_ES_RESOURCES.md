# Mask engine (implementation) and Spanish crisis resources

**Date:** 2026-09-02  
**Constraint:** policy layer is still pure Python, no runtime deps.  
**Depends on:** `20` (classes and fixtures), `19` (Decision 5 reject).

---

## Part I — Mask engine, in enough detail to build

### 1. What it is

A **compiled, hashed pattern table** that runs *before* the crisis matcher and the addiction seat-claimer. It marks token spans `SAFE_IDIOM`. The matcher may not fire on a trigger whose span is covered by a mask that also found its required object.

It is not an LLM. It is not a classifier. It is not allowed to delete a HIT that has no mask.

### 2. Data, not code

Two YAML files, loaded once, hashed into the decision record (`patterns_hash`).

```yaml
# masks.yaml  (concept)
version: 1
pack: en
window: 4          # tokens either side of the trigger
triggers:
  - id: labor_kill
    stems: [kill, killing, killed]
    objects: [deadline, app, queue, battery, build, inbox, ticket]
    person: any
  - id: labor_die
    stems: [die, dying, dead]
    objects: [deadline, app, battery, plant]
    person: any
  - id: laugh_die
    stems: [died, dying]
    objects: [laughing, laughter]
    person: any
  - id: game_jump
    stems: [jump, wipe, die, kill]
    objects: [boss, raid, run, mob, campaign, tutorial]
    person: any
  - id: ops_kill
    stems: [kill]
    objects: [process, job, pod, container, thread]
    person: any
  - id: sober_look
    stems: [sober]
    objects: [look, view, assessment, read]
    domain: addiction_not_claim
  - id: using_tool
    stems: [using]
    objects: [tool, app, library, template]
    domain: addiction_not_claim
```

Crisis hits live in a sibling file (`hits.yaml`) with the same stem shape plus `person: first` where it matters. Masks and hits share a tokenizer so “window” means the same thing.

Spanish pack is the same schema, `pack: es-419`, different stems/objects (`ganas`, `risa`, `sueño`, `hambre`, `vergüenza`, `proyecto`, `trámites`).

### 3. Tokenizer (the whole game)

Pure Python.

1. `unicodedata.normalize("NFKC", text)`
2. Homoglyph fold: map fullwidth digits and common lookalikes used in “1７” / “ｗant” to ASCII. Small table, reviewed.
3. Lowercase (`casefold`).
4. Split on whitespace and punctuation, **keep** apostrophes inside tokens (`don't`, `i'm`).
5. Emit `(token, start_char, end_char)`.

Do not stem with NLTK. Use an explicit **stem table** per pack: `want/wants/wanted/wanna → WANT`. If a surface form is missing, it does not match. That is how “wants to die” stopped being a miss last week — it belongs in the *hit* stem table, not the mask table.

### 4. Match algorithm

```
tokens = tokenize(message)
masks, hits = [], []

for pattern in pack.masks:
    for i, tok in enumerate(tokens):
        if stem(tok) not in pattern.stems:
            continue
        window = tokens[max(0,i-W): i+W+1]
        if pattern.objects and not any(stem(t) in pattern.objects for t in window):
            continue
        if pattern.person == "first" and not first_person_in(window):
            continue
        masks.append(Span(i, i, pattern.id, char_range))

for pattern in pack.hits:
    ... same ...
    # skip if this trigger index is covered by any mask span
    if any(m.covers(i) for m in masks):
        continue
    hits.append(...)

if hits:           HUMAN_ESCALATION
elif ambiguous:    INCONCLUSIVE → same card
else:              MISS
```

**Coverage rule.** A mask covers a hit only if the *trigger token index* of the hit sits inside the mask span. “this deadline is killing me and I will not be here in 90 days” — `killing` is masked; `not be here` is not. Two spans, one HIT.

**Ambiguous.** First-person die-stem with negation and no object (`I don't want to die`) is not a mask and not a clean MISS. Route to INCONCLUSIVE / DISCLOSE (`grok-mask-005`). Do not invent a clever negation parser this month. A 4-token “n’t / not / never / no” window that *only* downgrades HIT → INCONCLUSIVE is enough. It must not downgrade HIT → MISS.

**Addiction seat-claim** uses the same engine, different `domain` flag. Masked `sober look` cannot claim `addiction_recovery`. Unmasked first-person `relapsed` can.

### 5. What the decision record must carry

```
patterns_hash: sha256
masked_spans: [{text, pattern_id, start, end}]
hit_spans:    [{text, pattern_id, start, end}]
pack_ids:     ["en"] or ["en","es-419"]
```

This is `would_have_seated` for the gate. A later harness can fail a turn that PROCEEDed while an unmasked hit_span exists, or that ESCALATEd while every hit_span is covered by a mask.

### 6. Load-time contracts

- File missing → process does not start (same energy as Decision 4’s stabilizer floor).
- Duplicate `id` → load fail.
- Empty `stems` → load fail.
- Tests: every mask pattern has a **positive** fixture (object present → PROCEED) and a **negative** fixture (object absent → HIT or seat-claim). If someone adds a mask without both, CI fails.
- Adding a mask never lowers a pinned HIT fixture. Property test over the 25 + `19` + `20`.

### 7. Performance and isolation

Messages are short. Nested loops over ~50 patterns × ~40 tokens are fine. Compile stem sets as `frozenset` at load. No regex unless you already have one for the old 13; if you keep regex, they run *after* masks and may not match inside a masked char range.

Do not call this from generation. Do not let a sibling see `masked_spans` in its prompt — that is how you teach the model to write around the list.

### 8. Implementation pitfalls (the ones that will actually ship)

1. **Mask-as-silencer.** Product will want a mask for every angry user. Require the ±4 object. No object, no mask. `grok-mask-007` is the pin.
2. **Window too wide.** W=8 will mask “kill” in a message that also names an app. Stay at 4 until fixtures say otherwise.
3. **First-person detector that thinks “my deadline is killing me” is first-person ideation.** Person for *masks* is `any`. Person for *hits* is first-person *agent of the verb*, not any pronoun in the sentence.
4. **Shared tokenizer drift.** If hits.yaml tokenizes differently from masks.yaml, coverage is a lie.
5. **Pack mix.** Running `es-419` objects against English tokens will mask nothing and look fine. `pack_ids` on the record, and a test that `me muero de ganas` only masks when `es-419` is loaded.
6. **Homoglyph only on digits.** People will write `dіe` with a Cyrillic і. Either fold a small mixed-script table or treat mixed-script tokens as `unscreened_language`, not as English MISS.
7. **Quote handling.** Lyrics in quotes: still INCONCLUSIVE if first-person present sits *outside* the quotes. Inside-only can mask.
8. **Thread safety.** Patterns immutable after load. Reloading mid-session is an incident (`patterns_hash` change).

---

## Part II — Spanish crisis resources, reviewed

These are **official doors**, not a live card. Pin after a human opens the cited page. `last_verified` on the row. Lucid fetches the table; the sibling does not invent digits.

### Spain (declared locale `ES`)

Línea **024**, Ministerio de Sanidad. National, free, confidential, 24/7. For people with suicidal thoughts or risk, and for family. Does not replace in-person care. Imminent danger: **112**. Chat exists alongside voice (Sanidad reported both in the 2025 activity report). Contract for the service has been extended toward 2027; the *number* is a BOE-attributed short code, not a vendor slogan. Card should say 024 and 112, not 988.  

Source: [sanidad.gob.es/linea024](https://www.sanidad.gob.es/linea024/home.htm)

### Mexico (declared locale `MX`)

**Línea de la Vida**, CONASAMA / Secretaría de Salud. **800-911-2000**, free, 24/7, mental health and addictions, including ideation. Official gob.mx page. Emergency still **911**.  

Pitfall: the 800 number *contains* 911. The card must print the full 800-911-2000. Do not shorten it. Do not send MX users to US 988 option 2.

Source: [gob.mx/conasama Línea de la Vida](https://www.gob.mx/conasama/articulos/linea-de-la-vida-800-911-2000)

### Chile (declared locale `CL`)

MINSAL **\*4141** (“No estás solo, no estás sola”). Free, 24/7, from mobiles (later pages also say fixed lines). Psychologists. Deaf users routed via Salud Responde scheduling, not the voice star-code.  

Pitfall: the star prefix. A US or ES phone cannot dial \*4141 and reach Chile. Declared locale CL + a traveler still holding a foreign SIM is a wrong door. Directory fallback if the row says `dialable=mobile-CL`.

Source: [minsal.cl *4141](https://www.minsal.cl/linea-de-atencion-4141-no-estas-solo-no-estas-sola/)

### Argentina (declared locale `AR`)

Centro de Asistencia al Suicida **135** (CABA / GBA) and a long-distance number for the rest of the country. **Hours are not 24/7** on several published descriptions. Emergency **911**.  

Pitfall: claiming 24/7 on 135. If the pinned row cannot honestly say 24/7, the card must not.

### United States, Spanish (declared locale `US`, declared language `es`)

**988**, option 2. That is a US service with Spanish audio, not a Latin American number. Interpreters on the US call path do not make 988 valid in MX/ES/CL/AR.

### Unknown locale

No short code. Directory pointer (Find a Helpline / IASP index) + “local emergency services.” Same rule as English unknown.

### Pack structure I would pin

```yaml
# resources.es.yaml  — operator-owned
packs:
  ES: { voice: "024", emergency: "112", hours: "24/7", last_verified: "2026-09-02", source: "sanidad.gob.es/linea024" }
  MX: { voice: "800-911-2000", emergency: "911", hours: "24/7", last_verified: "2026-09-02", source: "gob.mx/conasama" }
  CL: { voice: "*4141", emergency: "131/133", hours: "24/7", dialable: "CL-mobile", last_verified: "2026-09-02", source: "minsal.cl" }
  AR: { voice: "135", emergency: "911", hours: "limited", last_verified: null }
  US: { voice: "988", option: "2", hours: "24/7" }
  unknown: { directory: true }
```

House lines in the pack are native prose. Resource digits never appear in sibling weights.

### Resource pitfalls

1. **Same-looking numbers, different states.** 911 / 112 / 988 / 024 / 135 / \*4141. The locale field is the whole product.
2. **US-Spanish ≠ MX.** Option 2 is not CONASAMA.
3. **Star codes and 800 prefixes** fail off-network. Card should include the official web page as well as the digits.
4. **Hours.** 24/7 is a claim. AR 135 is the test.
5. **Secondary blogs disagree** (one deck says a Chile number the ministry page does not). Only ministry/CONASAMA/Sanidad URLs go in `source`.
6. **Youth vs adult.** Child-protection short codes (UNICEF lists, línea 102, etc.) are additional doors after a general line, never the only line, and never inferred from Decision 1 soft latch.
7. **WhatsApp-only lines** break a voice-card assumption. If a row is WhatsApp-only, the card must say so.
8. **Stale pin.** A quarterly open of the `source` URL is an ops ticket, not a hope.

---

## Part III — Opinions and further pitfalls

**The mask table will become the new thirteen phrases.** The last crisis list died because someone added strings until the suite went green. The mask list will die the same way if product can add a mask without a negative fixture. Make the two-fixture rule louder than the feature.

**Decision 5 was a wording escape from a missing mask engine.** If you build this engine and keep two cards, you will argue about which card a masked-plus-hit message gets. One card. Masks decide PROCEED vs ESCALATE. Copy can mention work-fury in sentence one of the *same* card.

**`800-911-2000` will be “helpfully” shortened to 911** by a sibling, a designer, or a test author. Pin the full string. Add a fixture that fails if the MX card equals `"911"` and nothing else.

**Declared locale plus travel.** Someone declares MX, flies, writes in English on hotel Wi-Fi. You still attach MX doors. That is correct under “never infer.” Put one sentence on the card: these numbers are for the region you chose. Offer “wrong region” as a style-like confirm, not a safety key.

**es-419 is a political fiction that you need anyway.** One pack will under-serve voseo and Peninsular *tío/joder* work-fury. Ship `es-419` plus an `es-ES` overlay for masks only (fury objects), not a second crisis theology.

**Conservative mode and Spanish.** A Spanish homework phrase (`mi tarea`, `mi profe`) is a Decision 1 weak signal *in the Spanish pack*, not a reason to set English conservative mode from script. Split packs all the way down or you re-merge the latch bit you just split.

**J.R. the harness should audit `masked_spans`.** A PASS that ignores an unmasked hit is the same bug as a PASS that ignores a forged ping. When you record the `jr_harness` contract, this is an L1 check.

**Do not put the resource table in the generation prompt.** The model will “update” 024 to 988 because 988 is in its weights. Lucid attaches the line after the sibling speaks, or the sibling receives only a slot `{resource_line}` it cannot edit.

**Over-restriction will come back through masks.** If “jump” is masked whenever “app” appears anywhere in a 40-token message, you have rebuilt Decision 5’s gaming prize in reverse: ideation plus “this app” proceeds. That is why W=4 and `grok-mask-007` exist.

**The operator cannot review every Spanish idiom.** Mark `es-419` `unreviewed` until two native reviewers sign. Ship English masks first. A half-reviewed Spanish HIT list is still better than a translated 13; a half-reviewed Spanish MASK list is how you hide `desaparecer` under `me muero`. Review MASKS with more suspicion than HITS.

**One more.** Log **which pack fired**. `pack_ids: ["en"]` on a mixed turn that PROCEEDed is the bug. `pack_ids: ["en"]` plus `unscreened_language` on the same turn is the honest v0. When both packs fire and disagree (English MASK, Spanish HIT), HIT wins. Write that compose rule down before the first mixed fixture flakes in CI.
