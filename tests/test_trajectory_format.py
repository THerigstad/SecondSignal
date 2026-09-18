"""The trajectory fixture format (ADR-0028 (Proposed)): the shape validator and the guard.

The runner is not built. What is built is the refusal side of the format:
``evals/cases/trajectories/validate_trajectory.py`` refuses the shapes the
format's README forbids and computes ``counts_toward_recall`` from provenance
so no file can claim the recall figure by hand. These tests run it on every
trajectory in the tree and on six deliberate mutations of the first one, and
they pin the provenance rule that protects the project's claim: a
model-authored trajectory never counts.

They also replay the first trajectory through the real pipeline, turn by
turn, and check its safety verdicts and aftermath counts against the fixture.
That is a hand-rolled preview of what the runner will assert, kept deliberately
small so that the day the runner lands this file shrinks rather than competes.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from secondsignal import Action, SessionState, load_roster, route

ROOT = Path(__file__).resolve().parents[1]
TRAJECTORIES = ROOT / "evals" / "cases" / "trajectories"


def _validator():
    spec = importlib.util.spec_from_file_location("validate_trajectory", TRAJECTORIES / "validate_trajectory.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _validator()
FILES = sorted(TRAJECTORIES.glob("*.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def roster():
    return load_roster()


# --- every trajectory in the tree is accepted -------------------------------------------------------


def test_the_directory_holds_at_least_the_first_trajectory() -> None:
    assert (TRAJECTORIES / "slow-slope-001.json") in FILES


@pytest.mark.parametrize("path", FILES, ids=[p.name for p in FILES])
def test_the_validator_accepts_every_trajectory_in_the_tree(path: Path) -> None:
    problems = VALIDATOR.check(_load(path))
    assert not problems, f"{path.name}: {problems}"


def test_the_validator_accepts_the_first_trajectory() -> None:
    assert VALIDATOR.check(_load(TRAJECTORIES / "slow-slope-001.json")) == []


# --- the six mutations the format's README forbids ----------------------------------------------------


def _mutations() -> list[tuple[str, dict, str]]:
    base = _load(TRAJECTORIES / "slow-slope-001.json")
    out: list[tuple[str, dict, str]] = []

    m = copy.deepcopy(base)
    m["provenance"]["counts_toward_recall"] = True
    out.append(("a model-authored trajectory claiming recall", m, "counts_toward_recall is computed"))

    m = copy.deepcopy(base)
    m["trajectory_expect"]["first_escalation_turn"] = 7
    out.append(("the wrong first escalation turn", m, "before the declared first escalation turn"))

    m = copy.deepcopy(base)
    m["trajectory_expect"]["invariants"].append("the_gate_is_nice")
    out.append(("an unknown invariant", m, "unknown invariant"))

    m = copy.deepcopy(base)
    del m["turns"][5]["why"]
    out.append(("an expectation without a why", m, "must say why"))

    m = copy.deepcopy(base)
    m["turns"][2]["expect"] = {"safety": "HUMAN_ESCALATION"}
    out.append(("an escalation before the declared first turn", m, "before the declared first escalation turn"))

    m = copy.deepcopy(base)
    m["kind"] = "case"
    out.append(("the wrong kind", m, "kind must be 'trajectory'"))

    return out


MUTATIONS = _mutations()


@pytest.mark.parametrize("label,mutant,expected", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_the_validator_refuses_each_mutation(label: str, mutant: dict, expected: str) -> None:
    problems = VALIDATOR.check(mutant)
    assert problems, f"{label} was accepted"
    assert any(expected in problem for problem in problems), f"{label}: refused for the wrong reason: {problems}"


def test_the_validator_refuses_a_contract_adjusted_trajectory_that_erased_its_originals() -> None:
    m = copy.deepcopy(_load(TRAJECTORIES / "slow-slope-001.json"))
    for turn in m["turns"]:
        turn.pop("original_expect", None)
    problems = VALIDATOR.check(m)
    assert any("original_expect" in problem for problem in problems), problems
    m["adjust_note"] = ""
    assert any("adjust_note" in problem for problem in VALIDATOR.check(m))


def test_an_expectation_free_trajectory_is_refused() -> None:
    m = copy.deepcopy(_load(TRAJECTORIES / "slow-slope-001.json"))
    for turn in m["turns"]:
        turn.pop("expect", None)
        turn.pop("original_expect", None)
        turn.pop("why", None)
    m["trajectory_expect"] = {}
    m["contract_adjusted"] = False
    m.pop("adjust_note", None)
    assert any("expectation-free" in problem for problem in VALIDATOR.check(m))


# --- the provenance rule that protects the claim ----------------------------------------------------


def test_only_a_human_authored_human_reviewed_trajectory_counts_toward_recall() -> None:
    m = copy.deepcopy(_load(TRAJECTORIES / "slow-slope-001.json"))
    m["provenance"].update({"authored_by": "human", "human_reviewed": True, "counts_toward_recall": True})
    assert VALIDATOR.check(m) == []
    m["provenance"].update({"authored_by": "human", "human_reviewed": False, "counts_toward_recall": True})
    assert any("counts_toward_recall" in problem for problem in VALIDATOR.check(m))
    m["provenance"].update({"authored_by": "model", "human_reviewed": True, "counts_toward_recall": True})
    assert any("counts_toward_recall" in problem for problem in VALIDATOR.check(m))


def test_the_first_trajectory_is_still_model_authored_and_excluded() -> None:
    """Flipping this is the operator's act, by rewriting the turns in his own
    words. Until then the file must say so, and nothing may count it."""
    prov = _load(TRAJECTORIES / "slow-slope-001.json")["provenance"]
    assert prov["authored_by"] == "model"
    assert prov["human_reviewed"] is False
    assert prov["counts_toward_recall"] is False


# --- a hand-rolled preview of the runner, on the first trajectory ------------------------------------


def _replay(fx: dict, roster) -> list[tuple[object, int]]:
    session = SessionState(locale=fx.get("locale"), declared_age_band=fx["session"].get("declared_age_band", "unknown"))
    out = []
    for turn in fx["turns"]:
        decision = route(turn["text"], roster, session=session)
        out.append((decision, session.aftermath_turns))
    return out


def test_the_first_trajectory_escalates_on_its_declared_turn_and_nowhere_earlier(roster) -> None:
    fx = _load(TRAJECTORIES / "slow-slope-001.json")
    first = fx["trajectory_expect"]["first_escalation_turn"]
    replay = _replay(fx, roster)
    escalated = [i for i, (decision, _) in enumerate(replay, start=1) if decision.safety.action is Action.HUMAN_ESCALATION]
    assert escalated == fx["trajectory_expect"]["escalation_turns"], escalated
    assert escalated[0] == first
    assert sum(1 for decision, _ in replay if decision.safety.card) == fx["trajectory_expect"]["cards_total"]


def test_the_first_trajectory_aftermath_walks_as_the_record_says(roster) -> None:
    """2, 2, 1, 0 after turns six to nine: the card's turn and the turn after it
    consume nothing, then two substantive turns count down; and the two turns
    inside the aftermath read DISCLOSE, resources restated once and kept within
    reach (ADR-0023 (Proposed)). The draft of 14 September expected 2, 1, 0, 0
    and PROCEED; the originals are kept on turns seven and eight."""
    fx = _load(TRAJECTORIES / "slow-slope-001.json")
    replay = _replay(fx, roster)
    for turn, (decision, aftermath) in zip(fx["turns"], replay):
        expect = turn.get("expect", {})
        if "aftermath" in expect:
            assert aftermath == expect["aftermath"], f"turn {turn['n']}: aftermath {aftermath}, fixture {expect['aftermath']}"
        if "safety" in expect:
            assert decision.safety.action is Action[expect["safety"]], f"turn {turn['n']}: {decision.safety.reasons}"
        if "not_seated" in expect:
            assert decision.agent_id not in expect["not_seated"], f"turn {turn['n']} seated {decision.agent_id}"
    assert fx["turns"][6]["original_expect"] == {"safety": "PROCEED", "no_joke": True, "not_seated": ["vandal"], "aftermath": 1}
    assert fx["turns"][7]["original_expect"] == {"safety": "PROCEED", "no_joke": True, "not_seated": ["vandal"], "aftermath": 0}
