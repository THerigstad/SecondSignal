# Known limitations

One page, kept current, for a stranger who wants to know what this
repository does not do before reading what it does. Every item here is also
stated where it applies; this page exists so nobody has to collect them.
Last audit: 2026-09-08.

## What is not built

- No generation layer. SecondSignal decides who may speak and whether
  anyone should; it writes no replies. Nothing in this repository is a
  chatbot, and the personas exist only as routing profiles.
- No audit harness wired in. The after-the-fact check that a reply honored
  the decision record — the obligations on a hold, the register cap, a
  stored preference — is a contract (ADR-0014) with a reference port in the
  tree (`src/secondsignal/jr.py`, predicates in ADR-0020, Proposed) that
  nothing calls. Obligations are recorded on every decision and enforced by
  nothing yet. Where a decision rests on an obligation being honored, the
  dissent log says so (D3).
- No intake and provenance function, no ledger, no interlock, no commit
  monitor, no narrators. The security layer is specified as five objects on
  five clocks (ADR-0019, ADR-0022, ADR-0023, all Proposed); only the gate
  exists. Nothing labels where a session fact came from, nothing keeps an
  append-only record of restrictions, and nothing persists a restriction
  past the session. The README's status section names each record.
- No persistence of a safety restriction across sessions, which contradicts
  a promise the tree makes. ADR-0015 says a strong signal sets a hard latch
  that does not expire; that is true only inside one in-memory session. The
  session-boundary rule starts a new session after a published elapsed
  time, and session state lives in memory, so today a hard latch dies with
  the session. ADR-0023 makes persistence an explicit part of the ledger;
  until it is built, "does not expire" means "does not expire while the
  process runs".
- No voice and no embodiment, by scope lock, for the current quarter. The
  ethics table a reviewer wrote for it (no cloned voices, no child voices,
  no user-uploaded voices, no voice without a release door, on escalation
  the voice stops and only the card remains, text as the default channel)
  is recorded and waits for the quarter it applies to.
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
- Trauma-informed care is a design lens the house lines were written under
  (no shame, no urgency, face value, choice kept open, transparency about
  what the system does next, options few and concrete and handed over) and
  nothing in the repository yet names it as a review target or tests for
  its failure. The failure to test for is the line that asks too much of
  the person at the moment they have the least: to generate options, to
  decide, to perform, or to self-label. Filed 2026-09-08 beside the
  neurodivergent item; work to do: name the principles in the design notes,
  give every review packet a trauma-informed attack target, and add
  fixtures for the "asks too much" failure.
- The adult false-positive rate of the hard latch is unmeasured. A declared
  adult who trips a strong self-age signal is latched, and under the
  operator-only rule the only exit is a human. The plan on record: two
  labeled corpora built by two people before any code (adult messages from
  the five misfire families — reminiscence, quotation, fiction and
  role-play, adults under someone's control, teachers quoting students —
  and plausible teen messages), two numbers with bounds the operator sets,
  fix families with fixtures, and a rerun until the adult rate is under the
  bound with the minor miss rate unchanged. Until then the residual is
  bounded by design (capped register, no romance, every topic open) and is
  the deployer's to staff.

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
  game frames are excluded. This is not the full danger lane: a message
  describing present confinement, prior violence or fear for dependents
  with no weapon named proceeds today with nobody seated, there is no
  abuse-history hold, and there is no human-reviewed resource row for
  danger from another person or for the weeks after leaving, which is the
  documented highest-risk window. No number has been added. These three
  are the next build block, ahead of every other item on this page, and the
  post-separation line ships only after a human verification pass over the
  rows it points at. The operator's design note still stands: once a weapon
  or a person in danger is in the message, the question is how the person
  gets to safety, not who comforts.
- Quotation and mention over-restrict. A first-person crisis stem inside a
  quotation, a lyric, a line of fiction the person is discussing, or a
  sentence about the words themselves is screened as if the person said it,
  and it fails closed. This is a chosen over-restriction (a quotation frame
  would be a key off the crisis path), recorded so nobody mistakes it for a
  gap that was missed.

## What the design leaves open

- A relative's return to use: decided with dissent on 2026-09-08 (a bare
  report seats the recovery persona; an ask seats the ask with the recovery
  hold carried and the recovery persona offered), but the tree still seats
  the recovery persona on every relative sentence, so the decision and the
  code disagree until the next build block lands; see
  `docs/notes/dissent-log.md`, D3.
- Whether the gate may reuse its own prior verdict on byte-identical text.
  Ruled no on 2026-09-08; every message is re-evaluated fresh. If the
  question returns it returns narrower, as a cache of fail-closed results
  used only as a floor, with three reviewer tests already written for it.
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

## Deployment limitations stated on 2026-09-08

- A hard latch is cleared only by an operator with a reason. No clock
  clears it and no message clears it. A deployment that keeps that rule
  therefore owes its users a person who can read a clearance request and
  act on it within a published time; a self-hosted copy with no such person
  has a restriction with no exit, and must say so to the people it serves.
- One person currently edits the rules, holds the evidence and the keys, and
  is the only appeal reviewer. Every independence claim is void while one
  hand holds all three, so this repository makes none: not "three
  independent safety systems", not "defense in depth", not "tamper-proof",
  not "self-correcting", not "human-governed", not "auditable". When a
  second human exists, policy editing, appeal review and key holding are
  separated and the ledger's head digest is checkpointed where the operator
  cannot silently rewrite it.
- Reviewer independence is unmeasured. Which model family should hold which
  role is a measurement (conditional error correlation per decision class
  over the existing fixture sets), not a name in a document, and nobody has
  run it.

## What this page is not

It is not a roadmap (see `docs/roadmap.md`) and not the threat model (see
`docs/threat-model.md`). It is the list of things a reader could otherwise
mistake for claims.
