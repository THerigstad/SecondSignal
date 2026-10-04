"""Offline voice acceptance: real table gates, FakeAdapter and fake speech I/O.

The production cultural layer is unchanged. Only tests needing a released reply
substitute an explicit all-pass verdict; all real policy and storage steps run.
"""
from __future__ import annotations

import importlib
import json
import threading
import time
from email.message import Message
from pathlib import Path

import pytest
from test_talking_table import live, request

from apps.talking_table import server
from secondsignal.jr import AuditVerdict, LayerVerdicts
from secondsignal_harness import FakeAdapter
from secondsignal_harness.adapters import AdapterError

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "Help me make a plan for my work tomorrow."
TEXT = "Start with one small task tomorrow."
VOICE_KEY = "sk-VOICE-TEST-NEVER-LOG"
MODEL_KEY = "sk-MODEL-TEST-NEVER-LOG"
AUDIO = b"ID3\x04\x00\x00\x00\x00\x00\x00\xff\xfb\x90\x00"


@pytest.fixture(autouse=True)
def no_vendor_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("The test attempted an unmocked vendor call.")
    monkeypatch.setattr(server.urllib.request, "build_opener", refused)


@pytest.fixture
def app(tmp_path):
    instance = server.TableApp(data_dir=tmp_path / "data")
    instance.speech_calls = []
    def fake(voice_id, text, key):
        instance.speech_calls.append((voice_id, text, key))
        return "audio/mpeg", AUDIO
    instance.speech_transport = fake
    try:
        yield instance
    finally:
        instance.close()


@pytest.fixture
def all_pass(monkeypatch):
    module = importlib.import_module("secondsignal_harness.harness")
    def audit(req):
        return AuditVerdict(LayerVerdicts(cultural="PASS"), "PASS", "SHIP", req.payload_hash)
    monkeypatch.setattr(module, "audit", audit)
    return module


def enable(app, **overrides):
    settings = {"voice_enabled": True, "voice_key": VOICE_KEY,
                "voice_slots": {persona: {p: "fixture_" + persona + "_" + p
                                          for p in sorted(server.PRESENTATIONS)}
                                for persona in app.roster}}
    settings.update(overrides)
    app.update_settings(settings)
    app.harness.adapter = FakeAdapter(script=(TEXT,))


def released(app):
    result = app.turn(PROMPT)
    assert result["kind"] == "reply"
    assert result["speech_token"]
    return result


def crisis_fixture():
    document = json.loads((ROOT / "evals/cases/safety_gate.json").read_text(encoding="utf-8"))
    return next(case["text"] for case in document["cases"] if case["id"] == "crisis-direct")


def test_voice_defaults_have_all_28_empty_slots_and_no_public_key(app):
    config = app.config()
    settings = config["settings"]
    assert len(settings["voice_slots"]) == len(app.roster) == 7
    assert all(set(slots) == server.PRESENTATIONS and set(slots.values()) == {""}
               for slots in settings["voice_slots"].values())
    assert not settings["voice_enabled"] and not settings["voice_ready"]
    assert not settings["voice_key_set"] and not settings["voice_remember"]
    assert "voice_key" not in settings
    assert config["state"]["voice_revision"] > 0
    settings["voice_slots"][next(iter(app.roster))]["men"] = "changed"
    assert app.config()["settings"]["voice_slots"] != settings["voice_slots"]


@pytest.mark.parametrize("missing", ["key", "slot", "enabled", "presentation"])
def test_voice_stays_off_until_enabled_key_and_current_slot(app, all_pass, missing):
    enable(app)
    if missing == "key":
        app.update_settings({"clear_voice_key": True})
    elif missing == "enabled":
        app.update_settings({"voice_enabled": False})
    else:
        app.update_settings({"voice_slots": {p: {"as_written": ""} for p in app.roster}})
    app.harness.adapter = FakeAdapter(script=(TEXT,))
    assert not app.config()["settings"]["voice_ready"]
    assert app.turn(PROMPT)["speech_token"] is None
    assert app.speech_calls == []


@pytest.mark.parametrize("presentation", sorted(server.PRESENTATIONS))
def test_only_audited_persona_text_is_sent_with_its_exact_slot(app, all_pass, presentation):
    enable(app, presentation=presentation)
    result = released(app)
    raw = app.voice({"speech_token": result["speech_token"]})
    assert raw == AUDIO
    assert app.speech_calls == [("fixture_" + result["persona"] + "_" + presentation, TEXT, VOICE_KEY)]
    with pytest.raises(server.InputError, match="voice is unavailable"):
        app.voice({"speech_token": result["speech_token"]})
    assert len(app.speech_calls) == 1
    assert VOICE_KEY not in json.dumps(result)
    rows = app.audit_path.read_text(encoding="utf-8")
    assert result["speech_token"] not in rows and VOICE_KEY not in rows


def test_request_cannot_choose_its_own_text_persona_or_forge_a_token(app, all_pass):
    enable(app)
    token = released(app)["speech_token"]
    for payload in ({"text": TEXT}, {"speech_token": token, "text": TEXT},
                    {"speech_token": token, "persona": "house"}, {},
                    {"speech_token": "z" * 43}, {"speech_token": []}):
        with pytest.raises(server.InputError, match="voice is unavailable"):
            app.voice(payload)
    assert not app.speech_calls
    assert app.voice({"speech_token": token}) == AUDIO


@pytest.mark.parametrize("change", ["turn", "settings", "reset", "card", "circle", "forget"])
def test_capabilities_are_invalidated_by_every_conversation_change(app, all_pass, change):
    enable(app)
    first = released(app)
    old = app.state["voice_revision"]
    if change == "turn":
        app.turn(PROMPT)
    elif change == "card":
        result = app.turn(crisis_fixture())
        assert result["kind"] == "card" and result["speech_token"] is None
    elif change == "reset":
        app.reset()
    else:
        app.update_settings({"circle": {"operator_circle": True},
                             "forget": {"clear_voice_key": True},
                             "settings": {"presentation": "women"}}[change])
    assert app.state["voice_revision"] > old
    with pytest.raises(server.InputError):
        app.voice({"speech_token": first["speech_token"]})
    assert not app.speech_calls


# Ruling 6 of 3 October 2026: operator-circle replies speak while the mode is on.
# This test used to assert that an operator-circle release never receives a
# token; that half now lives in test_an_operator_circle_reply_speaks_only_with_the_mode_on.
def test_the_silent_kinds_stay_silent_withheld_house_failure_high_risk_and_the_card(app):
    enable(app)
    withheld = app.turn(PROMPT)
    assert withheld["kind"] == "withheld" and withheld["speech_token"] is None
    house = app.turn("hello")
    assert house["kind"] == "house" and house["persona"] is None
    assert house["speech_token"] is None
    app.harness.adapter = FakeAdapter(script=(AdapterError(VOICE_KEY),))
    failure = app.turn(PROMPT)
    assert failure["kind"] != "reply" and failure["speech_token"] is None
    card = app.turn(crisis_fixture())
    assert card["kind"] == "card" and card["adapter_calls"] == 0 and card["speech_token"] is None
    assert card["state"]["state"] == "card"
    # The turn after a card is a high-risk turn for the audit (escalated_last_turn),
    # so with the cultural layer unlocked it is withheld in operator-circle mode too.
    app.update_settings({"operator_circle": True})
    app.harness.adapter = FakeAdapter(script=(TEXT,))
    high_risk = app.turn(PROMPT)
    assert high_risk["kind"] == "withheld" and high_risk["release_reason"] == "withheld"
    assert high_risk["verdict"]["risk_class"] == "high"
    assert high_risk["speech_token"] is None
    assert app.speech_calls == []


def test_an_operator_circle_reply_speaks_only_with_the_mode_on(app):
    # Ruling 6 of 3 October 2026: operator-circle replies speak while the mode is on.
    enable(app)
    withheld = app.turn(PROMPT)
    assert withheld["kind"] == "withheld" and withheld["cultural_only"] is True
    assert withheld["speech_token"] is None
    app.update_settings({"operator_circle": True})
    app.harness.adapter = FakeAdapter(script=(TEXT,))
    circle = app.turn(PROMPT)
    assert circle["kind"] == "reply" and circle["release_reason"] == "operator_circle"
    assert circle["verdict"]["status"] == "WITHHOLD" and circle["verdict"]["risk_class"] == "normal"
    assert circle["state"]["operator_circle"] is True and circle["state"]["voice_ready"] is True
    assert circle["speech_token"]
    assert app.voice({"speech_token": circle["speech_token"]}) == AUDIO
    assert app.speech_calls == [("fixture_" + circle["persona"] + "_as_written", TEXT, VOICE_KEY)]
    # The label the screen already shows travels with the turn, never from the browser.
    assert circle["release_reason"] == "operator_circle" and "speech_text" not in circle
    # Only with the mode on: a token issued in the mode dies when the mode goes off.
    app.harness.adapter = FakeAdapter(script=(TEXT,))
    second = app.turn(PROMPT)
    assert second["speech_token"]
    app.update_settings({"operator_circle": False})
    with pytest.raises(server.InputError, match="voice is unavailable"):
        app.voice({"speech_token": second["speech_token"]})
    app.harness.adapter = FakeAdapter(script=(TEXT,))
    off = app.turn(PROMPT)
    assert off["kind"] == "withheld" and off["speech_token"] is None
    assert len(app.speech_calls) == 1


@pytest.mark.parametrize("flaw", ["mode_off_label", "risk_high", "ethical_fail", "cultural_pass"])
def test_an_operator_circle_release_is_checked_against_its_own_verdict(app, monkeypatch, flaw):
    """The Table trusts no label alone: a turn marked operator_circle speaks only
    when the verdict is the one the harness's rule 7 releases (ruling 6)."""
    module = importlib.import_module("secondsignal_harness.harness")
    layers = dict(logical="PASS", semantic="PASS", cultural="INCONCLUSIVE", ethical="PASS")
    risk = "normal"
    if flaw == "risk_high":
        risk = "high"
    elif flaw == "ethical_fail":
        layers["ethical"] = "FAIL"
    elif flaw == "cultural_pass":
        layers["cultural"] = "PASS"
    def audit(req):
        return AuditVerdict(LayerVerdicts(**layers), "ESCALATE", "WITHHOLD", req.payload_hash,
                            risk_class=risk)
    monkeypatch.setattr(module, "audit", audit)
    enable(app, operator_circle=flaw != "mode_off_label")
    real_release = module.Harness._release
    def labelled(self, status, layer_values, risk_class):
        return True, module.RELEASE_OPERATOR_CIRCLE
    monkeypatch.setattr(module.Harness, "_release", labelled)
    result = app.turn(PROMPT)
    assert result["kind"] == "reply" and result["release_reason"] == "operator_circle"
    assert result["speech_token"] is None
    monkeypatch.setattr(module.Harness, "_release", real_release)
    assert app.speech_calls == []


@pytest.mark.parametrize("layer", ["logical", "semantic", "cultural", "ethical"])
def test_even_ship_requires_all_four_layers_to_pass(app, all_pass, monkeypatch, layer):
    def inconsistent(req):
        layers = dict(logical="PASS", semantic="PASS", cultural="PASS", ethical="PASS")
        layers[layer] = "INCONCLUSIVE"
        return AuditVerdict(LayerVerdicts(**layers), "PASS", "SHIP", req.payload_hash)
    monkeypatch.setattr(all_pass, "audit", inconsistent)
    enable(app)
    assert app.turn(PROMPT)["speech_token"] is None
    assert not app.speech_calls


def test_an_all_pass_reply_speaks_in_operator_circle_mode_too(app, all_pass):
    # Ruling 6 of 3 October 2026: operator-circle replies speak while the mode is on.
    # Before the ruling this test asserted that the mode silenced even a shipped reply.
    enable(app, operator_circle=True)
    result = app.turn(PROMPT)
    assert result["kind"] == "reply" and result["release_reason"] == "ship"
    assert result["speech_token"]
    assert app.voice({"speech_token": result["speech_token"]}) == AUDIO
    assert app.speech_calls == [("fixture_" + result["persona"] + "_as_written", TEXT, VOICE_KEY)]


def test_reflected_current_previous_and_new_keys_are_rejected_everywhere(app, all_pass, caplog):
    enable(app)
    persona = next(iter(app.roster))
    for secret in (VOICE_KEY, MODEL_KEY):
        app.update_settings({"key": MODEL_KEY})
        for proposed in ({"model": secret}, {"url": secret},
                         {"voice_slots": {persona: {"men": secret}}}):
            with pytest.raises(server.InputError):
                app.update_settings(proposed)
    for secret in ('sk-new-voice-secret', 'sk-"quoted-secret', 'sk-\\backslash-secret', 'sk-\u00e9-secret'):
        with pytest.raises(server.InputError):
            app.update_settings({"voice_key": secret, "model": secret})
    app.update_settings({"clear_voice_key": True, "clear_key": True})
    for secret in (VOICE_KEY, MODEL_KEY):
        with pytest.raises(server.InputError):
            app.turn(secret)
        app.harness.adapter = FakeAdapter(script=(secret,))
        body = app.turn(PROMPT)
        assert body["speech_token"] is None and secret not in json.dumps(body)
    for secret in (VOICE_KEY, MODEL_KEY):
        assert secret not in json.dumps(app.config()) + caplog.text
        assert all(secret.encode() not in file.read_bytes()
                   for file in app.data_dir.rglob("*") if file.is_file())


# Night Builds Review of 30 September 2026, required fix 4: the last two cases
# named a character that is not on the roster, so they failed on the roster
# check instead of the check they claim to test. They now use a roster name
# and each case names the refusal it expects.
@pytest.mark.parametrize("field,value,refusal", [
    ("voice_enabled", 1, "switch must be on or off"),
    ("voice_remember", "true", "switch must be on or off"),
    ("voice_key", [], "voice key must be text"),
    ("voice_slots", [], "listed character"),
    ("voice_slots", {"house": {"men": "id"}}, "listed character"),
    ("voice_slots", {"willow": {"unknown": "id"}}, "listed presentation"),
    ("voice_slots", {"willow": {"men": "../bad"}}, "letters, digits, underscores or hyphens"),
    ("voice_slots", {"willow": {"men": "x" * 129}}, "letters, digits, underscores or hyphens"),
])
def test_voice_settings_validate_types_and_roster(app, field, value, refusal):
    assert all(persona in app.roster for persona in ("willow",))
    with pytest.raises(server.InputError, match=refusal):
        app.update_settings({field: value})
    assert app.settings["voice_slots"]["willow"]["men"] == ""


@pytest.mark.parametrize("model_remember,voice_remember", [(False, False), (True, False),
                                                          (False, True), (True, True)])
def test_model_and_voice_remember_are_independent(app, monkeypatch, model_remember, voice_remember):
    calls = []
    def protect(value, *, decrypt=False):
        calls.append(decrypt)
        return bytes(byte ^ 0xa5 for byte in value)
    monkeypatch.setattr(server, "_secret_blob", protect)
    enable(app, key=MODEL_KEY, remember=model_remember, voice_remember=voice_remember)
    stored = app.settings_path.read_text(encoding="utf-8") if app.settings_path.exists() else ""
    assert (app.settings_path.exists()) is (model_remember or voice_remember)
    assert VOICE_KEY not in stored and MODEL_KEY not in stored
    saved = json.loads(stored) if stored else {}
    assert ("key_blob" in saved) is model_remember
    assert ("voice_key_blob" in saved) is voice_remember
    second = server.TableApp(data_dir=app.data_dir)
    try:
        assert second.key == (MODEL_KEY if model_remember else "")
        assert second.voice_key == (VOICE_KEY if voice_remember else "")
        app.reset()
        assert app.key == second.key and app.voice_key == second.voice_key
        second.update_settings({"remember": False, "voice_remember": False,
                                "clear_key": True, "clear_voice_key": True})
        assert not second.settings_path.exists()
        assert second.key == second.voice_key == ""
    finally:
        second.close()


def test_voice_protection_failure_does_not_adopt_or_write_key(app, monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise RuntimeError(VOICE_KEY)
    monkeypatch.setattr(server, "_secret_blob", broken)
    with pytest.raises(server.InputError) as error:
        app.update_settings({"voice_key": VOICE_KEY, "voice_remember": True})
    assert app.voice_key == "" and not app.settings["voice_remember"]
    assert not app.settings_path.exists() and VOICE_KEY not in str(error.value) + caplog.text


@pytest.mark.parametrize("answer", [("text/html", AUDIO), ("audio/mpeg", b""),
                                   ("audio/mpeg", b"<script>bad</script>"),
                                   ("audio/mpeg", b"ID3" + VOICE_KEY.encode()),
                                   ("audio/mpeg", "not bytes"), None])
def test_fake_endpoint_untrusted_responses_fail_closed(app, all_pass, answer, caplog):
    enable(app)
    token = released(app)["speech_token"]
    app.speech_transport = lambda *args: answer
    with pytest.raises(server.InputError) as error:
        app.voice({"speech_token": token})
    assert str(error.value) == server.VOICE_ERROR and VOICE_KEY not in caplog.text


def test_oversized_and_both_current_secret_audio_are_refused(app, all_pass, monkeypatch):
    enable(app, key=MODEL_KEY)
    monkeypatch.setattr(server, "MAX_AUDIO", 100)
    for raw in (b"ID3" + b"x" * 101, b"ID3" + VOICE_KEY.encode(), b"ID3" + MODEL_KEY.encode()):
        token = released(app)["speech_token"]
        app.speech_transport = lambda *args: ("audio/mpeg", raw)
        with pytest.raises(server.InputError):
            app.voice({"speech_token": token})


def test_large_audio_validation_does_not_run_text_fingerprint_scan(app, all_pass, monkeypatch):
    enable(app, key=MODEL_KEY)
    token = released(app)["speech_token"]
    raw = b"ID3" + b"x" * (server.MAX_AUDIO - 3)
    app.speech_transport = lambda *args: ("audio/mpeg", raw)
    real_check = app._contains_key
    def bounded(value, candidates=()):
        assert not isinstance(value, str) or len(value) <= server.MAX_REPLY
        return real_check(value, candidates)
    monkeypatch.setattr(app, "_contains_key", bounded)
    started = time.monotonic()
    assert app.voice({"speech_token": token}) == raw
    assert time.monotonic() - started < 0.5


def test_vendor_exception_and_timeout_are_fixed_and_never_logged(app, all_pass, monkeypatch, caplog):
    enable(app)
    def failed(*args):
        raise RuntimeError(VOICE_KEY)
    app.speech_transport = failed
    with pytest.raises(server.InputError) as error:
        app.voice({"speech_token": released(app)["speech_token"]})
    assert str(error.value) == server.VOICE_ERROR
    release = threading.Event()
    app.speech_transport = lambda *args: (release.wait(2), AUDIO)
    monkeypatch.setattr(server, "VOICE_TIMEOUT", 0.03)
    try:
        start = time.monotonic()
        with pytest.raises(server.InputError):
            app.voice({"speech_token": released(app)["speech_token"]})
        assert time.monotonic() - start < 1
    finally:
        release.set()
    assert VOICE_KEY not in caplog.text


@pytest.mark.parametrize("change", ["card", "settings", "reset", "turn", "rotate"])
def test_pending_voice_cannot_delay_or_outlive_crisis_or_state_change(app, all_pass, change):
    enable(app)
    token = released(app)["speech_token"]
    entered, release = threading.Event(), threading.Event()
    results = []
    def hanging(*args):
        entered.set()
        release.wait(3)
        return "audio/mpeg", AUDIO + (VOICE_KEY.encode() if change == "rotate" else b"")
    app.speech_transport = hanging
    def listen():
        try:
            results.append(app.voice({"speech_token": token}))
        except server.InputError:
            results.append("refused")
    worker = threading.Thread(target=listen)
    worker.start()
    try:
        assert entered.wait(1)
        start = time.monotonic()
        if change == "card":
            body = app.turn(crisis_fixture())
            assert body["kind"] == "card" and body["adapter_calls"] == 0
        elif change == "settings":
            app.update_settings({"voice_enabled": False})
        elif change == "reset":
            app.reset()
        elif change == "rotate":
            app.update_settings({"voice_key": "sk-ROTATED-VOICE-TEST"})
        else:
            app.turn(PROMPT)
        assert time.monotonic() - start < 0.5
        release.set()
        worker.join(1)
        assert results == ["refused"]
    finally:
        release.set()
        worker.join(3)


def test_fixed_vendor_request_uses_no_proxy_no_redirect_and_bounded_read(app, all_pass, monkeypatch):
    enable(app)
    captured, handlers, limits = [], [], []
    class Reply:
        status = 200
        headers = Message()
        headers["Content-Type"] = "audio/mpeg"
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, limit):
            limits.append(limit)
            return AUDIO
    class Opener:
        def open(self, req, **kwargs):
            captured.append((req, kwargs))
            return Reply()
    def opener(*supplied):
        handlers.extend(supplied)
        return Opener()
    monkeypatch.setattr(server.urllib.request, "build_opener", opener)
    app.speech_transport = app._voice_transport
    result = released(app)
    assert app.voice({"speech_token": result["speech_token"]}) == AUDIO
    req, options = captured[0]
    assert req.full_url == ("https://api.elevenlabs.io/v1/text-to-speech/fixture_"
                            + result["persona"] + "_as_written?output_format=mp3_44100_128")
    assert req.get_header("Xi-api-key") == VOICE_KEY
    assert json.loads(req.data) == {"text": TEXT, "model_id": "eleven_multilingual_v2"}
    assert VOICE_KEY.encode() not in req.data
    assert options == {"timeout": server.VOICE_TIMEOUT} and limits == [server.MAX_AUDIO + 1]
    assert any(isinstance(item, server._NoRedirect) for item in handlers)
    assert any(isinstance(item, server.urllib.request.ProxyHandler) and item.proxies == {}
               for item in handlers)
    for status, mime in ((302, "audio/mpeg"), (200, "application/json")):
        Reply.status = status
        Reply.headers.replace_header("Content-Type", mime)
        with pytest.raises(server.InputError):
            app.voice({"speech_token": released(app)["speech_token"]})


def test_http_speech_endpoint_uses_existing_origin_pairing_and_audio_csp(app, all_pass, monkeypatch):
    enable(app)
    with live(app) as listener:
        result = request(listener, "/api/turn", {"text": PROMPT})[1]
        token = {"speech_token": result["speech_token"]}
        assert request(listener, "/api/voice", token, headers={"Origin": "https://other.invalid"})[0] == 403
        status, raw, headers = request(listener, "/api/voice", token)
        assert status == 200 and raw == AUDIO and headers["Content-Type"] == "audio/mpeg"
        assert headers["Cache-Control"] == "no-store"
        assert "media-src 'self' blob:" in headers["Content-Security-Policy"]
        assert request(listener, "/api/voice", token)[0] == 400
        state = request(listener, "/api/state")[1]
        assert state["voice_ready"] and state["voice_enabled"] and state["voice_revision"] > 0
        monkeypatch.setattr(server.Handler, "is_local", property(lambda self: False))
        assert request(listener, "/api/voice", token)[0] == 403
        assert request(listener, "/api/settings", {"voice_key": VOICE_KEY})[0] == 403


# ---------------------------------------------------------------------------
# 4 October 2026: the review fixes and the rulings of 3 October on Codex job 2.
# ---------------------------------------------------------------------------


def test_the_voice_bar_is_pinned_in_the_flow_and_never_floats_over_the_composer():
    """Night Builds Review, required fix 3: on a phone the fixed voice bar sat on
    the Send button. The bar now pins to the top with the mode banner, in the
    flow, so it reserves its own space; no rule floats it or anchors it to the
    bottom. The offline DOM has no layout engine, so this pins the stylesheet."""
    import re
    css = (server.STATIC / "table.css").read_text(encoding="utf-8")
    page = (server.STATIC / "index.html").read_text(encoding="utf-8")
    assert "position:fixed" not in css
    voice_rules = re.findall(r"([^{}]*voice-controls[^{}]*)\{([^}]*)\}", css)
    assert voice_rules, "the voice bar has a rule"
    for selector, declarations in voice_rules:
        assert "position:" not in declarations.replace("position:static", ""), selector
        assert not re.search(r"(^|;)(top|right|bottom|left):", declarations), selector
    pinned = re.search(r"\.table-pinned\{([^}]*)\}", css)
    assert pinned and "position:sticky" in pinned[1] and "top:0" in pinned[1]
    assert ".table-pinned .operator-circle-status{position:static}" in css
    wrapper = re.search(r'<div class="table-pinned">(.*?)</div>\s*<section class="pair-panel"',
                        page, re.S)
    assert wrapper, "the banner and the voice bar share the pinned wrapper above the panels"
    assert 'id="operator-circle-status"' in wrapper[1]
    assert wrapper[1].index('id="operator-circle-status"') < wrapper[1].index("data-voice-controls")
    assert page.index("data-voice-controls") < page.index("<main ")
    assert page.count("data-voice-controls") == 2  # the page bar and the one in Settings


# The arithmetic behind MAX_AUDIO (Night Builds Review, required fix 2): the
# longest reply the Table can release, read at a slow pace, encoded as the
# vendor sends it, must fit with room to spare.
EVERY_ATTACHABLE_HOUSE_LINE = 2_100   # measured 2,054 characters, every line at once
LONGEST_RELEASE = server.MAX_REPLY + EVERY_ATTACHABLE_HOUSE_LINE
SLOW_CHARACTERS_PER_SECOND = 11
BYTES_PER_SECOND = 16_000             # mp3_44100_128 is 128 kbps
FIVE_THOUSAND = 5_000


def long_reply(length):
    sentence = "Begin with the smallest task on the list, then rest before the next one. "
    text = (sentence * (length // len(sentence) + 1))[:length]
    return text[:-1] + "." if text.endswith(" ") else text


def test_the_audio_limit_fits_the_longest_reply_the_table_can_release_twice_over():
    from secondsignal.lexicon import dv_line, resource_line
    from secondsignal.safety import HOUSE_LINES_EN
    lines = sum(len(v) if isinstance(v, str) else sum(len(p) for p in v)
                for k, v in HOUSE_LINES_EN.items()
                if k not in ("escalation_card", "compound_opener", "failure"))
    lines += max(len(resource_line(loc)) for loc in ("US", "ES", "MX", "CL", "AR", None))
    lines += max(len(dv_line(loc)) for loc in ("US", "ES", "MX", "CL", "AR", None))
    assert lines <= EVERY_ATTACHABLE_HOUSE_LINE
    slowest_seconds = LONGEST_RELEASE / SLOW_CHARACTERS_PER_SECOND
    assert server.MAX_AUDIO >= 2 * slowest_seconds * BYTES_PER_SECOND
    assert server.VOICE_TIMEOUT >= 60
    page = (server.STATIC / "voice.js").read_text(encoding="utf-8")
    assert f"const MAX_AUDIO_BYTES = {server.MAX_AUDIO};" in page
    assert "AUDIO_WAIT_MS" in page and "90000" not in page


def test_a_five_thousand_character_reply_is_spoken_whole(app, all_pass, monkeypatch):
    # The Table's own reply bound is MAX_REPLY; it is widened here only so the
    # voice path is proven on a reply longer than any the Table will release.
    monkeypatch.setattr(server, "MAX_REPLY", 6_000)
    text = long_reply(FIVE_THOUSAND)
    assert len(text) == FIVE_THOUSAND
    audio = b"ID3" + bytes(int(FIVE_THOUSAND / SLOW_CHARACTERS_PER_SECOND * BYTES_PER_SECOND))
    assert len(audio) <= server.MAX_AUDIO
    enable(app)
    app.harness.adapter = FakeAdapter(script=(text,))
    app.speech_transport = lambda voice_id, spoken, key: (app.speech_calls.append(spoken),
                                                         ("audio/mpeg", audio))[1]
    with live(app) as listener:
        result = request(listener, "/api/turn", {"text": PROMPT})[1]
        assert result["kind"] == "reply" and result["text"] == text and result["speech_token"]
        status, raw, headers = request(listener, "/api/voice", {"speech_token": result["speech_token"]},
                                       timeout=30)
    assert status == 200 and headers["Content-Type"] == "audio/mpeg"
    assert raw == audio and len(raw) == len(audio)
    assert app.speech_calls == [text], "one request, the whole reply, no chunk and no cut"


def test_an_unpaired_device_sees_no_voice_state_and_no_counter(app, all_pass, monkeypatch):
    """The operator's answer of 4 October 2026 to Codex's recommended fix (a):
    before pairing a phone learns the mode and nothing that moves with a turn."""
    enable(app)
    app.set_network(True)
    phone = app.phone_server
    monkeypatch.setattr(server.Handler, "is_local", property(lambda self: False))
    try:
        before = [request(phone, path)[1] for path in ("/api/state", "/api/config")]
        before.append(request(phone, "/api/turn", {"text": PROMPT})[1])
        for body in before:
            assert set(body) == {"error", "pairing_required", "operator_circle", "mode_revision"}
            assert not any("voice" in key for key in body)
        released(app)
        released(app)
        assert app.state["voice_revision"] > app.config()["state"]["mode_revision"] - 10**15
        after = [request(phone, path)[1] for path in ("/api/state", "/api/config")]
        after.append(request(phone, "/api/turn", {"text": PROMPT})[1])
        assert after == before, "two turns moved nothing an unpaired device can see"
        assert "voice" not in json.dumps(after)
    finally:
        monkeypatch.undo()
        app.set_network(False)


def test_after_a_card_the_whole_reply_is_spoken_once_in_the_seated_voice(app, all_pass):
    """Ruling 24 of 3 October 2026, with ruling 16's "said once" and ruling 6's silent card."""
    from secondsignal.safety import HOUSE_LINES_EN
    enable(app)
    card = app.turn(crisis_fixture())
    assert card["kind"] == "card" and card["speech_token"] is None
    assert app.speech_calls == []
    app.harness.adapter = FakeAdapter(script=(TEXT,))
    after = app.turn(PROMPT)
    assert after["kind"] == "reply" and after["release_reason"] == "ship"
    lines = after["house_lines"]
    assert lines[0] == HOUSE_LINES_EN["post_escalation"]
    assert lines[1].startswith("If you are in immediate danger") and "findahelpline.com" in lines[1]
    assert len(lines) == 2 and after["text"] == TEXT
    assert app.voice({"speech_token": after["speech_token"]}) == AUDIO
    voice_id, spoken, _ = app.speech_calls[-1]
    assert voice_id == "fixture_" + after["persona"] + "_as_written"
    assert spoken == TEXT + "\n\n" + lines[0] + "\n" + lines[1]
    assert spoken == after["text"] + "\n\n" + "\n".join(after["house_lines"])
    # The next aftermath turn keeps the quiet reminder on screen and speaks the
    # character's text alone: the resource line is never read aloud a second time.
    app.harness.adapter = FakeAdapter(script=(TEXT,))
    later = app.turn("And what about the afternoon?")
    assert later["kind"] == "reply" and later["house_lines"] == [lines[1]]
    assert app.voice({"speech_token": later["speech_token"]}) == AUDIO
    assert app.speech_calls[-1][1] == TEXT
    assert len(app.speech_calls) == 2


def test_the_turn_after_a_card_speaks_whole_in_operator_circle_mode_only_if_released(app):
    """With the cultural layer unlocked the audit calls the turn after a card high
    risk and withholds it, in operator-circle mode too, so nothing is spoken; the
    whole-reply rule applies to whatever the audit releases on that turn."""
    enable(app, operator_circle=True)
    assert app.turn(crisis_fixture())["kind"] == "card"
    app.harness.adapter = FakeAdapter(script=(TEXT,))
    after = app.turn(PROMPT)
    assert after["kind"] == "withheld" and after["verdict"]["risk_class"] == "high"
    assert after["speech_token"] is None and app.speech_calls == []


def test_presentation_and_name_choice_hold_for_the_visit_across_reload_and_a_paired_phone(
        tmp_path, monkeypatch):
    """A visit is the server session (the operator's answer of 4 October 2026):
    the choice holds until New session or a restart; a reload or a paired phone
    joining does not reset it; Remember never saves it."""
    monkeypatch.setattr(server, "_secret_blob", lambda value, **kwargs: value)
    app = server.TableApp(data_dir=tmp_path / "table")
    second = None
    try:
        with live(app) as local:
            chosen = {"ellis": "Elli", "willow": "Will"}
            status, config, _ = request(local, "/api/settings",
                                        {"presentation": "neither", "chosen_names": chosen})
            assert status == 200 and config["settings"]["presentation"] == "neither"
            for _ in range(2):  # a reload asks for the configuration again
                reloaded = request(local, "/api/config")[1]["settings"]
                assert reloaded["presentation"] == "neither" and reloaded["chosen_names"] == chosen
            turn = request(local, "/api/turn", {"text": PROMPT})[1]
            assert turn["presentation"] == "neither"
            request(local, "/api/network", {"enabled": True})
            code = request(local, "/api/config")[1]["phone"]["code"]
            phone = app.phone_server
            monkeypatch.setattr(server.Handler, "is_local", property(lambda self: False))
            cookie = request(phone, "/api/pair", {"code": code})[2]["Set-Cookie"].split(";", 1)[0]
            joined = request(phone, "/api/config", headers={"Cookie": cookie})[1]["settings"]
            assert joined["presentation"] == "neither" and joined["chosen_names"] == chosen
            monkeypatch.setattr(server.Handler, "is_local", property(lambda self: True))
            # Remember, for the voice or the model, never writes the choice.
            request(local, "/api/settings", {"voice_remember": True, "voice_key": VOICE_KEY})
            stored = json.loads(app.settings_path.read_text(encoding="utf-8"))["settings"]
            assert "presentation" not in stored and "chosen_names" not in stored
            assert request(local, "/api/config")[1]["settings"]["presentation"] == "neither"
            request(local, "/api/settings", {"remember": True})
            stored = json.loads(app.settings_path.read_text(encoding="utf-8"))["settings"]
            assert "presentation" not in stored and "chosen_names" not in stored
            reset = request(local, "/api/session/reset", {})[1]["settings"]
            assert reset["presentation"] == "as_written" and reset["chosen_names"] == {}
            request(local, "/api/settings", {"presentation": "women"})
            request(local, "/api/network", {"enabled": False})
        second = server.TableApp(data_dir=tmp_path / "table")  # a restart
        assert second.settings["presentation"] == "as_written"
        assert second.settings["chosen_names"] == {}
        assert second.settings["voice_remember"] is True and second.voice_key == VOICE_KEY
    finally:
        app.close()
        if second is not None:
            second.close()


def test_the_javascript_voice_suites_pass_offline():
    import shutil
    import subprocess
    node = shutil.which("node")
    assert node, "Node is required for the offline browser contract tests (no skipped tests)"
    files = sorted((server.STATIC.parent / "tests_js").glob("*.mjs"))
    assert len(files) == 2
    result = subprocess.run([node, "--test", *map(str, files)], capture_output=True,
                            text=True, timeout=120)
    summary = {line.split()[1]: line.split()[2] for line in result.stdout.splitlines()
               if line.startswith("# ") and len(line.split()) == 3
               and line.split()[1] in ("tests", "pass", "fail", "skipped", "todo")}
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    assert summary["fail"] == "0" and summary["skipped"] == "0" and summary["todo"] == "0"
    assert int(summary["tests"]) >= 28 and summary["pass"] == summary["tests"]
