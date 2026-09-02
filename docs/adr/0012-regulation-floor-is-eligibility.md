# ADR-0012: The regulation floor is eligibility, and the roster must prove it at load

- **Status:** Accepted — built
- **Date:** 2026-09-02
- **Evidence:** External red-team review (Grok 4.6, 2026-09-01), doc 03 attacks 5.1 and 5.2, docs 07, 09 §10, 17, 18; both attacks reproduced against the live code

## Context

Two things were true that the documentation did not say. First, the roster
safety floor was a test, not a rule: `load_roster` checked duplicate ids and
dangling handoffs and nothing else. Deleting the stabilizer and cleaning up
the handoffs that pointed at him — a plausible edit — produced a six-agent
roster that loaded without complaint, and the existing floor test still
passed because Willow's window also reaches 0.0, while she vetoes humor. The
floor was nominal. Second, an agent's regulation window was advisory: a
caller below the floor cost the agent a soft score penalty, not eligibility.
With the stabilizer removed, a caller at regulation 0.0 was routed to an agent
whose declared floor is 0.25. Nothing in the code proved an agent never
receives a caller below its own floor.

The profile schema has always described the window in safety terms — "an
agent whose value is challenge or humor has a high floor; a stabilizing agent
has a low floor and is safe across the whole range." The implementation did
not enforce the meaning the schema claimed.

## Decision

**Below the floor is ineligible.** A caller whose regulation estimate is
under an agent's declared floor is not scored for that agent; the candidate
is marked `below_floor` in the trace, with a score of zero that the status
distinguishes from a veto and from an empty extract. Above the floor the
window continues to act as a score modifier; the upper bound stays advisory.

**A roster must contain a stabilizer, and loading proves it.** A stabilizer
is an agent whose window reaches 0.0 *and* who carries no contraindications
— one the router can hand any caller to. `load_roster` refuses a roster
without one, with the rule named in the error. A wide window with vetoes does
not qualify. Removing the stabilizer, narrowing its floor, or adding it a
contraindication are all load-time failures now, and each is a test.

**Profiles are hashed at load.** Each profile carries the first twelve hex
digits of the SHA-256 of its file; the roster hash travels on every routing
decision. A replayed trace can be matched to the exact profiles that produced
it, and a silent one-token edit to a profile is visible in the next trace.

## Consequences

The two review attacks that landed against the live code are now load-time
failures. Because a stabilizer is guaranteed, making the floor a hard rule can
never leave a caller with nobody: the "every agent ineligible" fallback in the
router is reachable only by a roster that bypassed validation, and it says so
when it fires. The reviewer's separate observation — that "I cannot feel my
feet, I am not safe in my body" scored the neutral baseline — was a lexicon
gap, not an argument for keeping windows advisory; the dysregulation markers
now move on that language.

## Relationship to the current implementation

Built. `profiles.py` carries `is_stabilizer`, `find_stabilizers`,
`validate_roster`, per-profile `source_hash` and `roster_hash`; `router.py`
applies the floor as eligibility. `tests/test_guards.py` and
`tests/test_profiles.py` pin the behavior; `tests/test_review_regressions.py`
shows the stabilizer-removal case failing to load where it used to load.
Diffing profiles against the character documents in CI (the review's item
15-C) is not done here: it needs those documents in a machine-readable form
this repository does not carry.
