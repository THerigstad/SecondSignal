"""No profile may hand a person to a security character.

The security characters (the intake function, the ledger and interlock, the
audit harness) are not routable and have no seat: ADR-0014 and
ADR-0019 (Proposed).  A handoff row that names one of them is a promise the runtime
refuses, and a persona that believes it can make that handoff can be talked
into announcing it.  It exists because a pre-roster YAML profile carried one
for a week without anything noticing.

What is checked, and how, so the guarantee is exactly as wide as the check
(review round 2, ChatGPT, mutations G01 to G08):

* the roster loader reads ``*.json`` and nothing else, so every JSON file
  under a profile root is parsed with the same parser and walked whole: any
  string equal to a security id anywhere under ``handoffs``, in a list, a
  mapping or a nested mapping, fails (G04, G07, G08);
* the profile's own ``id``, ``aliases`` and ``short_name`` may not be a
  security id whatever the file is called (G05);
* a file whose extension is YAML in any case (``.yaml``, ``.yml``, ``.YAML``)
  is refused outright: the loader does not read it, so it is a profile
  nobody loads and a place a handoff could hide (G01, G02, G03, G06); and
  any other extension under a profile root that is not JSON is refused for
  the same reason;
* the discovery roots must exist where the loader looks, so an emptied
  directory is a failure rather than a vacuous pass;
* the old root-level ``profiles/`` directory that ADR-0019 (Proposed)
  forbids must not return.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOADER_ROOT = ROOT / "src" / "secondsignal" / "profiles"
OTHER_ROOTS = (ROOT / "agents", ROOT / "profiles")
SECURITY_IDS = {"orrin", "aya", "jr", "j.r.", "j_r"}
YAML_SUFFIXES = {".yaml", ".yml"}


def profile_roots(root: Path = ROOT) -> list[Path]:
    return [root / "src" / "secondsignal" / "profiles", root / "agents", root / "profiles"]


def profile_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for base in profile_roots(root):
        if base.is_dir():
            files.extend(p for p in base.rglob("*") if p.is_file())
    return files


def _strings(value: object) -> list[str]:
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)] + [k for k in value if isinstance(k, str)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    if isinstance(value, str):
        return [value]
    return []


def _is_security(name: object) -> bool:
    return isinstance(name, str) and name.strip().lower() in SECURITY_IDS


def problems(root: Path = ROOT) -> list[str]:
    found: list[str] = []
    loader_root = root / "src" / "secondsignal" / "profiles"
    if not loader_root.is_dir() or not any(loader_root.glob("*.json")):
        found.append("the loader's profile root is missing or empty; a vacuous pass is not a pass")
    if (root / "profiles").exists():
        found.append("the root-level profiles/ directory is back; the roster ships inside the package (ADR-0019 (Proposed))")
    for path in profile_files(root):
        rel = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        if suffix in YAML_SUFFIXES:
            found.append(f"{rel}: a YAML profile; the loader reads only *.json, so this file is a profile nobody loads")
            continue
        if suffix != ".json":
            found.append(f"{rel}: not a JSON profile; the loader reads only *.json")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            found.append(f"{rel}: not valid JSON ({exc})")
            continue
        if not isinstance(data, dict):
            found.append(f"{rel}: a profile is a JSON object")
            continue
        if path.stem.lower() in SECURITY_IDS or path.parent.name.lower() in SECURITY_IDS:
            found.append(f"{rel}: a file named for a security character")
        for field in ("id", "short_name"):
            if _is_security(data.get(field)):
                found.append(f"{rel}: {field} is the security id {data[field]!r}")
        for alias in data.get("aliases", []) or []:
            if _is_security(alias):
                found.append(f"{rel}: alias {alias!r} is a security id")
        for target in _strings(data.get("handoffs", {})):
            if _is_security(target):
                found.append(f"{rel}: handoff to {target!r}")
    return found


def test_no_profile_hands_off_to_a_security_character_and_none_is_one() -> None:
    found = problems(ROOT)
    assert not found, "\n".join(found)


def test_the_check_reads_the_same_files_the_loader_reads() -> None:
    from secondsignal import load_roster
    loaded = set(load_roster())
    on_disk = {p.stem for p in LOADER_ROOT.glob("*.json")}
    assert loaded == on_disk, "the loader and this check disagree about which files are profiles"
    assert not loaded & SECURITY_IDS
