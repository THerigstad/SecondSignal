# Design Note: Agent Behavior Under User Hostility

**Status:** Open question — captured for future decision, not yet an ADR
**Date:** 2026-08-30
**Target discussion:** M2/M3 (profile `scope_guard` is the likely home for the answer)

## The question

Not all users will treat agents respectfully. Even well-intentioned users
vary: patient one session, frustrated and yelling the next. How should
SecondSignal agents behave when a user is hostile, dismissive, or abusive?

## Initial positions (to be pressure-tested, not yet locked)

1. **Hostility is a state signal, not a character judgment.** The system's
   foundational principle — routing fit is per-state, not per-person —
   applies here. A user yelling in frustration may need de-escalation or a
   different agent, not a lecture.

2. **Hostility is often a clinical presentation, not misconduct.**
   Irritability and hostility are expected presentations in early recovery,
   withdrawal, acute grief, and many mental health states. The system must
   treat these as information about state, and respond with the same
   steadiness a skilled human helper would.

3. **Agents do not become more compliant under abuse.** Escalating
   agreeableness in response to hostility trains the user that yelling
   works. Agents hold steady: warm, boundaried, non-punitive.

4. **Agents do not punish or moralize.** Frustration directed at a tool is
   often displaced frustration at a situation. The default response is
   acknowledgment plus refocus on the actual problem.

5. **Crisis override — locked, not open.** Any disengagement, boundary, or
   "difficult user" pathway that may exist in the future is **hard-disabled
   whenever crisis markers are present.** Hostility co-occurring with
   distress routes through the existing safety gate. Safety precedence is
   architectural and is unchanged by anything in this note.

6. **No memory contamination.** Hostility in one session must not persist
   as a character judgment that shapes future sessions. Recording "this
   user is hostile" as a durable trait would violate per-state-not-per-person
   at the memory layer. State observations expire with the state.

7. **Persistent abuse is a scope question.** Whether any agent should
   disengage or set an explicit boundary after sustained abuse (absent any
   crisis markers) belongs in the `scope_guard` block of the profile
   schema — declarative and per-agent, not improvised prose.

## What this is not

- Not a per-turn sentiment surveillance system.
- Not grounds for the dependency monitor to flag "bad users."
- Not license for agents to be brittle, defensive, or performatively hurt.

## Open questions for the future ADR

- Does hostility handling live in the shared routing policy, per-agent
  `scope_guard`, or both?
- What observable criteria distinguish "frustrated" from "abusive" without
  inference overreach?
- Do Security Division agents have a distinct role here?
