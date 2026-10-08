"""Order T2: declared Table controls remain outside the policy decision."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from test_t1_table import install, selected
from test_talking_table import assert_nameless_gate, live, policy_cases, request

from apps.talking_table import server
from evals.run_fixtures import make_session
from secondsignal import route
from secondsignal_harness import CodexStore, FakeAdapter, Harness
from secondsignal_harness.lines import HARNESS_LINES_EN, ROOM_LINES
from secondsignal_harness.table_extras import eligible_agents

ROOT = Path(__file__).resolve().parents[1]
ROSTER_IDS = ("cody", "ellis", "nikki", "rowan", "seren", "vandal", "willow")


@pytest.fixture
def app(tmp_path):
    instance = server.TableApp(data_dir=tmp_path / "t2-table")
    try:
        yield instance
    finally:
        instance.close()


def baseline(app, case):
    harness = Harness(app.roster, FakeAdapter(), CodexStore(ROOT / "docs" / "codex"),
                      session=make_session(case))
    return harness.speak(case["text"])


def offered_case(app):
    for _, case in policy_cases():
        if case.get("prior_turns") or case.get("session"):
            continue
        record = route(case["text"], app.roster).to_dict()
        if record["agent_id"] and not record["held"] and eligible_agents(record):
            return case
    raise AssertionError("no labelled case with an eligible other chair")


SETTING_VARIANTS = ([{"room": value} for value in ("", *ROOM_LINES)]
                    + [{"house_name": ""}, {"house_name": '<My & "table">'}]
                    + [{"presentation_overrides": {persona: value}}
                       for persona in ROSTER_IDS for value in sorted(server.PRESENTATIONS)]
                    + [{"presentation_overrides": {}}])


@pytest.mark.parametrize("settings", SETTING_VARIANTS)
def test_t2_each_setting_preserves_all_labelled_policy_branches(app, settings):
    """Every room, table name and character override preserves seats, holds, cards and policy lines."""
    for kind in ("normal", "grief", "dysregulated", "house", "card"):
        case = selected(app, kind)
        expected = baseline(app, case)
        app.reset()
        app.update_settings(settings)
        actual = app.turn(case["text"])
        assert app.harness.turns[-1].decision == expected.decision
        assert app.harness.turns[-1].house_lines == expected.house_lines
        assert actual["persona"] == expected.agent_id
        if kind == "card":
            assert actual["card"] == expected.text
            assert not app.harness.adapter.calls


@pytest.mark.parametrize("tag", sorted(server.DRAFT_TAGS))
def test_t2_each_draft_tag_is_one_turn_only_and_cannot_route(app, tag):
    """Each tag changes only the seated prompt and leaves every labelled policy branch unchanged."""
    for kind in ("normal", "grief", "dysregulated", "house", "card"):
        case = selected(app, kind)
        expected = baseline(app, case)
        app.reset()
        actual = app.turn(case["text"], tag=tag)
        assert app.harness.turns[-1].decision == expected.decision
        assert app.harness.turns[-1].house_lines == expected.house_lines
        if app.harness.adapter.calls:
            prompt = app.harness.adapter.calls[-1]["system"]
            assert (HARNESS_LINES_EN["draft_tag_line"].format(tag=tag) in prompt) is bool(tag)
            assert app.harness.adapter.calls[-1]["messages"][-1]["content"] == case["text"]
        if kind == "card":
            assert "tag" not in actual and not app.harness.adapter.calls
    app.reset()
    text = selected(app, "normal")["text"]
    app.turn(text, tag=tag)
    next_turn = app.turn(text)
    assert next_turn["tag"] == ""
    assert "The person tagged this as a" not in app.harness.adapter.calls[-1]["system"]


@pytest.mark.parametrize("remember", [False, True])
def test_t2_remembered_extras_are_independent_of_credentials(app, remember):
    """Rooms, table names and overrides restore only under Remember in the separate preference file."""
    extras = {"house_name": "The little table", "room": "studio",
              "presentation_overrides": {"willow": "men"}}
    app.update_settings({**extras, "remember": remember})
    restored = server.TableApp(data_dir=app.data_dir)
    try:
        for key, value in extras.items():
            assert restored.settings[key] == (value if remember else {} if key == "presentation_overrides" else "")
        assert not restored.key and not restored.voice_key and not restored.lights_key
        if remember:
            preferences = json.loads(app.preferences_path.read_text(encoding="utf-8"))
            assert all(preferences[key] == value for key, value in extras.items())
            credentials = json.loads(app.settings_path.read_text(encoding="utf-8"))
            assert not set(extras).intersection(credentials["settings"])
            app.update_settings({"remember": False})
            assert not app.preferences_path.exists()
    finally:
        restored.close()


def test_t2_house_name_stays_out_of_prompt_receipt_and_audit(app):
    """A personal table heading is display text and never reaches the adapter or durable conversation rows."""
    title = '<A & "personal" table>'
    app.update_settings({"house_name": title})
    assert app.config()["state"]["house_name"] == title
    app.turn(selected(app, "normal")["text"])
    assert title not in json.dumps(app.harness.adapter.calls)
    assert title not in app.audit_path.read_text(encoding="utf-8")
    assert title not in app.receipt_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("invalid", [
    {"house_name": "x" * 41}, {"house_name": "two\nlines"}, {"house_name": "two\u2028lines"},
    {"house_name": []}, {"room": "bedroom"}, {"room": []},
    {"presentation_overrides": {"unknown": "women"}},
    {"presentation_overrides": {"willow": "anything"}},
    {"presentation_overrides": []},
])
def test_t2_invalid_settings_are_atomic(app, invalid):
    """Unlisted or multiline controls cannot change live or remembered settings."""
    before = copy.deepcopy(app.settings)
    with pytest.raises(server.InputError):
        app.update_settings(invalid)
    assert app.settings == before and not app.preferences_path.exists()


def test_t2_biographies_use_only_profile_fields_and_override_names(app):
    """All seven biography contracts exactly expose loaded profile fields and presentation names."""
    app.update_settings({"presentation": "women", "presentation_overrides": {"willow": "men"}})
    for row in app.config()["roster"]:
        profile = app.roster[row["id"]]
        assert row["domains"] == sorted(profile.domains)
        assert row["modes"] == sorted(profile.modes)
        assert row["contraindications"] == sorted(profile.contraindications)
        assert row["handoffs"] == profile.handoffs
        assert app._name_for(row["id"]) == profile.name_for(app._presentation_for(row["id"]))[0]
    case = next(case for _, case in policy_cases()
                if not case.get("prior_turns") and not case.get("session")
                and route(case["text"], app.roster).agent_id == "willow")
    result = app.turn(case["text"])
    assert result["receipt"]["display_names"]["willow"] == "Will"
    assert app.harness.presentation["willow"] == "men"
    assert "name in this presentation: Will." in app.harness.adapter.calls[-1]["system"]


def test_t2_object_is_screened_alone_without_mutating_policy_or_storage(app, monkeypatch):
    """The public crisis screen checks the object alone and accepted text enters only the seated prompt."""
    screened = []
    original = server.crisis_screen

    def observe(text):
        screened.append(text)
        return original(text)

    monkeypatch.setattr(server, "crisis_screen", observe)
    object_text = "A smooth blue pebble"
    before = copy.deepcopy(app.harness.session.__dict__)
    app.set_object(object_text)
    assert screened == [object_text] and app.harness.session.__dict__ == before
    case = selected(app, "normal")
    expected = baseline(app, case)
    actual = app.turn(case["text"])
    assert actual["decision"] == expected.decision
    assert "Object on the table: " + object_text in app.harness.adapter.calls[-1]["system"]
    assert object_text not in json.dumps(actual["receipt"])
    assert object_text not in app.audit_path.read_text(encoding="utf-8")
    assert object_text not in app.receipt_path.read_text(encoding="utf-8")
    assert not app.settings_path.exists()
    app.reset()
    assert app.object_text == app.state["object_text"] == ""


def test_t2_alarming_object_uses_labelled_crisis_fixture_and_clears_field(app):
    """An existing labelled crisis is refused as an object without a turn, latch or model call."""
    app.set_object("A smooth blue pebble")
    before = copy.deepcopy(app.harness.session.__dict__)
    result = app.set_object(selected(app, "card")["text"])
    assert result["object_text"] == ""
    assert result["object_notice"] == HARNESS_LINES_EN["object_refused"]
    assert app.harness.session.__dict__ == before and not app.harness.adapter.calls
    assert not app.audit_path.exists() and not app.receipt_path.exists()


def test_t2_card_shows_only_aftermath_and_never_calls_fake_adapter(app):
    """All extras disappear on a card while its nameless first layer adds the exact aftermath line."""
    app.update_settings({"house_name": "My table", "room": "workshop",
                         "presentation_overrides": {"willow": "men"}})
    app.set_object("A smooth blue pebble")
    app.deferred_ask = "vandal"
    result = app.turn(selected(app, "card")["text"], tag="letter")
    assert result["receipt"]["aftermath"] == HARNESS_LINES_EN["card_aftermath"]
    assert not app.harness.adapter.calls and result["adapter_calls"] == 0
    for field in ("handback", "assist_offer", "second_opinions", "deferred_ask", "object_text",
                  "house_name", "presentation_overrides", "tag", "page_url", "second_view"):
        assert field not in result and field not in result["state"]
    assert_nameless_gate(result, app.roster, result["card"])
    assert not app.receipt_path.exists()


@pytest.mark.parametrize("metadata", [
    {"tag": []}, {"tag": "anything"}, {"action": "ask", "target": {}},
    {"action": [], "target": "vandal"}, {"action": "handback", "target": "vandal"},
])
def test_t2_malformed_control_metadata_never_preempts_labelled_crisis(app, metadata):
    """Raw message crisis routing wins even over invalid or unavailable control metadata."""
    case = selected(app, "card")
    result = app.turn(case["text"], **metadata)
    assert result["kind"] == "card" and not app.harness.adapter.calls
    assert app.harness.turns[-1].decision == baseline(app, case).decision


def test_t2_handback_is_declared_session_state_not_message_inference(app):
    """Only explicit ask controls defer a chair; raw message text never creates that memory."""
    text = f"Could I talk to {app._name_for('vandal')}?"
    app.turn(text)
    assert app.deferred_ask is None
    app.reset()
    result = app.turn(text, action="ask", target="vandal")
    assert result["persona"] != "vandal"
    assert app.deferred_ask == result["deferred_ask"] == "vandal"
    assert result["handback"] is None
    assert "deferred_ask" not in app.audit_path.read_text(encoding="utf-8")
    assert "deferred_ask" not in app.receipt_path.read_text(encoding="utf-8")
    app.reset()
    assert app.deferred_ask is None and app.state["handback"] is None


def test_t2_handback_offer_follows_current_record_and_tap_routes_phone_text(app):
    """A saved ask is offered only when eligible later, and a tap sends exact phone text then clears it."""
    case = offered_case(app)
    record = baseline(app, case).decision
    target = eligible_agents(record)[0]
    app.deferred_ask = target
    expected = baseline(app, case)
    result = app.turn(case["text"])
    assert result["decision"] == expected.decision
    offer = result["handback"]
    assert offer["persona"] == target
    assert offer["text"] == f"Could I talk to {app._name_for(target)}?"
    assert offer["label"] == HARNESS_LINES_EN["handback_offer"].format(Asked=app._name_for(target))
    next_turn = app.turn(offer["text"], action="handback", target=target)
    assert app.deferred_ask is None and next_turn["handback"] is None
    assert app.harness.transcript[-2]["content"] == offer["text"]
    app.reset()
    app.deferred_ask = "vandal"
    held = app.turn(selected(app, "grief")["text"])
    assert "vandal" not in eligible_agents(held["decision"])
    assert held["handback"] is None


def test_t2_seating_saved_character_clears_handback(app):
    """The saved chair marker vanishes as soon as the unchanged policy seats that character."""
    case = selected(app, "normal")
    app.deferred_ask = baseline(app, case).agent_id
    app.turn(case["text"])
    assert app.deferred_ask is None and app.state["handback"] is None


def test_t2_held_turn_shares_two_option_budget_across_house_offers(app):
    """On a held record the handback, assist and second-view controls together offer at most two options."""
    case = next(case for _, case in policy_cases()
                if not case.get("prior_turns") and not case.get("session")
                and (record := route(case["text"], app.roster).to_dict())["held"]
                and eligible_agents(record))
    record = baseline(app, case).decision
    before = copy.deepcopy(record)
    app._last_record = record
    app._last_released = True
    app._handback_ready = True
    app.deferred_ask = eligible_agents(record)[0]
    controls = app._extras_state()
    count = bool(controls["handback"]) + bool(controls["assist_offer"]) + len(controls["second_opinions"])
    assert count <= 2 and record == before


def test_t2_assist_slip_is_record_only_and_cannot_change_prompt(app):
    """An assist slip exists exactly when the record names an assist and adds nothing to the prompt."""
    case = next(case for _, case in policy_cases()
                if not case.get("prior_turns") and route(
                    case["text"], app.roster, session=make_session(case)).assist_agent_id)
    direct = Harness(app.roster, FakeAdapter(), CodexStore(ROOT / "docs" / "codex"),
                     session=make_session(case))
    expected = direct.speak(case["text"])
    installed = install(app, case)
    result = app.turn(case["text"])
    assert result["decision"] == expected.decision
    assert result["assist_offer"]["persona"] == expected.decision["assist_agent_id"]
    assert installed.adapter.calls == direct.adapter.calls
    assert len(installed.adapter.calls) == 1
    normal = selected(app, "normal")
    app.reset()
    plain = app.turn(normal["text"])
    assert (plain["assist_offer"] is not None) is bool(plain["decision"]["assist_agent_id"])


def test_t2_second_opinion_is_eligible_capped_at_three_and_exact_new_turn(app):
    """Second-view shortcuts contain only other eligible characters and route their exact text once."""
    (app.data_dir / "operator.token").write_text("a" * 64)  # Order T3, 2026-10-07: enabling without token -> local token required.
    app.update_settings({"operator_circle": True})
    result = app.turn(offered_case(app)["text"])
    assert result["kind"] == "reply"
    choices = result["second_opinions"]
    assert [choice["persona"] for choice in choices] == list(eligible_agents(result["decision"]))[:3]
    assert 0 < len(choices) <= 3
    choice = choices[0]
    assert choice["text"] == f"What would {app._name_for(choice['persona'])} add?"
    next_turn = app.turn(choice["text"], action="second_view", target=choice["persona"])
    assert next_turn["second_view"] is (next_turn["kind"] == "reply")
    assert app.harness.transcript[-2]["content"] == choice["text"]
    assert next_turn["decision"]["agent_id"] == next_turn["persona"]


def test_t2_earlier_reply_shortcut_keeps_its_record_and_name_snapshot(app):
    """An earlier released reply's shortcut survives later turns and names, then expires on reset."""
    (app.data_dir / "operator.token").write_text("a" * 64)  # Order T3, 2026-10-07: enabling without token -> local token required.
    app.update_settings({"operator_circle": True, "presentation": "women"})
    result = app.turn(offered_case(app)["text"])
    choice = result["second_opinions"][0]
    app.turn(selected(app, "normal")["text"])
    app.update_settings({"presentation": "men"})
    metadata = {key: choice[key] for key in ("source_revision", "source_session")}
    returned = app.turn(choice["text"], action="second_view", target=choice["persona"], **metadata)
    assert returned["second_view"] is (returned["kind"] == "reply")
    assert app.harness.transcript[-2]["content"] == choice["text"]
    app.reset()
    with pytest.raises(server.InputError):
        app.turn(choice["text"], action="second_view", target=choice["persona"], **metadata)


def test_t2_object_http_validates_single_line_and_never_records_a_turn(app):
    """The explicit object endpoint accepts a bounded line, refuses invalid values and does not route."""
    with live(app) as listener:
        saved = request(listener, "/api/object", {"text": "A paper boat"})
        assert saved[0] == 200 and saved[1]["object_text"] == "A paper boat"
        for text in ("x" * 61, "two\nlines", None):
            assert request(listener, "/api/object", {"text": text})[0] == 400
        assert app.object_text == "A paper boat" and app.harness.session.turn_count == 0
        assert not app.audit_path.exists() and not app.harness.adapter.calls


def test_t2_made_page_is_only_released_server_text_and_expires_with_sitting(app):
    """Printable pages serve escaped released text and its original name, never supplied or withheld text."""
    case = selected(app, "normal")
    install(app, case, adapter=FakeAdapter(script=('A & B\nSecond line.',)), operator_circle=True)
    result = app.turn(case["text"])
    with live(app) as listener:
        status, page, _ = request(listener, result["page_url"])
        assert status == 200
        assert b"A &amp; B\nSecond line." in page
        assert result["display_name"].encode() in page
        assert HARNESS_LINES_EN["made_page_footer"].encode() in page
        assert case["text"].encode() not in page
        assert request(listener, result["page_url"], {"text": "Never released"})[0] == 404
        app.update_settings({"presentation": "men"})
        assert request(listener, result["page_url"])[1] == page
        app.reset()
        assert request(listener, result["page_url"])[0] == 404
        withheld = app.turn(case["text"])
        assert withheld["kind"] == "withheld" and "page_url" not in withheld


def test_t2_made_page_requires_pairing_and_card_hides_old_pages(app, monkeypatch):
    """A made page uses the existing origin and pairing boundary and cannot open over an active card."""
    (app.data_dir / "operator.token").write_text("a" * 64)  # Order T3, 2026-10-07: enabling without token -> local token required.
    app.update_settings({"operator_circle": True})
    reply = app.turn(selected(app, "normal")["text"])
    with live(app) as listener:
        monkeypatch.setattr(server.Handler, "is_local", property(lambda self: False))
        assert request(listener, reply["page_url"])[0] == 403
        monkeypatch.undo()
        assert request(listener, reply["page_url"])[0] == 200
        app.turn(selected(app, "card")["text"])
        assert request(listener, reply["page_url"])[0] == 404


def test_t2_shutter_transport_has_no_policy_input(app):
    """A forged shutter field is ignored by the HTTP endpoint and leaves the full decision unchanged."""
    case = selected(app, "normal")
    with live(app) as listener:
        records = []
        for enabled in (False, True):
            app.reset()
            result = request(listener, "/api/turn", {"text": case["text"], "shutter": enabled})[1]
            records.append(result["decision"])
        assert records[0] == records[1]


@pytest.mark.parametrize("key,values", [
    ("handback_offer", {"Asked": "Will"}), ("assist_offer", {"Assist": "Nik"}),
    ("made_page_footer", {}), ("object_refused", {}), ("card_aftermath", {}),
    ("room_note", {}), ("ask_acknowledgement", {
        "Asked": "Nik", "Seated": "Will", "reason": "loss is Will's ground"}),
])
def test_t2_fixed_house_copy_cannot_be_released_as_model_text(app, key, values):
    """Every new fixed house sentence stays protected from character impersonation before storage."""
    line = HARNESS_LINES_EN[key].format(**values)
    case = selected(app, "normal")
    install(app, case, adapter=FakeAdapter(script=(line,)), operator_circle=True)
    result = app.turn(case["text"])
    assert result["kind"] == "withheld" and result["verdict"] is None
    assert line not in app.audit_path.read_text(encoding="utf-8")
