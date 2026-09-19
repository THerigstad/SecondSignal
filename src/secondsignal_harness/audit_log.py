"""The audit log: the one thing the harness may write (ADR-0014; ADR-0029 (Proposed), rule 6).

A row is appended before anything is released, and the write is proven by
reading the row back by its id. JSON lines on disk when a path is given;
in memory otherwise (tests). Rows never carry a key; the harness plants no
secrets in them and ``tests/test_harness_contract.py`` asserts the absence
of a planted fake key from every row.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_JSON_NATIVE = (str, int, float, bool, type(None))


def _check_json_native(value: Any, path: str = "row") -> None:
    """Refuse anything that is not JSON-native (the sixth ADR-0020 (Proposed) correction, applied here too)."""
    if isinstance(value, _JSON_NATIVE):
        return
    if isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _check_json_native(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path}: non-string key {key!r}")
            _check_json_native(item, f"{path}.{key}")
        return
    raise TypeError(f"{path}: {type(value).__name__} is not JSON-native")


def canonical_row(row: dict[str, Any]) -> str:
    """The exact bytes a row id is computed from: sorted keys, no whitespace games."""
    _check_json_native(row)
    return json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class AuditLog:
    """Append-only rows, each with an id that is the SHA-256 of its canonical bytes."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self._rows: list[dict[str, Any]] = []
        if self.path is not None and self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._rows.append(json.loads(line))

    def append(self, row: dict[str, Any]) -> str:
        """Write one row and return its id only after the write can be read back."""
        body = dict(row)
        body.pop("row_id", None)
        row_id = hashlib.sha256(canonical_row(body).encode("utf-8")).hexdigest()
        body["row_id"] = row_id
        line = canonical_row(body)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
        self._rows.append(json.loads(line))
        if self.read(row_id) is None:
            raise RuntimeError("the audit row could not be read back after the write")
        return row_id

    def read(self, row_id: str) -> dict[str, Any] | None:
        if self.path is not None:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    candidate = json.loads(line)
                    if candidate.get("row_id") == row_id:
                        return dict(candidate)
            return None
        for candidate in self._rows:
            if candidate.get("row_id") == row_id:
                return dict(candidate)
        return None

    def rows(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._rows]

    def __len__(self) -> int:
        return len(self._rows)


__all__ = ["AuditLog", "canonical_row"]
