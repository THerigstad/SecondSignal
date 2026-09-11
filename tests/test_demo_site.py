"""The built demo carries the complete runtime and its matching hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from demo.build_site import PICTURES, ROOT, build, runtime_files


def test_demo_site_manifest_and_copied_files(tmp_path: Path) -> None:
    out = tmp_path / "site"
    returned_manifest = build(out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))

    assert manifest == returned_manifest
    assert manifest["schema_version"] == 1
    entries = manifest["files"]
    listed_paths = [entry["path"] for entry in entries]
    assert len(listed_paths) == len(set(listed_paths)), "duplicate manifest paths"
    assert set(listed_paths) == {path.as_posix() for path in runtime_files()}

    for entry in entries:
        relative_path = entry["path"]
        source_bytes = (ROOT / relative_path).read_bytes()
        copied_bytes = (out / relative_path).read_bytes()
        assert entry["sha256"] == hashlib.sha256(source_bytes).hexdigest(), relative_path
        assert entry["sha256"] == hashlib.sha256(copied_bytes).hexdigest(), relative_path
        assert entry["bytes"] == len(source_bytes) == len(copied_bytes), relative_path

    all_python_paths = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src" / "secondsignal").rglob("*.py")
        if path.is_file()
    }
    assert all_python_paths <= set(listed_paths)
    assert (out / "index.html").read_bytes() == (ROOT / "demo" / "index.html").read_bytes()
    assert (out / ".nojekyll").is_file()
    assert manifest["pictures"] == list(PICTURES)
    for relative_path in PICTURES:
        assert (out / relative_path).read_bytes() == (ROOT / relative_path).read_bytes()
