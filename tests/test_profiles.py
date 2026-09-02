"""Invariants that must hold across the whole agent roster.

These are the tests that justify keeping agent definitions as data. A prompt
cannot be asserted against; a profile can.
"""

from __future__ import annotations

import json

import pytest

from secondsignal.profiles import DEFAULT_PROFILE_DIR, load_roster
from secondsignal.signals import DOMAIN_LEXICON, MODE_LEXICON


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def test_roster_loads(roster):
    assert len(roster) >= 5, "roster should contain a meaningful number of agents"


def test_every_handoff_target_resolves(roster):
    for profile in roster.values():
        for condition, target in profile.handoffs.items():
            assert target in roster, (
                f"{profile.id} hands off on {condition!r} to unknown agent {target!r}"
            )


def test_no_agent_hands_off_to_itself(roster):
    for profile in roster.values():
        for condition, target in profile.handoffs.items():
            assert target != profile.id, (
                f"{profile.id} hands off to itself on {condition!r}; this would loop"
            )


def test_regulation_windows_are_wellformed(roster):
    for profile in roster.values():
        low, high = profile.regulation_window
        assert 0.0 <= low <= high <= 1.0, f"{profile.id} has invalid window ({low}, {high})"


def test_roster_has_a_full_range_stabilizer(roster):
    """At least one agent must be safe at regulation 0.0.

    If no agent accepts an acutely dysregulated caller, the router has nowhere
    safe to send them and will be forced into a bad route. This is the single
    most important structural property of a roster.
    """
    # Behavioral, not nominal (ADR-0012): the floor agent must reach 0.0 AND
    # carry no contraindications. A wide window with vetoes does not count.
    stabilizers = [p.id for p in roster.values() if p.is_stabilizer]
    assert stabilizers, "roster has no agent safe at full dysregulation without vetoes"


def test_tags_are_known_vocabulary(roster):
    """Profiles may only reference domain and mode tags the extractor emits.

    Catches the common failure where a profile is written against a tag that no
    signal extractor ever produces, silently making it dead configuration.
    """
    vocabulary = set(DOMAIN_LEXICON) | set(MODE_LEXICON)
    for profile in roster.values():
        unknown = (profile.domains | profile.modes | profile.contraindications) - vocabulary
        assert not unknown, f"{profile.id} references unknown tags: {sorted(unknown)}"

        unknown_conditions = set(profile.handoffs) - vocabulary
        assert not unknown_conditions, (
            f"{profile.id} has handoff conditions outside the vocabulary: "
            f"{sorted(unknown_conditions)}"
        )


def test_every_agent_documents_its_risks(roster):
    """A profile without a stated failure mode has not been thought through."""
    for profile in roster.values():
        assert profile.risks, f"{profile.id} declares no known risks"


def test_no_agent_is_competent_in_a_domain_it_vetoes(roster):
    for profile in roster.values():
        overlap = profile.domains & profile.contraindications
        assert not overlap, (
            f"{profile.id} both claims and vetoes: {sorted(overlap)}"
        )


def test_profiles_are_valid_json_with_required_fields():
    required = {"id", "display_name", "one_line"}
    for path in DEFAULT_PROFILE_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert required <= set(data), f"{path.name} missing {required - set(data)}"


def test_duplicate_ids_are_rejected(tmp_path):
    payload = {
        "id": "duplicate",
        "display_name": "A",
        "one_line": "x",
    }
    (tmp_path / "a.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate agent id"):
        load_roster(tmp_path)


def test_dangling_handoff_is_rejected(tmp_path):
    payload = {
        "id": "solo",
        "display_name": "Solo",
        "one_line": "x",
        "handoffs": {"grief": "nobody"},
    }
    (tmp_path / "solo.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="not a loaded agent"):
        load_roster(tmp_path)
