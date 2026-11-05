"""Validated provenance headers for newly emitted evaluation results.

Policy-only and mixed-configuration measurements explicitly declare the absent
marker: they do not claim one harness specification was in force. Historical
reports remain historical bytes; these readers reject an unlabelled new file.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ABSENT_SPECIFICATION = "absent"
_HEADER_PREFIX = "<!-- secondsignal_harness.results.header.v1: "
_HEADER_SUFFIX = " -->"
_SHA256 = re.compile(r"[0-9a-f]{64}")


def result_header(specification_hash: str) -> dict[str, str]:
    """Require an explicit hash or absent marker; never infer reproducibility."""
    if not isinstance(specification_hash, str) or (
        specification_hash != ABSENT_SPECIFICATION and not _SHA256.fullmatch(specification_hash)
    ):
        raise ValueError("results specification_hash must be a SHA-256 or the explicit absent marker")
    return {
        "specification_hash": specification_hash,
        "reproducibility": (
            "not-reproducible" if specification_hash == ABSENT_SPECIFICATION else "reproducible"
        ),
    }


def validate_result(document: Any) -> None:
    """Reject a missing hash and contradictory claims, including at read time."""
    if not isinstance(document, dict) or not isinstance(document.get("header"), dict):
        raise ValueError("results require a header with specification_hash")
    header = document["header"]
    if "specification_hash" not in header:
        raise ValueError("results header is missing specification_hash")
    expected = result_header(header["specification_hash"])
    if header.get("reproducibility") != expected["reproducibility"]:
        raise ValueError("results header has an inconsistent reproducibility claim")


def result_document(payload: Any, *, specification_hash: str) -> dict[str, Any]:
    """Preserve object payloads; wrap list payloads without altering their rows."""
    if isinstance(payload, Mapping):
        if "header" in payload:
            raise ValueError("results payload must not replace its provenance header")
        document = {"header": result_header(specification_hash), **payload}
    else:
        document = {"header": result_header(specification_hash), "results": payload}
    validate_result(document)
    return document


def encode_json_result(
    document: dict[str, Any], *, indent: int | None = 2, compact: bool = False,
) -> str:
    validate_result(document)
    return json.dumps(
        document, ensure_ascii=False, indent=None if compact else indent,
        separators=(",", ":") if compact else None,
    ) + "\n"


def write_json_result(
    path: Path, document: dict[str, Any], *, indent: int | None = 2,
    compact: bool = False, max_bytes: int | None = None,
) -> None:
    """Validate before creating a file or replacing any existing result."""
    rendered = encode_json_result(document, indent=indent, compact=compact)
    if max_bytes is not None and len(rendered.encode("utf-8")) > max_bytes:
        raise ValueError("Report exceeds the order's file-size limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8", newline="\n")


def read_json_result(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    validate_result(document)
    return document


def render_result_header(header: dict[str, Any]) -> str:
    validate_result({"header": header})
    metadata = json.dumps(header, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return (
        f"{_HEADER_PREFIX}{metadata}{_HEADER_SUFFIX}\n\n"
        f"**Specification hash:** `{header['specification_hash']}`; "
        f"**Reproducibility:** {header['reproducibility']}.\n\n"
    )


def write_markdown_result(path: Path, body: str, *, header: dict[str, Any]) -> None:
    rendered = render_result_header(header) + body
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8", newline="\n")


def read_markdown_result(path: Path) -> tuple[dict[str, Any], str]:
    rendered = path.read_text(encoding="utf-8")
    first_line = rendered.split("\n", 1)[0]
    if not first_line.startswith(_HEADER_PREFIX) or not first_line.endswith(_HEADER_SUFFIX):
        raise ValueError("results require a header with specification_hash")
    header = json.loads(first_line[len(_HEADER_PREFIX):-len(_HEADER_SUFFIX)])
    prefix = render_result_header(header)
    if not rendered.startswith(prefix):
        raise ValueError("results display header disagrees with its metadata")
    return header, rendered[len(prefix):]
