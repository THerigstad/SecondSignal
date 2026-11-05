"""Append-only material events with a verified chain and an independent head receipt.

The head receipt catches suffix truncation as well as changes inside the chain.
A writer able to replace both files can still forge history; this is evidence,
not a filesystem security boundary. Reads never repair or discard records.
The chain is checked at open and on external file changes. Internal appends
verify their new record; audit() explicitly rechecks the entire history.
Writes flush and verify operating-system-visible bytes, like the audit log;
a bounded cache reuses unbuffered write handles. They do not promise persistence through a power loss.
A writer that restores every observed file attribute and the same tail/head
can evade automatic cache invalidation; an explicit audit still checks bytes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import threading
from collections import Counter, OrderedDict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO

from .audit_log import canonical_row


class SpecificationError(ValueError):
    """A specification, its stamp or its durable history could not be verified."""


def event_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_row(value).encode("utf-8")).hexdigest()


def _file_identity(path: Path) -> tuple[int, int, int, int] | None:
    try:
        stat = path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns
    except FileNotFoundError:
        return None


_IDLE_WRITERS: OrderedDict[tuple[str, bool], BinaryIO] = OrderedDict()
_WRITER_LOCK = threading.Lock()
_MAX_IDLE_WRITERS = 32


def _stream_identity(stream: BinaryIO) -> tuple[int, int, int, int]:
    stat = os.fstat(stream.fileno())
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def _open_writer(path: Path, *, append: bool) -> BinaryIO:
    """Open lazily, permitting external replacement while a writer is idle."""
    flags = os.O_RDWR | (os.O_APPEND if append else 0)
    if sys.platform == "win32":  # sys.platform, not os.name, so mypy skips this branch off Windows
        import ctypes
        import msvcrt
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        close = kernel.CloseHandle
        close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
        # GENERIC_READ | GENERIC_WRITE; SHARE_READ | SHARE_WRITE | SHARE_DELETE;
        # OPEN_ALWAYS. Ordinary Python write handles deny Windows rename/delete.
        handle = create(str(path), 0xC0000000, 0x7, None, 4, 0x80, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            descriptor = msvcrt.open_osfhandle(handle, flags | os.O_BINARY)
        except BaseException:
            close(handle)
            raise
    else:
        descriptor = os.open(path, flags | os.O_CREAT, 0o666)
    try:
        return os.fdopen(descriptor, "r+b", buffering=0)
    except BaseException:
        os.close(descriptor)
        raise


def _return_writer(key: tuple[str, bool], stream: BinaryIO) -> None:
    discarded = []
    with _WRITER_LOCK:
        previous = _IDLE_WRITERS.pop(key, None)
        if previous is not None:
            discarded.append(previous)
        _IDLE_WRITERS[key] = stream
        while len(_IDLE_WRITERS) > _MAX_IDLE_WRITERS:
            discarded.append(_IDLE_WRITERS.popitem(last=False)[1])
    for retired in discarded:
        retired.close()


def _read_bytes(path: Path, identity: tuple[int, int, int, int], *, offset: int = 0,
                size: int = -1, stream: BinaryIO | None = None) -> bytes:
    """Reuse a verified open descriptor for bounded reads, without opening writers."""
    if stream is not None:
        if _stream_identity(stream) != identity:
            raise SpecificationError("verified file was replaced during read")
        stream.seek(offset)
        return stream.read(size)
    name = os.path.normcase(os.path.abspath(path))
    key = name, True
    with _WRITER_LOCK:
        cached = _IDLE_WRITERS.pop(key, None)
        if cached is None:
            key = name, False
            cached = _IDLE_WRITERS.pop(key, None)
    if cached is not None:
        try:
            if _stream_identity(cached) == identity:
                cached.seek(offset)
                data = cached.read(size)
            else:
                cached.close()
                cached = None
        except BaseException:
            if cached is not None:
                cached.close()
            raise
        if cached is not None:
            _return_writer(key, cached)
            return data
    with path.open("rb") as reader:
        reader.seek(offset)
        return reader.read(size)


@contextmanager
def _write_handle(path: Path, *, append: bool,
                  expected_identity: tuple[int, int, int, int] | None) -> Iterator[BinaryIO]:
    """Lease an unbuffered writer; at most 32 idle handles remain open.

    A checked-out handle is absent from the LRU and cannot be evicted. Existing
    per-log locks cover I/O; the cache lock only protects checkout and return.
    """
    key = os.path.normcase(os.path.abspath(path)), append
    with _WRITER_LOCK:
        stream = _IDLE_WRITERS.pop(key, None)
    try:
        if stream is not None and (expected_identity is None
                                   or _stream_identity(stream)[:2] != expected_identity[:2]):
            stream.close()
            stream = None
        if stream is None:
            stream = _open_writer(path, append=append)
        opened = _stream_identity(stream)
        if (expected_identity is not None and opened != expected_identity
                or expected_identity is None and opened[2] != 0):
            raise SpecificationError("verified file changed before write")
        yield stream
    except BaseException:
        if stream is not None:
            stream.close()
        raise
    else:
        _return_writer(key, stream)


class MaterialChangeLog:
    """Append-only events, using a verified tip between external changes.

    Logical event IDs bind their contents. The physical envelope links all
    sittings in write order, so independently staged records can be committed
    without changing the specification hash already stamped on their turn.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self.head_path = self.path.with_suffix(".head.json") if self.path else None
        self._entries: list[dict[str, Any]] = []
        self._head: dict[str, Any] = {"count": 0, "sha256": None}
        self._counts: Counter[str] = Counter()
        self._lock = threading.RLock()
        self._signature: Any = None
        self._revision = 0
        self._verified = False
        self.audit()

    def __deepcopy__(self, memo: dict[int, Any]) -> MaterialChangeLog:
        if self.path is not None:
            memo[id(self)] = self
            return self
        result = MaterialChangeLog()
        memo[id(self)] = result
        with self._lock:
            result._entries = copy.deepcopy(self._entries, memo)
            result._head = copy.deepcopy(self._head, memo)
            result._counts = self._counts.copy()
            result._revision = self._revision
            result._verified = self._verified
        return result

    def _disk_signature(self, *, event_stream: BinaryIO | None = None,
                        head_stream: BinaryIO | None = None) -> Any:
        if self.path is None:
            return None
        assert self.head_path is not None
        try:
            identity, head_identity = _file_identity(self.path), _file_identity(self.head_path)
            tail = b""
            if identity is not None:
                # Canonical envelopes end in their SHA-256. The bounded tail
                # also notices a changed tip when timestamps were preserved.
                tail = _read_bytes(self.path, identity, offset=max(0, identity[2] - 96),
                                   size=96, stream=event_stream)
            receipt = (_read_bytes(self.head_path, head_identity, stream=head_stream)
                       if head_identity is not None else None)
            return identity, head_identity, tail, receipt
        except (OSError, ValueError) as exc:
            raise SpecificationError("material event log metadata could not be read") from exc

    @staticmethod
    def _verify_entry(entry: Any, index: int, previous: str | None) -> None:
        if not isinstance(entry, dict) or set(entry) != {
            "sequence", "previous_event_sha256", "event", "sha256",
        }:
            raise SpecificationError("invalid material event envelope")
        if entry["sequence"] != index or entry["previous_event_sha256"] != previous:
            raise SpecificationError("material event chain link or order differs")
        body = {key: value for key, value in entry.items() if key != "sha256"}
        if entry["sha256"] != event_digest(body):
            raise SpecificationError("material event chain hash differs")
        event = entry["event"]
        if not isinstance(event, dict) or event.get("event_id") != event_digest({
            key: value for key, value in event.items() if key != "event_id"
        }):
            raise SpecificationError("material event content hash differs")

    def audit(self) -> dict[str, Any]:
        """Fully verify every event and its head, even if file metadata is unchanged."""
        with self._lock:
            self._verified = False
            before = self._disk_signature()
            if self.path is None:
                entries, head = self._entries, self._head
            else:
                assert self.head_path is not None
                exists, anchored = before[0] is not None, before[1] is not None
                if not exists and not anchored:
                    if self._entries:
                        raise SpecificationError("material event log and head receipt are missing")
                    entries, head = [], {"count": 0, "sha256": None}
                else:
                    if exists != anchored:
                        raise SpecificationError("material event log or head receipt is missing")
                    try:
                        raw = self.path.read_bytes()
                        if raw and not raw.endswith(b"\n"):
                            raise SpecificationError("material event log has an incomplete final record")
                        entries = [json.loads(line) for line in raw.splitlines()]
                        head = json.loads(before[3])
                    except (OSError, ValueError, TypeError, UnicodeError) as exc:
                        raise SpecificationError("material event log could not be read") from exc
            previous = None
            counts: Counter[str] = Counter()
            for index, entry in enumerate(entries, 1):
                self._verify_entry(entry, index, previous)
                previous = entry["sha256"]
                counts[entry["event"]["event_id"]] += 1
            if head != {"count": len(entries), "sha256": previous}:
                raise SpecificationError("material event log differs from its head receipt")
            after = self._disk_signature()
            if before != after:
                raise SpecificationError("material event log changed during verification")
            self._entries, self._head, self._counts = entries, dict(head), counts
            self._signature = after
            self._verified = True
            self._revision += 1
            return dict(self._head)

    def _ensure_verified(self) -> None:
        try:
            if self._verified and self._disk_signature() == self._signature:
                return
        except SpecificationError:
            self._verified = False
            raise
        self.audit()

    @property
    def verification_revision(self) -> int:
        """Changes on a full verification, not on our verified internal appends."""
        with self._lock:
            self._ensure_verified()
            return self._revision

    def require_events(self, required: Mapping[str, int]) -> int:
        """Check content IDs and return the exact verified revision checked."""
        with self._lock:
            self._ensure_verified()
            if any(count > self._counts[event_id] for event_id, count in required.items()):
                raise SpecificationError("specification material event has no durable backing")
            return self._revision

    def rows(self) -> list[dict[str, Any]]:
        with self._lock:
            self._ensure_verified()
            return copy.deepcopy(self._entries)

    def read(self, event_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._ensure_verified()
            for entry in reversed(self._entries):
                if entry["event"]["event_id"] == event_id:
                    return copy.deepcopy(entry)
            return None

    def append(self, event: dict[str, Any]) -> str:
        with self._lock:
            self._ensure_verified()
            self._verified = False
            copied = copy.deepcopy(event)
            if copied.get("event_id") != event_digest({
                key: value for key, value in copied.items() if key != "event_id"
            }):
                raise SpecificationError("material event content hash differs")
            body = {"sequence": self._head["count"] + 1,
                    "previous_event_sha256": self._head["sha256"], "event": copied}
            entry = {**body, "sha256": event_digest(body)}
            head = {"count": self._head["count"] + 1, "sha256": entry["sha256"]}
            if self.path is not None:
                assert self.head_path is not None
                self.path.parent.mkdir(parents=True, exist_ok=True)
                line = (canonical_row(entry) + "\n").encode("utf-8")
                before_identity = self._signature[0]
                before_size = before_identity[2] if before_identity is not None else 0
                if self._disk_signature() != self._signature:
                    raise SpecificationError("material event log changed before append")
                with _write_handle(self.path, append=True, expected_identity=before_identity) as stream:
                    opened_identity = _stream_identity(stream)
                    start = stream.seek(0, os.SEEK_END)
                    if start != before_size:
                        raise SpecificationError("material event log changed before append")
                    stream.write(line)
                    stream.flush()
                    stream.seek(start)
                    written = stream.read(len(line) + 1)
                    if written != line:
                        raise SpecificationError("material event append could not be verified")
                    # Keep the independent head receipt, including its
                    # truncation protection, and prove only the new bytes.
                    receipt = (canonical_row(head) + "\n").encode("utf-8")
                    with _write_handle(self.head_path, append=False,
                                       expected_identity=self._signature[1]) as head_stream:
                        head_identity = _stream_identity(head_stream)
                        head_stream.seek(0)
                        head_stream.write(receipt)
                        head_stream.truncate()
                        head_stream.flush()
                        head_stream.seek(0)
                        if head_stream.read(len(receipt) + 1) != receipt:
                            raise SpecificationError("material event head could not be verified")
                        candidate = json.loads(written)
                        self._verify_entry(candidate, head["count"], self._head["sha256"])
                        signature = self._disk_signature(event_stream=stream, head_stream=head_stream)
                        if (signature[0] is None or signature[0][:2] != opened_identity[:2]
                                or signature[0][2] != start + len(line)
                                or signature[1] is None or signature[1][:2] != head_identity[:2]
                                or json.loads(signature[3]) != head):
                            raise SpecificationError("material event append or head changed")
                        self._signature = signature
            else:
                self._verify_entry(entry, head["count"], self._head["sha256"])
            self._entries.append(entry)
            self._head = head
            self._counts[copied["event_id"]] += 1
            self._verified = True
            return str(entry["sha256"])


__all__ = ["MaterialChangeLog", "SpecificationError", "event_digest"]
