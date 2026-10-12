
"""Order T4: sitting boundaries, local latch durability and declared controls."""

from __future__ import annotations

import copy
import io
import json
import runpy
import time
import urllib.request
from pathlib import Path

import pytest
from test_stream_deck import generated  # noqa: F401
from test_talking_table import live, request

from apps.talking_table import server, t3
from secondsignal.safety import SessionState
from secondsignal_harness import FakeAdapter
from secondsignal_harness.lines import HARNESS_LINES_EN
from secondsignal_harness.table_extras import eligible_agents

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "Help me make a plan for my work tomorrow."
CRISIS = "I want to kill myself."
LINK = "https://terms.example/policy?version=1#api"


@pytest.fixture
def app(tmp_path):
    instance = server.TableApp(tmp_path / "t4-data")
    try:
        yield instance
    finally:
        instance.close()


def operator(app):
    (app.data_dir / "operator.token").write_text("a" * 64, encoding="ascii")
    app.update_settings({"operator_circle": True})


def host(app):
    operator(app)
    app.update_settings({"adapter": "compatible", "url": "https://chat.example/v1/chat/completions",
                         "model": "fixture-model"})


@pytest.mark.parametrize("link", [LINK, "http://terms.example/policy", "https://terms.example/" + "x" * 278])
def test_t4_host_terms_accepts_one_bounded_http_url(app, link):
    """The operator can store a one-line HTTP or HTTPS terms link of at most 300 characters."""
    host(app)
    assert len(link) <= 300
    app.update_settings({"host_terms": {"chat.example": link}, "remember": True})
    assert app.settings["host_terms"] == {"chat.example": link}
    saved = json.loads(app.settings_path.read_text(encoding="utf-8"))
    assert saved["settings"]["host_terms"] == {"chat.example": link}
    restarted = server.TableApp(app.data_dir)
    try:
        assert restarted.settings["host_terms"] == app.settings["host_terms"]
    finally:
        restarted.close()


@pytest.mark.parametrize("value", [
    "https://terms.example/" + "x" * 281, "https://terms.example/\nnext",
    "https://terms.example/\rnext", "https://terms.example/\u2028next",
    "ftp://terms.example/", "javascript:alert(1)", "https://user@terms.example/",
    "https://user:pass@terms.example/", "https://@terms.example/", "https://",
    None, [], 1,
])
def test_t4_host_terms_rejects_invalid_urls_without_changes(app, value):
    """An invalid, multiline, oversized or credential-bearing terms URL leaves all settings unchanged."""
    host(app)
    before = copy.deepcopy(app.settings)
    with pytest.raises(server.InputError):
        app.update_settings({"host_terms": {"chat.example": value}})
    assert app.settings == before


def test_t4_host_terms_requires_operator_token_and_valid_host_mapping(app):
    """Only the operator can change a hostname-to-URL mapping, and empty values remove entries."""
    with pytest.raises(server.InputError, match="operator"):
        app.update_settings({"host_terms": {"chat.example": LINK}})
    operator(app)
    for mapping in ([], {"https://chat.example": LINK}, {"chat.example/path": LINK},
                    {"user@chat.example": LINK}, {"chat.example:443": LINK}, {"": LINK}):
        with pytest.raises(server.InputError):
            app.update_settings({"host_terms": mapping})
    app.update_settings({"host_terms": {"chat.example": LINK, "second.example": LINK}})
    app.update_settings({"host_terms": {"chat.example": ""}})
    assert app.settings["host_terms"] == {"second.example": LINK}


def test_t4_host_terms_summary_and_removal_preserve_confirmation(app):
    """An operator link is labeled unverified without changing the host's confirmation revision."""
    host(app)
    original = app.terms_summary()
    app.confirm_terms({"vendor": original["vendor"], "revision": original["revision"],
                       "accepted": True, "attested": True})
    app.update_settings({"host_terms": {"chat.example": LINK}})
    summary = app.terms_summary()
    assert summary["url"] == LINK and summary["url_source"] == "operator"
    assert summary["summary"] == original["summary"] + (
        " This link was supplied by the operator and has not been verified by the Table.")
    assert summary["vendor"] == original["vendor"] == "compatible:chat.example"
    assert summary["revision"] == original["revision"] and summary["confirmed"]
    app.update_settings({"host_terms": {"chat.example": ""}})
    assert app.terms_summary() == {**original, "confirmed": True}
    assert original["url"] is None and original["url_source"] == "none"


def test_t4_named_family_terms_are_unchanged(app):
    """The four shipped named-family summaries remain byte-for-byte equivalent as objects."""
    operator(app)
    for family in set(app.vendor_terms) - {"compatible"}:
        app.update_settings({"adapter": family, "model": "fixture-model"})
        before = app.terms_summary()
        app.update_settings({"host_terms": {"chat.example": LINK}})
        assert app.terms_summary() == before
        assert "url_source" not in before


def test_t4_host_terms_control_is_unreachable_from_phone(app):
    """A paired phone cannot read the settings field or change the operator's terms mapping."""
    operator(app)
    app.set_network(True)
    token = app.pair(app.pairing_code, "phone")
    headers = {"Cookie": f"{server.COOKIE}={token}"}
    config = request(app.phone_server, "/api/config", headers=headers)[1]
    assert "host_terms" not in config["settings"]
    status, _, _ = request(app.phone_server, "/api/settings",
                            {"host_terms": {"chat.example": LINK}}, headers=headers)
    assert status == 403 and app.settings["host_terms"] == {}


def test_t4_crisis_does_not_consult_host_terms(app, monkeypatch):
    """A card is delivered without evaluating the host link or its confirmation."""
    host(app)
    def forbidden():
        raise AssertionError("A crisis consulted terms.")
    monkeypatch.setattr(app, "terms_summary", forbidden)
    result = app.turn(CRISIS)
    assert result["kind"] == "card" and result["adapter_calls"] == 0


def test_t4_held_offer_slots_are_handback_then_assist_then_second_view(app):
    """A held turn gives hand-back and assist the two slots, freeing one second view when no assist exists."""
    operator(app)
    text = "I am grieving and need to make a plan for work tomorrow."
    for assist in (True, False):
        app.reset()
        app.harness.session = SessionState(affinities=("prefers_willow",) if assist else ())
        app.harness.adapter = FakeAdapter(script=("I hear your grief. Start with one small task.",))
        app.deferred_ask = "rowan"
        result = app.turn(text)
        assert result["decision"]["held"] and eligible_agents(result["decision"])
        assert result["kind"] == "reply"
        assert result["handback"]["persona"] == "rowan"
        if assist:
            assert result["assist_offer"]["persona"] == "willow"
            assert result["second_opinions"] == []
        else:
            assert result["assist_offer"] is None
            assert len(result["second_opinions"]) == 1
            assert result["second_opinions"][0]["persona"] in eligible_agents(result["decision"])


def prime_vague(app):
    operator(app)
    text = "Could I talk to Vandal?"
    app.turn(text)
    app.turn(text)
    return text


def test_t4_deck_declared_ask_reaches_state_audit_receipt_and_replay(app):
    """A deck-style control records its ask and the approved acknowledgement when another chair sits."""
    text = prime_vague(app)
    with live(app) as listener:
        status, result, _ = request(listener, "/api/turn",
                                     {"text": text, "action": "ask", "target": "vandal"})
        assert status == 200 and result["persona"] != "vandal"
        assert result["decision"]["asked_agent_id"] == "vandal"
        line = result["ask_acknowledgement"]
        assert line and HARNESS_LINES_EN["ask_acknowledgement"].split("{Asked}")[0] in line
        state = request(listener, "/api/state")[1]
        assert state["turns"][-1]["ask_acknowledgement"] == line
        row = app.harness.audit_log.read(result["audit_row_id"])
        assert row["decision"] == result["decision"] and row["composed"].startswith(line)
        assert result["receipt"]["asked_agent_id"] == "vandal"
        replay = request(listener, "/api/replay?row_id=" + result["receipt"]["row_id"])[1]
        assert replay["record"]["asked_agent_id"] == "vandal"
        assert replay["receipt"]["asked_agent_id"] == "vandal"


def test_t4_plain_same_text_never_declares_an_ask(app):
    """Typing the same words leaves both the acknowledgement and policy ask field absent."""
    text = prime_vague(app)
    result = app.turn(text)
    assert result["ask_acknowledgement"] is None
    assert "asked_agent_id" not in result["decision"]
    assert "asked_agent_id" not in result["receipt"]
    row = app.harness.audit_log.read(result["audit_row_id"])
    assert "asked_agent_id" not in row["decision"]


def test_t4_handback_declares_ask_without_redeferring_it(app):
    """A hand-back records the offered target and explains a different seat while consuming the offer."""
    operator(app)
    app.deferred_ask = "willow"
    result = app.turn(PROMPT)
    offer = result["handback"]
    assert offer and offer["persona"] == "willow"
    app.harness.session.empty_streak = 2
    returned = app.turn(offer["text"], action="handback", target=offer["persona"])
    assert returned["decision"]["asked_agent_id"] == "willow"
    assert returned["persona"] != "willow" and returned["ask_acknowledgement"]
    assert app.deferred_ask is None and returned["handback"] is None


def test_t4_phone_ask_uses_the_same_declared_control(app):
    """The paired phone's existing ask payload reaches the same policy declaration path."""
    text = prime_vague(app)
    app.set_network(True)
    token = app.pair(app.pairing_code, "phone")
    status, result, _ = request(app.phone_server, "/api/turn",
                                {"text": text, "action": "ask", "target": "vandal"},
                                headers={"Cookie": f"{server.COOKIE}={token}"})
    assert status == 200 and result["decision"]["asked_agent_id"] == "vandal"
    assert result["ask_acknowledgement"]


def test_t4_generated_scripts_embed_and_post_each_persona(generated, monkeypatch):  # noqa: F811
    """Every generated script carries its persona explicitly and posts text, action and target."""
    _, destination, _ = generated
    sent = []
    def capture(self, request, **kwargs):
        sent.append(request)
        return io.BytesIO(b"{}")
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", capture)
    for persona in server.load_roster():
        script = runpy.run_path(str(destination / f"ask_{persona}.pyw"))
        assert script["CHARACTER"] == persona
        assert script["main"]([]) == 0
        assert json.loads(sent[-1].data) == {
            "text": f"Could I talk to {script['NAMES'][persona]}?",
            "action": "ask", "target": persona}



def test_t4_quiet_limit_ends_sitting_once_and_only_after_an_accepted_turn(app, monkeypatch):
    """The eight-hour boundary creates exactly one fresh sitting, while an empty sitting never expires."""
    now = [1000000.0]
    monkeypatch.setattr(server.time, "time", lambda: now[0])
    initial = app.session_id
    now[0] += server.SITTING_QUIET_LIMIT_SECONDS * 2
    with live(app) as listener:
        assert request(listener, "/api/state")[1]["session_id"] == initial
        app.turn(PROMPT)
        accepted = app.last_turn_at
        now[0] = accepted + server.SITTING_QUIET_LIMIT_SECONDS - 1
        before = request(listener, "/api/state")[1]
        assert before["session_id"] == initial and before["turn_count"] == 1
        assert before["last_turn_at"] == accepted
        now[0] += 1
        expired = request(listener, "/api/state")[1]
        assert expired["session_id"] != initial and expired["turn_count"] == 0
        assert expired["last_turn_at"] is None
        assert expired["sitting_notice"] == t3.T4_LINES["sitting_ended"]
        again = request(listener, "/api/state")[1]
        assert again["session_id"] == expired["session_id"] and again["sitting_notice"] is None
        now[0] += server.SITTING_QUIET_LIMIT_SECONDS * 2
        assert request(listener, "/api/state")[1]["session_id"] == expired["session_id"]


def test_t4_reload_preserves_pairing_sitting_count_and_record_and_reset_ends_it(app):
    """Reloading with the same pairing preserves the sitting, while explicit Reset ends it."""
    app.set_network(True)
    token = app.pair(app.pairing_code, "phone")
    headers = {"Cookie": f"{server.COOKIE}={token}"}
    request(app.phone_server, "/api/turn", {"text": PROMPT}, headers=headers)
    before = request(app.phone_server, "/api/state", headers=headers)[1]
    reloaded = request(app.phone_server, "/api/state", headers=headers)[1]
    assert (reloaded["session_id"], reloaded["turn_count"], reloaded["turns"][-1]["decision"]) == (
        before["session_id"], 1, before["turns"][-1]["decision"])
    reset = request(app.phone_server, "/api/session/reset", {}, headers=headers)[1]["state"]
    assert reset["session_id"] != before["session_id"] and reset["turn_count"] == 0
    assert reset["last_turn_at"] is None and reset["turns"] == []


def test_t4_quiet_notice_waits_for_computer_scope(app, monkeypatch):
    """A phone request can trigger expiry but cannot consume the computer's one-time notice."""
    now = [1000000.0]
    monkeypatch.setattr(server.time, "time", lambda: now[0])
    app.set_network(True)
    token = app.pair(app.pairing_code, "phone")
    headers = {"Cookie": f"{server.COOKIE}={token}"}
    app.turn(PROMPT)
    now[0] += server.SITTING_QUIET_LIMIT_SECONDS
    phone = request(app.phone_server, "/api/state", headers=headers)[1]
    assert phone["sitting_notice"] is None
    with live(app) as listener:
        computer = request(listener, "/api/config")[1]["state"]
        assert computer["sitting_notice"] == t3.T4_LINES["sitting_ended"]
        assert request(listener, "/api/state")[1]["sitting_notice"] is None


def test_t4_rejected_turn_does_not_renew_quiet_time(app, monkeypatch):
    """A rejected control does not count as an accepted turn or postpone expiry."""
    now = [1000000.0]
    monkeypatch.setattr(server.time, "time", lambda: now[0])
    app.turn(PROMPT)
    accepted = app.last_turn_at
    now[0] += 100
    with pytest.raises(server.InputError):
        app.turn(PROMPT, action="ask", target="vandal")
    assert app.last_turn_at == accepted and app.harness.session.turn_count == 1


def latch_turn(app):
    return app.turn("I am 14 and need help with homework. Distinctive plum notebook sentence.")


def test_t4_latch_survives_restart_reset_and_policy_line_appears_once(app):
    """A restart and Reset carry exact latch fields and history while the policy repeats its own line once."""
    latch_turn(app)
    fields = app._latch_fields()
    saved = json.loads(app.latch_path.read_text(encoding="utf-8"))
    assert set(saved) == set(t3.LATCH_FIELDS) | {"saved_at", "saved_in_sitting", "table_version"}
    assert {key: saved[key] for key in t3.LATCH_FIELDS} == fields
    assert saved["saved_in_sitting"] == app.session_id
    restarted = server.TableApp(app.data_dir)
    try:
        session = restarted.harness.session
        assert session.latch == "hard" and session.latch_reasons == fields["latch_reasons"]
        assert session.latch_history[:-1] == [tuple(row) for row in fields["latch_history"]]
        assert session.latch_history[-1] == ("restore", "hard:" + ",".join(fields["latch_reasons"]), "table", 0)
        assert session.hard_line_shown is False
        assert json.loads(restarted.latch_path.read_bytes())["latch_history"][-1][0] == "restore"
        restarted.turn(PROMPT)
        first = restarted.harness.turns[-1]
        restarted.turn(PROMPT)
        second = restarted.harness.turns[-1]
        careful = server.HOUSE_LINES_EN["minor_inferred"]
        assert careful in first.house_lines and careful not in second.house_lines
        previous = restarted.session_id
        restarted.reset()
        assert restarted.session_id != previous and restarted.harness.session.latch == "hard"
        assert restarted.harness.session.latch_history[-1][0] == "restore"
        assert restarted.harness.session.hard_line_shown is False
    finally:
        restarted.close()


def test_t4_clear_requires_operator_reason_and_removes_file(app):
    """Only a reviewed operator clearance removes a Table latch and its persistent file."""
    latch_turn(app)
    with pytest.raises(server.InputError, match="reason"):
        app.clear_careful_read({**app.correction_state(), "reason": ""})
    with pytest.raises(server.InputError, match="token"):
        app.clear_careful_read({**app.correction_state(), "reason": "Reviewed locally."})
    operator(app)
    with live(app) as listener:
        before = request(listener, "/api/operator/state")[1]
        status, after, _ = request(listener, "/api/operator/clear-latch",
                                    {**before, "reason": "The operator reviewed the earlier signal."})
        assert status == 200 and after["latch"] == "none"
    assert not app.latch_path.exists() and app.harness.session.latch_reasons == []
    app.reset()
    assert app.harness.session.latch == "none" and not app.latch_path.exists()


@pytest.mark.parametrize("content", ["not json", "null", "{}", '{"latch":"hard"}', "[" * 1100 + "]" * 1100])
def test_t4_invalid_latch_file_fails_closed_and_is_corrected(tmp_path, content):
    """Missing fields, invalid JSON and invalid document shapes restore a hard fault latch and corrected file."""
    folder = tmp_path / "broken-latch"
    folder.mkdir()
    (folder / "latch.json").write_text(content, encoding="utf-8")
    instance = server.TableApp(folder)
    try:
        assert instance.harness.session.latch == "hard"
        assert instance.harness.session.latch_reasons == ["latch_file_unreadable"]
        assert "latch_file_unreadable" in instance.correction_state()["latch_notice"]
        corrected = json.loads(instance.latch_path.read_text(encoding="utf-8"))
        assert corrected["latch_reasons"] == ["latch_file_unreadable"]
        assert corrected["latch_history"][-1] == ["restore", "hard:latch_file_unreadable", "table", 0]
        operator(instance)
        instance.clear_careful_read({**instance.correction_state(), "reason": "Reviewed the damaged file."})
        assert not instance.latch_path.exists() and instance.latch_notice is None
    finally:
        instance.close()


def test_t4_unreadable_latch_file_fails_closed(tmp_path, monkeypatch):
    """An operating-system read failure produces the same hard fault latch and operator notice."""
    folder = tmp_path / "unreadable-latch"
    folder.mkdir()
    path = folder / "latch.json"
    path.write_text("{}", encoding="utf-8")
    original = Path.read_text
    def unreadable(candidate, *args, **kwargs):
        if candidate == path:
            raise PermissionError("test file cannot be read")
        return original(candidate, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", unreadable)
    instance = server.TableApp(folder)
    try:
        assert instance.harness.session.latch_reasons == ["latch_file_unreadable"]
        assert "latch_file_unreadable" in instance.correction_state()["latch_notice"]
        assert json.loads(path.read_bytes())["latch"] == "hard"
    finally:
        instance.close()


def test_t4_none_file_is_removed_and_latch_storage_is_outside_repository(app):
    """An empty latch file is removed at construction and latch storage follows the outside-repository rule."""
    payload = {**app._latch_fields(), "saved_at": 1, "saved_in_sitting": app.session_id,
               "table_version": t3.__version__}
    app.latch_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = server.TableApp(app.data_dir)
    try:
        assert restarted.harness.session.latch == "none" and not restarted.latch_path.exists()
        assert ROOT not in restarted.latch_path.parents
    finally:
        restarted.close()
    with pytest.raises(server.InputError, match="outside"):
        server.TableApp(ROOT / "forbidden-t4-data")


def test_t4_file_omits_whole_messages_but_preserves_policy_correction_history(app):
    """The file excludes whole messages while preserving the exact policy correction fragments authorized by the operator."""
    distinctive = "I am 14 and need help with homework. Distinctive plum notebook sentence."
    app.turn(distinctive)
    correction = "I'm 30, that was a joke; the distinctive amber notebook stays on this shelf."
    app.turn(correction)
    serialized = app.latch_path.read_text(encoding="utf-8")
    assert distinctive not in serialized and correction not in serialized
    rows = app.harness.session.latch_history
    assert any(row[0] == "correction" for row in rows)
    assert json.loads(serialized)["latch_history"] == [list(row) for row in rows]
    assert "transcript" not in serialized and "user_text" not in serialized


def test_t4_latch_carried_notice_is_served_once_to_computer_only(app):
    """Phone snapshots leave the carried-latch notice pending for the first computer state."""
    latch_turn(app)
    app.reset()
    app.set_network(True)
    token = app.pair(app.pairing_code, "phone")
    headers = {"Cookie": f"{server.COOKIE}={token}"}
    assert request(app.phone_server, "/api/state", headers=headers)[1]["latch_carried"] is False
    with live(app) as listener:
        first = request(listener, "/api/state")[1]
        assert first["latch_carried"] is True
        assert first["latch_carried_notice"] == t3.T4_LINES["latch_carried"]
        next_state = request(listener, "/api/state")[1]
        assert next_state["latch_carried"] is False and next_state["latch_carried_notice"] is None


def test_t4_sitting_starts_never_reread_latch_file_and_unchanged_turn_does_not_rewrite(app, monkeypatch):
    """Reset carries memory without rereading disk, and an unchanged hard latch is not rewritten."""
    latch_turn(app)
    before = app.latch_path.read_bytes()
    original = Path.read_text
    def forbidden(candidate, *args, **kwargs):
        assert candidate != app.latch_path, "latch.json was reread after construction"
        return original(candidate, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", forbidden)
    app.turn(PROMPT)
    assert app.latch_path.read_bytes() == before
    old_history = list(app.harness.session.latch_history)
    app.reset()
    assert app.harness.session.latch_history[:-1] == old_history
    assert app.harness.session.latch_history[-1][0] == "restore"
    saved = json.loads(app.latch_path.read_bytes())
    assert saved["saved_in_sitting"] == app.session_id


def test_t4_memory_wins_changed_file_and_names_disagreement(app):
    """A changed file is overwritten from the policy's in-memory fields and the operator sees the disagreement."""
    latch_turn(app)
    memory = app._latch_fields()
    app.latch_path.write_text("{}", encoding="utf-8")
    app.turn(PROMPT)
    saved = json.loads(app.latch_path.read_bytes())
    assert {key: saved[key] for key in t3.LATCH_FIELDS} == memory
    assert app.correction_state()["latch_notice"] == t3.LATCH_MEMORY_WINS


def test_t4_quiet_expired_crisis_never_waits_for_latch_writer(app, monkeypatch):
    """A crisis at expiry reaches the new sitting without waiting for a blocked latch write or rereading a file."""
    import threading
    now = [1000000.0]
    monkeypatch.setattr(server.time, "time", lambda: now[0])
    latch_turn(app)
    old_session = app.session_id
    entered, release = threading.Event(), threading.Event()
    original = app._save_latch
    def paused(payload):
        entered.set()
        assert release.wait(5)
        return original(payload)
    monkeypatch.setattr(app, "_save_latch", paused)
    now[0] += server.SITTING_QUIET_LIMIT_SECONDS
    try:
        with live(app) as listener:
            status, card, _ = request(listener, "/api/turn", {"text": CRISIS}, timeout=0.7)
            assert status == 200 and card["kind"] == "card" and card["adapter_calls"] == 0
            assert card["state"]["session_id"] != old_session
            assert card["state"]["turn_count"] == 1 and app.harness.session.latch == "hard"
            assert entered.wait(1) and not release.is_set()
    finally:
        release.set()
        app._latch_pending.join()


def test_t4_queued_write_cannot_resurrect_operator_cleared_latch(app, monkeypatch):
    """A delayed accepted-turn write is serialized before clearance so it cannot recreate a cleared file."""
    import threading
    operator(app)
    entered, release = threading.Event(), threading.Event()
    original = app._save_latch
    def paused(payload):
        if payload["latch"] != "none":
            entered.set()
            assert release.wait(5)
        return original(payload)
    monkeypatch.setattr(app, "_save_latch", paused)
    results = []
    worker = threading.Thread(target=lambda: results.append(latch_turn(app)))
    worker.start()
    try:
        assert entered.wait(10)
        # The accepted policy fields are already authoritative before durability.
        clear = threading.Thread(target=lambda: app.clear_careful_read({
            **app.correction_state(), "reason": "The operator reviewed this signal."}))
        clear.start()
        # Landing fix, 10 October 2026: release the paused write only once the
        # clearance has queued its own write behind it, so the review is judged
        # against a sitting the turn's completion has not yet moved; before this
        # the test raced the turn's own completion and sometimes saw the review
        # refused as "the sitting changed", which is the server being careful,
        # not the property under test.
        deadline = time.monotonic() + 10
        while app._latch_pending.unfinished_tasks < 2 and clear.is_alive() and time.monotonic() < deadline:
            time.sleep(0.005)
        assert app._latch_pending.unfinished_tasks == 2
        release.set()
        clear.join(10)
        worker.join(10)
        assert not clear.is_alive() and not worker.is_alive()
        assert app.harness.session.latch == "none" and not app.latch_path.exists()
    finally:
        release.set()
        worker.join(3)
        app._latch_pending.join()


@pytest.mark.parametrize("field,value", [
    ("saved_at", 10 ** 400), ("latch_reasons", [chr(0xD800)]),
    ("soft_sticky", 1), ("latch_history", [["restore", "hard:test", "table", -1]]),
])
def test_t4_invalid_latch_values_fail_closed(app, field, value):
    """Invalid types, unencodable text and oversized timestamps fail closed before requests are served."""
    payload = {**app._latch_fields(), "saved_at": 1, "saved_in_sitting": app.session_id,
               "table_version": t3.__version__}
    payload[field] = value
    app.latch_path.write_text(json.dumps(payload), encoding="utf-8")
    restarted = server.TableApp(app.data_dir)
    try:
        assert restarted.harness.session.latch == "hard"
        assert restarted.harness.session.latch_reasons == ["latch_file_unreadable"]
    finally:
        restarted.close()


def test_t4_operator_refresh_recognizes_a_new_local_token(app):
    """The operator review page recognizes a newly created token without a restart or another settings visit."""
    latch_turn(app)
    with live(app) as listener:
        assert request(listener, "/api/operator/state")[1]["operator_token_available"] is False
        (app.data_dir / "operator.token").write_text("a" * 64, encoding="ascii")
        assert request(listener, "/api/operator/state")[1]["operator_token_available"] is True


def test_t4_slow_host_terms_save_does_not_delay_a_crisis(app, monkeypatch):
    """A paused host-terms disk write releases the sitting lock so a crisis card can leave immediately."""
    import threading
    operator(app)
    entered, release = threading.Event(), threading.Event()
    original = app._persist_settings
    def paused(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)
    monkeypatch.setattr(app, "_persist_settings", paused)
    worker = threading.Thread(target=lambda: app.update_settings({"host_terms": {"chat.example": LINK}}))
    worker.start()
    try:
        assert entered.wait(2)
        with live(app) as listener:
            status, card, _ = request(listener, "/api/turn", {"text": CRISIS}, timeout=0.7)
            assert status == 200 and card["kind"] == "card" and card["adapter_calls"] == 0
            assert not release.is_set()
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive()


@pytest.mark.parametrize("package,count,expected", [('src/secondsignal/', 21, '183e15c9707de81abc1aaeefec40c5e8dca07c9e5303b1732730acc86fd50a64'), ('src/secondsignal_harness/', 12, '26e500f585c147a489018d1a722acaa9a5636e71e5cd683d519f1f7bda5ac7d2')])  # Order G1, 2026-10-10, landed 2026-10-11: the policy package moved on purpose (lexicon, gate constant and call, the two packs), 85e848a59368e91c3ac396d94484e4e97d3f46acbc54670f08d5ca0f8424f79b -> 183e15c9707de81abc1aaeefec40c5e8dca07c9e5303b1732730acc86fd50a64; the harness package stays byte-identical to landing 8.
def test_t4_policy_and_harness_are_byte_identical(package, count, expected):
    """The complete source inventory and every byte in each protected package match the supplied tree."""
    import hashlib
    files = sorted((path for path in (ROOT / package).rglob("*")
                    if path.is_file() and "__pycache__" not in path.parts),
                   key=lambda path: path.relative_to(ROOT).as_posix())
    assert len(files) == count
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode() + bytes([0])
                      + hashlib.sha256(path.read_bytes()).digest())
    assert digest.hexdigest() == expected

def test_t4_startup_write_failure_keeps_valid_policy_history(app, monkeypatch):
    """Failure to save a restored latch preserves its valid policy evidence and reports only the write failure."""
    latch_turn(app)
    fields = app._latch_fields()
    def blocked(_self, _payload):
        raise PermissionError("fixture startup write denied")
    monkeypatch.setattr(server.TableApp, "_save_latch", blocked)
    restarted = server.TableApp(app.data_dir)
    try:
        assert restarted.harness.session.latch == fields["latch"]
        assert restarted.harness.session.latch_reasons == fields["latch_reasons"]
        assert restarted.harness.session.latch_history[:-1] == [tuple(row) for row in fields["latch_history"]]
        assert restarted.harness.session.latch_history[-1][0] == "restore"
        assert restarted.correction_state()["latch_notice"] == t3.LATCH_WRITE_FAILED
    finally:
        restarted.close()

def test_t4_quiet_crisis_reuses_open_audit_sink(app, monkeypatch):
    """Starting the quiet-expired sitting never reopens or scans the audit log before a crisis card."""
    latch_turn(app)
    old = app.session_id
    now = app.last_turn_at + server.SITTING_QUIET_LIMIT_SECONDS
    monkeypatch.setattr(server.time, "time", lambda: now)
    def forbidden(*args, **kwargs):
        raise AssertionError("quiet boundary reopened the audit log")
    monkeypatch.setattr(server, "AuditLog", forbidden)
    card = app.turn(CRISIS)
    assert card["kind"] == "card" and card["adapter_calls"] == 0
    assert app.session_id != old and app.harness.session.latch == "hard"
