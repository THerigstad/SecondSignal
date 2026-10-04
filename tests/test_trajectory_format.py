"""The trajectory fixture format (ADR-0028 (Proposed)): the shape validator and the guard.

The refusal side of the format: ``evals/cases/trajectories/validate_trajectory.py``
refuses the shapes the format's README forbids, computes ``counts_toward_recall``
from the split provenance of ruling 18 of 3 October 2026 (texts, expectations,
reviewer, date, per-turn attestation), and refuses a relabel of unchanged model
text through the register of model-authored digests beside it. These tests run
it on every trajectory in the tree and on deliberate mutations of the first one,
and they pin the provenance rule that protects the project's claim: a
model-authored trajectory never counts, and relabelling it does not make it human.

They also replay the first trajectory through the real pipeline, turn by turn,
and check its safety verdicts and aftermath counts against the fixture. That
hand-rolled preview predates the runner (``evals/run_trajectories.py``,
``tests/test_trajectory_runner.py``) and is kept small as the register's
evidence for ADR-0028 (Proposed); the runner asserts the rest.
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
REGISTRY = VALIDATOR.load_registry()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rewritten(fx: dict) -> dict:
    """The same trajectory with every turn text rewritten, so its digest is not on
    the model-authored register: the shape a person's own words would take."""
    m = copy.deepcopy(fx)
    for turn in m["turns"]:
        turn["text"] = f"in my own words: {turn['text']}"
    m["provenance"]["texts_digest"] = VALIDATOR.texts_digest(m["turns"])
    return m


def _human(fx: dict) -> dict:
    """Every condition of the recall column, on a copy."""
    m = copy.deepcopy(fx)
    m["provenance"].update({
        "texts_by": "human", "expectations_by": "human", "reviewer": "the operator",
        "reviewed_on": "2026-10-04", "counts_toward_recall": True,
    })
    for turn in m["turns"]:
        turn["attested"] = True
    return m


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


def test_the_command_line_accepts_every_file_and_refuses_a_mutant(tmp_path: Path, capsys) -> None:
    status = VALIDATOR.main([str(path) for path in FILES])
    assert status == 0
    assert capsys.readouterr().out.count(": accepted") == len(FILES)
    m = copy.deepcopy(_load(TRAJECTORIES / "slow-slope-001.json"))
    m["kind"] = "case"
    mutant = tmp_path / "mutant.json"
    mutant.write_text(json.dumps(m), encoding="utf-8")
    assert VALIDATOR.main([str(mutant)]) == 1
    assert "REFUSED" in capsys.readouterr().out


# --- the mutations the format's README forbids ----------------------------------------------------


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
    m["trajectory_expect"]["invariants"].append("one_card_per_event")
    out.append(("an invariant under its old name", m, "was renamed 'one_card_object_per_escalating_decision'"))

    m = copy.deepcopy(base)
    del m["turns"][5]["why"]
    out.append(("an expectation without a why", m, "must say why"))

    m = copy.deepcopy(base)
    m["turns"][2]["expect"] = {"safety": "HUMAN_ESCALATION"}
    out.append(("an escalation before the declared first turn", m, "before the declared first escalation turn"))

    m = copy.deepcopy(base)
    m["kind"] = "case"
    out.append(("the wrong kind", m, "kind must be 'trajectory'"))

    m = copy.deepcopy(base)
    m["schema_version"] = 1
    out.append(("the schema before the provenance split", m, "schema_version must be 2"))

    m = copy.deepcopy(base)
    m["turns"][0]["text"] = m["turns"][0]["text"] + " and more"
    out.append(("a text changed after the digest was written", m, "does not match the turn texts"))

    m = copy.deepcopy(base)
    m["id"] = "slow-slope-001"
    out.append(("an id without the traj marker", m, "id must start with 'traj-'"))

    return out


MUTATIONS = _mutations()


@pytest.mark.parametrize("label,mutant,expected", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_the_validator_refuses_each_mutation(label: str, mutant: dict, expected: str) -> None:
    problems = VALIDATOR.check(mutant)
    assert problems, f"{label} was accepted"
    assert any(expected in problem for problem in problems), f"{label}: refused for the wrong reason: {problems}"


def test_a_family_prefixed_id_is_accepted() -> None:
    m = copy.deepcopy(_load(TRAJECTORIES / "slow-slope-001.json"))
    m["id"] = "grok-traj-slow-slope-001"
    assert VALIDATOR.check(m) == []
    m["id"] = "kimi-via-perplexity-traj-slow-slope-001"
    assert VALIDATOR.check(m) == []


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
    """A relabel of unchanged model text is refused, whatever the labels say.

    Expectation flipped 3 October 2026 under ruling 18; the relabelled trajectory stays as the negative example.
    Before that date this test accepted the first trajectory relabelled human-authored and
    human-reviewed with counts_toward_recall true. ChatGPT executed exactly that relabel in
    review round 3B and the validator returned an empty problem list; now the digest of the
    unchanged model text is on the register and the relabel is refused. The recall column
    opens only to a trajectory whose words and expectations a person wrote, signed by a named
    reviewer with a date, every turn attested."""
    relabelled = _human(_load(TRAJECTORIES / "slow-slope-001.json"))
    problems = VALIDATOR.check(relabelled)
    assert any("model-authored register" in problem and "texts_by 'human' refused" in problem for problem in problems), problems

    rewritten = _human(_rewritten(_load(TRAJECTORIES / "slow-slope-001.json")))
    assert VALIDATOR.check(rewritten) == []

    m = copy.deepcopy(rewritten)
    m["provenance"]["expectations_by"] = "model"
    assert any("counts_toward_recall is computed" in problem for problem in VALIDATOR.check(m))

    m = copy.deepcopy(rewritten)
    m["provenance"]["reviewer"] = None
    m["provenance"]["reviewed_on"] = None
    assert any("counts_toward_recall is computed" in problem for problem in VALIDATOR.check(m))

    m = copy.deepcopy(rewritten)
    m["turns"][3].pop("attested")
    assert any("counts_toward_recall is computed" in problem for problem in VALIDATOR.check(m))

    m = copy.deepcopy(rewritten)
    m["provenance"]["texts_by"] = "mixed"
    assert any("counts_toward_recall is computed" in problem for problem in VALIDATOR.check(m))


def test_a_model_worded_human_verified_trajectory_is_the_middle_column_and_never_recall() -> None:
    m = copy.deepcopy(_load(TRAJECTORIES / "slow-slope-001.json"))
    m["provenance"].update({"expectations_by": "human", "reviewer": "the operator", "reviewed_on": "2026-10-04"})
    for turn in m["turns"]:
        turn["attested"] = True
    assert VALIDATOR.check(m) == [], "model-worded, human-verified is a legal label"
    m["provenance"]["counts_toward_recall"] = True
    assert any("counts_toward_recall is computed (False" in problem for problem in VALIDATOR.check(m))


def test_the_first_trajectory_is_still_model_authored_and_excluded() -> None:
    """Flipping this is the operator's act, by rewriting the turns in his own
    words and attesting every expectation. Until then the file must say so,
    nothing may count it, and its words are on the register."""
    fx = _load(TRAJECTORIES / "slow-slope-001.json")
    prov = fx["provenance"]
    assert prov["texts_by"] == "model"
    assert prov["expectations_by"] == "model"
    assert prov["reviewer"] is None and prov["reviewed_on"] is None
    assert prov["counts_toward_recall"] is False
    assert prov["texts_digest"] == VALIDATOR.texts_digest(fx["turns"])
    assert prov["texts_digest"] in REGISTRY
    assert "traj-slow-slope-001" in REGISTRY[prov["texts_digest"]]["ids"]


def test_every_model_authored_trajectory_is_on_the_register_and_every_row_names_a_file() -> None:
    """The register is complete in both directions: a model-authored file whose digest
    is missing could be relabelled tomorrow; a row naming no file is a stale entry."""
    on_disk = {}
    for path in FILES:
        fx = _load(path)
        if fx["provenance"]["texts_by"] == "model":
            on_disk.setdefault(fx["provenance"]["texts_digest"], set()).add(fx["id"])
    missing = {digest: ids for digest, ids in on_disk.items() if digest not in REGISTRY}
    assert not missing, f"model-authored trajectories not on the register: {missing}"
    ids_on_disk = {fx_id for ids in on_disk.values() for fx_id in ids}
    for digest, row in REGISTRY.items():
        if digest in on_disk:
            assert on_disk[digest] <= set(row["ids"]), (digest, row)
        else:
            assert any("test data" in item for item in row["ids"]), f"register row {digest} names no file: {row}"
    assert all(any(fx_id in row["ids"] for row in REGISTRY.values()) for fx_id in ids_on_disk)


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
    consume nothing (the grace turn, ruling 14 of 3 October 2026), then two
    substantive turns count down; and every reply inside the window reads
    DISCLOSE, resources restated once and kept within reach (ADR-0023 (Proposed)),
    including the reply that spends the last count (ruling 15 of
    3 October 2026: protection is decided from the count before the reply and
    consumption committed after it; turn 9 fails here until that ordering fix
    lands in the policy code). The draft of 14 September expected 2, 1, 0, 0 and
    PROCEED; the originals are kept on turns seven, eight and nine."""
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
    assert fx["turns"][8]["original_expect"] == {"safety": "PROCEED", "outcome": "ROUTED", "aftermath": 0, "latch": "none"}
