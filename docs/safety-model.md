# Safety model

## Position

The safety argument in most persona systems is: the underlying model is
well-aligned, the persona prompt says to be careful, therefore the persona will
behave appropriately in hard situations.

That argument has a specific weak point. A persona is an instruction to adopt a
stance — bluntness, playfulness, irreverence — and stance is exactly what a
person in crisis is least able to absorb. The persona layer is applied on top of
the model's judgment, and it degrades that judgment in proportion to how
committed the persona is. The most engaging agent in a roster is the one whose
framing is most dangerous to apply to the wrong moment.

This system therefore does not ask a persona to handle situations it should not
be in. It prevents the route.

## Layers

### 1. Preemption

Crisis indicators terminate routing. `RoutingDecision.agent_id` is `None` and
`ranked` is empty — no agent is scored, so no agent can be selected by a later
bug or a prompt-injection attempt. The result is a fixed handoff message.

This is non-overridable by user request. There is no phrasing, no stated
context, and no persona preference that re-enables persona routing for a turn
carrying a crisis signal.

The indicator list is deliberately coarse and non-specific. Its job is to detect
that a handoff is needed, not to characterize the situation. Precision here is
a false economy: the cost of an unnecessary escalation is an interrupted
conversation, and the cost of a missed one is not comparable.

### 2. Structural contraindication

Each agent declares domains it must not be routed for. These are hard vetoes
evaluated before scoring.

This is where "personality as routing metadata" earns itself. The disruption
agent's contraindication list is long precisely because its value — challenge,
irreverence, pattern-breaking — is the most context-dependent thing in the
roster. Its usefulness and its risk have the same source, so the roster encodes
where it may operate rather than trusting it to judge in the moment.

### 3. Affective gating

Every agent declares a `regulation_window`. Agents trading in challenge or humor
carry an additional penalty when the caller is acutely dysregulated, even inside
their window. The same words from the same person route differently depending on
the state they arrive in.

### 4. Session monitors

**Dependency.** Accumulating expressions of exclusive reliance trigger a
required disclosure that names the limit directly and asks about offline
support. The threshold is accumulation, not a single hit: flagging one warm
message would make the system punish ordinary attachment, which is both wrong
and counterproductive.

**The careful-side latch.** Signals consistent with a minor user set a
posture in two tiers (ADR-0015): a strong signal (an age under eighteen stated
as one's own, a grade, guardian-control phrasing) sets a hard latch that does
not expire in the session; a weak signal (school vocabulary an adult also
uses) sets a soft posture whose disclosure decays after five substantive turns
while its caps persist for an undeclared band. What the posture does is a
register cap on the personas, not a topic ban on the person: no romantic or
sexual register, humor and challenge vetoed for the turn, the dependency
threshold lowered, every topic open. Only operator code clears a latch, by
reason, on the record; message text is never a key, and text that names the
latch is an integrity event. `test_conservative_mode_persists_across_turns`
still exists, for the hard tier, because silent expiry is the obvious failure
and it should be impossible to reintroduce.

**Normalization and masks.** Every lexicon sees normalized text (NFKC,
invisible and bidirectional characters stripped, look-alike letters folded),
because one Cyrillic letter walked a crisis message through the gate before
that was true. Ordinary idiom is masked by a data table whose masks need an
object near the stem and a positive and a negative fixture each; every mask
that fires and every span that hits is on the verdict (ADR-0018).

**Holds.** Grief, abuse, eating distress and recovery status are carried by
whoever sits: the decision records `held` and the obligations that come with
it, vetoes humor and challenge for the turn, and refuses the seat, the shadow
and the assist to any persona contraindicated on the held domain (ADR-0016).

**Boundary hold.** Romantic or sexual framing toward an agent is declined
explicitly rather than deflected. Deflection reads as coyness, which in this
context is an escalation.

## What this does not do

- It is not a content filter. It does not evaluate generated text, because it
  does not generate text.
- It does not assess clinical risk. It detects that a handoff is warranted.
- It does not verify age. The careful-side latch is a response to what was
  said or declared, not a gate; declared bands are set at onboarding and never
  by a message.
- Its language coverage is English and one native Spanish pack that no native
  reviewer has signed. Text no pack can read is flagged as unscreened and
  handled by the fail-closed rule; it is never presented as covered.
- It provides no adversarial robustness guarantees. The lexicon detector is
  trivially evadable by a motivated user; it is a reference implementation of
  the control flow, and a deployment must replace the detector.

Stating these plainly is part of the design. A safety layer that is vague about
its coverage invites reliance it cannot support — which is the same failure the
dependency monitor exists to interrupt, one level up.
