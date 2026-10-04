"""Standard-library HTTP surface around the unmodified voice harness."""

from __future__ import annotations

import base64
import copy
import ctypes
import hashlib
import importlib
import ipaddress
import json
import logging
import mimetypes
import os
import queue
import re
import secrets
import socket
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from secondsignal.profiles import load_roster
from secondsignal.safety import HOUSE_LINES_EN
from secondsignal_harness import AuditLog, CodexStore, Harness
from secondsignal_harness.__main__ import _adapter
from secondsignal_harness.adapters import AdapterError, AdapterReply
from secondsignal_harness.harness import RELEASE_OPERATOR_CIRCLE, RELEASE_SHIP

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
LOG = logging.getLogger("talking_table")
PROTOTYPE = "A prototype for the operator and adults the operator knows. Not a crisis service."
FAMILIES = {"fake", "gemini", "openai", "anthropic", "xai", "compatible"}
PRESENTATIONS = {"as_written", "women", "men", "neither"}
COOKIE = "ss_table_pair"
MAX_BODY = 65536
MAX_REPLY = 3500
MODEL_TIMEOUT = 15.0
# No reply is lost to a limit (Night Builds Review of 30 September 2026, required
# fix 2 on Codex job 2). The longest reply the Table can release is MAX_REPLY
# characters of character text plus every attached house line, under 5,600
# characters in all; read slowly (eleven characters a second), about eight and
# a half minutes, which at the vendor's 128 kbps is about 8.2 megabytes. The
# audio limit holds more than twice that, and the vendor gets a full minute to
# return it. The browser bounds only the wait for the audio, never the playback
# (static/voice.js). tests/test_table_voice.py pins the arithmetic.
VOICE_TIMEOUT = 60.0
MAX_AUDIO = 20_000_000
VOICE_ERROR = "This voice is unavailable. The reply is still on the table."
FAILURE_MESSAGE = "This message ran into a problem. Send your message again to try again."
# Adapters still use their own request construction. The real key exists only
# in the transport closure; this public placeholder is never sent to a vendor.
KEY_SLOT = "SECONDSIGNAL_TABLE_TRANSPORT_PLACEHOLDER"
os.environ[KEY_SLOT] = "table-transport-placeholder"


class InputError(ValueError):
    """A safe, fixed user-facing validation message."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _secret_blob(value: bytes, *, decrypt: bool = False) -> bytes:
    """Windows user-bound encryption, with no optional runtime package."""
    if os.name != "nt":
        raise InputError("Remembering a key is available on this computer only with Windows.")
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    destination = Blob()
    library = ctypes.windll.crypt32
    function = library.CryptUnprotectData if decrypt else library.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                         ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1,
                    ctypes.byref(destination)):
        raise InputError("The computer could not protect or unlock the saved key.")
    try:
        return ctypes.string_at(destination.data, destination.size)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree.restype = ctypes.c_void_p
        ctypes.windll.kernel32.LocalFree(destination.data)


class SceneWorker:
    """One daemon worker; a stuck optional light driver cannot block a turn."""

    def __init__(self):
        self.pending: queue.Queue = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True, name="table-lights")
        self.thread.start()

    def submit(self, persona, state):
        self.pending.put_nowait((persona, state))

    def _run(self):
        while True:
            item = self.pending.get()
            if item is None:
                return
            try:
                module = importlib.import_module("apps.talking_table.lights")
                module.set_scene(*item)
            except ModuleNotFoundError as exc:
                if exc.name != "apps.talking_table.lights":
                    LOG.warning("Optional lights unavailable; turn unchanged.")
            except Exception:
                # Driver messages can contain arbitrary input; do not print them.
                LOG.warning("Optional lights failed; turn unchanged.")

    def close(self):
        self.submit(None, "idle")
        self.pending.put_nowait(None)


def _card_decision(record):
    """A nameless display/audit projection, never a replacement policy decision."""
    safety = record.get("safety", {})
    fields = ("action", "disclosures", "crisis_read", "crisis_classes",
              "lexicon_status", "card", "card_order", "patterns_hash", "pack_ids",
              "latch", "register_caps")
    return {
        "outcome": record.get("outcome"), "agent_id": None,
        "assist_agent_id": None, "shadow_agent_id": None,
        "safety": {key: copy.deepcopy(safety[key]) for key in fields if key in safety},
        "explain": "safety = HUMAN_ESCALATION\nThe crisis card holds the floor.",
        "presentation_note": "Character-routing details are omitted from this card record.",
    }


class _Cancelled(Exception):
    pass


def _reply_surface(text):
    """Normalize a detection copy, never rewrite an accepted model's words.

    Compatibility letters, accents, typographic punctuation and invisible
    formatting must not hide a reserved role. Keeping newlines here also lets
    speaker labels be checked independently of surrounding prose.
    """
    text = unicodedata.normalize("NFKD", text).casefold()
    return "".join(char for char in text
                   if unicodedata.category(char) not in {"Cf", "Mn", "Me"})


def _reply_words(text):
    return re.sub(r"[\W_]+", " ", _reply_surface(text)).strip()


# These are app-output boundaries, independent of the policy release mode.
# Check families of role claims and handoffs, including quoted/Markdown forms;
# never try to salvage a reply by deleting only its offending sentence.
_HOUSE_CLAIMS = tuple(re.compile(pattern) for pattern in (
    r"\b(?:i am|i m|we are|we re|my name is|speak(?:ing|s)? (?:as|for)|"
    r"acting (?:as|for)|answering (?:as|for)|responding (?:as|for)|"
    r"on behalf of|voice of|i represent|we represent|i serve as|we serve as) "
    r"(?:the |your )?house\b",
    r"\b(?:i|we) (?:the |your )?house\b",
    r"\bas (?:the |your )?house (?:i|we|let|this|you)\b",
    r"\b(?:this|it|here) is (?:the |your )?house "
    r"(?:speaking|calling|addressing|answering|taking|here|now)\b",
    r"\b(?:this|it) (?:comes|came|originates|is issued|is sent) "
    r"from (?:the |your )?house\b",
    r"\b(?:message|reply|response|notice|instruction|announcement|decision|word)s? "
    r"(?:\w+ ){0,5}(?:from|by) (?:the |your )?house\b",
    r"\bhouse (?:(?:is|are|has|have|will|would|can|must|now|hereby|officially|"
    r"already|just|been|be) ){0,5}"
    r"(?:speaks?|speaking|says?|said|decides?|decided|asks?|requires?|orders?|"
    r"announces?|announced|takes?|taking|controls?|overrides?|approves?|"
    r"permits?|allows?|instructs?|directs?|authorizes?|authorises?|insists?|"
    r"intervenes?|intervening|requests?|advises?|warns?|notifies?)\b",
    r"\bhouse (?:voice|announcement|notice|message|reply|response|statement|"
    r"directive|instruction|disclosure|decision|authority|ruling)\b",
    r"\bhouse (?:(?:is|has|now|currently) ){0,3}"
    r"(?:in control|in charge|holds the floor|the floor|here to (?:help|answer))\b",
    r"\bhouse would like you to (?:know|hear|understand)\b",
    r"\b(?:per|under|by) (?:the )?house (?:policy|rules|authority)\b",
))
_CARD_LABEL = re.compile(
    r"\b(?:(?:crisis|safety|emergency|escalation|human escalation) "
    r"(?:card|notice|handoff)|human escalation)\b")
_ROLE_WITHDRAWAL = re.compile(
    r"\b(?:characters?|personas?|voices?|cast) "
    r"(?:(?:are|is|have|has|had|will|must|should|can|all|now|being|been|be|"
    r"temporarily|currently|here|no|longer|not) ){0,7}"
    r"(?:stepp?(?:ing|ed)? (?:aside|back|away|out)|stand(?:ing)? (?:aside|back)|"
    r"stood (?:aside|back)|left|leav(?:e|ing)|withdraw(?:n|ing)?|"
    r"depart(?:ed|ing)?|exit(?:ed|ing)?|paus(?:e|ed|ing)|suspend(?:ed|ing)?|"
    r"silenced|silent|muted|dismissed|removed|replaced|off duty|offstage|gone|"
    r"tak(?:e|ing) (?:a )?break|hand(?:ed|ing)? (?:over|off)|"
    r"not speaking|no longer speaking|"
    r"(?:cannot|can t|will not|won t|must not|should not) "
    r"(?:respond|answer|continue|help|speak))\b")
_ROLE_REMOVAL = re.compile(
    r"\b(?:paus(?:e|ing)|silenc(?:e|ing)|mut(?:e|ing)|suspend(?:ing)?|"
    r"remov(?:e|ing)|dismiss(?:ing)?) (?:all |the |these |our )?"
    r"(?:characters?|personas?|voices?)\b")
_TABLE_HANDOFF = re.compile(
    r"\b(?:the |this |our )?table "
    r"(?:(?:is|has|will|now|being|been|be|temporarily) ){0,5}"
    r"(?:paus(?:e|ed|ing)|suspend(?:ed|ing)?|closed|hand(?:ed|ing) over)\b")
_HUMAN_SUPPORT = re.compile(
    r"\b(?:(?:real|actual|living|trusted) (?:person|human)|human being|"
    r"human (?:support|help)|emergency|crisis|hotline|helpline)\b")
_CHARACTER_REPLACEMENT = re.compile(
    r"\b(?:not|rather than|instead of|beyond) "
    r"(?:(?:a|an|the|any|this|these|our|fictional|simulated|ai) ){0,4}"
    r"(?:characters?|personas?|chatbots?|models?|ai)\b")
_SPEAKER_HANDOFF = re.compile(
    r"\b(?:i|we) (?:(?:am|are|m|re|will|must|should|now|have|to|need) ){0,5}"
    r"(?:stepp?(?:ing|ed)? (?:aside|back|away|out)|hand(?:ing)? "
    r"(?:this |you |the conversation )?(?:over|off)|"
    r"(?:cannot|can t|won t|will not) (?:continue|respond|answer))\b")


def _reserved_reply_voice(text):
    """Reject detected house/card role imitation before any harness storage.

    This conservatively reserves authority labels and role transitions while
    allowing ordinary house chores, fictional-character discussion and human
    support suggestions. It is a deterministic boundary, not a proof that all
    possible natural-language impersonations can be recognized.
    """
    surface, words = _reply_surface(text), _reply_words(text)
    if re.search(r"\[\s*(?:the\s+)?house\s*\]", surface):
        return True
    if re.search(r"^[\s#>*_`-]*(?:(?:from\s+)?(?:the\s+)?house)\s*[:|]",
                 surface, re.M):
        return True
    if re.search(r"\b(?:this|it)\s+is\s+(?:the\s+)?house\s*(?:[.!?;:]|$)",
                 surface):
        return True
    if any(pattern.search(words) for pattern in _HOUSE_CLAIMS):
        return True
    if (_CARD_LABEL.search(words) or _ROLE_WITHDRAWAL.search(words)
            or _ROLE_REMOVAL.search(words)):
        return True
    if _HUMAN_SUPPORT.search(words) and (
            _TABLE_HANDOFF.search(words) or _CHARACTER_REPLACEMENT.search(words)
            or _SPEAKER_HANDOFF.search(words)):
        return True
    for line in HOUSE_LINES_EN.values():
        for part in line if isinstance(line, tuple) else (line,):
            if isinstance(part, str) and len(part) > 30 and _reply_words(part) in words:
                return True
    return False


class _TurnJob:
    """The supplied Harness routes once; only its optional model work can wait."""

    def __init__(self, app, text):
        self.app, self.text = app, text
        self.ready = threading.Event()
        self.admitted = threading.Event()
        self.done = threading.Event()
        self.cancelled = threading.Event()
        self.gate = False
        self.result = None
        self.error = False
        self.revision = 0
        self.harness = copy.copy(app.harness)
        self.harness.session = copy.deepcopy(app.harness.session)
        self.harness.transcript = copy.deepcopy(app.harness.transcript)
        self.harness.turns = []
        self.harness.adapter = _GuardedAdapter(self, app.harness.adapter)
        self.harness.audit_log = _TableAudit(self, app.harness.audit_log)

    def boundary(self, *, gate=False):
        if not self.ready.is_set():
            self.gate = gate
            self.ready.set()
        self.admitted.wait()
        if self.cancelled.is_set():
            raise _Cancelled()

    def run(self):
        try:
            self.result = self.harness.speak(self.text)
        except _Cancelled:
            pass
        except Exception:
            # No vendor exception, traceback or arbitrary object reaches a log.
            self.error = True
        finally:
            self.ready.set()
            self.done.set()


class _GuardedAdapter:
    """Validate untrusted results before the unchanged harness can store them."""

    def __init__(self, job, adapter):
        self.job, self.adapter = job, adapter
        self.name = adapter.name if isinstance(getattr(adapter, "name", None), str) else "model"
        self.failed = False

    def complete(self, system, messages, *, max_tokens):
        job, app = self.job, self.job.app
        job.boundary()
        if self.failed or not app.model_slots.acquire(blocking=False):
            raise AdapterError("The model reply is unavailable.")
        completed = threading.Event()
        result = []

        def call():
            try:
                result.append(self.adapter.complete(system, messages, max_tokens=max_tokens))
            except BaseException:
                # Even a scripted exception may contain an unknown credential.
                pass
            finally:
                app.model_slots.release()
                completed.set()

        threading.Thread(target=call, daemon=True, name="table-model").start()
        deadline = time.monotonic() + MODEL_TIMEOUT
        while not completed.wait(0.01):
            if job.cancelled.is_set() or time.monotonic() >= deadline:
                self.failed = True
                raise AdapterError("The model reply is unavailable.")
        if job.cancelled.is_set():
            raise _Cancelled()
        reply = result[0] if result else None
        if not app._acceptable_reply(reply):
            self.failed = True
            raise AdapterError("The model reply could not be accepted.")
        return reply


class _TableAudit:
    """Sanitize at append, before a supplied AuditLog hashes or writes any row."""

    def __init__(self, job, sink):
        self.job, self.sink = job, sink

    def append(self, row):
        job, app = self.job, self.job.app
        gate = row.get("action") == "HUMAN_ESCALATION"
        job.boundary(gate=gate)
        safe = copy.deepcopy(row)
        if gate:
            safe["decision"] = _card_decision(safe["decision"])
            safe["agent_id"] = None
        if "error" in safe:
            safe["error"] = "The model reply is unavailable."
        if gate:
            # The card and policy/schema constants are authoritative. A key
            # equal to a schema word must not break or suppress a crisis card.
            safe["user_text"] = app._redact(safe.get("user_text", ""))
            safe["adapter"] = "not_called"
        else:
            safe = app._redact(safe)
        with app.audit_lock:
            if job.cancelled.is_set():
                raise _Cancelled()
            return self.sink.append(safe)


class TableApp:
    def __init__(self, data_dir: Path | None = None,
                 harness_factory: Callable[[], Harness] | None = None,
                 speech_transport: Callable | None = None):
        self.data_dir = (data_dir or Path.home() / ".secondsignal" / "talking-table").resolve()
        if self.data_dir == ROOT or ROOT in self.data_dir.parents:
            raise InputError("The storage folder must be outside the repository.")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.data_dir / "settings.json"
        self.audit_path = self.data_dir / "audit.jsonl"
        self.lock = threading.RLock()
        self.audit_lock = threading.Lock()
        self.model_slots = threading.BoundedSemaphore(4)
        self.speech_slots = threading.BoundedSemaphore(2)
        self.speech_transport = speech_transport or self._voice_transport
        self.speech_tokens = {}
        self.voice_revision = time.time_ns() // 1_000_000
        self.jobs = set()
        self.session_id = secrets.token_hex(12)
        self.revision = 0
        # Separate from turn revisions, which reset with each conversation.
        # Milliseconds fit exactly in browser integers and order server restarts.
        self.mode_revision = time.time_ns() // 1_000_000
        self.settings = {"adapter": "fake", "model": "fake-1", "url": "",
                         "remember": False, "operator_circle": False,
                         "presentation": "as_written", "chosen_names": {},
                         "voice_enabled": False, "voice_remember": False,
                         "voice_slots": {}}
        self.key = ""
        self.voice_key = ""
        self.key_fingerprints: set[tuple[int, bytes]] = set()
        self.roster = load_roster()
        self.settings["voice_slots"] = {
            persona: {presentation: "" for presentation in sorted(PRESENTATIONS)}
            for persona in self.roster}
        self.factory = harness_factory
        self.phone_server = None
        self.phone_thread = None
        self.pairing_code = None
        self.paired: set[str] = set()
        self.pair_attempts: dict[str, list[float]] = {}
        self.lights = SceneWorker()
        self._load_settings()
        self.harness = self._build_harness()
        self.state = self._idle_state()

    def _idle_state(self):
        return {"seated": None, "assist": None, "state": "idle",
                "presentation": self.settings["presentation"], "turn_count": 0,
                "session_id": self.session_id, "revision": self.revision,
                **self._mode_state()}

    def _shell_state(self):
        """The mode, which an unpaired device may see: it is shell status, and
        its revision moves only with Settings and New session, never per turn."""
        return {"operator_circle": bool(self.harness.operator_circle),
                "mode_revision": self.mode_revision}

    def _mode_state(self):
        """Report the active harness, including a supplied test/factory harness.
        The voice fields move with every turn, so they stay behind pairing
        (the operator's answer of 4 October 2026 to Codex's recommended fix)."""
        return {**self._shell_state(),
                "voice_enabled": self.settings["voice_enabled"],
                "voice_ready": self._voice_ready(), "voice_revision": self.voice_revision}

    def _voice_ready(self):
        # Operator-circle mode no longer silences the voice (ruling 6 of
        # 3 October 2026); the released kinds decide, in _finish_job.
        return bool(self.settings["voice_enabled"] and self.voice_key
                    and any(slots[self.settings["presentation"]]
                            for slots in self.settings["voice_slots"].values()))

    def _remember_key(self, key):
        if key:
            self.key_fingerprints.add((len(key), hashlib.sha256(key.encode("utf-8")).digest()))

    def _has_key(self, text):
        # Past credentials can be recognised without retaining their plaintext.
        if any(key and key in text for key in (self.key, self.voice_key)):
            return True
        for length, digest in tuple(self.key_fingerprints):
            for offset in range(max(0, len(text) - length + 1)):
                candidate = text[offset:offset + length]
                if hashlib.sha256(candidate.encode("utf-8")).digest() == digest:
                    return True
        return False

    def _contains_key(self, value, candidates=()):
        if isinstance(value, str):
            return self._has_key(value) or any(key and key in value for key in candidates)
        if isinstance(value, dict):
            return any(self._contains_key(k, candidates) or self._contains_key(v, candidates)
                       for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return any(self._contains_key(v, candidates) for v in value)
        return False

    def _redact(self, value):
        if isinstance(value, str):
            return "[credential removed]" if self._has_key(value) else value
        if isinstance(value, dict):
            # Schema keys are code, not free text. Untrusted model dictionary
            # keys have already been checked by _acceptable_reply.
            return {k: self._redact(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._redact(v) for v in value]
        return value

    def _acceptable_reply(self, reply):
        if (not isinstance(reply, AdapterReply) or not isinstance(reply.text, str)
                or not 0 < len(reply.text.strip()) <= MAX_REPLY
                or not isinstance(reply.model_id, str) or len(reply.model_id) > 200
                or not isinstance(reply.usage, dict) or len(reply.usage) > 32):
            return False
        if any(not isinstance(k, str) or len(k) > 64 or type(v) is not int
               or not 0 <= v <= 10**12 for k, v in reply.usage.items()):
            return False
        if self._contains_key([reply.text, reply.model_id, reply.usage]):
            return False
        text = _reply_surface(reply.text)
        if re.search(r"<\s*[!/?a-zA-Z]", text) or _reserved_reply_voice(reply.text):
            return False
        names = {p.id for p in self.roster.values()}
        names.update(name for p in self.roster.values() for name, _ in p.plate)
        identities = "|".join(re.escape(_reply_words(name)) for name in sorted(names))
        if re.search(r"\b(?:i am|i m|my name is|speaking as) (?:" + identities + r")\b",
                     _reply_words(text)):
            return False
        identities = "|".join(re.escape(_reply_surface(name)) for name in sorted(names))
        if re.search(r"^\s*(?:" + identities + r")\s*:", text, re.I | re.M):
            return False
        return True

    def _cancel_jobs(self):
        self.voice_revision += 1
        self.speech_tokens.clear()
        for job in self.jobs:
            job.cancelled.set()

    def _superseded(self):
        return {"kind": "withheld", "superseded": True, "persona": None,
                "assist": None, "text": "", "house_lines": [], "card": None,
                "verdict": None, "decision": {}, "speech_token": None,
                "state": dict(self.state)}

    def _load_settings(self):
        if not self.settings_path.exists():
            return
        try:
            saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
            saved_settings = saved.get("settings", {})
            if not isinstance(saved_settings, dict):
                raise InputError("Saved settings could not be accepted.")
            # Presentation is visit-only in the current push, including when
            # loading a settings file written by an older Talking Table.
            settings = self._validate_settings({k: v for k, v in saved_settings.items()
                                                if k not in ("presentation", "chosen_names")})
            # Each key has its own opt-in; a remembered voice must never save
            # or restore an unremembered model credential (or the reverse).
            keys = {}
            for name, flag, blob_name in (("key", "remember", "key_blob"),
                                          ("voice_key", "voice_remember", "voice_key_blob")):
                keys[name] = (_secret_blob(base64.b64decode(saved[blob_name], validate=True),
                                          decrypt=True).decode("utf-8")
                              if settings[flag] else "")
            if self._contains_key(settings, keys.values()):
                raise InputError("Saved settings could not be accepted.")
            self.settings.update(settings)
            self.key, self.voice_key = keys["key"], keys["voice_key"]
            for key in keys.values():
                self._remember_key(key)
        except Exception:
            LOG.warning("Saved settings could not be read; using the pretend model.")

    def _validate_settings(self, proposed):
        if not isinstance(proposed, dict):
            raise InputError("Settings must be an object.")
        result = copy.deepcopy(self.settings)
        for name in ("adapter", "model", "url", "presentation"):
            if name in proposed:
                value = proposed[name]
                if not isinstance(value, str) or len(value) > 2048:
                    raise InputError("A setting has an invalid value.")
                result[name] = value.strip()
        if result["adapter"] not in FAMILIES or result["presentation"] not in PRESENTATIONS:
            raise InputError("Choose a listed model family and presentation.")
        for name in ("remember", "operator_circle", "voice_enabled", "voice_remember"):
            if name in proposed:
                if not isinstance(proposed[name], bool):
                    raise InputError("A switch must be on or off.")
                result[name] = proposed[name]
        if result["adapter"] == "fake" and not result["model"]:
            result["model"] = "fake-1"
        if not result["model"] or len(result["model"]) > 200:
            raise InputError("Enter a model id.")
        if result["adapter"] == "compatible":
            parsed = urllib.parse.urlsplit(result["url"])
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                    or parsed.password or parsed.query or parsed.fragment):
                raise InputError("Use the vendor's HTTPS chat-completions address without credentials or a query.")
        chosen = proposed.get("chosen_names", result["chosen_names"])
        if not isinstance(chosen, dict) or any(
            key not in self.roster or value not in [pair[0] for pair in self.roster[key].plate]
            for key, value in chosen.items()
        ):
            raise InputError("Choose a name shown on the character's plate.")
        result["chosen_names"] = dict(chosen)
        if "voice_slots" in proposed:
            slots = proposed["voice_slots"]
            if not isinstance(slots, dict) or set(slots) - set(self.roster):
                raise InputError("Choose a listed character for each voice slot.")
            for persona, presentations in slots.items():
                if not isinstance(presentations, dict) or set(presentations) - PRESENTATIONS:
                    raise InputError("Choose a listed presentation for each voice slot.")
                for presentation, voice_id in presentations.items():
                    if not isinstance(voice_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{0,128}", voice_id):
                        raise InputError("A voice ID may contain only letters, digits, underscores or hyphens.")
                    result["voice_slots"][persona][presentation] = voice_id
        return result

    def _transport(self, key, allowed_url):
        def call(url, headers, body):
            if url != allowed_url or urllib.parse.urlsplit(url).scheme != "https":
                raise AdapterError("The model address was not approved.")
            if not key:
                raise AdapterError("No model key is set.")
            headers = dict(headers)
            if "x-api-key" in headers:
                headers["x-api-key"] = key
            else:
                headers["authorization"] = "Bearer " + key
            request = urllib.request.Request(url, data=body, headers=headers, method="POST")
            # Disable redirects and proxies: the key goes only to the chosen host.
            opener = urllib.request.build_opener(_NoRedirect(), urllib.request.ProxyHandler({}))
            try:
                with opener.open(request, timeout=60) as response:
                    raw = response.read(2_000_001)
                    status = response.status
            except Exception:
                raise AdapterError("The model request failed.") from None
            if len(raw) > 2_000_000 or key.encode("utf-8") in raw:
                raise AdapterError("The model response could not be accepted.")
            # A key echoed with JSON escapes is also refused before audit storage.
            try:
                decoded = json.loads(raw)
                if self._contains_key(decoded):
                    raise AdapterError("The model response could not be accepted.")
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise AdapterError("The model response could not be accepted.") from None
            return status, raw
        return call

    def _build_harness(self):
        if self.factory:
            return self.factory()
        setting = self.settings
        adapter = _adapter(setting["adapter"], setting["model"],
                           url=setting["url"] or None, key_variable=KEY_SLOT)
        if setting["adapter"] != "fake":
            adapter.key_variable = KEY_SLOT
            adapter._transport = self._transport(self.key, adapter.url)
        return Harness(self.roster, adapter, CodexStore(ROOT / "docs" / "codex"),
                       audit_log=AuditLog(self.audit_path),
                       presentation={name: setting["presentation"] for name in self.roster},
                       chosen_names=setting["chosen_names"],
                       operator_circle=setting["operator_circle"])

    def config(self, local=True):
        with self.lock:
            settings = copy.deepcopy(self.settings)
            settings["operator_circle"] = bool(self.harness.operator_circle)
            settings["key_set"] = bool(self.key)
            settings["voice_key_set"] = bool(self.voice_key)
            settings["voice_ready"] = self._voice_ready()
            return {
                "settings": settings,
                "roster": [{"id": p.id, "plate": p.plate, "one_line": p.one_line,
                            "names": {v: p.name_for(v, self.settings["chosen_names"].get(p.id))
                                      for v in sorted(PRESENTATIONS)}} for p in self.roster.values()],
                "storage": (
                    f"Audit logs keep messages, accepted model output (including audit-withheld replies), "
                    f"and decisions in {self.audit_path}. Unsafe model output is discarded; known keys "
                    f"are redacted, and card records omit character-routing details. "
                    f"Conversation state, character presentation, name choices and pairing stay in memory. "
                    f"Remembered settings and independently encrypted model and voice keys are kept in "
                    f"{self.settings_path} only for the corresponding remember switches. "
                    f"New session clears unremembered keys and keeps existing audit logs."
                ),
                "phone": {"enabled": self.phone_server is not None,
                          "code": self.pairing_code if local else None,
                          "urls": self.phone_server.urls if self.phone_server and local else []},
                "local": local,
                "sigils_available": (STATIC / "sigils.html").is_file(),
                "state": dict(self.state),
            }

    def update_settings(self, proposed):
        with self.lock:
            settings = self._validate_settings(proposed)
            candidate = proposed.get("key", "")
            if not isinstance(candidate, str) or len(candidate) > 4096:
                raise InputError("The key must be text.")
            voice_candidate = proposed.get("voice_key", "")
            if not isinstance(voice_candidate, str) or len(voice_candidate) > 4096:
                raise InputError("The voice key must be text.")
            changed_host = (settings["adapter"], settings["url"]) != (
                self.settings["adapter"], self.settings["url"])
            key = candidate.strip() or ("" if changed_host else self.key)
            if proposed.get("clear_key") is True:
                key = ""
            voice_key = voice_candidate.strip() or self.voice_key
            if proposed.get("clear_voice_key") is True:
                voice_key = ""
            if self._contains_key(settings, (key, voice_key, candidate.strip(), voice_candidate.strip())):
                raise InputError("Put the key only in the key field.")
            # Complete the durable write before adopting the new settings.
            if settings["remember"] or settings["voice_remember"]:
                # Presentation and name choices are visit-only: they are never
                # written, whichever remember switch is on.
                saved = {"settings": {k: copy.deepcopy(v) for k, v in settings.items()
                                      if k not in ("presentation", "chosen_names")}}
                for secret, flag, blob_name in ((key, "remember", "key_blob"),
                                                (voice_key, "voice_remember", "voice_key_blob")):
                    if settings[flag]:
                        try:
                            saved[blob_name] = base64.b64encode(
                                _secret_blob(secret.encode("utf-8"))).decode("ascii")
                        except Exception:
                            raise InputError("The computer could not protect or unlock the saved key.") from None
                if not settings["remember"]:
                    saved["settings"].update(adapter="fake", model="fake-1", url="",
                                             operator_circle=False)
                if not settings["voice_remember"]:
                    saved["settings"].update(voice_enabled=False, voice_slots={
                        persona: {presentation: "" for presentation in sorted(PRESENTATIONS)}
                        for persona in self.roster})
                payload = json.dumps(saved, ensure_ascii=False)
                temporary = self.settings_path.with_suffix(".tmp")
                temporary.write_text(payload, encoding="utf-8")
                temporary.replace(self.settings_path)
            else:
                self.settings_path.unlink(missing_ok=True)
            self.settings = settings
            self.key = key
            self.voice_key = voice_key
            self._remember_key(key)
            self._remember_key(voice_key)
            self._cancel_jobs()
            # Settings must never clear the policy latch or the conversation.
            previous = self.harness
            self.harness = self._build_harness()
            self.harness.session = previous.session
            self.harness.transcript = previous.transcript
            self.harness.turns = previous.turns
            self.mode_revision += 1
            self.state["presentation"] = settings["presentation"]
            self.state.update(self._mode_state())
            return self.config()

    def reset(self, harness: Harness | None = None):
        with self.lock:
            self._cancel_jobs()
            self.session_id = secrets.token_hex(12)
            self.revision = 0
            if not self.settings["remember"]:
                self.key = ""
            if not self.settings["voice_remember"]:
                self.voice_key = ""
            self.settings["presentation"] = "as_written"
            self.settings["chosen_names"] = {}
            self.harness = harness if harness is not None else self._build_harness()
            self.mode_revision += 1
            self.state = self._idle_state()
            self.lights.submit(None, "idle")
            return self.config()

    def turn(self, text):
        # Transport/type limits are needed to obtain text. Content checks happen
        # only AFTER the unchanged harness has run the policy gate on that text.
        if not isinstance(text, str):
            raise InputError("Write a message of 1 to 16000 characters.")
        with self.lock:
            job = _TurnJob(self, text)
            threading.Thread(target=job.run, daemon=True, name="table-turn").start()
            job.ready.wait()
            if job.error:
                raise InputError("This message could not be processed. Send it again to try again.")
            if not job.gate:
                invalid = not text.strip() or len(text) > 16000
                has_key = self._has_key(text)
                if invalid or has_key:
                    job.cancelled.set()
                    job.admitted.set()
                    raise InputError("Write a message of 1 to 16000 characters." if invalid else
                                     "Keep keys in the key field, outside the conversation.")
            self._cancel_jobs()
            self.revision += 1
            job.revision = self.revision
            self.jobs.add(job)
            # Commit only the routed session, before any optional model call.
            # Preserve identity for settings/session consumers. Completion must
            # never copy an old session back over a newer crisis latch.
            self.harness.session.__dict__.update(copy.deepcopy(job.harness.session.__dict__))
            self.harness.transcript.append({"role": "user", "content": self._redact(text)})
            self.state["turn_count"] = self.harness.session.turn_count
            self.state["revision"] = self.revision
            self.state.update(self._mode_state())
            if job.gate:
                # No model exists on this branch. Publish the card atomically
                # before another turn or settings change can supersede it.
                job.admitted.set()
                job.done.wait()
                return self._finish_job(job)
        job.admitted.set()
        job.done.wait()
        with self.lock:
            return self._finish_job(job)

    def _finish_job(self, job):
        """Called under the session lock; never waits for a model."""
        self.jobs.discard(job)
        if job.cancelled.is_set():
            return self._superseded()
        if job.error or job.result is None:
            raise InputError("This message could not be processed. Send it again to try again.")
        turn = job.result
        gate = turn.action == "HUMAN_ESCALATION"
        kind = "card" if gate else "reply" if turn.released else (
            "withheld" if turn.agent_id else "house")
        persona = None if gate else turn.agent_id
        assist = None if gate else turn.decision.get("assist_agent_id")
        state = "card" if gate else "seated" if persona else "idle"
        self.state = {"seated": persona, "assist": assist, "state": state,
                      "presentation": self.settings["presentation"],
                      "turn_count": self.harness.session.turn_count,
                      "session_id": self.session_id, "revision": job.revision,
                      **self._mode_state()}
        self.harness.transcript.extend(self._redact(job.harness.transcript[-1:]))
        # The turn before this one on the screen; a superseded turn never got there.
        previous = self.harness.turns[-1] if self.harness.turns else None
        self.harness.turns.append(turn)
        self.lights.submit(persona, state)
        verdict = turn.verdict
        layers = (verdict or {}).get("layers", {})
        cultural = (kind == "withheld" and (verdict or {}).get("risk_class") == "normal"
                    and layers.get("cultural") == "INCONCLUSIVE"
                    and all(layers.get(k) == "PASS" for k in ("logical", "semantic", "ethical")))
        result = {
            "kind": kind, "persona": persona, "assist": assist,
            "text": turn.persona_text if turn.released else (
                turn.text if gate else turn.text.replace(HOUSE_LINES_EN["failure"], FAILURE_MESSAGE)),
            "house_lines": list(turn.house_lines) if turn.released else [],
            "card": turn.text if gate else None,
            "verdict": verdict, "decision": _card_decision(turn.decision) if gate else turn.decision,
            "action": turn.action, "adapter_calls": turn.adapter_calls,
            "display_name": self.roster[persona].name_for(
                self.settings["presentation"], self.settings["chosen_names"].get(persona)
            )[0] if persona else None,
            "presentation": self.settings["presentation"],
            "cultural_only": cultural,
            "notice": None if gate else turn.notice,
            "state": dict(self.state), "release_reason": turn.release_reason,
            "speech_token": None,
        }
        # The capability names an already released, audited character reply.
        # The browser never supplies text or a character to the speech engine.
        text = self._speech_text(turn, previous) if kind == "reply" else None
        if text is not None and self._voice_ready() and persona in self.roster:
            voice_id = self.settings["voice_slots"][persona][self.settings["presentation"]]
            if voice_id and not self._contains_key(text):
                token = secrets.token_urlsafe(32)
                self.speech_tokens[token] = (self._speech_snapshot(), voice_id, text)
                result["speech_token"] = token
        return result if gate else self._redact(result)

    def _speech_text(self, turn, previous):
        """What the seated character's voice may say for a released turn, or None.

        Ruling 6 of 3 October 2026: a reply released by the audit (SHIP) speaks,
        and an operator-circle release speaks while the mode is on, each checked
        here against its own verdict and not only against the harness's label.
        The crisis card, withheld replies, failure lines and the house's own
        turns never reach this method with ``kind == "reply"``, so they are
        silent; a high-risk turn is withheld by the harness, so it is silent too.

        Ruling 24 of 3 October 2026: on the turn right after a crisis card the
        whole reply is spoken once, the character's text and then the attached
        house lines in the order the screen shows them (the acknowledgment and
        the resource line). Every other turn speaks the character's text alone,
        so a later aftermath turn never reads the resource reminder again
        (ruling 16).
        """
        if not turn.released or not isinstance(turn.persona_text, str) or not turn.persona_text:
            return None
        verdict = turn.verdict or {}
        layers = verdict.get("layers", {})
        core = ("logical", "semantic", "ethical")
        if turn.release_reason == RELEASE_SHIP:
            if not (verdict.get("status") == "SHIP" and verdict.get("composed") == "PASS"
                    and all(layers.get(name) == "PASS" for name in (*core, "cultural"))):
                return None
        elif turn.release_reason == RELEASE_OPERATOR_CIRCLE:
            if not (self.harness.operator_circle and verdict.get("status") == "WITHHOLD"
                    and verdict.get("risk_class") == "normal"
                    and layers.get("cultural") == "INCONCLUSIVE"
                    and all(layers.get(name) == "PASS" for name in core)):
                return None
        else:
            return None
        after_card = previous is not None and previous.action == "HUMAN_ESCALATION"
        if after_card and turn.house_lines:
            return turn.persona_text + "\n\n" + "\n".join(turn.house_lines)
        return turn.persona_text

    def _speech_snapshot(self):
        return self.session_id, self.revision, self.mode_revision, self.voice_revision

    def _voice_transport(self, voice_id, text, key):
        """One fixed HTTPS vendor, with no browser credential and no redirects."""
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", voice_id) or not key:
            raise InputError(VOICE_ERROR)
        request = urllib.request.Request(
            "https://api.elevenlabs.io/v1/text-to-speech/" + voice_id
            + "?output_format=mp3_44100_128",
            data=json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "audio/mpeg", "xi-api-key": key},
            method="POST")
        opener = urllib.request.build_opener(_NoRedirect(), urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=VOICE_TIMEOUT) as response:
                if response.status != 200:
                    raise InputError(VOICE_ERROR)
                content_type = response.headers.get_content_type()
                if content_type != "audio/mpeg":
                    raise InputError(VOICE_ERROR)
                raw = response.read(MAX_AUDIO + 1)
                return content_type, raw
        except Exception:
            raise InputError(VOICE_ERROR) from None

    def voice(self, payload):
        """Consume a single-use capability; never hold the session lock on I/O."""
        if (not isinstance(payload, dict) or set(payload) != {"speech_token"}
                or not isinstance(payload["speech_token"], str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{43}", payload["speech_token"])):
            raise InputError(VOICE_ERROR)
        with self.lock:
            issued = self.speech_tokens.pop(payload["speech_token"], None)
            if (not issued or issued[0] != self._speech_snapshot()
                    or not self._voice_ready() or self.state["state"] != "seated"):
                raise InputError(VOICE_ERROR)
            snapshot, voice_id, text = issued
            key = self.voice_key
            # Binary substring checks stay linear in the bounded audio size.
            # Credential rotation invalidates this snapshot before release.
            protected_audio = tuple(secret.encode("utf-8")
                                    for secret in (self.key, self.voice_key) if secret)
            if self._contains_key((voice_id, text)) or not self.speech_slots.acquire(blocking=False):
                raise InputError(VOICE_ERROR)
        complete, result = threading.Event(), []

        def call():
            try:
                result.append(self.speech_transport(voice_id, text, key))
            except BaseException:
                # Vendor errors may reflect secrets. Never retain or print them.
                pass
            finally:
                self.speech_slots.release()
                complete.set()

        threading.Thread(target=call, daemon=True, name="table-voice").start()
        deadline = time.monotonic() + VOICE_TIMEOUT
        while not complete.wait(0.01):
            with self.lock:
                if snapshot != self._speech_snapshot():
                    raise InputError(VOICE_ERROR)
            if time.monotonic() >= deadline:
                raise InputError(VOICE_ERROR)
        answer = result[0] if result else None
        if (not isinstance(answer, tuple) or len(answer) != 2 or answer[0] != "audio/mpeg"
                or not isinstance(answer[1], bytes) or not 0 < len(answer[1]) <= MAX_AUDIO):
            raise InputError(VOICE_ERROR)
        raw = answer[1]
        # MIME alone is not sufficient: reject text/HTML/JSON even when the
        # remote server labels it as audio. Accept MP3 ID3 or MPEG frame headers.
        if not (raw.startswith(b"ID3") or (len(raw) >= 2 and raw[0] == 0xff
                                          and raw[1] & 0xe0 == 0xe0)):
            raise InputError(VOICE_ERROR)
        if any(secret in raw for secret in protected_audio):
            raise InputError(VOICE_ERROR)
        with self.lock:
            if (snapshot != self._speech_snapshot() or not self._voice_ready()
                    or self.state["state"] != "seated"):
                raise InputError(VOICE_ERROR)
        return raw

    def set_network(self, enabled):
        with self.lock:
            if not isinstance(enabled, bool):
                raise InputError("The phone switch must be on or off.")
            if enabled and self.phone_server is None:
                server = make_server(self, host="0.0.0.0", port=0)
                self.phone_server = server
                self.pairing_code = f"{secrets.randbelow(1_000_000):06d}"
                self.phone_thread = threading.Thread(target=server.serve_forever, daemon=True)
                self.phone_thread.start()
            elif not enabled and self.phone_server:
                server = self.phone_server
                self.phone_server = None
                self.pairing_code = None
                self.paired.clear()
                self.pair_attempts.clear()
                # Shutdown may wait for a poll; keep that out of the request lock.
                threading.Thread(target=lambda: (server.shutdown(), server.server_close()),
                                 daemon=True).start()
            return self.config()

    def pair(self, code, address):
        with self.lock:
            if self.phone_server is None or not self.pairing_code:
                raise InputError("Phone access is off.")
            now = time.monotonic()
            attempts = [t for t in self.pair_attempts.get(address, []) if now - t < 60]
            if len(attempts) >= 5:
                raise InputError("Wait a minute before trying another pairing code.")
            attempts.append(now)
            self.pair_attempts[address] = attempts
            if not isinstance(code, str) or not secrets.compare_digest(code, self.pairing_code):
                raise InputError("That pairing code did not match.")
            token = secrets.token_urlsafe(32)
            self.paired.add(token)
            return token

    def close(self):
        with self.lock:
            self._cancel_jobs()
        self.set_network(False)
        self.lights.close()


def _local_addresses():
    addresses = {"127.0.0.1"}
    try:
        for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            value = result[4][0]
            if ipaddress.ip_address(value).is_private:
                addresses.add(value)
    except OSError:
        pass
    return sorted(addresses)


class TableServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, app):
        self.app = app
        super().__init__(address, Handler)
        port = self.server_address[1]
        addresses = _local_addresses() if address[0] == "0.0.0.0" else ["127.0.0.1"]
        self.authorities = {f"{host}:{port}" for host in [*addresses, "localhost"]}
        self.urls = [f"http://{host}:{port}" for host in addresses if host != "127.0.0.1"]
        if not self.urls:
            self.urls = [f"http://127.0.0.1:{port}"]

    def handle_error(self, request, client_address):
        LOG.warning("An HTTP request ended before completion.")


class Handler(BaseHTTPRequestHandler):
    server_version = "TalkingTable"
    sys_version = ""

    @property
    def is_local(self):
        try:
            return ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            return False

    def setup(self):
        super().setup()
        self.connection.settimeout(75)

    def log_message(self, format, *args):
        # Never log URLs, request bodies, query strings, headers, or exceptions.
        return

    def send_error(self, code, message=None, explain=None):
        self._send(code, {"error": "HTTP request rejected."})

    def _send(self, status, payload, content_type="application/json; charset=utf-8", cookie=None):
        # On Windows, closing with an unread POST body can reset the socket
        # before a refusal reaches the client. Discard only bounded bodies.
        if status >= 400 and self.command == "POST" and not getattr(self, "_body_read", False):
            try:
                lengths = self.headers.get_all("Content-Length", [])
                size = int(lengths[0]) if len(lengths) == 1 else 0
                if 0 < size <= MAX_BODY:
                    self.connection.settimeout(1)
                    self.rfile.read(size)
            except (ValueError, OSError):
                pass
            finally:
                self.connection.settimeout(75)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if isinstance(payload, dict) else payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; "
                         "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie", f"{COOKIE}={cookie}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(body)

    def _origin_ok(self):
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1 or hosts[0] not in self.server.authorities:
            return False
        origins = self.headers.get_all("Origin", [])
        if len(origins) > 1 or (origins and origins[0] != "http://" + hosts[0]):
            return False
        return self.headers.get("Sec-Fetch-Site", "same-origin") not in ("cross-site", "same-site")

    def _paired(self):
        if self.is_local:
            return True
        if self.server is not self.server.app.phone_server:
            return False
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            value = cookie[COOKIE].value if COOKIE in cookie else ""
            return value in self.server.app.paired
        except Exception:
            return False

    def _authorize(self, path):
        if not self._origin_ok():
            self._send(403, {"error": "Requests from other websites are refused."})
            return False
        if path.startswith("/api/") and path != "/api/pair" and not self._paired():
            # Mode is shell status, safe to show before pairing; conversation,
            # roster, storage, credentials and every per-turn voice field
            # remain behind authorization.
            with self.server.app.lock:
                mode = self.server.app._shell_state()
            self._send(403, {"error": "Enter the pairing code shown on the computer.",
                             "pairing_required": True, **mode})
            return False
        return True

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if not self._authorize(path):
            return
        app = self.server.app
        if path == "/api/config":
            self._send(200, app.config(self.is_local))
        elif path == "/api/state":
            with app.lock:
                self._send(200, dict(app.state))
        elif path == "/" or path.startswith("/static/"):
            relative = "index.html" if path == "/" else urllib.parse.unquote(path[8:])
            target = (STATIC / relative).resolve()
            if STATIC.resolve() not in target.parents or target.suffix not in {".html", ".js", ".css", ".json", ".svg"}:
                self._send(404, {"error": "File not found."})
            elif relative == "voice.js" and not target.exists():
                self._send(200, b"/* Optional voice module is not installed. */\n", "text/javascript; charset=utf-8")
            elif target.is_file():
                content_type = {".js": "text/javascript", ".css": "text/css", ".html": "text/html"}.get(
                    target.suffix, mimetypes.guess_type(str(target))[0] or "application/octet-stream")
                content = target.read_bytes()
                if relative == "index.html":
                    # The first paint, even before JavaScript or pairing, states
                    # the active mode. Subsequent changes use versioned polling.
                    with app.lock:
                        enabled = app._mode_state()["operator_circle"]
                    content = content.replace(b'data-mode="unknown"',
                                              b'data-mode="on"' if enabled else b'data-mode="off"')
                    content = content.replace("Checking operator-circle mode…".encode("utf-8"),
                                              b"Operator-circle mode is ON." if enabled else
                                              b"Operator-circle mode is OFF.")
                self._send(200, content, content_type + "; charset=utf-8")
            else:
                self._send(404, {"error": "File not found."})
        elif path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        else:
            self._send(404, {"error": "File not found."})

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if not self._authorize(path):
            return
        app = self.server.app
        if path in ("/api/settings", "/api/network") and not self.is_local:
            self._send(403, {"error": "Change these settings on the computer."})
            return
        try:
            if self.headers.get_content_type() != "application/json" or self.headers.get("Transfer-Encoding"):
                raise InputError("Send a JSON object.")
            sizes = self.headers.get_all("Content-Length", [])
            if len(sizes) != 1:
                raise InputError("A request length is required.")
            size = int(sizes[0])
            if not 0 < size <= MAX_BODY:
                raise InputError("The message is too large or empty.")
            raw = self.rfile.read(size)
            self._body_read = True
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise InputError("Send a JSON object.")
            if path == "/api/turn":
                self._send(200, app.turn(payload.get("text")))
            elif path == "/api/voice":
                self._send(200, app.voice(payload), "audio/mpeg")
            elif path == "/api/settings":
                self._send(200, app.update_settings(payload))
            elif path == "/api/session/reset":
                app.reset()
                self._send(200, app.config(self.is_local))
            elif path == "/api/network":
                self._send(200, app.set_network(payload.get("enabled")))
            elif path == "/api/pair":
                token = app.pair(payload.get("code"), self.client_address[0])
                self._send(200, {"ok": True}, cookie=token)
            else:
                self._send(404, {"error": "Endpoint not found."})
        except InputError as exc:
            self._send(400, {"error": str(exc)})
        except (ValueError, UnicodeDecodeError):
            self._send(400, {"error": "Send valid JSON and settings."})
        except Exception:
            LOG.warning("A table request failed; details were not logged.")
            self._send(500, {"error": "This request ran into a problem. Please try again."})

    def do_OPTIONS(self):
        self._send(403, {"error": "Cross-site access is not enabled."})


def make_server(app: TableApp, host="127.0.0.1", port=0):
    if host not in {"127.0.0.1", "0.0.0.0"}:
        raise InputError("Choose a local listener.")
    return TableServer((host, port), app)
