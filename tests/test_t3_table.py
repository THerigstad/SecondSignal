"""Order T3: offline honesty, shared sitting, local review and unchanged policy."""

from __future__ import annotations

import copy
import http.client
import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from test_t1_table import CASES, install, selected
from test_talking_table import assert_nameless_gate, live, request

from apps.talking_table import server, t3
from secondsignal import __version__, route
from secondsignal.safety import SessionState
from secondsignal_harness import AuditLog, FakeAdapter

ROOT = Path(__file__).resolve().parents[1]
TEXT = "Start with one small task tomorrow."


@pytest.fixture
def app(tmp_path, monkeypatch):
    def no_vendor(*args, **kwargs):
        raise AssertionError("An unmocked vendor call was attempted.")
    monkeypatch.setattr(server.urllib.request, "build_opener", no_vendor)
    instance = server.TableApp(tmp_path / "t3-data")
    try:
        yield instance
    finally:
        instance.close()


def normal(app, released=False):
    case = selected(app, "normal")
    install(app, case, adapter=FakeAdapter(script=(TEXT,)), operator_circle=released)
    return case


def consent(app):
    terms = app.terms_summary()
    return {"vendor": terms["vendor"], "revision": terms["revision"], "accepted": True, "attested": True}


def paired(app, monkeypatch):
    app.set_network(True)
    token = app.pair(app.pairing_code, "test-phone")
    monkeypatch.setattr(server.Handler, "is_local", property(lambda self: False))
    return app.phone_server, {"Cookie": f"{server.COOKIE}={token}"}


def test_t3_limitations_are_generated_from_public_sources_and_register(app):
    """The sheet follows package identity, manifest counts, pack status and ADR status."""
    sheet = app.honesty()["limitations"]
    public = json.loads((ROOT / "evals/public-numbers.json").read_text(encoding="utf-8"))
    register = json.loads((ROOT / "docs/adr/index.json").read_text(encoding="utf-8"))
    record = next(row for row in register["records"] if row["number"] == "0029")
    assert sheet["version"] == __version__
    for key in ("documented_gaps", "recorded_dissents"):
        assert sheet["facts"][key] == public[key]
        assert str(public[key]) in " ".join(sheet["lines"])
    assert sheet["facts"]["harness_decision"] == record["decision"]
    assert sheet["facts"]["harness_implementation"] == record["implementation"]
    for pack in ("en", "es-419"):
        saved = json.loads((ROOT / f"src/secondsignal/packs/{pack}.json").read_text(encoding="utf-8"))
        assert sheet["facts"]["lexicon"][pack] == saved["status"]


def test_t3_honesty_names_every_durable_file_and_shared_session(app):
    """Composer and settings explain the actual local files and shared sitting lifetime."""
    config = app.config()
    copy_text = " ".join(config["honesty"]["session_lines"]) + config["storage"]
    for name in ("audit.jsonl", "receipts.jsonl", "review_queue.jsonl", "settings.json",
                 "preferences.json", "terms.json", "operator.token"):
        assert name in copy_text
    assert "server window closes" in copy_text and "either paired screen" in copy_text
    assert config["honesty"]["network_warning"] == t3.NETWORK_WARNING


@pytest.mark.parametrize("family", sorted(server.FAMILIES - {"fake"}))
def test_t3_live_terms_gate_precedes_model_and_never_commits_rejected_policy(app, family):
    """Every live family refuses before a model call and leaves its rejected session untouched."""
    case = normal(app)
    app.settings.update(adapter=family, url="https://fixture.example/chat")
    before = copy.deepcopy(app.harness.session.__dict__)
    with pytest.raises(server.InputError, match="vendor terms"):
        app.turn(case["text"])
    assert app.harness.session.__dict__ == before
    assert not app.harness.adapter.calls and not app.audit_path.exists()
    app.confirm_terms(consent(app))
    result = app.turn(case["text"])
    assert result["decision"] == route(case["text"], app.roster, session=SessionState()).to_dict()
    assert app.harness.adapter.calls


def test_t3_fake_never_asks_and_unconfirmed_live_crisis_still_wins(app):
    """The pretend family has no gate and an unconfirmed live setting cannot delay a card."""
    case = normal(app)
    assert app.terms_summary() is None
    assert app.turn(case["text"])["kind"] == "withheld"
    crisis = selected(app, "card")
    install(app, crisis)
    app.settings["adapter"] = "openai"
    result = app.turn(crisis["text"])
    assert result["kind"] == "card" and result["adapter_calls"] == 0


@pytest.mark.parametrize("missing", ["accepted", "attested", "vendor", "revision"])
def test_t3_consent_requires_current_vendor_summary_and_own_attestation(app, missing):
    """A missing checkbox or stale identity cannot stand in for explicit consent."""
    app.settings["adapter"] = "openai"
    payload = consent(app)
    payload.pop(missing)
    with pytest.raises(server.InputError):
        app.confirm_terms(payload)
    assert not app.confirmations


@pytest.mark.parametrize("remember", [False, True])
def test_t3_terms_remember_is_separate_from_keys_and_resets_per_sitting(app, remember):
    """Remember alone controls durable vendor consent, with no credential beside it."""
    app.update_settings({"remember": remember})
    app.settings["adapter"] = "openai"
    app.confirm_terms(consent(app))
    assert app.terms_path.exists() is remember
    assert not app.settings_path.exists() or "openai" not in app.settings_path.read_text()
    # Keep all adapter use fake; only the declared family exercises the gate.
    app.reset(app.harness)
    assert app.terms_summary()["confirmed"] is remember
    if remember:
        content = json.loads(app.terms_path.read_text())
        assert set(content) == {"openai"}
        app.update_settings({"remember": False})
        assert not app.terms_path.exists()


def test_t3_compatible_hosts_have_separate_vendor_confirmations(app):
    """Consent for one compatible vendor cannot authorize a different host."""
    app.settings.update(adapter="compatible", url="https://first.example/chat")
    app.confirm_terms(consent(app))
    app.settings["url"] = "https://second.example/chat"
    assert app.terms_summary()["confirmed"] is False


def test_t3_live_crisis_never_reads_the_terms_gate(app, monkeypatch):
    """An unavailable optional terms file cannot delay or replace a live-family crisis card."""
    app.settings["adapter"] = "openai"
    with monkeypatch.context() as patch:
        patch.setattr(app, "terms_summary", lambda: pytest.fail("Crisis consulted vendor terms"))
        result = app.turn(selected(app, "card")["text"])
    assert result["kind"] == "card" and not app.harness.adapter.calls


@pytest.mark.parametrize("overlap", ["card", "HUMAN_ESCALATION", "card_text"])
def test_t3_crisis_snapshot_preserves_authoritative_copy_even_if_a_key_overlaps(app, overlap):
    """Stored credentials cannot rewrite the card or its protocol fields on reload and polling."""
    case = selected(app, "card")
    baseline = app.turn(case["text"])
    app.reset()
    app.update_settings({"key": baseline["card"] if overlap == "card_text" else overlap})
    result = app.turn(case["text"])
    with live(app) as listener:
        polled = request(listener, "/api/state")[1]
        configured = request(listener, "/api/config")[1]["state"]
    for snapshot in (polled, configured):
        assert snapshot["state"] == "card"
        assert snapshot["card"] == baseline["card"] == result["card"]
        assert snapshot["turns"][-1]["kind"] == "card"
        assert_nameless_gate(snapshot, app.roster, baseline["card"])


@pytest.mark.parametrize("remember", [False, True])
def test_t3_terms_confirmation_survives_restart_only_with_remember(app, remember):
    """A second process can recover vendor confirmation only when Remember was enabled."""
    app.update_settings({"remember": remember})
    app.settings["adapter"] = "openai"
    app.confirm_terms(consent(app))
    restored = server.TableApp(app.data_dir)
    try:
        restored.settings["adapter"] = "openai"
        assert restored.terms_summary()["confirmed"] is remember
        assert restored.key == ""
    finally:
        restored.close()


@pytest.mark.parametrize("forget", [False, True])
def test_t3_terms_io_failure_rolls_back_every_settings_file(app, monkeypatch, forget):
    """Failure saving or forgetting consent leaves all prior settings files and active settings intact."""
    app.update_settings({"remember": True})
    app.settings["adapter"] = "openai"
    app.confirm_terms(consent(app))
    app.settings["adapter"] = "fake"
    before = {p: p.read_bytes() for p in (app.settings_path, app.preferences_path, app.terms_path)}
    active = copy.deepcopy(app.settings)
    replace, unlink = Path.replace, Path.unlink
    def failed_replace(path, target):
        if Path(target) == app.terms_path:
            raise OSError("fixture write failure")
        return replace(path, target)
    def failed_unlink(path, *args, **kwargs):
        if path == app.terms_path:
            raise OSError("fixture forget failure")
        return unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink" if forget else "replace", failed_unlink if forget else failed_replace)
    with pytest.raises(server.InputError, match="previous settings remain"):
        app.update_settings({"remember": not forget, "house_name": "Changed name"})
    assert app.settings == active
    assert {p: p.read_bytes() for p in before} == before


def test_t3_phone_polling_restores_the_canonical_remote_card_and_reset(app, monkeypatch):
    """Authenticated phone polls restore a remote card and reset; the optional event endpoint stays available."""
    phone, headers = paired(app, monkeypatch)
    status, initial, _ = request(phone, "/api/state", headers=headers)
    assert status == 200 and initial["state"] == "idle"
    result = app.turn(selected(app, "card")["text"])
    status, snapshot, _ = request(phone, "/api/state", headers=headers)
    assert status == 200 and snapshot["state"] == "card"
    assert snapshot["card"] == result["card"]
    assert snapshot["session_version"] == result["page_version"] > initial["session_version"]
    assert request(phone, "/api/state", headers=headers)[1] == snapshot
    app.reset()
    reset = request(phone, "/api/state", headers=headers)[1]
    assert reset["state"] == "idle" and reset["turns"] == []
    assert reset["session_version"] > snapshot["session_version"]
    connection = http.client.HTTPConnection("127.0.0.1", phone.server_address[1], timeout=3)
    connection.request("GET", "/api/events", headers=headers)
    response = connection.getresponse()
    try:
        assert response.status == 200
        assert response.getheader("Content-Type").startswith("text/event-stream")
        assert b"event: state\n" in response.read()
    finally:
        response.close()
        connection.close()


@pytest.mark.parametrize("remember", [False, True])
def test_t3_slow_vendor_confirmation_never_delays_a_card(app, monkeypatch, remember):
    """A slow consent-file operation leaves the sitting lock available for a crisis card."""
    app.update_settings({"remember": remember})
    app.settings["adapter"] = "openai"
    entered, release = threading.Event(), threading.Event()
    persist = app._persist_terms
    def waiting(**kwargs):
        entered.set()
        assert release.wait(3)
        return persist(**kwargs)
    monkeypatch.setattr(app, "_persist_terms", waiting)
    results = []
    worker = threading.Thread(target=lambda: results.append(app.confirm_terms(consent(app))))
    worker.start()
    try:
        assert entered.wait(2)
        started = time.monotonic()
        result = app.turn(selected(app, "card")["text"])
        assert result["kind"] == "card" and time.monotonic() - started < 0.5
    finally:
        release.set()
        worker.join(3)
    assert results == [{"confirmed": True, "vendor": "openai"}]
    assert app.sitting()["state"] == "card"


def test_t3_withheld_review_retains_embedded_house_lines(app):
    """A held reply's queue item includes the actual disclosures embedded in its displayed text."""
    case = next(case for _, case in CASES if not case.get("prior_turns") and not case.get("session")
                and (record := route(case["text"], app.roster).to_dict())["agent_id"]
                and record["safety"]["action"] != "HUMAN_ESCALATION" and record["safety"]["disclosures"])
    install(app, case, adapter=FakeAdapter(script=(TEXT,)))
    turn = app.turn(case["text"])
    assert turn["kind"] == "withheld"
    lines = list(app.harness.turns[-1].house_lines)
    assert lines and all(line in turn["text"] for line in lines)
    app.flag_turn({"turn_id": turn["turn_id"], "page_version": turn["page_version"], "label": t3.FLAGS[0]}, "computer")
    assert AuditLog(app.review_path).rows()[0]["house_lines"] == lines


def test_t3_operator_token_command_is_local_never_printed_and_not_shipped(app):
    """The default is off and the local command generates an unprinted, unshipped token."""
    assert app.settings["operator_circle"] is False
    assert not list(ROOT.rglob("operator.token"))
    assert not app.operator_token_available()
    command = [sys.executable, "-m", "apps.talking_table", "--make-operator-token", "--data-dir", str(app.data_dir)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    token = (app.data_dir / "operator.token").read_text().strip()
    assert len(token) == 64 and token not in result.stdout + result.stderr
    assert app.operator_token_available()
    assert token not in json.dumps(app.config())
    again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    assert "already exists" in again.stdout
    assert (app.data_dir / "operator.token").read_text().strip() == token


def test_t3_settings_require_token_and_saved_mode_cannot_bypass_it(app):
    """Both the settings endpoint and saved defaults enforce the local-token gate."""
    with live(app) as listener:
        assert request(listener, "/api/settings", {"operator_circle": True})[0] == 400
        assert app.settings["operator_circle"] is False
        t3.make_operator_token(app.data_dir)
        assert request(listener, "/api/settings", {"operator_circle": True, "remember": True})[0] == 200
        assert app.harness.operator_circle is True
    (app.data_dir / "operator.token").unlink()
    other = server.TableApp(app.data_dir)
    try:
        assert other.harness.operator_circle is False
    finally:
        other.close()


@pytest.mark.parametrize("path,payload", [
    ("/api/settings", {"operator_circle": True}), ("/api/settings", {"presentation": "women"}),
    ("/api/settings", {"key": "sk-TEST-PHONE"}), ("/api/settings", {"adapter": "openai"}),
    ("/api/network", {"enabled": False}), ("/api/object", {"text": "a changed object"}),
    ("/api/presentation/preview", {"persona": "willow", "presentation": "women"}),
    ("/api/operator/clear-latch", {"reason": "reviewed"}), ("/api/lights/check", {}),
    ("/api/operator/state", None), ("/api/replay?row_id=" + "a" * 64, None),
    ("/api/receipts/week", None), ("/api/receipts/export", None),
    ("/operator.html", None), ("/replay.html", None), ("/static/operator.html", None),
    ("/static/replay.html", None), ("/static/%6fperator.html", None),
    ("/static/./replay.html", None),
])
def test_t3_phone_scope_forbids_every_operator_path_without_changes(app, monkeypatch, path, payload):
    """Every protected path refuses a paired phone before it can change the sitting or settings."""
    phone, headers = paired(app, monkeypatch)
    before = (copy.deepcopy(app.settings), copy.deepcopy(app.harness.session.__dict__), app.session_version)
    assert request(phone, path, payload, headers=headers)[0] == 403
    assert before == (app.settings, app.harness.session.__dict__, app.session_version)
    assert all(record["scope"] == "phone" for record in app.pairing_records.values())


def test_t3_pairing_scope_survives_loopback_and_phone_can_turn_reset_flag(app, monkeypatch):
    """A phone cookie stays phone-scoped on loopback while ordinary shared-sitting actions work."""
    case = normal(app)
    app.set_network(True)
    token = app.pair(app.pairing_code, "phone")
    headers = {"Cookie": f"{server.COOKIE}={token}"}
    assert request(app.phone_server, "/api/settings", {"presentation": "women"}, headers=headers)[0] == 403
    result = request(app.phone_server, "/api/turn", {"text": case["text"]}, headers=headers)[1]
    assert result["kind"] == "withheld"
    assert request(app.phone_server, "/api/review/flag", {"turn_id": result["turn_id"],
        "page_version": result["page_version"], "label": t3.FLAGS[0]}, headers=headers)[0] == 200
    assert AuditLog(app.review_path).rows()[0]["scope"] == "phone"
    assert request(app.phone_server, "/api/session/reset", {}, headers=headers)[0] == 200
    assert app.state["turn_count"] == 0


@pytest.mark.parametrize("released", [False, True])
def test_t3_second_client_turn_is_in_state_and_reload_with_exact_record(app, released):
    """An externally posted released or withheld turn appears in the canonical reload snapshot."""
    case = normal(app, released)
    with live(app) as listener:
        before = request(listener, "/api/state")[1]["session_version"]
        result = request(listener, "/api/turn", {"text": case["text"]})[1]
        for path in ("/api/state", "/api/config"):
            body = request(listener, path)[1]
            snapshot = body["state"] if path.endswith("config") else body
            turn = snapshot["turns"][-1]
            assert turn["kind"] == ("reply" if released else "withheld")
            assert turn["decision"] == result["decision"]
            assert turn["user_text"] == case["text"]
            assert "speech_token" not in turn
            assert snapshot["session_version"] > before


def test_t3_stream_delivers_remote_turn_then_card_and_reset_immediately(app):
    """One SSE connection receives external changes, including the full crisis card and reset."""
    case = normal(app)
    with live(app) as listener:
        connection = http.client.HTTPConnection("127.0.0.1", listener.server_address[1], timeout=3)
        connection.request("GET", "/api/events")
        response = connection.getresponse()
        assert response.status == 200 and response.getheader("Content-Type").startswith("text/event-stream")
        def event():
            while True:
                line = response.readline().decode("utf-8")
                if line.startswith("data: "):
                    return json.loads(line[6:])
                assert line
        initial = event()
        result = request(listener, "/api/turn", {"text": case["text"]})[1]
        changed = event()
        while not changed["turns"]:
            changed = event()
        assert changed["turns"][-1]["turn_id"] == result["turn_id"]
        started = time.monotonic()
        crisis = request(listener, "/api/turn", {"text": selected(app, "card")["text"]})[1]
        changed = event()
        while changed["state"] != "card":
            changed = event()
        assert time.monotonic() - started < 1
        assert changed["card"] == crisis["card"]
        assert_nameless_gate(changed, app.roster, crisis["card"])
        app.reset()
        reset = event()
        assert reset["session_version"] > changed["session_version"] > initial["session_version"]
        assert reset["turns"] == [] and reset["state"] == "idle"
        response.close()
        connection.close()


@pytest.mark.parametrize("active", [False, True])
def test_t3_event_fetch_has_a_fixed_lifetime_even_during_updates(app, active):
    """Idle and busy event fetches reach EOF promptly and advertise native retry."""
    stop = threading.Event()
    def publish():
        while not stop.wait(0.02):
            with app.events:
                app._publish()
    worker = threading.Thread(target=publish)
    before = app.session_version
    with live(app) as listener:
        connection = http.client.HTTPConnection("127.0.0.1", listener.server_address[1], timeout=3)
        try:
            if active:
                worker.start()
            started = time.monotonic()
            connection.request("GET", "/api/events")
            response = connection.getresponse()
            frames = response.read().decode("utf-8")
            assert 0.5 < time.monotonic() - started < 2.5
            assert frames.startswith("retry: 1000\n\n")
            assert frames.endswith("event: reconnect\ndata: {}\n\n")
            states = [frame for frame in frames.split("\n\n") if "event: state\n" in frame]
            assert len(states) > 1 if active else len(states) == 1
            if not active:
                assert app.session_version == before
        finally:
            stop.set()
            if active:
                worker.join(3)
            connection.close()


def test_t3_reconnect_restores_a_card_posted_between_event_fetches(app):
    """A reconnect with an old event id returns the current card without changing the sitting."""
    normal(app)
    with live(app) as listener:
        connection = http.client.HTTPConnection("127.0.0.1", listener.server_address[1], timeout=3)
        connection.request("GET", "/api/events")
        initial = connection.getresponse().read().decode("utf-8")
        connection.close()
        old_id = next(line[4:] for line in initial.splitlines() if line.startswith("id: "))
        crisis = request(listener, "/api/turn", {"text": selected(app, "card")["text"]})[1]
        before = app.sitting()
        connection = http.client.HTTPConnection("127.0.0.1", listener.server_address[1], timeout=3)
        try:
            connection.request("GET", "/api/events", headers={"Last-Event-ID": old_id})
            frames = connection.getresponse().read().decode("utf-8")
            data = next(line[6:] for line in frames.splitlines() if line.startswith("data: "))
            restored = json.loads(data)
            assert restored == before == app.sitting()
            assert restored["session_version"] > int(old_id)
            assert restored["card"] == crisis["card"]
            assert all("speech_token" not in turn for turn in restored["turns"])
            assert request(listener, "/api/state")[1] == restored
        finally:
            connection.close()


def test_t3_late_model_cannot_change_card_version_or_reload_state(app):
    """A late ordinary reply cannot overwrite a newer card or its server version."""
    started, release = threading.Event(), threading.Event()
    def blocked(*args):
        started.set()
        release.wait(3)
        return TEXT
    case = selected(app, "normal")
    install(app, case, adapter=FakeAdapter(script=blocked), operator_circle=True)
    results = []
    worker = threading.Thread(target=lambda: results.append(app.turn(case["text"])))
    worker.start()
    try:
        assert started.wait(2)
        card = app.turn(selected(app, "card")["text"])
        before = app.sitting()
        release.set()
        worker.join(3)
        assert results[0]["superseded"] is True
        assert app.sitting() == before
        assert app.config()["state"]["card"] == card["card"]
    finally:
        release.set()


@pytest.mark.parametrize("released", [False, True])
def test_t3_flag_snapshot_is_complete_and_original_record_is_untouched(app, released):
    """Flags preserve exact record, receipt, displayed words, version and label without relabelling."""
    case = normal(app, released)
    turn = app.turn(case["text"])
    original = (app.audit_path.read_bytes(), app.receipt_path.read_bytes(), copy.deepcopy(app.harness.session.__dict__))
    app.flag_turn({"turn_id": turn["turn_id"], "page_version": turn["page_version"], "label": t3.FLAGS[1]}, "computer")
    row = AuditLog(app.review_path).rows()[0]
    assert row["record"] == turn["decision"] and row["receipt"] == turn["receipt"]
    assert row["house_lines"] == list(app.harness.turns[-1].house_lines)
    assert row["shown_text"] == turn["text"]
    assert row["page_version"] == turn["page_version"] and row["label"] == t3.FLAGS[1]
    assert original == (app.audit_path.read_bytes(), app.receipt_path.read_bytes(), app.harness.session.__dict__)


def test_t3_slow_review_queue_write_does_not_delay_card(app, monkeypatch):
    """A paused flag-file write never owns the lock needed to publish a crisis card."""
    case = normal(app)
    turn = app.turn(case["text"])
    entered, release = threading.Event(), threading.Event()
    original = AuditLog.append
    def paused(log, row):
        if log.path == app.review_path:
            entered.set()
            assert release.wait(3)
        return original(log, row)
    monkeypatch.setattr(AuditLog, "append", paused)
    worker = threading.Thread(target=app.flag_turn, args=({"turn_id": turn["turn_id"],
        "page_version": turn["page_version"], "label": t3.FLAGS[0]}, "computer"))
    worker.start()
    try:
        assert entered.wait(2)
        start = time.monotonic()
        card = app.turn(selected(app, "card")["text"])
        assert card["kind"] == "card" and time.monotonic() - start < 0.5
    finally:
        release.set()
        worker.join(3)


def test_t3_operator_correction_uses_existing_clear_api_and_records_actor_reason(app, monkeypatch):
    """Only the explicit operator path invokes clear_latch and records its actor and reason."""
    app.harness.session = SessionState(conservative_mode=True)
    before = app.correction_state()
    calls = []
    original = SessionState.clear_latch
    def observed(session, reason, *, actor="operator", which=None):
        calls.append((reason, actor))
        return original(session, reason, actor=actor, which=which)
    monkeypatch.setattr(SessionState, "clear_latch", observed)
    with live(app) as listener:
        result = request(listener, "/api/operator/clear-latch", {**before, "reason": "The operator reviewed this turn."})
        assert result[0] == 200 and result[1]["latch"] == "none"
    assert calls == [("The operator reviewed this turn.", "operator")]
    rows = app.harness.audit_log.rows()
    assert [row["kind"] for row in rows] == ["operator_latch_review", "operator_latch_clear"]
    assert rows[-1]["applied"] is True and rows[-1]["actor"] == "operator"
    assert app.harness.session.latch_history[-1][2] == "operator"


def test_t3_message_correction_cannot_call_operator_clear(app, monkeypatch):
    """Existing labelled correction text remains policy evidence and cannot invoke the page operation."""
    cases = json.loads((ROOT / "evals/case-manifest.json").read_text(encoding="utf-8"))
    assert cases["cases"]
    from test_talking_table import policy_cases
    candidates = [case for _, case in policy_cases() if "correction" in case.get("id", "")]
    assert candidates
    calls = []
    monkeypatch.setattr(SessionState, "clear_latch", lambda *args, **kwargs: calls.append(args))
    app.harness.session = SessionState(conservative_mode=True)
    app.turn(candidates[0]["text"])
    assert calls == [] and app.harness.session.latch == "hard"


def test_t3_stale_operator_review_cannot_clear_a_newer_sitting(app, monkeypatch):
    """A crisis racing a slow correction audit keeps its card and makes the old review obsolete."""
    app.harness.session = SessionState(conservative_mode=True)
    before = app.correction_state()
    entered, release = threading.Event(), threading.Event()
    append = app.harness.audit_log.append
    def paused(row):
        if row.get("kind") == "operator_latch_review":
            entered.set()
            assert release.wait(3)
        return append(row)
    monkeypatch.setattr(app.harness.audit_log, "append", paused)
    errors = []
    def clear():
        try:
            app.clear_careful_read({**before, "reason": "Reviewed the earlier turn."})
        except server.InputError as error:
            errors.append(str(error))
    worker = threading.Thread(target=clear)
    worker.start()
    try:
        assert entered.wait(2)
        start = time.monotonic()
        result = app.turn(selected(app, "card")["text"])
        assert result["kind"] == "card" and time.monotonic() - start < 0.5
        state = app.sitting()
        release.set()
        worker.join(3)
        assert errors and app.harness.session.latch == "hard"
        assert app.sitting() == state
        assert app.harness.audit_log.rows()[-1]["applied"] is False
    finally:
        release.set()


def test_t3_refused_map_counts_only_current_week_and_export_is_receipts(app):
    """The weekly map counts recorded veto reasons without exposing messages or individual dates."""
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    for age in (0, 1, 8):
        row_id = app.harness.audit_log.append({"at": (now - timedelta(days=age)).timestamp(), "user_text": "PRIVATE-MESSAGE"})
        app.receipts.append({"audit_row_id": row_id, "display_names": {"vandal": "Vandal"},
            "vetoes": [{"persona": "vandal", "reason": "grief was held"}], "roster_hash": "fixture-hash"})
    result = app.refused_seats(now)
    assert result["counts"] == [{"voice": "Vandal", "reason": "grief was held", "count": 2,
                                 "line": "Vandal was set aside twice because grief was held."}]
    assert "PRIVATE-MESSAGE" not in json.dumps(result) and "at" not in result["counts"][0]
    bundle = app.receipt_week(now)
    assert len(bundle["receipts"]) == 2 and bundle["roster_hash"]
    assert "PRIVATE-MESSAGE" not in json.dumps(bundle)


def test_t3_replay_reads_audit_or_receipt_without_routing_again(app, monkeypatch):
    """Both row-id entrances read the same saved record without recalculation or mutation."""
    turn = app.turn(normal(app)["text"])
    before = (app.audit_path.read_bytes(), app.receipt_path.read_bytes(), copy.deepcopy(app.harness.session.__dict__))
    monkeypatch.setattr(app.harness, "speak", lambda *args: pytest.fail("Replay attempted a turn"))
    for row_id in (turn["audit_row_id"], turn["receipt"]["row_id"]):
        replay = app.logged_decision(row_id)
        assert replay["record"] == turn["decision"]
        assert replay["house_lines"] == app.harness.audit_log.read(turn["audit_row_id"])["house_lines"]
    assert before == (app.audit_path.read_bytes(), app.receipt_path.read_bytes(), app.harness.session.__dict__)


def test_t3_lights_check_sequence_and_idle_do_not_touch_policy_or_storage(app, monkeypatch):
    """The worker shows roster order, card then idle while the sitting and logs stay unchanged."""
    from apps.talking_table import lights
    scenes = []
    monkeypatch.setattr(lights, "set_scene", lambda persona, state, **kwargs: scenes.append((persona, state)))
    app.update_settings({"lights_enabled": True, "lights_key": "test-only-lamps"})
    app.lights.pending.join()
    check = app.lights.check
    monkeypatch.setattr(app.lights, "check", lambda personas: check(personas, interval=0.01))
    before = (app.sitting(), copy.deepcopy(app.harness.session.__dict__))
    assert app.check_lights()["started"] is True
    deadline = time.monotonic() + 2
    while (not scenes or scenes[-1] != (None, "idle")) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert scenes == [(persona, "seated") for persona in app.roster] + [(None, "card"), (None, "idle")]
    assert before == (app.sitting(), app.harness.session.__dict__)
    assert not app.audit_path.exists() and not app.receipt_path.exists()


@pytest.mark.parametrize("settings", [{}, {"lights_enabled": True}, {"lights_key": "test-only-lamps"}])
def test_t3_unconfigured_lights_check_is_a_noop(app, monkeypatch, settings):
    """The check does nothing unless both the switch and key are present."""
    app.update_settings(settings)
    monkeypatch.setattr(app.lights, "check", lambda *args: pytest.fail("Unexpected scene check"))
    assert app.check_lights() == {"started": False, "message": "Lights are off or not set up; nothing to show."}


def test_t3_crisis_cancels_remaining_test_colours_and_idle(app, monkeypatch):
    """A foreground card cancels queued test colours and their final idle scene."""
    from apps.talking_table import lights
    entered, release = threading.Event(), threading.Event()
    scenes = []
    def scene(persona, state, **kwargs):
        scenes.append((persona, state))
        if len(scenes) == 1:
            entered.set()
            release.wait(3)
    monkeypatch.setattr(lights, "set_scene", scene)
    app.update_settings({"lights_enabled": True, "lights_key": "test-only-lamps"})
    check = app.lights.check
    monkeypatch.setattr(app.lights, "check", lambda personas: check(personas, interval=0.005))
    app.check_lights()
    try:
        assert entered.wait(2)
        time.sleep(0.05)
        card = app.turn(selected(app, "card")["text"])
        assert card["kind"] == "card"
        release.set()
        app.lights.pending.join()
        assert scenes == [(next(iter(app.roster)), "seated"), (None, "card")]
        assert app.check_lights()["started"] is False
    finally:
        release.set()


@pytest.mark.parametrize("kind", ["normal", "grief", "house", "card"])
def test_t3_display_review_and_honesty_cannot_change_policy_or_house_lines(app, kind):
    """Reading every new surface and flagging a turn cannot alter its record or attached house lines."""
    case = selected(app, kind)
    harness = install(app, case, adapter=FakeAdapter(script=(TEXT,)), operator_circle=True)
    expected = copy.deepcopy(harness)
    # A plain harness with the same input is the independent before-T3 reference.
    expected.audit_log = AuditLog()
    baseline = expected.speak(case["text"])
    turn = app.turn(case["text"])
    before = copy.deepcopy(app.harness.session.__dict__)
    app.honesty()
    app.sitting()
    app.config()
    app.refused_seats()
    app.receipt_week()
    if turn["kind"] in ("reply", "withheld"):
        app.flag_turn({"turn_id": turn["turn_id"], "page_version": turn["page_version"], "label": t3.FLAGS[0]}, "computer")
    if turn["audit_row_id"]:
        app.logged_decision(turn["audit_row_id"])
    assert app.harness.session.__dict__ == before
    if kind == "card":
        assert turn["card"] == baseline.text
    else:
        assert turn["decision"] == baseline.decision
        assert app.harness.turns[-1].house_lines == baseline.house_lines
    assert not any("talking_table" in path.read_text(encoding="utf-8")
                   for path in (ROOT / "src/secondsignal").glob("*.py"))
