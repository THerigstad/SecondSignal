"""The authorized verified-tip cache retains an explicit full audit."""
from __future__ import annotations

import copy
import json
import os

import pytest

from secondsignal_harness import event_log
from secondsignal_harness.audit_log import canonical_row
from secondsignal_harness.event_log import MaterialChangeLog, SpecificationError, event_digest


def history(tmp_path):
    log = MaterialChangeLog(tmp_path / "changes.jsonl")
    for index in range(3):
        event = {"field": "setting", "old_value": index, "new_value": index + 1,
                 "requested_by": "operator", "authorized_by": "fixture",
                 "interval": {"from_turn": index + 1, "until_turn": None}, "reversed": False}
        event["event_id"] = event_digest(event)
        log.append(event)
    return log


def tamper_middle(log, *, preserve_mtime):
    original = log.path.read_bytes()
    stat = log.path.stat()
    lines = original.splitlines()
    entry = json.loads(lines[1])
    entry["event"]["new_value"] = 9
    lines[1] = canonical_row(entry).encode("utf-8")
    changed = b"\n".join(lines) + b"\n"
    assert len(changed) == len(original) and changed[-96:] == original[-96:]
    log.path.write_bytes(changed)
    if preserve_mtime is not None:
        os.utime(log.path, ns=(stat.st_atime_ns,
                              stat.st_mtime_ns if preserve_mtime else stat.st_mtime_ns + 1_000_000))


def test_hm2_unchanged_reads_reuse_tip_but_explicit_audit_checks_every_digest(tmp_path, monkeypatch):
    log = history(tmp_path)
    original, calls = event_log.event_digest, []
    def counted(value):
        calls.append(1)
        return original(value)
    monkeypatch.setattr(event_log, "event_digest", counted)
    first = log.rows()
    assert log.read(first[0]["event"]["event_id"]) == first[0]
    assert calls == []
    assert log.audit() == {"count": 3, "sha256": first[-1]["sha256"]}
    assert len(calls) == 6
    first[0]["event"]["new_value"] = "edited copy"
    assert log.rows()[0]["event"]["new_value"] == 1


def test_hm2_same_size_middle_change_invalidates_cached_history(tmp_path):
    log = history(tmp_path)
    tamper_middle(log, preserve_mtime=False)
    with pytest.raises(SpecificationError):
        log.rows()


def test_hm2_explicit_audit_detects_change_with_restored_cache_fingerprint(tmp_path):
    log = history(tmp_path)
    original = log.path.read_bytes()
    event = log.rows()[0]["event"]
    tamper_middle(log, preserve_mtime=True)
    # This deliberately demonstrates the documented metadata-cache limit.
    assert log.rows()[1]["event"]["new_value"] == 2
    with pytest.raises(SpecificationError):
        log.audit()
    # A known verification failure cannot fall back to the old matching cache.
    with pytest.raises(SpecificationError):
        log.rows()
    with pytest.raises(SpecificationError):
        log.read(event["event_id"])
    with pytest.raises(SpecificationError):
        log.append(event)
    log.path.write_bytes(original)
    assert log.rows()[0]["event"] == event


def test_hm2_idle_writer_does_not_hide_ordinary_same_size_external_edit(tmp_path):
    log = history(tmp_path)
    # No explicit timestamp manipulation: this must work with the cached
    # Windows write handle still open after the original appends.
    tamper_middle(log, preserve_mtime=None)
    with pytest.raises(SpecificationError):
        log.rows()


def test_hm2_committed_snapshot_cache_distinguishes_equal_python_scalars(tmp_path):
    from test_hm2_spec import make_spec

    from secondsignal_harness.spec import specification_hash

    spec, _, _ = make_spec(tmp_path)
    for original, changed in ((1, True), (1, 1.0), (0.0, -0.0)):
        document = spec.snapshot()
        document["cache_scalar_probe"] = original
        document["specification_hash"] = specification_hash(document)
        spec._storage.commit(document, [])
        tampered = copy.deepcopy(document)
        tampered["cache_scalar_probe"] = changed
        assert tampered == document  # Python equality is deliberately insufficient.
        with pytest.raises(SpecificationError):
            spec._storage.commit(tampered, [])
        assert spec.read_snapshot(document["specification_hash"]) == document
