"""H1: append-only byte receipts, including dropped writes and bounded I/O."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from secondsignal_harness.audit_log import AuditLog, canonical_row


class Handle:
    def __init__(self, inner, write=None, reads=None):
        self.inner, self.write_filter, self.reads = inner, write, reads

    def __enter__(self):
        self.inner.__enter__()
        return self

    def __exit__(self, *args):
        return self.inner.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def write(self, text):
        return self.inner.write(self.write_filter(text) if self.write_filter else text)

    def read(self, size=-1):
        if self.reads is not None:
            self.reads.append(size)
            assert 0 <= size <= 4096, "tail proof requested unbounded I/O"
        return self.inner.read(size)


@pytest.mark.parametrize("fault", [
    "drop", "drop_duplicate", "truncate", "missing_newline", "wrong_tail", "forged_id", "spaces",
])
def test_h1_write_proof_rejects_a_write_that_did_not_land(tmp_path, monkeypatch, fault):
    """Missing, incomplete, replaced and noncanonical appends cannot produce a receipt."""
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    row = {"text": "Okay.", "index": 1}
    log.append(row)
    old = path.read_text(encoding="utf-8")
    original = Path.open

    def corrupt(text):
        if fault in {"drop", "drop_duplicate"}:
            return ""
        if fault == "truncate":
            return text[:len(text) // 2]
        if fault == "missing_newline":
            return text[:-1]
        if fault == "wrong_tail":
            return old
        if fault == "forged_id":
            body = json.loads(text)
            body["index"] = 99
            return canonical_row(body) + "\n"
        return " " + text

    def opening(self, mode="r", *args, **kwargs):
        inner = original(self, mode, *args, **kwargs)
        return Handle(inner, write=corrupt) if self == path and mode == "a" else inner

    monkeypatch.setattr(Path, "open", opening)
    with pytest.raises(RuntimeError, match="could not be read back"):
        log.append(row if fault == "drop_duplicate" else {**row, "index": 2})
    assert len(log) == 1


def test_h1_tail_reads_are_bounded_independently_of_log_size(tmp_path, monkeypatch):
    """A 20,000-row and 40,000-row log require exactly the same bounded receipt reads."""
    original = Path.open
    measurements = []
    for count in (20_000, 40_000):
        path = tmp_path / f"week-{count}.jsonl"
        seed = {"text": "Okay.", "padding": "x" * 256}
        seed["row_id"] = hashlib.sha256(canonical_row(seed).encode()).hexdigest()
        line = (canonical_row(seed) + "\n").encode()
        with original(path, "wb") as handle:
            for _ in range(count):
                handle.write(line)
        log = AuditLog(path)
        assert len(log) == count
        reads = []

        def opening(self, mode="r", *args, **kwargs):
            inner = original(self, mode, *args, **kwargs)
            return Handle(inner, reads=reads) if self == path and mode == "rb" else inner

        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", opening)
            row_id = log.append({"text": "Okay.", "index": 7})
        body = log.rows()[-1]
        assert body["row_id"] == row_id
        assert 0 < sum(reads) <= len(canonical_row(body).encode()) + 3
        measurements.append(reads)
    assert measurements[0] == measurements[1]


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_h1_existing_log_bytes_and_ids_survive_appends(tmp_path, newline):
    """Old LF/CRLF bytes and canonical identifiers remain identical after a Unicode append."""
    path = tmp_path / "audit.jsonl"
    rows = []
    for index in range(3):
        body = {"index": index, "text": "Okay."}
        body["row_id"] = hashlib.sha256(canonical_row(body).encode()).hexdigest()
        rows.append(body)
    before = newline.join(canonical_row(row).encode() for row in rows) + newline
    path.write_bytes(before)
    log = AuditLog(path)
    row_id = log.append({"text": "Σήμερα " * 2400})
    assert path.read_bytes().startswith(before)
    assert all(log.read(row["row_id"]) == row for row in rows)
    added = log.read(row_id)
    body = dict(added)
    body.pop("row_id")
    assert row_id == hashlib.sha256(canonical_row(body).encode()).hexdigest()
    assert AuditLog(path).rows() == [*rows, added]


def test_h1_append_does_not_call_historical_lookup(tmp_path, monkeypatch):
    """Both disk and memory appends succeed without consulting read(row_id)."""
    for log in (AuditLog(tmp_path / "audit.jsonl"), AuditLog()):
        def forbidden(*args):
            raise AssertionError("historical scan reached")
        monkeypatch.setattr(log, "read", forbidden)
        row_id = log.append({"text": "Okay."})
        assert log.rows()[0]["row_id"] == row_id
