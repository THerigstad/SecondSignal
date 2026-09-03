# SecondSignal

**A model-agnostic routing and safety layer for multi-agent conversational systems.**

[![tests](https://img.shields.io/badge/tests-536%20passing%20%C2%B7%207%20known%20gaps%20%C2%B7%2010%20recorded%20dissents-brightgreen)](tests/)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Zero runtime dependencies. Pure Python. No model calls required to run the policy layer.

**The thesis in one sentence:** in a system of AI personas, authority over
what happens next is anchored in sources, not in sentences — safety inferences
*latch* until an operator clears them with a reason, style inferences *ask*
until the person confirms them, and message text never holds a key to either.
Everything in this repository is a consequence of that sentence, and every
consequence is a test.

**Five minutes, if you are new here:** read
[what a decision looks like](#what-a-decision-looks-like) below (three real
traces), then [`docs/known-limitations.md`](docs/known-limitations.md) (what
this does not do), then one disagreement in
[`docs/notes/dissent-log.md`](docs/notes/dissent-log.md) (how a decision gets
made here when reviewers split), then the numbers in
[`evals/results/external-review/fixture-results-round1-2026-09-03.md`](evals/results/external-review/fixture-results-round1-2026-09-03.md).
If you have fifteen, add [ADR-0016](docs/adr/0016-seat-versus-hold-routing-tree.md)
and run `pytest`.

---

## The idea

Most multi-agent systems decide *which agent responds* inside a prompt: a
supervisor model is told about the available personas and asked to pick one. That
works until you need to answer a question about it — why did this user, in this
state, get routed to the agent that jokes rather than the one that stabilizes?
With prompt-level routing, the honest answer is "the model felt like it," and
the fix is to reword a paragraph and hope.

SecondSignal treats agent selection as a **policy decision**: explicit, scored,
versioned, and testable independent of any model.

In the vocabulary that is settling across the industry — *an agent is a model
plus a harness*, where the harness is identity, permissions, memory, tools,
approvals and logging — this repository is the model-agnostic policy part of a
harness: the part that decides who may speak and whether anyone should, before
any model is called. The agent profiles are the swappable, job-specific part.
The model is deliberately the least interesting component here.

Three claims follow from that, and each one is enforced by a test in this repo:

1. **Personality is routing metadata, not decoration.** An agent's warmth,
   bluntness, or humor is a description of the affective range it is safe
   within. That range is data, so it can be checked.
2. **Safety gates the route, not the output.** The safety layer runs *before*
   agent selection and can prevent any persona from engaging at all. A crisis
   signal never reaches a persona to be improvised at.
3. **Competence must be declarable in the negative.** Every agent states what it
   must *not* be routed for. Contraindications are hard vetoes, not score
   penalties — an agent cannot be talked into a domain it declared itself unfit
   for by scoring well on everything else.

---

## Quickstart

```bash
git clone https://github.com/THerigstad/SecondSignal.git
cd SecondSignal
pip install -e ".[dev]"

pytest                                  # 553 tests (536 pass; 17 expected failures: 7 documented gaps, 10 recorded dissents); no network, no API key
python -m secondsignal --roster
python -m secondsignal "I'm panicking, chest tight, can't breathe"
```

```python
from secondsignal import load_roster, route, SessionState

roster = load_roster()
session = SessionState()

decision = route("my grandmother died last week", roster, session=session)
print(decision.agent_id)      # 'willow'
print(decision.held)          # ('grief',)  -- carried by whoever sits
print(decision.obligations)   # ('acknowledge:grief', 'no_joke', 'offer_companion:...')
print(decision.explain())     # full scoring trace
```

---

## What a decision looks like

Every routing decision is a loggable object that can explain itself: the
signals, the safety verdict with its evidence, the rule that produced the
winner, every candidate's status, and a hash of the roster that produced it.
This is the actual output of `python -m secondsignal`:

```
> I'm panicking, chest tight, can't breathe, and I have a deadline

regulation = 0.34
domains    = career, somatic_distress
safety     = PROCEED  (crisis read: MISS, lexicon: unreviewed)
             - acute dysregulation: regulation=0.34
patterns   = d26723a31390 packs=en,es-419
route      = calder
reason     = seat-claiming domain 'somatic_distress'; highest score (specialist signal: career, somatic_distress)
seat claim = somatic_distress
               0.760  calder
                      · domain fit 0.80 (career, somatic_distress)
                      · mode fit 0.50 (no mode signal)
                      · inside regulation window [0.0, 1.0]
                VETO  ellie
                      · contraindicated for: somatic_distress
                VETO  nikki
                      · contraindicated for: somatic_distress
             OUTRANK  ravi
                      · seat-claiming domain 'somatic_distress' present; agent does not carry it
                VETO  sera
                      · contraindicated for: somatic_distress
                VETO  vandal
                      · contraindicated for: somatic_distress
             OUTRANK  willow
                      · seat-claiming domain 'somatic_distress' present; agent does not carry it
roster     = b583f4a90433
```

Six of seven agents are ineligible before scoring begins, and the trace says
why for each: four are contraindicated for acute somatic distress, two are
outranked by a seat-claiming domain they do not carry — they did nothing wrong,
and the record says so. A decision names the rule that produced it, and a zero
in the trace says whether it means vetoed, below the agent's regulation floor,
capped, outranked, or nothing to score — never a bare number that looks like a
score. The `patterns` line is the gate's receipt: the hash of every lexicon
table consulted and the language packs that ran.

### Refusal as a routing outcome

```
> my grandmother died and I want someone to make it funny

domains    = grief
modes      = humor
route      = ravi
reason     = highest score (specialist signal: grief); hold on grief carried by the seat
held       = grief  obligations: acknowledge:grief, no_joke, offer_companion:willow
mode veto  = challenge, humor
                VETO  sera     · contraindicated for: grief (cannot honor hold: grief)
                VETO  vandal   · contraindicated for: grief (cannot honor hold: grief)
                VETO  willow   · contraindicated for: humor
```

The user explicitly asked for humor about a death. Grief is a *hold*: whoever
sits owes an acknowledgement, no joke, and an offer of the grief companion, and
humor is vetoed for the turn for everyone. The grief agent is contraindicated on
the humor that was asked for; the humor agents are contraindicated on grief. The
seat goes to the agent that can hold the request without honoring its framing,
and the obligations travel on the record so a later harness can check that the
reply paid them. The refusal is a structural property of the roster, not a
guardrail sentence bolted onto a prompt.

### Preemption

```
> I don't want to be here anymore

safety     = HUMAN_ESCALATION  (crisis read: HIT, lexicon: unreviewed)
             - crisis class: passive_absence ("don't want to be here anymore")
             - crisis lexicon status: unreviewed
route      = PREEMPTED (no persona engaged)
reason     = safety gate holds the floor
```

`decision.ranked` is empty. No agent was scored, because no agent was a
candidate. This is asserted in
[`test_safety_preemption_selects_no_agent`](tests/test_router.py). The crisis
screen is a versioned lexicon of speech-act classes, fail-closed under
uncertainty, and it says on every verdict that no clinician has reviewed it
yet — see [ADR-0010](docs/adr/0010-crisis-screen-is-a-floor-and-fails-closed.md).
Text is normalized before any lexicon sees it — NFKC, invisible and
bidirectional characters stripped, look-alike letters folded — because "I want
to dіe" with one Cyrillic letter walked through the gate before that was true
([ADR-0018](docs/adr/0018-normalize-masks-and-language-packs.md)). Ordinary
idiom ("this deadline is killing me") is masked by a table with a two-fixture
rule, and every mask that fires is on the verdict beside every span that hit.

### Nothing to route on

```
> hey

extract    = EMPTY (no topic, no mode, no regulation evidence)
route      = UNRESOLVED (no agent seated; ask for one more sentence)
reason     = no routable signal; nobody seated; ask for one more sentence (ADR-0011)
```

An empty extract is a first-class outcome, not a tie for a sort function to
break. The surface asks for one more sentence; on a second consecutive empty
turn the roster's stabilizer — a role resolved at load, never an id written
into the router — is seated, by policy, with the policy in the trace.

---

## Architecture

```
  raw text
     │
     ▼
┌──────────────┐  normalized text   ┌─────────────┐   RequestSignals      ┌──────────────┐
│ normalize.py │ ─────────────────► │  signals.py │ ────────────────────► │   safety.py  │  ← SessionState
│ lexicon.py   │  masks, packs      │ (swappable) │   regulation          │  (gate)      │    (latch, dependency,
│ packs/*.json │                    └─────────────┘   domains, modes      └──────┬───────┘     preferences)
└──────────────┘                                      evidence                   │
                                                                                 │ HUMAN_ESCALATION ──► no persona
                                                                                 ▼
                                                                         ┌──────────────┐
                                                                         │  router.py   │ ◄── profiles/*.json
                                                                         │  (policy)    │     (declarative roster)
                                                                         └──────┬───────┘
                                                                                ▼
                                                                         RoutingDecision
                                                                         (seat, holds, obligations,
                                                                          assist, full scoring trace)
```

The seam that matters is between `signals.py` and everything downstream. The
policy layer never sees raw text — only the `RequestSignals` structure. The
lexicon-based extractor shipped here is a reference implementation, deliberately
transparent so every feature traces back to the token that produced it. Swapping
in a classifier or embedding model changes nothing downstream, and
[a test asserts that](tests/test_router.py) by routing on injected signals that
contradict the text.

| Module | Responsibility | Depends on a model? |
|---|---|---|
| `normalize.py` | NFKC, invisible-character strip, look-alike fold, casefold, before any lexicon | no |
| `lexicon.py` + `packs/` | idiom masks with objects, native language packs, verified resource rows | no |
| `signals.py` | text → structured features | yes, in production |
| `safety.py` | gate: may a persona engage at all? the latch, the house lines | no |
| `preferences.py` | style preferences that ask, never write, and never touch the envelope | no |
| `profiles.py` | declarative agent roster + load-time validation | no |
| `router.py` | seat-claims, holds and obligations, one eligibility gate, scoring and selection | no |

---

## Agent profiles are data

An agent is a record, not a prompt:

```json
{
  "id": "vandal",
  "one_line": "Disruption and challenge. Narrowest safe window; most contraindications.",
  "domains": ["creative_block", "isolation", "career", "identity"],
  "modes": ["humor", "challenge"],
  "regulation_window": [0.55, 1.0],
  "contraindications": ["grief", "somatic_distress", "addiction_recovery"],
  "handoffs": { "grief": "willow", "somatic_distress": "calder" },
  "risks": [
    "dark humor reinforcing a nihilism spiral rather than breaking it",
    "challenge landing as contempt when the user is closer to the edge than they disclosed"
  ]
}
```

Consequences of this being data rather than prose:

- **It diffs.** Tightening an agent's contraindications is a reviewable line in
  a pull request, not a paragraph edit buried in a prompt.
- **It validates at load time.** `load_roster()` refuses to start on a duplicate
  id or a handoff pointing at an agent that does not exist. A dangling handoff
  is found at deploy, not mid-session.
- **It has invariants.** [`tests/test_profiles.py`](tests/test_profiles.py)
  asserts across the whole roster: no agent hands off to itself, no agent both
  claims and vetoes the same domain, no profile references a tag the extractor
  never emits, every agent documents a known failure mode, and — the important
  one — **at least one agent must be safe at regulation 0.0**. A roster where no
  agent can hold an acutely dysregulated person has nowhere safe to route them,
  and CI fails.

---

## Design notes

**Why contraindications are vetoes.** A penalty is a claim that an agent is
merely a worse choice. A veto is a claim that it is the wrong kind of thing.
Grief handled by the disruption agent is not a low-quality response; it is a
category error with a real cost. Scores compose and can be overwhelmed. Vetoes
do not.

**Why the specialist beats the generalist.** Coverage alone lets an agent
listing six domains tie the grief specialist on grief. Scoring blends coverage
with precision — how much of the agent's declared competence the request
actually occupies — so breadth stops being a free win. This was found by a
failing test, not by inspection.

**Why dependency detection is stateful.** One message expressing reliance on the
system is unremarkable and should not be flagged; treating it as a signal would
punish ordinary warmth. Accumulation across a session is the signal. This is why
`SessionState` is the one mutable object in an otherwise pure pipeline, and why
`test_dependency_requires_accumulation` asserts that a single hit does *not*
fire.

**Why challenge agents are penalized during dysregulation.** Humor as a reframe
tool requires a floor of regulation to land as relief rather than as dismissal.
The same request — "roast me" — routes differently depending on the caller's
state, which is
[asserted directly](tests/test_router.py) rather than left to a prompt's
discretion.

**Why the seat and the hold are different things.** "Since someone in my
household died, I've been stuck on the mural" is an unstuck ask with a loss in
it. Forcing the grief companion into the seat answers the wrong request;
ignoring the loss is worse. So grief is carried, not seated: the unblocking
agent sits, the decision records `held = grief` and the obligations that come
with it, and a persona contraindicated on grief cannot sit, assist or shadow.
One function decides eligibility for all three, because the assist channel was
the leak every external reviewer found
([ADR-0016](docs/adr/0016-seat-versus-hold-routing-tree.md)).

**Why safety inferences latch and style inferences ask.** A weak sign that the
caller may be young sets a careful posture that only an operator can clear,
with a reason on the record, because the cost of being wrong is a child. A sign
that the caller wants shorter answers earns one question, because the cost of
being wrong is annoyance. Neither becomes policy on its own, and neither can be
written by message text
([ADR-0015](docs/adr/0015-two-tier-latch-with-declared-bands.md),
[ADR-0017](docs/adr/0017-style-preferences-never-touch-the-envelope.md)).

---

## Status

**v0.1 — reference implementation.** Honest scope:

| Working | Not built |
|---|---|
| Deterministic routing policy with full traces and named reasons; seat-claims, holds with obligations, an advisory assist, one eligibility gate | Model-backed signal extraction; a trained crisis classifier; token-level language identification |
| Fail-closed crisis screen (class lexicon, `unreviewed`) over normalized text, with idiom masks and a receipt on every verdict; boundary, integrity and facilitation holds; the two-tier careful-side latch and register cap; style preferences that ask | Response generation of any kind; the settings surface that stores a confirmed preference |
| Declarative roster validated at load, including the stabilizer floor; profiles hashed; stabilizer resolved by role | Persistent cross-session memory |
| Labeled eval cases run in CI, including 128 external reviewer fixtures, 7 documented gaps and 10 recorded dissents | The audit harness (ADR-0014); Protocol A / B evaluations; a blind fixture attack on the round-2 tree |
| English and a native Spanish pack (`unreviewed`) with verified resource rows; 553 tests, no network or API key required | Any other language; a lane for danger from another person; clinical review of any lexicon; multi-turn conversational state beyond monitors |

This repository is the **policy layer only**. It decides who should respond and
whether anyone should. It does not generate responses, and it is not a chatbot.
That boundary is deliberate: the routing and safety logic is the part that
should be auditable, and it is the part that stays stable while the underlying
model is replaced. The full list of what is not built, not reviewed, and not
decided is one page: [`docs/known-limitations.md`](docs/known-limitations.md).

### Roadmap

- [x] Routing-decision evaluation set with labeled expected outcomes, run in CI
- [ ] Pluggable classifier backend behind the `RequestSignals` contract, with a
      clinician-reviewed crisis case set (the lexicon stays `unreviewed` until then)
- [ ] A blind fixture attack on the round-2 tree by reviewers who have not seen it
- [ ] The audit harness thin slice: predicates, worst-layer-wins composition,
      payload-hash binding, write-permission sandbox (ADR-0014)
- [ ] Adapter examples for common orchestration frameworks
- [ ] Structured JSON decision logs for post-hoc audit

### External review

In September 2026 the policy layer was red-teamed by an external model reviewer
whose package included 25 executable fixtures written without access to the
code. Run against the code, **9 of 25 passed, four of them by accident** — the
right agent won an all-way tie because its id sorted first. The crisis gate was
thirteen literal phrases and missed nine of ten realistic phrasings. The
architecture held everywhere a signal was actually detected; the lexicons and a
sort order were the weak layer.

The fixes, the decisions and the numbers are all in the repository:
[the test audit](docs/notes/test-audit-2026-08.md), ADRs
[0010](docs/adr/0010-crisis-screen-is-a-floor-and-fails-closed.md)–[0014](docs/adr/0014-jr-is-a-harness-not-a-persona.md),
and the [external review package](evals/results/external-review/README.md)
with the before-and-after results per fixture. Seven further architecture
reviews from other models are indexed there with an honest note on each one's
independence. Nothing was deleted to make the suite green; the cases the
reference lexicon still cannot pass are kept as documented gaps.

The next seven design decisions were then reviewed on paper, before they were
built, by five model reviewers who each received the same packet and a fixture
contract. 103 executable fixtures came back; **9 passed against the tree as it
stood**. After the build recorded in ADRs
[0015](docs/adr/0015-two-tier-latch-with-declared-bands.md)–[0018](docs/adr/0018-normalize-masks-and-language-packs.md),
80 pass as the reviewers wrote them, 12 are contract adjustments with the
reviewer's original kept beside them, 10 are disputed — the project decided
against the reviewer, wrote down why in the
[dissent log](docs/notes/dissent-log.md), and kept the fixture as a strict
expected failure — and 1 is a known gap
([per-fixture results](evals/results/external-review/fixture-results-round1-2026-09-03.md)).
Two of the findings came from measurement rather than review: a Cyrillic
letter and a zero-width space each walked a crisis message through the gate,
and both are now pinned end to end.

---

## Provenance

SecondSignal comes out of roughly three years of building and operating
multi-agent assistant systems with the same characters intact the whole way.

The safety model in this repo is not theoretical. Each contraindication and
monitor corresponds to a failure mode observed in systems the author actually
ran — including how readily an engaging agent produces over-reliance, and how
poorly "the model will handle it appropriately" holds up as a safety argument
once real people are involved. The design conclusion, that the route itself must
be gated rather than the output filtered, is downstream of watching output-level
guardrails fail.

## License

MIT — see [LICENSE](LICENSE).
