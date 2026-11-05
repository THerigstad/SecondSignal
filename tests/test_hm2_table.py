"""HM2: real Table controls and sitting boundaries carry harness evidence."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest
from test_talking_table import CRISIS, PROMPT, live, request

from apps.talking_table import server
from secondsignal_harness import AdapterReply, FakeAdapter, event_log
from secondsignal_harness import spec as specification_module
from secondsignal_harness.audit_log import canonical_row
from secondsignal_harness.spec import HarnessSpecification


@pytest.fixture
def app(tmp_path):
    instance = server.TableApp(tmp_path / "hm2-table")
    try:
        yield instance
    finally:
        instance.close()


def snapshot(app):
    return app.harness.ensure_specification().snapshot()


def events(app):
    return snapshot(app)["records"]["material_change_events"]


def operator(app):
    (app.data_dir / "operator.token").write_text("a" * 64, encoding="ascii", newline="\n")
    app.update_settings({"operator_circle": True})


def test_hm2_table_five_turns_have_one_specification_and_ordered_ordinals(app):
    for _ in range(5):
        app.turn(PROMPT)
    app.flush_specifications()
    rows = app.harness.audit_log.rows()
    assert len(rows) == 5
    assert [row["sitting_turn_ordinal"] for row in rows] == [1, 2, 3, 4, 5]
    assert {row["schema"] for row in rows} == {"secondsignal_harness.audit_row.v2"}
    assert {row["specification_hash"] for row in rows} == {snapshot(app)["specification_hash"]}
    assert [row["material_change_event_id"] for row in rows] == [None] * 5
    assert events(app) == []


def test_hm2_model_change_keeps_sitting_and_records_operator_authority(app):
    app.turn(PROMPT)
    first = snapshot(app)
    sitting = app.session_id
    session = app.harness.session
    transcript = list(app.harness.transcript)
    app.update_settings({"model": "second-fake-model"})
    changed = snapshot(app)
    assert app.session_id == sitting and app.harness.session is session
    assert app.harness.transcript == transcript
    assert changed["specification_hash"] != first["specification_hash"]
    assert changed["model_pairing"]["requested"]["model_id"] == "second-fake-model"
    assert changed["records"]["run_start"]["model_pairing"]["requested"]["model_id"] == "fake-1"
    assert events(app)
    assert '"control": "update_settings"' in json.dumps(events(app))
    assert '"scope": "computer"' in json.dumps(events(app))
    app.turn(PROMPT)
    row = app.harness.audit_log.rows()[-1]
    assert row["sitting_turn_ordinal"] == 2 and row["material_change_event_id"] is not None
    assert row["specification_hash"] == snapshot(app)["specification_hash"]


def test_hm2_host_terms_and_retention_changes_are_recorded_but_rejection_is_inert(app):
    initial = snapshot(app)
    with pytest.raises(server.InputError, match="token"):
        app.update_settings({"host_terms": {"host.example": "https://host.example/terms"}})
    assert snapshot(app) == initial
    operator(app)
    old_events = len(events(app))
    app.update_settings({"host_terms": {"host.example": "https://host.example/terms"},
                         "remember": True})
    recorded = events(app)[old_events:]
    assert recorded
    serialized = json.dumps(recorded)
    assert "https://host.example/terms" in serialized
    assert '"remember": true' in serialized
    assert '"operator_token": true' in serialized
    app.update_settings({"host_terms": {"host.example": ""}, "remember": False})
    assert len(events(app)) > old_events + len(recorded)


def test_hm2_pairing_changes_are_authorized_and_never_record_capability_secrets(app):
    app.set_network(True)
    pairing_code = app.pairing_code
    token = app.pair(pairing_code, "fixture-phone")
    paired = snapshot(app)
    assert events(app)
    assert '"pairing_code_verified": true' in json.dumps(events(app))
    before = snapshot(app)
    status, _, _ = request(app.phone_server, "/api/settings", {"model": "forbidden"},
                            headers={"Cookie": f"{server.COOKIE}={token}"})
    assert status == 403 and snapshot(app) == before
    app.set_network(False)
    assert snapshot(app)["specification_hash"] != paired["specification_hash"]
    app.flush_specifications()
    for path in app.data_dir.glob("audit.*.jsonl"):
        serialized = path.read_text(encoding="utf-8")
        assert token not in serialized
        assert '"pairing_code"' not in serialized
    assert token not in json.dumps(snapshot(app))
    assert '"paired_devices": 0' in json.dumps(events(app)[-1])


def test_hm2_applied_latch_clearance_names_request_reason_and_authorization(app):
    app.turn("I am 14 and need help with homework.")
    operator(app)
    before = len(events(app))
    app.clear_careful_read({**app.correction_state(), "reason": "The operator checked the age evidence."})
    recorded = events(app)[before:]
    serialized = json.dumps(recorded)
    assert "latch_clearance" in serialized
    assert "The operator checked the age evidence." in serialized
    assert '"operator_token": true' in serialized
    assert '"request_row_id"' in serialized
    assert app.harness.session.latch == "none"
    with pytest.raises(server.InputError):
        app.clear_careful_read({"session_id": "stale", "session_version": -1,
                                "reason": "Obsolete review."})
    assert events(app)[before:] == recorded


def test_hm2_quiet_expiry_records_end_without_waiting_for_specification_disk(app, monkeypatch):
    app.turn(PROMPT)
    app.flush_specifications()
    old_sitting = app.session_id
    entered, release = threading.Event(), threading.Event()
    original = HarnessSpecification.commit

    def paused(candidate):
        ending = candidate.snapshot()["records"]["run_end"]
        if ending and ending["outcome"]["reason"] == "quiet_expiry":
            entered.set()
            assert release.wait(5)
        return original(candidate)

    monkeypatch.setattr(HarnessSpecification, "commit", paused)
    monkeypatch.setattr(server.time, "time", lambda: app.last_turn_at + server.SITTING_QUIET_LIMIT_SECONDS
                        if app.last_turn_at is not None else 999999.0)
    try:
        started = time.monotonic()
        card = app.turn(CRISIS)
        assert card["kind"] == "card" and card["adapter_calls"] == 0
        assert time.monotonic() - started < 0.5
        assert entered.wait(1) and not release.is_set()
        assert app.session_id != old_sitting
        ended = app._closed_specifications[-1].snapshot()["records"]["run_end"]
        assert ended["outcome"]["reason"] == "quiet_expiry"
        assert ended["outcome"]["accepted_turns"] == 1
        assert app.harness.audit_log.rows()[-1]["sitting_turn_ordinal"] == 1
    finally:
        release.set()
        app.flush_specifications()


def test_hm2_settings_specification_write_never_blocks_a_crisis(app, monkeypatch):
    operator(app)
    app.flush_specifications()
    entered, release = threading.Event(), threading.Event()
    original = HarnessSpecification.commit
    errors = []

    def paused(candidate):
        if "https://delay.example/terms" in json.dumps(candidate.snapshot()):
            entered.set()
            assert release.wait(5)
        return original(candidate)

    def settings():
        try:
            app.update_settings({"host_terms": {"delay.example": "https://delay.example/terms"}})
        except Exception as error:
            errors.append(error)

    monkeypatch.setattr(HarnessSpecification, "commit", paused)
    worker = threading.Thread(target=settings)
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
    assert not worker.is_alive() and not errors
    app.flush_specifications()


def test_hm2_canceled_model_reply_cannot_change_live_model_pairing(app):
    entered, release = threading.Event(), threading.Event()

    class Delayed(FakeAdapter):
        def complete(self, system, messages, *, max_tokens):
            entered.set()
            assert release.wait(5)
            return AdapterReply("A small next step.", "late-reported-model")

    app.harness.adapter = Delayed()
    result, errors = [], []

    def turn():
        try:
            result.append(app.turn(PROMPT))
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=turn)
    worker.start()
    try:
        assert entered.wait(2)
        app.update_settings({"model": "current-fake-model"})
        current = snapshot(app)
        release.set()
        worker.join(3)
        assert not worker.is_alive() and not errors
        assert result[0]["superseded"] is True
        assert snapshot(app) == current
        assert "late-reported-model" not in json.dumps(snapshot(app))
    finally:
        release.set()
        worker.join(3)


def test_hm2_reset_and_shutdown_finalize_distinct_runs(app):
    app.turn(PROMPT)
    app.reset()
    reset = app._closed_specifications[-1].snapshot()["records"]["run_end"]
    assert reset["outcome"]["reason"] == "reset" and reset["outcome"]["accepted_turns"] == 1
    assert snapshot(app)["records"]["run_end"] == {}
    app.turn(PROMPT)
    app.close()
    shutdown = app._closed_specifications[-1].snapshot()["records"]["run_end"]
    assert shutdown["outcome"]["reason"] == "shutdown"
    assert shutdown["outcome"]["accepted_turns"] == 1


def test_hm2_quiet_boundary_uses_memory_and_carries_truthful_runtime_facts(app, monkeypatch):
    app.turn(PROMPT)
    app.flush_specifications()
    deadline = app.last_turn_at + server.SITTING_QUIET_LIMIT_SECONDS
    monkeypatch.setattr(server.time, "time", lambda: deadline)
    owner = threading.get_ident()
    read_text, read_bytes = Path.read_text, Path.read_bytes

    def check_text(path, *args, **kwargs):
        assert threading.get_ident() != owner, "quiet boundary read a text file"
        return read_text(path, *args, **kwargs)

    def check_bytes(path, *args, **kwargs):
        assert threading.get_ident() != owner, "quiet boundary read a byte file"
        return read_bytes(path, *args, **kwargs)

    with monkeypatch.context() as boundary:
        boundary.setattr(Path, "read_text", check_text)
        boundary.setattr(Path, "read_bytes", check_bytes)
        app.end_quiet_sitting()
    components = snapshot(app)["active_configuration"]["components"]
    memory = next(c for c in components if c["name"] == "context and memory")
    assert memory["configuration"]["latch_persistence"] is True
    assert memory["configuration"]["holds_survive_restart"] is False
    runtime = components[-1]["configuration"]["runtime"]
    assert runtime["quiet_limit_seconds"] == server.SITTING_QUIET_LIMIT_SECONDS
    assert runtime["model_concurrency_limit"] == server.MODEL_CONCURRENCY_LIMIT
    assert runtime["permissions"]["table_owned_latch_requires_token"] is True
    app.flush_specifications()


@pytest.mark.parametrize("change", ["pair", "revoke"])
def test_hm2_pairing_during_model_wait_preserves_authorized_history(app, change):
    app.set_network(True)
    if change == "revoke":
        app.pair(app.pairing_code, "initial-phone")
    initial = snapshot(app)
    initial_event = app.harness.specification.material_change_event_id
    entered, release = threading.Event(), threading.Event()

    class Delayed(FakeAdapter):
        def complete(self, system, messages, *, max_tokens):
            entered.set()
            assert release.wait(5)
            return AdapterReply("A small next step.", "actual-fake-model", model_version="1")

    app.harness.adapter = Delayed()
    results, errors = [], []

    def turn():
        try:
            results.append(app.turn(PROMPT))
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=turn)
    worker.start()
    try:
        assert entered.wait(2)
        if change == "pair":
            app.pair(app.pairing_code, "new-phone")
        else:
            app.set_network(False)
        changed_events = list(events(app))
        assert len(changed_events) > len(initial["records"]["material_change_events"])
        next_event = app.harness.specification.material_change_event_id
        release.set()
        worker.join(3)
        assert not worker.is_alive() and not errors and not results[0].get("superseded")
        current = snapshot(app)
        assert current["records"]["material_change_events"][:len(changed_events)] == changed_events
        assert current["model_pairing"]["host_reported"]["model_id"] == "actual-fake-model"
        first = app.harness.audit_log.rows()[-1]
        assert first["sitting_turn_ordinal"] == 1
        assert first["material_change_event_id"] == initial_event
        app.turn(PROMPT)
        second = app.harness.audit_log.rows()[-1]
        assert second["sitting_turn_ordinal"] == 2
        assert second["material_change_event_id"] == next_event
        assert all(event["requested_by"] != "embedding_application" for event in events(app))
    finally:
        release.set()
        worker.join(3)


def test_hm2_observed_operator_token_changes_update_permission_configuration(app):
    before = snapshot(app)
    path = app.data_dir / "operator.token"
    path.write_text("a" * 64, encoding="ascii", newline="\n")
    assert app.config()["honesty"]["operator_token_available"] is True
    available = snapshot(app)
    assert available["specification_hash"] != before["specification_hash"]
    assert '"operator_token_observation"' in json.dumps(events(app))
    runtime = available["active_configuration"]["components"][-1]["configuration"]["runtime"]
    assert runtime["operator_token_available"] is True
    assert runtime["permissions"]["operator_token_available"] is True
    app.turn(PROMPT)
    row = app.harness.audit_log.rows()[-1]
    assert row["material_change_event_id"] is not None
    path.write_text("invalidated locally", encoding="ascii", newline="\n")
    assert app.config()["honesty"]["operator_token_available"] is False
    runtime = snapshot(app)["active_configuration"]["components"][-1]["configuration"]["runtime"]
    assert runtime["permissions"]["operator_token_available"] is False
    assert "a" * 64 not in json.dumps(snapshot(app))


def seed_material_history(directory, count):
    """Write a valid historical chain once, without timing repeated appends."""
    directory.mkdir()
    lines, previous = [], None
    for index in range(count):
        event = {
            "kind": "change", "field": "historical_fixture_setting",
            "old_value": index, "new_value": index + 1,
            "requested_by": "operator", "authorized_by": "offline fixture",
            "interval": {"from_turn": index + 1, "until_turn": None},
            "reversed": False, "reverses_event_id": None,
        }
        event["event_id"] = event_log.event_digest(event)
        body = {"sequence": index + 1, "previous_event_sha256": previous, "event": event}
        previous = event_log.event_digest(body)
        lines.append(canonical_row({**body, "sha256": previous}))
    path = directory / "audit.material-changes.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    path.with_suffix(".head.json").write_text(
        canonical_row({"count": count, "sha256": previous}) + "\n",
        encoding="utf-8", newline="\n")


def test_hm2_table_turn_digest_work_does_not_grow_with_verified_history(tmp_path, monkeypatch):
    """A real material append must not rehash all earlier sittings per turn."""
    class Reported(FakeAdapter):
        def complete(self, system, messages, *, max_tokens):
            reply = super().complete(system, messages, max_tokens=max_tokens)
            return AdapterReply(reply.text, "changed-host-revision", reply.usage, reply.model_version)

    digest_counts = {}
    for historical_count in (100, 10_000):
        directory = tmp_path / f"history-{historical_count}"
        seed_material_history(directory, historical_count)
        instance = server.TableApp(directory)
        try:
            instance.flush_specifications()
            assert instance.turn(PROMPT)["adapter_calls"] == 1
            instance.flush_specifications()
            log = instance.harness.ensure_specification().event_log
            assert log.audit()["count"] == historical_count
            assert events(instance) == []
            instance.harness.adapter = Reported()
            original_digest = event_log.event_digest
            calls = 0

            def counted(value):
                nonlocal calls
                calls += 1
                return original_digest(value)

            # The history has already been opened and fully verified. Count
            # every logical and physical digest through the actual Table append.
            with monkeypatch.context() as counting:
                counting.setattr(event_log, "event_digest", counted)
                counting.setattr(specification_module, "event_digest", counted)
                reply = instance.turn(PROMPT)
                instance.flush_specifications()
            digest_counts[historical_count] = calls
            assert not reply.get("superseded") and reply["adapter_calls"] == 1
            entries = log.rows()
            assert len(entries) == historical_count + 1
            appended = entries[-1]["event"]
            assert appended["field"] == "host_reported_model"
            assert appended["new_value"]["model_id"] == "changed-host-revision"
            assert events(instance) == [appended]
            row = instance.harness.audit_log.rows()[-1]
            assert row["material_change_event_id"] == appended["event_id"]
            assert row["sitting_turn_ordinal"] == 2
        finally:
            instance.close()
    assert 0 < digest_counts[100] == digest_counts[10_000], digest_counts

