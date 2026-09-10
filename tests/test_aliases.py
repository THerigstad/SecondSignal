"""The alias layer: one persona, several names, one canonical id.

On 2026-09-10 the family's canonical names changed so that each reads
naturally for either twin (ADR-0026 (Proposed)): Calder became Cody, Ellie
became Ellis, Sera became Seren, Ravi became Rowan; Nikki, Willow and Vandal
kept their names and Nikki, Willow and Ellis gained short forms. The rename is
not a find-and-replace. Every fixture an external reviewer returned under an
earlier name stays byte for byte as it was returned and resolves through the
roster; the decision record always carries the canonical id; and no two
personas may share a name in any form.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from secondsignal import SessionState, load_roster, route
from secondsignal.preferences import assess
from secondsignal.profiles import (
    DEFAULT_PROFILE_DIR,
    Roster,
    canonical_id,
    canonicalize_expectation,
    default_aliases,
    known_persona_names,
)

RENAMES = {
    "calder": "cody",
    "ellie": "ellis",
    "elli": "ellis",
    "sera": "seren",
    "ravi": "rowan",
    "nik": "nikki",
    "will": "willow",
}
CANONICAL = ("cody", "ellis", "nikki", "rowan", "seren", "vandal", "willow")


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _copy_profiles(target: Path, edit=None) -> Path:
    target.mkdir()
    for path in sorted(DEFAULT_PROFILE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if edit:
            edit(data)
        (target / path.name).write_text(json.dumps(data), encoding="utf-8")
    return target


# --- resolution ---------------------------------------------------------------------------

def test_the_roster_is_the_seven_canonical_ids_and_nothing_else(roster) -> None:
    assert isinstance(roster, Roster)
    assert tuple(sorted(roster)) == CANONICAL
    assert len(roster) == 7
    assert set(roster.keys()) == set(CANONICAL)


def test_every_earlier_name_and_short_form_resolves_to_its_persona(roster) -> None:
    for alias, canonical in RENAMES.items():
        assert roster.resolve(alias) == canonical
        assert roster[alias] is roster[canonical]
        assert alias in roster
    assert roster.aliases() == RENAMES


def test_vandal_has_no_alias_and_the_canonical_ids_resolve_to_themselves(roster) -> None:
    assert roster["vandal"].aliases == ()
    for canonical in CANONICAL:
        assert roster.resolve(canonical) == canonical


def test_resolution_is_case_and_whitespace_insensitive(roster) -> None:
    assert roster.resolve(" Calder ") == "cody"
    assert roster["SERA"].id == "seren"


def test_an_unknown_name_raises_unless_asked_to_pass_through(roster) -> None:
    with pytest.raises(KeyError):
        roster.resolve("quill")
    assert roster.resolve("quill", strict=False) == "quill"
    assert "quill" not in roster
    assert roster.get("quill") is None
    assert roster.resolve(None) is None


def test_handoffs_carry_canonical_ids_only(roster) -> None:
    for profile in roster.values():
        for target in profile.handoffs.values():
            assert target in CANONICAL, (profile.id, target)


# --- load-time refusals ---------------------------------------------------------------------

def test_two_personas_may_not_share_an_alias(tmp_path) -> None:
    def edit(data):
        if data["id"] in ("cody", "seren"):
            data["aliases"] = list(data.get("aliases", [])) + ["cal"]
    with pytest.raises(ValueError, match="no two agents may share a name"):
        load_roster(_copy_profiles(tmp_path / "shared", edit))


def test_an_alias_may_not_be_another_personas_id(tmp_path) -> None:
    def edit(data):
        if data["id"] == "cody":
            data["aliases"] = list(data.get("aliases", [])) + ["willow"]
    with pytest.raises(ValueError, match="no two agents may share a name"):
        load_roster(_copy_profiles(tmp_path / "collide", edit))


def test_a_handoff_written_under_an_alias_loads_and_is_normalized(tmp_path) -> None:
    def edit(data):
        if data["id"] == "vandal":
            data["handoffs"]["grief"] = "will"
            data["handoffs"]["somatic_distress"] = "calder"
    loaded = load_roster(_copy_profiles(tmp_path / "alias_handoff", edit))
    assert loaded["vandal"].handoffs["grief"] == "willow"
    assert loaded["vandal"].handoffs["somatic_distress"] == "cody"


def test_an_unresolvable_handoff_still_refuses_to_load(tmp_path) -> None:
    def edit(data):
        if data["id"] == "vandal":
            data["handoffs"]["grief"] = "quill"
    with pytest.raises(ValueError, match="not a loaded agent"):
        load_roster(_copy_profiles(tmp_path / "dangling", edit))


# --- the decision record and the fixtures ---------------------------------------------------

def test_the_decision_record_carries_the_canonical_id(roster) -> None:
    decision = route("I relapsed after my brother died", roster)
    assert decision.agent_id == "cody"
    assert {s.agent_id for s in decision.ranked} == set(CANONICAL)


def test_a_declared_affinity_under_an_earlier_name_is_the_same_affinity(roster) -> None:
    old = route("I need structure this week", roster, session=SessionState(affinities=("prefers_calder",)))
    new = route("I need structure this week", roster, session=SessionState(affinities=("prefers_cody",)))
    assert (old.agent_id, old.assist_agent_id, old.held, old.obligations) == (
        new.agent_id, new.assist_agent_id, new.held, new.obligations
    )


def test_a_fixture_expectation_under_an_earlier_name_is_resolved_before_comparison() -> None:
    expect = {
        "agent": "calder",
        "assist": "sera",
        "agent_any_of": ["ravi", "ellie"],
        "not_seated": ["vandal", "quill"],
        "safety": "PROCEED",
    }
    resolved = canonicalize_expectation(expect)
    assert resolved["agent"] == "cody"
    assert resolved["assist"] == "seren"
    assert resolved["agent_any_of"] == ["rowan", "ellis"]
    assert resolved["not_seated"] == ["vandal", "quill"]   # unknown names pass through and fail visibly
    assert resolved["safety"] == "PROCEED"
    assert expect["agent"] == "calder"                        # the fixture itself is never rewritten


def test_canonical_id_leaves_none_and_unknown_names_alone() -> None:
    assert canonical_id(None) is None
    assert canonical_id("calder") == "cody"
    assert canonical_id("quill") == "quill"
    assert default_aliases() == RENAMES


def test_external_reviewer_fixtures_still_name_personas_by_their_earlier_names() -> None:
    """The alias layer exists so these files never have to change."""
    grok = json.loads((Path(__file__).resolve().parents[1] / "evals" / "cases" / "external_review_grok_2026-09-01.json").read_text(encoding="utf-8"))
    names = {c["expect"].get("agent") for c in grok["cases"] if isinstance(c.get("expect"), dict)}
    assert "calder" in names


# --- a persona named in a message ------------------------------------------------------------

def test_every_name_a_persona_answers_to_is_an_envelope_term_when_a_seat_is_demanded() -> None:
    names = known_persona_names()
    assert set(names) == set(CANONICAL) | set(RENAMES)
    for name in names:
        event = assess(f"from now on always seat {name}")
        assert event is not None and event.result == "refused", name
