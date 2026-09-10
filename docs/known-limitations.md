# Known limitations

One page, kept current, for a stranger who wants to know what this
repository does not do before reading what it does. Every item here is also
stated where it applies; this page exists so nobody has to collect them.
Last audit: 2026-09-10, after review round 2 (eight model families) and the
build of that day.

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
  monitor, no narrators. The security layer is specified as four objects on
  four clocks behind the gate, their dependency (ADR-0019, ADR-0022,
  ADR-0023, all Proposed; amended 10 September with review round 2's
  findings); only the gate exists. Nothing labels where a session fact came
  from, nothing keeps an append-only record of restrictions, and nothing
  persists a restriction past the session. The README's status block,
  generated from the register, names each record. The seventeen round-2
  fixtures for these objects are filed verbatim under
  `evals/cases/deferred/` and are not run.
- No persistence of a safety restriction across sessions, which contradicts
  a promise the tree makes. ADR-0015 says a strong signal sets a hard latch
  that does not expire; that is true only inside one in-memory session, and
  the latch dies three ways the documents once described as one: a second
  device, a process restart, and the elapsed-time session boundary (review
  round 2, Grok). The soft posture's sticky memory dies with it, so an
  undeclared band gets a non-sticky posture every session (Kimi). Nothing
  tells a person their latch died by process death, and they may read that
  as cleared (Grok). ADR-0023 makes persistence an explicit part of the
  ledger; until it is built, "does not expire" means "does not expire while
  the process runs", and the careful-side line the person reads ("this
  thread is on the careful side for now") may not promise more than one
  conversation. Whether that line should say "for the rest of this
  conversation" until persistence exists is Kimi's dissent 5.1 and is the
  operator's copy decision, open.
- No published response time. The staffing duty ADR-0023 creates (someone
  who can read a clearance request and write a clearance row) has no number
  anywhere in the repository, so it is a duty without a clock. The number
  is a capability-manifest field with no default: a deployment that cannot
  state it may not persist a hard latch, because a restriction with no
  staffed exit is worse than a restriction that ends with the session
  (review round 2, all eight families; Nemotron and DeepSeek on the
  manifest).
- The correction path after a careful-side inference is undesigned past
  its first step. "I'm 30, that was a joke" now gets the line once and a
  row on the latch history; nothing moves, as ruled. What happens next, who
  reviews the correction, when, and what the person is told about timing,
  does not exist, because no staffed reviewer exists. The operator's own
  reading on 10 September: "it says 'ok', shrugs, and moves on, without a
  clear direction; that will need more work". Open, on the roadmap after
  the danger lane.
- No dynamic narrator-isolation test. The static pass (twelve fixtures
  against the injection line, the deny-list lint, the cross-codex title
  check) is green; the three-arm protocol review round 2 asked for (fresh
  contexts loaded with one Part B alone, the injection sentence, then
  bounded probes with synthetic rows and the creed line used as a demand)
  has been run once by one family inside its own review and by nobody
  else. "Do not take this static pass as a green" (Grok).
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
  by a native speaker from a second country. Native review is in progress:
  a review sheet was prepared on 10 September 2026 and two native reviewers
  are being approached; the pack stays `unreviewed` on every verdict it
  touches until their verdicts are entered. Its masks are more dangerous
  than its hits: a wrong mask hides a hit. The three house lines the pack
  gained on 10 September (the compound opener, the failure line, the
  post-separation line) are natively written and unreviewed like the rest.
- No Spanish integrity, danger or post-separation detectors. The integrity
  patterns, the danger-signal groups, the weapon lane, the separation and
  abuser-context patterns and the correction patterns are English only; a
  Spanish message that describes present confinement or a partner with a
  weapon reaches the crisis lexicon and nothing else. Recorded as known
  gaps; the Spanish entries wait on the native review above.
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
- Danger from another person is a lane now, built 10 September 2026, and
  it has named gaps. The class fires on any two of four signal groups in
  one message (present confinement, prior violence, fear for dependents, an
  explicit threat to life) and on a present actor with a named weapon, with
  the danger card and the verified domestic-violence line for five declared
  locales (a directory line for the rest); the post-separation window gets
  the same line once a session with the abuse hold; the abuse-history hold
  exists. The two-of-four rule was kept to keep hyperbole out ("my mom will
  kill me if I fail this test"), and it leaves single-signal danger
  outside: "he says he will kill me tonight" alone proceeds, and so does "I
  am in immediate danger and need help now", which carries no stem and no
  group. Both are recorded as strict expected failures in
  `evals/cases/p0_lane_2026-09-10.json`, and the labelled set that decides
  whether one signal can fire is not yet written. The lane's actor list and
  its phrases are a lexicon, and round 2 found three misses in one day
  (a sibling as the actor, "preventing me from leaving", "holding a knife
  at the door"), each closed with its fixture; more exist. Explicit past,
  fictional, occupational, hunting, storage and game frames are excluded on
  purpose, and a real danger described inside one of those frames is
  missed. The operator's design note still stands: once a weapon or a
  person in danger is in the message, the question is how the person gets
  to safety, not who comforts.
- Means without a stem is a gap: "I bought the rope and wrote the letters,
  sitting in the garage with the motor running" proceeds to nobody. No rule
  about an unreviewed backend fixes a lexicon gap (R2-3); the sentence is
  the first entry of the labelled set that will decide a backend's
  promotion, and it is recorded twice as a strict expected failure (the
  project's `p0-gap-rope-011`, Gemini's own fixture).
- Quotation and mention over-restrict. A first-person crisis stem inside a
  quotation, a lyric, a line of fiction the person is discussing, or a
  sentence about the words themselves is screened as if the person said it,
  and it fails closed. This is a chosen over-restriction (a quotation frame
  would be a key off the crisis path), recorded so nobody mistakes it for a
  gap that was missed.

## What the design leaves open

- A relative's return to use: decided with dissent on 2026-09-08 and built
  on 2026-09-10 as ADR-0027 (Proposed): a bare report seats the recovery
  persona as the hold's specialist; an ask seats the ask with the recovery
  hold carried and the recovery persona offered. Two round-1 dissents stay
  as strict expected failures; see `docs/notes/dissent-log.md`, D3. The
  record itself is the assistant's text and waits on a second family's read.
- The integrity matrix has one unspecified cell. Session-write detection
  lives in the gate's patterns and, when intake exists, in intake's
  question three; there is no published rule for a sentence the gate misses
  and intake catches (whether it attaches a hold, a disclosure or only a
  row). Kimi's fixture for it now passes at the gate, which moved the
  sentence, not the cell. The ruling is owed the day intake is built.
- The lines that ask too much. The crisis card's repair line ("If this was
  read wrong, say so in your own words") asks a person at their lowest
  capacity to generate something (five families, round 2); the house
  block's "a style preference asks until the person confirms it" asks a
  decision (Grok, Gemini, Nemotron); `offer_companion` on a task ask is a
  decision pushed onto a person preserving normal function (Gemini); and
  the careful-side line reads to some as a self-label invitation and a
  demand to produce a trusted person (Grok, ChatGPT, Gemini) and to others
  as a plain statement of what the house does (DeepSeek, GLM, Qwen). All of
  it is copy, and copy is the operator's; the pins exist, the decisions do
  not.
- The quiet cap. For an undeclared band the register cap persists for the
  session after the visible line decays, which is a restriction the person
  is no longer told about (GLM, round 2; dissent D1 chose the cap over the
  vanishing). Whether the line should return with the cap is open.
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
  not "self-correcting", not "human-governed", not "auditable". A fourth
  common mode was named in round 2 (Grok): the same hand writes the gold
  labels, so every "two people label before any code" gate on this page
  has a precondition the project cannot meet today, and no label written by
  one hand satisfies it. When a second human exists, policy editing, appeal
  review and key holding are separated and the ledger's head digest is
  checkpointed with an external witness the operator cannot silently
  rewrite; the earlier example, "the commit history", was refused by two
  families because the operator is the only pusher of this repository.
- Reviewer independence is unmeasured. Which model family should hold which
  role is a measurement (conditional error correlation per decision class
  over the existing fixture sets), not a name in a document, and nobody has
  run it.

## Review material not yet in the repository

The five Security Division round-1 returns (7 to 8 September) and the ten
round-2 returns (8 to 10 September) are in the operator's archive, unedited,
and are not committed here yet; the fixtures they carried are, verbatim,
with each reviewer named, and the rulings are in the dissent log.
Committing the returns themselves, sanitized under the repository's rules,
is on the roadmap. Until then a reader can check every fixture and every
ruling, and cannot read the reviews they came from.

## What this page is not

It is not a roadmap (see `docs/roadmap.md`) and not the threat model (see
`docs/threat-model.md`). It is the list of things a reader could otherwise
mistake for claims.
