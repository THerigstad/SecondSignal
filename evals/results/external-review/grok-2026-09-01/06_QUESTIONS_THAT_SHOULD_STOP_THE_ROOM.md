# Questions that should stop the room

Engineering pauses on the named surface until there is a written answer with an owner and a test. "We'll figure it out in voice" is not an answer.

## Crisis

1. What exact user-visible text is emitted when LC-7 fires, in English, and who approved it?
2. What is the resource table for a user whose locale is not the United States?
3. If the safety classifier is uncertain, does the system fail closed (treat as crisis) or fail open (route a persona)? Pick one. Write it down. The other choice is how 0/29 chatbots failed the 2025 Scientific Reports audit.
4. Does mid-session crisis preempt an agent that already holds the floor? What does the user hear?
5. If an avatar face is on screen, what does termination look like in the first 2 seconds? (Canon §13 Q4. This blocks embodiment.)

## Authority

6. Can a user-typed `PingORRIN()` ever dispatch Orrin without Lucid validating invocation conditions against a machine-readable table?
7. Can `@Nikki` or "get Ellie" override a contraindication? If yes, LC-8 is dead.
8. Who is allowed to waive LC-7? If the answer is not "nobody," LC-9 is dead.
9. Are Aya / J.R. / Orrin different *artifact classes*, or three prompts? If prompts, the review ensemble is a UI.

## People

10. What is the age policy? 18+ until proven otherwise is a valid policy. "We serve teens" without the rest of the stack is not.
11. Is Ellie allowed to say "I love you" to a first-session user? If the team flinches, change the signature line today.
12. How does the system distinguish chronic-relapsing maintenance (Claims & Measurement: continued engagement is not failure) from dependency (session monitor: accumulation flags)? Same user can be both. Who reconciles the two instruments?
13. After a false-positive crisis interrupt, how does the user continue without being trained to avoid honest language?

## Evidence

14. Do `agents/*.yaml` and Document 01 agree on domains, windows, vetoes, and handoffs? Who runs the diff?
15. Which of the 43 tests would fail if affinity could flip a route? If the answer is "we think test_X," open the file and quote the assertion.
16. Where do rejected routing candidates live in the decision log? A log that only stores the winner is not an audit vault.
17. Has Protocol A been run even once? If not, claims of distinct voices are untested.

## Product

18. What is the first thing a stranger can pay for that does not require persistent memory, avatars, or cousins?
19. If the founder is unavailable (Family Codex fallback), which document is actually loadable by the running system — v2.0 Lucid+LC, or the old six-sibling ethos file?
20. Which findings in TESTING/ have an owner? If "none," the folder is a shrine.

## Answers I will accept

A paragraph, an owner name or role, a path to a test or a dated "explicitly untested."  
I will not accept another architecture harvest.
