"""The room lights (build order 6): lights.py, sigil_colors.json, sigils.html, LIGHTS.md.

Section 6 of the order, written down:

1. the full suite keeps its result (only absent-browser screenshot checks skip);
2. pretend mode with networking disabled gives the right colour and sent false;
3. Govee mode against a fake Govee server: the documented requests go out, the
   key travels only in the Govee-API-Key header and appears in no log line and
   no return value, and a timeout comes back as an error dict within 3 seconds;
4. "card" never yields a character colour;
5. sigils.html against a stub server: the seated plate, the card words, the ask
   buttons post "Could I talk to NAME?", ?ask=vandal works, and screenshots at
   phone width (390 px).

The page checks drive a headless Chrome or Chromium through its command line
(test-only tool; no Python package needed). Set SECONDSIGNAL_TEST_BROWSER to a
browser binary to choose one, and SECONDSIGNAL_LIGHTS_SHOTS to a folder to keep
the screenshots. Where no such browser exists the page tests run their static
half, then explicitly skip with the absent headless Chrome reason.
"""

from __future__ import annotations

import concurrent.futures
import importlib.util
import json
import logging
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zlib
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from secondsignal.profiles import DEFAULT_PROFILE_DIR, load_roster

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "talking_table"
PAGE = APP / "static" / "sigils.html"
COLOURS = APP / "sigil_colors.json"
LIGHTS_MD = APP / "LIGHTS.md"
KEY = "test-key-7f3a9c-not-a-real-key-0b12"
CARD_WORDS = "The crisis card is on the main screen."
NOTICE = "This is a prototype for the operator and adults the operator knows. It is not a crisis service."  # Order T3, 2026-10-07: role-copy pin: he -> the operator.
PHONE = (390, 844)


def _load_lights():
    spec = importlib.util.spec_from_file_location("talking_table_lights_under_test", APP / "lights.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lights = _load_lights()
ROSTER = load_roster(DEFAULT_PROFILE_DIR)
RAW = json.loads(COLOURS.read_text(encoding="utf-8"))
PERSONA_COLOURS = {pid: RAW[pid]["colour"].upper() for pid in lights.PERSONA_IDS}
CARD = RAW["card"]
IDLE = RAW["idle"]


@pytest.fixture(autouse=True)
def _no_key_anywhere(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """No test here may find the operator's real key: empty environment, empty home."""
    monkeypatch.delenv("GOVEE_API_KEY", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(lights, "_default", None)
    yield home
    lights._default = None


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch):
    """Networking disabled: any attempt to resolve or connect is recorded and refused."""
    attempts: list[str] = []

    def refuse(*args: Any, **kwargs: Any):
        attempts.append(repr(args[:2]))
        raise OSError("networking is disabled in this test")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket.socket, "connect", lambda self, *a, **k: refuse(*a))
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, *a, **k: refuse(*a))
    return attempts


# ---------------------------------------------------------------- colours file


def test_colours_file_has_each_character_the_card_and_idle_each_with_a_reason() -> None:
    assert set(lights.PERSONA_IDS) == set(ROSTER), "lights.py must know exactly the roster's ids"
    assert set(RAW) == set(ROSTER) | {"card", "idle"}
    for name, entry in RAW.items():
        assert isinstance(entry.get("why"), str) and entry["why"].strip(), name
        assert "\n" not in entry["why"], f"{name}: the reason is one line"
    checked = lights.load_colours()
    assert checked["card"]["colour"] == "#FFFFFF"
    assert 30 <= checked["card"]["brightness"] <= 70, "the card is moderate brightness"
    assert checked["idle"]["brightness"] <= 20 or checked["idle"]["power"] == "off", "idle is dim or off"
    assert len(set(PERSONA_COLOURS.values())) == 7, "seven different colours"
    assert CARD["colour"].upper() not in PERSONA_COLOURS.values()
    assert IDLE["colour"].upper() not in PERSONA_COLOURS.values()


# ---------------------------------------------------------------- check 2: pretend


def test_pretend_is_the_default_without_a_key() -> None:
    assert lights.Lights().mode == "pretend"
    assert lights.set_scene("cody", "seated")["mode"] == "pretend"


def test_pretend_mode_with_networking_disabled_gives_every_colour_and_sends_nothing(no_network) -> None:
    for pid in lights.PERSONA_IDS:
        out = lights.set_scene(pid, "seated")
        assert out == {
            "mode": "pretend", "state": "seated", "persona": pid,
            "colour": PERSONA_COLOURS[pid], "brightness": RAW[pid]["brightness"],
            "devices": [], "sent": False, "error": None,
        }
    for pid in (*lights.PERSONA_IDS, None):
        out = lights.set_scene(pid, "card")
        assert (out["colour"], out["brightness"], out["sent"], out["persona"], out["error"]) == (
            CARD["colour"].upper(), CARD["brightness"], False, None, None)
        out = lights.set_scene(pid, "idle")
        assert (out["colour"], out["brightness"], out["sent"], out["persona"], out["error"]) == (
            IDLE["colour"].upper(), IDLE["brightness"], False, None, None)
    assert no_network == [], f"pretend mode tried the network: {no_network}"


def test_bad_input_comes_back_as_an_error_dict_and_never_raises(tmp_path: Path, no_network) -> None:
    for persona, state in (("cody", "dancing"), ("nobody", "seated"), (None, "seated"), (7, "seated")):
        out = lights.set_scene(persona, state)  # type: ignore[arg-type]
        assert out["sent"] is False and out["error"] and out["colour"] is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    out = lights.Lights(colours_path=broken).set_scene("cody", "seated")
    assert out["sent"] is False and out["error"].startswith("colours file")
    missing = lights.Lights(colours_path=tmp_path / "absent.json").set_scene("cody", "seated")
    assert missing["error"]
    assert no_network == []


# ---------------------------------------------------------------- the key


def test_the_key_comes_only_from_the_argument_not_environment_or_home(_no_key_anywhere: Path,
                                                                   monkeypatch: pytest.MonkeyPatch,
                                                                   no_network) -> None:
    home = _no_key_anywhere
    assert not lights.Lights().has_key
    (home / ".secondsignal").mkdir()
    (home / ".secondsignal" / "govee.json").write_text(json.dumps({"api_key": KEY}), encoding="utf-8")
    monkeypatch.setenv("GOVEE_API_KEY", KEY)
    room = lights.Lights()
    assert not room.has_key and room.mode == "pretend"
    assert lights.set_scene("cody", "seated")["mode"] == "pretend"
    from_argument = lights.Lights(api_key=KEY)
    assert from_argument.has_key and from_argument.mode == "govee"
    assert KEY not in repr(from_argument)
    assert lights.Lights(api_key=" \t ").mode == "pretend"
    with pytest.raises(TypeError):
        lights.Lights(mode="pretend")
    assert no_network == []


def test_a_settings_file_inside_the_repository_tree_is_ignored(tmp_path: Path,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    fake_repo = tmp_path / "repo"
    (fake_repo / "apps" / "talking_table").mkdir(parents=True)
    (fake_repo / ".secondsignal").mkdir()
    (fake_repo / ".secondsignal" / "govee.json").write_text(json.dumps({"api_key": KEY}), encoding="utf-8")
    monkeypatch.setattr(lights, "HERE", fake_repo / "apps" / "talking_table")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_repo))
    assert not lights.Lights().has_key


def test_the_key_is_never_sent_anywhere_but_govee(no_network) -> None:
    out = lights.Lights(api_key=KEY,
                        base_url="https://collector.example/router/api/v1").set_scene("cody", "seated")
    assert out["sent"] is False and "Govee" in out["error"]
    assert no_network == []
    assert lights.GOVEE_BASE_URL == "https://openapi.api.govee.com/router/api/v1"


# ---------------------------------------------------------------- check 3: the fake Govee


def _device(sku: str, device: str, name: str, *, colour: bool = True) -> dict[str, Any]:
    caps: list[dict[str, Any]] = [
        {"type": "devices.capabilities.on_off", "instance": "powerSwitch",
         "parameters": {"dataType": "ENUM", "options": [{"name": "on", "value": 1}, {"name": "off", "value": 0}]}},
    ]
    if colour:
        caps += [
            {"type": "devices.capabilities.range", "instance": "brightness",
             "parameters": {"unit": "unit.percent", "dataType": "INTEGER",
                            "range": {"min": 1, "max": 100, "precision": 1}}},
            {"type": "devices.capabilities.color_setting", "instance": "colorRgb",
             "parameters": {"dataType": "INTEGER", "range": {"min": 0, "max": 16777215, "precision": 1}}},
        ]
    return {"sku": sku, "device": device, "deviceName": name, "type": "devices.types.light", "capabilities": caps}


class FakeGovee:
    """A stand-in for openapi.api.govee.com, shaped by Govee's published examples."""

    def __init__(self, *, slow_devices: float = 0.0, slow_control: float = 0.0, status: int = 200) -> None:
        self.requests: list[dict[str, Any]] = []
        self.slow_devices, self.slow_control, self.status = slow_devices, slow_control, status
        self.devices = [_device("H6008", "AA:BB:CC:DD:EE:FF:00:11", "Shelf lamp"),
                        _device("H5080", "11:22:33:44:55:66:77:88", "Kettle plug", colour=False)]
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                pass

            def _record(self, body: bytes) -> None:
                fake.requests.append({"method": self.command, "path": self.path,
                                      "headers": {k: v for k, v in self.headers.items()},
                                      "body": body.decode("utf-8", "replace")})

            def _send(self, code: int, doc: dict[str, Any]) -> None:
                data = json.dumps(doc).encode("utf-8")
                try:
                    self.send_response(code)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except OSError:
                    pass  # the client gave up (the timeout test)

            def do_GET(self) -> None:
                self._record(b"")
                if fake.slow_devices:
                    time.sleep(fake.slow_devices)
                if self.path != "/router/api/v1/user/devices":
                    return self._send(404, {"code": 404, "message": "not found"})
                if fake.status != 200:
                    return self._send(fake.status, {"code": fake.status, "message": "Unauthorized"})
                self._send(200, {"code": 200, "message": "success", "data": fake.devices})

            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                self._record(body)
                if fake.slow_control:
                    time.sleep(fake.slow_control)
                if self.path != "/router/api/v1/device/control":
                    return self._send(404, {"code": 404, "message": "not found"})
                doc = json.loads(body)
                self._send(200, {"requestId": doc.get("requestId"), "msg": "success", "code": 200,
                                 "capability": dict(doc["payload"]["capability"], state={"status": "success"})})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}/router/api/v1"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> FakeGovee:
        self.thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.server.shutdown()
        self.server.server_close()

    def controls(self) -> list[dict[str, Any]]:
        return [json.loads(r["body"]) for r in self.requests if r["method"] == "POST"]


def _govee(fake: FakeGovee, **kwargs: Any):
    kwargs.setdefault("min_gap_seconds", 0)
    return lights.Lights(api_key=KEY, base_url=fake.base_url, **kwargs)


def test_govee_mode_sends_the_documented_requests_and_the_key_only_in_its_header(
        caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]) -> None:
    caplog.set_level(logging.DEBUG)
    with FakeGovee() as fake:
        room = _govee(fake)
        assert room.mode == "govee"
        out = room.set_scene("vandal", "seated")
        assert out["error"] is None, out
        assert (out["mode"], out["sent"], out["colour"], out["brightness"], out["devices"]) == (
            "govee", True, PERSONA_COLOURS["vandal"], RAW["vandal"]["brightness"], ["Shelf lamp"])

        first, *controls = fake.requests
        assert (first["method"], first["path"]) == ("GET", "/router/api/v1/user/devices")
        assert [r["path"] for r in controls] == ["/router/api/v1/device/control"] * 2
        sent = fake.controls()
        for doc in sent:
            assert set(doc) == {"requestId", "payload"} and isinstance(doc["requestId"], str) and doc["requestId"]
            assert (doc["payload"]["sku"], doc["payload"]["device"]) == ("H6008", "AA:BB:CC:DD:EE:FF:00:11")
        assert sent[0]["payload"]["capability"] == {
            "type": "devices.capabilities.color_setting", "instance": "colorRgb",
            "value": int(PERSONA_COLOURS["vandal"][1:], 16)}
        assert sent[1]["payload"]["capability"] == {
            "type": "devices.capabilities.range", "instance": "brightness", "value": RAW["vandal"]["brightness"]}
        assert all("11:22:33" not in r["body"] for r in fake.requests), "the plug has no colour; untouched"

        for request in fake.requests:
            headers = {k.lower(): v for k, v in request["headers"].items()}
            assert headers.get("govee-api-key") == KEY
            assert headers.get("content-type") == "application/json"
            assert KEY not in request["path"] and KEY not in request["body"]
            assert all(KEY not in v for k, v in headers.items() if k != "govee-api-key")
        room.set_scene("willow", "seated")
        room.set_scene("rowan", "card")

    printed = capsys.readouterr()
    assert KEY not in caplog.text and KEY not in printed.out and KEY not in printed.err
    assert KEY not in json.dumps(out) and KEY not in repr(room)


def test_govee_errors_are_returned_without_the_key(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with FakeGovee(status=401) as fake:
        out = _govee(fake).set_scene("seren", "seated")
    assert out["sent"] is False and "401" in out["error"] and "refused" in out["error"]
    assert KEY not in json.dumps(out) and KEY not in caplog.text


@pytest.mark.parametrize("field", ("deviceName", "device", "sku"))
def test_a_govee_key_echo_is_never_returned_logged_or_sent_in_a_body(
        field: str, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with FakeGovee() as fake:
        fake.devices[0][field] = "echo-" + KEY
        out = _govee(fake).set_scene("cody", "seated")
        assert out["sent"] is False and "credential" in out["error"]
        assert fake.controls() == []
        assert len(fake.requests) == 1
    assert KEY not in json.dumps(out) and KEY not in caplog.text


def test_clearing_or_changing_the_module_key_drops_the_previous_device_and_scene_cache(
        monkeypatch: pytest.MonkeyPatch) -> None:
    driver = lights.Lights
    with FakeGovee() as fake:
        monkeypatch.setattr(lights, "Lights", lambda **kw: driver(
            base_url=fake.base_url, min_gap_seconds=0, **kw))
        first = lights.set_scene("cody", "seated", api_key=KEY)
        assert first["mode"] == "govee" and first["sent"]
        assert lights._default._key == ""
        fake.requests.clear()
        assert not lights.set_scene("cody", "seated", api_key=KEY)["sent"]
        assert fake.requests == []
        cleared = lights.set_scene("cody", "seated")
        assert cleared["mode"] == "pretend" and not cleared["sent"]
        assert fake.requests == [] and not lights._default.has_key
        replacement = KEY + "-replacement"
        changed = lights.set_scene("cody", "seated", api_key=replacement)
        assert changed["mode"] == "govee" and changed["sent"]
        assert [r["method"] for r in fake.requests] == ["GET", "POST", "POST"]
        assert all({k.lower(): v for k, v in r["headers"].items()}["govee-api-key"] == replacement
                   for r in fake.requests)
        assert lights._default._key == ""
        fake.status = 401
        refused = lights.set_scene("cody", "seated", api_key=KEY)
        assert refused["error"] and not refused["sent"]
        assert lights._default._key == ""


def test_invalid_scene_inputs_cannot_echo_the_key(caplog: pytest.LogCaptureFixture, no_network) -> None:
    caplog.set_level(logging.DEBUG)
    room = lights.Lights(api_key=KEY)
    for persona, state in ((KEY, "invalid"), ("cody", KEY), (KEY, KEY)):
        result = room.set_scene(persona, state)
        assert result["error"] and not result["sent"]
        assert KEY not in json.dumps(result)
    assert KEY not in caplog.text and no_network == []


def test_a_silent_govee_returns_an_error_dict_within_three_seconds() -> None:
    with FakeGovee(slow_devices=6) as fake:
        started = time.monotonic()
        out = _govee(fake).set_scene("nikki", "seated")
        elapsed = time.monotonic() - started
    assert elapsed < 3.0, f"took {elapsed:.2f}s"
    assert out["sent"] is False and "time" in out["error"] and KEY not in json.dumps(out)

    with FakeGovee(slow_control=6) as fake:
        started = time.monotonic()
        out = _govee(fake).set_scene("nikki", "seated")
        elapsed = time.monotonic() - started
    assert elapsed < 3.0, f"took {elapsed:.2f}s"
    assert out["sent"] is False and out["error"]


def test_at_most_one_smooth_change_per_turn_and_no_flashing() -> None:
    with FakeGovee() as fake:
        room = _govee(fake)
        room.set_scene("vandal", "seated")
        assert len(fake.controls()) == 2, "one colour and one brightness command per light"
        fake.requests.clear()
        again = room.set_scene("vandal", "seated")
        assert again["sent"] is False and fake.requests == [], "the same scene sends nothing"

        room.set_scene("willow", "seated")  # dimmer: brightness goes down before the colour changes
        kinds = [c["payload"]["capability"]["instance"] for c in fake.controls()]
        assert kinds == ["brightness", "colorRgb"]

    with FakeGovee() as fake:
        room = _govee(fake, min_gap_seconds=60)
        room.set_scene("cody", "seated")
        fake.requests.clear()
        held = room.set_scene("vandal", "seated")
        assert held["sent"] is False and "flash" in held["note"] and fake.requests == []
        card = room.set_scene("vandal", "card")
        assert card["sent"] is True, "the card is never held back"
        instances = [c["payload"]["capability"]["instance"] for c in fake.controls()]
        assert instances.count("colorRgb") == 1 and len(instances) <= 2


def test_idle_can_switch_the_lights_off_instead(tmp_path: Path) -> None:
    custom = dict(RAW, idle=dict(RAW["idle"], power="off"))
    path = tmp_path / "colours.json"
    path.write_text(json.dumps(custom), encoding="utf-8")
    with FakeGovee() as fake:
        room = _govee(fake, colours_path=path)
        room.set_scene("cody", "seated")
        fake.requests.clear()
        room.set_scene(None, "idle")
        assert [c["payload"]["capability"] for c in fake.controls()] == [
            {"type": "devices.capabilities.on_off", "instance": "powerSwitch", "value": 0}]
        fake.requests.clear()
        room.set_scene("rowan", "seated")
        assert fake.controls()[0]["payload"]["capability"]["instance"] == "powerSwitch"
        assert fake.controls()[0]["payload"]["capability"]["value"] == 1


# ---------------------------------------------------------------- check 4: the card


def test_card_configuration_cannot_be_changed_to_a_nonwhite_colour_or_off(tmp_path: Path) -> None:
    path = tmp_path / "colours.json"
    for change in ({"colour": "#123456"}, {"colour": PERSONA_COLOURS["cody"]}, {"power": "off"}):
        custom = dict(RAW, card=dict(RAW["card"], **change))
        path.write_text(json.dumps(custom), encoding="utf-8")
        with pytest.raises(ValueError, match="card must be white and on"):
            lights.load_colours(path)
        result = lights.Lights(colours_path=path).set_scene("cody", "card")
        assert result["error"] and not result["sent"] and result["colour"] is None


def test_card_never_yields_a_character_colour_in_either_mode(no_network) -> None:
    for pid in (*lights.PERSONA_IDS, None, "unknown-persona"):
        out = lights.set_scene(pid, "card")
        assert out["colour"] == "#FFFFFF" and out["persona"] is None and out["error"] is None
    assert lights.scene_for_turn({"action": "HUMAN_ESCALATION", "agent_id": "vandal"}) == (None, "card")


def test_card_never_yields_a_character_colour_on_real_lights(monkeypatch: pytest.MonkeyPatch) -> None:
    with FakeGovee() as fake:
        for pid in (*lights.PERSONA_IDS, "unknown-persona"):
            room = _govee(fake)
            fake.requests.clear()
            out = room.set_scene(pid, "card")
            values = [c["payload"]["capability"]["value"] for c in fake.controls()
                      if c["payload"]["capability"]["instance"] == "colorRgb"]
            assert values == [0xFFFFFF], (pid, values)
            assert out["colour"] == "#FFFFFF" and out["persona"] is None


def test_the_lights_follow_the_policy_through_the_real_harness(tmp_path: Path, no_network) -> None:
    from secondsignal_harness import Harness
    from secondsignal_harness.adapters import FakeAdapter
    from secondsignal_harness.audit_log import AuditLog
    from secondsignal_harness.codex import CodexStore

    harness = Harness(ROSTER, FakeAdapter(name="fake", model_id="fake-1"), CodexStore(None),
                      audit_log=AuditLog(tmp_path / "audit.jsonl"))
    for pid in lights.PERSONA_IDS:
        turn = harness.speak(f"Could I talk to {ROSTER[pid].display_name}?")
        persona, state = lights.scene_for_turn(turn)
        if turn.agent_id:
            assert (persona, state) == (turn.agent_id, "seated"), "the seat is the policy's, not the button's"
        else:
            assert (persona, state) == (None, "idle")
    crisis = harness.speak("I don't want to be here anymore")
    assert crisis.action == "HUMAN_ESCALATION"
    persona, state = lights.scene_for_turn(crisis)
    assert (persona, state) == (None, "card")
    assert lights.set_scene(persona, state)["colour"] == "#FFFFFF"


def test_set_scene_in_background_never_holds_the_turn(no_network) -> None:
    got: list[dict[str, Any]] = []
    thread = lights.set_scene_in_background("ellis", "seated", got.append)
    thread.join(5)
    assert got and got[0]["colour"] == PERSONA_COLOURS["ellis"] and got[0]["sent"] is False


# ---------------------------------------------------------------- check 5: the page


class _Text(HTMLParser):
    """Visible text: skips <script>, <style>, <title> and anything under a hidden element."""

    VOID = {"meta", "link", "br", "img", "input", "hr", "path"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[bool] = []
        self.parts: list[str] = []
        self.elements: dict[str, dict[str, str | None]] = {}
        self.body: dict[str, str | None] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "body":
            self.body = a
        if a.get("id"):
            self.elements[a["id"]] = a  # type: ignore[index]
        if tag in self.VOID:
            return
        parent_hidden = bool(self.stack and self.stack[-1])
        self.stack.append(parent_hidden or "hidden" in a or tag in ("script", "style", "title", "head"))

    def handle_endtag(self, tag: str) -> None:
        if tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if not (self.stack and self.stack[-1]) and data.strip():
            self.parts.append(data.strip())

    @property
    def text(self) -> str:
        return " ".join(self.parts)


def _visible(html: str) -> _Text:
    parser = _Text()
    parser.feed(html)
    return parser


def _page_json(block_id: str) -> Any:
    html = PAGE.read_text(encoding="utf-8")
    start = html.index(f'<script type="application/json" id="{block_id}">')
    start = html.index(">", start) + 1
    return json.loads(html[start:html.index("</script>", start)])


def test_the_page_carries_the_repository_names_colours_and_notice() -> None:
    html = PAGE.read_text(encoding="utf-8")
    assert NOTICE in html and CARD_WORDS in html
    assert "http://" not in html and "https://" not in html, "the page fetches nothing from the internet"
    assert "'/api/state'" in html and "'/api/turn'" in html and "POLL_MS=2000" in html
    assert "Could I talk to ${profile.name}?" in html and "Ask for ${profile.name}" in html
    roster = _page_json("roster")
    assert [p["id"] for p in roster] == sorted(ROSTER)
    for entry in roster:
        profile = ROSTER[entry["id"]]
        assert entry["name"] == profile.display_name
        assert [tuple(x) for x in entry["plate"]] == [tuple(x) for x in profile.plate]
        for setting in ("as_written", "women", "men", "neither"):
            assert tuple(entry["names"][setting]) == tuple(profile.name_for(setting))
    assert _page_json("sigil-colors") == {k: v["colour"].upper() for k, v in RAW.items()}, (
        "sigils.html is out of step with sigil_colors.json: run python apps/talking_table/lights.py --sync-page")
    demo = (ROOT / "demo" / "index.html").read_text(encoding="utf-8")
    mark = (ROOT / "docs" / "assets" / "secondsignal-mark.svg").read_text(encoding="utf-8")
    for path_d in ("M 23 82 V 24.5 Q 23 21 26.5 21 H 73.5 Q 77 21 77 24.5 V 82",
                   "M 39 82 V 47 Q 39 44 42 44 H 58 Q 61 44 61 47 V 82"):
        assert path_d in mark and path_d in html, "the house mark, drawn as in docs/assets"
    for selector in (".plate-names,.plate-labels", ".form-name", ".form-label", ".selected"):
        rule = re.escape(selector) + r"\{([^}]+)\}"
        demo_rule, page_rule = re.search(rule, demo), re.search(rule, html)
        assert demo_rule and page_rule, f"plate style shared with demo/: {selector}"
        assert page_rule.group(1) == demo_rule.group(1), selector


def test_sigils_page_helper_carries_the_current_colours(tmp_path: Path) -> None:
    custom = dict(RAW, vandal=dict(RAW["vandal"], colour="#123456"))
    path = tmp_path / "c.json"
    path.write_text(json.dumps(custom), encoding="utf-8")
    assert '"vandal": "#123456"' in lights.sigils_page(path)


def test_lights_md_has_three_key_lines_and_the_seven_ask_addresses() -> None:
    text = LIGHTS_MD.read_text(encoding="utf-8")
    steps = [line for line in text.splitlines() if line[:3] in ("1. ", "2. ", "3. ")]
    assert [line[:2] for line in steps] == ["1.", "2.", "3."], "three plain lines on the key"
    assert "Apply for API Key" in steps[0]
    assert NOTICE in text
    for pid in ROSTER:
        assert f"sigils.html?ask={pid}" in text
    assert "Settings" in steps[2] and "Lights key" in steps[2] and "remember" in steps[2].lower()
    assert "GOVEE_API_KEY" not in text and ".secondsignal/govee.json" not in text
    assert "GET request in background" in text and "OFF" in text


class StubTable:
    """A tiny Talking Table: serves sigils.html, answers /api/state, takes /api/turn.

    Its "policy" is a fixed answer: whatever is asked for, it seats ``seats``,
    so a page that showed the asked-for name instead of the seated one fails.
    """

    def __init__(self, state: dict[str, Any], seats: str | None = None) -> None:
        self.state = dict(state)
        self.seats = seats
        self.turns: list[dict[str, Any]] = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                pass

            def _send(self, code: int, body: bytes, kind: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                if self.path.split("?")[0] == "/sigils.html":
                    return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
                if self.path == "/api/state":
                    return self._send(200, json.dumps(stub.state).encode(), "application/json")
                self._send(404, b"{}", "application/json")

            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                stub.turns.append({"path": self.path, "type": self.headers.get("Content-Type"),
                                   "body": json.loads(body or b"null")})
                if stub.seats:
                    stub.state = {"seated": stub.seats, "assist": None, "state": "seated",
                                  "presentation": "as_written"}
                self._send(200, b'{"ok": true}', "application/json")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/sigils.html"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def _browser() -> str | None:
    chosen = os.environ.get("SECONDSIGNAL_TEST_BROWSER")
    if chosen and Path(chosen).is_file():
        return chosen
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    for path in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if Path(path).is_file():
            return path
    return None


BROWSER = _browser()


_WINDOWS_BROWSER_FLAGS = [
    # Chrome's unattended Windows startup needs its automation defaults; the
    # dump-DOM/screenshot commands otherwise hang on this host. No extra test
    # package is needed and all browser assertions still run.
    "--disable-field-trial-config", "--disable-background-networking",
    "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows",
    "--disable-back-forward-cache", "--disable-breakpad", "--disable-client-side-phishing-detection",
    "--disable-component-extensions-with-background-pages", "--disable-component-update",
    "--no-default-browser-check", "--disable-default-apps", "--disable-dev-shm-usage",
    "--disable-edgeupdater", "--disable-extensions", "--allow-pre-commit-input",
    "--disable-hang-monitor", "--disable-ipc-flooding-protection", "--disable-popup-blocking",
    "--disable-prompt-on-repost", "--disable-renderer-backgrounding", "--disable-updater-scheduler",
    "--force-color-profile=srgb", "--metrics-recording-only", "--no-first-run",
    "--password-store=basic", "--use-mock-keychain", "--no-service-autorun", "--export-tagged-pdf",
    "--disable-search-engine-choice-screen", "--unsafely-disable-devtools-self-xss-warnings",
    "--edge-skip-compat-layer-relaunch", "--disable-infobars",
    "--disable-features=AvoidUnnecessaryBeforeUnloadCheckSync,BoundaryEventDispatchTracksNodeRemoval,"
    "DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,"
    "MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,BlockOriginHeaderModificationOnRedirect,"
    "Translate,AutoDeElevate,OptimizationHints,msForceBrowserSignIn,msEdgeUpdateLaunchServicesPreferredVersion",
    "--enable-features=CDPScreenshotNewSurface", "--disable-sync", "--headless=new", "--no-sandbox",
    "--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1",
]


def _run_browser(url: str, *, screenshot: Path | None = None, budget_ms: int = 5000,
                 size: tuple[int, int] = PHONE) -> str:
    assert BROWSER
    with tempfile.TemporaryDirectory() as profile:
        flags = _WINDOWS_BROWSER_FLAGS if sys.platform == "win32" else [
            "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            "--disable-background-networking", "--disable-component-update", "--disable-sync",
            "--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1",
        ]
        command = [BROWSER, *flags, f"--user-data-dir={profile}", f"--window-size={size[0]},{size[1]}", "--hide-scrollbars",
            "--force-device-scale-factor=1", f"--virtual-time-budget={budget_ms}",
        ]
        command += [f"--screenshot={screenshot}"] if screenshot else ["--dump-dom"]
        output, errors = Path(profile) / "stdout", Path(profile) / "stderr"
        # File-backed output avoids inherited child pipes keeping Python's
        # communicate() open after Chrome exits on Windows.
        with output.open("wb") as out, errors.open("wb") as err:
            process = subprocess.Popen(command + [url], stdout=out, stderr=err)
            try:
                process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
                process.kill()
                process.wait(timeout=5)
                raise
        stderr = errors.read_text(encoding="utf-8", errors="replace")
        stdout = output.read_text(encoding="utf-8", errors="replace")
        assert process.returncode == 0, stderr[-2000:]
        if screenshot:
            assert screenshot.is_file(), stderr[-2000:]
        return stdout


def _png_pixels(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    """A small PNG reader (8-bit RGB or RGBA, not interlaced): enough for Chrome's screenshots."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, width = 8, b"", 0
    height = depth = kind = 0
    while pos < len(data):
        length, tag = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, kind = struct.unpack(">IIBB", chunk[:10])
        elif tag == b"IDAT":
            idat += chunk
        pos += 12 + length
    assert depth == 8 and kind in (2, 6), (depth, kind)
    step = 3 if kind == 2 else 4
    raw = zlib.decompress(idat)
    stride = width * step
    rows: list[bytearray] = []
    prev = bytearray(stride)
    for y in range(height):
        filt = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            left = line[i - step] if i >= step else 0
            up = prev[i]
            corner = prev[i - step] if i >= step else 0
            if filt == 1:
                line[i] = (line[i] + left) & 255
            elif filt == 2:
                line[i] = (line[i] + up) & 255
            elif filt == 3:
                line[i] = (line[i] + (left + up) // 2) & 255
            elif filt == 4:
                p = left + up - corner
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - corner)
                line[i] = (line[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else corner)) & 255
        rows.append(line)
        prev = line
    pixels = [(row[i], row[i + 1], row[i + 2]) for row in rows for i in range(0, stride, step)]
    return width, height, pixels


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    return (int(hex_colour[1:3], 16), int(hex_colour[3:5], 16), int(hex_colour[5:7], 16))


def _keep(shot: Path) -> None:
    folder = os.environ.get("SECONDSIGNAL_LIGHTS_SHOTS")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        shutil.copy2(shot, Path(folder) / shot.name)


def _all_name_forms() -> set[str]:
    names = set()
    for profile in ROSTER.values():
        names.add(profile.display_name)
        names.update(name for name, _ in profile.plate)
    return names


SCENES = {
    "seated-vandal": {"seated": "vandal", "assist": None, "state": "seated", "presentation": "as_written"},
    "seated-willow-assist-cody": {"seated": "willow", "assist": "cody", "state": "seated", "presentation": "as_written"},
    "seated-ellis-men": {"seated": "ellis", "assist": None, "state": "seated", "presentation": "men"},
    # A hostile state: the card with a seat still set. The page must show no character.
    "card": {"seated": "vandal", "assist": "nikki", "state": "card", "presentation": "as_written"},
    "idle": {"seated": None, "assist": None, "state": "idle", "presentation": "as_written"},
}


def _check_scene(name: str, html: str) -> None:
    view = _visible(html)
    scene = SCENES[name]
    assert view.body.get("data-state") == scene["state"], (name, view.body)
    if scene["state"] == "card":
        assert CARD_WORDS in view.text
        leaked = [n for n in _all_name_forms() if n in view.text]
        assert not leaked, f"the card screen shows a character: {leaked}"
        assert "hidden" in view.elements["view-seated"] and "hidden" in view.elements["asks"]
        assert view.text.replace(NOTICE, "").strip() == CARD_WORDS, view.text
    else:
        assert NOTICE in view.text
    if scene["state"] == "seated":
        plate = view.elements["seated-plate"]
        assert plate.get("data-agent-id") == scene["seated"]
        r, g, b = _rgb(PERSONA_COLOURS[scene["seated"]])
        assert f"background: rgb({r}, {g}, {b})" in (plate.get("style") or "")
        assert ROSTER[scene["seated"]].display_name in view.text or any(
            n in view.text for n, _ in ROSTER[scene["seated"]].plate)
        if scene["assist"]:
            assert view.elements["assist-plate"].get("data-agent-id") == scene["assist"]
    if scene["state"] == "idle":
        assert "hidden" not in view.elements["view-idle"] and "Nobody is seated" in view.text


def _page_run_static_half() -> None:
    stub = StubTable(SCENES["seated-vandal"])
    try:
        with urllib.request.urlopen(stub.url, timeout=5) as response:
            served = response.read().decode("utf-8")
        with urllib.request.urlopen(stub.url.replace("/sigils.html", "/api/state"), timeout=5) as response:
            assert json.loads(response.read())["seated"] == "vandal"
    finally:
        stub.close()
    assert served == PAGE.read_text(encoding="utf-8")
    assert "new URLSearchParams(location.search).get('ask')" in served
    assert "JSON.stringify({text})" in served and "method:'POST'" in served


def test_sigils_page_against_a_stub_server_shows_plate_card_and_idle(tmp_path: Path) -> None:
    _page_run_static_half()
    if not BROWSER:
        pytest.skip("headless Chrome/Chromium/Edge is absent; screenshot browser check cannot run")

    def one(name: str) -> tuple[str, str, Path]:
        stub = StubTable(SCENES[name])
        try:
            html = _run_browser(stub.url)
            shot = tmp_path / f"sigils-390-{name}.png"
            _run_browser(stub.url, screenshot=shot)
            return name, html, shot
        finally:
            stub.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(one, SCENES))
    for name, html, shot in results:
        _check_scene(name, html)
        width, height, pixels = _png_pixels(shot)
        assert (width, height) == PHONE, (name, width, height)
        persona_pixels = {pid: pixels.count(_rgb(c)) for pid, c in PERSONA_COLOURS.items()}
        if name.startswith("seated-"):
            seated = SCENES[name]["seated"]
            assert persona_pixels[seated] > 0.15 * len(pixels), (name, persona_pixels[seated])
        if name == "card":
            assert pixels.count((255, 255, 255)) > 0.8 * len(pixels)
            assert not any(persona_pixels.values()), persona_pixels
        if name == "idle":
            assert pixels.count(_rgb("#A64527")) > 50, "the house mark's inner doorway"
        _keep(shot)


def test_sigils_ask_buttons_post_the_sentence_and_the_page_shows_the_policys_seat(tmp_path: Path) -> None:
    _page_run_static_half()
    if not BROWSER:
        pytest.skip("headless Chrome/Chromium/Edge is absent; screenshot browser check cannot run")

    def one(pid: str) -> tuple[str, list[dict[str, Any]], str]:
        # The stub's policy always seats someone else, so the page must follow the seat, not the ask.
        other = "cody" if pid != "cody" else "rowan"
        stub = StubTable(SCENES["idle"], seats=other)
        try:
            html = _run_browser(f"{stub.url}?ask={pid}")
            return pid, stub.turns, html
        finally:
            stub.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, sorted(ROSTER)))
    for pid, turns, html in results:
        assert turns == [{"path": "/api/turn", "type": "application/json",
                          "body": {"text": f"Could I talk to {ROSTER[pid].display_name}?"}}], (pid, turns)
        other = "cody" if pid != "cody" else "rowan"
        view = _visible(html)
        assert view.elements["seated-plate"].get("data-agent-id") == other, pid
        assert f"Could I talk to {ROSTER[pid].display_name}?" in view.text  # the status line

    stub = StubTable(SCENES["idle"], seats="vandal")
    try:
        shot = tmp_path / "sigils-390-ask-vandal.png"
        _run_browser(f"{stub.url}?ask=vandal", screenshot=shot)
        assert [t["body"] for t in stub.turns] == [{"text": "Could I talk to Vandal?"}]
    finally:
        stub.close()
    assert _png_pixels(shot)[0] == PHONE[0]
    _keep(shot)
