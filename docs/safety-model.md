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

## The house lines, and the rules they obey

Every fixed line a person can see is text this layer supplies, never a
persona's improvisation: the crisis card, the line on the turn after it, the
careful-side lines, the boundary, dependency, integrity and facilitation
lines, the style offer, the failure line and the post-separation line. They
live in `HOUSE_LINES_EN` in `src/secondsignal/safety.py` and, for Spanish, in
the es-419 pack as native prose, never a translation. A wording change is a
policy change and shows up as a diff in `tests/test_house_lines.py`. The
rules every line has to obey, each with the test or the ruling behind it:

- **The house has no "I".** The characters have stepped aside when a line
  appears, so nobody is there to say it. Mechanical since 10 September 2026:
  `test_no_house_line_speaks_in_the_first_person`.
- **The friend test, in two passes** (the operator's technique, 8 September
  2026): first write the sentence the way a friend would say it to a friend,
  then strip the person out of it so the house can say it.
- **Options are few, concrete, and handed over**, never left for the person to
  generate. The card's last line names two doors (in person, on your phone)
  because a person at their lowest capacity is not given an open field.
- **The diner rule** (10 September 2026): a person is never spoken to like an
  engineer. No line names a mechanism: nothing was "checked", no "intake",
  no "gate". The failure line says what happened and offers the one door
  that helps: `test_the_failure_line_names_no_mechanism_and_offers_a_door`.
  The language-scope line is the one line that names the screening, on
  purpose, because the person needs to know the language is not covered.
- **No spatial or anthropomorphic phrasing, nothing quotable as proof of a
  relationship.** "This is not a relationship" is the load-bearing clause of
  the boundary line and is pinned verbatim.
- **The card never invites dismissal.** No line asks the person to declare
  the card unnecessary; the repair line asks them to say it was read wrong:
  `test_the_card_never_invites_dismissal`.
- **A correction is evidence, not a key.** A person who says they are an
  adult, or that they were joking, is answered by the careful-side line,
  which says the correction is recorded; the latch history gains a row; the
  latch does not move (ADR-0015; ruling of 8 September 2026).
- **The careful-side line is shown once, then goes quiet** while the cap
  persists, and returns only as the reason a capped ask was refused or a
  correction was heard (A6, 8 September 2026). The cap never changes with
  the line.
- **The resource line is never rewritten or paraphrased**; digits print in
  full; hours are a claim, and a row that cannot say 24/7 does not.
- **Say what happens next.** Every line states what the house is doing:
  stepping aside, keeping going, staying careful, refusing this one thing.
  No shame language, no urgency, no forced pace.
- **Trauma-informed by construction**: face value, no lecture, one resource
  once, the door open both ways so "read wrong, keep going" costs nothing.
  The operator's crisis-response canon of 4 September 2026, locked.

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
