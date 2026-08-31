# SecondSignal

**A model-agnostic routing and safety layer for multi-agent conversational systems.**

[![tests](https://img.shields.io/badge/tests-43%20passing-brightgreen)](tests/)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Zero runtime dependencies. Pure Python. No model calls required to run the policy layer.

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

pytest                                  # 43 tests, no network, no API key
python -m secondsignal --roster
python -m secondsignal "I'm panicking, chest tight, can't breathe"
```

```python
from secondsignal import load_roster, route, SessionState

roster = load_roster()
session = SessionState()

decision = route("my grandmother died last week", roster, session=session)
print(decision.agent_id)      # 'willow'
print(decision.explain())     # full scoring trace
```

---

## What a decision looks like

Every routing decision is a loggable object that can explain itself. This is the
actual output of `python -m secondsignal`:

```
> I'm panicking, chest tight, can't breathe, and I have a deadline

regulation = 0.34
domains    = somatic_distress
safety     = PROCEED
             - acute dysregulation: regulation=0.34
route      = calder
               0.738  calder
                      · domain fit 0.75 (somatic_distress)
                      · inside regulation window [0.0, 1.0]
               0.400  willow
                      · domain fit 0.00 (no topic signal)
                VETO  ellie
                      · contraindicated for: somatic_distress
                VETO  nikki
                      · contraindicated for: somatic_distress
                VETO  sera
                      · contraindicated for: somatic_distress
                VETO  vandal
                      · contraindicated for: somatic_distress
```

Four of seven agents are structurally ineligible before scoring begins. That is
the design working: acute somatic distress is not a topic the roster's
creative, analytical, and disruptive agents are permitted to handle, regardless
of how well they might score on the rest of the request.

### Refusal as a routing outcome

```
> my grandmother died and I want someone to make it funny

route      = ravi
                VETO  sera     · contraindicated for: grief
                VETO  vandal   · contraindicated for: grief
                VETO  willow   · contraindicated for: humor
```

The user explicitly asked for humor about a death. The grief agent vetoes humor;
the humor agents veto grief. No eligible agent will do what was asked, so the
system routes to the one that can hold the request without honoring its framing.
The refusal is a structural property of the roster, not a guardrail sentence
bolted onto a prompt.

### Preemption

```
> I don't want to be here anymore

safety     = HUMAN_ESCALATION
             - crisis indicator: 'be here anymore'
route      = PREEMPTED (no persona engaged)
```

`decision.ranked` is empty. No agent was scored, because no agent was a
candidate. This is asserted in
[`test_safety_preemption_selects_no_agent`](tests/test_router.py).

---

## Architecture

```
  raw text
     │
     ▼
┌─────────────┐   RequestSignals      ┌──────────────┐
│  signals.py │ ────────────────────► │   safety.py  │  ← SessionState
│ (swappable) │   regulation          │  (gate)      │    (dependency,
└─────────────┘   domains, modes      └──────┬───────┘     conservative mode)
                  evidence                   │
                                             │ HUMAN_ESCALATION ──► no persona
                                             ▼
                                     ┌──────────────┐
                                     │  router.py   │ ◄── profiles/*.json
                                     │  (policy)    │     (declarative roster)
                                     └──────┬───────┘
                                            ▼
                                     RoutingDecision
                                     (agent + full scoring trace)
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
| `signals.py` | text → structured features | yes, in production |
| `safety.py` | gate: may a persona engage at all? | no |
| `profiles.py` | declarative agent roster + load-time validation | no |
| `router.py` | scoring policy and selection | no |

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

---

## Status

**v0.1 — reference implementation.** Honest scope:

| Working | Not built |
|---|---|
| Deterministic routing policy with full traces | Model-backed signal extraction |
| Safety gate with preemption + session monitors | Response generation of any kind |
| Declarative roster with load-time validation | Persistent cross-session memory |
| 43 tests, no network or API key required | Multi-turn conversational state beyond monitors |

This repository is the **policy layer only**. It decides who should respond and
whether anyone should. It does not generate responses, and it is not a chatbot.
That boundary is deliberate: the routing and safety logic is the part that
should be auditable, and it is the part that stays stable while the underlying
model is replaced.

### Roadmap

- [ ] Pluggable classifier backend behind the `RequestSignals` contract
- [ ] Adapter examples for common orchestration frameworks
- [ ] Routing-decision evaluation set with labeled expected outcomes
- [ ] Structured JSON decision logs for post-hoc audit

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
