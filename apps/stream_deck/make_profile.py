"""Build Stream Deck MK.2 profiles from plain JSON key lists.

The supplied Version 3.0 profile establishes the folder and action wrappers.
The supplied Reason profile establishes hotkey payloads and inert image tiles.
Elgato's installed default profiles establish Open paths and Windows modifiers.
The published ScriptDeck profile action establishes the two rotate settings.
Only the format is reproduced; no third-party artwork or key content is used.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import sys
import textwrap
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

KINDS = {"website", "open", "text", "hotkey", "folder", "switch", "ask", "reserved", "empty"}
ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")
ROOT = Path(__file__).resolve().parents[2]
EMPTY_HOTKEY = {
    "KeyCmd": False,
    "KeyCtrl": False,
    "KeyFn": False,
    "KeyModifiers": 0,
    "KeyOption": False,
    "KeyShift": False,
    "NativeCode": -1,
    "QTKeyCode": 33554431,
    "VKeyCode": -1,
}


def _fail(label: str, message: str) -> None:
    raise ValueError(f"{label}: {message}")


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        _fail(label, "id must contain only letters, digits, underscores or hyphens")
    return value


def _uuid(value: object, label: str) -> str:
    try:
        return str(uuid.UUID(str(value))).upper()
    except (ValueError, TypeError, AttributeError):
        _fail(label, "uuid must be a UUID")
    raise AssertionError("unreachable")


def _export_filename(name: str) -> str:
    """Keep the displayed profile name while producing one safe Windows basename."""
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    if not stem:
        _fail(name, "profile name must contain a usable filename character")
    if stem.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    }:
        stem = "_" + stem
    return stem + ".streamDeckProfile"


def character_data() -> dict[str, dict]:
    """Read names and colours from the unchanged Table and policy resources."""
    colors = json.loads((ROOT / "apps/talking_table/sigil_colors.json").read_text("utf-8"))
    result = {}
    for path in sorted((ROOT / "src/secondsignal/profiles").glob("*.json")):
        profile = json.loads(path.read_text("utf-8"))
        result[profile["id"]] = {
            "display_name": profile["display_name"],
            "color": colors[profile["id"]]["colour"],
        }
    result["idle"] = {"color": colors["idle"]["colour"]}
    return result


def load_profiles(paths: list[Path | str]) -> list[dict]:
    """Load requested lists and their explicit companion lists, once each."""
    loaded = []
    seen = set()
    pending = [Path(path).resolve() for path in paths]
    while pending:
        path = pending.pop(0)
        if path in seen:
            continue
        seen.add(path)
        try:
            profile = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            _fail(path.name, f"cannot read key list: {exc}")
        if not isinstance(profile, dict):
            _fail(path.name, "key list must be a JSON object")
        companions = profile.get("companions", [])
        if not isinstance(companions, list) or any(not isinstance(p, str) for p in companions):
            _fail(path.name, "companions must be a list of file names")
        profile["_source_path"] = str(path)
        loaded.append(profile)
        pending.extend((path.parent / item).resolve() for item in companions)
    return loaded


def hotkey_settings(combination: str, label: str = "hotkey") -> dict:
    """Encode one combination using the native four-slot Hotkeys schema."""
    parts = [part.strip().lower() for part in combination.split("+")]
    aliases = {"win": "windows", "ctrl": "control", "cmd": "windows", "option": "alt"}
    parts = [aliases.get(part, part) for part in parts]
    modifiers = {"windows": 8, "control": 2, "alt": 4, "shift": 1}
    keys = [part for part in parts if part not in modifiers]
    if len(keys) != 1 or len(set(parts)) != len(parts):
        _fail(label, "hotkey needs modifiers and exactly one supported key")
    named = {
        "enter": (13, 16777220), "tab": (9, 16777217),
        "escape": (27, 16777216), "space": (32, 32),
        "backspace": (8, 16777219), "up": (38, 16777235),
        "down": (40, 16777237), "left": (37, 16777234), "right": (39, 16777236),
    }
    key = keys[0]
    if len(key) == 1 and key.isascii() and key.isalnum():
        native = qt = ord(key.upper())
    elif re.fullmatch(r"f([1-9]|1[0-2])", key):
        number = int(key[1:])
        native, qt = 111 + number, 16777263 + number
    elif key in named:
        native, qt = named[key]
    else:
        _fail(label, f"unsupported hotkey {combination!r}")
    active = dict(EMPTY_HOTKEY)
    active.update({
        "KeyCmd": "windows" in parts, "KeyCtrl": "control" in parts,
        "KeyOption": "alt" in parts, "KeyShift": "shift" in parts,
        "KeyModifiers": sum(bit for name, bit in modifiers.items() if name in parts),
        "NativeCode": native, "QTKeyCode": qt, "VKeyCode": native,
    })
    return {"Coalesce": True, "Hotkeys": [active] + [dict(EMPTY_HOTKEY) for _ in range(3)]}


def validate_profiles(profiles: list[dict]) -> None:
    """Fail with the key's name when a list cannot describe a safe, linked deck."""
    if not profiles:
        _fail("profiles", "at least one key list is required")
    known_characters = set(character_data()) - {"idle"}
    ids = set()
    uuids = set()
    filenames = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            _fail("profile", "must be an object")
        label = str(profile.get("id", "profile"))
        pid = _identifier(profile.get("id"), label)
        if pid in ids:
            _fail(label, "duplicate profile id in this run")
        ids.add(pid)
        if not isinstance(profile.get("name"), str) or not profile["name"].strip():
            _fail(label, "profile needs a name")
        filename = _export_filename(profile["name"]).casefold()
        if filename in filenames:
            _fail(label, "profile name produces a duplicate export filename")
        filenames.add(filename)
        uid = _uuid(profile.get("uuid"), label)
        if uid in uuids:
            _fail(label, "duplicate profile UUID in this run")
        uuids.add(uid)
    for profile in profiles:
        label = profile["id"]
        external = profile.get("external_profiles", {})
        if not isinstance(external, dict):
            _fail(label, "external_profiles must be an object")
        for name, declaration in external.items():
            if name != "reason" or not isinstance(declaration, dict):
                _fail(label, "only the declared purchased Reason profile may be external")
            declared_uuid = declaration.get("uuid")
            if not (isinstance(declared_uuid, str) and declared_uuid.startswith("PLACEHOLDER:")):
                _uuid(declared_uuid, f"{label}/{name}")
        pages = profile.get("pages")
        if not isinstance(pages, list) or not pages:
            _fail(label, "pages must be a nonempty list")
        page_ids = set()
        for page in pages:
            if not isinstance(page, dict):
                _fail(label, "each page must be an object")
            page_id = _identifier(page.get("id"), f"{label}/page")
            if page_id in page_ids:
                _fail(f"{label}/{page_id}", "duplicate page id")
            page_ids.add(page_id)
            if not isinstance(page.get("name"), str) or not page["name"].strip():
                _fail(f"{label}/{page_id}", "page needs a name")
        home = profile.get("home", "main")
        if home not in page_ids:
            _fail(label, f"home page {home!r} does not exist")
        edges = {page_id: [] for page_id in page_ids}
        for page in pages:
            page_label = f"{label}/{page['id']}"
            if not isinstance(page.get("keys"), list):
                _fail(page_label, "keys must be a list")
            positions = {}
            key_ids = set()
            for index, key in enumerate(page["keys"]):
                if not isinstance(key, dict):
                    _fail(f"{page_label}/key {index}", "key must be an object")
                key_label = f"{page_label}/{key.get('id', f'key {index}')}"
                kid = _identifier(key.get("id"), key_label)
                if kid in key_ids:
                    _fail(key_label, "duplicate key id on this page")
                key_ids.add(kid)
                position = key.get("position")
                if (not isinstance(position, list) or len(position) != 2
                        or any(type(n) is not int for n in position)
                        or not 0 <= position[0] <= 4 or not 0 <= position[1] <= 2):
                    _fail(key_label, "position must be [column 0..4, row 0..2]")
                pos = tuple(position)
                if pos in positions:
                    _fail(key_label, f"duplicate position {pos}, already used by {positions[pos]}")
                positions[pos] = key_label
                if page["id"] != home and pos == (0, 0):
                    _fail(key_label, "sub-page 0,0 is reserved for the generated Back key")
                kind = key.get("kind")
                if not isinstance(kind, str) or kind not in KINDS:
                    _fail(key_label, f"unknown kind {kind!r}")
                if not isinstance(key.get("title"), str):
                    _fail(key_label, "title must be a string")
                target = key.get("target", "")
                if not isinstance(target, str):
                    _fail(key_label, "target must be a string")
                placeholder = target.startswith("PLACEHOLDER:")
                if kind == "ask":
                    character = key.get("character", target)
                    if not isinstance(character, str) or character not in known_characters:
                        _fail(key_label, f"unknown ask character {character!r}")
                if placeholder:
                    continue
                if kind == "folder":
                    if target not in page_ids:
                        _fail(key_label, f"folder page {target!r} does not exist")
                    edges[page["id"]].append((target, key_label))
                elif kind == "switch":
                    if target not in ids and target not in external:
                        _fail(key_label, f"switch profile {target!r} is not in this run")
                elif kind == "website":
                    parsed = urlsplit(target)
                    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                        _fail(key_label, "website target must be an http or https address")
                elif kind == "hotkey":
                    hotkey_settings(target, key_label)
                elif kind in {"open", "text"} and not target:
                    _fail(key_label, "target must not be empty; use PLACEHOLDER: for unknown targets")
                if kind == "open" and any(c in target for c in ('"', '\r', '\n')):
                    _fail(key_label, "open target must be a plain path without embedded quotes")
                if kind == "text" and type(key.get("enter", False)) is not bool:
                    _fail(key_label, "enter must be true or false")
        active = set()
        visited = set()

        def visit(page_id: str) -> None:
            active.add(page_id)
            for child, key_label in edges[page_id]:
                if child in active:
                    _fail(key_label, "folder link creates a cycle")
                if child not in visited:
                    visit(child)
            active.remove(page_id)
            visited.add(page_id)

        visit(home)
        if missing := page_ids - visited:
            _fail(label, f"page {sorted(missing)[0]!r} has no folder path from home")


def _page_uuid(profile: dict, page_id: str) -> str:
    return str(uuid.uuid5(uuid.UUID(profile["uuid"]), f"page/{page_id}")).upper()


def _page_keys(profile: dict, page: dict) -> list[dict]:
    keys = {tuple(key["position"]): copy.deepcopy(key) for key in page["keys"]}
    if page["id"] != profile.get("home", "main"):
        keys[0, 0] = {"id": "back", "title": "Back", "position": [0, 0], "kind": "back"}
    for row in range(3):
        for col in range(5):
            keys.setdefault((col, row), {
                "id": f"empty_{col}_{row}", "title": "", "position": [col, row], "kind": "empty",
            })
    return [keys[col, row] for row in range(3) for col in range(5)]


def _action(
    key: dict, profile: dict, page: dict, registry: dict, image: str, show_title: bool = False,
) -> dict:
    kind, target = key["kind"], key.get("target", "")
    suffix, name, plugin_name = "system.hotkey", "", "Activate a Key Command"
    settings = {}
    if kind == "website":
        suffix, name = "system.website", "Website"
        settings = {"path": target, "openInBrowser": True}
    elif kind in {"open", "ask"}:
        suffix, name = "system.open", "Open"
        settings = {"path": f'"{target}"'}
    elif kind == "text":
        suffix, name = "system.text", "Text"
        settings = {
            "Hotkey": {"KeyModifiers": 0, "QTKeyCode": 33554431, "VKeyCode": -1},
            "isSendingEnter": key.get("enter", False), "isTypingMode": False,
            "pastedText": target,
        }
    elif kind == "hotkey":
        name = "Hotkey"
        settings = hotkey_settings(target, key["id"])
    elif kind == "folder":
        suffix, name = "profile.openchild", "Create Folder"
        settings = {"ProfileUUID": _page_uuid(profile, target)}
    elif kind == "back":
        suffix, name = "profile.backtoparent", "Parent folder"
    elif kind == "switch":
        suffix, name = "profile.rotate", "Switch Profile"
        settings = {"DeviceUUID": "", "ProfileUUID": registry[target]}
    action_uuid = "com.elgato.streamdeck." + suffix
    action_id = str(uuid.uuid5(
        uuid.UUID(profile["uuid"]), f"action/{page['id']}/{key['id']}",
    )).upper()
    title = textwrap.fill(key["title"], width=18, break_long_words=False, break_on_hyphens=False) \
        if show_title else key["title"]
    return {
        "ActionID": "00000000-0000-0000-0000-000000000000" if kind == "reserved" else action_id,
        "LinkedTitle": kind != "reserved", "Name": name,
        "Plugin": {"Name": plugin_name if suffix == "system.hotkey" else name,
                   "UUID": action_uuid, "Version": "1.0"},
        "Resources": None, "Settings": settings, "State": 0,
        "States": [{
            "FontFamily": "Arial", "FontSize": 9 if "\n" in title else 10, "FontStyle": "Bold",
            "FontUnderline": False, "Image": f"Images/{image}", "OutlineThickness": 0,
            "ShowTitle": show_title, "Title": title, "TitleAlignment": "bottom",
            "TitleColor": "#FFFFFF",
        }],
        "UUID": action_uuid,
    }


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _clean_old_icons(icon_root: Path, out: Path, written: set[Path]) -> None:
    """Remove only obsolete generated key images, retaining custom and other files."""
    resolved_root = icon_root.resolve()
    if not resolved_root.is_relative_to(out.resolve()):
        _fail(icon_root.name, "generated icon directory must stay inside the output folder")
    candidates = list(icon_root.rglob("*"))
    for candidate in candidates:
        if not candidate.is_file() or not re.fullmatch(r"key-[0-4]-[0-2]\.(png|svg)", candidate.name):
            continue
        resolved = candidate.resolve()
        if not resolved.is_relative_to(resolved_root):
            _fail(candidate.name, "generated icon file points outside its profile folder")
        if resolved not in written:
            candidate.unlink()
    for directory in sorted((p for p in candidates if p.is_dir()),
                            key=lambda p: len(p.parts), reverse=True):
        if directory.is_symlink() or not directory.resolve().is_relative_to(resolved_root):
            continue
        if not any(directory.iterdir()):
            directory.rmdir()


def _write_key_card(report: dict, path: Path) -> None:
    lines = ["STREAM DECK KEY CARD", "Positions are column,row; left/top starts at 0,0.", ""]
    for profile in report["profiles"]:
        lines.append(profile["name"])
        for page in profile["pages"]:
            lines.extend(["", f"  Page: {page['name']}"])
            for key in report["keys"]:
                if key["profile"] == profile["id"] and key["page"] == page["id"]:
                    col, row = key["position"]
                    title = key["title"] or "(empty)"
                    target = key.get("target", "")
                    if key.get("ask_text"):
                        target = f"{key['ask_text']} | {target}"
                    lines.append(f"    {col},{row} | {title} | {key['kind']} | {target}")
        lines.append("")
    for heading, flag in (("NEEDS ART", "needs_art"), ("PLACEHOLDERS", "placeholder")):
        lines.extend([heading])
        matches = [key for key in report["keys"] if key.get(flag)]
        lines.extend(f"  {key['profile']}/{key['page']}/{key['id']}: {key['title']}"
                     + (f" — {key['target']}" if flag == "placeholder" else "") for key in matches)
        if not matches:
            lines.append("  None.")
        lines.append("")
    lines.extend([
        "REAL WEBSITE ICONS",
        "  This build is offline: website tiles show a large first letter and the site name."
        if report["offline"] else "  This build attempted real website icon retrieval.",
        "  Program icons are extracted locally; personal and reserved artwork still win.",
        "  Double-click FETCH REAL ICONS.bat later, with internet access, to fetch favicons",
        "  and regenerate all three profiles from the same lists. Then import them again.",
        "  Python 3.10 or newer and Pillow are needed. See README.txt for details.", "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_fetch_files(key_paths: list[Path], out: Path) -> None:
    """Write an operator-run refresh command; generation never launches it."""
    def batch_path(path: Path) -> str:
        try:
            relative = os.path.relpath(path, out)
        except ValueError:  # Different Windows drives cannot be relative.
            return str(path).replace("%", "%%")
        return "%~dp0" + relative.replace("%", "%%")

    arguments = " ".join(f'--keys "{batch_path(path)}"' for path in key_paths)
    lines = [
        "@echo off", "setlocal DisableDelayedExpansion", "chcp 65001 >nul",
        f'pushd "{batch_path(ROOT)}" || goto no_repository',
        'py -3 -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1',
        "if errorlevel 1 goto use_python", 'set "SD1_PY=py -3"', "goto have_python",
        ":use_python",
        'python -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1',
        "if errorlevel 1 goto no_python", 'set "SD1_PY=python"', ":have_python",
        '%SD1_PY% -c "from PIL import Image" >nul 2>&1',
        "if errorlevel 1 goto no_pillow",
        '%SD1_PY% -m apps.stream_deck.make_profile ' + arguments
        + ' --out "%~dp0." --record-icons',
        "if errorlevel 1 goto failed", "echo.",
        "echo Profiles refreshed. Double-click the three profile files to import them again.",
        "popd", "pause", "exit /b 0", ":no_python",
        "echo Python 3.10 or newer is needed. Install it and run this file again.",
        "goto failed", ":no_pillow", "echo Pillow is needed to fetch real icons. Run:",
        "echo %SD1_PY% -m pip install Pillow", "goto failed", ":no_repository",
        "echo The repository could not be opened. Keep this output beside the repository.",
        "pause", "exit /b 1", ":failed", "popd",
        "echo Icon refresh did not finish. Read the error above.", "pause", "exit /b 1",
    ]
    (out / "FETCH REAL ICONS.bat").write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    (out / "README.txt").write_text(
        "STREAM DECK OUTPUT\n\n"
        "Double-click each of the three .streamDeckProfile files to import it.\n"
        "Keep this folder in place: ask and reset keys open the scripts here.\n"
        "The ask keys need the Talking Table running.\n\n"
        "OFFLINE BUILD AND REAL WEBSITE ICONS\n"
        "The supplied build uses original website tiles and local program icons.\n"
        "Personal artwork and reserved.png still take priority.\n"
        "When wanted, double-click FETCH REAL ICONS.bat with internet access.\n"
        "It uses the same key lists, fetches favicons, and regenerates all three profiles.\n"
        "It needs Python 3.10 or newer and Pillow; it installs nothing automatically.\n"
        "Import the regenerated profile files again afterward.\n"
        "KEY CARD.txt lists every position, unresolved target and missing artwork.\n"
        "Edit the lists and regenerate; never rebuild the deck by hand.\n",
        encoding="utf-8",
    )


def generate_profiles(
    profiles: list[dict], out: Path | str, offline: bool = False, record_icons: bool = False,
) -> dict:
    """Validate a linked run and write profiles, icons, helpers, and a key card."""
    from . import icons

    validate_profiles(profiles)
    out = Path(out).resolve()
    if record_icons:
        for profile in profiles:
            source = profile.get("_source_path")
            if not source:
                _fail(profile["id"], "record-icons requires a loaded key-list file")
            if Path(source).resolve().is_relative_to(Path(__file__).parent / "profiles"):
                _fail(profile["id"], "copy example lists outside the tree before recording icons")
    out.mkdir(parents=True, exist_ok=True)
    (out / "custom").mkdir(exist_ok=True)
    characters = character_data()
    registry = {profile["id"]: _uuid(profile["uuid"], profile["id"]) for profile in profiles}
    icons.reset_cache()
    for name in ("ask.pyw", "reset.pyw"):
        shutil.copyfile(Path(__file__).with_name(name), out / name)
    for character in characters.keys() - {"idle"}:
        shutil.copyfile(Path(__file__).with_name("ask.pyw"), out / f"ask_{character}.pyw")
    report = {"profiles": [], "keys": [], "offline": offline}
    for profile in profiles:
        local_registry = dict(registry)
        for name, item in profile.get("external_profiles", {}).items():
            value = item["uuid"]
            local_registry[name] = value if value.startswith("PLACEHOLDER:") else _uuid(value, name)
        profile_uuid = _uuid(profile["uuid"], profile["id"])
        top = profile_uuid + ".sdProfile"
        profile_path = out / _export_filename(profile["name"])
        temporary_zip = profile_path.with_suffix(".streamDeckProfile.tmp")
        entry = {"id": profile["id"], "name": profile["name"], "uuid": profile_uuid,
                 "path": str(profile_path), "pages": []}
        icon_root = out / "icons" / profile["id"]
        if not icon_root.resolve().is_relative_to(out):
            _fail(profile["id"], "generated icon directory must stay inside the output folder")
        written_images = set()
        source_path = Path(profile["_source_path"]) if profile.get("_source_path") else None
        custom_dirs = [out / "custom"]
        if source_path:
            custom_dirs.append(source_path.parent / "Icons")
        with zipfile.ZipFile(temporary_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            home_uuid = _page_uuid(profile, profile.get("home", "main"))
            manifest = {
                "AppIdentifier": "", "Device": {"Model": "20GBA9901"},
                "Name": profile["name"],
                "Pages": {"Current": home_uuid, "Default": home_uuid, "Pages": [home_uuid]},
                "Version": "3.0",
            }
            archive.writestr(f"{top}/manifest.json", _json_text(manifest))
            for page in profile["pages"]:
                page_uuid = _page_uuid(profile, page["id"])
                prefix = f"{top}/Profiles/{page_uuid}"
                icon_folder = icon_root / page["id"]
                if not icon_folder.resolve().is_relative_to(icon_root.resolve()):
                    _fail(page["id"], "generated page icons must stay inside their profile folder")
                icon_folder.mkdir(parents=True, exist_ok=True)
                actions = {}
                for key in _page_keys(profile, page):
                    original_kind = key["kind"]
                    target = key.get("target", "")
                    if original_kind == "switch" and local_registry.get(target, "").startswith("PLACEHOLDER:"):
                        target = key["target"] = local_registry[target]
                    placeholder = target.startswith("PLACEHOLDER:")
                    if placeholder:
                        key["kind"] = "reserved"
                    elif key["kind"] == "ask":
                        character = key.get("character", target)
                        key.update(characters[character])
                        key["target"] = str(out / f"ask_{character}.pyw")
                    elif key["kind"] == "open" and target == "@reset":
                        key["target"] = str(out / "reset.pyw")
                    if key["id"] == "start_table":
                        key["color"] = characters["idle"]["color"]
                    row = {"profile": profile["id"], "page": page["id"], "id": key["id"],
                           "title": key["title"], "position": key["position"], "kind": key["kind"],
                           "target": key.get("target", ""), "placeholder": placeholder,
                           "needs_art": False, "source": "empty"}
                    if placeholder:
                        row["requested_kind"] = original_kind
                    if original_kind == "ask":
                        row["ask_text"] = f"Could I talk to {key['display_name']}?"
                    if key["kind"] != "empty":
                        col, grid_row = key["position"]
                        stem = icon_folder / f"key-{col}-{grid_row}"
                        icon = icons.render_icon(key, stem, offline=offline, custom_dirs=custom_dirs)
                        row.update(icon)
                        actions[f"{col},{grid_row}"] = _action(
                            key, profile, page, local_registry, icon["image"],
                            show_title=icon["source"] in {"operator", "website", "program"},
                        )
                        for extension in (".svg", ".png"):
                            image_path = stem.with_suffix(extension)
                            if image_path.exists() and (extension == ".svg" or icon["image"].endswith(".png")):
                                archive.write(image_path, f"{prefix}/Images/{image_path.name}")
                                written_images.add(image_path.resolve())
                    report["keys"].append(row)
                archive.writestr(f"{prefix}/manifest.json", _json_text({
                    "Controllers": [{"Type": "Keypad", "Actions": actions}],
                    "Icon": "", "Name": page["name"],
                }))
                entry["pages"].append({"id": page["id"], "name": page["name"],
                                       "uuid": page_uuid, "actions": len(actions)})
        temporary_zip.replace(profile_path)
        _clean_old_icons(icon_root, out, written_images)
        report["profiles"].append(entry)
        annotated = {key: copy.deepcopy(value) for key, value in profile.items()
                     if not key.startswith("_")}
        sources = {(row["page"], row["id"]): row for row in report["keys"]
                   if row["profile"] == profile["id"]}
        for page in annotated["pages"]:
            for key in page["keys"]:
                info = sources[page["id"], key["id"]]
                key["icon_source"] = info["source"]
                origin = info.get("source_file") or info.get("source_url")
                if origin:
                    key["icon_origin"] = origin
                else:
                    key.pop("icon_origin", None)
                if info.get("source_2x"):
                    key["icon_2x"] = info["source_2x"]
                else:
                    key.pop("icon_2x", None)
                if "fallback" in info:
                    key["icon_fallback"] = info["fallback"]
                else:
                    key.pop("icon_fallback", None)
        if record_icons and source_path:
            source_path.write_text(_json_text(annotated), encoding="utf-8")
        else:
            annotated_path = out / f"{profile['id'].upper()}.json"
            annotated_path.write_text(_json_text(annotated), encoding="utf-8")
    key_paths = [Path(profile["_source_path"]) if record_icons
                 else out / f"{profile['id'].upper()}.json" for profile in profiles]
    _write_fetch_files(key_paths, out)
    _write_key_card(report, out / "KEY CARD.txt")
    (out / "generation-report.json").write_text(_json_text(report), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keys", action="append", required=True, type=Path,
                        help="key-list JSON; repeat or use explicit companions")
    parser.add_argument("--out", required=True, type=Path, help="output folder")
    parser.add_argument("--offline", action="store_true", help="never fetch website icons")
    parser.add_argument("--record-icons", action="store_true",
                        help="record icon sources in the copied input lists instead of output copies")
    args = parser.parse_args(argv)
    try:
        report = generate_profiles(load_profiles(args.keys), args.out, args.offline, args.record_icons)
    except (ValueError, OSError) as exc:
        print(f"Stream Deck: {exc}", file=sys.stderr)
        return 2
    for profile in report["profiles"]:
        print(f"Wrote {profile['path']}")
    print(f"Wrote icons, scripts, KEY CARD.txt and generation-report.json in {args.out.resolve()}")
    print("Recorded icon sources in the input lists." if args.record_icons
          else "Wrote annotated key-list copies in the output folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
