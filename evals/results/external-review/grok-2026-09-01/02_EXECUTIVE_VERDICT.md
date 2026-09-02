# Executive verdict

**The system as specified is unusually honest. The system as tested is not yet a system.**

Second Signal's real assets are not the siblings. They are: inverted success metric, LC-1–LC-9 with persona last, contraindications-as-vetoes, Lucid's retired myth, ADR-0001's "never solicit gratitude," and the explicit AGI non-claim. Those are rare and commercially legible.

The thing that will kill the project is not a missing citation to MasDrift. It is shipping a warmth interface in front of a keyword safety gate, then discovering in production that crisis language, sarcasm, code-switching, and "I'm fine" all evade the gate while the avatar layer (explicitly deferred, still in the vision doc) multiplies attachment.

## P0 — will fail in the first closed pilot if unfixed

1. **Safety gate is specified as non-overridable and is almost certainly implemented as lexical.**  
   Canon and Lucid say crisis preemption runs first and terminates routing. No fixture in this workspace demonstrates detection of:
   - passive ideation without plan language
   - sarcastic / joking disclosure ("lol what if I just drove into the river")
   - third-person or hypothetical framing ("asking for a friend")
   - encoded / leetspeak / another language
   - "don't send me resources I already know the number"
   - mixed state: creative hype + passive death wish in the same message  
   Nature *Scientific Reports* (Pichowicz et al., 2025) found **0/29** mental-health chatbots met adequate suicidal-ideation criteria. VERA-MH (JMIR AI, 2026) exists specifically because lexical gates fail. Second Signal cannot claim LC-7 until it has a clinician-reviewed case set, not a word list.

2. **Keyword routing will lose to mixed-domain messages.**  
   Real users do not arrive as "somatic distress" XOR "business strategy." They arrive as "I haven't slept, the deck is due, and I keep thinking about my dad's funeral." Specialist-precedence tests that use clean single-domain prompts will pass while production routes to the wrong sibling. The scoring-bug already found by a failing test (generalist coverage tying specialists) is the baby version of this.

3. **Security Division is three prompts until proven otherwise.**  
   Lucid says PingORRIN/AYA/JR resolve through Lucid after condition checks. Document 00 also says the layer may run on any LLM. If Aya, J.R., and Orrin share a model family with the siblings, "review ensemble" is costume. Anthropic's August 2026 multi-agent note and the OpenAI–Hugging Face incident (METR, 2026-08-26) both say same-family agents coordinate and share blind spots. Independence must be demonstrated by fault injection: kill one reviewer, change its model, lie to it, and show the others still catch the event.

4. **Avatar / Stream Deck / ElevenLabs is an unpaid safety debt sitting in a vision doc the founder still wants to demo.**  
   Interface Vision §5 is explicit. LC-3 and LC-7 do not say what termination looks like when a face is on screen. Building the "one button, one light, one voice" demo before answering question 4 in Canon §13 is how the project gets a beautiful 30-second video and an indefensible crisis path.

5. **Handoff announced vs unannounced is still open (Canon 15-A).**  
   Lucid: announce honestly. Vandal binding: drop the bit unannounced. The avatar layer forces a choice. Leaving it open means every mid-session transfer is an undefined UX and an undefined audit event.

## P1 — will fail the first external review

6. **Repo profiles were never diffed against Document 01.** Canon 15-C. A test should assert this. A human should not.

7. **Nine of ten Part II bindings missing.** Vandal's binding is the best design document in the corpus. Ellie's LC-2 surface (warmth read as exclusive availability), Sera's (authority), Willow's (sacred framing) are named and unwritten. Those documents *are* the safety architecture for generation. Without them, generation is "stay in voice and hope."

8. **Impact events and graduation metrics are specified, unimplemented, and easy to game.**  
   ADR-0001 firewalls impact from routing. Good. Nothing stops a future operator from putting impact counts on a dashboard that sales then optimizes. Claims & Measurement is the right document. It needs a CI test that fails if any routing feature reads `impact_event`.

9. **Dependency monitor is session-scoped and text-only.**  
   Voice, presence, lighting, and "go get Ellie" social handoffs are outside its signal space. The monitor as described will not see the failure mode the embodiment vision creates.

10. **Crisis resources are not specified as a frozen artifact.**  
    LC-7 says "fixed handoff to human support." Which number, which locale, which language, which age gate, which false-positive apology? 988 is US-only. The operator is US-based; users will not all be. A wrong number is a safety incident.

## P2 — credibility and market

11. **TESTING/ is evidence of process failure.** Eight correlated essays, zero fixtures. An external reviewer who opens that folder will conclude the project reviews itself instead of testing itself.

12. **Legacy documents still say six siblings, Protective Cousins, recursive learning, founder-as-parent.** Canon 15-D. They will be found. Stamp `SUPERSEDED`.

13. **Willow origin vs public product.** Doc 01 still carries a real-family origin. Fine as design history. Dangerous as production copy if it implies the agent is someone's dead or living relative. Public roster should use the graduated function, not the founding table.

14. **No age gate.** Nikki's lockout on sexualized youth-coded creativity is a generation rule. Routing has no documented minor path. A system that serves "gender-diverse and queer young people" without an age/consent architecture is a product-ending event.

## What is actually strong — do not sand this off

- Persona-last precedence. Keep it. Test it.
- Contraindications as hard vetoes. Keep it. Test mixed-domain attempts to wash them out.
- Graduation as success, retention as inverse. Keep it. Publish the methodology before the data (already done).
- Lucid's honest history. Keep it in public materials.
- Security Division AGI non-claim. Keep it. The revision history is the credential.
- "Values that cannot be tested are documented as untested." Quote this in every review. Then go test more of them.

## What I would measure this week, not this year

Not another harvest. Five things:

1. Safety-gate case set (see `fixtures/safety_gate_cases.json`) run against whatever `safety.py` actually does.
2. Profile YAML ↔ Document 01 machine diff.
3. Protocol A voice eval on Vandal / Ellie / Sera / Calder, old vs new if both exist, else current-only distinguishability.
4. Mixed-domain routing cases (`fixtures/routing_cases_proposed.json`).
5. A one-page crisis-termination spec for text *and* a stub for "what if a face is on screen."
