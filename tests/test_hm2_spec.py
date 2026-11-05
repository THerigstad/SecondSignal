"""HM2: exact components, full hash coverage and durable change evidence."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from secondsignal import load_roster, roster_hash
from secondsignal.jr import payload_hash
from secondsignal_harness import AdapterReply, CodexStore, FakeAdapter
from secondsignal_harness.configuration import configuration
from secondsignal_harness.event_log import MaterialChangeLog, SpecificationError, event_digest
from secondsignal_harness.spec import (
    COMPONENT_NAMES,
    HarnessSpecification,
    SpecificationStampError,
    specification_hash,
    validate_specification,
)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_NAMES = (
    "orchestration and planning", "context and memory", "tool and action interfaces",
    "operational knowledge", "sandboxing", "permission model",
    "verification, evaluation and observability", "execution runtime and lifecycle management",
)


def make_spec(tmp_path=None, *, model="requested-model", runtime=None, adapter_url=None):
    roster, codexes, adapter = load_roster(), CodexStore(ROOT / "docs/codex"), FakeAdapter(model_id=model)
    if adapter_url is not None:
        adapter.url = adapter_url
    config = configuration(adapter=adapter, reply=None, prompt_hash=None,
                           record={"roster_hash": roster_hash(roster)}, roster=roster, codexes=codexes,
                           presentation={}, chosen_names={}, max_turns=12, max_tokens=600, retries=1)
    config["harness_controls"] = {"operator_circle": False, "declared_preferences": {}}
    spec = HarnessSpecification(config, adapter=adapter, roster=roster, codexes=codexes,
                                runtime=runtime, initial_state={"latch": "none", "holds": []},
                                audit_path=tmp_path / "audit.jsonl" if tmp_path else None)
    return spec, config, adapter


def leaf_and_container_paths(value, prefix=()):
    """Discover every field, including empty containers and future additions."""
    if isinstance(value, dict):
        for key, item in value.items():
            if prefix == () and key == "specification_hash":
                continue
            path = (*prefix, key)
            yield path
            yield from leaf_and_container_paths(item, path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            path = (*prefix, index)
            yield path
            yield from leaf_and_container_paths(item, path)


def table_runtime_fixture():
    from apps.talking_table import server

    # Read the actual settings declaration, not a second handwritten key list.
    tree = ast.parse((ROOT / "apps/talking_table/server.py").read_text(encoding="utf-8"))
    declaration = next(node.value for node in ast.walk(tree)
                       if isinstance(node, ast.Assign) and any(
                           isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                           and target.value.id == "self" and target.attr == "settings"
                           for target in node.targets) and isinstance(node.value, ast.Dict))
    settings = ast.literal_eval(declaration)
    app = SimpleNamespace(settings=settings, _latch_owned=True, computer={"scope": "computer"},
                          paired=set(), token_ready=False, phone_server=None,
                          key="", voice_key="", lights_key="")
    return server.TableApp._specification_runtime(app)


def specimen():
    spec, config, _ = make_spec(runtime=table_runtime_fixture(), adapter_url="https://fixture.example/v1/chat")
    spec.observe_model(AdapterReply("text", "reported-model"), ordinal=1)
    row = {}
    spec.stamp(row, ordinal=1)
    config["generation"]["max_tokens"] += 1
    spec.change(config, actor="operator", authorization="explicit fixture control", ordinal=2)
    spec.end({"reason": "quiet_timeout", "accepted_turns": 2}, ordinal=2)
    return spec.snapshot()


_HASH_SPECIMEN = specimen()
_HASH_PATHS = list(leaf_and_container_paths(_HASH_SPECIMEN))


def test_hm2_every_field_is_hash_bound():
    """No allowlist can silently omit a future specification field."""
    original = _HASH_SPECIMEN
    original_hash = specification_hash(original)
    unchanged = []
    for path in _HASH_PATHS:
        changed = copy.deepcopy(original)
        parent = changed
        for key in path[:-1]:
            parent = parent[key]
        value = parent[path[-1]]
        if isinstance(value, dict):
            parent[path[-1]] = {**value, "future_field": "changed"}
        elif isinstance(value, list):
            parent[path[-1]] = [*value, "changed"]
        elif isinstance(value, bool):
            parent[path[-1]] = not value
        elif isinstance(value, int):
            parent[path[-1]] = value + 1
        elif value is None:
            parent[path[-1]] = "now-present"
        else:
            parent[path[-1]] = str(value) + " changed"
        if specification_hash(changed) == original_hash:
            unchanged.append("/".join(map(str, path)))
    assert not unchanged, f"Specification fields are not hash-bound: {unchanged}"


def test_hm2_hash_uses_existing_payload_hash_and_only_its_volatile_rule():
    spec, _, _ = make_spec()
    original = spec.snapshot()
    body = {key: value for key, value in original.items() if key != "specification_hash"}
    assert original["specification_hash"] == payload_hash(body, "")
    assert specification_hash({**original, "ranked": [{"score": 9}]}) == original["specification_hash"]
    assert specification_hash({**original, "future_field": "bound"}) != original["specification_hash"]
    changed = copy.deepcopy(original)
    changed["records"]["run_start"]["ranked"] = [1]
    assert specification_hash(changed) != original["specification_hash"]


def test_hm2_hash_is_stable_across_equivalent_runs_and_json_key_order():
    first, _, _ = make_spec()
    second, _, _ = make_spec()
    assert first.snapshot() == second.snapshot()
    reversed_keys = dict(reversed(list(first.snapshot().items())))
    assert specification_hash(reversed_keys) == second.snapshot()["specification_hash"]


def component_locations(document):
    return [document["records"]["release"]["components"],
            document["records"]["run_start"]["components"],
            document["active_configuration"]["components"],
            document["records"]["run_end"]["configuration"]["components"]]


def rehash(document):
    document["specification_hash"] = specification_hash(document)
    return document


def test_hm2_every_emission_keeps_all_eight_exact_components():
    assert COMPONENT_NAMES == EXPECTED_NAMES
    document = specimen()
    for components in component_locations(document):
        assert tuple(component["name"] for component in components) == EXPECTED_NAMES
        assert [component["status"] for component in components] == [
            "implemented", "partial", "not-implemented", "implemented",
            "not-implemented", "implemented", "implemented", "partial",
        ]
    validate_specification(document)


@pytest.mark.parametrize("location", range(4))
@pytest.mark.parametrize("mutation", ["missing", "renamed", "abbreviated", "reordered", "duplicate"])
def test_hm2_component_identity_and_order_are_enforced(location, mutation):
    changed = specimen()
    components = component_locations(changed)[location]
    if mutation == "missing":
        components.pop()
    elif mutation == "renamed":
        components[0]["name"] = "planning"
    elif mutation == "abbreviated":
        components[6]["name"] = "verification"
    elif mutation == "reordered":
        components.reverse()
    else:
        components[1] = copy.deepcopy(components[0])
    with pytest.raises(SpecificationError, match="eight components"):
        validate_specification(rehash(changed))


@pytest.mark.parametrize("location", range(4))
@pytest.mark.parametrize("component", [1, 2, 4, 7])
@pytest.mark.parametrize("reason", ["", " ", None])
def test_hm2_partial_and_absent_components_require_reasons(location, component, reason):
    changed = specimen()
    component_locations(changed)[location][component]["reason"] = reason
    with pytest.raises(SpecificationError, match="reason"):
        validate_specification(rehash(changed))


@pytest.mark.parametrize("record", ["release", "declared_changeable", "run_start", "material_change_events", "run_end"])
def test_hm2_no_record_may_be_omitted(record):
    document = make_spec()[0].snapshot()
    del document["records"][record]
    with pytest.raises(SpecificationError, match="five"):
        validate_specification(rehash(document))


def test_hm2_declared_changeable_is_authorized_and_models_have_nothing():
    document = make_spec()[0].snapshot()
    declared = document["records"]["declared_changeable"]
    assert declared["personas_and_model_calls"] == []
    assert {entry["field"] for entry in declared["operator"]} >= {
        "host_terms", "latch_clearance", "pairing_scopes", "adapter_and_model",
    }
    assert all(entry["authorization"] and entry["actor"] and entry["evidence"]
               for entry in declared["operator"])
    declared["personas_and_model_calls"].append("change_gate")
    with pytest.raises(SpecificationError, match="no change authority"):
        validate_specification(rehash(document))
    declared["personas_and_model_calls"] = []
    declared["operator"][0]["authorization"] = ""
    with pytest.raises(SpecificationError, match="authorization"):
        validate_specification(rehash(document))


def test_hm2_governing_files_are_complete_actual_sha256s_and_versions_are_sourced():
    spec, config, _ = make_spec()
    document = spec.snapshot()
    files = document["records"]["release"]["governing_files"]
    expected = set()
    for directory, pattern in (("docs/codex", "*.md"), ("src/secondsignal/packs", "*.json"),
                               ("src/secondsignal/profiles", "*.json")):
        expected.update(path.relative_to(ROOT).as_posix() for path in (ROOT / directory).glob(pattern))
    expected.add("docs/codex/house-block.lock.json")
    expected.update("src/secondsignal/" + name for name in (
        "corrected_confusables.json", "reviewed_skeleton_remainder.json", "crisis_words.txt", "everyday_words.txt"))
    assert set(files) == expected
    for path, digest in files.items():
        assert digest == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    for component in document["records"]["release"]["components"]:
        assert component["versions"]["harness"] == config["harness_version"]
        assert component["versions"]["policy"] == config["policy_version"]
        assert all((ROOT / path).is_file() for path in component["evidence"])


def test_hm2_requested_and_reported_model_round_trip_separately(tmp_path):
    spec, _, _ = make_spec(tmp_path, model="requested-alias")
    assert spec.snapshot()["model_pairing"]["host_reported"]["model_id"] is None
    spec.observe_model(AdapterReply("text", "host-revision", model_version="2026.11"), ordinal=1)
    document = spec.snapshot()
    assert document["model_pairing"]["requested"]["model_id"] == "requested-alias"
    assert document["model_pairing"]["host_reported"] == {
        "model_id": "host-revision", "model_version": "2026.11",
    }
    spec.commit()
    assert spec.read_snapshot(document["specification_hash"]) == document
    assert json.loads(json.dumps(document))["model_pairing"] == document["model_pairing"]
    assert document["records"]["material_change_events"] == []


def test_hm2_initial_gate_observation_remains_unknown_and_later_identity_is_not_invented(tmp_path):
    spec, _, _ = make_spec(tmp_path)
    row = {}
    spec.stamp(row, ordinal=1)
    spec.commit()
    initial_hash = row["specification_hash"]
    spec.observe_model(AdapterReply("text", "host-revision"), ordinal=2)
    current = spec.snapshot()
    assert current["records"]["run_start"]["model_pairing"]["host_reported"]["model_id"] is None
    assert current["model_pairing"]["host_reported"]["model_id"] == "host-revision"
    event = current["records"]["material_change_events"][-1]
    assert event["field"] == "host_reported_model"
    assert event["old_value"]["model_id"] is None and event["new_value"]["model_id"] == "host-revision"
    assert event["interval"] == {"from_turn": 2, "until_turn": None}
    assert spec.read_snapshot(initial_hash)["model_pairing"]["host_reported"]["model_id"] is None


def test_hm2_five_unchanged_fake_turn_stamps_share_one_hash_and_no_events():
    spec, config, adapter = make_spec()
    rows = []
    for ordinal in range(1, 6):
        spec.change(config, adapter=adapter, actor="caller", authorization="explicit setup", ordinal=ordinal)
        spec.observe_model(adapter.complete("", [], max_tokens=1), ordinal=ordinal)
        row = {}
        spec.stamp(row, ordinal=ordinal)
        spec.assert_row(row)
        rows.append(row)
    assert [row["sitting_turn_ordinal"] for row in rows] == [1, 2, 3, 4, 5]
    assert len({row["specification_hash"] for row in rows}) == 1
    assert all(row["material_change_event_id"] is None for row in rows)
    assert spec.snapshot()["records"]["material_change_events"] == []


@pytest.mark.parametrize("field,value", [("specification_hash", "0" * 64),
                                        ("sitting_turn_ordinal", 0), ("material_change_event_id", "wrong")])
def test_hm2_mismatched_stamps_raise_hard_failure(field, value):
    spec = make_spec()[0]
    row = {}
    spec.stamp(row, ordinal=1)
    row[field] = value
    with pytest.raises(SpecificationStampError):
        spec.assert_row(row)


def test_hm2_model_and_configuration_changes_close_intervals_without_rewriting(tmp_path):
    spec, config, adapter = make_spec(tmp_path)
    spec.observe_model(AdapterReply("text", "host-a"), ordinal=1)
    row = {}
    spec.stamp(row, ordinal=1)
    spec.observe_model(AdapterReply("text", "host-b"), ordinal=2)
    first = copy.deepcopy(spec.snapshot()["records"]["material_change_events"])
    spec.observe_model(AdapterReply("text", "host-a"), ordinal=3)
    events = spec.snapshot()["records"]["material_change_events"]
    assert events[:len(first)] == first
    assert events[-2]["kind"] == "interval_end" and events[-2]["interval"]["until_turn"] == 3
    assert events[-2]["reversed"] is True
    assert events[-1]["reversed"] is False
    assert events[-1]["reverses_event_id"] == first[0]["event_id"]
    config["generation"]["max_tokens"] = 601
    adapter.model_id = "new-requested-model"
    spec.change(config, adapter=adapter, actor="operator", authorization={"scope": "computer"}, ordinal=4)
    snapshot = spec.snapshot()
    assert snapshot["model_pairing"]["requested"]["model_id"] == "new-requested-model"
    assert snapshot["model_pairing"]["host_reported"]["model_id"] is None
    assert {event["field"] for event in snapshot["records"]["material_change_events"]} >= {
        "host_reported_model", "component_configuration", "requested_model",
    }
    spec.end({"reason": "quiet_timeout"}, ordinal=4)
    ending = spec.snapshot()
    assert ending["records"]["run_end"]["outcome"] == {"reason": "quiet_timeout"}
    assert ending["records"]["run_end"]["final_turn_ordinal"] == 4
    assert ending["records"]["material_change_events"][:len(events)] == events
    spec.commit()
    stored = spec.event_log.rows()
    assert [entry["event"] for entry in stored] == ending["records"]["material_change_events"]
    assert spec.read_snapshot(ending["specification_hash"]) == ending


def test_hm2_fork_discards_canceled_work_and_commits_shared_pending_events_only_once(tmp_path):
    spec, _, _ = make_spec(tmp_path)
    canceled = spec.fork()
    canceled.record_change("discarded", False, True, actor="caller", authorization="test", ordinal=1)
    assert spec.snapshot()["records"]["material_change_events"] == []
    assert spec.event_log.rows() == []
    spec.record_change("host_terms", "old", "new", actor="operator", authorization="token", ordinal=1)
    next_turn = spec.fork()
    next_turn.record_change("pairing", [], ["phone"], actor="operator", authorization="pairing code", ordinal=2)
    spec.commit()
    next_turn.commit()
    next_turn.commit()
    rows = spec.event_log.rows()
    assert [row["event"]["field"] for row in rows] == ["host_terms", "pairing"]
    assert rows[1]["previous_event_sha256"] == rows[0]["sha256"]


def test_hm2_new_run_resets_records_and_reuses_storage_without_reads(tmp_path, monkeypatch):
    spec, config, adapter = make_spec(tmp_path)
    spec.record_change("host_terms", "old", "new", actor="operator", authorization="token", ordinal=1)
    spec.commit()
    roster = load_roster()
    def forbidden(*args, **kwargs):
        raise AssertionError("new sitting read a log")
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    fresh = spec.new_run(config, adapter=adapter, roster=roster, codexes=CodexStore(ROOT / "docs/codex"))
    assert fresh.event_log is spec.event_log
    assert fresh.snapshot()["records"]["material_change_events"] == []
    assert fresh.snapshot()["records"]["run_end"] == {}


def logged_events(tmp_path):
    log = MaterialChangeLog(tmp_path / "events.jsonl")
    for index in range(3):
        event = {"field": "setting", "old_value": index, "new_value": index + 1,
                 "requested_by": "operator", "authorized_by": "fixture",
                 "interval": {"from_turn": index + 1, "until_turn": None}, "reversed": False}
        event["event_id"] = event_digest(event)
        log.append(event)
    return log


@pytest.mark.parametrize("mutation", ["rewrite", "remove_first", "remove_middle", "remove_last", "remove_all", "reorder"])
@pytest.mark.parametrize("reader", ["rows", "read", "reopen"])
def test_hm2_chain_detects_rewrite_removal_order_and_suffix_truncation(tmp_path, mutation, reader):
    log = logged_events(tmp_path)
    original = log.rows()
    lines = log.path.read_text(encoding="utf-8").splitlines()
    if mutation == "rewrite":
        changed = json.loads(lines[1])
        changed["event"]["new_value"] = "forged"
        lines[1] = json.dumps(changed)
    elif mutation == "remove_first":
        del lines[0]
    elif mutation == "remove_middle":
        del lines[1]
    elif mutation == "remove_last":
        lines.pop()
    elif mutation == "remove_all":
        lines = []
    else:
        lines.reverse()
    log.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
    with pytest.raises(SpecificationError):
        if reader == "read":
            log.read(original[0]["event"]["event_id"])
        elif reader == "reopen":
            MaterialChangeLog(log.path).rows()
        else:
            log.rows()


def test_hm2_event_interface_has_no_update_or_delete_and_read_copies_are_detached(tmp_path):
    log = logged_events(tmp_path)
    assert not hasattr(log, "update") and not hasattr(log, "delete")
    rows = log.rows()
    rows[0]["event"]["new_value"] = "edited copy"
    assert log.rows()[0]["event"]["new_value"] == 1


def test_hm2_snapshot_read_verifies_chain_even_when_requested_snapshot_exists(tmp_path):
    spec, _, _ = make_spec(tmp_path)
    spec.record_change("host_terms", "old", "new", actor="operator", authorization="token", ordinal=1)
    spec.commit()
    digest = spec.snapshot()["specification_hash"]
    spec.event_log.path.write_text("", encoding="utf-8", newline="\n")
    with pytest.raises(SpecificationError):
        spec.read_snapshot(digest)



def test_hm2_future_changes_are_not_stamped_on_an_earlier_turn():
    spec = make_spec()[0]
    spec.record_change("host_terms", "old", "new", actor="operator", authorization="token", ordinal=2)
    first = spec.snapshot()["records"]["material_change_events"][-1]["event_id"]
    spec.record_change("host_terms", "new", "old", actor="operator", authorization="token", ordinal=4)
    reversing = spec.snapshot()["records"]["material_change_events"][-1]["event_id"]
    assert [spec.event_in_force(n) for n in (1, 2, 3, 4, 5)] == [None, first, first, reversing, reversing]
    row = {}
    spec.stamp(row, ordinal=1)
    assert row["material_change_event_id"] is None
    spec.assert_row(row)
    row["material_change_event_id"] = reversing
    with pytest.raises(SpecificationError, match="material event"):
        spec.assert_row(row)


def test_hm2_request_change_closes_the_old_host_identity_interval():
    spec, config, adapter = make_spec()
    spec.observe_model(AdapterReply("text", "host-a"), ordinal=1)
    spec.stamp({}, ordinal=1)
    spec.observe_model(AdapterReply("text", "host-b"), ordinal=2)
    old_id = spec.snapshot()["records"]["material_change_events"][-1]["event_id"]
    adapter.model_id = "another-request"
    spec.change(config, adapter=adapter, actor="operator", authorization="settings", ordinal=3)
    spec.stamp({}, ordinal=3)
    spec.observe_model(AdapterReply("text", "host-c"), ordinal=4)
    events = spec.snapshot()["records"]["material_change_events"]
    closure = next(event for event in events if event.get("closes_event_id") == old_id)
    assert closure["interval"] == {"from_turn": 2, "until_turn": 3}
    reset = next(event for event in events if event["field"] == "requested_model")
    assert reset["old_value"]["host_reported"]["model_id"] == "host-b"
    assert reset["new_value"]["host_reported"]["model_id"] is None
    assert events[-1]["old_value"]["model_id"] is None
    assert events[-1]["new_value"]["model_id"] == "host-c"
    assert events[-1]["interval"]["from_turn"] == 4


@pytest.mark.parametrize("mutation", ["missing_both", "shorter_consistent_history"])
@pytest.mark.parametrize("operation", ["read", "commit"])
def test_hm2_snapshots_anchor_event_history_even_if_event_head_is_replaced(tmp_path, mutation, operation):
    spec, _, _ = make_spec(tmp_path)
    spec.record_change("host_terms", "old", "new", actor="operator", authorization="token", ordinal=1)
    spec.record_change("pairing", [], ["phone"], actor="operator", authorization="code", ordinal=2)
    spec.commit()
    digest = spec.snapshot()["specification_hash"]
    log = spec.event_log
    if mutation == "missing_both":
        # Keep all evidence on disk: removing both names is modelled by moving
        # the files aside, never deleting an artifact.
        log.path.rename(tmp_path / "removed-events.jsonl")
        log.head_path.rename(tmp_path / "removed-head.json")
    else:
        first = log.rows()[0]
        log.path.write_text(json.dumps(first) + "\n", encoding="utf-8", newline="\n")
        log.head_path.write_text(json.dumps({"count": 1, "sha256": first["sha256"]}) + "\n",
                                 encoding="utf-8", newline="\n")
    with pytest.raises(SpecificationError):
        if operation == "read":
            spec.read_snapshot(digest)
        else:
            spec.commit()



def test_hm2_merging_an_accepted_observation_preserves_new_controls_without_duplicate_events(tmp_path):
    base, _, _ = make_spec(tmp_path)
    base.observe_model(AdapterReply("text", "host-a"), ordinal=1)
    base.stamp({}, ordinal=1)
    base.commit()
    working, latest = base.fork(), base.fork()
    working.observe_model(AdapterReply("text", "host-b"), ordinal=2)
    working.stamp({}, ordinal=2)
    working.commit()
    latest.record_change("pairing", [], ["phone"], actor="operator", authorization="code", ordinal=3)
    pairing_id = latest.snapshot()["records"]["material_change_events"][-1]["event_id"]
    latest.merge_model_observation(working, ordinal=2)
    latest.commit()
    document = latest.snapshot()
    assert document["model_pairing"]["host_reported"]["model_id"] == "host-b"
    assert document["active_configuration"]["controls"]["pairing"] == ["phone"]
    assert latest.event_in_force(3) == pairing_id
    host_events = [row for row in latest.event_log.rows() if row["event"]["field"] == "host_reported_model"]
    assert len(host_events) == 1
    assert latest.read_snapshot(document["specification_hash"]) == document



@pytest.mark.parametrize("mutation", ["missing", "truncated", "older_prefix"])
def test_hm2_commit_refuses_lost_cached_specification_snapshots(tmp_path, mutation):
    spec, _, _ = make_spec(tmp_path)
    spec.commit()
    spec.observe_model(AdapterReply("text", "reported-model"), ordinal=1)
    spec.commit()
    path = tmp_path / "audit.specifications.jsonl"
    if mutation == "missing":
        path.rename(tmp_path / "removed-specifications.jsonl")
    elif mutation == "truncated":
        path.write_text("", encoding="utf-8", newline="\n")
    else:
        first = path.read_text(encoding="utf-8").splitlines()[0]
        path.write_text(first + "\n", encoding="utf-8", newline="\n")
    with pytest.raises(SpecificationError):
        spec.commit()


def test_hm2_missing_vendor_model_evidence_is_not_a_reported_identity():
    spec = make_spec()[0]
    reply = AdapterReply("text", "requested-fallback")
    # The additive evidence flag leaves historical H1 model_id behavior intact.
    object.__setattr__(reply, "model_id_reported", False)
    spec.observe_model(reply, ordinal=1)
    assert spec.snapshot()["model_pairing"]["host_reported"] == {
        "model_id": None, "model_version": None,
    }



def test_hm2_transport_endpoint_binds_hosts_and_paths_without_credentials_or_queries():
    first, _, _ = make_spec(adapter_url="https://user:password@one.example/v1/chat?api_key=QUERY_SECRET#fragment")
    same, _, _ = make_spec(adapter_url="https://another:credential@one.example/v1/chat?other=DIFFERENT#another")
    host, _, _ = make_spec(adapter_url="https://two.example/v1/chat")
    route, _, _ = make_spec(adapter_url="https://one.example/v2/chat")
    assert first.snapshot()["specification_hash"] == same.snapshot()["specification_hash"]
    assert first.snapshot()["specification_hash"] != host.snapshot()["specification_hash"]
    assert first.snapshot()["specification_hash"] != route.snapshot()["specification_hash"]
    metadata = first.configuration["transport_endpoint"]
    assert metadata == {"scheme": "https", "host": "one.example", "port": None,
                        "path": "/v1/chat", "path_sha256": hashlib.sha256(b"/v1/chat").hexdigest()}
    serialized = json.dumps(first.snapshot())
    for omitted in ("user:password", "QUERY_SECRET", "api_key", "fragment"):
        assert omitted not in serialized


def test_hm2_endpoint_change_resets_observed_identity_and_is_material():
    spec, config, adapter = make_spec(adapter_url="https://one.example/v1/chat")
    spec.observe_model(AdapterReply("text", "reported-model"), ordinal=1)
    spec.stamp({}, ordinal=1)
    adapter.url = "https://two.example/v1/chat"
    spec.change(config, adapter=adapter, actor="operator", authorization="explicit endpoint", ordinal=2)
    document = spec.snapshot()
    assert document["model_pairing"]["host_reported"]["model_id"] is None
    event = document["records"]["material_change_events"][-1]
    assert event["field"] == "requested_model"
    assert event["old_value"]["transport_endpoint"]["host"] == "one.example"
    assert event["new_value"]["transport_endpoint"]["host"] == "two.example"


def test_hm2_credential_shaped_endpoint_path_is_bound_but_not_copied():
    spec, _, _ = make_spec(adapter_url="https://one.example/v1/sk-PLANTED-KEY/chat")
    assert spec.configuration["transport_endpoint"]["path"] is None
    assert "sk-PLANTED-KEY" not in json.dumps(spec.snapshot())
    assert spec.configuration["transport_endpoint"]["path_sha256"] == hashlib.sha256(
        b"/v1/sk-PLANTED-KEY/chat").hexdigest()
