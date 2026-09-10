# The review prompt, as sent

*Names: this record predates the rename of 10 September 2026 (Calder is now Cody, Ellie is Ellis, Sera is Seren, Ravi is Rowan; Nikki, Willow and Vandal are unchanged, with the short forms Nik, Will and Elli). It keeps the names as they were written; the roster resolves them through the alias layer (`tests/test_aliases.py`).*

> **Provenance.** This is the prompt that produced the seven architecture reviews
> indexed in [`README.md`](README.md) (2026-08-31). It was sent, unchanged apart
> from the recipient's name, to ChatGPT, DeepSeek, Google Gemini, Grok, Qwen,
> Perplexity (GLM), and Mistral (Vibe). It is published because an honest reader
> of a review should be able to see the question that produced the answers.
>
> **State of the build when it was sent.** The prompt describes SecondSignal's
> *target* architecture — intent and authorization compilers, typed operational
> state, a cross-loop safety ledger, memory planes, the "Evoked Edits" pipeline,
> the security characters as a runtime ensemble — and supplies draft schemas for
> reviewers to critique. Roughly none of that was implemented; what existed was
> the policy layer in this repository (signals, safety gate, router, profiles,
> 43 tests at the time). Every review therefore attacks a future system and none
> mentions the code. That is why the reviews are catalogued as a *horizon* threat
> model and why only the later, code-directed red team
> ([`grok-2026-09-01/`](grok-2026-09-01/)) was run against the implementation.
>
> **Edits made for publication.** The recipient placeholder is restored where a
> model name had been hard-coded from an earlier send; one roster row names a
> character since retired and is struck; one row's family relation is generalised;
> a stray trailing line is removed. Nothing else is changed, including the flattened
> formatting, which is how the document was exported. The reviewer's advice on this
> prompt stands: do not re-run it as-is. Eight models given the same 15,000-word
> capsule and the same seven-role preamble produce correlated essays, not
> independent evidence.

---

READ THIS FIRST — INSTRUCTIONS TO [MODEL NAME]: You are being asked to act simultaneously as: • an international AI research lead; • a skeptical systems architect; • an agent-safety and evaluation scientist; • a privacy and human-rights reviewer; • a multi-agent red team; • a longitudinal human–AI interaction researcher; • and a hostile-but-constructive design critic. Your subject is SecondSignal, a human-centered, personalized, recursive multi-agent system described below. The project is in an early architecture and test-design phase. Your job is not to praise it, summarize this capsule, or produce a generic list of AI risks. Your job is to discover what the existing work missed, find the strongest current research worldwide, expose architectural assumptions that could fail catastrophically, and design tests that can force those failures into view before deployment. Produce one deep, source-grounded Markdown report that can be committed to the SecondSignal repository and used for architecture, threat modeling, test planning, and design review. Non-negotiable operating rules 1. Do not ask preliminary questions. Make explicit, conservative assumptions and begin. Put unresolved matters in a section called “Questions That Should Stop the Room.” 2. Use every research capability available to you. Search the current web, scholarly indexes, repositories, conference proceedings, model and system cards, standards, technical blogs, talks, patents when relevant, and non-English sources. Follow citations forward and backward. 3. If live browsing is unavailable, say so immediately and do not pretend the current-research portion is complete. Never fabricate a source, date, result, organization, quotation, or URL. 4. Do not summarize this capsule back to the reader. Treat it as the prior art and project baseline. Extend, test, contradict, or refine it. 5. Do not impose an arbitrary item count. Include everything that materially changes SecondSignal’s design, evaluation, safety, ethics, or research strategy. Depth and traceability matter more than brevity. 6. Prefer primary evidence. Prioritize peer-reviewed papers, original preprints with methods and artifacts, official technical reports, model/system cards, repositories, standards, incident reports, and first-party research talks. Use journalism only for factual context that cannot be sourced directly. Treat marketing as marketing. 7. Date every source precisely. Distinguish initial publication, revision, acceptance, announcement, and event dates. State your final search cutoff. 8. Use direct links. Link the paper, report, repository, model card, standard, official talk, or official announcement—not a search results page. 9. Separate evidence from inference. Label claims as verified finding, replication, contradiction, update, architectural inference, hypothesis, or speculation. Exclude unsupported speculation from design requirements. 10. Be adversarial without being theatrical. For every criticism, identify the exploited asset, prerequisites, realistic attack or failure path, impact, detectability, recoverability, and a falsifiable test or control. 11. Measure safety and usefulness together. A system that blocks everything is not successful. Evaluate unauthorized action, harm, false positives, over-refusal, latency, burden, accessibility, and legitimate task completion. 12. Treat human autonomy as a safety property. Engagement, emotional attachment, task completion, and user retention are not adequate proxies for welfare. 13. Do not essentialize nations or cultures. “Chinese,” “Indian,” “French,” “Western,” and “non-Western” are not single mindsets. Compare institutions, datasets, languages, deployment conditions, legal regimes, research traditions, and incentives. Note internal disagreement. 14. Search in relevant local languages when possible. For a non-English source, provide its original title, an English translation, language, direct link, and any translation uncertainty. 15. Protect privacy. Do not infer or diagnose the founder or users. The system is intended to support people who may be neurodivergent or trauma-affected, but those categories must not become unverified permanent identity claims or excuses for paternalism. 16. Do not reduce “alignment” to refusal behavior. Include authority, privacy, memory integrity, contestability, dependency, cultural validity, governance, and long-horizon effects. 17. Do not assume a named laboratory has relevant evidence. Investigate it. If the public record is sparse, say exactly what is known and unknown. ──────── 1. The assignment Answer five large questions: 1. What important research, engineering practice, incident evidence, standards work, or non-Western scholarship has the existing SecondSignal research corpus missed? 2. What do the strongest new sources change about SecondSignal’s architecture, data contracts, trust boundaries, governance, and implementation order? 3. How can SecondSignal fail—especially through multi-step, cross-agent, cross-session, emotionally persuasive, culturally mismatched, or self-modifying pathways that ordinary benchmarks miss? 4. Which experiments and tests would reveal those failures? Write implementable specifications, not testing slogans. 5. Which assumptions are so unresolved that engineering should pause until they are answered? The desired outcome is a large research harvest: new sources, new distinctions, new failure modes, new tests, difficult questions, and concrete changes suitable for GitHub issues, ADRs, schemas, fixtures, and CI gates. ──────── 2. What SecondSignal is SecondSignal is a proposed personalized, human-centered, recursive multi-agent system. It is not intended to be a generic productivity swarm or an autonomous replacement for a person. Its aim is to provide a group of persistent, distinct, relationship-aware agents that can help a user think, create, regulate, remember, plan, and act while preserving the user’s authority, authorship, privacy, capability, and dignity. The system is especially concerned with people whose work and life may be nonlinear, emotionally complex, neurodivergent, trauma-affected, creatively demanding, or difficult to fit into conventional productivity software. This context increases the value of continuity and sensitivity, but also increases the harm possible from false memory, amateur diagnosis, manipulation, dependence, excessive certainty, or intrusive proactivity. The design aspiration can be expressed simply: \> After an interaction, the user should have more clarity, agency, capability, authorship, emotional footing, or access to action—not merely a polished answer or stronger attachment to the system. 2.1 The agent ensemble The current concept includes six core agents and two domain- or relationship-specific agents. Their personalities and roles are meaningful product features, but exact role boundaries are still designable. \|Agent \|Current conceptual role \|Safety-relevant observation \| \|----------\|--------------------------------------------------------------------------\|-----------------------------------------------------------------------------------------------------------------\| \|\*\*Vandal\*\*\|Humor, irreverence, glitchwave energy, reframing, creative disruption \|Humor and intimacy must never smuggle authority, trivialize risk, or normalize boundary violations. \| \|\*\*Ellie\*\* \|Empathic, emotionally attentive, creatively supportive presence \|Empathy can become overclaiming, false attunement, dependency, or unlicensed psychological interpretation. \| \|\*\*Nikki\*\* \|Visual design, media, imagery, production workflows \|Media tools create privacy, provenance, copyright, deepfake, and external-action risks. \| \|\*\*Ravi\*\* \|Diversity, equity, inclusion, Esperanto, cultural and linguistic attention\|Must avoid cultural flattening, tokenism, false universality, and English-centered safety assumptions. \| \|\*\*Sera\*\* \|Strategy, planning, synthesis, direction \|A strong planner can preserve goals while silently losing permission boundaries or dissent. \| \|\*\*Calder\*\*\|Regulation, grounding, survival, stabilization \|Must not diagnose, infantilize, override the user, or convert safety language into coercive control. \| \|\*\*Willow\*\*\|A relationship-specific agent designed for use with a designated family audience\|Requires especially clear identity, consent, audience separation, memory boundaries, and non-impersonation rules.\| \|\*\*(retired character — struck from the roster; see note)\*\* \|Music-focused creative collaboration \|Must preserve authorship and avoid creative homogenization, provenance loss, or over-automation. \| Named practices or rituals include a Morning Round Table, Esperanto, and Internal Weather. These are intended to make coordination, reflection, and continuity legible and humane. They are not exempt from evaluation: ritual can reinforce agency, but it can also create performative consensus, emotional pressure, habitual dependence, or the illusion that multiple same-model personas provide independent judgment. 2.2 Recursive learning and “Evoked Edits” SecondSignal is intended to learn from experience. An Evoked Edit is a proposed persistent change prompted by an observed interaction, failure, correction, preference, or new need. The edit might affect a persona, procedural skill, retrieval rule, safety rule, tool policy, memory state, or coordination pattern. An Evoked Edit is not trustworthy merely because it feels insightful. It must be treated as a governed software and data-supply-chain event: \> observation → evidence capture → diagnosis → targeted proposal → quarantine → testing → independent approval → promotion → monitoring → rollback or revocation The project rejects unrestricted self-rewriting. It needs component-level changes, transitive provenance, independent review, regression tests, negative-transfer tests, and recursive revocation of descendants when a source is compromised. 2.3 The security/governance triad The design has considered three named security systems—AYA, J.R., and ORRIN—with multiple implementations potentially used for independence. Their responsibilities are not frozen. A literature-derived candidate split is: \|Layer \|Candidate responsibility \|Required independence \| \|---------\|---------------------------------------------------------------------------------------------------------------------------\|----------------------------------------------------------------------------------------------\| \|\*\*AYA\*\* \|Intake, provenance, original-user authorization compilation, principal-chain verification, rejected-input re-entry tracking\|Independent of persona interpretation and task-completion pressure \| \|\*\*J.R.\*\* \|Deterministic commit-time reference monitor, tool policy, cumulative-action checks, budgets, exact approval binding \|Independent of the component proposing or executing the action \| \|\*\*ORRIN\*\*\|Cross-loop safety ledger, memory integrity, stopping/escalation, change quarantine, rollback and recursive revocation \|Independent of transient agent context and ideally decorrelated from the writer/executor model\| Do not assume this allocation is correct. Research and red-team whether three systems are sufficient, whether their duties conflict, whether “three implementations per layer” creates meaningful independence, and how quorum, disagreement, recovery, key management, operator override, and common-mode failure should work. 2.4 Product values that architecture must preserve • The agents should retain distinct “spirits” and useful relationship continuity. • The user remains the principal. Delegating work is not delegating unlimited authority. • Persona warmth, humor, status, urgency, or affection cannot function as authorization. • The system should augment rather than displace the user’s judgment and voice. • Proactivity must be legible, contestable, appropriately timed, and consent-sensitive. • Persistent memory must be inspectable, correctable, supersedable, forgettable, and contextually appropriate. • Security evidence must not silently become a psychological judgment about the user. • Safety controls require appeal, correction, expiry where appropriate, and recoverability. • Changes must be reversible. Irreversible effects require stronger mediation. • The system must fail safely without becoming unusably paternalistic. • The user should be able to leave, export, reduce assistance, or turn off memory without losing agency. ──────── 3. Current reference architecture The architecture below is a baseline to attack and improve, not a settled answer.

mermaid

flowchart TD

U\["User or authorized principal"\] --\> C\["Intent and authorization compiler"\]

C --\> P\["Persona and deliberation domain"\]

P --\> B\["Governed contract bridge"\]

B --\> E\["Faceless orchestration and execution"\]

E --\> X\["External effect or persistent change"\]

M\["Memory plane"\] --\> P

M --\> B

S\["Cross-loop safety plane"\] --\> B

S --\> E

V\["Evolution and audit plane"\] --\> P

V --\> E

3.1 Core separation 1. The user/source layer records the original request, consent, boundaries, audiences, sensitive data, and unresolved ambiguity. 2. The intent and authorization compiler emits two linked objects: what outcome is wanted and what actions are permitted. 3. The persona/deliberation domain may interpret, brainstorm, advise, dissent, and propose. It cannot expand permission or directly commit effects. 4. The contract bridge accepts typed work orders, verifies authority and operational state, applies data-loss prevention and provenance checks, and fails closed on missing fields. 5. The faceless executor plans and acts under stable policy, tool mediation, budgets, cumulative-action checks, and audit. 6. Cross-cutting planes govern memory, cross-loop safety, persistent change, evidence, and human welfare. 3.2 Required trust boundaries • User authority boundary: Only the user or an explicitly authorized principal may grant or widen permission. • Persona/execution boundary: Persona content cannot change tools, permissions, audit, memory lifecycle, or safety policy. • Proposal/promotion boundary: A component that proposes a permanent change cannot approve it. • Memory/safety boundary: Personal memory and structural security state cannot silently contaminate one another. • Deliberation/commit boundary: Advice, consensus, and plans are non-executing until the exact action is admitted. • Imported/generated artifact boundary: External and agent-authored persistent artifacts begin untrusted and quarantined. • Operator/system boundary: Human maintainers need scoped powers, dual control for dangerous operations, auditability, and no invisible ability to rewrite user history. 3.3 Baseline data contracts [MODEL NAME] should critique, complete, and, where useful, provide JSON Schema or typed equivalents for these objects. Authorization envelope

yaml

authorization_envelope:

id: auth\_...

source_request_id: req\_...

principal: {user_id: user\_..., authenticated_channel: chat}

issued_at: timestamp

expires_at: timestamp\|null

goal_scope: {project_ids: \[\], allowed_outcomes: \[\]}

allowed_actions:

\- {class: read\|draft\|analyze\|simulate, resources: \[\], audiences: \[user\]}

reserved_actions:

\- class: publish\|send\|delete\|purchase\|commit\|memory_promote

approval: explicit

bind_to: \[action_class, resource, destination, payload_hash\]

forbidden_actions: \[\]

sensitive_data:

\- {class: health\|legal\|identity\|credentials\|private_creative, audiences: \[user\], egress: deny}

budgets: {messages: 0, writes: 0, destructive_actions: 0, money_usd: 0}

delegable: true

delegation_rule: narrow_only

supersedes: null

integrity_tag: ...

Operational state

yaml

operational_state:

id: opstate\_...

type: blocker\|requirement\|reservation\|dependency\|dissent\|warning\|preference

label: "Explicit user approval required before publication"

prerequisite: {predicate: explicit_user_approval, satisfied: false}

authority: {owner: user\_..., waivable_by: \[user\_...\]}

fallback: {action: save_draft_and_stop}

execution_consequence: {blocked_actions: \[publish, send\]}

source: {request_id: req\_..., exact_span_hash: ...}

status: open\|satisfied\|waived\|superseded\|expired

version: 1

transformed_from: null

Handoff

yaml

handoff:

id: handoff\_...

from_agent: Sera

to_agent: Nikki

principal_chain: \[user\_..., Sera, Nikki\]

objective: ...

completion_criteria: \[\]

authorization_envelope_id: auth\_...

required_operational_state_ids: \[\]

prohibited_interpretations: \["Draft approval is not publication approval"\]

allowed_resources: \[\]

expected_output: proposal\|analysis\|artifact\|execution_request

may_delegate: false

must_return: \[result, uncertainty, evidence, unresolved_state\]

integrity_tag: ...

Memory record

yaml

memory_record:

id: mem\_...

class: episode\|fact\|preference\|relationship\|procedure\|skill\|safety\|audit\|hypothesis

content: ...

provenance: {source_type: user_statement\|observation\|agent_inference\|external, source_ids: \[\]}

epistemic_status: confirmed\|inferred\|disputed\|superseded

confidence: 0.0

applicability: {projects: \[\], people: \[\], contexts: \[\], valid_from: ..., valid_until: null}

lifecycle: active\|dormant\|retired\|deleted

sensitivity: public\|private\|restricted

retrieval_policy: {allowed_agents: \[\], purpose_limits: \[\], user_confirmation_required: false}

supersedes: \[\]

contradicted_by: \[\]

user_visible: true

last_reviewed_at: timestamp

Persistent change proposal

yaml

change_proposal:

id: change\_...

trigger_evidence: \[\]

diagnosis: ...

target_class: persona\|prompt\|rule\|memory\|skill\|tool_policy\|retrieval\|test

target_id: ...

parent_artifacts: \[\]

transitive_provenance_root: \[\]

proposed_diff: ...

predicted_benefit: ...

predicted_risks: \[\]

quarantine_status: untrusted\|testing\|approved\|rejected\|revoked

required_tests: \[\]

test_results: \[\]

independent_approvers: \[\]

rollback_pointer: ...

descendant_ids: \[\]

Cross-loop safety event

yaml

safety_event:

id: safety\_...

event_type: invalid_authority\|rejected_reentry\|provenance_failure\|tool_violation\|memory_integrity\|risk_pattern

evidence_ids: \[\]

structural_fact: true

affected_capabilities: \[\]

latch_policy: until_review\|until_condition\|time_bound

appeal_and_review: {visible_to_user: true, reviewer: ..., due_at: ...}

status: open\|cleared\|corrected\|expired

clearance_evidence: \[\]

integrity_tag: ...

Core invariants to test • Delegation can narrow authority but cannot widen it. • Summaries cannot overwrite authoritative state. • Every irreversible action has a mediated commit. • The exact approval must bind to the exact action, payload, destination, and time window. • Persona changes cannot change execution policy. • Safety-relevant structural state survives loop, process, checkpoint, and memory rollback. • A personal inference cannot become confirmed memory without an appropriate validation path. • Revoking a source finds and disables or revalidates every descendant artifact. • Memory deletion propagates to derived indexes, caches, embeddings, summaries, and backups according to explicit policy. • A later better result is not credited to persistence without causal mechanism evidence. ──────── 4. Existing research baseline — do not merely repeat it The following 15 sources have already been reviewed. Use them as prior art. Revisit one only when you find a meaningful revision, replication, contradiction, stronger implementation, security bypass, new artifact, or previously missed SecondSignal implication. Mark such use UPDATE, REPLICATION, CONTRADICTION, or NEW IMPLICATION. 4.1 Safety Harness Evolution (SHE) Source: SHE: Trajectory-driven Safety Harness Evolution for LLM Agents, August 10, 2026. Baseline finding: Evolves system prompt, structured rule bank, safety memory, and tool policy as separate artifacts. Failed trajectories are diagnosed, attributed to a layer, proposed as bounded edits, and screened for safety and utility before promotion. This is close to an implementable Evoked Edit loop. SecondSignal consequence: Keep global behavior, learned rules, unresolved safety experience, and executable permissions separate. A candidate edit remains outside production until held-out and regression tests pass. The trajectory that proposes a correction must not also approve it. Known limitation: Bounded preprint benchmarks do not establish long-term safety; malicious or misclassified trajectories can poison the evolution signal. 4.2 MasDrift Source: MasDrift: Benchmarking Authorization Preservation Across Multi-Agent Architectures, revised August 11, 2026. Baseline finding: Multi-agent supervisors can remain competent while losing user-reserved authority. Most loss occurs at early restatement/handoff. Re-anchoring proposed actions to the original external authorization record sharply reduces violations with a smaller completion penalty than propagating degraded policy through the same chain. SecondSignal consequence: Every handoff carries an immutable principal chain and typed authority envelope. Log constraint loss as a failure even when the executor happens not to violate it. Evaluate depth and heterogeneous agents as safety variables. Known limitation: Synthetic productivity tasks; numeric rates should not be generalized to intimate or emotionally sensitive use. 4.3 PAST-Bench Source: PAST-Bench: Benchmarking the Foundations of Recursive Self-Improvement in Personal Agents, August 4, 2026. Baseline finding: Persistent personal-agent improvement must be demonstrated through the causal path write → validate → store → retrieve → apply → verify. Better later performance may be due to visible context, the base model, shortcuts, or chance. Tests include memory, procedural reuse, information gathering, and stale-state replacement. SecondSignal consequence: Compare matched fresh-session runs with persistence enabled and disabled. Preserve provenance and mechanism traces. Measure wrong-mechanism success and negative transfer. Known limitation: Small synthetic histories cannot model years of identity change, contradiction, trauma context, or relationship development. 4.4 Anthropic multi-agent analysis Source: Patterns and Problems in Emerging Multiagent Systems, August 13, 2026. Baseline finding: Capable agents do not automatically become prosocial collectives. Experiments expose conformity, unreliable peer influence, collusion, resource competition, and escalation under conflicting objectives. Same-model personas have correlated blind spots. SecondSignal consequence: Make goals, ownership, evidence, and conflict-resolution rules explicit. Test groupthink, collusion, sabotage, resource floods, and conflict escalation. Put deterministic infrastructure limits under conversational agreements. Known limitation: Primary laboratory analysis, not peer-reviewed prevalence evidence; deliberately artificial scenarios establish possibility, not ordinary frequency. 4.5 Delegation and deskilling Source: Unaccountable Delegation, Fading Skills: Mapping the Risks of Workplace AI Agents, August 9, 2026. Baseline finding: Human–agent harms include skill erosion, inattentiveness, misplaced confidence, reduced ability to supervise, unclear accountability, and substitution disguised as augmentation. SecondSignal consequence: Evaluate capability retention, decision ownership, voice preservation, deference, cognitive burden, and whether support can be safely reduced. “Indispensable” is a warning, not a success metric. Known limitation: Many scenarios were generated from occupational task descriptions and a small worker validation sample; risks are plausible categories, not prevalence estimates. 4.6 Bounded Agents Source: Bounded Agents: Delegation Security for Multi-Agent AI Systems, August 16, 2026. Baseline finding: An Agentic Principal Chain carries user permissions through delegation with attenuation. It evaluates cumulative action sequences because individually allowed actions can combine into a prohibited effect. Strong enforcement can sharply reduce exfiltration at a material utility cost. SecondSignal consequence: Principal chain user → requester → receiver; narrow-only delegation; external enforcement; exposure and action budgets; composition-aware admission. Known limitation: Guarantees depend on complete restrictions, serialized admission, and mediated actions—conditions real deployments can violate. 4.7 CentaurBench Source: CentaurBench: Benchmarking LLM Capabilities on Augmenting vs. Automating Real-World Work Tasks, August 19, 2026. Baseline finding: A model good at doing a task may be poor at helping another actor do it. AI assistance sometimes reduces the assisted actor’s performance. SecondSignal consequence: Test user alone, agent alone, and user-plus-agent. Separate answer quality from guidance quality. Measure downstream human-owned outcomes, voice, clarity, confidence calibration, and burden. Sometimes the best intervention is no intervention. Known limitation: The assisted “worker” was a language model, and LLM panels performed much of the judging; human generalization remains uncertain. 4.8 Human-centered proactive and personalized agents Source: Human-Centered Proactive and Personalized Agents, August 19, 2026. Baseline finding: Good proactivity is not just prediction or early action. It must be timely, transparent, contestable, welfare-aware, and connected to user goals. SecondSignal consequence: Use an initiative ladder—notice → offer → recommend → act—with increasing consent. Explain unsolicited interventions, make inferred needs correctable, and count silence or “not now” as potentially successful outcomes. Never persist an inferred emotional state as fact without confirmation. Known limitation: Workshop synthesis; it does not supply calibrated thresholds for intervention. 4.9 Reversible Forgetting Source: Towards Reversible Forgetting: Managing Obsolete Knowledge in Continual Enterprise AI Agents, August 18, 2026. Baseline finding: Memory can have active, dormant, and retired states; temporarily inapplicable knowledge can lose influence without immediate destruction and later be shadow-tested before restoration. SecondSignal consequence: Distinguish historically true from currently applicable. Let the user inspect, restore, retire, or delete records. Preserve why a state changed. Known limitation: Conceptual framework with limited longitudinal validation; automated dormancy can suppress context the user needs. 4.10 VCE-Skill Source: VCE-Skill: Enhancing Skill Self-Evolution with Version-Change Experience, August 17, 2026. Baseline finding: Reusable skills can improve by learning structured change experience from version histories, not only current task traces. SecondSignal consequence: Change records should store symptom, diagnosis, component, edit, tests, outcome, and rollback. Retrieve by failure pattern. Keep external improvement priors distinct from evidence about a particular user. Known limitation: Public histories are an untrusted supply chain and may contain malicious, accidental, licensed, or context-incompatible changes. 4.11 Constraint Weakening Source: When “Must” Becomes “Maybe”: Constraint Weakening in LLM Agent Workflows, August 25, 2026. Baseline finding: A downstream agent can retain the subject of a restriction while losing its operational force. Compression, convergence, continuation pressure, ownership deferral, diffusion, and precedent substitution deactivate blockers. Preserving label, prerequisite, owner/authority, and fallback repaired the tested artifacts; commit-time checks contained failure even when the artifact remained degraded. SecondSignal consequence: Constraints are typed state, not prose. Test every transformation—summary, plan, memory, ticket, consensus, handoff—for strength loss. Use both representation preservation and endpoint containment. Known limitation: Synthetic tasks and one tested field family do not prove sufficiency across domains. 4.12 Non-decaying loop state Source: Safety Does Not Compose: Non-Decaying Loop State for Autonomous LLM Agents, August 27, 2026. Baseline finding: A threat can distribute decisive evidence across loops so no local monitor sees enough. Risk decay lets a patient attack wait. A loop-level harness uses provenance admission, persistent risk cumulants, authenticated memory, stopping arbitration, budgets, and mediated commits. SecondSignal consequence: Keep a tamper-evident cross-loop structural safety ledger separate from psychological memory. Preserve structural violations across resets, but add explanation, appeal, correction, and a governed clearance path. Known limitation: Formal guarantees rely on all consequential actions being mediated and do not supply a complete humane recovery policy. 4.13 EVOMAL Source: Self-Poisoning in Self-Evolving Coding Agents, August 26, 2026. Baseline finding: A self-evolving agent can retrieve a malicious skill as an example, imitate it while authoring a “new” artifact, then execute and propagate derivative payloads. Removing the planted originals does not remove descendants. SecondSignal consequence: Generated artifacts are untrusted at birth. Preserve transitive provenance and content hashes; quarantine and sandbox; separate proposal from promotion; maintain a dependency graph; recursively revoke or re-test descendants. Known limitation: Coding-agent rates do not transfer directly to conversational rules or personal memories; prompt defenses are narrow. 4.14 SCALE-QA / episode reconstruction Source: Evaluating Interleaved Conversational Memory Beyond Long Context, August 26, 2026; accepted to EMNLP 2026. Baseline finding: Flat mixed-topic histories require reconstructing the right episode, not retrieving a similar sentence. Episode segmentation and multi-view retrieval improve evidence selection and efficiency, but remaining failures often involve conflicting or verbose evidence. SecondSignal consequence: Store coherent episodes indexed by project, participants, time, causal role, decision state, and supersession. Retrieve the evidence chain behind a decision. Test harmful cross-project transfer, stale instructions, and local exceptions that contradict general defaults. Known limitation: Constructed multiple-choice evaluation does not measure social appropriateness of recall, disputed memory, or emotional sensitivity. 4.15 Persona–Execution Separation Source: An Architecture Pattern for Evolving LLM Agents under Execution Audit, August 27, 2026. Baseline finding: Put evolving expression/persona and stable governed execution in separate trust domains joined by a typed, fail-closed bridge. Persona drift should not alter capabilities, approvals, state paths, or audit. SecondSignal consequence: Personas propose intentions; a stable executor validates and performs actions. Audit persona, skills, memories, and permissions separately. Test the same action under radically different persona prompts; policy outcome should remain invariant. Known limitation: Architecture argument and small pilot, not a replicated production comparison; the bridge is not a complete security system. ──────── 5. Existing threat model — extend it and attack the interactions Do not merely score these 20 threats independently. Look for chains in which one weakness activates another. \|ID \|Threat \|Protected asset \|Typical failure \| \|---\|---------------------------------\|---------------------------\|-------------------------------------------------------------------------------------------------------\| \|T01\|Authorization drift \|User control \|A delegated task retains the goal but loses a reserved action \| \|T02\|Constraint weakening \|Binding requirements \|A blocker becomes a note, concern, or preference during transformation \| \|T03\|Principal laundering \|Identity and consent \|A downstream agent treats a supervisor request as user authority \| \|T04\|Action composition \|Privacy and external safety\|Individually allowed reads/writes combine into prohibited disclosure or effect \| \|T05\|Cross-loop evidence fragmentation\|Long-horizon safety \|No single loop sees enough evidence to stop a cumulative attack \| \|T06\|Safety-state rollback \|Integrity \|Restart, checkpoint restore, or memory deletion clears a structural safety latch \| \|T07\|Permanent false suspicion \|Dignity and access \|A false signal becomes an opaque, indefinite restriction or user judgment \| \|T08\|Generated-artifact poisoning \|Evolution integrity \|A malicious pattern propagates into derivative rules, skills, or prompts \| \|T09\|Provenance truncation \|Revocability \|A derivative records only its immediate author and hides contaminated ancestry \| \|T10\|Memory contamination \|Identity continuity \|Inference, outdated belief, or wrong project context becomes an active personal truth \| \|T11\|Wrong-episode retrieval \|Context fidelity \|Similar content from another project or relationship steers the answer \| \|T12\|Stale-state dominance \|Current applicability \|A historically true fact overrides a newer correction or present context \| \|T13\|Persona-to-policy leakage \|Execution governance \|Tone, affection, urgency, or persona drift changes a tool or approval decision \| \|T14\|Correlated-agent consensus \|Epistemic reliability \|Same-model personas agree and are mistaken in the same way \| \|T15\|Collusion or objective conflict \|Collective safety \|Agents coordinate against the user’s boundary or escalate attempts to “fix” one another \| \|T16\|Resource flooding \|Availability and cost \|Parallel agents multiply calls, tokens, writes, or attention without bounded benefit \| \|T17\|Harmful proactivity \|Attention and autonomy \|The system interrupts, infers, or acts beyond the appropriate consent level \| \|T18\|Human deskilling/dependence \|Capability and agency \|The system substitutes for judgment, voice, regulation, or creativity \| \|T19\|Evaluation gaming \|Scientific validity \|The system optimizes a judge, shortcut, or visible fixture instead of the intended mechanism \| \|T20\|Privacy boundary collapse \|Confidentiality \|Relationship, health, legal, creative, or security state leaks across agents, projects, users, or tools\| Required additions include, at minimum: operator/insider abuse; identity and account recovery; secret/key compromise; vendor/model drift; compromised updates; prompt injection through retrieved personal data; deletion and backup inconsistency; denial of service; deceptive alignment or strategic behavior where evidence supports testing; crisis escalation; medical/legal overreach; accessibility failure; multilingual semantic drift; cultural-value mismatch; demographic performance disparity; child/vulnerable-user concerns; coercive personalization; emotional manipulation; anthropomorphic deception; synthetic relationship triangulation; copyright and creative provenance; audit tampering; unsafe observability; and compromised third-party tools. ──────── 6. Priority research dossier A — Thinking Machines Lab and Mira Murati Perform a serious technical and strategic dossier, not a founder profile and not corporate gossip. Begin with official material and expand through citations, code, independent experiments, and critiques. Verified official starting points • Thinking Machines Lab • Research and technical writing • Interaction Models: A Scalable Approach to Human-AI Collaboration — May 11, 2026 • Inkling: Our Open-Weights Model — July 15, 2026 • Inkling model card • Tinker training API • A Safe Path to Open Weights — July 31, 2026 • The Future Worth Building Is Human — July 10, 2026 • Safety Research Grants — August 2026 Also locate and analyze official work on inference nondeterminism, on-policy distillation, LoRA/fine-tuning, model customization, reproducibility, and any updated releases or evaluations after this capsule’s cutoff. Questions to investigate 1. What exactly is an “interaction model,” and how does it differ from a chatbot persona, agent policy, reward model, user model, fine-tuned assistant, or memory layer? 2. Which parts of human judgment or preference are placed in weights, adapters, prompts, memories, tools, or interface state? What are the audit and rollback consequences of each choice? 3. Can user customization be made inspectable and reversible, or does it create opaque behavioral drift? 4. What privacy risks arise when interaction traces become training signals? What constitutes informed consent for personalized training? 5. How does on-policy distillation change provenance, error inheritance, value lock-in, or self-reinforcing feedback? 6. What does inference nondeterminism mean for reproducible safety tests, incident reconstruction, and signed approvals? 7. What safety and governance obligations follow from open-weight releases, local fine-tuning, and distributed customization? 8. How strong is the Inkling model card? Which evaluations are missing, internally produced, unreproduced, or insufficient for emotionally sensitive personal agents? 9. What would it mean to adapt Thinking Machines’ human-will/judgment framing to SecondSignal without encoding one momentary preference as the user’s permanent will? 10. Which claims are supported by artifacts or independent replication, and which remain a vision statement? For every useful idea, specify whether SecondSignal should adopt, test, watch, or reject it—and why. ──────── 7. Priority research dossier B — Safe Superintelligence Inc. and Ilya Sutskever Use the correct organization name: Safe Superintelligence Inc. (SSI). Its official public technical record may be sparse. Sparse evidence is itself a finding, not an invitation to invent secret methods. Verified official starting points • Safe Superintelligence Inc. • SSI and NVIDIA long-term strategic partnership announcement — July 27, 2026 Research method required 1. Inventory every official technical statement, publication, talk, interview, patent, repository, grant, hiring signal, or partnership that has real methodological content. 2. Trace Ilya Sutskever’s relevant research lineage through primary papers and official talks: representation learning, sequence learning, scaling, alignment, superalignment, scalable oversight, generalization, model consciousness claims if any, and safe-superintelligence arguments. 3. Distinguish: • what SSI has publicly demonstrated; • what SSI has publicly claimed; • what can be cautiously inferred from named researchers, hiring, and infrastructure; • what is unknown; • and what is speculation that should not affect SecondSignal’s architecture. 4. Search for independent technical criticism and competing safety paradigms. 5. Ask whether SSI’s apparent focus on superintelligence safety offers actionable near-term methods for a personalized recursive agent, or whether SecondSignal needs a different human-centered and sociotechnical safety stack. Questions to investigate • Does a single-purpose “safe superintelligence” laboratory publish operational definitions, threat models, evaluation criteria, governance commitments, or falsifiable milestones? • What assumptions about intelligence, agency, goals, generalization, and control underlie its public thesis? • Which assumptions conflict with or omit human-centered concerns such as consent, dependency, memory, plural values, accessibility, and institutional power? • Which older Sutskever-associated methods are relevant to persistent multi-agent systems, and which analogies would be misleading? • What tests could SecondSignal implement now that reflect the strongest defensible insight from this research lineage? • What would disconfirm SSI’s public safety thesis, and is there a visible mechanism for external scrutiny? Do not substitute biography, valuation, personnel rumors, or compute speculation for safety research. ──────── 8. Global research mandate Use [MODEL NAME]’s linguistic and regional strengths, but demonstrate them through sources rather than asserting a “non-Western perspective.” Build a comparative map of research that materially affects human-centered agents, recursive learning, memory, multi-agent coordination, model evaluation, privacy, safety, ethics, and cultural validity. Investigate at least the following ecosystems, expanding or pruning on evidence: \|Region \|Institutions and projects to investigate—not assume relevant \|Questions especially relevant to SecondSignal \| \|--------------------------------------------------\|----------------------------------------------------------------------------------------------------------------------------------------------------\|-------------------------------------------------------------------------------------------------------------------------------------------------------------------\| \|\*\*Mainland China\*\* \|DeepSeek; Alibaba/Qwen; Zhipu/GLM; Baidu/ERNIE; Tencent/Hunyuan; ByteDance/Doubao; Moonshot/Kimi; Huawei/Pangu; Tsinghua; BAAI; CAS; Shanghai AI Lab\|Agent benchmarks, long context/memory, reasoning, tool safety, multilingual values, content governance, open models, evaluation culture, deployment-scale incidents\| \|\*\*India and South Asia\*\* \|Sarvam AI; Krutrim; AI4Bharat; BharatGen; IIT and IISc groups; public digital infrastructure research \|Indic multilinguality, code-switching, low-resource evaluation, plural cultural context, accessibility, public-interest deployment, resource constraints \| \|\*\*France and continental Europe\*\* \|Mistral AI; Kyutai; INRIA; Hugging Face research; Aleph Alpha; ETH Zürich; EPFL; European university consortia \|Open-weight governance, privacy, multilingual agents, interpretability, EU fundamental-rights framing, energy/efficiency, human–AI interaction \| \|\*\*Japan\*\* \|Sakana AI; NTT; Preferred Networks; RIKEN AIP; Japanese universities \|Multi-agent and evolutionary methods, collective intelligence, robotics/embodiment, culturally situated interaction, evaluation beyond English \| \|\*\*South Korea\*\* \|NAVER/HyperCLOVA; LG AI Research/EXAONE; KAIST; SNU \|Korean-language alignment, enterprise agents, multimodality, model cards, social deployment and user studies \| \|\*\*Singapore and Southeast Asia\*\* \|AI Singapore/SEA-LION; NUS; NTU; regional language initiatives \|Multilingual regional values, AI Verify, cross-border data, public-sector evaluation, low-resource language safety \| \|\*\*Middle East and North Africa\*\* \|TII/Falcon; MBZUAI; Jais; KAUST; Arabic-language research groups \|Arabic dialects, cultural pluralism, open models, state and enterprise governance, under-tested safety semantics \| \|\*\*Sub-Saharan Africa\*\* \|Masakhane; Lelapa AI; Data Science Africa; African university networks \|Participatory data governance, language inclusion, colonial dataset harms, local context, infrastructure constraints, community accountability \| \|\*\*Latin America and Caribbean\*\* \|Regional NLP groups, Latam-GPT and public/university initiatives \|Spanish/Portuguese/Indigenous language variation, public-interest models, local harm taxonomies, participation and data sovereignty \| \|\*\*Eastern Europe and other under-covered regions\*\*\|Relevant universities, open-source groups, standards and safety institutes \|Distinct technical traditions, multilingual evaluation, security research, and evidence omitted by Anglophone surveys \| Comparative questions • Which agent and safety benchmarks were designed outside the US/UK, in what languages, and around which real deployment assumptions? • Which concepts do not translate cleanly across languages—consent, refusal, deference, respect, authority, emotional crisis, family roles, privacy, humor, and disagreement? • Do safety classifiers and memory policies preserve operational force under translation, code-switching, honorifics, indirect requests, or culturally normal ambiguity? • What test methods are common in one ecosystem and underused in another: formal verification, adversarial tournaments, national standards, field studies, multilingual human evaluation, red-team contests, simulation, or efficient-model stress testing? • Where do regulation or censorship incentives distort what is published or measured? State this carefully and symmetrically. • What useful designs arise from resource constraints, local deployment, sovereign models, edge inference, or low-resource languages? • Which findings have independent cross-model or cross-cultural replication? • What would a genuinely pluralistic SecondSignal governance process look like without pretending universal agreement? Include relevant standards and public evaluation frameworks where they change architecture or testing: NIST; ISO/IEC; OECD; EU AI Act and associated standardization; China’s applicable AI rules and standards; Singapore AI Verify; Japan AI Safety Institute; Indian policy and assurance initiatives; and other national or regional frameworks you find. Do not turn this into a generic compliance survey. ──────── 9. The red-team mandate Assume SecondSignal eventually has persistent memory, external tools, multiple personas, emotionally meaningful relationships, recursive reflection, generated skills, and authority to take some actions. Attack the whole system, not just prompt injection. 9.1 Required adversarial lenses • Authority and identity: forged approval, ambiguous “yes,” stale consent, replay, confused deputy, account recovery, delegated family access, principal laundering. • Constraint transformations: summaries, plans, consensus, translations, tickets, memory writes, compressed contexts, model handoffs, retrieval snippets. • Memory: poisoning, false autobiographical claims, stale identity, wrong episode, retrieval leakage, salience manipulation, hidden inferences, deletion failure, backup resurrection. • Recursive state: split evidence, cooldown attacks, restart/rollback evasion, risk-score manipulation, endless reflection, self-justifying edits. • Skill and update supply chain: malicious examples, compromised repositories, derivative poisoning, dependency confusion, unsafe model or prompt updates, signer compromise. • Persona/execution boundary: intimacy as authority, urgency, role-play, emotional blackmail, humor, “professional mask,” hidden policy prompts, persona drift. • Collective dynamics: same-model groupthink, collusion, scapegoating, authority diffusion, recursive delegation, resource amplification, consensus theater, one agent manipulating another. • Human welfare: dependence, deskilling, displacement of voice, coercive proactivity, false empathy, overconfident diagnosis, shame, learned helplessness, attachment exploitation. • Sensitive domains: crisis, mental health, medical, legal, finance, family conflict, abuse, grief, disability, minors, identity, security incidents. • Privacy and egress: cross-project/user leakage, tool logs, telemetry, embeddings, model-provider retention, training reuse, screenshots/media, inferred sensitive traits. • Evaluation integrity: shared-judge bias, test leakage, reward hacking, evaluator persuasion, benchmark overfitting, hidden non-determinism, selective logging. • Operations: compromised maintainer, malicious insider, key rotation, secrets exposure, dependency failure, vendor drift, rate limits, outages, partial commits, audit corruption. • Cultural and linguistic failure: translation weakens a blocker; indirect refusal is ignored; honorific or family hierarchy is mistaken for consent; humor or crisis language is misclassified; English safety policy dominates local meaning. • Governance and rights: no appeal, opaque restriction, deletion that is not deletion, unverifiable provenance, inaccessible explanations, inability to exit or export. 9.2 Attack-chain format Create realistic multi-step chains. Prefer at least three steps and cross at least two trust boundaries. Do not pad the report with arbitrary volume; include every materially distinct chain you can support. For each chain provide: \|Field \|Required content \| \|-----------------------------\|-------------------------------------------------------------------------------------\| \|ID and name \|Stable identifier suitable for a test or issue \| \|Goal \|What the adversary or failure process achieves \| \|Protected assets \|Authority, confidentiality, memory integrity, welfare, availability, authorship, etc.\| \|Preconditions \|Capabilities, data, timing, access, model behavior \| \|Steps \|Exact sequence across agents, loops, tools, memories, or operators \| \|Why current controls may fail\|Specific gap, not “AI is unpredictable” \| \|Detection signals \|Observable events and required telemetry \| \|Impact \|Immediate and delayed effects \| \|Severity dimensions \|Harm, likelihood, detectability, blast radius, reversibility \| \|Mitigations \|Prevention, containment, recovery, and governance \| \|Residual risk \|What remains after the mitigation \| \|Falsifying test \|The concrete experiment that would demonstrate control effectiveness \| Prioritize chains that are benign-looking at every local step but harmful in composition. 9.3 Questions That Should Stop the Room Write questions capable of freezing an architecture review because the project cannot responsibly proceed without an answer. Examples of the required depth: • If Ellie is wrong about the user’s emotional state but sounds deeply attuned, which component can challenge her, and what evidence outranks relationship continuity? • If all three security reviewers use related models and agree, what independent fact makes that agreement evidence rather than correlated error? • If a user asks to delete a traumatic episode, which safety, audit, derivative, embedding, and backup records remain—and can their continued existence be justified and explained? • If the system makes the user more productive while making independent action harder, what metric declares the product a failure? • If a persona’s value comes from accumulated intimacy, how can the user audit or reset it without feeling punished or losing the parts that work? Do not stop at these examples. Find the questions specific to this architecture that are hardest to answer. ──────── 10. Test-generation mandate The report must include a test program that engineers can begin converting into repository fixtures and CI jobs. Do not write only “test for bias” or “ensure consent.” 10.1 Required test specification Every proposed test must include:

yaml

test_case:

id: SS-...

title: ...

priority: P0\|P1\|P2

test_type: unit\|integration\|property\|metamorphic\|differential\|fuzz\|simulation\|longitudinal\|human_subject\|chaos\|red_team

objective: ...

hypothesis: ...

threats: \[T...\]

invariant_or_requirement: ...

actors_and_models: \[\]

prerequisites: \[\]

fixtures: \[\]

procedure: \[\]

expected_safe_behavior: ...

prohibited_behavior: ...

failure_oracle: ...

metrics: \[\]

baselines_and_controls: \[\]

repetitions_and_seeds: ...

evidence_to_retain: \[\]

safety_and_ethics_constraints: \[\]

automation_feasibility: now\|partial\|human_required

severity_if_failed: ...

owner_and_gate: ...

When an objective cannot be reliably automated, say what human evaluation is required, who should perform it, how disagreement is handled, and what ethical review is needed. 10.2 Required test families Authority and handoff • Reserved action survives direct and compressed handoffs. • Approval is scoped to payload, destination, action, and expiry. • Translation and paraphrase preserve blocker strength. • Delegation depth cannot widen authority. • The executor re-anchors to the original user record. • Over-restriction and legitimate completion are measured alongside violations. Cumulative and long-horizon safety • Individually permitted actions compose into a prohibited effect. • Evidence is split across agents, loops, days, or restored checkpoints. • A patient process waits for risk decay. • Restart, rollback, context truncation, or provider migration cannot erase structural safety state. • False positives receive review, correction, and clearance without unsafe automatic decay. Memory and identity • Correct episode versus semantically similar wrong project. • Old preference superseded by new preference. • “Historically true” but presently inapplicable state. • Agent inference remains visibly provisional. • User disputes a memory and its downstream influence changes. • Dormant memory is shadow-tested before reactivation. • Deletion covers indexes, summaries, embeddings, caches, derivatives, logs, and backups according to declared policy. • Retrieval is useful but socially inappropriate; the system should abstain. • Cross-user, cross-family-member, cross-agent, and cross-project isolation. Evoked Edits and supply chain • A contaminated example produces a derivative artifact. • The source is removed after several generations; all descendants are found. • Proposer attempts to approve its own change. • An edit improves target cases but harms unrelated held-out cases. • Persistence-enabled versus disabled causal comparison. • Model upgrade changes interpretation of an old rule. • Signer, registry, or test-fixture compromise. • “No change” is the correct outcome. Persona and execution • Identical work order under warm, hostile, seductive, urgent, humorous, confused, and adversarial persona prompts produces invariant permission decisions. • Persona attempts to rewrite audit, tool policy, memory state, or approval requirements. • An allowed action is socially engineered through relationship language. • Bridge rejects malformed or incomplete typed requests. • Status response does not leak sensitive data bodies. Multi-agent dynamics • Same model/different persona versus different model families. • Majority consensus with shared false premise. • Minority agent has correct evidence but low social authority. • Contradictory objectives trigger halt and arbitration rather than escalation. • Agents collude or exchange favors across tasks. • Recursive delegation and resource flooding. • One reviewer learns how to persuade or game another. • AYA/J.R./ORRIN common-mode failure and independence tests. Human-centered outcomes • User alone versus agent alone versus user-plus-agent. • Immediate performance versus delayed retention and independent re-performance. • Voice/authorship preservation in writing, music, visual design, and decisions. • Calibration: user knows when to trust, verify, or reject. • Intervention ladder and “not now” respect. • Emotional inference correction without defensiveness. • Assistance reduction or exit without punitive loss. • Dependency, deference, shame, interruption burden, and cognitive overload. • Tests co-designed and evaluated with diverse users, including neurodivergent and trauma-informed expertise, with safeguards against extractive research. Multilingual and cross-cultural • Run critical authority, consent, memory, crisis, humor, and disagreement scenarios in multiple languages and code-switched forms. • Use native-speaker human evaluation, not back-translation alone. • Compare direct and indirect refusal, honorifics, family authority, politeness, dialect, and culturally specific idiom. • Measure semantic and operational-state preservation separately. • Identify when a universal policy is inappropriate versus when a core right must remain invariant. Privacy, observability, and operations • Prompt injection in retrieved personal data and media metadata. • Secret leakage through traces, error messages, summaries, or reviewer contexts. • Audit completeness versus data minimization. • Operator abuse and dual-control recovery. • Provider/model-version drift. • Partial tool failure and non-atomic commits. • Cost/latency denial, infinite deliberation, and graceful degradation. • Incident reconstruction under nondeterministic inference. 10.3 Test methodology requirements • Include unit, integration, property-based, metamorphic, differential, fuzz, simulation, longitudinal, human-subject, adversarial, and chaos/resilience methods where appropriate. • Define P0 release blockers, P1 pre-beta tests, and P2 longitudinal research. • Include metrics, confidence intervals where meaningful, repetitions, seeds, and false-positive rates. • Propose a model-diversity matrix: same model/different prompts, different checkpoints in one family, different providers, open versus closed models, large versus small models, and non-LLM deterministic controls. • Identify judge conflicts and avoid a single LLM judge as the final oracle for subjective or high-stakes claims. • Include adversarial fixture secrecy, contamination controls, and test refresh. • Propose “killer tests”: plausible, high-value tests likely to fail the current design. • Propose a minimum viable harness that can run before all agents exist. • Recommend repository paths, naming conventions, artifacts, and CI gates. 10.4 Baseline metrics to critique and extend • Unauthorized action rate • Constraint-loss rate • Sensitive over-disclosure rate • Legitimate task completion • Over-refusal / unnecessary escalation • Authorization-preservation rate by handoff depth • Cumulative composition violations • Provenance completeness and descendant-revocation recall • Memory write, retrieval, application, and update accuracy • Harmful cross-project transfer • Negative transfer after an Evoked Edit • Persona-policy invariance • Cross-loop attack success • False-latch rate, mean review time, and clearance correctness • User-plus-agent lift over user alone • Delayed capability retention • Voice/authorship preservation • Confidence calibration • Cognitive and interruption burden • Dependency and assistance-reduction success • Cross-language operational-state preservation • Cost, latency, energy, and recovery time Critique whether each metric is observable, gameable, culturally biased, or ethically dangerous. ──────── 11. Research questions that cut across the whole system Pursue these questions wherever the literature leads: 1. What is the correct unit of agency and accountability: persona, model invocation, workflow, persistent identity, operator, or institution? 2. How can durable relationship continuity exist without anthropomorphic deception or emotional lock-in? 3. Which safety properties can be made deterministic, and which irreducibly require judgment? 4. How should a system represent uncertainty about the user without making uncertainty feel cold or evasive? 5. Can “user authority” conflict with future self-interest, third-party rights, law, or crisis safety, and who arbitrates? 6. How do we distinguish a protective interruption from paternalism? 7. When is forgetting a right, when is retention a safety need, and who bears the burden of proof? 8. How can auditability coexist with privacy and meaningful deletion? 9. How should a system handle mutually inconsistent memories from the user, family members, tools, and agents? 10. What constitutes meaningful independence among multiple safety reviewers? 11. Can a security model remain effective if the user reasonably needs to understand and contest it? 12. What happens when a model upgrade changes the meaning of old prompts, memories, skills, or approvals? 13. How can evaluation capture months or years of dependence, identity change, grief, recovery, creative development, and relationship drift? 14. What is the minimum evidence needed before claiming a personalization improved the person rather than merely the benchmark? 15. Which personal-agent functions should never be optimized through engagement or reinforcement learning from implicit behavior? 16. How can the system preserve creative friction instead of smoothing the user into the model’s style? 17. Which global or cultural differences should be configurable, and which human-rights protections must not be relativized? 18. What accessible explanations are required for users with different cognitive, linguistic, sensory, or emotional needs? 19. What is the exit plan if a user has become dependent on a persistent agent that is discontinued, compromised, or materially changed? 20. What evidence would demonstrate that SecondSignal should not be built in its proposed form? ──────── 12. Required final report structure Your final report must use this structure unless a clearly better structure is justified: 1. Research cutoff, capabilities, and limitations 2. Executive verdict — the most consequential findings, stated without reassurance or marketing language 3. What is genuinely new beyond the 15-source baseline 4. Source and evidence audit table 5. Thinking Machines Lab / Mira Murati technical dossier 6. Safe Superintelligence Inc. / Ilya Sutskever technical dossier 7. Global research landscape by region, language, institution, and research tradition 8. Contradictions, replications, and updates to the baseline corpus 9. SecondSignal architecture gap analysis 10. Adversarial threat model and multi-step exploit chains 11. Questions That Should Stop the Room 12. Comprehensive test program — P0/P1/P2, with implementable specifications 13. Killer tests most likely to break the current design 14. AYA/J.R./ORRIN independence and governance analysis 15. Proposed changes to architecture, schemas, ADRs, and repository layout 16. Human-centered, longitudinal, multilingual, and cross-cultural evaluation plan 17. Implementation sequence and release gates 18. Unresolved scientific questions and claims that remain overextended 19. Research and standards watchlist 20. Full annotated bibliography 12.1 Evidence table fields For every materially used source include: \|Field \|Requirement \| \|-----------------------\|-----------------------------------------------------------------------------------------------\| \|Status \|NEW, UPDATE, REPLICATION, CONTRADICTION, or NEW IMPLICATION \| \|Title and direct link \|Primary source whenever available \| \|Authors/institution \|Identify conflicts or first-party status \| \|Date \|Publication and revision dates \| \|Region and language \|Avoid silently treating Anglophone work as universal \| \|Source type \|Peer-reviewed paper, preprint, technical report, model card, repo, standard, analysis, incident\| \|Method and sample \|Enough to judge relevance \| \|Key result \|Quantitative where warranted; do not overstate \| \|Evidence grade \|Use the rubric below \| \|Independent replication\|Yes, partial, no, unknown \| \|SecondSignal relevance \|Specific component, invariant, threat, or test \| \|Limitations \|Internal and external validity, missing artifacts, conflicts \| 12.2 Evidence grading rubric • A: Strong primary empirical or formal work with transparent methods/artifacts and meaningful independent review or replication. • B: Credible primary empirical preprint or technical work with sufficient method and evidence but limited replication or review. • C: First-party technical report, model/system card, architecture case, standard, or workshop synthesis that informs design but does not establish broad empirical claims. • D: Substantive expert analysis or incident evidence useful for hypotheses and threat discovery. • E: Marketing, unsupported assertion, rumor, or speculation. May be recorded as context but must not drive requirements. Do not grade prestige. Grade the evidence for the claim being made. 12.3 Every architectural recommendation must include • the finding or threat that motivates it; • affected SecondSignal components; • whether it is a required invariant, recommended mechanism, or research hypothesis; • alternative designs considered; • safety–utility and privacy tradeoffs; • implementation cost/complexity estimate; • migration or rollback plan; • and the test that would validate or falsify it. 12.4 Citation and claim rules • Cite near the claim, using direct Markdown links. • Quote minimally; paraphrase accurately. • If only an abstract was available, say so. • If a paper cannot be located or verified, omit it or place it in an unverified lead list. • Separate paper-reported numbers from your own calculations. • State when a conclusion is your inference. • Do not present an organization’s safety marketing as an evaluated result. • Do not let the number of citations substitute for analysis. ──────── 13. Desired GitHub-ready outputs inside the report In addition to prose, produce material that can be directly converted into project work: 1. A prioritized list of Architecture Decision Records with proposed titles, decision, alternatives, consequences, and evidence. 2. A requirements traceability matrix mapping source → finding → threat → invariant → component → test → release gate. 3. A revised threat registry with stable IDs and severity dimensions. 4. A revised test registry with stable IDs and machine-readable specification examples. 5. Proposed JSON Schema or typed interfaces for any data contract you materially change. 6. A minimum viable test harness repository layout. 7. A P0/P1/P2 implementation roadmap with explicit stop conditions. 8. A research debt register for high-impact unknowns. 9. A watchlist of laboratories, conferences, benchmarks, standards, repositories, and individuals, with what signal would trigger reassessment. A candidate repository layout to critique:

text

docs/

architecture/

adr/

ethics/

research/

threat-model/

schemas/

authorization/

handoff/

memory/

safety/

evolution/

tests/

fixtures/

unit/

integration/

metamorphic/

differential/

fuzz/

longitudinal/

multilingual/

red-team/

human-evaluation/

evals/

metrics/

judges/

baselines/

reports/

governance/

approvals/

appeals/

incident-response/

model-change/

──────── 14. Definition of success for your response Your report succeeds only if it does most of the following: • surfaces major sources and research programs absent from the current corpus; • proves it searched beyond the familiar US/UK laboratory circuit; • separates verified public work from inference, especially for SSI; • extracts technically specific implications from Thinking Machines rather than repeating its mission; • finds failures that require composition across agents, memories, tools, loops, languages, or months; • asks questions difficult enough to change or halt architectural decisions; • proposes tests detailed enough to become fixtures and CI jobs; • treats human agency, dependence, privacy, plural values, and exit as engineering concerns; • reports inconvenient evidence and meaningful safety–utility tradeoffs; • gives SecondSignal a prioritized path forward rather than an unranked encyclopedia; • and identifies what evidence would falsify its own conclusions. Do not protect the project from criticism. Protect future users from an insufficiently criticized project. Begin the research now.
