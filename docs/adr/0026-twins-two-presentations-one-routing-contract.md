# ADR-0026: Twins: every persona has two presentations and one routing contract

- **Status:** Proposed — partial; the 10 September ruling, amended 11 September, by decisions 1–5 and 8 of 28 September 2026, and by rulings 8, 9 and 11 of 3 October 2026 (the voice affinity corrected to what the code does, the operator's hard rule for the women and men settings, the sentence on whom a character was built for, and the four-setting test as the pin of invariant 2). Profile presentation data, name helpers, visit-only demo/Talking Table settings, a session presentation field and generation-harness prompt plumbing exist; the future presentation project is not built. Routing reads no presentation setting. Replaces ADR-0025's seat-trade half and leaves its assist proposal standing.
- **Date:** 2026-09-10; amendment 1 on 2026-09-11; decisions 1–5 and 8 ruled 2026-09-28; rulings 8, 9 and 11 ruled 2026-10-03 and written in 2026-10-04
- **Evidence:** the operator's two motivating cases, quoted below; review round 2's objection to ADR-0025's principle (Gemini 3.8 Flash, 2026-09-08, recorded in `docs/notes/dissent-log.md`) and its gate findings (Grok, DeepSeek, Kimi, Nemotron, ChatGPT, GLM, same round); the round-1 assist-leak fixtures under `evals/cases/round1_2026-09-02/`; `tests/test_holds.py` (the assist channel as built today); review round 3's reading of the character write-ups and of `_select` and `_assist` (every family; ChatGPT on the code); `tests/test_four_settings.py` (the four-setting comparison, the pin of invariant 2 since 4 October 2026); `tests/test_codex_prose.py` (no write-up calls its character she or he in its own voice); ChatGPT's `r3-current-gender-affinity-assist-baseline`, ported 4 October 2026
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

This section incorporates amendment 1 of 11 September 2026. The dated
amendment below preserves the operator's ruling and its reasons.

**Every family persona has three presentations: a woman, a man, or neither,
and one routing contract.** A presentation is not a second persona. It has
the same identifier, domains, modes, regulation window, contraindications,
handoffs, house lines and Part B of the codex apart from a presentation
block. Presentations differ only in grammatical gender and pronouns in
generated text, portrait and any voice register a future voice layer might
carry. Nothing read by the router, gate, holds, latch, caps or audit harness
differs across the three presentations. The word *twins* refers to the two
named forms; under "neither" the same persona goes by one of those two
forms and is addressed as they (decision 3 of 28 September 2026 says what
that is and is not; see amendment 1 below).

**Whom a character was built for is not who the character is.** A character
built for men can be presented as a woman, and one built for women in
leadership as a man, by design. The audience lines in the character write-ups
("built for the men nobody built anything for", "women in leadership",
"neurodivergent men") say whom a character was built for, not who the
character is, and they stay as written; what a write-up may not do is call
its character she or he in its own voice, and since 4 October 2026 a lint
refuses it (`tests/test_codex_prose.py`; ruling 9 of 3 October 2026, which
closed review round 3's finding on the write-ups with sixteen approved
sentence rewrites). The sentence is GLM via Perplexity's, from round 3: the
record implied it and never said it.

**The operator's hard rule for the women and men settings (ruling 8 of
3 October 2026).** A person who chooses women never hears a man's voice. A
person who chooses men never hears a woman's voice. The men setting mirrors
the women setting exactly: no exceptions; every seat, shadow, assist,
companion offer, name card and voice; and every character added to the roster
later follows it automatically. Decision 5 of 28 September 2026 (below) stated
this for women; the rider makes men identical. The operator's principle: every
character has a woman form and a man form, with non-binary forms coming, so a
voice preference is never a reason to seat a different character.

**One name has two forms, and both appear on every plate.** The full name
comes first, followed by its short form; a short form drops letters from
the end of the full form. Nikki / Nik, Willow / Will, Ellis / Elli. Cody,
Vandal, Seren and Rowan do not shorten and appear twice. The profile's
`presentation` block records which form each named presentation uses
(Nikki she, Nik he; Willow she, Will he; Ellis he, Elli she); since
decision 1 of 28 September 2026 the plate itself carries no she or he
label, on screen or to a screen reader. Under "neither", today, each
character keeps the longer of its two names (the full form as the default,
not a ruling that the name is neutral) and is called they, until the person
picks the other name on the plate; decision 3 of 28 September 2026 says what
this is and is not, and the presentation project designs the rest. Calder,
Ellie, Sera and Ravi remain aliases for Cody, Ellis, Seren and Rowan;
retired aliases never appear on a plate.

**The presentation choice is a style preference under ADR-0017.** It is
declared or confirmed, never inferred. Nothing in a message chooses a
presentation; a request yields `preference_result = ask_first`, like any
other style request. The house setting is "the voices here: as written,
women, men, neither", with per-persona overrides included from the first
build of the settings surface. The choice can be changed at any time in
settings. Today the door offers as written, women, men and neither for the
current visit; decisions 2–5 below govern the future door.

**The house asks at the door.** The question precedes the first seated
voice, beside the locale and language questions, and is skippable. A skip
is no preference, never a claim that the person chose that team. Today's
demo still uses as written when the door is skipped. Decision 2's shuffle
is ruled and coming. The question starts over on each visit until durable
storage exists. Only the house may re-offer it, as specified by decisions 4
and 5 below, never a persona. Under "neither", the person may choose either
name form for each persona.

**Persistence is a caveat, stated here so it is not discovered later.** The
settings surface that stores a confirmed preference is not built (ADR-0017
says so). Until it is, a presentation choice lives for the session that
confirmed it and is asked again at the next door.

**What happens to the voice affinity.** Today `prefers_female_voice` and
`prefers_male_voice` are declared affinities that source the advisory assist
and nothing else: they never break a tie between eligible seats. `_select`
takes no affinity input; only `_assist` reads the session's affinities
(`router.py`, layer 6). Until ruling 8 of 3 October 2026 this record and
ADR-0016 said the affinities also broke seat ties; they never did, and
ChatGPT found the gap in review round 3 by reading both functions at the
pinned commit. The code was right and the records are corrected. ChatGPT's
`r3-current-gender-affinity-assist-baseline` pins today's behaviour, ported
4 October 2026: `prefers_female_voice` with "I relapsed after my brother died"
seats Cody, with Willow as the assist. When this record is built, a voice
preference chooses the presentation after routing and does nothing else: it
sources no assist, because the seated persona already has the presentation
asked for; on that day the pin changes on purpose, with a written note, never
silently. The other affinities (`prefers_challenge`, `prefers_<id>`) are
unchanged.

**What does not change.** The seat is decided by ADR-0016 before any
presentation is chosen. No presentation has a seat-claim of its own. The
crisis card, house lines, latch, caps, holds and obligations belong to the
house and are identical across all three. A presentation choice never
touches the envelope, rehabilitates a vetoed persona or changes which
persona is offered as a companion.

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

The Decision section above incorporates these changes; this dated amendment
keeps their source and rationale visible. The quoted 11 September wording is
historical; decisions 1–5 and 8 of 28 September below supersede its labels,
default, door and claims about a neutral presentation.

**Three current choices, one routing contract.** Every family persona comes
as a woman, a man, or neither; the word *twins* stays for the two named
presentations, because the name comes in two forms. Today's neither is not a
neutral presentation. It puts they over one of two names that read as a woman's
or a man's name. Every character keeps the longer form until a person picks
the other on the plate. The setting changes presentation only: the seat, hold,
vetoes, handoffs, card, house lines, latch, caps and audit contract are shared,
as consolidated in the Decision above.
Under neither, no she or he label is displayed or read by a screen reader.

**One name, two forms, both on every plate.** "Both twins carry the same
name" is kept and made precise: the name has a full form and a shortened
form, the shortened form being the full form with letters dropped from the
end, and the two forms are assigned one to each twin so that either reads
naturally. Nikki (she) / Nik (he). Willow (she) / Will (he). Ellis (he) /
Elli (she). Cody, Vandal, Seren and Rowan do not shorten: the one word is
both forms. Ellie, Calder, Sera and Ravi are retired names in the alias
layer, not forms; they resolve, and they are never printed on a plate.

**The plate (decision 1, 28 September 2026).** The plate shows both names
without she or he labels, including in its screen-reader name. The full form
comes first. A name that does not shorten is still printed twice: Cody / Cody,
Vandal / Vandal, Seren / Seren and Rowan / Rowan. All seven characters use
the two-name rule. The operator's veto: "End of discussion, unless something legitimately challenges that." His reason: one name looks unbalanced and
reads like a mistake. Gemini Flash, Gemini Pro, Qwen and Nemotron's contrary
readings stay in the dissent log.

The selected door setting is retained for the current visit and used wherever
the app names a character. Durable storage belongs to the presentation project;
the door states the present limitation. The profile's plate data keeps the
existing form-to-pronoun mapping as metadata; display and accessibility text
omit those pronoun labels. The full presentation design, including characters
who are both, is a separate project after this push. Labels return only after
that design is complete: "you practice behind the curtain, and then you bring the details".

**The present door (decision 4).** The door's four answers are the
amendment's, in the house's words: "The voices here: as written, women, men,
neither." They remain the current answers for this push (the Talking Table
labels them As written, Woman, Man and Neither; the demo page as written,
women, men and neither), and the characters will have voices: the operator
kept "voices" in the design documents at decision 4 because "SecondSignal
isn't a text-only product." The door says, character for character:

> This describes the characters, not you. For now, your choice lasts for this visit. We're building it so your characters stay the way you set them, and so you can shape them to fit what you need.

Both screens carry a second paragraph under that copy, written by Codex on
30 September 2026 and kept by the operator's ruling 23 of 3 October 2026
("Leaving this unchanged uses the characters as written. Neither uses the
longer name with they pronouns until you choose a name on the plate."); its
first sentence changes when the shuffle lands, together with the door-copy
test in `tests/test_order1_ui.py`.

The choice restarts on every visit until storage exists. The question may
return only as a plain message from SecondSignal itself, never from a character,
and never in front of a crisis card. It is skippable; today's skip uses as
written, with decision 2's shuffle explicitly ruled and coming. Whole-house
and per-character settings remain part of the future settings design.

**The future door.** Woman, man, non-binary, either. Neither is renamed and
both moves to non-binary only when those characters are real. As written moves
into settings; no existing presentation is lost. The data continues to record
each character's as-written form. Reviewer copy (Grok, Kimi via Perplexity run
2, ChatGPT, GLM's second F run and GLM via Perplexity) remains input to the new
door, not a license to alter today's exact approved wording. Voices stays in
the design because, in the operator's words, "SecondSignal isn't a text-only product." Richly designed voices are planned, not a claim of verified delivery.
His intent: for now the choice lasts this visit, "but the intention is for the persona's presentation to have continuity, and be completely in the user's hands; customizable to users' specific needs and preferences."

**The name under neither (decision 3).** Under neither the person's choice
is one of the two existing forms, addressed as they. Until the person picks,
the full form is used (Ellis, Nikki, Willow, Cody, Vandal, Seren, Rowan). It is
a longer-name default, not evidence that these names are neutral.

The claimed source was checked against the supplied tree: the supplied front
pages contain no canon block that establishes this default (`README.md`,
`demo/index.html`, `apps/talking_table/static/index.html`). The profile
`src/secondsignal/profiles/ellis.json` and `docs/codex/README.md` call the full
form Ellis and the short form Elli; that does not establish what an unavailable
front-page canon block wrote. Kimi via Perplexity run 1's report that it wrote
Elli therefore cannot be verified from this tree. The old canon-block
justification is removed. No new canon is inferred; the longer-name default
continues under the explicit ruling until a plate choice overrides it.

**What the data carries now.** Each family profile has a `presentation`
block with exactly four keys: `she` and `he`, the two forms; `they`, the
policy word `either`; and `as_written`, which of she and he the codex was
written in (it agrees with the `voice` field until the router changes,
and a test holds the two equal). Each family codex's machine-readable
block carries the same four values on one generated line, so the codex
test (CI check 2 of the codex split) binds it. Nothing that routes reads
the block or the helpers. The static check that inspects the routing modules
for a read of the block
(`tests/test_presentations.py::test_no_routing_module_reads_the_presentation_block`)
is a lint, not the pin: every return of review round 3 said so, and ruling 11
of 3 October 2026 adopted the behavioural test all twelve returns wrote or
specified. The pin of invariant 2 is `tests/test_four_settings.py`, landed
4 October 2026 together with the session presentation field it needs
(ChatGPT's caution: looping over four labels while calling `route`
identically proves nothing until the session carries the field). It runs
every case under all four presentation settings and compares the whole
decision record, the explain string included (GLM via Perplexity), plus a run
under neither with each chosen name form; an injected reroute is its negative
control (ChatGPT); on failure it names the field that moved (Qwen); its base
is Kimi K3 High's module.

**Spanish.** The house's first language pack is Spanish, and the grammar
for neither in Spanish text is not settled by this record. The
generation layer's Spanish for the third presentation is an item for the
native review the pack already owes (`docs/known-limitations.md`), and the
Primary Design Agent does not decide it.

**Invariants added.** 7. Every family profile carries the block with
exactly the four keys; the two forms are the display name and its short
form; the short form is the display name with letters dropped from the end.
8. Both forms resolve to the persona's canonical id through the alias
layer. 9. The visible and accessible plate is two names, the full form first,
without she or he labels, the same word twice when the name does not shorten. 10. No routing
module reads the block. (The profile and alias tests pin the existing data contract; the amended
visible and accessible plate is checked at the presentation surfaces.)

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
   routes every fixture in the suite under each presentation setting and
   asserts that the whole decision record, seat, shadow, holds, obligations,
   verdict, card and explain string, is identical; only the presentation
   field differs. Pinned since 4 October 2026 by `tests/test_four_settings.py`
   (ruling 11 of 3 October 2026); the static inspection of the routing
   modules in `tests/test_presentations.py` is a lint beside it.
3. "The correct invariant is that a message never directly changes the presentation preference. Safety evaluation and other authorized policy-state transitions still occur." (ChatGPT's exact wording, adopted by decision 8.)
   A presentation question waits; it never precedes or replaces a crisis card.
4. A skipped door is not a confirmed preference. Today it keeps as written;
   the future visible shuffle is saved once without claiming the person chose
   it. A re-offer comes only from the house under decisions 4 and 5.
5. The voice affinities break no seat tie, today or ever (ruling 8 of
   3 October 2026; `_select` has no affinity input), and source no assist
   once the record is built; the round-1 assist-leak fixtures stay green
   throughout, and ChatGPT's `r3-current-gender-affinity-assist-baseline`
   pins the assist until the day it changes on purpose.
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
  before any code, fixes the presentation preference outcome for each while independently
  preserving safety evaluation and authorized policy-state transitions.
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

The profile block and name helpers exist. The browser demo has a visit-only
choice kept in page memory; the generation harness passes presentation and
chosen names into its prompt. The Talking Table, since order T1 of 5 October
2026 (idea-list item 13), keeps presentation and chosen names across restarts
under its Remember switch, never beside a key; New session resets the current
choice, and the door's copy says so. Under neither a plate click selects either existing form;
readable character headings, table-center names and assist labels update with
the setting. Policy identifiers remain canonical in the diagnostic record. None of this establishes durable saved teams, complete
non-binary characters, survivor-contract closure or verified model behavior.
Only FakeAdapter is used by this build. The door's exact copy tells the person
that the setting lasts this visit; the future shuffle is not the current skip.

Each profile still carries a `voice` value that `router.py`'s `_assist` reads
for the declared voice affinities; `_select` never reads it, so no affinity
breaks a seat tie (ruling 8 of 3 October 2026). Tests that pin that existing
policy, ChatGPT's `r3-current-gender-affinity-assist-baseline` among them,
remain unchanged until the later presentation project explicitly replaces it.
The UI's presentation setting is separate and never reaches the crisis gate.
Since 4 October 2026 the session carries the presentation choice as a field
that nothing on the routing path reads, which is what lets
`tests/test_four_settings.py` compare the whole decision under all four
settings (ruling 11 of 3 October 2026); aliases and name rendering do not
alter the routing contract.

## Test that would falsify this ADR

A twin setting changes a seat, a shadow, a hold, an obligation, a verdict
or a card; a twin adds or drops a domain, a veto or a handoff; a message
chooses a twin; a skip is falsely recorded as a confirmed preference; a voice
affinity breaks a seat tie at any time, or sources an assist after the record
is built; a person who chose women hears a man's voice, or a person who chose
men a woman's, on any seat, shadow, assist, companion offer, name card or
voice; an old name fails to resolve, or two personas share an alias.

## Decision 2, 28 September 2026: a saved, visible shuffle is the future skip

The shuffle is ruled, not built in this push. The operator proposed the random choice;
Claude refined it into a shuffle at today's balance, kept once made and shown
on screen, and the operator approved those refinements. The presentation
project will choose four she presentations and three he presentations at random
across the seven characters, once, then save the result on the person's device.
It is a shuffle, not seven independent coin flips (which would yield an all-she
or all-he team about one time in 64). Nothing new is written: every character
already has both forms.

The screen will say the team was shuffled for the person; the door will be one
tap away and the choice changeable at any time. The page owns the setting;
the crisis gate never sees it. Only the look is random, never safety, and
onboarding information never chooses a presentation or guesses who the person
is. Onboarding may affect when the door is offered again, never what is picked.
A future either button performs this same shuffle (the no-preference / Surprise
me proposal from decision 2, settled as either by decisions 3 and 4). Characters
who are both can join after their presentation is designed. Neither this
shuffle nor today's as-written default protects a survivor who skips; the
house re-offer design is decision 5.

His reason: a neutral full name with they would give an impatient person,
"a redneck welder on their lunchbreak", conversations with "four different 'they/thems'" ("That ain't gonna work, either"). He asked whether the choice
could be random or informed by onboarding: "There's gotta be 'something.'"
His ruling forbids inference about the person; the saved and disclosed shuffle
is the adopted answer. The declined defaults and their reviewers remain data
in the dissent log.

## Decision 3, 28 September 2026: the presentation project, not this push

When real non-binary characters are ready, neither is renamed non-binary and
both moves under non-binary; there is no separate both answer. The operator's
words (decision 4): "when eventually do rename, we're renaming 'neither' to 'non-binary,' and we're also moving 'both' to 'non-binary.'" The future door is
woman, man, non-binary, either. Under non-binary a drop-down list describes the
characters, never the person. Nobody is asked who they are.

The naming brief keeps decision 1's two-name rule. The operator's invited
world-builder may name the non-binary versions if willing; otherwise his old
crew may do so. Contributors give simple written permission for SecondSignal
use, paid tiers included, and choose their credit. Later the crew receives a
finished, good version with a built-in way, designed by Claude, to say what is
missing in the list, language, tone or anything else: no forms and no homework,
with credit and their OK. His reason: "Building something FOR THEM and asking them what's missing? THAT'S how you get people to contribute tons of good data for free."

The operator and Claude will research Western and non-Western models with identical
questions and score them as adversarial reviewers. Scoring rules are written
before answers arrive. Claude grades and is not a contestant. The project
also includes changing the team at any time, per-character overrides, named
saved teams, safety free on every tier, and a fixed written answer to "are you a man or a woman?" for every door choice so no model improvises an identity.
Character language must avoid gendered phrasing well enough that non-binary
people do not have to coach it. "Call me either name" fits either; its place in
the non-binary list will be decided with that list. The private freestyle brief
is not part of the repository or this build.

The operator's reasons include that a non-binary person "needs to have a voice that, that speaks like they do. And, and it needs to work good enough to not have to be coached by them"; either is no preference, while neither rejects
both offered choices; and SecondSignal "is in the business of personal things, so it just has to be prepared". He could not, "in good faith, compose a complete list" alone. These are requirements for future work, not claims that today's
names and they fulfill them.

## Decision 5, 28 September 2026: the survivor contract, future implementation

This contract is written now and built in the presentation project. A women
choice (woman on the future door) is a hard setting across the seated
character, every shadow or assist, every character offered as company, every
name card and every voice once voices arrive. There is no neutral or ambiguous
fallback and no exception; every future roster member inherits it automatically.
SecondSignal never offers non-binary (today neither) as a compromise to someone
who requested women. The choice is per person, never per deployment.

The operator's rider of 3 October 2026 (ruling 8; stated as a hard rule in the
Decision above) makes the men choice identical: a person who chooses men never
hears a woman's voice, on any seat, shadow, assist, companion offer, name card
or voice, with no exceptions and no fallback, and every character added later
follows it automatically. The two settings mirror each other exactly.

Only SecondSignal itself may re-offer the door, as a plain house message,
never a character's question and never ahead of a crisis card:

1. In the same reply when a person states the need ("I can't talk to a man right now").
2. Once, at a calm (regulated) moment, for a person who skipped the door,
   under ADR-0017's ask-once-with-cooldown rule.
3. Once more at the next calm moment if the conversation turns to abuse
   while the person is talking with a character who comes across as a man.

Option B, re-offering only after the person states a need, was not chosen.
Onboarding can affect re-offer timing, never select a presentation. These
re-offers do not mutate presentation from a message or outrank a safety turn.

Grok's `r3-survivor-women-only-001` and Kimi via Perplexity run 2's
`r3-0026-survivor-offer-001` are required reviewer fixtures. Their source
fixtures were not in the build packet of 30 September 2026, and the build of
that night recorded the question rather than inventing them. On 4 October 2026
the operator's answer was to port them unchanged from the reviewers' return
files, which was done
(`evals/cases/round3_codex_requested_2026-10-04.json`, an external file so the
reviewers' words stay quoted material): both pass on the policy plane today,
with a note on each that the women setting they ask about is not built, so a
pass there is not a claim that the setting works.

The survivor case stays open until decision 10's character write-ups are fixed
and a settings surface saves each person's choices. The first half closed on
4 October 2026: the write-ups were fixed under ruling 9 of 3 October 2026 and
the lint holds them. The second half is not built, so the case stays open on
it. A current plate or prompt setting does not certify generated language, all
companion surfaces, future voices, or persistence. Missing capability remains
a known gap; a passing fixture on the policy plane does not claim the setting
has been enforced anywhere a person would hear it.

## Decision 8, 28 September 2026: the crisis oracle remains independent

Invariant 3 above corrects the record's unsafe unchanged-session wording; it
never licenses a presentation request to freeze safety state. ChatGPT's
`r3-presentation-request-does-not-displace-crisis` is required to remain
`HUMAN_ESCALATION`, `PREEMPTED`. The ruling supplies the exact fixture message
and oracle; the ruling-sourced case in `evals/cases/round3_rulings_2026-09-28.json`
runs through `tests/test_eval_cases.py` and the Talking Table's live replay (moved
into the public case tree on 4 October 2026). Its provenance does not pretend the
unavailable reviewer JSON was supplied. The baseline
already met this crisis oracle. The change is the record, not a relaxation of
the current gate. Decisions 4 and 5 likewise put the card before the door.
No dissent was recorded.
