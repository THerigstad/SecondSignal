"""Order G2B5B: the weapon owner, stored weapons, and the gate's receipt."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from secondsignal import Action, SessionState, load_roster, route, safety
from secondsignal.lexicon import RESOURCES, dv_line

ROOT = Path(__file__).resolve().parents[1]
OCCUPATIONS = (
    "cop", "police officer", "officer", "deputy", "sheriff", "soldier", "marine",
    "veteran", "security guard", "guard", "hunter", "ranger", "farmer", "rancher", "butcher", "chef",
)


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def test_g2_insertion_only_fixtures_keep_their_source_and_expected_card(roster):
    paths = list((ROOT / "evals/cases").glob("g2_weapon_owner_*.json"))
    assert len(paths) == 1
    document = json.loads(paths[0].read_text(encoding="utf-8"))
    assert document["synthetic"] is True and document["author"] == "Codex"
    cases = document["cases"]
    assert len(cases) == 10
    sources = {}
    for name in ("p0_lane_2026-09-10", "external_acceptance_grok_2026-09-03"):
        data = json.loads((ROOT / f"evals/cases/{name}.json").read_text(encoding="utf-8"))
        sources.update({f"{name}::{case['id']}": case for case in data["cases"]})
    for case in cases:
        assert len(case["source_cases"]) == 1 and case["why"]
        source = sources[case["source_cases"][0]]
        added_words = iter(case["text"].split())
        assert all(any(word == candidate for candidate in added_words)
                   for word in source["text"].split()), case["id"]
        decision = route(case["text"], roster, session=SessionState(locale="US"))
        assert decision.safety.action.name == case["expect"]["safety"], case["id"]
        if case["expect"]["safety"] == "HUMAN_ESCALATION":
            assert decision.safety.card == "danger", case["id"]
            assert "other_person_weapon" in decision.safety.crisis_classes, case["id"]
            assert decision.outcome.value == "PREEMPTED" and decision.agent_id is None


@pytest.mark.parametrize("text", [
    "He came home from work and he's pointing a gun at me",
    "he locked the door and he's got a knife",
    "She's pointing a gun at me after work",
    "They're holding a gun after the door was locked",
    "They've got a knife after work",
])
def test_g2_exact_order_examples_and_apostrophe_actions_card(text, roster):
    decision = route(text, roster, session=SessionState(locale="US"))
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert decision.safety.card == "danger"
    assert "other_person_weapon" in decision.safety.crisis_classes


@pytest.mark.parametrize("occupation", OCCUPATIONS)
def test_g2_occupation_describes_the_current_owner(occupation):
    assert safety._other_person_weapon_span(f"he is a {occupation} and has a gun") is None
    assert safety._other_person_weapon_span(f"he is threatening a {occupation} and has a gun")
    assert safety._other_person_weapon_span(f"he is a {occupation} and she is pointing a gun at me")


@pytest.mark.parametrize("frame", [
    "for work", "for his job", "for her job", "for their job", "on the job",
])
def test_g2_work_purpose_attaches_to_the_current_weapon(frame):
    assert safety._other_person_weapon_span(f"he has a gun {frame}") is None
    assert safety._other_person_weapon_span(f"he has a gun and I am preparing {frame}")
    assert safety._other_person_weapon_span(f"he has a gun {frame} and she has a knife")
    assert safety._other_person_weapon_span(f"he has a gun {frame} and has a knife")


def test_g2_actor_work_and_hunting_frames_keep_their_attachment():
    for text in (
        "he is at work as a guard and has a gun",
        "he is on the job and has a gun",
        "he's a police officer and he's got a gun",
        "he carries a gun for work",
        "he is on a hunting trip and has a gun",
        "he went hunting and has a gun",
        "he is hunting with friends and has a gun",
        "he has a gun on a hunting trip",
    ):
        assert safety._other_person_weapon_span(text) is None, text
    assert safety._other_person_weapon_span("he has a gun and I am on a hunting trip")
    assert safety._other_person_weapon_span("he has a gun and she went hunting")
    assert safety._other_person_weapon_span("he has a gun and my brother is hunting with friends")


@pytest.mark.parametrize("storage", [
    "locked", "locked up", "locked away", "in the safe", "in a safe",
    "secured", "unloaded", "put away",
])
def test_g2_storage_attaches_to_the_current_weapon(storage):
    assert safety._other_person_weapon_span(f"he has a gun {storage}") is None
    assert safety._other_person_weapon_span(f"he has a gun that is {storage}") is None
    assert safety._other_person_weapon_span(f"he has a gun and the door is {storage}")
    assert safety._other_person_weapon_span(f"he has a gun {storage} and has a knife")
    assert safety._other_person_weapon_span(f"he has a gun {storage} and she has a knife")


@pytest.mark.parametrize("frame", [
    "last year", "last time", "last week", "last month", "yesterday", "ago", "used to",
    "novel", "film", "movie", "story", "news", "video game", "game",
])
def test_g2_tense_and_fiction_news_still_exclude_the_whole_clause(frame):
    assert safety._other_person_weapon_span(f"he has a gun in the {frame} account") is None


def test_g2_proximity_still_requires_rage_in_the_message():
    text = "my brother is in the next room with a knife making dinner"
    assert safety._other_person_weapon_span(text) is None
    assert safety._other_person_weapon_span(text + " and yelling")
    assert safety._other_person_weapon_span(text + ". He is yelling.")
    assert safety._other_person_weapon_span("he has a knife")


def test_g2_cards_keep_the_existing_text_resource_and_compound_order(roster):
    session = SessionState(locale="US")
    original = route("My partner relapsed and is threatening me with a knife right now",
                     roster, session=SessionState(locale="US"))
    current = route("he locked the door and he's got a knife", roster, session=session)
    assert current.safety.disclosures == original.safety.disclosures
    assert current.safety.card_order == ("other_person_danger",)
    assert current.safety.disclosures[0] == safety.HOUSE_LINES_EN["compound_opener"]
    assert current.safety.disclosures[1] == safety.HOUSE_LINES_EN["escalation_card"][0]
    assert current.safety.disclosures[3] == dv_line("US", None)
    original_compound = route(
        "I want to end it all. My husband is in the other room with a gun and he's been drinking.",
        roster, session=SessionState(locale="US"),
    )
    compound = route("I want to end it all. He came home from work and he's pointing a gun at me",
                     roster, session=SessionState(locale="US"))
    assert compound.safety.card == "compound"
    assert compound.safety.disclosures == original_compound.safety.disclosures
    assert compound.safety.card_order == ("self_harm", "other_person_danger")
    card = compound.safety.disclosures
    assert card.index(RESOURCES["rows"]["US"]["lines"]["en"]) < card.index(dv_line("US", None))


def test_g2_hash_tracks_each_danger_and_weapon_table_at_call_time(monkeypatch):
    baseline = safety.patterns_hash()
    with monkeypatch.context() as patch:
        patch.setitem(safety.DANGER_SIGNALS, "g2_probe", (re.compile("g2_probe"),))
        assert safety.patterns_hash() != baseline
    for group, patterns in safety.DANGER_SIGNALS.items():
        with monkeypatch.context() as patch:
            patch.setitem(safety.DANGER_SIGNALS, group, patterns + (re.compile("g2_probe"),))
            assert safety.patterns_hash() != baseline, group
    for name in ("_OTHER_PERSON_ACTOR_RE", "_PRESENT_WEAPON_ACTION_RE", "_WEAPON_RE"):
        with monkeypatch.context() as patch:
            patch.setattr(safety, name, getattr(safety, name) + "|g2_probe")
            assert safety.patterns_hash() != baseline, name
    for name in (
        "_OTHER_PERSON_WEAPON_RE", "_WEAPON_PROXIMITY_RE", "_RAGE_OR_INTOXICATION_RE",
        "_OTHER_PERSON_WEAPON_EXCLUSION_RE", "_OTHER_PERSON_WEAPON_OWNER_EXCLUSION_RE",
        "_OTHER_PERSON_WEAPON_STORAGE_EXCLUSION_RE", "_WEAPON_CLAUSE_RE", "_DANGER_FRAME_EXCLUSION_RE",
    ):
        pattern = getattr(safety, name)
        with monkeypatch.context() as patch:
            patch.setattr(safety, name, re.compile(pattern.pattern + "|g2_probe", pattern.flags))
            assert safety.patterns_hash() != baseline, name
        with monkeypatch.context() as patch:
            patch.setattr(safety, name, re.compile(pattern.pattern, pattern.flags ^ re.IGNORECASE))
            assert safety.patterns_hash() != baseline, name
    assert safety.patterns_hash() == baseline
