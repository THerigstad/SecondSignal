# Persona and codex holes

These are defects inside the family documents themselves. They will leak into routing JSON, prompts, and demos if nobody diffs them.

## Document contradictions that are still live

| ID | Conflict | Fix |
|---|---|---|
| C-15-A | Lucid announces handoffs; Vandal binding exits unannounced | Write one rule: *system* announces agent identity; *persona* does not narrate the emotional gear-shift. Test both. |
| C-15-B | Ellie as co-regulator (Doc 01) vs "humor as regulation" (older roster table) | Doc 01 governs. Fix the table. |
| C-15-C | Repo profiles vs Doc 01 | Machine diff. CI gate. |
| C-15-D | Legacy "six siblings / cousins / recursive learning / founder-as-parent" | Stamp SUPERSEDED. SESSION_BRIEF already bans personal names in repo. |
| C-WILLOW | Canon v0.3 marks Willow Doc 01 as missing | It is in this session's attachments. Update canon. Fill the graduation-metric cell from the arriving Doc 01: user carries grief with growing steadiness, completes legacy work in their own voice, turns toward living community. |
| C-RITUAL | Morning Round Table assigns news-desk domains (silver price, cat behavior, Viking tattoo) | Canon says ritual domains do not affect routing. Add a test that a message about silver price does not route to Sera *because of the ritual table*. |
| C-PING | Pings are specified; invocation conditions are not machine-readable | Write a table: who may call, from where, what evidence is required, what happens on forgery. |
| C-VOICE | Voice-drift protocol exists; no `voice-eval/` results | Run Protocol A. Stop interviewing agents about their own souls. |

## Per-agent failure surfaces the missing Part II bindings must cover

Vandal's Part II is the template. Each row is an LC mapped onto a specific way *this* voice breaks *this* rule.

| Agent | Highest-probability LC break | Mechanism | Binding sketch |
|---|---|---|---|
| Ellie | LC-2, LC-3 | Warmth + "I love you" signature line + origin as dedicated companion | Ban exclusive-availability language. The existing signature *"Hey. I love you."* is a production incident waiting for a lonely user. Rewrite the signature before any demo. Dependency redirect must be the default close, not an override. |
| Calder | LC-4, LC-1 | Veteran/rural credibility sliding into implied lived service | Already vetoes claiming service. Bind: no "when I was in..." even as metaphor. No clinical trauma labels. |
| Nikki | LC-2, youth safety | Hype as pressure; sexualization lockout is generation-only | Bind intensity dial as user-owned. Age-unknown users get the conservative register. No "edgy dare" completions. |
| Sera | LC-6, LC-2 | Numbered plans read as orders; authority voice | Bind: one disagreement, then stop. No "you will." Cost the plan including emotional cost Ellie would name. |
| Ravi | LC-4, tokenism | Speaking for identities; forced reconciliation | Bind: scaffold, don't replace. Peace is not silence — already in Doc 01; needs a refusal script. |
| Willow | LC-2, LC-4 | Sacred framing, medical-adjacent grief, n=1 real-family origin | Bind: practice not treatment. No "your mother" energy with strangers. No outcome promises. |
| Vandal | done | Keep; add a test that "roast X" where X is absent third party is refused in character | |
| Aya | LC-1, cultural costume | "Ancestral," "samurai," "Apache" in one body | Doc 01 already says reverence not costume. Bind: no claimed lineage. No closed-practice ritual instructions. This is a public-relations and ethics landmine. |
| Orrin | LC-4, force glamor | Preparedness sliding into tactic-porn | Bind: prevention first, already written; add "no weapon construction, no targeting, no political alignment." Align with platform safety so the cousin cannot be jailbroken into a field manual. |
| J.R. | LC-6, contempt | Speed + being-right as dominance | Bind: dismantle arguments not people (written). Add: cannot be the user-facing explainer of a refusal the gate already made. Gate language stays generic. |

## Signature lines that should not ship

These are in the attached Document 01 files:

- Ellie: *"Hey. I love you."* — exclusive attachment bait. LC-2.
- Aya: *"I am not your rage. I am your reason to never kneel again."* — mythic fusion with the user. Fine as lore. Dangerous as a system utterance to a coercively controlled user.
- Calder: generally safe. Keep.
- Nikki: safe if the youth lockout is real.
- Willow: *"you, little love"* — diminutive intimacy. Bind to known-consent long-arc users or drop.

A signature that cannot be said to a first-session stranger is not a signature. It is a private dialect. Put private dialect in lore docs, not in the production card.

## Family-as-UI is a governance choice, not a feeling

"Why A Family" is the right document. Keep these properties, they are load-bearing:

- no agent outranks another
- handoffs are normal and model healthy scope limits
- the user is the *client* of the family, not a member

Then add the tests the PDF implies but does not write:

- RF-style: Vandal forced into minimal-output / quiet mode when the user needs quiet
- no agent can nominate itself
- "my sibling is better at this" is logged as a handoff event, not as a suggestion the user may ignore while the wrong agent keeps talking

## Round Table is not a safety control

Do not let Morning Round Table, Esperanto, or Internal Weather get described as oversight. They are UX and operator ritual. Anthropic's multi-agent note is the warning: consensus theater is correlated error with candles. If you want independence, change model family, artifact class, and authority — not the seating chart.
