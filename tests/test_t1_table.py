"""Order T1: local receipts and settings use the unchanged labelled policy."""

from __future__ import annotations

import copy
import json
import threading
from pathlib import Path

import pytest
from test_talking_table import assert_nameless_gate, live, policy_cases, request

from apps.talking_table import server
from apps.talking_table.table_kit import decision_receipt, resources
from evals.run_fixtures import make_session
from secondsignal import route
from secondsignal_harness import AuditLog, CodexStore, FakeAdapter, Harness
from secondsignal_harness.adapters import AdapterError
from secondsignal_harness.prompt import LANGUAGE_STYLES, STYLE_VALUES

ROOT = Path(__file__).resolve().parents[1]
CASES = list(policy_cases())


@pytest.fixture
def app(tmp_path):
    instance = server.TableApp(data_dir=tmp_path / "table")
    try:
        yield instance
    finally:
        instance.close()


def selected(app, kind):
    for _, case in CASES:
        if case.get("prior_turns") or case.get("session"):
            continue
        record = route(case["text"], app.roster).to_dict()
        gate = record["safety"]["action"] == "HUMAN_ESCALATION"
        if ((kind == "card" and gate)
                or (kind == "grief" and record["held"] and not gate)
                or (kind == "dysregulated" and not gate and any(
                    r.startswith("acute dysregulation:") for r in record["safety"]["reasons"]))
                or (kind == "normal" and record["agent_id"] and not gate and not record["held"])
                or (kind == "house" and not gate and not record["agent_id"])):
            return case
    raise AssertionError("missing labelled fixture: " + kind)


def install(app, case, **kwargs):
    adapter = kwargs.pop("adapter", FakeAdapter())
    harness = Harness(app.roster, adapter, CodexStore(ROOT / "docs" / "codex"),
                      audit_log=AuditLog(app.audit_path), session=make_session(case), **kwargs)
    app.reset(harness)
    return harness


def test_t1_receipt_is_the_exact_display_object_and_has_no_raw_screen_evidence(app):
    """Every completed noncrisis branch stores the exact receipt used by both screen layers."""
    for kind in ("normal", "grief", "house", "dysregulated", "failure"):
        case = selected(app, "normal" if kind == "failure" else kind)
        options = {"adapter": FakeAdapter(script=(AdapterError("unavailable"),))} if kind == "failure" else {}
        install(app, case, **options)
        result = app.turn(case["text"])
        receipt = result["receipt"]
        stored = json.loads(app.receipt_path.read_text(encoding="utf-8").splitlines()[-1])
        assert receipt == stored == result["state"]["receipt"] == app.state["receipt"]
        assert receipt["seat"] == result["persona"]
        assert receipt["obligations"] == result["decision"]["obligations"]
        assert receipt["fold_receipt"] == result["decision"]["safety"]["screen_folds"]
        assert receipt["roster_hash"] == result["decision"]["roster_hash"]
        assert receipt["audit_verdicts"] == result["verdict"]
        assert receipt["release_rule"] == result["release_reason"]
        assert receipt["model_called"] is bool(result["adapter_calls"])
        serialized = json.dumps(receipt)
        assert case["text"] not in serialized
        for field in ("hit_spans", "masked_spans", "normalized_forms", "patterns_hash", "user_text", "signals"):
            assert field not in serialized
        if kind == "grief":
            assert receipt["holds"] and all(h["duration"] == "this turn" for h in receipt["holds"])
        if kind == "dysregulated":
            assert receipt["regulation"] == "Challenge voices were ineligible because this turn read as dysregulated."


def test_t1_card_receipt_and_polled_technical_record_are_nameless_and_not_stored(app):
    """A card publishes both nameless layers immediately and writes no crisis receipt."""
    case = selected(app, "card")
    result = app.turn(case["text"])
    assert not app.receipt_path.exists()
    assert result["state"]["card"] == result["card"]
    assert result["state"]["decision"] == result["decision"]
    assert result["receipt"]["gate_withheld"] and not result["receipt"]["model_called"]
    assert_nameless_gate(result, app.roster, result["card"])


def test_t1_receipt_projection_discards_untrusted_evidence_fields(app):
    """Receipt projection uses an explicit schema even when raw evidence contains planted data."""
    record = route(selected(app, "normal")["text"], app.roster).to_dict()
    record["safety"].update(hit_spans=[{"text": "RAW-STEM", "pattern": "RAW-PATTERN"}],
                            normalized_forms=["RAW-NORMALIZED"], reasons=["RAW-REASON"])
    candidate = next(c for c in record["ranked"] if c["agent_id"] != record["agent_id"])
    candidate.update(status="vetoed", rationale=["RAW-CLAUSE"])
    value = decision_receipt({"decision": record, "user_text": "RAW-MESSAGE"}, {})
    assert "RAW-" not in json.dumps(value)
    assert value["vetoes"][0]["reason"]


def test_t1_preferences_restore_independently_of_a_broken_credential_file(app):
    """Remembered style is not bound to a credential or dependent on decrypting one."""
    app.update_settings({"remember": True, "declared_preferences": {"verbosity": "short"}})
    app.settings_path.write_text("not valid settings", encoding="utf-8")
    restored = server.TableApp(data_dir=app.data_dir)
    try:
        assert restored.key == "" and restored.settings["remember"]
        assert restored.settings["declared_preferences"] == {"verbosity": "short"}
    finally:
        restored.close()


@pytest.mark.parametrize("operation", ["replace", "unlink", "settings_replace"])
def test_t1_two_settings_files_roll_back_together_on_io_failure(app, monkeypatch, operation):
    """A failed preferences save or forget cannot leave durable and active settings disagreeing."""
    app.update_settings({"remember": True, "declared_preferences": {"verbosity": "short"}})
    original_settings = copy.deepcopy(app.settings)
    files = {path: path.read_bytes() for path in (app.settings_path, app.preferences_path)}
    method = "replace" if operation == "settings_replace" else operation
    original = getattr(Path, method)

    def fail(path, *args, **kwargs):
        target = app.settings_path if operation == "settings_replace" else app.preferences_path
        if (method == "replace" and args and args[0] == target) or (method == "unlink" and path == target):
            raise OSError("fixture storage refusal")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, method, fail)
    with pytest.raises(server.InputError, match="previous settings remain"):
        app.update_settings({"remember": operation != "unlink",
                             "declared_preferences": {"verbosity": "detailed"}})
    assert app.settings == original_settings
    assert {path: path.read_bytes() for path in files} == files


@pytest.mark.parametrize("remember", [False, True])
def test_t1_declared_settings_remember_without_a_key_and_forget_when_disabled(app, remember):
    """Confirmed reply settings survive restart only under Remember and contain no credential fields."""
    declared = {key: values[-1] for key, values in STYLE_VALUES.items()}
    app.update_settings({"declared_preferences": declared, "humour_grief": True,
                         "language_style": "technical_english", "remember": remember})
    assert app.preferences_path.exists() is remember
    restored = server.TableApp(data_dir=app.data_dir)
    try:
        assert restored.settings["declared_preferences"] == (declared if remember else {})
        assert restored.settings["humour_grief"] is remember
        assert restored.settings["language_style"] == ("technical_english" if remember else "match")
        if remember:
            preferences = json.loads(app.preferences_path.read_text(encoding="utf-8"))
            assert set(preferences) == {"declared_preferences", "humour_grief", "language_style",
                                       "presentation", "chosen_names"}
            assert "declared_preferences" not in app.settings_path.read_text(encoding="utf-8")
            app.update_settings({"remember": False})
            assert not app.preferences_path.exists()
    finally:
        restored.close()


@pytest.mark.parametrize("proposed", [
    {"declared_preferences": {"seat": "willow"}}, {"declared_preferences": {"pace": "anything"}},
    {"declared_preferences": []}, {"humour_grief": "yes"}, {"language_style": "anything"},
])
def test_t1_settings_refuse_policy_keys_or_unconfirmed_free_text_atomically(app, proposed):
    """Only listed settings can be confirmed; invalid input cannot alter the live session or files."""
    before = copy.deepcopy(app.settings)
    session = app.harness.session
    with pytest.raises(server.InputError):
        app.update_settings(proposed)
    assert app.settings == before and app.harness.session is session
    assert not app.preferences_path.exists()


def test_t1_table_settings_reach_fake_adapter_without_becoming_policy_state(app):
    """The Table passes declared settings to the prompt and receipt without writing policy preferences."""
    (app.data_dir / "operator.token").write_text("a" * 64)  # Order T3, 2026-10-07: enabling without token -> local token required.
    app.update_settings({"declared_preferences": {"pace": "one_step"}, "operator_circle": True,
                         "humour_grief": True, "language_style": "technical_english"})
    result = app.turn(selected(app, "normal")["text"])
    assert "Declared preferences:" in app.harness.adapter.calls[0]["system"]
    assert result["receipt"]["declared_preferences"] == {"pace": "one_step"}
    assert result["receipt"]["presentation_instructions"] == {
        "language_style": "technical_english", "humour_grief_opt_in": True}
    assert app.harness.session.preferences == {}
    assert result["effort_contract"] is (result["kind"] == "reply")


def test_t1_full_model_slots_report_no_call_or_applied_instructions(app):
    """A queued-slot refusal cannot claim a model was called or preferences reached a prompt."""
    app.update_settings({"declared_preferences": {"pace": "one_step"}, "humour_grief": True})
    for _ in range(4):
        assert app.model_slots.acquire(blocking=False)
    try:
        result = app.turn(selected(app, "normal")["text"])
        assert result["kind"] == "withheld" and not app.harness.adapter.calls
        assert not result["receipt"]["model_called"]
        assert result["receipt"]["declared_preferences"] == {}
        assert result["receipt"]["presentation_instructions"] == {}
    finally:
        for _ in range(4):
            app.model_slots.release()


def test_t1_all_view_and_presentation_inputs_keep_labelled_policy_and_house_lines(app):
    """Every new Table setting and either client view preserve each selected labelled safety branch."""
    variants = [{"declared_preferences": {key: value}}
                for key, values in STYLE_VALUES.items() for value in values]
    variants += [{"humour_grief": value} for value in (False, True)]
    variants += [{"language_style": value} for value in LANGUAGE_STYLES]
    variants += [{"presentation": value} for value in server.PRESENTATIONS]
    for kind in ("normal", "grief", "dysregulated", "card", "house"):
        case = selected(app, kind)
        baseline = Harness(app.roster, FakeAdapter(), CodexStore(ROOT / "docs" / "codex"),
                           session=make_session(case)).speak(case["text"])
        for settings in variants:
            app.reset()
            app.update_settings(settings)
            result = app.turn(case["text"])
            assert result["action"] == baseline.action
            assert result["persona"] == baseline.agent_id
            if result["kind"] == "card":
                assert result["card"] == baseline.text
            else:
                assert result["decision"] == baseline.decision
                assert app.harness.turns[-1].house_lines == baseline.house_lines
    case = selected(app, "normal")
    with live(app) as listener:
        outcomes = []
        for view in (False, True):
            app.reset()
            outcomes.append(request(listener, "/api/turn", {"text": case["text"], "low_demand": view})[1])
        assert outcomes[0]["decision"] == outcomes[1]["decision"]


def test_t1_stalled_model_is_superseded_by_a_pollable_card(app):
    """A stalled FakeAdapter cannot delay or later replace the card, either layer, or the latch."""
    entered, release = threading.Event(), threading.Event()
    results = []

    def stall(system, messages):
        entered.set()
        release.wait(5)
        return "Late text."

    case = selected(app, "normal")
    install(app, case, adapter=FakeAdapter(script=stall), operator_circle=True)
    worker = threading.Thread(target=lambda: results.append(app.turn(case["text"])), daemon=True)
    try:
        worker.start()
        assert entered.wait(2)
        card = app.turn(selected(app, "card")["text"])
        assert card["kind"] == "card" and not release.is_set()
        assert app.state["card"] == card["card"]
        state = copy.deepcopy(app.state)
        release.set()
        worker.join(2)
        assert not worker.is_alive() and results[0]["superseded"]
        assert app.state == state and app.harness.session.escalated_last_turn
        saved = [json.loads(line) for line in app.receipt_path.read_text(encoding="utf-8").splitlines()]
        assert len(saved) == 1 and saved[0]["release_rule"] == "superseded"
        assert saved[0]["seat"] and saved[0]["model_called"]
        assert saved[0]["audit_verdicts"] is None and saved[0]["audit_row_id"] is None
        assert "Late text." not in json.dumps(saved)
    finally:
        release.set()
        worker.join(2)


def test_t1_followup_pending_after_card_does_not_publish_a_new_card_revision(app):
    """Polling while a follow-up waits can distinguish the old card from a new escalation."""
    entered, release = threading.Event(), threading.Event()

    def stall(system, messages):
        entered.set()
        release.wait(5)
        return "Okay."

    card = app.turn(selected(app, "card")["text"])
    app.harness.adapter = FakeAdapter(script=stall)
    worker = threading.Thread(target=lambda: app.turn(selected(app, "normal")["text"]), daemon=True)
    try:
        worker.start()
        assert entered.wait(2)
        assert app.state["revision"] > app.state["card_revision"] == card["state"]["revision"]
        assert app.state["card"] == card["card"]
    finally:
        release.set()
        worker.join(2)


def test_t1_superseded_receipt_disk_wait_cannot_hold_up_a_card(app, monkeypatch):
    """Even a stalled superseded-receipt write leaves the crisis path and state lock available."""
    entered, release = threading.Event(), threading.Event()
    writing, finish_write = threading.Event(), threading.Event()
    original = app.receipts.append

    def stall(system, messages):
        entered.set()
        release.wait(5)
        return "Okay."

    def slow_receipt(row):
        writing.set()
        finish_write.wait(5)
        return original(row)

    monkeypatch.setattr(app.receipts, "append", slow_receipt)
    app.harness.adapter = FakeAdapter(script=stall)
    worker = threading.Thread(target=lambda: app.turn(selected(app, "normal")["text"]), daemon=True)
    try:
        worker.start()
        assert entered.wait(2)
        card_text = selected(app, "card")["text"]
        assert app.turn(card_text)["kind"] == "card"
        assert writing.wait(2) and not finish_write.is_set()
        with live(app) as listener:
            assert request(listener, "/api/turn", {"text": card_text}, timeout=0.5)[1]["kind"] == "card"
            assert request(listener, "/api/state", timeout=0.5)[1]["state"] == "card"
    finally:
        finish_write.set()
        release.set()
        worker.join(2)


def test_t1_normal_receipt_disk_wait_cannot_hold_up_a_card(app, monkeypatch):
    """A completed model's slow receipt write never owns the lock required by a new card."""
    writing, release = threading.Event(), threading.Event()
    original = app.receipts.append
    results = []

    def slow_receipt(row):
        writing.set()
        release.wait(5)
        return original(row)

    monkeypatch.setattr(app.receipts, "append", slow_receipt)
    normal = selected(app, "normal")["text"]
    worker = threading.Thread(target=lambda: results.append(app.turn(normal)), daemon=True)
    try:
        worker.start()
        assert writing.wait(2)
        with live(app) as listener:
            card = request(listener, "/api/turn", {"text": selected(app, "card")["text"]}, timeout=0.5)[1]
            assert card["kind"] == "card" and not release.is_set()
            assert request(listener, "/api/state", timeout=0.5)[1]["state"] == "card"
        release.set()
        worker.join(2)
        assert results[0]["superseded"] and app.state["state"] == "card"
    finally:
        release.set()
        worker.join(2)


def test_t1_preview_text_is_verbatim_for_every_character_and_presentation(app):
    """All 28 text previews quote a shipped codex and absent voice slots expose no voice control."""
    previews = app.config()["presentation_previews"]
    assert set(previews) == server.PRESENTATIONS
    for personas in previews.values():
        assert set(personas) == set(app.roster)
        for sample in personas.values():
            assert "> " + sample["text"] in (ROOT / sample["source"]).read_text(encoding="utf-8")
            assert not sample["voice_available"] and "speech_token" not in sample


def test_t1_preview_voice_uses_exact_slot_single_use_and_crisis_revocation(app):
    """Configured preview audio uses the existing capability path and dies on a crisis card."""
    calls = []
    app.speech_transport = lambda voice, text, key: (calls.append((voice, text)) or ("audio/mpeg", b"ID3fixture"))
    app.update_settings({"voice_key": "test-preview-secret-not-real", "voice_enabled": True,
                         "voice_slots": {"willow": {"women": "fixture_willow_women"}}})
    preview = app.preview({"persona": "willow", "presentation": "women"})
    assert app.state["state"] == "idle"
    assert app.voice({"speech_token": preview["speech_token"]}) == b"ID3fixture"
    assert calls == [("fixture_willow_women", preview["text"])]
    with pytest.raises(server.InputError):
        app.voice({"speech_token": preview["speech_token"]})
    preview = app.preview({"persona": "willow", "presentation": "women"})
    app.turn(selected(app, "card")["text"])
    with pytest.raises(server.InputError):
        app.voice({"speech_token": preview["speech_token"]})
    assert not app.config()["presentation_previews"]["women"]["willow"]["voice_available"]


def test_t1_preview_readiness_survives_polling_until_normal_revocation(app):
    """A preview for an unsaved presentation stays playable across polls and is revoked by the next turn."""
    app.speech_transport = lambda voice, text, key: ("audio/mpeg", b"ID3fixture")
    app.update_settings({"voice_key": "test-preview-poll-secret-not-real", "voice_enabled": True,
                         "voice_slots": {"willow": {"women": "fixture_willow_women"}}})
    assert app.settings["presentation"] == "as_written" and not app.state["voice_ready"]
    with live(app) as listener:
        preview = request(listener, "/api/presentation/preview", {"persona": "willow", "presentation": "women"})[1]
        assert request(listener, "/api/state")[1]["voice_ready"]
        assert app.voice({"speech_token": preview["speech_token"]}) == b"ID3fixture"
        assert request(listener, "/api/state")[1]["voice_ready"]
        assert request(listener, "/api/config")[1]["settings"]["voice_ready"]
        app.turn(selected(app, "normal")["text"])
        assert not request(listener, "/api/state")[1]["voice_ready"]
        assert app.preview_snapshot is None


def test_t1_resources_actions_cover_declared_country_and_default_without_a_turn(app):
    """Resource addresses are usable links or call actions and opening the control mutates nothing."""
    for locale in ("", *server.LOCALES):
        app.update_settings({"locale": locale})
        before = copy.deepcopy(app.harness.session.__dict__)
        with live(app) as listener:
            actual = request(listener, "/api/resources")[1]
        assert actual == resources(locale or None) == app.config()["resource"]
        assert actual["actions"] and all(a["url"].startswith(("https://", "tel:", "sms:")) for a in actual["actions"])
        assert app.harness.session.__dict__ == before and not app.harness.turns


def test_t1_resources_control_does_not_repeat_spoken_aftermath_resource(app):
    """Repeated Resources reads leave the existing spoken-once aftermath sequence unchanged."""
    card = selected(app, "card")["text"]
    normal = selected(app, "normal")["text"]
    baseline = Harness(app.roster, FakeAdapter(), CodexStore(ROOT / "docs" / "codex"))
    for text in (card, normal, normal):
        before = copy.deepcopy(app.harness.session.__dict__)
        for _ in range(3):
            app.config()["resource"]
        assert app.harness.session.__dict__ == before
        expected, actual = baseline.speak(text), app.turn(text)
        assert app.harness.turns[-1].house_lines == expected.house_lines
        assert actual["action"] == expected.action
        assert app.harness.session.__dict__ == baseline.session.__dict__
