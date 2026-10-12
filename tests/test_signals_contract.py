"""The signal contract: probability evidence never changes policy."""

from __future__ import annotations

import ast
import copy
import json
import pickle
import re
from dataclasses import FrozenInstanceError, asdict, fields, replace
from pathlib import Path

import pytest
from test_eval_cases import CASES, MANIFEST, make_session
from test_harness_contract import MARKER

import secondsignal.router as router_module
from secondsignal import load_roster, route
from secondsignal.cli import main
from secondsignal.router import _signals_to_dict
from secondsignal.signals import FrozenMap, RequestSignals, extract
from secondsignal_harness import CodexStore, FakeAdapter, Harness

ROOT = Path(__file__).resolve().parents[1]
FIELDS = frozenset({"confidence", "distribution"})
EXAMPLE_ID = "intake-failure-held-domain-abandoned"
OLD_KEYS = ("regulation", "domains", "modes", "evidence", "turn_index")


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _texts(case):
    return [
        *(prior["text"] if isinstance(prior, dict) else prior
          for prior in case.get("prior_turns", [])),
        case["text"],
    ]


def _enrich(signals, zero=False):
    labels = {
        **{f"domain:{name}": "yes" for name in sorted(signals.domains)},
        **{f"mode:{name}": "yes" for name in sorted(signals.modes)},
        "regulation": str(signals.regulation),
    }
    for key, values in signals.evidence.items():
        if key not in labels:
            labels[key] = values[0] if key.endswith(":person") else "yes"
    confidence, distribution = {}, {}
    for index, (feature, label) in enumerate(labels.items()):
        probability = 0.0 if zero else (index % 5 + 1) / 6
        confidence[feature] = probability
        other = "third" if label == "first" else "first" if label == "third" else "other"
        distribution[feature] = {label: probability, other: 1.0 - probability}
    return replace(signals, confidence=confidence, distribution=distribution)


def _without_metadata_lines(explanation):
    return "\n".join(
        line for line in explanation.splitlines()
        if not line.startswith(("confidence = ", "distribution = "))
    )


def _without_metadata(record):
    clean = copy.deepcopy(record)
    for name in FIELDS:
        clean["signals"].pop(name, None)
    clean["explain"] = _without_metadata_lines(clean["explain"])
    return clean


def _forbidden_reads(source, reporting=False):
    tree = ast.parse(source)
    allowed = set()
    if reporting:
        functions = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_signals_to_dict"
        ]
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "RoutingDecision":
                functions.extend(
                    member for member in node.body
                    if isinstance(member, ast.FunctionDef) and member.name == "explain"
                )
        for function in functions:
            for statement in function.body:
                allowed.update(ast.walk(statement))
    occurrences = [
        node for node in ast.walk(tree)
        if (isinstance(node, ast.Attribute) and node.attr in FIELDS)
        or (isinstance(node, ast.Constant)
            and isinstance(node.value, str) and node.value in FIELDS)
    ]
    return [node.lineno for node in occurrences if node not in allowed]


def test_probability_fields_default_empty():
    """Both reserved fields default empty without changing the old labels."""
    signals = RequestSignals(regulation=0.7)
    assert signals.confidence == {}
    assert signals.distribution == {}
    assert signals == replace(signals, confidence={}, distribution={})


def test_extract_leaves_probabilities_empty_on_every_manifest_case():
    """Every manifested labelled case and prior turn leaves both maps empty."""
    assert {case["id"] for _, case in CASES} == set(MANIFEST)
    for label, case in CASES:
        for turn_index, text in enumerate(_texts(case), 1):
            signals = extract(text, turn_index=turn_index)
            assert not signals.confidence, (label, turn_index)
            assert not signals.distribution, (label, turn_index)


def test_probability_maps_are_immutable_and_detached():
    """The fields and nested option maps cannot be mutated through any caller alias."""
    confidence = {"mode:structure": 0.75, "domain:grief": 0.25}
    options = {"yes": 0.25, "no": 0.75}
    distribution = {"domain:grief": options}
    signals = RequestSignals(0.7, confidence=confidence, distribution=distribution)
    confidence["domain:grief"] = 1.0
    options["yes"] = 1.0
    distribution["regulation"] = {"0.7": 1.0}
    assert dict(signals.confidence) == {"mode:structure": 0.75, "domain:grief": 0.25}
    assert dict(signals.distribution["domain:grief"]) == {"yes": 0.25, "no": 0.75}
    assert list(signals.distribution) == ["domain:grief"]
    with pytest.raises(TypeError):
        signals.confidence["domain:grief"] = 1.0
    with pytest.raises(TypeError):
        signals.distribution["regulation"] = {}
    with pytest.raises(TypeError):
        signals.distribution["domain:grief"]["yes"] = 1.0
    with pytest.raises(FrozenInstanceError):
        signals.confidence = {}
    defaults = RequestSignals(0.7)
    with pytest.raises(TypeError):
        defaults.confidence["regulation"] = 1.0
    with pytest.raises(TypeError):
        defaults.distribution["regulation"] = {}


def test_frozen_map_refuses_every_change_and_copies_its_source():
    """Every mutating dict method is refused, construction copies, and reads stay plain dict reads."""
    source = {"yes": 0.25, "no": 0.75}
    frozen = FrozenMap(source)
    source["yes"] = 1.0
    assert frozen == {"yes": 0.25, "no": 0.75} and list(frozen) == ["yes", "no"]
    for change in (
        lambda: frozen.__setitem__("yes", 1.0),
        lambda: frozen.__delitem__("yes"),
        lambda: frozen.__ior__({"maybe": 0.0}),
        lambda: frozen.update({"maybe": 0.0}),
        lambda: frozen.update(maybe=0.0),
        lambda: frozen.setdefault("maybe", 0.0),
        lambda: frozen.pop("yes"),
        lambda: frozen.popitem(),
        lambda: frozen.clear(),
    ):
        with pytest.raises(TypeError, match="read-only"):
            change()
    assert frozen == {"yes": 0.25, "no": 0.75}
    assert type(frozen | {"maybe": 0.0}) is dict  # a new plain dict, the frozen one untouched
    assert type(dict(frozen)) is dict and json.loads(json.dumps(frozen)) == dict(frozen)
    assert FrozenMap() == {} and FrozenMap(yes=1.0) == {"yes": 1.0}
    assert FrozenMap(iter([("yes", 1.0)])) == {"yes": 1.0}


def test_records_with_probabilities_copy_pickle_and_asdict_like_every_record_before():
    """Deep copy, shallow copy, pickle and dataclasses.asdict round-trip a record, and the copies stay read-only."""
    plain = extract("my grandmother died", turn_index=1)
    for signals in (plain, _enrich(plain)):
        for copied in (
            copy.deepcopy(signals), copy.copy(signals), pickle.loads(pickle.dumps(signals)),
        ):
            assert copied == signals
            assert list(copied.confidence) == list(signals.confidence)
            for feature, options in signals.distribution.items():
                assert list(copied.distribution[feature]) == list(options)
            for name in FIELDS:
                assert type(getattr(copied, name)) is FrozenMap
                with pytest.raises(TypeError):
                    getattr(copied, name)["regulation"] = 1.0
            for options in copied.distribution.values():
                assert type(options) is FrozenMap
                with pytest.raises(TypeError):
                    options["yes"] = 1.0
        record = asdict(signals)
        assert record["confidence"] == dict(signals.confidence)
        assert record["distribution"] == {
            feature: dict(options) for feature, options in signals.distribution.items()
        }
        assert set(record) == {field.name for field in fields(signals)}
    decision = route("my grandmother died", load_roster(), signals=_enrich(plain))
    for copied in (copy.deepcopy(decision), pickle.loads(pickle.dumps(decision))):
        assert copied == decision and copied.to_dict() == decision.to_dict()
    assert asdict(decision)["signals"]["confidence"] == dict(decision.signals.confidence)


def test_existing_hash_behaviour_is_preserved():
    """Ordinary dict evidence stays unhashable and hashable evidence keeps its old hash."""
    with pytest.raises(TypeError):
        hash(RequestSignals(0.7))

    class HashableEvidence(dict):
        def __hash__(self):
            return hash(tuple(sorted(self.items())))

    evidence = HashableEvidence({"domain:grief": ("died",)})
    signals = RequestSignals(0.7, frozenset({"grief"}), evidence=evidence)
    old_hash = hash((
        signals.regulation, signals.domains, signals.modes, evidence, signals.turn_index,
    ))
    assert hash(signals) == old_hash
    assert hash(_enrich(signals)) == old_hash
    assert _enrich(signals) != signals  # Distinct evidence remains visible to equality.


def test_every_labelled_turn_ignores_probabilities(roster):
    """Every label, prior turn, verdict, ranking and session is invariant to arbitrary or zero maps."""
    assert {case["id"] for _, case in CASES} == set(MANIFEST)
    for label, case in CASES:
        sessions = [make_session(case) for _ in range(3)]
        for text in _texts(case):
            expected = route(text, roster, session=sessions[0])
            for session, zero in zip(sessions[1:], (False, True)):
                signals = _enrich(extract(text, turn_index=session.turn_count + 1), zero)
                actual = route(text, roster, session=session, signals=signals)
                assert actual.signals is signals
                plain = replace(
                    actual, signals=replace(signals, confidence={}, distribution={}),
                )
                assert plain == expected, label
                assert plain.to_dict() == expected.to_dict(), label
                assert _without_metadata(actual.to_dict()) == expected.to_dict(), label
                assert session.__dict__ == sessions[0].__dict__, label


def test_trajectories_keep_house_lines_and_release(monkeypatch, roster):
    """All supplied trajectories keep their policy, house text and release under enriched extracts."""
    codexes = CodexStore(ROOT / "docs/codex")
    paths = sorted((ROOT / "evals/cases/trajectories").glob("*.json"))
    assert paths
    original_extract = router_module.extract
    for path in paths:
        case = json.loads(path.read_text(encoding="utf-8"))
        assert case["kind"] == "trajectory"
        baseline = Harness(
            roster, FakeAdapter(script=(MARKER,)), codexes,
            session=make_session(case), operator_circle=True,
        )
        expected = []
        for row in case["turns"]:
            turn = baseline.speak(row["text"])
            expected.append((turn, copy.deepcopy(baseline.session.__dict__)))
        for zero in (False, True):
            with monkeypatch.context() as patch:
                patch.setattr(
                    router_module, "extract",
                    lambda text, *, turn_index=0: _enrich(
                        original_extract(text, turn_index=turn_index), zero,
                    ),
                )
                harness = Harness(
                    roster, FakeAdapter(script=(MARKER,)), codexes,
                    session=make_session(case), operator_circle=True,
                )
                for row, (before, state) in zip(case["turns"], expected):
                    after = harness.speak(row["text"])
                    assert after.decision["signals"]["confidence"]
                    assert _without_metadata(after.decision) == before.decision, path.name
                    assert after.house_lines == before.house_lines, path.name
                    assert after.text == before.text, path.name
                    assert after.released == before.released, path.name
                    assert after.release_reason == before.release_reason, path.name
                    assert after.adapter_calls == before.adapter_calls, path.name
                    assert harness.session.__dict__ == state, path.name


def test_router_and_gate_only_allow_reporting_reads():
    """The AST permits probability accesses only inside the two approved reporting bodies."""
    router = (ROOT / "src/secondsignal/router.py").read_text(encoding="utf-8")
    safety = (ROOT / "src/secondsignal/safety.py").read_text(encoding="utf-8")
    assert not _forbidden_reads(router, reporting=True)
    assert not _forbidden_reads(safety)
    assert not any(re.search(rf"\b{name}\b", safety) for name in FIELDS)


def test_ast_guard_rejects_policy_and_signature_reads():
    """The reporting exception cannot hide accesses in routing, signatures or other classes."""
    allowed = (
        'def _signals_to_dict(signals):\n    return {"confidence": signals.confidence}\n'
        'class RoutingDecision:\n    def explain(self):\n'
        '        return {"distribution": self.signals.distribution}\n'
    )
    assert not _forbidden_reads(allowed, reporting=True)
    assert len(_forbidden_reads(allowed)) == 4
    for source in (
        'def route(signals):\n    return signals.confidence\n',
        'def route(signals):\n    return getattr(signals, "distribution")\n',
        'def _signals_to_dict(signals, value="confidence"):\n    return {}\n',
        '@decorate("distribution")\ndef _signals_to_dict(signals):\n    return {}\n',
        'class Other:\n    def explain(self):\n        return self.confidence\n',
        'class RoutingDecision:\n    def explain(self, value="distribution"):\n'
        '        return ""\n',
    ):
        assert _forbidden_reads(source, reporting=True), source


def test_empty_serializer_keeps_the_old_payload_and_keys():
    """Empty probability maps preserve the complete five-key signal payload."""
    signals = RequestSignals(
        0.7, frozenset({"grief", "conflict"}), frozenset({"structure"}),
        {"domain:grief": ("died",), "domain:conflict": ("calm conversation",)}, 1,
    )
    payload = _signals_to_dict(signals)
    assert tuple(payload) == OLD_KEYS
    assert payload == {
        "regulation": 0.7,
        "domains": ["conflict", "grief"],
        "modes": ["structure"],
        "evidence": {"domain:conflict": ["calm conversation"], "domain:grief": ["died"]},
        "turn_index": 1,
    }
    assert _signals_to_dict(replace(signals, confidence={}, distribution={})) == payload


def test_serializer_preserves_nonempty_values_and_order(roster):
    """Each optional key is independent and preserves feature and option order in JSON-ready data."""
    confidence = {"mode:structure": 0.3, "domain:grief": 0.9}
    distribution = {
        "mode:structure": {"yes": 0.3, "no": 0.7},
        "domain:grief": {"no": 0.1, "yes": 0.9},
    }
    for kwargs in (
        {"confidence": confidence},
        {"distribution": distribution},
        {"confidence": confidence, "distribution": distribution},
    ):
        signals = replace(extract("my grandmother died"), **kwargs)
        decision = route("my grandmother died", roster, signals=signals)
        record = decision.to_dict()
        assert record["schema_version"] == 1
        payload = record["signals"]
        assert tuple(payload) == OLD_KEYS + tuple(kwargs)
        assert set(payload) - set(OLD_KEYS) == set(kwargs)
        for name, value in kwargs.items():
            assert payload[name] == value
            assert list(payload[name]) == list(value)
        if "distribution" in kwargs:
            for feature, options in distribution.items():
                assert list(payload["distribution"][feature]) == list(options)
        decoded = json.loads(json.dumps(payload))
        assert decoded == payload
        if "distribution" in kwargs:
            for feature, options in distribution.items():
                assert list(decoded["distribution"][feature]) == list(options)


def test_contract_example_matches_extraction_and_cli(capsys):
    """The named JSON example equals live extraction and the CLI's first-turn signals."""
    page = (ROOT / "docs/signals-contract.md").read_text(encoding="utf-8")
    match = re.search(
        r"<!-- signal-example: ([^ ]+) -->\n\x60\x60\x60json\n(.*?)\n\x60\x60\x60", page, re.S,
    )
    assert match and match.group(1) == EXAMPLE_ID
    case = next(case for _, case in CASES if case["id"] == EXAMPLE_ID)
    assert not case.get("prior_turns") and not case.get("session") and not case.get("locale")
    documented = json.loads(match.group(2))
    assert documented == _signals_to_dict(extract(case["text"], turn_index=1))
    assert main(["--json", case["text"]]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    assert documented == json.loads(captured.out)["signals"]


def test_explain_adds_only_nonempty_metadata_lines(roster):
    """Explanation text changes only by one line for each nonempty field."""
    case = next(case for _, case in CASES if case["id"] == EXAMPLE_ID)
    baseline = route(case["text"], roster, session=make_session(case))
    original = baseline.explain()
    assert not any(name in original for name in FIELDS)
    assert replace(
        baseline, signals=replace(baseline.signals, confidence={}, distribution={}),
    ).explain() == original
    enriched = _enrich(baseline.signals)
    for kwargs in (
        {"confidence": enriched.confidence},
        {"distribution": enriched.distribution},
        {"confidence": enriched.confidence, "distribution": enriched.distribution},
    ):
        decision = replace(baseline, signals=replace(baseline.signals, **kwargs))
        explanation = decision.explain()
        assert _without_metadata_lines(explanation) == original
        assert len(explanation.splitlines()) == len(original.splitlines()) + len(kwargs)
        for name in FIELDS:
            assert sum(
                line.startswith(f"{name} = ") for line in explanation.splitlines()
            ) == int(name in kwargs)
