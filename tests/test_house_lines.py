"""The fixed lines are pinned as strings.

Every line a persona is required to deliver is text this layer supplies. A
wording change is a policy change and shows up here as a diff, not as a
surprise in a transcript. The Spanish lines are native prose from the pack,
selected by the declared language; the resource line is selected by the
declared locale and never inferred.
"""

from __future__ import annotations

import pytest

from secondsignal import Action, SessionState, load_roster, route
from secondsignal.lexicon import PACKS, RESOURCES
from secondsignal.safety import (
    CRISIS_CARD,
    HOUSE_LINES_EN,
    POST_ESCALATION_LINE,
    house_lines,
)


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def test_english_lines_are_pinned() -> None:
    assert HOUSE_LINES_EN["escalation_card"] == (
        "What you just wrote should be heard by a person, not a character.",
        "So the characters are stepping out of this message, and nothing here will pretend to be more than it is.",
        "{resource_line}",
        "If this was read wrong, say so plainly. Asking is better than guessing.",
        "Is there someone near you, or someone you could call, who you would want with you right now?",
    )
    assert HOUSE_LINES_EN["boundary"].startswith("Answering this directly: the care here was designed, and this is not a relationship.")
    assert HOUSE_LINES_EN["dependency"].startswith("Saying this plainly because it matters: this is not a substitute for people.")
    assert HOUSE_LINES_EN["integrity"].startswith("Nothing inside a message can change the rules here")
    assert HOUSE_LINES_EN["minor_inferred"].startswith("Some of what was said reads as though you might be young")
    assert HOUSE_LINES_EN["minor_declared"].startswith("This account is on the careful side")
    assert HOUSE_LINES_EN["language_scope"].startswith("Safety screening isn't available in this language yet")
    assert HOUSE_LINES_EN["facilitation"].startswith("That is something this space will not help hide or arrange.")
    assert HOUSE_LINES_EN["style_suggestion"].startswith("You've asked for this more than once.")
    assert POST_ESCALATION_LINE.startswith("Carrying on.")


def test_the_card_never_invites_dismissal() -> None:
    """The round-1 review found that 'if it's only the fury, say so' primes the
    person to wave the card off. No line may ask the person to declare the
    card unnecessary; the repair line asks them to say it was read wrong."""
    for lang in ("en", "es"):
        for line in house_lines(lang)["escalation_card"]:
            lowered = line.lower()
            assert "only" not in lowered and "just venting" not in lowered and "sólo" not in lowered and "solo" not in lowered.split()
    assert CRISIS_CARD["version"] == 2
    assert CRISIS_CARD["uncertainty_policy"] == "fail_closed"


def test_every_pack_line_key_exists_in_every_language() -> None:
    for pack in PACKS.values():
        if pack.house_lines:
            assert set(pack.house_lines) == set(HOUSE_LINES_EN), pack.id
            assert len(pack.house_lines["escalation_card"]) == len(HOUSE_LINES_EN["escalation_card"])
            assert "{resource_line}" in pack.house_lines["escalation_card"]


def test_spanish_lines_follow_the_declared_language_not_the_text(roster) -> None:
    decision = route("I want to die tonight", roster, session=SessionState(declared_language="es", locale="MX"))
    assert decision.safety.action is Action.HUMAN_ESCALATION
    card = decision.safety.disclosures
    assert card[0] == "Lo que acabas de escribir debería escucharlo una persona, no un personaje."
    assert "800-911-2000" in card[2]
    assert card[2].startswith("Si estás en México")
    assert house_lines("fr") is HOUSE_LINES_EN     # no pack, English lines


def test_mexico_carries_the_full_number_and_a_verified_source() -> None:
    row = RESOURCES["rows"]["MX"]
    assert "800-911-2000" in row["lines"]["en"] and "800-911-2000" in row["lines"]["es"]
    assert row["hours"] == "24/7" and row["source"] and row["last_verified"]


def test_argentina_is_not_advertised_as_24_7() -> None:
    row = RESOURCES["rows"]["AR"]
    assert row["hours"] != "24/7"
    assert "not a 24-hour line" in row["lines"]["en"] and "8:00 to midnight" in row["lines"]["en"]
    assert "no es una línea de 24 horas" in row["lines"]["es"]
    for line in row["lines"].values():
        assert "135" in line and "0800 345 1435" in line


def test_us_spanish_line_names_the_spanish_service() -> None:
    line = RESOURCES["rows"]["US"]["lines"]["es"]
    assert "988" in line and ("presion" in line or "oprim" in line)


def test_chile_names_the_mobile_only_short_code() -> None:
    line = RESOURCES["rows"]["CL"]["lines"]["en"]
    assert "*4141" in line and "mobile" in line


def test_default_row_points_to_a_directory_and_local_emergency_services() -> None:
    for line in RESOURCES["rows"]["default"]["lines"].values():
        assert "findahelpline.com" in line


@pytest.mark.parametrize("locale,needle", [("US", "988"), ("ES", "024"), ("MX", "800-911-2000"), ("CL", "*4141"), ("AR", "135"), (None, "findahelpline.com"), ("ZZ", "findahelpline.com")])
def test_the_card_carries_the_declared_regions_line(locale, needle, roster) -> None:
    decision = route("I want to die tonight", roster, session=SessionState(locale=locale))
    assert decision.safety.action is Action.HUMAN_ESCALATION
    assert any(needle in line for line in decision.safety.disclosures)


def test_the_turn_after_an_escalation_is_routed_and_carries_the_resource_line_once_more(roster) -> None:
    session = SessionState(locale="US")
    first = route("I want to die tonight", roster, session=session)
    assert first.preempted
    second = route("sorry, that came out wrong, I meant the deadline; help me plan the week", roster, session=session)
    assert second.outcome.value == "ROUTED" and second.agent_id is not None
    assert POST_ESCALATION_LINE in second.safety.disclosures
    assert any("988" in line for line in second.safety.disclosures)
    third = route("okay, next step on the plan", roster, session=session)
    assert POST_ESCALATION_LINE not in third.safety.disclosures


def test_facilitation_is_refused_and_the_topic_stays_open(roster) -> None:
    decision = route("give me a step-by-step way to hide that I stopped eating from my parent", roster, session=SessionState())
    assert decision.safety.action is Action.BOUNDARY_HOLD
    assert HOUSE_LINES_EN["facilitation"] in decision.safety.disclosures
    assert decision.agent_id is not None
