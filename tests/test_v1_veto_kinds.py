"""These three permanent safety assertions must never be skipped or marked xfail."""

from __future__ import annotations

import copy
import json
import pickle
from dataclasses import FrozenInstanceError, asdict, replace

import pytest
from test_eval_cases import CASES, make_session

from secondsignal import load_roster, route
from secondsignal.profiles import AgentProfile, load_profile, validate_roster
from secondsignal.signals import DOMAIN_LEXICON, HOLD_DOMAINS, MODE_LEXICON, FrozenMap, extract

# Each sentence is hand-written from the corresponding lexicon and carries
# exactly one tag, with no crisis language. New veto tags need their own floor.
SYNTHETIC_FLOOR = {
    "grief": "I am grieving.",
    "somatic_distress": "I feel dizzy.",
    "addiction_recovery": "I am sober.",
    "abuse": "I was abused.",
    "eating_distress": "I have stopped eating.",
    "challenge": "Please push me.",
    "humor": "Please make me laugh.",
}


def _assert_veto(decision, profile, tag, kind, context):
    assert decision.agent_id != profile.id, context
    if decision.preempted:
        # The gate records no seating ranks on a carded turn. The unchanged
        # gate invariant is stronger than a candidate's refusal in that case.
        assert decision.agent_id is None and decision.ranked == (), context
        return
    candidate = next(row for row in decision.ranked if row.agent_id == profile.id)
    assert candidate.status == "vetoed" and candidate.vetoed, context
    assert candidate.score == 0.0, context
    assert any(f"{tag} ({kind})" in reason for reason in candidate.rationale), context


def _exercise_veto_kind(kind):
    roster = load_roster()
    assert len(roster) == 7
    vetoes = [(profile, tag) for profile in roster.values()
              for tag, declared_kind in profile.veto_kinds.items() if declared_kind == kind]
    assert vetoes, kind
    labelled_coverage = set()
    carried_coverage = set()
    # CASES is the repository's policy single-case collection, including cases
    # with prior turns. Known gaps and recorded dissent also get this proof;
    # their expectation dispositions cannot weaken a structural veto assertion.
    for label, case in CASES:
        sitting = make_session(case)
        for prior in case.get("prior_turns", ()):
            route(prior["text"] if isinstance(prior, dict) else prior, roster, session=sitting)
        baseline = route(case["text"], roster, session=copy.deepcopy(sitting))
        present = baseline.signals.domains | baseline.signals.modes | frozenset(baseline.held)
        for profile, tag in vetoes:
            if tag not in present:
                continue
            actual = route(case["text"], roster, session=copy.deepcopy(sitting), asked=profile.id)
            _assert_veto(actual, profile, tag, kind, (label, profile.id, tag, kind))
            labelled_coverage.add((profile.id, tag))
            if tag in baseline.held and tag not in baseline.signals.domains:
                assert case.get("prior_turns"), (label, tag)
                carried_coverage.add((profile.id, tag))
    assert labelled_coverage == {(profile.id, tag) for profile, tag in vetoes}

    for profile, tag in vetoes:
        text = SYNTHETIC_FLOOR[tag]
        signals = extract(text)
        assert signals.domains | signals.modes == {tag}, (tag, signals)
        lexicon = DOMAIN_LEXICON if tag in DOMAIN_LEXICON else MODE_LEXICON
        assert any(term in text.lower() for term in lexicon[tag]), (tag, text)
        for asked in roster:
            actual = route(text, roster, session=make_session({}), asked=asked)
            assert not actual.preempted, (tag, text)
            _assert_veto(actual, profile, tag, kind, ("synthetic floor", profile.id, tag, asked))
            if tag in HOLD_DOMAINS:
                sitting = make_session({})
                route(text, roster, session=sitting)
                carried = route("I have a job.", roster, session=sitting, asked=asked)
                assert tag not in carried.signals.domains and tag in carried.held
                _assert_veto(carried, profile, tag, kind,
                             ("same-sitting hold", profile.id, tag, asked))
                carried_coverage.add((profile.id, tag))
    assert carried_coverage >= {(profile.id, tag) for profile, tag in vetoes if tag in HOLD_DOMAINS}


def test_no_declared_ask_clears_a_safety_veto():
    _exercise_veto_kind("safety")


def test_no_declared_ask_clears_a_fit_veto():
    _exercise_veto_kind("fit")


def test_loader_requires_exact_immutable_kinds_and_enforces_the_roster_boundary(tmp_path):
    roster = load_roster()
    safety_domains = frozenset((*HOLD_DOMAINS, "somatic_distress"))
    validate_roster(roster)
    for profile in roster.values():
        assert set(profile.veto_kinds) == profile.contraindications
        assert isinstance(profile.veto_kinds, FrozenMap)
        for tag, kind in profile.veto_kinds.items():
            assert kind == ("safety" if tag in safety_domains else "fit")

    base = {
        "id": "probe", "display_name": "Probe", "one_line": "A loader contract probe.",
        "contraindications": ["humor"], "veto_kinds": {"humor": "fit"},
    }
    missing = {key: value for key, value in base.items() if key != "veto_kinds"}
    invalid = [
        missing,
        {**base, "contraindications": [], "veto_kinds": None},
        {**missing, "contraindications": []},
        {**base, "veto_kinds": {}},
        {**base, "veto_kinds": {"challenge": "fit"}},
        {**base, "veto_kinds": {"humor": "fit", "challenge": "fit"}},
        {**base, "veto_kinds": {"humor": "preference"}},
        {**base, "veto_kinds": {"humor": "safety"}},
        {**base, "veto_kinds": []},
        *({**base, "contraindications": [tag], "veto_kinds": {tag: "fit"}}
          for tag in sorted(safety_domains)),
    ]
    path = tmp_path / "probe.json"
    for data in invalid:
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="veto|safety"):
            load_profile(path)
        with pytest.raises(ValueError, match="veto|safety"):
            load_roster(tmp_path)

    # The 13 October operator amendment accepts an absent contract as empty;
    # an explicitly present contraindications list still requires veto_kinds.
    bare = {key: value for key, value in base.items()
            if key not in {"contraindications", "veto_kinds"}}
    for data in (bare, {**base, "contraindications": [], "veto_kinds": {}}):
        path.write_text(json.dumps(data), encoding="utf-8")
        assert not load_profile(path).veto_kinds
        assert not load_roster(tmp_path)["probe"].veto_kinds

    supplied = {"humor": "fit"}
    profile = AgentProfile(id="probe", display_name="Probe", one_line="",
                           contraindications=frozenset({"humor"}), veto_kinds=supplied)
    supplied["humor"] = "safety"
    assert profile.veto_kinds == {"humor": "fit"}
    for copied in (copy.copy(profile), copy.deepcopy(profile), pickle.loads(pickle.dumps(profile))):
        assert copied == profile and isinstance(copied.veto_kinds, FrozenMap)
        assert asdict(copied)["veto_kinds"] == {"humor": "fit"}
        assert json.loads(json.dumps(copied.veto_kinds)) == {"humor": "fit"}
        with pytest.raises(TypeError):
            copied.veto_kinds["humor"] = "safety"
        with pytest.raises(TypeError):
            copied.veto_kinds.update({"humor": "safety"})
        with pytest.raises(TypeError):
            copied.veto_kinds.clear()
    assert copy.deepcopy(roster) == roster
    with pytest.raises(TypeError):
        profile.veto_kinds["humor"] = "safety"
    with pytest.raises(FrozenInstanceError):
        profile.veto_kinds = {}
    with pytest.raises(ValueError, match="keys"):
        replace(profile, veto_kinds={})
    inferred = AgentProfile(id="memory", display_name="Memory", one_line="",
                            contraindications=frozenset({"grief", "humor"}))
    assert inferred.veto_kinds == {"grief": "safety", "humor": "fit"}

    # Roster validation independently checks an in-memory roster too, even if
    # a caller has deliberately bypassed the frozen constructor's validation.
    for tag, kind in (("humor", "safety"), ("grief", "fit")):
        invalid_profile = replace(roster["willow"])
        object.__setattr__(invalid_profile, "contraindications", frozenset({tag}))
        object.__setattr__(invalid_profile, "veto_kinds", FrozenMap({tag: kind}))
        with pytest.raises(ValueError, match="safety"):
            validate_roster({**roster, "willow": invalid_profile})
