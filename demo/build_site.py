"""Build the demo site: the page beside the files it runs, and a manifest.

    python demo/build_site.py --out _site

The page (``demo/index.html``) runs the real package in the visitor's browser
under Pyodide. It does not carry a copy of the code; it fetches the files
listed in ``manifest.json``, checks each one's SHA-256 against the manifest
before writing it into the interpreter's file system, and refuses to run if
any differs. This builder is what writes that manifest, from the tree as it
stands, so nothing on the page can drift from the code the way a typed
number can.

Copied into the site, at the same relative paths as in the repository:

* ``src/secondsignal/`` (every ``.py``, and the ``packs`` and ``profiles`` JSON)
* ``evals/__init__.py``, ``evals/run_fixtures.py``, ``evals/case-manifest.json``
* ``evals/cases/`` (every JSON document, the deferred ones included, because the
  case test checks that deferred planes are not run)
* ``tests/test_eval_cases.py`` (the file CI runs; pytest runs it in the browser)
* ``pyproject.toml`` (pytest reads its options from it)
* ``docs/assets/secondsignal-mark.svg`` and ``docs/assets/secondsignal-house.png``
  (recorded in ``docs/assets/generation-prompts.json``; the page uses the
  recorded alt text)

The manifest records the commit that built the site when the build runs in
GitHub Actions (``GITHUB_SHA``), or ``unknown`` otherwise; the page shows it.
No dependencies beyond the standard library.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "demo" / "index.html"

# The files the interpreter needs, in the order they are written.
RUNTIME_GLOBS: tuple[str, ...] = (
    "src/secondsignal/*.py",
    "src/secondsignal/packs/*.json",
    "src/secondsignal/profiles/*.json",
    "evals/__init__.py",
    "evals/run_fixtures.py",
    "evals/case-manifest.json",
    "evals/cases/**/*.json",
    "tests/test_eval_cases.py",
    "pyproject.toml",
)

# Pictures the page shows; each has an entry in docs/assets/generation-prompts.json.
PICTURES: tuple[str, ...] = (
    "docs/assets/secondsignal-mark.svg",
    "docs/assets/secondsignal-house.png",
)


def runtime_files(root: Path = ROOT) -> list[Path]:
    """Every file the page fetches into the interpreter, relative to ``root``."""
    out: list[Path] = []
    for pattern in RUNTIME_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and "__pycache__" not in path.parts:
                out.append(path.relative_to(root))
    return out


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out: Path, root: Path = ROOT, commit: str | None = None) -> dict:
    """Write the site into ``out`` and return the manifest that was written."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copyfile(root / "demo" / "index.html", out / "index.html")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    files: list[dict[str, object]] = []
    for rel in runtime_files(root):
        src = root / rel
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        files.append({"path": rel.as_posix(), "sha256": _sha256(src), "bytes": src.stat().st_size})

    for rel in PICTURES:
        src = root / rel
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    manifest = {
        "schema_version": 1,
        "repository": "THerigstad/SecondSignal",
        "commit": commit or os.environ.get("GITHUB_SHA") or "unknown",
        "built_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "files": files,
        "pictures": list(PICTURES),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="_site", help="the folder to write the site into")
    parser.add_argument("--commit", default=None, help="the commit to record (default: GITHUB_SHA or unknown)")
    args = parser.parse_args(argv)
    manifest = build(Path(args.out).resolve(), commit=args.commit)
    total = sum(int(entry["bytes"]) for entry in manifest["files"])
    print(f"{len(manifest['files'])} files, {total} bytes, commit {manifest['commit']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
