"""The pictures under docs/assets/ are recorded, and the record is checked.

Every image in docs/assets/ has an entry in generation-prompts.json with the
hash of the file as committed; the alt text a page uses for a picture is the
alt text the record keeps. Added at the push-3 pre-push check, which found a
diagram re-drawn without its hash moving and an alt text that described a
pose the picture does not show.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
RECORD = json.loads((ASSETS / "generation-prompts.json").read_text(encoding="utf-8"))
NOT_PICTURES = {"README.md", "generation-prompts.json"}


def _recorded_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in RECORD["assets"]:
        if isinstance(entry["sha256"], dict):
            out.update(entry["sha256"])
        else:
            out[entry["file"]] = entry["sha256"]
    return out


def _alt_texts() -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in RECORD["assets"]:
        for name in (entry["sha256"].keys() if isinstance(entry["sha256"], dict) else [entry["file"]]):
            out[name] = entry["alt_text"]
    return out


def _pictures() -> list[Path]:
    return sorted(p for p in ASSETS.iterdir() if p.is_file() and p.name not in NOT_PICTURES)


def test_every_picture_is_recorded_and_nothing_recorded_is_missing() -> None:
    on_disk = {p.name for p in _pictures()}
    recorded = set(_recorded_hashes())
    assert on_disk == recorded, {"unrecorded": sorted(on_disk - recorded), "missing": sorted(recorded - on_disk)}


@pytest.mark.parametrize("path", _pictures(), ids=lambda p: p.name)
def test_the_recorded_hash_is_the_hash_of_the_committed_file(path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == _recorded_hashes()[path.name], f"{path.name}: the file changed and generation-prompts.json did not"


def _image_alts(markdown: str) -> dict[str, str]:
    """Alt text by picture file name, from markdown images and <img> tags."""
    alts: dict[str, str] = {}
    for alt, src in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", markdown):
        if not src.startswith("http"):   # badges are not pictures of the project's
            alts[Path(src).name] = alt
    for tag in re.findall(r"<img\b[^>]*>", markdown):
        src = re.search(r'src="([^"]+)"', tag)
        alt = re.search(r'alt="([^"]*)"', tag)
        if src and alt and "docs/assets/" in src.group(1):
            alts[Path(src.group(1)).name] = alt.group(1)
    return alts


@pytest.mark.parametrize("page", ["README.md", "docs/confessions.md"])
def test_a_page_uses_the_recorded_alt_text(page: str) -> None:
    recorded = _alt_texts()
    used = _image_alts((ROOT / page).read_text(encoding="utf-8"))
    assert used, f"{page}: no picture found"
    for name, alt in used.items():
        assert name in recorded, f"{page}: {name} is not in generation-prompts.json"
        assert alt == recorded[name], f"{page}: alt text for {name} differs from the record"
