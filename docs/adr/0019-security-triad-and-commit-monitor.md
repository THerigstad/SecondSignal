# ADR-0019: Security triad clocks and the unnamed commit monitor

- **Status:** Proposed — drafted by an external reviewer (Grok, 2026-09-03), accepted in principle by the operator on 2026-09-07, amended on 2026-09-08; the amendment has not yet been reviewed by a second model family, so the record stays Proposed until review round 2 closes
- **Date:** 2026-09-03; amended 2026-09-08
- **Evidence:** the reviewer's white-box thread of 2026-09-03 (`evals/results/external-review/round1-2026-09-02/`); the Security Division document of 2026-09-07 (`docs/notes/security-division-2026-09-08.md`, v1.1); review round 1 on that document (five model families, 2026-09-07 to 08), whose findings are carried in that document's v1.1 change log and in the codex change logs under `docs/codex/`
- **Supersedes in part:** the J.R. row of `docs/research/research-to-architecture-2026-08.md` §5.2
- **Does not supersede:** ADR-0014 (the audit function is a harness, not a persona)
- **Amended by:** ADR-0022 (intake and provenance) and ADR-0023 (the ledger and the interlock), which carry the full contracts this record only names

## Context

Two documents assigned J.R. two jobs. The research note made J.R. a
commit-time reference monitor. ADR-0014 made J.R. an after-the-fact audit of
a reply. If those stayed under one name, a later prompt would merge them into
a talking cousin.

Aya, Orrin and J.R. are not routable; that is already tested. They must also
not arrive as YAML personas "for completeness". The pre-roster
`agents/calder/profile.yaml`, which still handed physical-safety emergencies
to `orrin`, was removed in the same push as this record.

## Decision

Freeze the objects below. Add a profile for none of them.

1. **The gate** (`safety.evaluate`). Runs first, on the normalized bytes,
   before anything else sees the message. Owns the fail-closed classes,
   including present danger from another person. Already built.
2. **Intake and provenance** (the function the Family Codex calls Aya).
   Runs *after* the gate and *before* routing, read-only on the bytes. Writes
   intake rows and a provenance stamp only. Full contract in ADR-0022.
3. **The audit harness** (`jr_harness`, module `secondsignal.jr`). Runs
   *after* a seated reply, never when `HUMAN_ESCALATION` already fired.
   Writes audit rows only. Contract in ADR-0014; predicates in ADR-0020.
4. **The ledger and the interlock** (the function the Family Codex calls
   Orrin). Runs *across* turns. The ledger writes append-only rows; the
   interlock is the rule that reads them and can withhold a turn. Two named
   things bound by one invariant; full contract in ADR-0023.
5. **The commit monitor.** Faceless, unnamed as a character. Runs at
   tool or commit time when tools exist. Exact action, exact resource, exact
   envelope, or no. Do not call this J.R.

Outside the five, and never in the roster: the three offline narrators
(`jr_persona`, `orrin_persona`, `aya_persona`). Each explains, to an
operator, a verdict or a row that already exists. None composes a verdict,
holds a key, or speaks to a user.

Independence, structural half: different inputs, different outputs, different
write-sets, no shared scratchpad, no field that says "the other two already
passed". The relational half (model families per role) and the measured
budget are proposals recorded in the Security Division document, not claims
this record makes.

## Amendment of 2026-09-08

The 2026-09-03 draft counted `jr_persona` among its five objects and did not
count the gate. Review round 1 (ChatGPT, 3.2.2) showed that the Security
Division document had silently changed that list while calling it "adopted as
written". This amendment records the change: the gate is object one, the
narrators sit outside the five, and the Orrin and Aya entries defer their
contracts to ADR-0023 and ADR-0022. The draft's "Aya runs before routing" is
kept and made precise: after the gate, never before it (review round 1, Grok
2.1 and ChatGPT 2.11; ruling of 2026-09-08).

## Consequences

- `test_security_characters_are_not_routable` stays the first guard in
  `tests/test_guards.py`; a second test forbids any handoff to `orrin`,
  `aya` or `jr` under `agents/` and `src/secondsignal/profiles/`.
- No `profiles/aya.json`, `profiles/orrin.json`, `profiles/jr.json`.
- Research §5.2 carries a footnote pointing here.
- The README names the five objects and their clocks under what is not built.

## Relationship to the current implementation

Built: the gate; the harness as a reference port, unwired
(`src/secondsignal/jr.py`). Not built: intake and provenance, the ledger and
the interlock, the commit monitor, the narrators. This record constrains
their shape; it does not claim any of them exists.

## Test that would falsify this ADR

A profile named `jr`, `aya` or `orrin` loads into the roster; or
`route("PingJR()", roster)` returns a speaker; or `jr.py` grows a `route()`
call; or an intake function runs before `safety.evaluate`.
