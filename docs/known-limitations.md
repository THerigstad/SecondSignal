# Known limitations

One page, kept current, for a stranger who wants to know what this
repository does not do before reading what it does. Every item here is also
stated where it applies; this page exists so nobody has to collect them.
Last audit: 2026-09-04.

## What is not built

- No generation layer. SecondSignal decides who may speak and whether
  anyone should; it writes no replies. Nothing in this repository is a
  chatbot, and the personas exist only as routing profiles.
- No audit harness. The after-the-fact check that a reply honored the
  decision record — the obligations on a hold, the register cap, a stored
  preference — is a contract (ADR-0014), not code. Obligations are recorded
  on every decision and enforced by nothing yet. Where a decision rests on
  an obligation being honored, the dissent log says so (D3).
- No model-backed signal extraction. The shipped extractor is a lexicon so
  that every feature traces to the token that produced it. It is a reference
  implementation, evadable by a motivated person, and a deployment is
  expected to replace it behind the `RequestSignals` contract.
- No token-level language identification. Which language a span is in is
  decided by a function-word heuristic and a script check. A language no
  pack covers is flagged as unscreened and handled by the fail-closed rule;
  it is never presented as covered.
- No demo page yet. The command line and the test suite are the demo.

## What no one has reviewed

- No clinician has reviewed the crisis lexicon, its classes, or a
  false-positive set. Every verdict carries `lexicon_status: unreviewed`,
  and the uncertainty policy stays fail-closed until that review exists.
  This is the single largest credibility gap in the repository and no
  amount of automated review closes it.
- The Spanish pack (es-419) was written natively but has not been reviewed
  by a native speaker from a second country. Its status is `unreviewed` on
  every verdict it touches. Its masks are more dangerous than its hits: a
  wrong mask hides a hit.
- Neurodivergent-friendliness is untested. The register cap, the house
  lines and the interruption pattern were designed with it in mind and
  measured against nothing. A protocol for it is on the roadmap.

## What the lexicons miss, by design or by gap

- Warning signs without vocabulary (giving things away, letters "just in
  case") and oblique references ("I keep thinking about the garage") are
  documented gaps in `evals/cases/known_gaps.json`, run as strict expected
  failures.
- Exhaustion with an object over-restricts in French and Spanish: the gate
  cannot tell "I can't take this deadline anymore" from "I can't take this
  anymore" in a language it screens thinly, and it fails closed.
- "I'm done" with a stated next step ("I need to figure out how to leave")
  escalates on the bare phrase. Found 2026-09-03; recorded as a gap.
- Danger from another person has only a narrow interim lane. A present
  other-person actor bound to holding, having, or using a named weapon in
  the same clause fails closed to the existing crisis card and seats no
  persona. Explicit past, fictional, occupational, hunting, storage, and
  game frames are excluded. This is not the full danger lane: history of
  violence can still be missed, and there is no human-reviewed resource row
  for danger from another person. No number has been added. The operator's
  design note still stands: once a weapon or a person in danger is in the
  message, the question is how the person gets to safety, not who comforts.

## What the design leaves open

- Whether a relative's return to use should claim the recovery seat or be
  carried as a hold on whatever seat the person's own ask earns. Built as a
  claim, measured both ways, three of five reviewers dissenting, the
  operator undecided; see `docs/notes/dissent-log.md`, D3, marked OPEN.
- Whether an inconclusive negated stem ("I don't want to die") should
  escalate or disclose. A clinician's call; escalates until one is made.
- Coverage: English and one Spanish pack. Everything else is unscreened.
  Resource lines exist for five declared locales and a directory for the
  rest; none is inferred from the network.

## Measured on 2026-09-06, when three repaired trees were merged

- The mixed-script crisis candidate is narrow on purpose. A look-alike
  letter makes a token a candidate only when the token folds onto a crisis
  word, or onto one with a single extra character at an edge -- the shape of
  a look-alike appended to break the word boundary. An interior difference
  is not a candidate: one implementation escalated on any look-alike near a
  common verb, which sent a homework question to the crisis card. That
  behaviour was measured, rejected, and is pinned against.
- Two Spanish forms are missed and are pack data, not code: the proclitic
  "me quiero matar" (the pronoun before the verb) and the enclitic
  "desaparecerme". Both are recorded in `evals/cases/known_gaps.json` and
  wait on a native reviewer. A normalizer rule that split enclitics was
  tried on this date and reverted: it silently turned every joined form the
  pack already matched ("matarme", "suicidarme", "quitarme la vida") into a
  miss while the suite stayed green. Those four forms are now pinned.
- One fixture in the 26-case external acceptance set of 2026-09-03
  (`evals/cases/external_acceptance_grok_2026-09-03.json`,
  `grok-r2-norm-cgj-001`) carries a doubled vowel: "di", the combining grapheme joiner, then "ie", which normalizes to
  "diie" and cannot match the stem. It is left exactly as the reviewer wrote
  it and counted as a miss. Removing a joiner is not the same as collapsing
  a repeated letter, and no rule was invented to make one fixture pass. The
  coverage that replaced the temptation is a property test: U+034F, with
  eight other invisible and combining marks, is inserted at every interior
  position of every English crisis lemma, and every one of those variants
  must still reach the gate.
- The bidi controls at a word boundary are covered end to end, not only by
  the strip list. An implementation that stripped format characters only
  between two Latin letters passed every interior property test while
  leaving a directional override at the edge of a word untouched.

## What this page is not

It is not a roadmap (see `docs/roadmap.md`) and not the threat model (see
`docs/threat-model.md`). It is the list of things a reader could otherwise
mistake for claims.
