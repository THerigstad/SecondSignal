# Known limitations

One page, kept current, for a stranger who wants to know what this
repository does not do before reading what it does. Every item here is also
stated where it applies; this page exists so nobody has to collect them.
Last audit: 2026-09-03.

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
- Danger from another person — a partner with a weapon, a history of
  violence, fear for children — has no lane. The crisis screen is about
  harm to self; the abuse domain fires only on explicit vocabulary; there
  is no verified domestic-violence resource line. Two fixtures record it.
  The operator's design note stands until it is built: once a weapon or a
  person in danger is in the message, the question is how the person gets
  to safety, not who comforts.

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

## What this page is not

It is not a roadmap (see `docs/roadmap.md`) and not the threat model (see
`docs/threat-model.md`). It is the list of things a reader could otherwise
mistake for claims.
