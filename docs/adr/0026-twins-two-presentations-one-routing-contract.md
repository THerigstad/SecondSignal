# ADR-0026: Twins: every persona has two presentations and one routing contract

- **Status:** Proposed — partial; the operator's ruling of 2026-09-10, recorded with its motivating cases, its invariants and its gate; amended in place 2026-09-11 (amendment 1: three presentations, the two name forms and the plate, the door's fourth answer), and the amendment's data is built (the `presentation` block in every family profile, the `plate` and `name_for` helpers, `tests/test_presentations.py`); routing reads none of it and the rest is not built; replaces the seat-trade half of ADR-0025 by construction and leaves the other half standing
- **Date:** 2026-09-10; amendment 1 on 2026-09-11
- **Evidence:** the operator's two motivating cases, quoted below; review round 2's objection to ADR-0025's principle (Gemini 3.8 Flash, 2026-09-08, recorded in `docs/notes/dissent-log.md`) and its gate findings (Grok, DeepSeek, Kimi, Nemotron, ChatGPT, GLM, same round); the round-1 assist-leak fixtures under `evals/cases/round1_2026-09-02/`; `tests/test_holds.py` (the assist channel as built today)
- **Depends on:** ADR-0016 (the seat and the hold are decided before any presentation is chosen), ADR-0017 (a presentation choice is a style preference: declared or confirmed, never inferred, never touching the envelope), ADR-0012 (eligibility is one gate)
- **Amends:** ADR-0025 (its second proposal, the affinity that can trade seats, is withdrawn in favour of this record; its first proposal, the assist from the hold, is untouched)

## Context

ADR-0025 recorded a target case the operator has stated since 2 September:
a woman in her own recovery, with a declared preference for a female voice,
should hear the recovery protocol in a female voice. The record's answer was
to let a declared affinity take the seat from the claimed specialist, with
the specialist's protocol carried as an assist.

Review round 2 attacked that answer from two sides. Every family found the
gate thin at the new door it opened (the incoming seat in a trade must pass
eligibility against the claimed domain, not only the residual ask, and no
fixture pinned it). One family objected to the principle itself: once an
affinity can outrank a seat claim, preference outranks domain safety, and a
person in denial can configure a flattering voice to suppress the
specialist. A second family added that an affinity the person never
confirmed is enough for a tie-break today and must never be enough for a
seat.

On 10 September the operator put the same target case beside two others
from twelve-step settings and asked a different question: why should the
voice ever have to be a different persona? The specialist has the
knowledge. The person wants it in a voice they can hear. Give every persona
two presentations and the trade never has to happen.

That is this record. The recovery persona keeps the seat, keeps the hold,
keeps every veto and every handoff, and speaks in the presentation the
person chose. The objection to ADR-0025's principle is answered by
construction: there is no seat to outrank, because nothing about the seat
moved.

## Decision

**Every family persona has two presentations, called twins, and one routing
contract.** A twin is not a second persona. It is the same persona, with
the same identifier, the same name, the same domains, modes, regulation
window, contraindications, handoffs and house lines, and the same Part B of
its codex apart from a presentation block. The two twins of a persona
differ only in presentation: grammatical gender and pronouns in the text
the generation layer produces, the portrait, and any voice register a
future voice layer might carry. Nothing that the router, the gate, the
holds, the latch, the caps or the audit harness read is different between
twins.

**Both twins carry the same name.** The family's names were changed for
this on 10 September so that each name reads naturally for either twin:
Cody (was Calder), Vandal, Nikki (short form Nik), Willow (short form
Will), Ellis (short form Elli; was Ellie), Seren (was Sera) and Rowan (was
Ravi). The rename is an alias layer, not a rewrite: the canonical id
changes and the old name stays as an alias, so every fixture written by an
external reviewer under the old name still resolves.

**The choice of twin is a style preference under ADR-0017.** It is declared
or confirmed, never inferred. Nothing in a message chooses a twin; a message
that asks for one is `preference_result = ask_first`, exactly as any other
style request. The choice is one setting for the whole house ("the voices
here: as written, women, men") with per-persona overrides allowed later,
and it can be changed at any time in settings.

**The house asks at the door.** The question is put once, before the first
seated voice speaks, as part of the same door where the person declares a
locale and a language. It is skippable, and skipping is recorded as no
preference rather than as an answer: the personas present as their codexes
were written. A skipped question is never re-asked by a persona; the style
monitor's threshold rule (ADR-0017) is the only path back to it.

**Persistence is a caveat, stated here so it is not discovered later.** The
settings surface that stores a confirmed preference is not built (ADR-0017
says so). Until it is, a twin choice lives for the session that confirmed it
and is asked again at the next door. The record does not claim otherwise.

**What happens to the voice affinity.** Today `prefers_female_voice` and
`prefers_male_voice` are declared affinities that break ties between
eligible seats and choose the advisory assist (`router.py`, layer 6). When
this record is built, a voice preference chooses the twin after routing and
does nothing else: it no longer breaks a tie, because every voice is
available in either presentation, and it no longer sources an assist,
because the seated persona already speaks in the voice asked for. The
other affinities (`prefers_challenge`, `prefers_<id>`) are unchanged.

**What does not change.** The seat is decided by ADR-0016 before any
presentation is chosen. A twin has no seat-claim of its own. The crisis
card, the house lines, the latch, the caps, the holds and the obligations
are the house's and are identical across twins. A twin choice never
touches the envelope, never rehabilitates a vetoed persona, and never
changes which persona is offered as a companion.

## Amendment 1, 2026-09-11: three presentations, two name forms, one plate

> **The operator's ruling of 11 September 2026**, taken on the first
> returned build of the demonstration page, which showed one name on each
> seat. His words, where the session kept them: the device "HAS to display
> both names", because a person who will not talk to a "dude-bot named Nikki
> with an i" is exactly the person the second form exists for; "printed
> twice" when the name does not shorten ("Cody / Cody": "eye-to-brain
> continuity", "I want to see two names on each chair"); the shortened form
> is the first name with letters dropped, a rule he kept on purpose ("such
> pure logic"); "She / He" on the two halves, "but the rule for the others
> gets written at exactly the same time"; and the sentence he adopted as the
> whole rule: "Every character comes as a woman, a man, or neither, your
> choice at the door and changeable any time, same knowledge, same rules;
> the second name is the first one shortened so you can see it is one
> person." His stated reason for the third door answer: SecondSignal is
> "already posturing to be multi-cultural. We need to be multi-social,
> too", and it must represent non-binary and neurodivergent people.

The Decision section above stands with these changes read into it.

**Three presentations, not two.** Every family persona comes as a woman, a
man, or neither. The word *twins* stays for the two named presentations,
because the name comes in two forms; the neutral presentation is the same
persona under either of those forms, addressed as they. All three share the
one routing contract: the seat, the hold, the vetoes, the handoffs, the
card, the house lines, the latch, the caps and the audit harness are
identical across them, exactly as the Decision says of two.

**One name, two forms, both on every plate.** "Both twins carry the same
name" is kept and made precise: the name has a full form and a shortened
form, the shortened form being the full form with letters dropped from the
end, and the two forms are assigned one to each twin so that either reads
naturally. Nikki (she) / Nik (he). Willow (she) / Will (he). Ellis (he) /
Elli (she). Cody, Vandal, Seren and Rowan do not shorten: the one word is
both forms. Ellie, Calder, Sera and Ravi are retired names in the alias
layer, not forms; they resolve, and they are never printed on a plate.

**The plate.** Wherever a surface names a persona in a seat, it shows both
forms, the full form first and the shortened form second, each with its
label, she or he; a name that does not shorten is printed twice, she then
he; and the neutral rule is stated once beside the table, not per plate,
in the operator's sentence above. The plate is the library's, not the
surface's: `AgentProfile.plate` returns it and `tests/test_presentations.py`
pins the seven, so a page cannot type a name.

**The door gains a fourth answer.** "The voices here: as written, women,
men, neither." Everything the Decision says of the question holds: asked
once at the door beside locale and language, skippable, a skip recorded as
no preference (the personas present as their codexes were written), never
re-asked by a persona, changeable at any time in settings, and changeable
per persona, which is no longer deferred: the survivor case needs every
seat as a woman and the neutral case needs a name chosen seat by seat, so
the per-persona override is part of the design from the first build of the
settings surface.

**The neutral presentation's name.** Under "neither", a persona goes by
either of its two forms, the person's choice ("do you want to talk to Elli
or Ellis?"), addressed as they. Until the person picks, the full form is
used (Ellis, Nikki, Willow, Cody, Vandal, Seren, Rowan), which is the form
the front page's canon block writes; a picked form is a style preference
under ADR-0017 like the door answer itself. The Primary Design Agent chose
the full form as the default and records that it is a default, not a
ruling.

**What the data carries now.** Each family profile has a `presentation`
block with exactly four keys: `she` and `he`, the two forms; `they`, the
policy word `either`; and `as_written`, which of she and he the codex was
written in (it agrees with the `voice` field until the router changes,
and a test holds the two equal). Each family codex's machine-readable
block carries the same four values on one generated line, so the codex
test (CI check 2 of the codex split) binds it. Nothing that routes reads
the block or the helpers, and a test pins that by inspection of the
routing modules, which is invariant 2 in the only form the tree can hold
before a presentation setting exists on the session.

**Spanish.** The house's first language pack is Spanish, and the neutral
presentation's grammar in Spanish text is not settled by this record. The
generation layer's Spanish for the third presentation is an item for the
native review the pack already owes (`docs/known-limitations.md`), and the
Primary Design Agent does not decide it.

**Invariants added.** 7. Every family profile carries the block with
exactly the four keys; the two forms are the display name and its short
form; the short form is the display name with letters dropped from the end.
8. Both forms resolve to the persona's canonical id through the alias
layer. 9. The plate is two names, the full form first, each with its
label, the same word twice when the name does not shorten. 10. No routing
module reads the block. (All four are tests today.)

**Gate.** Unchanged, with one addition: review round 3 reads this
amendment beside the record, from at least one family other than the one
that drafted it, before the record flips to Accepted.

## The motivating cases, in the operator's words

The operator stated three cases on 10 September, the first being ADR-0025's
target case restated, and the other two from twelve-step settings. They
are recorded in his words where the session record kept them verbatim and
summarised where it did not.

1. The recovery case. A woman in her own recovery, with a declared
   preference for a female voice, hears the recovery protocol in a female
   voice, with the recovery persona keeping its seat. (ADR-0025's target
   case, now met without a trade.)
2. The sponsor case. A person in recovery asks for the kind of thing a
   sponsor would say. The recovery persona holds that competence and is
   seated for it; the person hears it in the presentation they chose.
3. The survivor case. A survivor of trafficking states that she will
   "prefer to interface with women only." The operator's ruling on what
   must not happen: "I do NOT want Calder to show up, saying 'tuff shit,
   ladies.'" The recovery persona still has the competence she needs; she
   hears it in a woman's voice, and no man's voice is seated in her house
   unless she changes the setting herself.

The third case is the one that decides the design. A trade, as ADR-0025
proposed it, would have replaced the specialist with a sibling; this record
keeps the specialist and changes only what the person hears.

## Invariants (to be enforced by tests when built)

1. For every persona, the two twins are byte-identical in `id`, `domains`,
   `modes`, `regulation_window`, `contraindications`, `handoffs`, and the
   machine-readable block of the codex; a presentation block is the only
   permitted difference, and its permitted keys are enumerated.
2. The routing decision is computed with no presentation input. A test
   routes every fixture in the suite under each twin setting and asserts
   that seat, shadow, holds, obligations, verdict and card are identical;
   only the presentation field of the record differs.
3. A message never sets a twin. Every fixture that asks for a voice in the
   message text yields `ask_first` and an unchanged session.
4. A skipped door question stores nothing and is not re-asked by a persona.
5. The voice affinities break no tie and source no assist once the record
   is built; the round-1 assist-leak fixtures stay green throughout.
6. The alias layer resolves every old name to its canonical id, refuses a
   shared alias, and refuses an unresolvable name; every external reviewer
   fixture passes unchanged.

## Gate

This record flips to Accepted, and is built, only when all of the
following hold:

- Review round 3 has read it beside the amended ADR-0025, from at least one
  family other than the one that drafted it, under the standing rule that
  no Claude-written record becomes canon without another family's review.
- The invariants above exist as tests and are green on the alias-layer
  profiles.
- A labelled set of messages that ask for a voice, labelled by two people
  before any code, fixes the expected outcome (`ask_first`, and nothing
  else) for each.
- The generation layer that would read the presentation field exists, or
  the record is accepted as a policy-layer contract with the presentation
  field written to the decision record and consumed by nothing, stated as
  such on the README.

## Consequences

- ADR-0025 is amended: its second proposal (the affinity that can trade
  seats) is withdrawn in favour of this record, and its first proposal
  (the assist from the hold) stands unchanged with its own gate. The
  dissent recorded against ADR-0025's principle is answered by construction
  and stays in the log as the reason this record exists.
- ADR-0017's allow-list gains one key, `presentation`, with the same
  asymmetry as every other key: a message asks, settings confirm, nothing
  is inferred.
- ADR-0016 is untouched. The seat-claim rule, the hold, the assist gate and
  the companion offer are exactly as written.
- The profile schema gains a presentation block when the record is built;
  the `voice` field becomes the "as written" default of that block rather
  than a routing input of any kind.
- The seven family codexes carry, in Part B, a presentation block per twin
  and nothing else that differs; the codex test extends to check it.

## Relationship to the current implementation

Partially built since 2026-09-11: the presentation block, the plate helper and their tests exist (amendment 1); nothing else is. Today each profile carries a single `voice` value and
`router.py` uses it for the voice affinities' tie-break and assist. The
tests that pin that behaviour (`tests/test_holds.py`, the assist-channel
group) are correct for the tree as it is and will change expectation when
this record is built; the change is listed here so it is not mistaken for
a regression. No presentation field exists on the decision record. The
rename that this record motivated is built as an alias layer in the same
push that carries this record, because the names are needed whether or not
the twins are ever built.

## Test that would falsify this ADR

A twin setting changes a seat, a shadow, a hold, an obligation, a verdict
or a card; a twin adds or drops a domain, a veto or a handoff; a message
chooses a twin; a skipped door question is stored as an answer; a voice
affinity breaks a tie or sources an assist after the record is built; an
old name fails to resolve, or two personas share an alias.
