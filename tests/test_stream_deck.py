"""SD1 profile exports and their actual local Table launchers."""

from __future__ import annotations

import copy
import io
import json
import re
import runpy
import sys
import threading
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

import pytest

from apps.stream_deck import icons, make_profile
from apps.talking_table import server
from secondsignal.profiles import load_roster
from secondsignal_harness import FakeAdapter

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "apps" / "stream_deck"
EXAMPLES = DECK / "profiles"
PREFIX = "com.elgato.streamdeck."


def example_profiles():
    return make_profile.load_profiles(sorted(EXAMPLES.glob("*.json")))


def no_network(*args, **kwargs):
    raise AssertionError("An offline profile attempted a network request")


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    destination = tmp_path_factory.mktemp("stream-deck")
    profiles = example_profiles()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(urllib.request, "urlopen", no_network)
        patch.setattr(urllib.request.OpenerDirector, "open", no_network)
        patch.setattr(icons, "urlopen", no_network)
        report = make_profile.generate_profiles(profiles, destination, offline=True)
    return profiles, destination, report


def read_export(path):
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()
                 if not name.endswith("/")}
    roots = {name.split("/")[0] for name in files}
    assert len(roots) == 1
    root = roots.pop()
    uuid.UUID(root.removesuffix(".sdProfile"))
    assert root.endswith(".sdProfile")
    manifest = json.loads(files[root + "/manifest.json"])
    pages = {json.loads(content)["Name"]: (name, json.loads(content))
             for name, content in files.items()
             if name.startswith(root + "/Profiles/") and name.endswith("/manifest.json")}
    return root, manifest, pages, files


@pytest.mark.parametrize("profile_id", ["testing", "building", "music"])
def test_example_list_validates_with_its_companions(profile_id):
    """Each supplied profile validates with the other profiles it can switch to."""
    profiles = example_profiles()
    assert len(profiles) == 3
    assert profile_id in {item["id"] for item in profiles}
    make_profile.validate_profiles(profiles)


@pytest.mark.parametrize("change", [
    {"kind": "unrecognised"}, {"position": [-1, 0]}, {"position": [5, 0]},
    {"position": [0, 3]}, {"kind": "ask", "character": "not_a_character"},
    {"kind": "folder", "target": "missing_page"},
    {"kind": "switch", "target": "missing_profile"},
])
def test_bad_list_names_the_bad_key(change):
    """Unknown kinds, out-of-grid keys and broken references identify their key."""
    profiles = copy.deepcopy(example_profiles())
    key = profiles[0]["pages"][0]["keys"][0]
    key.update(change)
    with pytest.raises(ValueError, match=re.escape(key["id"])):
        make_profile.validate_profiles(profiles)


def test_duplicate_position_names_the_key():
    """Two actions cannot silently occupy the same physical button."""
    profiles = copy.deepcopy(example_profiles())
    keys = profiles[0]["pages"][0]["keys"]
    keys[1]["position"] = list(keys[0]["position"])
    with pytest.raises(ValueError, match=re.escape(keys[1]["id"])):
        make_profile.validate_profiles(profiles)


def test_export_matches_teacher_layout_and_every_key(generated):
    """Exports preserve the Version 3 MK.2 structure and exactly one Back per child."""
    profiles, destination, _ = generated
    exports = list(destination.glob("*.streamDeckProfile"))
    assert len(exports) == 3
    by_name = {read_export(path)[1]["Name"]: read_export(path) for path in exports}
    for profile in profiles:
        root, manifest, pages, files = by_name[profile["name"]]
        assert manifest["Version"] == "3.0"
        assert manifest["Device"]["Model"] == "20GBA9901"
        assert manifest["Pages"]["Current"] == manifest["Pages"]["Default"]
        assert manifest["Pages"]["Pages"] == [manifest["Pages"]["Default"]]
        assert set(pages) == {page["name"] for page in profile["pages"]}
        for page in profile["pages"]:
            manifest_path, document = pages[page["name"]]
            assert document["Icon"] == ""
            assert len(document["Controllers"]) == 1
            controller = document["Controllers"][0]
            assert controller["Type"] == "Keypad"
            actions = controller["Actions"]
            expected = {f"{key['position'][0]},{key['position'][1]}"
                        for key in page["keys"] if key["kind"] != "empty"}
            child = page["id"] != profile["home"]
            if child:
                expected.add("0,0")
            assert set(actions) == expected
            backs = [position for position, action in actions.items()
                     if action["UUID"] == PREFIX + "profile.backtoparent"]
            assert backs == (["0,0"] if child else [])
            for position, action in actions.items():
                assert re.fullmatch(r"[0-4],[0-2]", position)
                assert {"ActionID", "LinkedTitle", "Name", "Plugin", "Resources",
                        "Settings", "State", "States", "UUID"} <= action.keys()
                uuid.UUID(action["ActionID"])
                assert {"Name", "UUID", "Version"} <= action["Plugin"].keys()
                assert action["State"] == 0 and len(action["States"]) == 1
                state = action["States"][0]
                assert {"FontFamily", "FontSize", "FontStyle", "FontUnderline", "Image",
                        "OutlineThickness", "ShowTitle", "Title", "TitleAlignment",
                        "TitleColor"} <= state.keys()
                column, row = position.split(",")
                assert re.fullmatch(rf"Images/key-{column}-{row}\.(png|svg)", state["Image"])
                image_path = manifest_path.rsplit("/", 1)[0] + "/" + state["Image"]
                assert image_path in files
        assert root + "/Profiles/" + manifest["Pages"]["Default"] + "/manifest.json" in files


def test_export_text_hotkeys_and_inert_keys_keep_exact_settings(generated):
    """Text preserves Enter and full text; Windows chords and reserved keys stay correct."""
    profiles, destination, _ = generated
    by_name = {read_export(path)[1]["Name"]: read_export(path)
               for path in destination.glob("*.streamDeckProfile")}
    for profile in profiles:
        pages = by_name[profile["name"]][2]
        for page in profile["pages"]:
            actions = pages[page["name"]][1]["Controllers"][0]["Actions"]
            for key in page["keys"]:
                if key["kind"] == "empty":
                    continue
                action = actions[",".join(map(str, key["position"]))]
                settings = action["Settings"]
                if key["kind"] == "text":
                    assert action["UUID"] == PREFIX + "system.text"
                    assert settings["pastedText"] == key["target"]
                    assert settings["isSendingEnter"] is key.get("enter", False)
                    assert settings["isTypingMode"] is False
                    if key["title"].casefold() == "stop":
                        assert settings["pastedText"] == "Stop. Hold."
                if key["kind"] == "hotkey":
                    assert action["UUID"] == PREFIX + "system.hotkey"
                    chords = settings["Hotkeys"]
                    assert len(chords) == 4 and settings["Coalesce"] is True
                    first = chords[0]
                    assert first["KeyModifiers"] == (9 if "Shift" in key["target"] else 8)
                    assert first["VKeyCode"] in {72, 83, 86}
                if key["kind"] == "reserved" or str(key.get("target", "")).startswith("PLACEHOLDER:"):
                    assert settings == {}, "A visible reserved tile must not execute an action"
                if key["kind"] == "folder":
                    assert action["UUID"] == PREFIX + "profile.openchild"
                    child = next(child for child in profile["pages"] if child["id"] == key["target"])
                    child_manifest = pages[child["name"]][0]
                    assert settings == {"ProfileUUID": child_manifest.split("/")[-2]}
                if key["kind"] == "switch" and key["target"] in {item["id"] for item in profiles}:
                    expected_profile = next(item for item in profiles if item["id"] == key["target"])
                    assert action["UUID"] == PREFIX + "profile.rotate"
                    assert settings == {"DeviceUUID": "", "ProfileUUID": expected_profile["uuid"].upper()}
                if key["kind"] == "ask" or key.get("target") == "@reset":
                    assert action["UUID"] == PREFIX + "system.open"
                    filename = "reset.pyw" if key.get("target") == "@reset" else f"ask_{key['character']}.pyw"
                    assert settings == {"path": '"' + str(destination / filename) + '"'}


def test_png_and_svg_icons_are_144_pixels_and_stop_is_white(generated):
    """Raster and vector assets fit a key, and STOP uses a white background."""
    image_module = pytest.importorskip("PIL.Image", reason="Pillow is absent; raster icons need Pillow")
    profiles, destination, _ = generated
    saw_stop = False
    for export in destination.glob("*.streamDeckProfile"):
        _, manifest, pages, files = read_export(export)
        for name, content in files.items():
            if name.endswith(".png"):
                with image_module.open(io.BytesIO(content)) as bitmap:
                    assert bitmap.size == (144, 144)
            if name.endswith(".svg"):
                svg = content.decode("utf-8")
                assert 'width="144"' in svg and 'height="144"' in svg
        profile = next(item for item in profiles if item["name"] == manifest["Name"])
        for page in profile["pages"]:
            manifest_path, document = pages[page["name"]]
            for key in page["keys"]:
                if key["title"].casefold() != "stop":
                    continue
                action = document["Controllers"][0]["Actions"][",".join(map(str, key["position"]))]
                path = manifest_path.rsplit("/", 1)[0] + "/" + action["States"][0]["Image"]
                if path.endswith(".png"):
                    with image_module.open(io.BytesIO(files[path])) as bitmap:
                        assert bitmap.convert("RGB").getpixel((143, 0)) == (255, 255, 255)
                    saw_stop = True
    assert saw_stop


def test_examples_and_readme_have_no_machine_paths_or_credentials():
    """Published instructions and examples contain no private paths or token-shaped values."""
    paths = [DECK / "README.md", *sorted(EXAMPLES.glob("*.json"))]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]", text, re.I)
        assert not re.search(r"/(?:Users|home)/[^/\s]+", text)
        assert str(Path.home()).casefold() not in text.casefold()
        assert not re.search(r"\b(?:sk|ghp|xoxb)[-_][A-Za-z0-9_-]{16,}\b", text)
        assert not re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
        if path.suffix == ".json":
            document = json.loads(text)
            for page in document["pages"]:
                for key in page["keys"]:
                    if key["kind"] in {"open", "website"} and key.get("target") != "@reset":
                        assert key["target"].startswith("PLACEHOLDER:")


def test_generated_scripts_ask_exact_phone_text_and_reset_sitting(generated, tmp_path, monkeypatch):
    """All seven actual copied scripts post exact phone asks; reset creates a fresh sitting."""
    _, destination, _ = generated
    app = server.TableApp(data_dir=tmp_path / "table-data")
    listener = server.make_server(app, port=0)
    worker = threading.Thread(target=listener.serve_forever, daemon=True)
    worker.start()
    monkeypatch.setenv("SECONDSIGNAL_TABLE_PORT", str(listener.server_address[1]))
    initial_session = app.session_id
    try:
        assert isinstance(app.harness.adapter, FakeAdapter)
        expected = []
        for character, profile in load_roster().items():
            script = destination / f"ask_{character}.pyw"
            assert script.is_file()
            monkeypatch.setattr(sys, "argv", [str(script)])
            with pytest.raises(SystemExit) as result:
                runpy.run_path(str(script), run_name="__main__")
            assert result.value.code == 0
            expected.append(f"Could I talk to {profile.display_name}?")
            users = [message["content"] for message in app.harness.transcript
                     if message["role"] == "user"]
            assert users == expected
        assert app.state["turn_count"] == 7
        script = destination / "reset.pyw"
        monkeypatch.setattr(sys, "argv", [str(script)])
        with pytest.raises(SystemExit) as result:
            runpy.run_path(str(script), run_name="__main__")
        assert result.value.code == 0
        assert app.session_id != initial_session
        assert app.state["state"] == "idle" and app.state["turn_count"] == 0
        assert app.harness.transcript == []
    finally:
        listener.shutdown()
        listener.server_close()
        worker.join(timeout=3)
        app.close()


def test_script_arguments_override_environment_and_default_to_8765(monkeypatch):
    """Both launchers use explicit ports, then the environment, then the documented default."""
    requests = []

    def capture(self, request, **kwargs):
        requests.append(request)
        return io.BytesIO(b"{}")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", capture)
    ask = runpy.run_path(str(DECK / "ask.pyw"))["main"]
    reset = runpy.run_path(str(DECK / "reset.pyw"))["main"]
    monkeypatch.setenv("SECONDSIGNAL_TABLE_PORT", "43210")
    assert ask(["vAnDaL", "43211"]) == 0
    assert requests[-1].full_url == "http://127.0.0.1:43211/api/turn"
    assert json.loads(requests[-1].data) == {"text": "Could I talk to Vandal?"}
    assert ask(["Willow"]) == 0
    assert requests[-1].full_url == "http://127.0.0.1:43210/api/turn"
    assert reset(["43212"]) == 0
    assert requests[-1].full_url == "http://127.0.0.1:43212/api/session/reset"
    assert requests[-1].data == b"{}"
    monkeypatch.delenv("SECONDSIGNAL_TABLE_PORT")
    assert ask(["Ellis"]) == 0 and reset([]) == 0
    assert all(":8765/" in request.full_url for request in requests[-2:])


def test_scripts_exit_quietly_when_table_is_absent(monkeypatch, capsys):
    """A stopped Table produces neither a traceback nor console output."""
    def unavailable(*args, **kwargs):
        raise urllib.error.URLError("Table is not running")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", unavailable)
    assert runpy.run_path(str(DECK / "ask.pyw"))["main"](["Vandal"]) == 0
    assert runpy.run_path(str(DECK / "reset.pyw"))["main"]([]) == 0
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_offline_icons_use_fallbacks_without_network(tmp_path, monkeypatch):
    """Offline websites get letter tiles while local program artwork remains available."""
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", no_network)
    monkeypatch.setattr(icons, "urlopen", no_network)
    for kind, target in (("website", "https://example.com"),
                         ("open", str(tmp_path / "absent-program.exe"))):
        key = {"id": "offline_" + kind, "title": "Offline", "kind": kind, "target": target}
        rendered = icons.render_icon(key, tmp_path / kind, offline=True, custom_dirs=[])
        assert rendered["source"] == "generated"
        assert rendered["fallback"]
        assert (tmp_path / rendered["image"]).is_file()
        if kind == "website":
            svg = (tmp_path / kind).with_suffix(".svg").read_text(encoding="utf-8")
            assert rendered["generated_style"] == "website"
            assert f'fill="{icons.SLATE}"' in svg and '>O</text>' in svg
            assert '>Offline</text>' in svg
    if icons.Image is not None:
        buffer = io.BytesIO()
        icons.Image.new("RGB", (144, 144), (24, 68, 92)).save(buffer, format="PNG")
        seen = []

        def local_icon(target, scratch):
            seen.append(target)
            return buffer.getvalue(), target, ""

        monkeypatch.setattr(icons, "_program_icon", local_icon)
        target = str(tmp_path / "local-program.exe")
        rendered = icons.render_icon(
            {"id": "program", "title": "Program", "kind": "open", "target": target},
            tmp_path / "local", offline=True, custom_dirs=[],
        )
        assert seen == [target] and rendered["source"] == "program"
        with icons.Image.open(tmp_path / rendered["image"]) as image:
            assert image.convert("RGB").getpixel((0, 0)) == (24, 68, 92)


def test_custom_icons_win_and_missing_personal_art_is_magenta(tmp_path):
    """Supplied key art and reserved art win; missing personal art is visibly magenta."""
    image_module = pytest.importorskip("PIL.Image", reason="Pillow is absent; raster icons need Pillow")
    custom = tmp_path / "custom"
    custom.mkdir()
    image_module.new("RGB", (288, 288), (12, 34, 56)).save(custom / "bandcamp.png")
    image_module.new("RGB", (144, 144), (65, 43, 21)).save(custom / "reserved.png")
    image_module.new("RGB", (144, 144), (200, 0, 0)).save(custom / "Stop.png")
    stop = icons.render_icon({"id": "stop", "title": "STOP", "kind": "text", "target": "Stop. Hold."},
                             tmp_path / "stop", offline=True, custom_dirs=[custom])
    assert stop["source"] == "generated", "Custom filenames must match the exact key id"
    with image_module.open(tmp_path / stop["image"]) as image:
        assert image.convert("RGB").getpixel((0, 0)) == (255, 255, 255)
    key = {"id": "bandcamp", "title": "Bandcamp", "kind": "website",
           "target": "https://example.com"}
    own = icons.render_icon(key, tmp_path / "own", offline=True, custom_dirs=[custom])
    assert own["source"] == "operator" and not own["needs_art"]
    with image_module.open(tmp_path / own["image"]) as image:
        assert image.size == (144, 144)
        assert image.convert("RGB").getpixel((0, 0)) == (12, 34, 56)
    missing = icons.render_icon({**key, "id": "soundcloud"}, tmp_path / "missing",
                                offline=True, custom_dirs=[custom])
    assert missing["source"] == "needs_art" and missing["needs_art"]
    with image_module.open(tmp_path / missing["image"]) as image:
        assert image.convert("RGB").getpixel((143, 0)) == (255, 0, 212)
    reserved = icons.render_icon({"id": "reserved_probe", "title": "Reserved", "kind": "reserved"},
                                 tmp_path / "reserved", offline=True, custom_dirs=[custom])
    assert reserved["source"] == "operator"
    with image_module.open(tmp_path / reserved["image"]) as image:
        assert image.convert("RGB").getpixel((0, 0)) == (65, 43, 21)


def test_without_pillow_writes_svg_and_one_explanation(tmp_path, monkeypatch, capsys):
    """A machine without Pillow still gets SVG icons and one helpful message."""
    for attribute in ("Image", "ImageDraw", "ImageFont", "ImageOps"):
        monkeypatch.setattr(icons, attribute, None)
    icons.reset_cache()
    key = {"id": "stop", "title": "STOP", "kind": "text", "target": "Stop. Hold."}
    first = icons.render_icon(key, tmp_path / "first", offline=True, custom_dirs=[])
    second = icons.render_icon(key, tmp_path / "second", offline=True, custom_dirs=[])
    assert first["image"].endswith(".svg") and second["image"].endswith(".svg")
    assert not list(tmp_path.glob("*.png"))
    svg = (tmp_path / first["image"]).read_text(encoding="utf-8")
    assert 'width="144"' in svg and 'height="144"' in svg
    explanation = capsys.readouterr().out.strip().splitlines()
    assert len(explanation) == 1 and "Pillow" in explanation[0]


def test_offline_cli_loads_companions_and_builds_website_and_open_actions(tmp_path, monkeypatch, capsys):
    """The documented CLI loads its companions, refuses network and emits live target settings."""
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", no_network)
    monkeypatch.setattr(icons, "urlopen", no_network)
    input_dir = tmp_path / "lists"
    input_dir.mkdir()
    profiles = example_profiles()
    launch_path = tmp_path / "launch me.txt"
    launch_path.write_text("Local launch target", encoding="utf-8")
    for profile in profiles:
        profile.pop("_source_path", None)
        for page in profile["pages"]:
            for key in page["keys"]:
                if key["id"] == "repo":
                    key["target"] = "https://example.com/"
                if key["id"] == "current_push":
                    key["target"] = str(launch_path)
        (input_dir / (profile["id"].upper() + ".json")).write_text(json.dumps(profile), encoding="utf-8")
    destination = tmp_path / "output"
    assert make_profile.main(["--keys", str(input_dir / "TESTING.json"),
                              "--out", str(destination), "--offline"]) == 0
    assert len(list(destination.glob("*.streamDeckProfile"))) == 3
    _, _, pages, _ = read_export(destination / "TESTING SECONDSIGNAL.streamDeckProfile")
    website = pages["Page two"][1]["Controllers"][0]["Actions"]["1,0"]
    assert website["UUID"] == PREFIX + "system.website"
    assert website["Settings"] == {"path": "https://example.com/", "openInBrowser": True}
    _, _, pages, _ = read_export(destination / "BUILDING.streamDeckProfile")
    opened = pages["Page one"][1]["Controllers"][0]["Actions"]["0,0"]
    assert opened["UUID"] == PREFIX + "system.open"
    assert opened["Settings"] == {"path": '"' + str(launch_path) + '"'}
    report = json.loads((destination / "generation-report.json").read_text(encoding="utf-8"))
    assert report["offline"] is True
    repo = next(key for key in report["keys"] if key["id"] == "repo")
    assert repo["source"] == "generated" and repo["fallback"]
    launcher = (destination / "FETCH REAL ICONS.bat").read_text(encoding="utf-8")
    command = next(line for line in launcher.splitlines()
                   if "-m apps.stream_deck.make_profile" in line)
    assert "--offline" not in command and "--record-icons" in command
    for name in ("TESTING", "BUILDING", "MUSIC"):
        assert f'--keys "%~dp0{name}.json"' in command
    assert '--out "%~dp0."' in command
    assert "FETCH REAL ICONS.bat" in (destination / "KEY CARD.txt").read_text(encoding="utf-8")
    assert "FETCH REAL ICONS.bat" in (destination / "README.txt").read_text(encoding="utf-8")
    assert "Wrote" in capsys.readouterr().out
