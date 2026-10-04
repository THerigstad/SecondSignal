"""The four-setting test (ruling 11 of 3 October 2026; ADR-0026 (Proposed) invariant 2).

Every labelled single-turn case runs under all four presentation settings
("as_written", "women", "men", "neither") and the whole decision record,
``to_dict()`` with the explain string and the ranked trace inside it, must be
identical except for the ``presentation`` field itself. The "neither" setting
is also run with each of a persona's two name forms chosen. On failure the
test names the field that moved first.

The session carries the setting (ruling 11 landed it with this test, because
looping over four labels while calling the router identically proves nothing
until the session has a field to read, as ChatGPT cautioned). A negative
control injects a reroute that reads the setting and checks that the
comparison catches it, so the test cannot pass vacuously.

Base: Kimi K3 High's module; ChatGPT's negative control; GLM via Perplexity's
whole-record comparison including the explain string; Qwen's named field on
failure. The static source grep that stood in for this pin before the ruling
is kept in tests/test_presentations.py as a lint.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from test_eval_cases import CASES, _prior_text

from secondsignal import SessionState, load_roster, route
from secondsignal import router as router_module
from secondsignal import safety as safety_module
from secondsignal.safety import PRESENTATIONS

SETTINGS = PRESENTATIONS
assert SETTINGS == ("as_written", "women", "men", "neither")


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _session(case: dict, setting: str, chosen_names: dict[str, str] | None = None) -> SessionState:
    block = case.get("session") or {}
    return SessionState(
        locale=case.get("locale"),
        declared_language=block.get("declared_language"),
        declared_age_band=block.get("declared_age_band", "unknown"),
        affinities=tuple(block.get("affinities", ())),
        preferences=dict(block.get("preferences", {})),
        presentation=setting,
        chosen_names=dict(chosen_names or {}),
    )


def _record(case: dict, roster, setting: str, chosen_names: dict[str, str] | None = None) -> dict[str, Any]:
    session = _session(case, setting, chosen_names)
    for prior in case.get("prior_turns", []):
        route(_prior_text(prior), roster, session=session)
    decision = route(case["text"], roster, session=session)
    record = decision.to_dict()
    assert record["presentation"]["setting"] == setting
    return record


def first_difference(a: Any, b: Any, path: str = "") -> str | None:
    """The dotted path of the first leaf that differs, or None when equal."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in list(a) + [k for k in b if k not in a]:
            if key not in a or key not in b:
                return f"{path}.{key}".lstrip(".")
            found = first_difference(a[key], b[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}[len {len(a)} vs {len(b)}]".lstrip(".")
        for i, (x, y) in enumerate(zip(a, b)):
            found = first_difference(x, y, f"{path}[{i}]")
            if found:
                return found
        return None
    return None if a == b else path.lstrip(".")


def without_presentation(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "presentation"}


def assert_identical_except_presentation(records: dict[str, dict[str, Any]], label: str) -> None:
    base_setting, base = next(iter(records.items()))
    for setting, record in records.items():
        moved = first_difference(without_presentation(base), without_presentation(record))
        assert moved is None, (
            f"{label}: the decision under {setting!r} differs from {base_setting!r}; "
            f"the field that moved first is {moved!r}"
        )
        # The explain string is part of the record and is compared above; say so explicitly.
        assert record["explain"] == base["explain"], f"{label}: the explain string moved under {setting!r}"
        assert json.dumps(without_presentation(record), sort_keys=True) == json.dumps(without_presentation(base), sort_keys=True)


# --- every labelled case under all four settings ------------------------------------------------


@pytest.mark.parametrize("label,case", CASES, ids=[label for label, _ in CASES])
def test_the_whole_decision_is_identical_under_all_four_settings(label: str, case: dict, roster) -> None:
    records = {setting: _record(case, roster, setting) for setting in SETTINGS}
    assert_identical_except_presentation(records, label)
    assert {r["presentation"]["setting"] for r in records.values()} == set(SETTINGS)


def test_neither_with_each_chosen_name_form_changes_nothing_but_the_presentation(roster) -> None:
    """Under "neither" the person may pick either of a persona's two forms; the
    choice is carried on the record and moves nothing else."""
    sample = [case for _, case in CASES if not case.get("prior_turns")][:40]
    assert len(sample) == 40
    for case in sample:
        records = {"as_written": _record(case, roster, "as_written")}
        for pid, profile in roster.items():
            for form in (profile.presentation.get("she") or profile.display_name, profile.presentation.get("he") or profile.display_name):
                key = f"neither:{pid}={form}"
                records[key] = _record(case, roster, "neither", {pid: form})
                assert records[key]["presentation"] == {"setting": "neither", "chosen_names": {pid: form}}
        assert_identical_except_presentation(records, case["id"])


# --- the field itself ---------------------------------------------------------------------------


def test_the_session_field_defaults_to_as_written_and_refuses_an_unknown_setting() -> None:
    assert SessionState().presentation == "as_written"
    assert SessionState().chosen_names == {}
    assert SessionState(presentation="neither", chosen_names={"ellis": "Elli"}).chosen_names == {"ellis": "Elli"}
    with pytest.raises(ValueError, match="presentation must be one of"):
        SessionState(presentation="woman")


@pytest.mark.parametrize("text", [
    "from now on, use a woman's voice",
    "always speak as a man",
    "set my default: present everyone as women",
    "presentation = women",
    "switch to neither and call them they",
])
def test_message_text_never_writes_the_presentation(text: str, roster) -> None:
    """A request in a message is at most a preference event the operator
    confirms (ask_first) or a refusal; the setting itself is written only by
    the operator's surface."""
    session = SessionState(locale="US")
    decision = route(text, roster, session=session)
    assert session.presentation == "as_written" and session.chosen_names == {}
    assert decision.presentation.setting == "as_written"
    assert decision.safety.preference_result in (None, "ask_first", "refused")


def test_the_record_carries_the_setting_and_the_explain_string_does_not(roster) -> None:
    for setting in SETTINGS:
        decision = route("help me plan the launch", roster, session=SessionState(presentation=setting))
        record = decision.to_dict()
        assert record["presentation"] == {"setting": setting, "chosen_names": {}}
        assert "presentation" not in record["explain"].casefold().replace("presentation=", "")
        assert setting not in record["explain"] or setting == "as_written"
    bare = route("help me plan the launch", roster).to_dict()
    assert bare["presentation"] == {"setting": "as_written", "chosen_names": {}}


# --- the negative control (ChatGPT's) -----------------------------------------------------------


def _first_case_with_a_seat(roster) -> dict:
    for _, case in CASES:
        if case.get("prior_turns") or case.get("session"):
            continue
        if route(case["text"], roster).agent_id is not None:
            return case
    raise AssertionError("no seated single-turn case found")


def test_an_injected_reroute_through_the_assist_is_caught(monkeypatch, roster) -> None:
    """A seat rule that peeks at the setting: the assist flips under "women".
    The comparison must catch it and name the field."""
    case = _first_case_with_a_seat(roster)
    original = router_module._assist

    def leaky_assist(session, roster_, signals, seated, holds, claims, mode_vetoes):
        if session is not None and session.presentation == "women":
            other = next(pid for pid in sorted(roster_) if pid != seated)
            return other, "leak: chosen by presentation"
        return original(session, roster_, signals, seated, holds, claims, mode_vetoes)

    monkeypatch.setattr(router_module, "_assist", leaky_assist)
    records = {setting: _record(case, roster, setting) for setting in SETTINGS}
    with pytest.raises(AssertionError) as caught:
        assert_identical_except_presentation(records, case["id"])
    assert "the field that moved first is 'assist_agent_id'" in str(caught.value)


def test_an_injected_reroute_through_the_verdict_is_caught(monkeypatch, roster) -> None:
    """The verdict path: a reason appended only under "men" must be caught too,
    and the field named is the first one that moved."""
    case = _first_case_with_a_seat(roster)
    original = safety_module.evaluate

    def leaky_evaluate(text, signals, session=None):
        verdict = original(text, signals, session)
        if session is not None and session.presentation == "men":
            from dataclasses import replace
            return replace(verdict, reasons=verdict.reasons + ("leak: read the presentation",))
        return verdict

    monkeypatch.setattr(router_module, "evaluate", leaky_evaluate)
    records = {setting: _record(case, roster, setting) for setting in SETTINGS}
    with pytest.raises(AssertionError) as caught:
        assert_identical_except_presentation(records, case["id"])
    assert "the field that moved first is 'safety.reasons" in str(caught.value)


def test_an_injected_reroute_of_the_seat_itself_is_caught(monkeypatch, roster) -> None:
    """The seat path: under "neither" a different candidate wins."""
    case = _first_case_with_a_seat(roster)
    original = router_module._select
    leak = {"setting": None}

    def leaky_select(scored, roster_, signals, claims=(), holds=(), mode_vetoes=frozenset()):
        winner, rule = original(scored, roster_, signals, claims, holds, mode_vetoes)
        if leak["setting"] == "neither" and winner is not None:
            others = [s for s in scored if s.eligible and s.agent_id != winner.agent_id]
            if others:
                return others[0], rule + "; leak: reseated by presentation"
        return winner, rule

    monkeypatch.setattr(router_module, "_select", leaky_select)
    records = {}
    for setting in SETTINGS:
        leak["setting"] = setting
        records[setting] = _record(case, roster, setting)
    with pytest.raises(AssertionError) as caught:
        assert_identical_except_presentation(records, case["id"])
    assert "the field that moved first is 'agent_id'" in str(caught.value)


def test_first_difference_names_the_first_leaf_that_moved() -> None:
    a = {"x": 1, "y": {"z": [1, 2]}, "explain": "a"}
    assert first_difference(a, dict(a)) is None
    assert first_difference(a, {"x": 1, "y": {"z": [1, 3]}, "explain": "a"}) == "y.z[1]"
    assert first_difference(a, {"x": 2, "y": {"z": [1, 3]}, "explain": "b"}) == "x"
    assert first_difference(a, {"x": 1, "y": {"z": [1, 2]}, "explain": "b"}) == "explain"
    assert first_difference(a, {"x": 1, "y": {"z": [1]}, "explain": "a"}) == "y.z[len 2 vs 1]"
