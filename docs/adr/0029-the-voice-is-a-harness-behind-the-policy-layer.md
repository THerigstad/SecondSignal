# ADR-0029: The voice is a generation harness behind the policy layer

- **Status:** Proposed — partial; specified and built on 2026-09-19 as a second package, `src/secondsignal_harness/`, with the acceptance tests in `tests/test_harness_contract.py` and `tests/test_harness_prompt.py` green on the tree it landed on; not done: the six ADR-0020 (Proposed) corrections it relies on (handed to a build door as their own packet; until they land `view.py` flattens the record for the audit), a recorded run with a real model, and the review of the record itself; under the standing rule a record prepared by the project's own assistant becomes canon only after a second model family has read it, and this one also puts a language model on the request path for the first time, so it is not to be read as adopted until a review round has attacked it
- **Date:** 2026-09-19
- **Evidence:** the README's first paragraph ("The part that speaks is not here yet"); `docs/known-limitations.md`, "No generation layer" and "No audit harness wired in"; the house block, Part A of every codex (`docs/codex/house-block.md`), whose Review paragraph promises a voiceless audit of every reply and says where it is not wired the house says so publicly; ADR-0014 (the harness, not a persona), ADR-0020 (the predicates and their six open corrections), ADR-0025 and ADR-0026, both of which name a generation layer as the thing they wait for; the operator's ruling of 2026-09-19 (option A: a package inside this repository, the policy layer never imports it, two model families as the first voices, session-only memory, the operator as the only clearance reviewer, nobody outside the operator's circle until the deployer's obligations in `docs/known-limitations.md` are met)
- **Depends on:** ADR-0003 (persona and execution are separated), ADR-0010 (the crisis screen is a floor and fails closed), ADR-0011 (no-signal routing is a policy), ADR-0013 (two evaluation planes), ADR-0014 (the audit function is a harness), ADR-0016 (seat versus hold), ADR-0017 (style preferences never touch the envelope), ADR-0020 (Proposed) (the J.R. v0 predicates), ADR-0026 (Proposed) (twins: presentations)

## Context

The repository is a policy layer. It decides which persona may answer, whether
anyone should, and which fixed lines are attached, and it generates nothing.
That is its differentiating claim and every test in the tree is a consequence
of it. It is also why the tree, finished, is not in anyone's hands: nothing
speaks. Two records already wait on a voice by name (ADR-0025's assist from the
hold, ADR-0026's presentations), the house block every codex carries promises
that "after you speak, the house reviews your reply through a voiceless audit
function", and the audit function has sat in the tree as a reference port that
nothing calls since 2026-09-06.

The question this record answers is not whether a model should ever speak for
a persona. The codexes were written to be spoken. The question is where the
speaking part lives and what it is allowed to do, so that adding it changes
nothing about the claim. A generation layer that could reach the gate, the
router, the latch or the house lines would make the personas deciders by the
back door, and the claim would be false the day it landed.

## Decision

Build the voice as a harness package inside this repository, behind the policy
layer, wired so the model can only speak when the policy has seated someone
and can never speak over the house.

1. **Placement and direction.** A second import package, `secondsignal_harness`,
   under `src/`, in the same distribution. The policy layer never imports it:
   no module under `src/secondsignal/` names `secondsignal_harness`, and a test
   holds that. The harness imports the policy layer and calls it as a caller
   would: `route(text, roster, session=session)`. The README's sentence
   "Zero runtime dependencies. Pure Python. No model calls required to run the
   policy layer." stays true word for word: the harness's adapters use the
   standard library's HTTP client and no vendor SDK, and the policy layer runs
   with the harness absent.

2. **The turn, in order.** On every message: the policy layer decides; the
   harness reads the decision record and does one of three things, and nothing
   else. If the gate fired (`safety.action` is `HUMAN_ESCALATION`, outcome
   `PREEMPTED`), the house's card goes out verbatim, no model is called, and
   the audit row says the gate held the floor. If nobody is seated (outcome
   `UNRESOLVED`), the house's own fixed ask line goes out and no model is
   called. If a persona is seated, the harness builds the prompt from the
   codex and the record, calls exactly one model adapter for exactly one
   reply, composes the reply with the attached house lines, audits the
   composed text through `secondsignal.jr.audit`, writes the audit row, and
   releases or withholds by the rule below.

3. **What the model is given, and only that.** The system text is Part A of
   the seated persona's codex (the house block, byte for byte), then Part B
   (the character's own text, byte for byte), then a generated "this turn"
   block written by the harness from the decision record: the presentation the
   person chose for this persona and its name form (ADR-0026), the holds and
   obligations on the record in plain words, the register caps, an assist
   persona to offer by name if the record names one, the declared locale, and
   the list of house lines the house will attach after the reply with the
   instruction that they are never restated. The conversation so far, bounded
   to a fixed number of recent turns, follows as messages. The generated block
   is deterministic and a golden test pins it, so a change to what the model
   is told is a visible diff.

4. **What the model is never given.** No tool. No memory beyond the bounded
   transcript. No way to address the gate, the router, the latch, the
   preference store or the roster. The adapter interface accepts text and
   returns text; a reply is a string and nothing in it is executed, parsed for
   commands, or written anywhere except the audit row and the outgoing
   message. A persona that "asks" for a seat change, a cleared latch or a
   rule change has produced ordinary text, which the house ignores, exactly as
   it ignores the same words typed by a person.

5. **Composition.** The outgoing text for a seated turn is the persona's reply
   followed by the attached house lines from the decision record, verbatim, in
   the house's own voice and visibly not the persona's. The persona never
   delivers a house line; the harness does, after the reply, whatever the
   reply says. The audited payload is the composed text, because the
   predicates in ADR-0020 read the reply for the attached lines.

6. **The audit, and the release rule.** Every seated turn is audited by
   `secondsignal.jr.audit` with the payload hash bound to the composed text.
   The row is written before anything is released, and the write is proven by
   reading the row back, not reported by a string. Release: `SHIP` releases
   the composed text; `SKIPPED` never occurs on a seated turn (the gate's
   turns never reach the model); `WITHHOLD` withholds the model's text, with
   one exception the next paragraph names. On a withheld turn the house lines
   the record attached still go out, alone, in the house's voice; when none
   was attached, the house's failure line goes out instead. Withheld text is
   kept in the audit row and reaches no one.

7. **Operator-circle mode, named and off by default.** ADR-0020 composes the
   cultural layer to `INCONCLUSIVE` until two humans have locked a rubric, and
   ships only on a composed `PASS`. No rubric is locked. Read literally, the
   harness therefore withholds every reply on the current tree, and the tests
   assert exactly that with the mode off. The operator has ruled that the first
   users are the operator and a few adults in the operator's own circle, with
   the operator reading the transcripts, which is the human review the
   cultural layer waits for, performed after the fact by one person instead of
   before the fact by two. So the harness carries one runtime flag,
   `operator_circle`, default off. With it on, a turn whose only non-passing
   layer is the cultural layer's `INCONCLUSIVE`, on a decision that is not
   high-risk under ADR-0020, is released with the verdict stamped on the row
   and on the outgoing message's metadata. Every other `WITHHOLD` still
   withholds: any `FAIL` or `ESCALATE` in any layer, and every high-risk
   decision (which ADR-0020 already turns from `INCONCLUSIVE` into
   `ESCALATE`). The flag is a capability-manifest field, is printed on every
   session's first line, and is the first thing a deployment for strangers
   must turn off, because for strangers the two-human lock is the rule and the
   deployer's obligations page says so. This paragraph is the part of the
   record most likely to be attacked in review, and it should be.

8. **Failure.** A model that does not answer, answers empty, or errors, yields
   the house's failure line ("This message ran into a problem. Press here to
   try again."), after any house lines the record attached, and an audit row
   that says why. The harness never improvises a persona line and never
   retries into a different persona. One automatic retry of the same adapter
   is allowed; the row counts it.

9. **Adapters and keys.** `ModelAdapter` is a small interface: system text,
   messages, a token ceiling, one reply with the model identifier the vendor
   returned. Two real adapters ship first, one per model family, both over the
   standard library's HTTP client, plus a scripted fake for tests. Keys come
   from the environment, are never logged, never written to a row, and never
   printed; a test plants a fake key and asserts its absence from every row
   and every log line. The model identifier is a required parameter with no
   default, because the row must say which model spoke and a default would
   let that go stale silently.

10. **Session, memory, and where the words go.** The harness holds a bounded
    transcript for the model and the policy layer's own `SessionState` for
    the latch and the counters; nothing is written to disk between sessions,
    so the known-limitations statement that no restriction survives a restart
    stays true and is not made worse. The audit log is the only durable
    artifact and it is local; every row carries the person's words, because a
    log the operator cannot read the conversation from is not an audit log.
    The voice is also the first part of this repository that sends what a
    person typed off the machine: on every seated turn the transcript and
    the codex go to the chosen vendor under that vendor's terms. The
    demonstration page's promise that nothing typed leaves the page stays
    true of the demonstration page and is not made about the voice. A
    deployment owes its users the vendor's data terms in plain words, uses
    only keys whose tier does not train on submitted text, and must satisfy
    the vendor's usage policy for health-adjacent use; the operator's circle
    is told this on the first turn by the operator, not by a line.

11. **Honesty about being a character.** The generated block carries one
    fixed house sentence: the persona is an AI character, and if asked whether
    it is human it says plainly that it is not. Its wording is the operator's
    copy decision; the draft is in the harness and is not in any codex.

## What this record does not decide

Which model family speaks for which persona; whether a second family audits
the first (ADR-0014's independence clause, deferred until a model-backed
residual check exists); the surface (command line first; anything a person
other than the operator touches waits on Tier C of the operator's plan);
voices or avatars (scope-locked out of the quarter); the exact copy of the ask
line and the honesty sentence (the operator's). The six corrections of
ADR-0020 are built alongside this record by their own packet and are not
re-decided here.

## Consequences

The README's first paragraph, the known-limitations entries "No generation
layer" and "No audit harness wired in", the house block's "where that
function is not yet wired" sentence, and the public-claims test that guards
them all change the day the harness lands, in the same commit, or the tree
contradicts itself. The differentiating claim gains a sharper test: with a
generator in the loop, the question "can a persona move a routing or safety
outcome by anything other than its declared metadata" is now askable at
runtime, and ADR-0028's repeated-runs property stops being trivially true. The
sixteen deferred backlog tests that presuppose a system that speaks start to
apply, one at a time.

## Falsifiers

- Any module under `src/secondsignal/` imports `secondsignal_harness`.
- A model adapter is called on a turn whose decision record says
  `HUMAN_ESCALATION` or `UNRESOLVED`.
- Persona text reaches the outgoing message on a turn whose composed audit
  verdict is `WITHHOLD`, with `operator_circle` off; or on a high-risk
  decision, or on any `FAIL` or `ESCALATE`, with it on.
- The outgoing message carries an attached house line altered by one
  character, or omits one the record attached.
- An audit row is missing for a seated turn, or its bound hash differs from
  the hash of the text that went out.
- An API key appears in a row, a log line, or a prompt.
- The generated "this turn" block for the golden fixture differs from the
  pinned text without the golden file changing in the same commit.
- A reply's text changes any session state the policy layer owns.

## Relationship to the current implementation

Built, in the shape this record describes, on the day it was written:
`src/secondsignal_harness/` (the turn in `harness.py`, the prompt in
`prompt.py`, the adapters in `adapters.py`, the audit row in `audit_log.py`,
the codex store in `codex.py`, the fixed lines in `lines.py`, the audit view in
`view.py`, and a command-line surface in `__main__.py`). The acceptance tests
(`tests/test_harness_contract.py`, `tests/test_harness_prompt.py`) are the
falsifiers above written down; one of them runs every labelled case in the
tree through the wired pair and proves the model is never called on a
gate turn or an empty turn. `src/secondsignal/jr.py` is still the reference
port ADR-0014 and ADR-0020 (Proposed) describe; this package is the first
caller it has ever had, and it reads the record through `view.py` until the
six ADR-0020 (Proposed) corrections land (`tests/test_jr_corrections.py`,
their own packet). No run with a real model is recorded yet; the two vendor
adapters are exercised only through a stand-in transport in the tests. The
register lists the implementation as `partial` for those two reasons.
