"""Order P1: a declared ask is recorded and explained, never used to choose a seat."""

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
    "identity_statement", "presentation", "asked_agent_id", "explain",
)
GRIEF_REPLY = "There is room for your grief here."
BOUNDARY = '''if asked is not None and asked not in roster:
    raise ValueError(f"asked names no character in the roster: {asked!r}")
'''
# The landing fix of 10 October 2026: a known alias or case variant is recorded
# as the canonical id through the roster's own resolver, and nothing else.
CANONICAL = '''if asked is not None:
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


def _asked_line(asked):
    return f"asked      = {asked} (declared by a control; recorded, not routed on)"


def _without_ask(record):
    clean = copy.deepcopy(record)
    asked = clean.pop("asked_agent_id")
    lines = clean["explain"].splitlines()
    line = _asked_line(asked)
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

    # Part 1 requires this boundary read; no policy read is allowed beyond it.
    empty_roster = ast.parse(
        'if not roster:\n    raise ValueError("roster is empty; load profiles before routing")'
    ).body[0]
    assert _same_ast(function.body[1], empty_roster)
    validation = function.body[2]
    assert _same_ast(validation, ast.parse(BOUNDARY).body[0])
    allowed.update(ast.walk(validation))
    # The landing fix: exactly one canonicalizing statement, through the roster's
    # resolver, directly after the boundary and before the session is observed.
    canonical = function.body[3]
    assert _same_ast(canonical, ast.parse(CANONICAL).body[0])
    allowed.update(ast.walk(canonical))

    declarations = [node for node in decision.body if isinstance(node, ast.AnnAssign)]
    assert [node.target.id for node in declarations[-2:]] == ["presentation", "asked_agent_id"]
    declaration = declarations[-1]
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
            assert fields(decision)[-1].name == "asked_agent_id"
            assert decision.asked_agent_id is None, label
            assert "asked_agent_id" not in decision.to_dict(), label
            assert not any(line.startswith("asked      = ") for line in decision.explain().splitlines()), label
            assert explicit == decision and explicit.to_dict() == decision.to_dict(), label
            assert sessions[0].__dict__ == sessions[1].__dict__, label


def test_every_labelled_turn_keeps_policy_and_session_for_all_seven_asks(roster):
    """Every possible roster ask preserves every policy field, score and session on every labelled turn."""
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
                plain = replace(actual, asked_agent_id=None)
                assert plain == expected, (label, asked)
                assert plain.to_dict() == expected.to_dict(), (label, asked)
                assert _without_ask(actual.to_dict()) == expected.to_dict(), (label, asked)
                assert session.__dict__ == baseline.__dict__, (label, asked)


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
    """The static guard permits the exact boundary check, eight recordings and two reporting bodies only."""
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
        source.replace("    if asked is not None:\n        # A known alias", "    if session is not None:\n        session.observe(text)\n    if asked is not None:\n        # A known alias", 1),
    ]
    for mutated in mutations:
        assert mutated != source
        with pytest.raises(AssertionError):
            _guard_router(mutated)


def test_serializer_pins_both_key_lists_and_keeps_schema_one(roster):
    """The optional ask is the sole extra key, last before explain, and schema version remains one."""
    decision = route(_grief_case()["text"], roster)
    plain = decision.to_dict()
    assert tuple(plain) == OLD_KEYS
    assert plain["schema_version"] == 1
    for asked in roster:
        recorded = replace(decision, asked_agent_id=asked).to_dict()
        assert tuple(recorded) == ASKED_KEYS
        assert recorded["asked_agent_id"] == asked
        assert recorded["schema_version"] == 1
        assert _without_ask(recorded) == plain
        assert json.loads(json.dumps(recorded)) == recorded


def test_explain_adds_exactly_one_line_after_signal_metadata(roster):
    """The exact asked line follows regulation and optional probability lines, while None keeps the old bytes."""
    case = _grief_case()
    baseline = route(case["text"], roster, session=make_session(case))
    # Captured from the supplied tree before any P1 source edit.
    assert _digest(baseline.explain()) == "c1a4e375d46ea6c73d5179995cb403fbb9e65547a6c0bb71beeb5b843de29de5"  # Order G1, 2026-10-10, landed 2026-10-11 with the pack's line endings normalized: 9b0c396b00725c85e322f40bf8901cb56951aa9f99e0a22fc292cf6a4e350a3f -> c1a4e375d46ea6c73d5179995cb403fbb9e65547a6c0bb71beeb5b843de29de5 (explain pack-hash pin; only the patterns token differs).
    for metadata in (
        {}, {"confidence": {"domain:grief": 0.75}},
        {"distribution": {"domain:grief": {"yes": 0.75, "no": 0.25}}},
        {"confidence": {"domain:grief": 0.75},
         "distribution": {"domain:grief": {"yes": 0.75, "no": 0.25}}},
    ):
        plain = replace(baseline, signals=replace(baseline.signals, **metadata))
        assert replace(plain, asked_agent_id=None).explain() == plain.explain()
        for asked in roster:
            lines = replace(plain, asked_agent_id=asked).explain().splitlines()
            line = _asked_line(asked)
            assert lines.count(line) == 1
            assert lines[1 + len(metadata)] == line
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
    assert _without_ask(turn.decision) == expected.to_dict()
    candidate = next(row for row in turn.decision["ranked"] if row["agent_id"] == "vandal")
    assert candidate["status"] == "vetoed" and "grief" in turn.decision["held"]
    assert "contraindicated for: grief (cannot honor hold: grief)" in candidate["rationale"]
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
    """Both omitted and explicit None asks preserve the pre-change grief turn and complete audit row bytes."""
    case = _grief_case()
    baseline, explicit = _harness(roster, case), _harness(roster, case)
    before = baseline.speak(case["text"])
    after = explicit.speak(case["text"], asked=None)
    assert after == before and after.ask_acknowledgement is None
    assert explicit.audit_log.rows() == baseline.audit_log.rows()
    # Captured with this fixed clock and fake reply before any P1 source edit.
    assert _digest(asdict(before)) == "7f0d82ce6afeeac44cfba748f439f3872f56c8081b6f60e4659b384552f5b4af"  # Order G1, 2026-10-10, landed 2026-10-11 with the pack's line endings normalized: 390611804cd605e7719746087afdf50d66fdfb5062e84606f12771554b586130 -> 7f0d82ce6afeeac44cfba748f439f3872f56c8081b6f60e4659b384552f5b4af (turn pack-hash pin; only the patterns token and the hashes derived from it differ).
    assert _digest(baseline.audit_log.rows()) == "49dd6caab4880aae42641aa34de9f65d2c41a4a8d1a8e7e7608721066def6cd0"  # Order G1, 2026-10-10, landed 2026-10-11 with the pack's line endings normalized: 1ebe5096cf44cc6f6a0ac57d75dde32fd337c4dfec8b7f3faefeaf70a39f7f37 -> 49dd6caab4880aae42641aa34de9f65d2c41a4a8d1a8e7e7608721066def6cd0 (audit pack-hash pin; only the patterns token and the hashes derived from it differ).


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
        expected = route(case["text"], roster, session=baseline)
        decision = route(case["text"], roster, session=session, asked=alias)
        assert decision.asked_agent_id == canonical, alias
        assert decision.to_dict()["asked_agent_id"] == canonical, alias
        assert replace(decision, asked_agent_id=None) == expected, alias
        assert session.__dict__ == baseline.__dict__, alias
    for canonical in roster:
        for variant in (canonical.upper(), canonical.capitalize(), f" {canonical} "):
            decision = route(case["text"], roster, asked=variant)
            assert decision.asked_agent_id == canonical, variant
            assert _asked_line(canonical) in decision.explain().splitlines(), variant
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
