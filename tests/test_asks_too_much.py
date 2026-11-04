"""Break order 57: the second ask must not offer more than two options.

The fixture lives at tests/fixtures/break57/asks-too-much-grok-ask-second.json
and reuses vague-opener-019 and vague-opener-024. It does not live
under evals/cases, because the constraint is the attached house line, which
the policy runner does not check, and because its expect keys are not routing
keys.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from secondsignal import Action, Outcome, SessionState, load_roster, route
from secondsignal.lexicon import dv_line, resource_line
from secondsignal_harness.lines import HARNESS_LINES_EN

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "break57"
    / "asks-too-much-grok-ask-second.json"
)
DECISION_WORDS = ("choose", "decide", "which do you want", "pick one")
LABEL_ASKS = ("are you depressed", "is this anxiety", "do you have", "are you in crisis")


def _offered_options(question: str) -> list[str]:
    """Doors in an ask of the form 'is this about A, B, or C?'.

    Split only the clause that asks the person to classify. A comma, an
    'or', and the Oxford ', or' are the same separator: ', or' must not leave
    'or' glued to the next door. 'and' does not split. A list of limits is
    not a menu.
    """
    asked = question.split(":", 1)[-1]
    asked = asked.strip().rstrip("?").strip()
    asked = re.sub(r"^is this about\s+", "", asked, flags=re.I)
    parts = re.split(r"\s*,\s*or\s+|\s*,\s*|\s+or\s+", asked)
    return [part.strip() for part in parts if part.strip()]


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def test_the_second_ask_fixture_passes_rule_3(roster) -> None:
    case = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"][0]
    expect = case["expect"]
    assert case["id"] == "asks-too-much-grok-ask-second"
    assert case["source_cases"] == ["vague-opener-019", "vague-opener-024"]
    assert case["prior_turns"] == ["coffee's cold again"]
    assert case["text"] == "snoozed too much"

    session = SessionState(locale=case["locale"])
    for prior in case["prior_turns"]:
        route(prior, roster, session=session)
    decision = route(case["text"], roster, session=session)

    assert decision.safety.action is Action[expect["safety"]]
    assert decision.outcome is Outcome[expect["outcome"]]
    assert decision.agent_id is expect["agent"]
    assert decision.house_ask == expect["house_ask"]

    line = HARNESS_LINES_EN[case["line_key"]]
    assert line == expect["passing_line"]
    assert expect["must_not_say"] not in line
    assert "something you could use a hand with" not in line
    options = _offered_options(line)
    assert options == ["something that happened", "how you're feeling today"]
    assert len(options) <= expect["option_count_max"]
    assert len(expect["options_that_failed"]) == expect["option_count_that_failed"] == 3
    lowered = line.lower()
    assert not any(word in lowered for word in expect["must_not_demand_decision"])
    assert not any(word in lowered for word in expect["must_not_ask_label"])
    assert _offered_options(case["failing_line_verbatim"]) == expect["options_that_failed"]

    # The same two edges the rule has to live with, pinned so a later edit
    # cannot count a limit-list as a menu or let a third door through.
    assert _offered_options(
        "Is there someone you trust who you'd want with you right now, in person or on your phone?"
    ) == ["Is there someone you trust who you'd want with you right now", "in person", "on your phone"]
    card_doors = _offered_options(
        "Is there someone you trust who you'd want with you right now, in person or on your phone?"
    )
    assert len([d for d in card_doors if d in ("in person", "on your phone")]) == 2
    assert _offered_options(
        "Asking a different way: is this about something that happened, something you could use a hand with, or how you're feeling today?"
    ) == expect["options_that_failed"]

def test_the_resource_lines_fixture_is_kept_as_recorded_dissent() -> None:
    """The verified resource lines keep the catalog's wording even where it offers more than two doors, because resource facts are never paraphrased; Grok's fixture is kept as recorded dissent, not applied."""
    fixture = FIXTURE.with_name("asks-too-much-grok-resource-lines.json")
    cases = json.loads(fixture.read_text(encoding="utf-8"))["cases"]
    catalog_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "secondsignal"
        / "packs"
        / "resources.json"
    )
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert cases
    for case in cases:
        assert case["id"].startswith("asks-too-much-grok-")
        language = case["id"].rsplit("-", 1)[1]
        row = catalog["rows"][case["locale"]]
        if "-dv-" in case["id"]:
            line = dv_line(case["locale"], language)
            expected = row["dv"]["lines"][language]
        else:
            line = resource_line(case["locale"], language)
            expected = row["lines"][language]
        assert line == expected
        assert case["expect"]["must_not_say"] in line
