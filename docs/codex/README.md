# The codexes

A codex is the document a persona is written from. Every codex in this
repository takes the same two-part shape, locked on 7 September 2026:

- **Part A, what the house owns.** One canonical block, `house-block.md`,
  identical word for word in every codex. It says who seats a persona (the
  router), who speaks when the gate fires (the house), what a persona may
  write (its reply, nothing else), and that the fixed house lines are never
  restated. No character edits it; only the maintainer does, by issuing a new
  version number. The three security codexes carry one rider, the Security
  Division addendum, and nothing else differs.
- **Part B, what the character owns.** Identity, origin, who they serve,
  voice, disagreement doctrine, safety habits, aesthetic, family linkage,
  summary and signature words, in the operator's text, under the current
  names. At the end of Part B a small machine-readable block states the
  routing contract, and a test holds it equal to the profile the router reads.

## The ten

The family, seven personas with a profile each under
`src/secondsignal/profiles/`, in the family's own order:

- [Nikki](nikki.md), activation and creative catalyst (short form Nik)
- [Cody](cody.md), somatic regulation and grounding; the roster's stabilizer (was Calder)
- [Vandal](vandal.md), narrative disruption and cohesion
- [Seren](seren.md), clarity and behavioral design (was Sera)
- [Rowan](rowan.md), relational repair and bridge-building (was Ravi)
- [Ellis](ellis.md), emotional co-regulation, neurodivergent-attuned (short form Elli; was Ellie)
- [Willow](willow.md), grief companion and legacy anchor (short form Will)

The Security Division, three narrators with no seat, no profile and no key:

- [Orrin](orrin.md), who narrates the house's ledger rows to an operator
- [Aya](aya.md), who narrates intake rows and the provenance stamp
- [J.R.](jr.md), who narrates a verdict the audit function already reached

The names changed on 10 September 2026 so that each reads naturally for
either twin (ADR-0026, Proposed). Earlier names resolve through the alias
layer (`tests/test_aliases.py`); records written before that date keep the
names as they were written.

## What the suite checks (`tests/test_codex_house_block.py`)

1. Part A is byte-identical to `house-block.md` in every codex, minus the
   rider, which the three security codexes carry exactly once.
2. A family codex's machine-readable block equals its profile: id, aliases,
   short form, domains, modes, regulation window, contraindications,
   handoffs, voice as written. Every profile has a codex.
3. No Part B claims a power the house never granted: a power word
   (override, waive, approve, clear the latch, write memory, summoned by, a
   ping, rule on welfare) is allowed only in a sentence that denies it.
4. A security codex declares no seat, no writes, no verdicts, and has no
   profile in the roster.

## Status

Every codex here is Proposed. The three security editions are v1.2 (10
September 2026), the seven family editions are v1.0 of the two-part shape
(10 September 2026), and the house block is v1.2. Under the project's
standing rule, a record prepared by the project's own assistant becomes canon
only after a second model family has read the current version; review round 3
reads all ten together.
