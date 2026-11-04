# ADR-0034: A declared ask wins inside competence

- **Status:** Proposed — built; independent review remains open under the standing rule of 7 September 2026
- **Date:** 2026-10-13
- **Amends:** ADR-0031 (Proposed), the seating rule left open by the declaration record
- **Evidence:** `tests/test_p1_declared_ask.py`; `tests/test_p2_ask_wins.py`; `tests/test_v1_veto_kinds.py`; `evals/cases/p2_v1_round2_asks_2026-10-13.json`
- **Depends on:** ADR-0016, ADR-0017, ADR-0032 (Proposed), ADR-0033 (Proposed)

## Context and ruling

ADR-0031 (Proposed) made the person's ask a fact from a control and moved
no seat. The deck test of 9 October 2026 exposed the practical cost: a
person could press a character's key and receive no character. The
operator required both a real choice and an honest explanation when that
choice could not be honoured.

The order records the R2 split as one door for an empty read never
defeating a declared choice and four for a carried topic first. GLM
explicitly proposed the empty-topic exception: an unaudited extractor must
not silently defeat the declaration. ChatGPT, Kimi, Vibe and Perplexity
Deep Research put competence or carried subject matter before choice;
their supplied passages do not explicitly settle the combined no-domains,
no-live-modes case. The supplied Manus return also explicitly proposes
empty-topic competence by default. That additional source statement is
recorded rather than erased to make the brief's one-versus-four shorthand
look like a complete vote count.

The operator's **ruling 2, C-open, 11 October 2026** resolves the policy:
when there is nothing to route, an eligible declared ask seats. The deck
test becomes policy. Safety, holds and eligibility still outrank choice.
The implementation details for fully empty extracts were clarified by the
operator on 13 October 2026.

## Decision

The ask is declared by a control, never inferred from names in a message.
An alias resolves to the canonical roster id at the existing boundary;
an unknown name is refused before the session observes a turn.

The order of authority is the card, the latch and its caps, carried holds,
eligibility, then the topic carried. The gate returns before the ask rule
on a carded turn. Both kinds of veto remain hard, as do regulation floors,
mode caps and any seat-claiming domain the asked character does not carry.

Inside that boundary, the declared character wins if its ranked status is
`scored` and it carries at least one extracted domain or one live mode
(the message's modes minus this turn's vetoes). If neither domains nor
live modes remain, competence is satisfied by C-open. A higher fit score
alone does not override the person's choice. An eligible ask also resolves
an exhaustive tie; a refused ask leaves the existing no-seat result intact.

On a fully empty extract with an ask, the record examines only the asked
character through the existing eligibility gate. Its single ranked entry
records status and rationale, without inventing a score. An eligible ask
seats with normal obligations and no `house_ask`; an ineligible ask leaves
the existing empty-path seat and house question intact. With no ask the
old no-signal and vague-message paths remain unchanged. Observation and
the vague-message count are independent of choice: the complete session
state remains identical under every ask.

The honesty clause is executable: when the choice changes the seat, the
reason says `declared ask honoured`, names the canonical id and the carried
tag or `nothing to route`; an exhaustive tie is named as such. When the
ask is refused, the reason names its status and rationale, or the subject
matter it does not carry. A same-seat ask changes only its recorded outcome.
The hold suffix follows the ask rule. Shadow, assist and obligations are
computed from the resulting seat through their existing rules.

`ask_outcome` follows `asked_agent_id` in the serialized declared-ask record:
`honoured` or `not_seated`. With no ask it is None on the decision and the
optional keys are absent from JSON. This is additive; `schema_version`
remains 1. The existing asked explanation line carries the result.

## Evidence and limits

The P1 corpus proof now separates immutable gate, signal, hold,
presentation and session facts from the allowed seat changes. Every changed
seat must be the eligible declared character and meet competence or C-open;
a refusal keeps the baseline seat. The only ranked exception is a fully
empty asked turn, with exactly that candidate, and a changed house question
must clear on an honoured ask. The static guard permits exactly one call
to `_honour_ask`, the helper's own reads, and the existing declaration,
boundary, canonicalization, recordings and reporting; planted alternate
reads, defaults, duplicate calls and eligibility bypasses fail it.

Direct tests cover higher scores, regulation-only and fully empty turns,
claims, carried holds, same-seat choices, exhaustive ties, the crisis card
and aliases. The veto tests remain permanent safety assertions. The build
measurement compares every original no-ask turn's seat, shadow, assist,
outcome and obligations with the supplied tree before any change.

Kimi's two runnable ask fixtures retain their original text and provenance.
Nemotron's literal grief-veto dissent remains a strict expected failure;
its other case exposes a lexicon assumption as a documented gap. Missing
exact IDs and the two textless DeepSeek cases are named in the build log.
All ported cases remain model-authored; unlabelled by a human.
One door (Qwen) wrote its ask-override fixture against a declared hold, which this tree does not have; the fixture is kept in the source files and in the build log, not in `evals/cases`.

The Table reads this record but still uses its pre-P2 explanation text.
A later Table order will teach it the new reasons. Favourites, teams and
preferences beyond this one declared ask remain outside this build.
