"""The presentation block and the name plate (ADR-0026 (Proposed) as amended 2026-09-11).

The operator's ruling of 11 September 2026, in his own words where the
record kept them: every plate shows two name forms, "printed twice" when the
name does not shorten ("Cody / Cody"); the second form is the first with
letters dropped, so a reader can see the two forms are one person; a "she"
and a "he" label on the halves, and the rule for the neutral presentation
written at the same time, never later: "Every character comes as a woman, a
man, or neither, your choice at the door and changeable any time, same
knowledge, same rules; the second name is the first one shortened so you can
see it is one person."

These tests pin the data and the helper a surface reads. They pin nothing
about routing except that routing does not read this block at all.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from secondsignal.profiles import AgentProfile, load_roster

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "src" / "secondsignal" / "profiles"
ROUTING_MODULES = ("router.py", "safety.py", "signals.py", "preferences.py", "lexicon.py", "normalize.py", "jr.py")

PERMITTED_KEYS = {"as_written", "she", "he", "they"}

# The ruling's plates, one per persona: full form first, shortened second, labels on each.
RULED_PLATES = {
    "cody": (("Cody", "she"), ("Cody", "he")),
    "vandal": (("Vandal", "she"), ("Vandal", "he")),
    "nikki": (("Nikki", "she"), ("Nik", "he")),
    "willow": (("Willow", "she"), ("Will", "he")),
    "ellis": (("Ellis", "he"), ("Elli", "she")),
    "seren": (("Seren", "she"), ("Seren", "he")),
    "rowan": (("Rowan", "she"), ("Rowan", "he")),
}


def _raw_profiles() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(PROFILES.glob("*.json"))}


@pytest.fixture(scope="module")
def roster():
    return load_roster()


# --- the block ------------------------------------------------------------------------------


@pytest.mark.parametrize("pid", sorted(RULED_PLATES))
def test_every_family_profile_carries_the_block_with_exactly_the_permitted_keys(pid: str) -> None:
    data = _raw_profiles()[pid]
    block = data["presentation"]
    assert set(block) == PERMITTED_KEYS, f"{pid}: keys {sorted(block)}"
    assert block["as_written"] in ("she", "he")
    assert block["they"] == "either", "the neutral presentation goes by either form, the person's choice"
    assert block["she"].strip() and block["he"].strip()


@pytest.mark.parametrize("pid", sorted(RULED_PLATES))
def test_the_as_written_presentation_agrees_with_the_voice_field(pid: str) -> None:
    """`voice` is the field the tie-break reads today; ADR-0026 (Proposed) makes it the
    "as written" default of the presentation block. Until the router changes,
    the two must say the same thing."""
    data = _raw_profiles()[pid]
    assert data["presentation"]["as_written"] == {"f": "she", "m": "he"}[data["voice"]]


@pytest.mark.parametrize("pid", sorted(RULED_PLATES))
def test_the_two_forms_are_the_display_name_and_its_short_form(pid: str) -> None:
    """The dropped-letter rule: the short form is the full name with letters
    dropped from the end (Elli from Ellis, Nik from Nikki, Will from Willow),
    and a persona whose name does not shorten uses the same word for both."""
    data = _raw_profiles()[pid]
    forms = {data["presentation"]["she"], data["presentation"]["he"]}
    full, short = data["display_name"], data.get("short_name", "")
    if short:
        assert short != full and full.startswith(short), f"{pid}: {short!r} is not {full!r} with letters dropped from the end"
        assert forms == {full, short}
    else:
        assert forms == {full}


@pytest.mark.parametrize("pid", sorted(RULED_PLATES))
def test_both_forms_resolve_to_the_same_persona_through_the_alias_layer(pid: str, roster) -> None:
    profile = roster[pid]
    for form in (profile.presentation["she"], profile.presentation["he"]):
        assert roster.resolve(form) == pid, f"{form!r} must resolve to {pid}"


# --- the plate ------------------------------------------------------------------------------


@pytest.mark.parametrize("pid", sorted(RULED_PLATES))
def test_the_plate_is_the_ruled_one(pid: str, roster) -> None:
    """Always two names, the full one first, the shortened second, each with
    its label; printed twice when they are the same word (she, then he)."""
    plate = roster[pid].plate
    assert plate == RULED_PLATES[pid]
    assert len(plate) == 2
    (first, first_label), (second, second_label) = plate
    assert {first_label, second_label} == {"she", "he"}
    assert len(first) >= len(second)


def test_a_profile_without_the_block_still_plates_two_names() -> None:
    bare = AgentProfile(id="x", display_name="Sam", one_line="")
    assert bare.plate == (("Sam", "she"), ("Sam", "he"))


def test_name_for_each_door_answer(roster) -> None:
    ellis, nikki, cody = roster["ellis"], roster["nikki"], roster["cody"]
    assert ellis.name_for("women") == ("Elli", "she")
    assert ellis.name_for("men") == ("Ellis", "he")
    assert ellis.name_for("as_written") == ("Elli", "she"), "Ellis was written as a woman; as written lights the she form"
    assert nikki.name_for("as_written") == ("Nikki", "she")
    assert cody.name_for("as_written") == ("Cody", "he")
    # neither: they, and the full form until the person picks one of the two forms
    assert ellis.name_for("neither") == ("Ellis", "they")
    assert ellis.name_for("neither", chosen="Elli") == ("Elli", "they")
    assert ellis.name_for("neither", chosen="Ellie") == ("Ellis", "they"), "a retired name is not a form"
    assert cody.name_for("neither", chosen="Cody") == ("Cody", "they")


# --- routing does not read it ---------------------------------------------------------------


def test_no_routing_module_reads_the_presentation_block() -> None:
    """ADR-0026 (Proposed), invariant 2, in the only form the tree can pin before a
    presentation setting exists: the modules that decide seat, hold, card and
    verdict never mention the block or the plate."""
    # attribute or key access to the block, or a call to the helpers; the bare
    # word is a career-domain lexicon entry in signals.py and is not a read
    pattern = re.compile(r"\.presentation\b|\[\s*[\"']presentation[\"']\s*\]|get\(\s*[\"']presentation[\"']|\.plate\b|name_for\(")
    src = ROOT / "src" / "secondsignal"
    for name in ROUTING_MODULES:
        text = (src / name).read_text(encoding="utf-8")
        assert not pattern.search(text), f"{name} reads the presentation block; routing must not"


def test_the_block_does_not_change_the_roster_hash_semantics(roster) -> None:
    """Every profile is hashed as loaded, so adding the block changed every
    source hash once, visibly, and a later silent edit stays visible."""
    for pid in RULED_PLATES:
        assert len(roster[pid].source_hash) == 12
