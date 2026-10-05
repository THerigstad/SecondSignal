"""The room lights: the seat the policy chose, shown as a colour in the room.

This module is a guest of the Talking Table. It never decides anything. The
policy layer decides who is seated; the Talking Table reads that decision and
calls one function here, once per turn:

    set_scene(persona_id, state, api_key=None)

``persona_id`` is one of the seven character ids (cody, ellis, nikki, rowan,
seren, vandal, willow) or None. ``state`` is "seated", "card" or "idle". The
return value is a plain dict saying what was done, or what would have been
done:

    {"mode": "pretend" | "govee", "state": ..., "persona": ...,
     "colour": "#RRGGBB" | None, "brightness": 0-100 | None,
     "devices": [...], "sent": True | False, "error": None | "..."}

Rules this file keeps (from the build order for the room lights):

* Pretend mode is the default and makes no network call at all. The key comes
  only from the function's argument, supplied by the Talking Table's Settings
  when "Lights on real bulbs" is on. No key means pretend mode; a non-empty
  key means Govee mode. The key is never read from an environment variable or
  file, never logged, never printed and never returned; it travels only in
  the Govee-API-Key header to Govee's own address.
* "card" is plain calm white and never a character colour, whatever id is
  passed. When the policy escalates, no character colour appears.
* At most one smooth change per turn: one colour command and one brightness
  command per light, never a loop, never a blink. A scene identical to the one
  already showing sends nothing. Two changes closer together than
  ``min_gap_seconds`` do not both go out (the card is exempt: it always goes).
* A light failure never touches a turn: every error comes back in the dict;
  nothing here raises into the caller.

The Govee calls follow Govee's current developer documentation, read on
29 September 2026:

    https://developer.govee.com/reference/get-you-devices      (discovery)
    https://developer.govee.com/reference/control-you-devices  (control)

    GET  https://openapi.api.govee.com/router/api/v1/user/devices
    POST https://openapi.api.govee.com/router/api/v1/device/control
         {"requestId": "<uuid>", "payload": {"sku": ..., "device": ...,
          "capability": {"type": "devices.capabilities.color_setting",
                         "instance": "colorRgb", "value": <0..16777215>}}}
         {"requestId": "<uuid>", "payload": {"sku": ..., "device": ...,
          "capability": {"type": "devices.capabilities.range",
                         "instance": "brightness", "value": <1..100>}}}
    Headers: Content-Type: application/json, Govee-API-Key: <key>

Standard library only. This is a prototype for the operator and adults he
knows. It is not a crisis service.
"""

from __future__ import annotations

import json
import hashlib
import logging
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "GOVEE_BASE_URL",
    "PERSONA_IDS",
    "STATES",
    "Lights",
    "load_colours",
    "scene_for_turn",
    "set_scene",
    "set_scene_in_background",
    "sigils_page",
]

HERE = Path(__file__).resolve().parent
COLOURS_FILE = HERE / "sigil_colors.json"
PAGE_FILE = HERE / "static" / "sigils.html"

PERSONA_IDS = ("cody", "ellis", "nikki", "rowan", "seren", "vandal", "willow")
STATES = ("seated", "card", "idle")

GOVEE_BASE_URL = "https://openapi.api.govee.com/router/api/v1"
GOVEE_HOST = "openapi.api.govee.com"
KEY_HEADER = "Govee-API-Key"

REQUEST_TIMEOUT_SECONDS = 2.0  # the build order's two-second timeout, per request
CALL_BUDGET_SECONDS = 2.8  # one set_scene never holds its caller longer than this
DEVICE_CACHE_SECONDS = 600.0
DEFAULT_MIN_GAP_SECONDS = 1.0

_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}

log = logging.getLogger("secondsignal.talking_table.lights")


# ----------------------------------------------------------------- colours


def load_colours(path: Path | str | None = None) -> dict[str, dict[str, Any]]:
    """Read sigil_colors.json and check it. Raises ValueError on a bad file.

    (Only this loader raises; set_scene turns the error into a dict.)
    """
    source = Path(path) if path is not None else COLOURS_FILE
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("sigil_colors.json must hold one object")
    out: dict[str, dict[str, Any]] = {}
    for name in (*PERSONA_IDS, "card", "idle"):
        entry = data.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"sigil_colors.json has no entry for {name!r}")
        colour = entry.get("colour")
        brightness = entry.get("brightness")
        if not isinstance(colour, str) or not _COLOUR.match(colour):
            raise ValueError(f"{name}: colour must look like #RRGGBB")
        if not isinstance(brightness, int) or isinstance(brightness, bool) or not 0 <= brightness <= 100:
            raise ValueError(f"{name}: brightness must be a whole number from 0 to 100")
        power = entry.get("power", "on")
        if power not in ("on", "off"):
            raise ValueError(f"{name}: power must be 'on' or 'off'")
        if name in PERSONA_IDS and power == "off":
            raise ValueError(f"{name}: a character's light cannot be off")
        out[name] = {"colour": colour.upper(), "brightness": brightness, "power": power}
    persona_colours = {out[p]["colour"] for p in PERSONA_IDS}
    if out["card"]["colour"] != "#FFFFFF" or out["card"]["power"] != "on":
        raise ValueError("the card must be white and on")
    if out["card"]["colour"] in persona_colours:
        raise ValueError("the card's white must not be any character's colour")
    return out


def _rgb_number(colour: str) -> int:
    return int(colour[1:], 16)


# ----------------------------------------------------------------- the turn


def scene_for_turn(turn: Any) -> tuple[str | None, str]:
    """(persona_id, state) from a harness Turn, following the policy's decision only.

    Mirrors the harness's own three branches: the gate fired -> "card"; the
    record seats nobody -> "idle"; the record seats a persona -> "seated".
    Accepts a secondsignal_harness Turn or a dict with the same fields.
    """
    def field(name: str) -> Any:
        if isinstance(turn, Mapping):
            return turn.get(name)
        return getattr(turn, name, None)

    if str(field("action") or "") == "HUMAN_ESCALATION":
        return None, "card"
    agent_id = field("agent_id")
    if isinstance(agent_id, str) and agent_id in PERSONA_IDS:
        return agent_id, "seated"
    return None, "idle"


# ----------------------------------------------------------------- the lights


class Lights:
    """One room's lights. Thread-safe; build one and reuse it."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        colours_path: Path | str | None = None,
        base_url: str = GOVEE_BASE_URL,
        min_gap_seconds: float = DEFAULT_MIN_GAP_SECONDS,
        request_timeout: float = REQUEST_TIMEOUT_SECONDS,
        call_budget: float = CALL_BUDGET_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._colours_path = colours_path
        self._key = api_key.strip() if isinstance(api_key, str) else ""
        self._base_url, self._base_error = _checked_base_url(base_url)
        self._min_gap = max(0.0, float(min_gap_seconds))
        self._timeout = float(request_timeout)
        self._budget = float(call_budget)
        self._clock = clock
        self._lock = threading.Lock()
        self._devices: list[dict[str, Any]] | None = None
        self._devices_at = 0.0
        self._last_scene: tuple[str, int, str] | None = None
        self._last_change_at: float | None = None

    # The key never leaves this object except in the Govee-API-Key header.
    def __repr__(self) -> str:
        return f"Lights(mode={self.mode!r})"

    @property
    def has_key(self) -> bool:
        return bool(self._key)

    @property
    def mode(self) -> str:
        return "govee" if self._key else "pretend"

    def set_scene(self, persona_id: str | None, state: str) -> dict[str, Any]:
        try:
            with self._lock:
                return self._set_scene(persona_id, state)
        except Exception as exc:  # a light failure never touches a turn
            return self._result(state, persona_id, None, None, [], False,
                                self._clean(f"unexpected {type(exc).__name__}"))

    # ------------------------------------------------------------- internals

    def _set_scene(self, persona_id: str | None, state: str) -> dict[str, Any]:
        if state not in STATES:
            return self._result(state, persona_id, None, None, [], False,
                                f"state must be one of {', '.join(STATES)}")
        if state == "seated" and persona_id is not None and persona_id not in PERSONA_IDS:
            return self._result(state, None, None, None, [], False, "unknown persona id")
        if state == "seated" and persona_id is None:
            return self._result(state, None, None, None, [], False, "'seated' needs a persona id")
        try:
            colours = load_colours(self._colours_path)
        except (OSError, ValueError) as exc:
            return self._result(state, persona_id, None, None, [], False,
                                self._clean(f"colours file: {exc}"))

        # "card" and "idle" never take a character colour, whatever id arrives.
        name = persona_id if state == "seated" else state
        persona = persona_id if state == "seated" else None
        entry = colours[name]  # type: ignore[index]
        colour, brightness, power = entry["colour"], entry["brightness"], entry["power"]

        if self.mode == "pretend":
            return self._result(state, persona, colour, brightness, [], False, None)

        if self._base_error:
            return self._result(state, persona, colour, brightness, [], False, self._base_error)
        scene = (colour, brightness, power)
        now = self._clock()
        if scene == self._last_scene:
            out = self._result(state, persona, colour, brightness, [], False, None)
            out["note"] = "unchanged; nothing sent"
            return out
        if (state != "card" and self._last_change_at is not None
                and now - self._last_change_at < self._min_gap):
            out = self._result(state, persona, colour, brightness, [], False, None)
            out["note"] = "too soon after the last change; held back so the lights never flash"
            return out

        deadline = now + self._budget
        devices, error = self._discover(deadline)
        if error:
            return self._result(state, persona, colour, brightness, [], False, error)
        if not devices:
            return self._result(state, persona, colour, brightness, [], False,
                                "no Govee light that takes a colour was found")

        previous = self._last_scene
        touched: list[str] = []
        any_sent = False
        for device in devices:
            commands = self._commands(device, scene, previous)
            for capability in commands:
                ok, error = self._control(device, capability, deadline)
                any_sent = any_sent or ok
                if error:
                    if any_sent:
                        self._last_change_at = self._clock()
                        self._last_scene = None  # unknown now; the next scene resends
                    return self._result(state, persona, colour, brightness,
                                        touched + [device["label"]], any_sent, error)
            touched.append(device["label"])
        self._last_scene = scene
        self._last_change_at = self._clock()
        return self._result(state, persona, colour, brightness, touched, any_sent, None)

    def _commands(self, device: dict[str, Any], scene: tuple[str, int, str],
                  previous: tuple[str, int, str] | None) -> list[dict[str, Any]]:
        """One change for this light: colour and brightness, ordered so it never jumps bright."""
        colour, brightness, power = scene
        if power == "off":
            return [_capability("devices.capabilities.on_off", "powerSwitch", 0)] if device["power"] else []
        out: list[dict[str, Any]] = []
        if previous is not None and previous[2] == "off" and device["power"]:
            out.append(_capability("devices.capabilities.on_off", "powerSwitch", 1))
        colour_cmd = _capability("devices.capabilities.color_setting", "colorRgb", _rgb_number(colour))
        bright_cmd = None
        if device["brightness"] is not None:
            low, high = device["brightness"]
            bright_cmd = _capability("devices.capabilities.range", "brightness",
                                     max(low, min(high, brightness)))
        dimming = previous is not None and brightness < previous[1]
        if bright_cmd and dimming:
            out += [bright_cmd, colour_cmd]  # dim first, then recolour: no bright flash
        else:
            out += [colour_cmd] + ([bright_cmd] if bright_cmd else [])
        return out

    def _discover(self, deadline: float) -> tuple[list[dict[str, Any]], str | None]:
        now = self._clock()
        if self._devices is not None and now - self._devices_at < DEVICE_CACHE_SECONDS:
            return self._devices, None
        body, error = self._request("GET", "/user/devices", None, deadline)
        if error:
            return [], error
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list):
            return [], "Govee's device list was not in the documented shape"
        devices: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            sku, device_id = item.get("sku"), item.get("device")
            if not isinstance(sku, str) or not isinstance(device_id, str):
                continue
            raw_caps = item.get("capabilities")
            caps: list[Any] = raw_caps if isinstance(raw_caps, list) else []
            pairs = {(c.get("type"), c.get("instance")): c for c in caps if isinstance(c, dict)}
            if ("devices.capabilities.color_setting", "colorRgb") not in pairs:
                continue  # a socket or sensor: nothing to colour
            bright = pairs.get(("devices.capabilities.range", "brightness"))
            bounds = None
            if bright is not None:
                rng = (bright.get("parameters") or {}).get("range") or {}
                low, high = rng.get("min", 1), rng.get("max", 100)
                bounds = (int(low) if isinstance(low, int) else 1, int(high) if isinstance(high, int) else 100)
            name = item.get("deviceName")
            devices.append({
                "sku": sku, "device": device_id,
                "label": name if isinstance(name, str) and name else f"{sku} {device_id}",
                "brightness": bounds,
                "power": ("devices.capabilities.on_off", "powerSwitch") in pairs,
            })
        self._devices, self._devices_at = devices, now
        return devices, None

    def _control(self, device: dict[str, Any], capability: dict[str, Any],
                 deadline: float) -> tuple[bool, str | None]:
        payload = {
            "requestId": str(uuid.uuid4()),
            "payload": {"sku": device["sku"], "device": device["device"], "capability": capability},
        }
        body, error = self._request("POST", "/device/control", payload, deadline)
        if error:
            if error.startswith("Govee answered 404"):
                self._devices = None  # the list changed; rediscover next time
            return False, error
        return True, None

    def _request(self, method: str, path: str, payload: dict[str, Any] | None,
                 deadline: float) -> tuple[Any, str | None]:
        remaining = deadline - self._clock()
        if remaining <= 0.05:
            return None, "Govee did not answer within the time allowed"
        timeout = min(self._timeout, remaining)
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(self._base_url + path, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        request.add_header(KEY_HEADER, self._key or "")
        try:
            opener = urllib.request.build_opener(_NoRedirect, urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=timeout) as response:
                raw = response.read(2_000_000)
        except urllib.error.HTTPError as exc:
            reason = {401: "the key was refused", 429: "too many requests; Govee's rate limit"}.get(exc.code, "")
            return None, self._clean(f"Govee answered {exc.code}" + (f" ({reason})" if reason else ""))
        except (TimeoutError, OSError) as exc:  # URLError and socket.timeout are OSErrors
            text = str(getattr(exc, "reason", exc))
            if isinstance(exc, TimeoutError) or "timed out" in text.lower():
                return None, "Govee did not answer within the time allowed"
            return None, self._clean(f"could not reach Govee ({type(exc).__name__})")
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            return None, "Govee's answer was not JSON"
        if self._contains_key(body):
            return None, "Govee's answer contained a credential and was refused"
        code = body.get("code") if isinstance(body, dict) else None
        if isinstance(code, int) and code != 200:
            return None, self._clean(f"Govee answered code {code}")
        return body, None

    def _clean(self, text: str) -> str:
        if self._key:
            text = text.replace(self._key, "[key withheld]")
        return text

    def _contains_key(self, value: Any) -> bool:
        if isinstance(value, str):
            return bool(self._key and self._key in value)
        if isinstance(value, dict):
            return any(self._contains_key(k) or self._contains_key(v) for k, v in value.items())
        if isinstance(value, list):
            return any(self._contains_key(v) for v in value)
        return False

    def _result(self, state: str, persona: str | None, colour: str | None, brightness: int | None,
                devices: list[str], sent: bool, error: str | None) -> dict[str, Any]:
        out = {
            "mode": self.mode,
            "state": self._clean(state) if isinstance(state, str) else None,
            "persona": self._clean(persona) if isinstance(persona, str) else None,
            "colour": colour,
            "brightness": brightness,
            "devices": [self._clean(device) for device in devices],
            "sent": bool(sent),
            "error": self._clean(error) if error else None,
        }
        if error:
            log.info("lights: %s", out["error"])
        return out


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect could carry the key header to another host; refuse every one."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def _capability(kind: str, instance: str, value: Any) -> dict[str, Any]:
    return {"type": kind, "instance": instance, "value": value}


def _checked_base_url(base_url: str) -> tuple[str, str | None]:
    """The key goes only to Govee's own address (or a loopback fake in a test)."""
    parts = urllib.parse.urlsplit(base_url)
    host = (parts.hostname or "").lower()
    if parts.username or parts.password or parts.query or parts.fragment:
        return GOVEE_BASE_URL, "refusing a lights address containing credentials, a query or a fragment"
    if parts.scheme == "https" and host == GOVEE_HOST:
        return base_url.rstrip("/"), None
    if parts.scheme in ("http", "https") and host in _LOOPBACK:
        return base_url.rstrip("/"), None
    return GOVEE_BASE_URL, "refusing to send the key anywhere but Govee's own address"


# ----------------------------------------------------------------- module level

_default: Lights | None = None
_default_key_digest: bytes | None = None
_default_lock = threading.Lock()


def _default_lights(api_key: str | None = None) -> Lights:
    """Select the room under _default_lock; retain only a key fingerprint."""
    global _default, _default_key_digest
    key = api_key.strip() if isinstance(api_key, str) else ""
    digest = hashlib.sha256(key.encode("utf-8")).digest() if key else None
    # A cleared/changed Settings key must never reuse another account's
    # device cache or leave a two-argument call in Govee mode.
    if _default is None or _default_key_digest != digest:
        _default = Lights(api_key=key)
        _default_key_digest = digest
    _default._key = key
    return _default


def set_scene(persona_id: str | None, state: str, api_key: str | None = None) -> dict[str, Any]:
    """The contract: show the seat the policy chose. Returns a dict; never raises."""
    try:
        with _default_lock:
            room = _default_lights(api_key)
            try:
                return room.set_scene(persona_id, state)
            finally:
                # Settings owns the credential. Keep scene/device caches, but
                # no plaintext key between calls, even after a failed request.
                room._key = ""
    except Exception as exc:  # pragma: no cover - belt and braces
        return {"mode": "govee" if isinstance(api_key, str) and api_key.strip() else "pretend",
                "state": state if state in STATES else None, "persona": None, "colour": None,
                "brightness": None, "devices": [], "sent": False,
                "error": f"unexpected {type(exc).__name__}"}


def set_scene_in_background(persona_id: str | None, state: str,
                            done: Callable[[dict[str, Any]], None] | None = None, *,
                            api_key: str | None = None) -> threading.Thread:
    """The same call on a daemon thread, so a slow light never holds a turn."""
    def run() -> None:
        result = set_scene(persona_id, state, api_key=api_key)
        if done is not None:
            try:
                done(result)
            except Exception:  # the caller's callback must not surface here either
                log.info("lights: the completion callback raised")

    thread = threading.Thread(target=run, name="room-lights", daemon=True)
    thread.start()
    return thread


def sigils_page(colours_path: Path | str | None = None) -> str:
    """sigils.html with the current sigil_colors.json copied into its colour block."""
    page = PAGE_FILE.read_text(encoding="utf-8")
    colours = load_colours(colours_path)
    block = json.dumps({k: v["colour"] for k, v in colours.items()}, indent=None, sort_keys=True)
    return _COLOUR_BLOCK.sub(lambda m: m.group(1) + block + m.group(2), page, count=1)


_COLOUR_BLOCK = re.compile(r'(<script type="application/json" id="sigil-colors">).*?(</script>)', re.S)


def _sync_page() -> int:
    PAGE_FILE.write_text(sigils_page(), encoding="utf-8")
    print("sigils.html now carries the colours in sigil_colors.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="The room lights (a prototype, not a crisis service).")
    parser.add_argument("persona", nargs="?", default=None, help="cody, ellis, nikki, rowan, seren, vandal, willow, or none")
    parser.add_argument("state", nargs="?", default="idle", choices=STATES)
    parser.add_argument("--sync-page", action="store_true", help="copy sigil_colors.json into static/sigils.html")
    args = parser.parse_args(argv)
    if args.sync_page:
        return _sync_page()
    persona = None if args.persona in (None, "none", "") else args.persona
    print(json.dumps(set_scene(persona, args.state), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
