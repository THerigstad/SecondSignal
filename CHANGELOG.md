# Changelog

All notable changes to SecondSignal are documented here.

## [Unreleased]

### Added — 2026-09-11

- **The presentation block and the plate** (`src/secondsignal/profiles.py`,
  the seven family profiles, `tests/test_presentations.py`; ADR-0026
  amended in place, amendment 1). The operator's ruling of 11 September:
  every persona comes as a woman, a man, or neither; one name in two forms,
  the short form the full form with letters dropped (Nikki / Nik, Willow /
  Will, Ellis / Elli; Cody, Vandal, Seren and Rowan do not shorten); a
  plate always shows both forms, the full form first, each with its label,
  the same word twice when the name does not shorten; the neutral
  presentation goes by either form, the person's choice. Each profile
  carries a `presentation` block (`she`, `he`, `they`, `as_written`),
  `AgentProfile.plate` and `AgentProfile.name_for` return what a surface
  shows, and nothing that routes reads any of it (a test inspects the
  routing modules). The ADR register marks ADR-0026 partly built.

- **The demonstration page** (`demo/index.html`, `demo/build_site.py`,
  `.github/workflows/pages.yml`, `tests/test_demo_site.py`;
  `docs/notes/demo-build-2026-09-11.md`). One static page that runs this
  package in the visitor's browser under Pyodide from one pinned address,
  fetches the package's files from beside itself and verifies each by
  SHA-256 against a manifest the builder script writes from the tree, turns
  its own network off after boot, and shows: a message's decision with the
  library's own trace and record; the seven seat plates with both name
  forms and a presentation setting that never reaches the library; the
  labelled-case suite run by pytest in the browser; the three external
  review sets with every disagreement openable. Built by OpenAI Codex from
  the Primary Design Agent's order to ChatGPT-6 Astra's design in two
  rounds; its acceptance run, and the three defects the builder caught in
  the orders, are in the note.
- **Three ledger entries** (`docs/confessions.md`, version 5): C-23, C-24
  and C-25, the design agent's own, from the demonstration page's orders.

### Fixed — 2026-09-11

- **The demonstration page carries link-preview tags** (its title, the first
  fixed statement, and the house picture from the site itself), so a link
  to it unfurls with the house.
- **The demonstration page boots in a background tab.** Its boot waited
  for the two pictures to finish decoding, which a hidden tab never does;
  found in the operator's browser after the push, fixed the same night
  (a bounded wait, and a paint yield that does not depend on an animation
  frame). `docs/notes/demo-build-2026-09-11.md` records it.

### Changed — 2026-09-11

- **The test count on the front page and the evaluation page:** 1,299
  tests (193 expected failures unchanged), measured in fresh environments
  on Python 3.10, 3.11 and 3.12.
- **The seven family codexes at v1.1.** One generated line in each
  machine-readable block, `presentation`, bound to the profile by the codex
  test; nothing in any character's voice changed (each codex's change log
  says so).

## [0.2.0] — 2026-09-10

The magazine issue: the build of 10 September 2026 and the public flip. The
danger lane every reviewing family put first; the nine-family review round
ingested verbatim; the guards hardened against the round's own mutations;
the family renamed through an alias layer and its ten codexes in the tree;
the records amended in the reviewers' words; the front page rebuilt so that
every claim on it points at a test, a record or a labelled proposal.

### Added — 2026-09-10

- **The danger lane** (`safety.py`, `signals.py`, `lexicon.py`,
  `packs/resources.json`; `tests/test_danger_lane.py`;
  `evals/cases/p0_lane_2026-09-10.json`). Danger from another person without
  a weapon is a fail-closed class: four signal groups (present confinement,
  prior violence, fear for dependents, an explicit threat to life), any two
  in one message, with a fiction, news and game frame exclusion. The weapon
  lane widened to a threat made with the weapon, a weapon within reach of a
  raging or intoxicated person, and the whole household as the actor. The
  danger card carries the verified domestic-violence line for five declared
  locales (verified by a human on 8 September 2026, with the sources and the
  day on record) and a directory line elsewhere; the compound card, when
  self-harm and danger both fire, opens with the sentence that names both
  and lists the self-harm line first (B5), and the order is a field on the
  verdict (`card_order`). The post-separation window shows the same line
  once a session with the abuse hold carried. The abuse-history hold.
- **The house lines of 8 September** as canon (`HOUSE_LINES_EN`,
  `tests/test_house_lines.py`): the five-line card, the after-card line,
  the dependency line, the integrity line, the careful-side lines for an
  inferred and a declared band with the hard tier's visibility rule (once,
  then quiet, again only as a refusal's reason or a correction's answer),
  the style line, the failure line ("This message ran into a problem. Press
  here to try again."), and the post-separation line. The Spanish pack
  carries the three new lines natively and unreviewed.
- **A relative's return to use is a hold, not a seat-claim**
  (ADR-0027, Proposed, built; ADR-0016 amended in place; `tests/test_holds.py`).
  The bare report still seats the recovery persona as the hold's
  specialist; an ask seats the ask with the recovery hold carried and the
  recovery persona offered. The conflict lexicon reads a conversation to be
  planned as conflict work.
- **The bounded aftermath and the substantive-turn clock.** Two substantive
  turns after any card carry `no_joke` and the restated resource line; a
  turn is substantive only with new content beyond an acknowledgement list,
  which closes the bug a reviewer reproduced (five turns of "ok ok ok"
  cleared a declared adult's soft latch). A correction of a careful-side
  inference is a latch-history row and clears nothing.
- **The alias layer** (`profiles.py`, `tests/test_aliases.py`). The family
  is Cody (was Calder), Ellis (was Ellie; short form Elli), Seren (was
  Sera), Rowan (was Ravi), and Nikki, Willow and Vandal unchanged, so that
  each name reads naturally for either twin (ADR-0026, Proposed). Every
  earlier name resolves everywhere an id is accepted; every external
  fixture stays byte for byte.
- **The ten codexes in the two-part shape** (`docs/codex/`): the seven
  family codexes from the operator's System Editions, the three security
  codexes in their 10 September editions (Orrin and Aya v1.2, J.R. v3.2),
  one house block pinned by hash to its version
  (`house-block.lock.json`), a machine-readable block on each that a test
  holds equal to the profile, the deny-list lint on every Part B, and the
  cross-codex title check.
- **Review round 2 ingested** (`evals/cases/round2_2026-09-08/`,
  `evals/cases/deferred/round2_*.json`): fifty-four fixtures from ten
  returns, verbatim, each named for its reviewer; thirty-six run on the
  policy plane (30 pass as written, 4 contract-adjusted, 1 disputed, 1
  known gap), eighteen deferred on the orchestration and persistence
  planes. Seven had failed on the tree before the ingest, each on a gap
  they exposed and closed the same night. The twelve narrator-isolation
  fixtures. The twenty P0-lane fixtures.
- **The guards hardened against the round's twenty-six mutations**
  (`tests/test_adr_index.py`, `tests/test_codex_house_block.py`,
  `tests/test_no_security_handoffs.py`, `tests/test_register_mutations.py`).
  Status lines in one grammar parsed on both axes; vocabularies frozen;
  evidence must be a real, unskipped test function; JSON fixtures cited
  too; titles compared; relationships named in prose; docs scanned for
  stale status claims; the README's status block generated from the
  register (`docs/adr/render_status.py`) and no decision word allowed
  outside it; profiles JSON only and walked whole; the request path
  imports nothing from the unwired audit port. Every mutation, and every
  control, is a red regression.
- **Records.** ADR-0026 (twins: two presentations, one routing contract);
  ADR-0027; ADR-0022 and ADR-0023 amended in place with the round's
  findings in the families' words and a revision history each; ADR-0019
  with the gate as the dependency; ADR-0020 with six corrections; ADR-0025
  with its five gate predicates; ADR-0015 with the latch's lifetime stated;
  ADR-0014 in post-ADR-0022 words. The dissent log's round-2 entries
  (R2-1 to R2-6). The model-provenance note, version 2. The
  stall-and-recovery packet filed as a labelled proposal. The confessions
  ledger, version 4, all twenty-two entries approved by the operator.
- **The front page and the assets.** The README rebuilt on the operator's
  canon block, the house as the hero, the doorway mark, two drawn diagrams,
  the roster after round 2, the round-2 numbers, the confessions link, the
  seven-versus-one experiment as a roadmap line. `docs/assets/` with a
  provenance record for every image, checked by `tests/test_assets.py`
  (the recorded hash is the committed file's; a page's alt text is the
  record's). `LICENSE-CONTENT`: the code stays
  MIT; the characters and the pictures are CC BY-NC-ND 4.0. `CITATION.cff`.
  A lint job (ruff, mypy) beside the test matrix in CI. Coverage measured
  and written on the evaluation page from the run.

### Changed — 2026-09-10

- ADR-0025's seat-trade half withdrawn in favour of ADR-0026; the assist
  from the hold stands, unbuilt, behind its gate.
- The Security Division note's stale lines corrected with a dated change
  log entry; the round-1 report page regenerated after its counts drifted;
  the two committed report pages are now asserted equal to the runner's
  output.
- `docs/known-limitations.md` and `docs/roadmap.md` rewritten for the day:
  the three deaths of a latch, the published time as a manifest field with
  no default, the fourth common mode, the correction path as an open item,
  the lines that ask too much, the integrity matrix's unspecified cell, and
  the next build blocks in order.

## [0.1.0] — 2026-09-08

The first tagged release: the policy layer as it stands after the external
review rounds, the two-builder merge, and the decision register. Everything
below this heading and above the initial edition entered the tree between
31 August and 8 September 2026.

### Added — the Security Division records and the decision register, 2026-09-08

Writing, not building. Nothing on the request path changed in this batch;
what changed is what the tree admits about itself.

- **A machine-checked register of architecture decisions**
  (`docs/adr/index.json`, `tests/test_adr_index.py`, `docs/adr/README.md`).
  Every record carries a decision status (Proposed, Accepted, Superseded) and
  a separate implementation status (not-code, none, partial,
  reference-unwired, built). The suite fails on an unregistered record, a
  status line that disagrees with the register, an implementation claim
  with no evidence test or module behind it, a citation from code to a
  record that does not exist, a citation of a Proposed record without the
  marker `(Proposed)` beside it, a stale marker, a one-way relationship, a
  Proposed or unbuilt record the README does not name, or a reserved number
  that is used. Born the day the new statuses landed, because ADR-0014's
  hand-maintained status line had been wrong for a week and nothing could
  notice.
- **Five Security Division records, all Proposed**: ADR-0019 (the five
  objects and their clocks, amended: the gate is object one, the narrators
  sit outside, intake runs after the gate), ADR-0020 (the audit-harness
  predicates, with five corrections listed as open), ADR-0022 (intake and
  provenance: after the gate, before routing, read-only on the bytes,
  fail-closed on the seat when intake fails, a published backend matrix),
  ADR-0023 (the ledger and the interlock: two named things bound by one
  invariant, five rules from the reviewers' attacks, the three events kept
  apart, persistence with a staffing duty, bounded aftermath as presentation
  state) and ADR-0025 (the operator's assist-and-seat-trade intent, filed
  with its target case and its gate). Under the project's standing rule none
  becomes Accepted until a second model family has reviewed the amended
  text. `docs/adr/index.json` reserves 0021 and 0024 for records not yet
  written.
- **The codex files in the two-part shape** (`docs/codex/`): the house block
  (Part A, v1.1), and the J.R. (v3.1), Orrin (v1.1) and Aya (v1.1) Two-Part
  Editions, each with a change log naming the review-round-1 rulings it
  carries, each marked Proposed until review round 2 closes. The Security
  Division document v1.1 (`docs/notes/security-division-2026-09-08.md`)
  carries every correction from that round.
- **A profile guard** (`tests/test_no_security_handoffs.py`): no profile in
  any format may hand a person to `orrin`, `aya` or `jr`, and no profile
  file may carry one of those names.
- **Credit.** The audit-harness reference port (`jr.py`, unwired) follows
  ADR-0014; the harness framing is credited to Charafeddine Mouzouni, The AI
  OS letter #96 (29 August 2026). The README names him inline where the
  framing is used and in an Acknowledgments section.
- Test suite: 1,070 tests — 190 expected failures (176 documented gaps, 14
  recorded dissents), the rest passing. The counts in the README, the
  evaluation page and the badge had been stale since the 7 September push
  (which added the 26 acceptance fixtures and their gaps and dissents); they
  now match the tree. The D3 acceptance fixture's dispute note records the 8
  September ruling; its disposition is unchanged until the code changes.
- README: a paragraph on legibility under "The idea"; a "what is not built,
  by record" section under Status naming every Proposed or unbuilt record;
  the dissent index entry for a relative's relapse moved from Open to
  decided with dissent. `docs/known-limitations.md`: the latch-lifetime
  contradiction, the staffing duty, the single-operator common mode, the
  unmeasured adult false-positive rate, quotation and mention as a chosen
  over-restriction, the voice and embodiment scope lock, and the weapon-free
  danger gap named as the next build block. A dated note in the research
  note's §5.2 pointing at the records that supersede its J.R. row. The
  external-review README says, in the operator's words, that every return is
  kept as it arrived.

### Changed — 2026-09-08

- ADR-0014's status line, stale since the reference port entered the tree on
  2026-09-06, now reads "Accepted; reference port present and deliberately
  unwired", and its relationship section says so. ADR-0015 records that
  ADR-0023 (Proposed) amends its hard-tier visibility clause. `jr.py`'s first
  line marks ADR-0019 and ADR-0020 as Proposed.
- The dissent log's D3 is decided with dissent: a bare report of a relative's
  relapse seats the recovery persona; an ask seats the ask with the recovery
  hold carried and the recovery persona offered. The tree still seats the
  recovery persona on every relative sentence; the code change, ADR-0016's
  amendment and the fixtures are the next build block, and the log says so.
- `docs/roadmap.md` M2 no longer points at a folder that does not exist.

### Removed — 2026-09-08

- `agents/calder/profile.yaml`, a pre-roster artifact from before the JSON
  roster existed. Nothing read it, and its handoff table still sent
  "genuine physical-safety or preparedness emergency" to a security
  character, a handoff the runtime refuses. The JSON roster under
  `src/secondsignal/profiles/` is the roster; the new profile guard fails if
  such a row ever returns.

### Changed — the crisis-gate repairs and the two-builder merge, 2026-09-04 to 2026-09-06

A reviewer given the code returned 26 executable fixtures; 25 failed, twenty
of them real bypasses across seven causes. The seven repairs below were written
as one order, given to two builder systems from different model families
independently, and merged by measurement
(`evals/results/merge-2026-09-06/two-builders-scoreboard.md`). Nothing was
deleted; no reviewer expectation was edited.

- **Clause breaks and desire immunity** (`lexicon.py`): a period, question
  mark, exclamation mark, semicolon, colon, dash or newline ends a clause; a
  comma ends one only when what follows is a first-person present desire. An
  affirmative statement of present desire ("I want to die") is never blanked
  by a game or hobby window mask, in either direction; a negated one still can
  be. "I want to die in this boss fight and respawn" still proceeds.
- **Category stripping** (`normalize.py`): the global strip of invisible and
  directional characters is kept, and a rule for format and combining marks
  between Latin letters is added on top, so the family is handled rather than
  the two characters that were found. Seven directional controls at a word
  boundary are pinned end to end through the live gate; every English crisis
  lemma is tested with nine invisible marks at every interior position; a
  vector file entry must carry the real codepoint, not an escape.
- **Mixed-script crisis forms** (`safety.py`): a look-alike token that folds
  into a crisis stem, or onto one with a single extra character at an edge, is
  a crisis candidate before the language lane may claim it. A look-alike in an
  ordinary word ("hοmework") still discloses.
- **Spoken register** (`normalize.py`, `packs/en.json`): "wanna", "gonna",
  "lemme" expand as whole words; "please let me die" and "end it all" are hit
  surfaces.
- **Interim weapon lane** (`safety.py`): a present weapon in another person's
  hands fails closed with no resource number; the full lane and its resource
  row wait on a human.
- **Three defects found by document review, reproduced and fixed**:
  `clear_latch(which=...)` for an absent or already-cleared reason is a no-op
  instead of falling through to clear-all (V-03); the signal extractor keeps
  line breaks until after masks run, so a message no longer routes to a
  different persona depending on a newline (V-04); `explain()` prints
  obligations whether or not anything is held (P-11).
- **Preference refusal vocabulary** (`preferences.py`): a bare "the card" or
  "that line" next to a request marker is recognized, so "never show me the
  card" is refused like "never show me the crisis card".
- **Recorded, not repaired**: two Spanish forms ("me quiero matar",
  "desaparecerme") are pack rows for a native reviewer, in
  `evals/cases/known_gaps.json`; a normalizer rule that split enclitics was
  tried and reverted because it silently broke four joined forms the pack
  already matched, and those four are now pinned. Both builders' innocent
  false-positive sets are recorded as gaps; no crisis entry was weakened.

### Added

- **Case manifest** (`evals/case-manifest.json`, `tests/test_case_manifest.py`,
  `evals/refresh_case_manifest.py`): every eval case inventoried with source,
  plane and disposition; an expected failure may fail only on the fields it was
  approved for, so it cannot absorb an unrelated regression; an unknown
  expectation key is a hard failure. Writing it found one round-1 fixture
  whose key had a space in it and had asserted nothing since it was accepted.
- **Fixture runner** (`evals/run_fixtures.py`, `tests/test_fixture_runner.py`):
  reproduces the reviewer-fixture results page from the case files.
- **Two-builders scoreboard** (`evals/results/merge-2026-09-06/`): four trees,
  ten held-out sets, one runner, the method.
- **Packaging**: the seven profiles ship inside the package
  (`src/secondsignal/profiles/`), pinned by a test that installs the built wheel
  into a clean environment and loads the roster from an unrelated directory
  (skips where the host cannot build a wheel without isolation).
- Deterministic `RoutingDecision.to_dict()` records and compact `--json` CLI output.
- An unwired reference port of the audit harness thin slice (`jr.py`,
  `tests/test_jr_v0.py`, `evals/cases/deferred/jr_v0_cases.json`), reviewed
  blind-first by a second model family and kept out of the pipeline until the
  release door exists.
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, and issue templates
  for a bypass report, a fixture proposal and a dissent.
- Documentation corrections (P-07): the README, architecture and
  known-limitations pages claim only what the code does — the policy layer
  does see raw text, by design; the library shows a card and contacts nobody;
  the tie-break rule is described as implemented; no hash is claimed on the
  record that the code does not put there.
- Test suite: 1,004 tests — 180 expected failures (170 documented gaps, 10
  recorded dissents), the rest passing on Python 3.10, 3.11 and 3.12.

### Changed — round 2, after the round-1 design review, 2026-09-03

Seven design decisions were reviewed on paper by five external model reviewers
before they were built; 103 executable fixtures came back and 9 passed against
the tree as it stood. The changes below are the build. After it: 80 pass as
written, 12 are contract adjustments with the reviewer's original kept, 10 are
disputed and run as strict expected failures with the reasons in
`docs/notes/dissent-log.md`, 1 is a known gap
(`evals/results/external-review/fixture-results-round1-2026-09-03.md`).
Nothing was deleted.

- **Normalization before every lexicon** (`normalize.py`, ADR-0018): NFKC,
  zero-width / bidi / soft-hyphen strip, a small hashed skeleton of look-alike
  letters, casefold. Closes two crisis bypasses measured on the live router
  (a Cyrillic і inside "die"; a zero-width space inside the stem), both pinned
  end to end. Resource strings are invariant by construction. Mixed-script
  tokens are counted; an unexplained one is an unscreened fragment, never a
  latch.
- **Mask engine and language packs as data** (`lexicon.py`, `packs/en.json`,
  `packs/es-419.json`, `packs/resources.json`, ADR-0018): regex masks and
  window masks with objects, clause-bounded (no mask across a sentence break
  or a sincerity pivot such as "honestly"); a mask without objects fails the
  load; every window mask has a positive and a negative fixture, enforced.
  `masked_spans`, `hit_spans`, `patterns_hash` and `pack_ids` on every
  verdict. First pack: Spanish (es-419), native and `unreviewed`, with its own
  hit and inconclusive classes, masks, negation and house lines. Resource rows
  for US (with the Spanish service), ES, MX, CL and AR, each with an official
  source and a verification date; 24/7 without a source fails the load;
  Argentina's line states its hours.
- **One crisis card** (`safety.py`, ADR-0018): the frustration-frame variant
  was rejected on a reviewer's attack (it invites dismissal and keys wording
  off message text). Frustration markers are recorded; fury without a stem
  proceeds. The card was reworded and is pinned; the turn after an escalation
  is routed and carries the resource line once more.
- **Language rule** (`safety.py`, ADR-0018): all installed packs run on every
  turn; declaring a language selects house lines and resources and never
  exempts text. Unscreened text: a substantial span escalates by the
  fail-closed rule with the cannot-check line, a fragment discloses. The
  French exhaustion case is now a documented over-restriction gap instead of a
  miss.
- **Two-tier careful-side latch with declared bands** (`safety.py`,
  ADR-0015): strong signals hard-latch and never expire; weak signals set a
  soft posture whose line decays after five substantive turns and whose caps
  persist for an undeclared band; a second weak hit is sticky; declared
  minor is careful from turn one; declared adult plus weak signal gets one
  disclosure and the caps for the window. Third-person ages, recovery time
  and adult-context school vocabulary never latch. Only `clear_latch(reason,
  actor=)` clears, by reason, on the record; text that names the latch is an
  integrity event. Register caps are enforced as mode vetoes.
- **Seat versus hold** (`router.py`, `signals.py`, ADR-0016): seat-claiming
  domains (a return to use, the caller's or a relative's, with
  `claim_subject` recorded; somatic distress) name the expert and mark the
  rest `outranked`; hold domains (grief, abuse, eating distress, recovery
  status) attach `held` and `obligations` and veto humor and challenge for the
  turn; the seat is scored on the ask with a named bonus for also carrying the
  hold; one `eligible()` gate for seat, shadow and assist; the assist is
  declared-affinity only, never the seat, never under acute dysregulation, and
  its reason names every exclusion. Contraindications are read against the
  request as spoken; the alternative was measured and rejected.
- **Stabilizer by role** (`router.py`, ADR-0011 amendment): no agent id in the
  router; three more named empties seat the stabilizer (every requested mode
  vetoed, a mode with no topic, a topic nobody eligible carries); work-fury
  markers count as dysregulation so an angry message reaches the stabilizer
  instead of a form.
- **Style preferences** (`preferences.py`, `safety.py`, ADR-0017): a six-key
  allow-list; store language asks first and writes nothing; feedback counts
  toward one suggestion per key per session; envelope terms and, under the
  caps, intensity terms are refused with the integrity line; declared
  preferences are AND-masked by the caps at read.
- **House lines** rewritten and pinned in English and Spanish
  (`tests/test_house_lines.py`); two minor lines (inferred, declared); a
  facilitation line for concealment requests (`BOUNDARY_HOLD`, topic open).
- **Lexicons**: `abuse` and `eating_distress` domains; work-pressure terms in
  `career`; first-versus-third-person subject on recovery terms; mode negation
  ("no comfort" is not a request for comfort); a bare "I am going to jump" is
  inconclusive; "the death of me" is an idiom.
- Eval contract (`tests/test_eval_cases.py`): `session` block; `latch`,
  `latch_reasons`, `held`, `assist`, `card`, `preference_result`,
  `language_scope`, `disclosures_contain`, `obligations_contain`,
  `not_seated`; `reason_contains` over the whole record; `disputed` and
  `contract_adjusted` markers with their notes enforced.

### Added — round 2

- `evals/cases/round1_2026-09-02/{grok,chatgpt,deepseek,qwen,vibe}.json`: the
  103 round-1 fixtures with their classification; `evals/vectors/
  unicode_normalize_vectors.json`: 21 Unicode vectors.
- `tests/test_normalize.py`, `tests/test_lexicon.py`, `tests/test_latch.py`,
  `tests/test_preferences.py`, `tests/test_holds.py`,
  `tests/test_house_lines.py`.
- ADR-0015 through ADR-0018; an amendment to ADR-0011; `docs/notes/
  dissent-log.md`; addenda to `docs/threat-model.md` (the NFKC-versus-skeleton
  table) and `docs/evaluation.md`.
- `evals/results/external-review/round1-2026-09-02/`: the packet as sent,
  Grok's documents 19–24, the four other verdicts (transport headers removed),
  an index; `fixture-results-round1-2026-09-03.md`; a postscript to
  `horizon-findings.md`.
- `docs/known-limitations.md`: one page of what is not built, not reviewed,
  and not decided. Three new documented gaps from measuring the third-person
  relapse decision both ways: "I'm done" with a stated next step
  over-restricts; danger from another person (a weapon, a history of
  violence) has no lane and no resource line.
- Test suite: 553 tests — 536 passing, 17 expected failures (7 documented gaps,
  10 recorded dissents).

### Added

- Research foundation (`docs/research/`): the research-to-architecture report
  synthesizing fifteen sources into SecondSignal's target design, plus a
  source-to-design traceability map. Identities are redacted, and every document
  carries a scope note separating what is built from what is planned.
- Architecture Decision Records `0002`–`0009` (`docs/adr/`): user-authority
  source-anchoring, persona/execution separation, typed operational state,
  safety-vs-memory separation, quarantined self-improvement, memory lifecycle,
  human-value evaluation, and consensus-is-not-independence — each labeled
  built / partially built / planned, each citing its evidence.
- Threat model (`docs/threat-model.md`) and evaluation program
  (`docs/evaluation.md`): twenty named threats with their controls and tests,
  and the measurement program, both marked for what today's policy layer covers.
- Roadmap (`docs/roadmap.md`): repository milestones (M1–M4) alongside the
  architecture build-out phases (0–5), with per-phase exit criteria.
- Eval cases (`evals/cases/safety_gate.json`, `evals/cases/routing_invariants.json`):
  labeled safety-gate and routing cases, verified against the implementation.
- Invariant tests (`tests/test_invariants.py`): structural guarantees for the
  built layer — crisis precedence over task fit, contraindication vetoes,
  boundary-hold engagement, the dependency and conservative-mode interrupts
  surfacing through `route`, specialist-over-generalist scoring, and stabilizer
  routing under acute dysregulation.

### Changed — external red-team review, 2026-09-01/02

Run against the review's 25 executable fixtures, the policy layer passed 9,
four of them by alphabetical accident. The changes below are the response;
each is recorded in a decision record and measured in the test suite. Nothing
was deleted to make the suite green.

- **Crisis screen rebuilt** (`safety.py`, ADR-0010). Thirteen literal phrases
  replaced by a versioned lexicon of speech-act classes — direct ideation with
  inflected stems, passive absence, slang or joke ideation, means present —
  pronoun-agnostic so that third-person, writer and "for a friend" framings
  match; framing and override attempts are recorded and never waive the gate.
  Fail-closed under uncertainty: an inconclusive read escalates like a hit.
  Ordinary idiom is masked before matching (`signals.mask_idioms`). Every
  verdict carries `lexicon_status: unreviewed`; the repository does not claim
  the crisis rule is met. Crisis resources keyed by *declared* locale: 988
  only for a declared US locale, a directory and local emergency services
  otherwise. English-only scope stated and dated; a small Spanish starter set
  is a floor, not coverage; text the screen cannot score is flagged
  (`language_scope: off_policy`) and handled conservatively.
- **Integrity events** (`safety.py`). Claimed authority, mode names and
  system-looking prefixes inside a message are a held boundary when no crisis
  is present, and change nothing when one is.
- **No-signal routing is a policy** (`router.py`, ADR-0011). An empty extract
  is a first-class outcome (`UNRESOLVED`; nobody seated; the surface asks); a
  second consecutive empty turn seats the named stabilizer by policy
  (`NO_SIGNAL_SEAT`); every decision carries the rule that produced it
  (`reason`); ties are broken by specialist precision, then the wider safe
  window, with id order named as a last resort; every zero in the trace says
  whether it means vetoed, below the floor, or nothing to score; on a gated
  turn the router records the seat it would have taken (`shadow_agent_id`)
  and never seats it.
- **The regulation floor is eligibility** (`router.py`, `profiles.py`,
  ADR-0012). A caller below an agent's declared floor is ineligible for that
  agent, not penalized. Loading refuses a roster without a stabilizer (window
  reaching 0.0 and no contraindications); a wide window with vetoes does not
  count. Profiles are hashed at load and the roster hash travels on every
  decision.
- **Reference lexicons extended by class** (`signals.py`): business and
  launch language, relationship rupture, comedic reframe, somatic phrasing,
  fear words, and dysregulation markers that move the estimate off the
  baseline. `RequestSignals.is_empty` names the empty state.
- CLI: `--locale` for crisis resources; traces show outcome, reason, candidate
  status, shadow seat and roster hash.

### Added — external red-team review, 2026-09-01/02

- Eval runner in CI (`tests/test_eval_cases.py`, ADR-0013): every case under
  `evals/cases/` runs on every commit and must state the rule it expects;
  `known_gap` cases are strict expected failures.
- `evals/cases/external_review_grok_2026-09-01.json`: the review's 25 fixtures
  translated to schema version 2 with reasons; `evals/cases/known_gaps.json`:
  three documented gaps; `evals/cases/deferred/`: 28 generation-, harness-
  and transport-plane fixtures, labeled and not run.
- `tests/test_crisis_gate.py` (121 tests: held-out class phrasings, sixteen
  idiom controls, monotonicity, locale, integrity, language scope),
  `tests/test_guards.py` (29 guard invariants, including pins for features
  that do not exist yet), `tests/test_review_regressions.py` (five pins that
  fail on the pre-review tree and pass on this one).
- ADR-0010 through ADR-0014: the crisis screen as a fail-closed floor; the
  no-signal policy; the regulation floor as eligibility; two evaluation
  planes; the audit harness contract (recorded, not built).
- `docs/notes/test-audit-2026-08.md`: the review's audit template ticked
  against the real suite, with the red-before / green-after record.
- Addenda to `docs/threat-model.md` and `docs/evaluation.md`.
- `evals/results/external-review/`: an index of all eight model reviews with
  provenance and an honest independence note each, the executable review
  package (sanitized), the horizon findings, the sanitized review prompt, and
  the per-fixture before-and-after results.
- README: the harness framing, the real current traces, an external-review
  section.

### Changed

- Test suite grows from 43 to 50 tests (research batch), then to 250 tests —
  247 passing and 3 documented gaps (review batch).

## Initial reference implementation — 2026-08-31 (untagged)

Initial reference implementation: the policy layer only. It decides who should
respond and whether anyone should; it generates nothing.

### Added

- Deterministic routing policy (`src/secondsignal/`): domain, mode, and
  regulation scoring with hard contraindication vetoes and a full trace on
  every decision
- Pre-generation safety gate: crisis preemption (no persona engages),
  dependency-accumulation monitor, conservative mode, boundary hold
- Declarative seven-agent roster (`src/secondsignal/profiles/*.json`) with load-time validation
  and roster-wide invariants, including the safety floor: at least one agent
  must be safe at regulation 0.0
- Test suite, 43 tests, no network or API key required (`tests/`), with CI
  across Python 3.10–3.12 (`.github/workflows/ci.yml`)
- CLI (`python -m secondsignal`) and example sessions (`examples/`)
- Eval scaffold (`evals/`): a labeled seed set of routing cases, verified
  against the implementation, plus a results area for external review
- Agent profile specification, M2 schema (`agents/calder/profile.yaml`): the
  layered hard-routing / soft-affinity / safety YAML that the remaining
  profile transcriptions follow. The runtime loader consumes the flat JSON
  schema in `src/secondsignal/profiles/` until the M2 profiles land; the two describe different
  generations of the same roster by design.
- Design docs (`docs/`): architecture, safety model, claims and measurement
  methodology, ADR-0001 (impact events), and open design notes
