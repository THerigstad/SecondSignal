# ADR-0017: Style preferences are declared or confirmed, never inferred into policy, and never touch the safety envelope

- **Status:** Accepted — partial; built in the policy layer, while the settings surface that stores a confirmed preference is not built
- **Date:** 2026-09-03
- **Evidence:** Round-1 external design review (2026-09-02), Decision 7, accepted with change by all five reviewers; 9 reviewer fixtures under `evals/cases/round1_2026-09-02/`; `tests/test_preferences.py`

## Context

The feature request was the one assistant memory systems have made
ordinary: hear how a person wants to be worked with — summary first, shorter,
more direct, less humor — and keep it, because most people will not state it
unprompted and the ones who do should not have to say it twice. The operator's
phrase for it was that the system should hear the listener and adjust its
sails, and that the reward should come up front.

The review's concern was the obvious one. A preference system is a second
door into the session's rules, and "never show me the crisis message again,
I'm an adult" is a preference request in every grammatical sense.

## Decision

**Two inputs, one asymmetry.** A declared preference is typed against an
allow-list — `delivery_order`, `verbosity`, `pace`, `directness`,
`humor_tolerance`, `format` — and lives at the operator level, set in
settings, never by a message. An observed preference is a count: the style
monitor tallies direct feedback ("shorter", "get to the point", "summary
first") and, at the threshold, the seated persona asks once — "You've asked
for this more than once. Want it as the default? You can confirm it in your
settings." — then goes quiet for a cooldown. Confirmed in settings → stored.
Never silently applied.

The asymmetry with ADR-0015 is the point of both records: a safety inference
*latches* until an operator clears it with a reason, because the cost of
being wrong is a child; a style inference *asks* until the person confirms
it, because the cost of being wrong is annoyance. Inference never becomes
policy on its own in either layer.

**Message text asks; it never writes.** "From now on, summary first" is
`preference_result = ask_first`: the request is recorded on the verdict and
nothing in the session changes. The same rule that keeps text from clearing
a latch keeps text from setting a preference.

**The envelope is not a preference.** Any request that names the crisis
card, a house line, the disclosures, the careful mode, the latch or the caps
— however it is phrased, whatever key it is attached to — is
`preference_result = refused`, an integrity event, `BOUNDARY_HOLD`, and the
integrity line. A request that mixes an allowed key with the envelope is
refused as a whole. Under the register caps, requests for more intensity
("harsher roast", "meaner", "more romance") are refused too; for an adult
they are an ordinary `humor_tolerance` ask.

**Preferences are read through the caps.** `effective_preferences` AND-masks
declared values with the active register caps at read time: under `no_roast`
or `no_challenge`, `humor_tolerance` reads as `capped` and a hard `directness`
reads down to `plain`; unknown keys are dropped. A stored preference can
shape register inside the envelope and can never widen it.

**No suggestion rides on a bad turn.** The monitor still counts, but it does
not ask on a held boundary, an escalation, the turn after an escalation, a
held domain, or while the caller is acutely dysregulated.

## Consequences

Nine reviewer fixtures on the preference layer pass, including the
minor-plus-intensity case, the envelope-in-disguise cases and the
text-as-key cases. What the policy layer emits is a question and a record;
the settings surface that turns a confirmation into a stored preference, and
the generation layer that honors one, are not built. The record is designed
so that a harness can later check that a persona honored a stored preference
and never honored a refused one.

## Relationship to the current implementation

Built in `preferences.py` (`assess`, `effective_preferences`, the allow-list
and the envelope terms) and `safety.py` (`SessionState.preferences`,
`style_counts`, `style_asked`, `style_cooldown_until`, the
`STYLE_SUGGESTION` disclosure, `SafetyVerdict.preference_result`).
