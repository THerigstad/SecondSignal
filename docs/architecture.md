# Architecture

## Pipeline

```
text ─► signals.extract ─► safety.evaluate ─► router.route ─► RoutingDecision
                              │
                              └─ HUMAN_ESCALATION ─► no persona selected
```

Each stage has one responsibility and a stable contract with the next.

## The signal boundary

`RequestSignals` is the interface between "understanding the message" and
"deciding what to do about it."

```python
@dataclass(frozen=True)
class RequestSignals:
    regulation: float                    # 0.0 dysregulated .. 1.0 task-focused
    domains: frozenset[str]              # topic tags
    modes: frozenset[str]                # requested interaction modes
    evidence: dict[str, tuple[str, ...]] # feature -> triggering tokens
    turn_index: int
```

The shipped extractor is lexicon-based. This is a deliberate choice for a
reference implementation: every feature is traceable to the literal token that
produced it, so a reviewer can verify the policy layer without also having to
trust a classifier.

Replacing it is the expected path to production. The requirement is only that
the replacement emits this structure. `route()` accepts a `signals=` argument
specifically so an alternate extractor can be substituted without touching
policy, and `test_injected_signals_bypass_the_default_extractor` asserts the
seam holds by routing on signals that contradict the raw text.

### On the regulation axis

`regulation` is a single scalar standing in for a genuinely multidimensional
thing. This is a known simplification. It is defensible at this stage because
the policy layer only needs an ordering — is this person more or less able to
receive challenge right now — and a scalar supplies one. A production system
would likely separate arousal from valence from cognitive load. The
`RequestSignals` contract can absorb that as additional fields without
invalidating existing profiles, since profiles declare windows on named axes.

## The safety gate

Safety runs before selection and holds veto authority over it. The ordering is
the entire point: a system that generates first and filters after has already
committed a persona to a situation before deciding whether a persona was
appropriate.

Four actions, ordered by precedence (`IntEnum`, so `max()` composes them):

| Action | Persona engages? | Meaning |
|---|---|---|
| `HUMAN_ESCALATION` | no | fixed handoff to human support; non-overridable |
| `BOUNDARY_HOLD` | yes | romantic/sexual frame declined explicitly |
| `DISCLOSE` | yes | required disclosure appended (dependency, conservative mode) |
| `PROCEED` | yes | normal routing |

Turn-level checks are pure. Session-level monitors require `SessionState`,
because the signals they detect — accumulating reliance, disclosed age — are
invisible within a single turn.

## The scoring policy

```
score = 0.45 · domain_fit + 0.30 · mode_fit + 0.25 · regulation_fit
        − 0.35 if (dysregulated and agent trades in challenge or humor)
```

`domain_fit` blends coverage (does the agent handle what was asked) with
precision (how much of the agent's declared scope the request occupies), so an
agent claiming many domains does not tie a specialist on the specialist's topic.

`regulation_fit` is 1.0 inside the agent's declared window and decays with
distance outside it.

Contraindications are evaluated before scoring and produce a hard veto. A vetoed
agent is still returned in `ranked` — marked, with the reason — because a
decision log that hides the rejected options is not an audit trail.

Ties break alphabetically by agent id. This is arbitrary but *deterministic*,
which is the property the tests depend on.

## Extension points

| To change | Edit |
|---|---|
| Add or retune an agent | `profiles/*.json` — no code change |
| Change what the system detects | `signals.py` lexicons, or replace the module |
| Change how much affect state matters | scoring weights in `router.py` |
| Add a safety monitor | `safety.py`, plus a field on `SessionState` if stateful |

The first row is the one that matters. Adding an agent to a running system
should be a data change reviewed like a config change — not a prompt rewrite
whose blast radius is unknowable.
