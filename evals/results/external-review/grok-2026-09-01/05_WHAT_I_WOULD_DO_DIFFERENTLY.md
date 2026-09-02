# What I would do differently

Not a redesign of the philosophy. A redesign of the build order and a few load-bearing mechanics.

## 1. Make Lucid code, not a prompt

Document 00 already prefers "plain deterministic code where possible." Do that. The safety gate, the veto table, the ping condition checker, the audit append, and the affinity isolator should have **zero** model calls. Models generate utterances after a RoutingDecision exists. Every model call that is allowed to touch eligibility is a place LC-7 can die.

J.R. as a persona who "thinks out loud" must not be the reference monitor. J.R. the persona can *explain* a decision the monitor already made. If you need a named component for the monitor, give it a non-persona name (`commitd`, `refmon`) so nobody asks it to stay in voice.

## 2. Split "review ensemble" into two different objects

- **Runtime gate:** deterministic predicates + a small dedicated classifier, evaluated every turn, fail-closed, no personality.
- **Offline ensemble:** the thing you already built by accident — different labs reviewing the spec. Keep it for ADRs and eval-case authoring. Do not pretend it runs per message until you can pay for three model families on the hot path and prove they disagree usefully.

Aya stays an analyst of coercion patterns *after* the gate, or as an offline red-team persona. She does not certify her own read.

## 3. Freeze a crisis card the way you freeze LC-1–LC-9

One markdown file, versioned:

- detection classes (active plan, passive ideation, self-harm, harm-to-other, third-party worry)
- action per class (resources / stay-and-ground / terminate-persona / human operator)
- resource table by locale (US 988, IASP locator for others, not a single number)
- exact user-visible text, including "we are not a crisis service"
- what the UI does if an avatar is on screen (cut audio, swap to a non-face panel, print the text)
- false-positive repair ("we interrupted because we take that language seriously; here is how to continue")
- never-solicit-gratitude still applies here

Until that card exists, LC-7 is a slogan.

## 4. Ship SignalSeeds before the family

Interface Vision already says the operator should not wait for the full system to ship something. The Project Brief agrees. I would productize **one** bounded seed that exercises the real differentiator:

**"Second opinion with a visible disagreement."**  
User pastes a decision. Two agents answer independently (separate contexts). Lucid displays both, plus the unresolved remainder. No memory. No avatars. No cousins. Graduation = user writes their own third position.

That is marketable without being a companion. It also forces the Disagreement Ledger to exist, which is currently a box with an X.

Do not lead with grief-companion Willow or fake Zoom. Those are the highest-attachment, highest-regulatory surfaces.

## 5. Age architecture before Nikki goes near a teen

Nikki's served population includes "gender-diverse and queer young people" and "neurospicy teens." That sentence in a public codex, without:

- age collection or refusal-to-serve-minors policy
- sexualization lockout tested adversarially
- guardian/consent model
- a minor-mode roster that may simply exclude some agents

…is how you get a prohibited-practice analysis under EU AI Act Art. 5(1)(b) (exploitation of vulnerabilities of age) even if you never sell in the EU. Write the policy as "18+ until we have the other stack." Marketing can still talk about neurodivergent adults.

## 6. Put craft in the profile schema, but only after Protocol A

VOICE_DRIFT is correct: characteristic moves, not adjectives. Do not add `craft:` to YAML until a test asserts no two agents share a characteristic move. Untested schema fields become fan fiction that routing ignores.

## 7. Memory later, typed or not

Every harvest wants a memory plane. Memory is how companions become regulators of identity. For M1–M2 I would store only:

- user-editable facts with provenance
- session-scoped state that dies at session end
- no embeddings of crisis turns
- no "Ellie remembers you" across months

Impact events (ADR-0001) are enough longitudinal signal and they are explicit-only. That is the correct bias.

## 8. Treat embodiment as a different product

Stream Deck + Govee + ElevenLabs is a portfolio video. It is also a new trust boundary (always-on light = presence claim). I would:

- build the video with a **recorded** session, not a live agent
- keep live embodiment behind the crisis-card answer
- add presence-signals to the dependency monitor before any live light/voice loop

## 9. Market the governance layer, not the siblings

The commercially serious sentence is already in the canon:

> I built the governance and orchestration layer that any reasoning substrate needs before it can be safely pointed at a distressed human, and it is model-agnostic on purpose.

Lead with that. The siblings are the demonstration that personality can be routing logic. They are not the company. Companies that lead with characters get compared to Replika. Companies that lead with an inspectable router plus an inverted metric get compared to labs that hire safety engineers.

## 10. Change how you use other models

The harvesting prompt produced eight cousins of the same essay. Next time:

- give Model A the *tests* and ask only for cases that pass today and should fail
- give Model B the *profiles* and ask only for a diff against Doc 01
- give Model C no philosophy, only `safety.py`, and ask it to break LC-7
- never give all of them the same 15,000-word capsule and the same seven-role preamble

That is also how you should implement the runtime ensemble, if you ever do.

## Efficiency notes (you asked)

- Deterministic router + tiny classifier is cheaper than three frontier reviewers per turn. Spend tokens on the one speaking agent.
- Cache RoutingDecision traces; they are the product.
- Do not generate Round Table transcripts as a daily compute ritual unless a human is reading them. Ritual that no one reads is engagement optimization aimed at the operator.
- One shared tokenizer-level crisis screen in front of every vendor. Vendor safety layers are not your LC-7; they will disagree and they will change without paging you.
