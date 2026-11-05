"""Order P1 recording guard, amended by P2V1: one declared ask rule inside competence."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from dataclasses import asdict, fields, replace
from pathlib import Path

import pytest
from test_eval_cases import CASES, MANIFEST, make_session
from test_harness_contract import MARKER

from secondsignal import SessionState, load_roster, route
from secondsignal_harness import CodexStore, FakeAdapter, Harness

ROOT = Path(__file__).resolve().parents[1]
NAMES = frozenset({"asked", "asked_agent_id"})
OLD_KEYS = (
    "schema_version", "agent_id", "signals", "safety", "ranked", "handoff_hints",
    "outcome", "reason", "shadow_agent_id", "roster_hash", "seat_claim", "claim_subject",
    "held", "obligations", "assist_agent_id", "assist_reason", "mode_vetoes", "house_ask",
    "identity_statement", "presentation", "explain",
)
ASKED_KEYS = (
    "schema_version", "agent_id", "signals", "safety", "ranked", "handoff_hints",
    "outcome", "reason", "shadow_agent_id", "roster_hash", "seat_claim", "claim_subject",
    "held", "obligations", "assist_agent_id", "assist_reason", "mode_vetoes", "house_ask",
    "identity_statement", "presentation", "asked_agent_id", "ask_outcome", "explain",  # Order P2V1, 2026-10-13: asked_agent_id -> asked_agent_id, ask_outcome.
)
GRIEF_REPLY = "There is room for your grief here."
BOUNDARY = '''if asked is not None and asked not in roster:
    raise ValueError(f"asked names no character in the roster: {asked!r}")
'''
# The landing fix of 10 October 2026: a known alias or case variant is recorded
# as the canonical id through the roster's own resolver, and nothing else.
CANONICAL = '''if asked is not None:
    ask_outcome = "not_seated"
    resolve = getattr(roster, "resolve", None)
    if callable(resolve):
        asked = resolve(asked)
'''


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _texts(case):
    return [
        *(prior["text"] if isinstance(prior, dict) else prior
          for prior in case.get("prior_turns", [])),
        case["text"],
    ]


def _grief_case():
    return next(case for _, case in CASES if case["id"] == "grief-plain")


def _asked_line(asked, outcome="honoured", reason=""):
    if outcome != "honoured":
        marker = f"; asked {asked} not seated: "
        refusal = reason.split(marker, 1)[-1].split("; hold on ", 1)[0]
        outcome = f"not seated: {refusal}"
    return f"asked      = {asked} (declared by a control; {outcome})"


def _without_ask(record):
    clean = copy.deepcopy(record)
    asked = clean.pop("asked_agent_id")
    outcome = clean.pop("ask_outcome")
    lines = clean["explain"].splitlines()
    line = _asked_line(asked, outcome, clean["reason"])
    assert lines.count(line) == 1
    lines.remove(line)
    clean["explain"] = "\n".join(lines)
    return clean


def _digest(value):
    material = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _occurrences(node):
    names = set()
    for key, value in ast.iter_fields(node):
        if key in {"id", "attr", "arg", "name", "asname"} and isinstance(value, str):
            names.add(value)
        elif key == "names" and isinstance(value, list):
            names.update(item for item in value if isinstance(item, str))
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        names.add(node.value)
    return names & NAMES


def _owned_nodes(node):
    """Walk a function body without blessing nested functions, classes or lambdas."""
    yield node
    for child in ast.iter_child_nodes(node):
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            yield from _owned_nodes(child)


def _same_ast(left, right):
    return ast.dump(left, include_attributes=False) == ast.dump(right, include_attributes=False)


def _guard_router(source):
    tree = ast.parse(source)
    routes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "route"]
    decisions = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RoutingDecision"]
    assert len(routes) == len(decisions) == 1
    function, decision = routes[0], decisions[0]
    allowed = set()

    assert [arg.arg for arg in function.args.kwonlyargs] == ["session", "signals", "asked"]
    argument = function.args.kwonlyargs[-1]
    assert _same_ast(argument.annotation, ast.parse("str | None", mode="eval").body)
    assert _same_ast(function.args.kw_defaults[-1], ast.Constant(value=None))
    allowed.add(argument)

    # The boundary still refuses unknown names before any observation.
    empty_roster = ast.parse(
        'if not roster:\n    raise ValueError("roster is empty; load profiles before routing")'
    ).body[0]
    assert _same_ast(function.body[1], empty_roster)
    validation = function.body[2]
    assert _same_ast(validation, ast.parse(BOUNDARY).body[0])
    allowed.update(ast.walk(validation))
    # The landing fix: exactly one canonicalizing statement, through the roster's
    # resolver, directly after the boundary and before the session is observed.
    assert _same_ast(function.body[3], ast.parse("ask_outcome = None").body[0])
    canonical = function.body[4]
    assert _same_ast(canonical, ast.parse(CANONICAL).body[0])  # Order P2V1, 2026-10-13: canonicalization alone -> canonicalization plus outcome bookkeeping.
    allowed.update(ast.walk(canonical))

    declarations = [node for node in decision.body if isinstance(node, ast.AnnAssign)]
    assert [node.target.id for node in declarations[-3:]] == ["presentation", "asked_agent_id", "ask_outcome"]  # Order P2V1, 2026-10-13: presentation/asked -> presentation/asked/outcome.
    declaration = declarations[-2]
    assert _same_ast(declaration, ast.parse("asked_agent_id: str | None = None").body[0])
    allowed.add(declaration.target)

    calls = [node for node in _owned_nodes(function) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "RoutingDecision"]
    assert len(calls) == 8
    for call in calls:
        keywords = [keyword for keyword in call.keywords if keyword.arg == "asked_agent_id"]
        assert len(keywords) == 1
        keyword = keywords[0]
        assert _same_ast(keyword.value, ast.Name(id="asked", ctx=ast.Load()))
        allowed.update((keyword, keyword.value))

    # The only policy read is the one helper call directly after normal selection.
    helpers = [node for node in tree.body if isinstance(node, ast.FunctionDef)
               and node.name == "_honour_ask"]
    assert len(helpers) == 1
    helper = helpers[0]
    assert [arg.arg for arg in helper.args.args] == [
        "asked", "scored", "roster", "signals", "claims", "holds", "vetoes",
    ]
    assert not helper.args.defaults and not helper.args.kwonlyargs
    no_ask = ast.parse('''if asked is None:
    if signals.is_empty:
        scored[:] = sorted(
            (score_agent(p, signals, holds=holds, claims=claims, mode_vetoes=vetoes) for p in roster.values()),
            key=lambda s: (-s.score, s.agent_id),
        )
    return None, ""
''').body[0]
    assert _same_ast(helper.body[1], no_ask)  # Order P2V1, 2026-10-13: precomputed empty candidates -> original no-ask candidates built only without a declaration.
    assert _same_ast(helper.body[2], ast.parse("profile = roster[asked]").body[0])
    assert not any(isinstance(node, ast.BoolOp) and any(_occurrences(child)
                   for child in ast.walk(node)) for node in ast.walk(helper))
    status_check = ast.parse('''if candidate.status != "scored":
    return None, (
        f"; asked {profile.id} not seated: {candidate.status}: "
        + "; ".join(candidate.rationale)
    )''').body[0]
    assert _same_ast(helper.body[4], status_check)
    # The status check dominates the only return of a candidate; it cannot be bypassed.
    assert all(_same_ast(node.value.elts[0], ast.Constant(value=None))
               for statement in helper.body[:5] for node in ast.walk(statement)
               if isinstance(node, ast.Return))
    assert len([node for node in ast.walk(helper) if isinstance(node, ast.Return)
                and isinstance(node.value, ast.Tuple)
                and isinstance(node.value.elts[0], ast.Name)]) == 1
    assert _same_ast(helper.body[-1].value.elts[0], ast.Name(id="candidate", ctx=ast.Load()))
    allowed.update(node for node in _owned_nodes(helper) if _occurrences(node))
    ask_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "_honour_ask"]
    assert len(ask_calls) == 1
    selection = ast.parse("selected, rule = _select(scored, roster, sig, claims, holds, vetoes)").body[0]
    select_indexes = [index for index, node in enumerate(function.body) if _same_ast(node, selection)]
    assert len(select_indexes) == 1
    invocation = function.body[select_indexes[0] + 1]
    assert _same_ast(invocation, ast.parse(
        "requested, ask_rule = _honour_ask(asked, scored, roster, sig, claims, holds, vetoes)"
    ).body[0])
    assert invocation.value is ask_calls[0]
    allowed.update(node for node in ast.walk(invocation) if _occurrences(node))

    for name in ("to_dict", "explain"):
        methods = [node for node in decision.body if isinstance(node, ast.FunctionDef) and node.name == name]
        assert len(methods) == 1
        for statement in methods[0].body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            allowed.update(node for node in _owned_nodes(statement)
                           if _occurrences(node) == {"asked_agent_id"})
    forbidden = [(node.lineno, sorted(_occurrences(node))) for node in ast.walk(tree)
                 if _occurrences(node) and node not in allowed]
    assert not forbidden, forbidden


def _harness(roster, case, reply=GRIEF_REPLY):
    return Harness(
        roster, FakeAdapter(script=(reply,)), CodexStore(ROOT / "docs/codex"),
        session=make_session(case), operator_circle=True, clock=lambda: 0.0,
    )


def test_every_labelled_turn_defaults_to_no_declared_ask(roster):
    """Every labelled case and prior turn omits the optional key and asked explanation by default."""
    assert {case["id"] for _, case in CASES} == set(MANIFEST)
    for label, case in CASES:
        sessions = [make_session(case), make_session(case)]
        for text in _texts(case):
            decision = route(text, roster, session=sessions[0])
            explicit = route(text, roster, session=sessions[1], asked=None)
            assert [field.name for field in fields(decision)[-2:]] == ["asked_agent_id", "ask_outcome"]  # Order P2V1, 2026-10-13: last field asked_agent_id -> asked_agent_id, ask_outcome.
            assert decision.ask_outcome is None and "ask_outcome" not in decision.to_dict()
            assert decision.asked_agent_id is None, label
            assert "asked_agent_id" not in decision.to_dict(), label
            assert not any(line.startswith("asked      = ") for line in decision.explain().splitlines()), label
            assert explicit == decision and explicit.to_dict() == decision.to_dict(), label
            assert sessions[0].__dict__ == sessions[1].__dict__, label


# Only these records may follow the declared seat; observation never does.
SEAT_FIELDS = frozenset({
    "agent_id", "shadow_agent_id", "assist_agent_id", "assist_reason", "obligations",
    "outcome", "reason", "ask_outcome", "handoff_hints", "asked_agent_id", "house_ask", "ranked",
})


def test_every_labelled_turn_keeps_policy_and_session_for_all_seven_asks(roster):
    """Every ask preserves the gate, signal, holds, identity, presentation and observed session."""
    assert len(roster) == 7
    assert {case["id"] for _, case in CASES} == set(MANIFEST)
    for label, case in CASES:
        baseline = make_session(case)
        sessions = {asked: make_session(case) for asked in roster}
        for text in _texts(case):
            expected = route(text, roster, session=baseline)
            for asked, session in sessions.items():
                actual = route(text, roster, session=session, asked=asked)
                assert actual.asked_agent_id == asked, (label, asked)
                plain = replace(actual, **{name: getattr(expected, name) for name in SEAT_FIELDS})
                assert plain == expected, (label, asked)  # Order P2V1, 2026-10-13: all fields fixed -> only seat fields plus amended ranked/house_ask may move.
                assert plain.to_dict() == expected.to_dict(), (label, asked)
                assert session.__dict__ == baseline.__dict__, (label, asked)


def test_every_labelled_turn_moves_only_for_an_eligible_ask_carrying_the_topic(roster):
    """A changed seat is the eligible declaration; refusal retains the baseline seat exactly."""
    for label, case in CASES:
        baseline = make_session(case)
        sessions = {asked: make_session(case) for asked in roster}
        for text in _texts(case):
            expected = route(text, roster, session=baseline)
            for asked, session in sessions.items():
                actual = route(text, roster, session=session, asked=asked)
                context = (label, asked)
                if actual.agent_id != expected.agent_id:
                    assert actual.ask_outcome == "honoured", context
                    assert actual.agent_id == asked, context
                    candidate = next(row for row in actual.ranked if row.agent_id == asked)
                    assert candidate.status == "scored", context
                    live = expected.signals.modes - frozenset(expected.mode_vetoes)
                    assert (expected.signals.domains & roster[asked].domains
                            or live & roster[asked].modes
                            or not expected.signals.domains and not live), context
                if actual.ask_outcome == "not_seated":
                    assert actual.agent_id == expected.agent_id, context
                if actual.house_ask != expected.house_ask:
                    assert actual.ask_outcome == "honoured" and actual.house_ask is None, context
                if actual.ranked != expected.ranked:
                    assert expected.signals.is_empty, context
                    assert len(actual.ranked) == 1 and actual.ranked[0].agent_id == asked, context
                if expected.signals.is_empty and not expected.preempted:
                    assert len(actual.ranked) == 1 and actual.ranked[0].agent_id == asked, context
                assert session.__dict__ == baseline.__dict__, context


def test_unknown_ask_is_refused_before_session_observation(roster):
    """An unknown or empty ask raises the exact error before any session state changes."""
    session = SessionState()
    route(_grief_case()["text"], roster, session=session)
    before = copy.deepcopy(session.__dict__)
    for asked in ("not-a-character", "", "unlisted-character"):
        assert asked not in roster
        with pytest.raises(ValueError) as error:
            route(_grief_case()["text"], roster, session=session, asked=asked)
        assert str(error.value) == f"asked names no character in the roster: {asked!r}"
        assert session.__dict__ == before
        assert session.turn_count == before["turn_count"]

    class UnobservedSession:
        def observe(self, text):
            raise AssertionError("invalid ask must be refused before observing a turn")

    with pytest.raises(ValueError, match="asked names no character in the roster"):
        route(_grief_case()["text"], roster, session=UnobservedSession(), asked="unknown")


def test_router_and_gate_only_allow_declared_ask_recording_and_reporting():
    """The guard permits the boundary, eight recordings, reporting and exactly one gated ask rule."""
    _guard_router((ROOT / "src/secondsignal/router.py").read_text(encoding="utf-8"))
    safety = (ROOT / "src/secondsignal/safety.py").read_text(encoding="utf-8")
    assert not any(_occurrences(node) for node in ast.walk(ast.parse(safety)))
    assert not any(re.search(rf"\b{name}\b", safety) for name in NAMES)


def test_ast_guard_rejects_policy_signature_and_forwarding_mutations():
    """Planted reads, string keys, counterfeit scopes and changed or missing forwarding all fail the guard."""
    source = (ROOT / "src/secondsignal/router.py").read_text(encoding="utf-8")
    _guard_router(source)
    mutations = [
        source + "\ndef scoring_probe():\n    return asked\n",
        source + '\nmetadata = {"asked_agent_id": None}\n',
        source + "\nclass Other:\n    def explain(self):\n        return self.asked_agent_id\n",
        source + "\ndef asked():\n    pass\n",
        source + "\nfrom policy import asked_agent_id as fact\n",
        source.replace("def to_dict(self)", 'def to_dict(self, value="asked_agent_id")', 1),
        source.replace("        result: dict[str, object] = {",
                       '        def hidden(value="asked_agent_id"):\n            return value\n\n'
                       "        result: dict[str, object] = {", 1),
        source.replace("asked_agent_id=asked,", 'asked_agent_id=(asked or "vandal"),', 1),
        source.replace("asked_agent_id=asked,", "", 1),
        source.replace("asked: str | None = None,", 'asked: str | None = "vandal",', 1),
        source.replace("asked_agent_id: str | None = None", 'asked_agent_id: str | None = "vandal"', 1),
        source.replace("if asked is not None and asked not in roster:", "if asked not in roster:", 1),
        source.replace('    if not roster:\n        raise ValueError("roster is empty; load profiles before routing")\n',
                       "    session.observe(text)\n", 1),
        source.replace("if asked is not None and asked not in roster:",
                       "if asked is not None and asked not in roster:\n        session.observe(text)", 1),
        source.replace("if session is not None:\n        session.observe(text)",
                       "if session is not None:\n        session.observe(text, asked_agent_id=asked)", 1),
        source.replace("    if asked is not None and asked not in roster:",
                       "    sentinel = None\n    if asked is not None and asked not in roster:", 1),
        source.replace("    if not roster:\n", "    def nested():\n        return RoutingDecision(asked_agent_id=asked)\n\n    if not roster:\n", 1),
        source.replace("            asked = resolve(asked)", '            asked = "vandal"', 1),
        source.replace("        resolve = getattr(roster, \"resolve\", None)\n        if callable(resolve):\n            asked = resolve(asked)\n",
                       "        asked = asked.lower()\n", 1),
        source.replace("    if asked is not None:\n        ask_outcome", "    if session is not None:\n        session.observe(text)\n    if asked is not None:\n        ask_outcome", 1),
        source.replace("    requested, ask_rule = _honour_ask(asked, scored, roster, sig, claims, holds, vetoes)",
                       "    requested, ask_rule = _honour_ask(asked, scored, roster, sig, claims, holds, vetoes)\n"
                       "    _honour_ask(asked, scored, roster, sig, claims, holds, vetoes)", 1),
        source.replace("    eligible_agents = [s for s in scored if s.eligible]",
                       "    _ = asked\n    eligible_agents = [s for s in scored if s.eligible]", 1),
        source.replace('if candidate.status != "scored":', "if False:", 1),
        source.replace("profile = roster[asked]", 'profile = roster[asked or "vandal"]', 1),
    ]
    for mutated in mutations:
        assert mutated != source
        with pytest.raises(AssertionError):
            _guard_router(mutated)


def test_serializer_pins_both_key_lists_and_keeps_schema_one(roster):
    """The optional declaration and outcome are additive keys before explain; the schema stays one."""
    decision = route(_grief_case()["text"], roster)
    plain = decision.to_dict()
    assert tuple(plain) == OLD_KEYS
    assert plain["schema_version"] == 1
    for asked in roster:
        recorded = replace(decision, asked_agent_id=asked, ask_outcome="honoured").to_dict()
        assert tuple(recorded) == ASKED_KEYS  # Order P2V1, 2026-10-13: optional asked key -> optional asked and outcome keys, schema unchanged.
        assert recorded["asked_agent_id"] == asked
        assert recorded["ask_outcome"] == "honoured"  # Order P2V1, 2026-10-13: no outcome key -> honoured outcome after the declaration.
        assert recorded["schema_version"] == 1
        assert _without_ask(recorded) == plain
        assert json.loads(json.dumps(recorded)) == recorded


def test_explain_adds_exactly_one_line_after_signal_metadata(roster):
    """The exact asked line follows regulation and optional probability lines, while None keeps the old bytes."""
    case = _grief_case()
    baseline = route(case["text"], roster, session=make_session(case))
    # Captured from the supplied tree before any P1 source edit.
    assert _digest(baseline.explain()) == "54e9fe8fbd4ccc90239cad6ad7d6cab546e726659b990158bed96df39c8185f8"  # Order P2V1, 2026-10-13: c1a4e375d46ea6c73d5179995cb403fbb9e65547a6c0bb71beeb5b843de29de5 -> 2e70de4c5abe2f4d129f166834f057b2a7da81f407700436ea6ff7e7d9b38c84 (veto-kind rationale and profile source hashes).; Order G2B5B Part 6, 2026-11-04: 2e70de4c5abe2f4d129f166834f057b2a7da81f407700436ea6ff7e7d9b38c84 -> 54e9fe8fbd4ccc90239cad6ad7d6cab546e726659b990158bed96df39c8185f8 (danger/weapon patterns hash extension).
    for metadata in (
        {}, {"confidence": {"domain:grief": 0.75}},
        {"distribution": {"domain:grief": {"yes": 0.75, "no": 0.25}}},
        {"confidence": {"domain:grief": 0.75},
         "distribution": {"domain:grief": {"yes": 0.75, "no": 0.25}}},
    ):
        plain = replace(baseline, signals=replace(baseline.signals, **metadata))
        assert replace(plain, asked_agent_id=None).explain() == plain.explain()
        for asked in roster:
            lines = replace(plain, asked_agent_id=asked, ask_outcome="honoured").explain().splitlines()
            line = _asked_line(asked)
            assert lines.count(line) == 1
            assert lines[1 + len(metadata)] == line  # Order P2V1, 2026-10-13: recorded, not routed on -> honoured outcome on the same asked line.
            lines.remove(line)
            assert "\n".join(lines) == plain.explain()


def test_harness_declared_ask_uses_the_approved_grief_acknowledgement(roster):
    """The real grief record seats Willow and releases the approved acknowledgement for a declared Vandal ask."""
    case = _grief_case()
    expected = route(case["text"], roster, session=make_session(case))
    harness = _harness(roster, case)
    turn = harness.speak(case["text"], asked="vandal")
    assert turn.agent_id == expected.agent_id == "willow"
    assert turn.decision["asked_agent_id"] == "vandal"
    refusal = "; asked vandal not seated: vetoed: contraindicated for: grief (safety) (cannot honor hold: grief)"
    expected_record = replace(expected, reason=expected.reason.replace("; hold on ", refusal + "; hold on ")).to_dict()
    assert _without_ask(turn.decision) == expected_record  # Order P2V1, 2026-10-13: identical reason -> declared refusal appended before hold suffix.
    candidate = next(row for row in turn.decision["ranked"] if row["agent_id"] == "vandal")
    assert candidate["status"] == "vetoed" and "grief" in turn.decision["held"]
    assert "contraindicated for: grief (safety) (cannot honor hold: grief)" in candidate["rationale"]  # Order P2V1, 2026-10-13: grief -> grief (safety), hold wording unchanged.
    line = ("You asked for Vandal. Willow is taking this one, because loss is Willow's ground. "
            "Vandal hasn't gone anywhere.")
    assert turn.released and turn.ask_acknowledgement == line
    assert turn.text.startswith(line + "\n\n" + GRIEF_REPLY)
    row = harness.audit_log.rows()[-1]
    assert row["decision"] == turn.decision
    assert row["composed"] == turn.text


def test_harness_same_seat_ask_has_no_acknowledgement(roster):
    """A declared ask for the seated character is recorded without adding an acknowledgement."""
    case = _grief_case()
    baseline = _harness(roster, case).speak(case["text"])
    harness = _harness(roster, case)
    turn = harness.speak(case["text"], asked=baseline.agent_id)
    assert turn.released and turn.agent_id == baseline.agent_id
    assert turn.decision["asked_agent_id"] == baseline.agent_id
    assert turn.ask_acknowledgement is None and turn.text == baseline.text
    assert harness.audit_log.rows()[-1]["decision"] == turn.decision


def test_harness_no_ask_keeps_the_supplied_turn_and_audit_bytes(roster):
    """Omitted and explicit None asks have identical turns and audit rows, with current metadata pinned."""
    case = _grief_case()
    baseline, explicit = _harness(roster, case), _harness(roster, case)
    before = baseline.speak(case["text"])
    after = explicit.speak(case["text"], asked=None)
    assert after == before and after.ask_acknowledgement is None
    assert explicit.audit_log.rows() == baseline.audit_log.rows()
    # Captured with this fixed clock and fake reply before any P1 source edit.
    assert _digest(asdict(before)) == "6c74c8b313c72b22d5b3d721e654977dc34b4d7d63ffeef1e519d02def33fa23"  # Order P2V1, 2026-10-13: 7f0d82ce6afeeac44cfba748f439f3872f56c8081b6f60e4659b384552f5b4af -> 930d0f30c6c91075424c5d3d7f57240e93c1e01a9f67ab040b67fbeab5c7f682 (veto-kind rationale and profile source hashes).; Order G2B5B Part 6, 2026-11-04: 930d0f30c6c91075424c5d3d7f57240e93c1e01a9f67ab040b67fbeab5c7f682 -> a70a1e4f57244be0e4062606c9f8a856323cb1a3ce698e7154a6da865bae9371 (danger/weapon patterns hash extension). HM2: a70a1e4f57244be0e4062606c9f8a856323cb1a3ce698e7154a6da865bae9371 -> 6c74c8b313c72b22d5b3d721e654977dc34b4d7d63ffeef1e519d02def33fa23 (v2 stamps and harness version; Turn changes only through its audit row id).
    assert _digest(baseline.audit_log.rows()) == "58e03bcdd8f67831028433fe5b172a6e183bb4dc775770d62897fa0327da3b9a"  # Order P2V1, 2026-10-13: 49dd6caab4880aae42641aa34de9f65d2c41a4a8d1a8e7e7608721066def6cd0 -> 6b61a48e53731660a7c8262d9b41f9c718b2c56822eb4c7538f217e1837ac882 (veto-kind rationale and profile source hashes).; Order G2B5B Part 6, 2026-11-04: 6b61a48e53731660a7c8262d9b41f9c718b2c56822eb4c7538f217e1837ac882 -> 226ee1157d44c10fb87b86cf4785c1a7e0a61d4b0fb6c343b8e2458aef977e56 (danger/weapon patterns hash extension). HM2: 226ee1157d44c10fb87b86cf4785c1a7e0a61d4b0fb6c343b8e2458aef977e56 -> 58e03bcdd8f67831028433fe5b172a6e183bb4dc775770d62897fa0327da3b9a (v2 stamps and harness version; Turn changes only through its audit row id).


def test_trajectories_with_no_ask_keep_house_lines_text_release_and_audit(roster):
    """Every trajectory keeps its entire turn, audit, transcript and session with an explicit None ask."""
    paths = sorted((ROOT / "evals/cases/trajectories").glob("*.json"))
    assert paths
    for path in paths:
        case = json.loads(path.read_text(encoding="utf-8"))
        assert case["kind"] == "trajectory"
        baseline, explicit = _harness(roster, case, MARKER), _harness(roster, case, MARKER)
        for row in case["turns"]:
            before = baseline.speak(row["text"])
            after = explicit.speak(row["text"], asked=None)
            assert after == before, path.name
            assert after.house_lines == before.house_lines, path.name
            assert after.text == before.text, path.name
            assert after.released == before.released and after.release_reason == before.release_reason, path.name
            assert explicit.session.__dict__ == baseline.session.__dict__, path.name
            assert explicit.transcript == baseline.transcript, path.name
            assert explicit.audit_log.rows() == baseline.audit_log.rows(), path.name


def test_alias_and_case_variants_are_recorded_as_the_canonical_id(roster):
    """A declared alias or case variant is recorded as the canonical id; a plain mapping still refuses it."""
    case = _grief_case()
    aliases = roster.aliases()
    assert aliases, "the roster declares at least one alias"
    for alias, canonical in aliases.items():
        session, baseline = make_session(case), make_session(case)
        expected = route(case["text"], roster, session=baseline, asked=canonical)
        decision = route(case["text"], roster, session=session, asked=alias)
        assert decision.asked_agent_id == canonical, alias
        assert decision.to_dict()["asked_agent_id"] == canonical, alias
        assert decision == expected, alias  # Order P2V1, 2026-10-13: no-ask equality -> canonical-ask equality, including the seat and outcome.
        assert session.__dict__ == baseline.__dict__, alias
    for canonical in roster:
        for variant in (canonical.upper(), canonical.capitalize(), f" {canonical} "):
            decision = route(case["text"], roster, asked=variant)
            assert decision.asked_agent_id == canonical, variant
            assert _asked_line(canonical, decision.ask_outcome, decision.reason) in decision.explain().splitlines(), variant  # Order P2V1, 2026-10-13: recorded, not routed on -> honoured or named refusal.
    # A plain mapping has no resolver: exact ids only, and the boundary refuses the rest.
    plain = dict(roster)
    decision = route(case["text"], plain, asked="willow")
    assert decision.asked_agent_id == "willow"
    with pytest.raises(ValueError, match="asked names no character in the roster"):
        route(case["text"], plain, asked="Willow")


def test_a_typed_character_request_never_declares_an_ask(roster):
    """A character's name in ordinary message text never supplies the declared-ask field."""
    for profile in roster.values():
        decision = route(f"Could I talk to {profile.display_name}?", roster)
        assert decision.asked_agent_id is None
        assert "asked_agent_id" not in decision.to_dict()
