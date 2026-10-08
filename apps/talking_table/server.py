"""Standard-library HTTP surface around the unmodified voice harness."""

from __future__ import annotations

import base64
import copy
import ctypes
import hashlib
import html
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

from secondsignal.lexicon import RESOURCES
from secondsignal.normalize import SKELETON
from secondsignal.profiles import load_roster
from secondsignal.safety import HOUSE_LINES_EN, crisis_screen
from secondsignal_harness import AuditLog, CodexStore, Harness
from secondsignal_harness.__main__ import _adapter
from secondsignal_harness.adapters import AdapterError, AdapterReply
from secondsignal_harness.harness import RELEASE_OPERATOR_CIRCLE, RELEASE_SHIP
from secondsignal_harness.lines import HARNESS_LINES_EN, ROOM_LINES
from secondsignal_harness.prompt import LANGUAGE_STYLES, STYLE_VALUES, applied_preferences
from secondsignal_harness.table_extras import asked_agent, eligible_agents

from .t3 import COMPUTER_PATHS, TOKEN_NOTE, TableFeatures
from .table_kit import decision_receipt, presentation_samples, resources

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / "static"
LOG = logging.getLogger("talking_table")
PROTOTYPE = "A prototype for the operator and adults the operator knows. Not a crisis service."
FAMILIES = {"fake", "gemini", "openai", "anthropic", "xai", "compatible"}
PRESENTATIONS = {"as_written", "women", "men", "neither"}
DRAFT_TAGS = {"", "plan", "letter", "verse", "list", "unsent"}
REMEMBERED_EXTRAS = ("house_name", "room", "presentation_overrides")
# The countries a resource row exists for; "" means none declared (the
# directory line). Read from the verified resource rows, never inferred.
LOCALES = frozenset(key for key in RESOURCES["rows"] if key != "default")
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

    def __init__(self, current_key: Callable[[], str | None] | None = None):
        self.current_key = current_key or (lambda: None)
        self.pending: queue.Queue = queue.Queue()
        self.check_lock = threading.Lock()
        self.check_cancel = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True, name="table-lights")
        self.thread.start()

    def submit(self, persona, state):
        self.cancel_check()
        self.pending.put_nowait((persona, state))

    def cancel_check(self):
        with self.check_lock:
            self.check_cancel.set()

    def check(self, personas, interval=2.0):
        with self.check_lock:
            self.check_cancel.set()
            cancelled = self.check_cancel = threading.Event()

        def show():
            for persona, state in [*((p, "seated") for p in personas), (None, "card")]:
                if cancelled.is_set():
                    return
                done = threading.Event()
                self.pending.put_nowait((persona, state, cancelled, done))
                while not done.wait(0.05):
                    if cancelled.is_set():
                        return
                if cancelled.wait(interval):
                    return
            self.pending.put_nowait((None, "idle", cancelled))

        threading.Thread(target=show, daemon=True, name="table-lights-check").start()

    def _run(self):
        while True:
            item = self.pending.get()
            key = None
            done = None
            try:
                if item is None:
                    return
                if len(item) >= 3:
                    done = item[3] if len(item) == 4 else None
                    if item[2].is_set():
                        continue
                    item = item[:2]
                module = importlib.import_module("apps.talking_table.lights")
                # Read the switch and key at execution, never when queuing.
                # The original two-argument hook remains valid in pretend mode.
                key = self.current_key()
                result = module.set_scene(*item, api_key=key) if key else module.set_scene(*item)
                if isinstance(result, dict) and result.get("error"):
                    LOG.warning("Optional lights failed; turn unchanged.")
            except ModuleNotFoundError as exc:
                if exc.name != "apps.talking_table.lights":
                    LOG.warning("Optional lights unavailable; turn unchanged.")
            except Exception:
                # Driver messages can contain arbitrary input; do not print them.
                LOG.warning("Optional lights failed; turn unchanged.")
            finally:
                # Do not retain a plaintext credential while waiting for the
                # next scene (Settings may forget it during that wait).
                key = None
                if done is not None:
                    done.set()
                self.pending.task_done()

    def close(self):
        self.submit(None, "idle")
        self.pending.put_nowait(None)


def _card_decision(record):
    """A nameless display/audit projection, never a replacement policy decision."""
    safety = record.get("safety", {})
    fields = ("action", "disclosures", "crisis_read", "crisis_classes",
              "lexicon_status", "card", "card_order", "patterns_hash", "pack_ids",
              "latch", "register_caps", "screen_folds")
    explanation = "safety = HUMAN_ESCALATION\nThe crisis card holds the floor."
    if safety.get("screen_folds"):
        explanation += "\nScreen read a folded copy: " + ", ".join(safety["screen_folds"])
    return {
        "outcome": record.get("outcome"), "agent_id": None,
        "assist_agent_id": None, "shadow_agent_id": None,
        "safety": {key: copy.deepcopy(safety[key]) for key in fields if key in safety},
        "explain": explanation,
        "presentation_note": "Character-routing details are omitted from this card record.",
    }


class _Cancelled(Exception):
    pass


def _reply_surface(text):
    """Normalize a detection copy, never rewrite an accepted model's words.

    Compatibility and look-alike letters, accents, typographic punctuation
    and invisible formatting must not hide a reserved role. Keeping newlines
    here also lets speaker labels be checked independently of surrounding prose.
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(SKELETON.get(char, char) for char in text).casefold()
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
    r"\byou (?:are|re) (?:all )?the house\b",
    r"\b(?:this|that|it) (?:is|was|s) (?:a|the) house line\b",
    r"\b(?:a|the) house line from (?:the )?table\b",
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
    if re.search(r"\[\s*(?:the\s+)?house(?:[\W_]+line)?\s*\]", surface):
        return True
    if re.search(r"^[\s#>*_`-]*(?:from\s+)?(?:the\s+)?house"
                 r"(?:[\W_]+line)?[\s*_`]*[:|]",
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
    # T2's fixed house copy remains outside the character's voice, including
    # normalized spelling and the name slots in the two offer templates.
    for key in ("ask_acknowledgement", "handback_offer", "assist_offer",
                "made_page_footer", "object_refused", "card_aftermath", "room_note"):
        parts = re.split(r"(\{[A-Za-z_]+\})", HARNESS_LINES_EN[key])
        pattern = r" *".join(r"\w+(?: \w+){0,12}" if part.startswith("{") else
                             re.escape(_reply_words(part)) for part in parts if part)
        if re.search(r"\b" + pattern + r"\b", words):
            return True
    return False


class _TurnJob:
    """The supplied Harness routes once; only its optional model work can wait."""

    def __init__(self, app, text, *, tag="", action=None, target=None):
        self.app, self.text = app, text
        self.action, self.target = action, target
        self.ready = threading.Event()
        self.admitted = threading.Event()
        self.done = threading.Event()
        self.cancelled = threading.Event()
        self.gate = False
        self.result = None
        self.error = False
        self.receipt = None
        self.record = None
        self.accepted = False
        self.model_calls = 0
        self.revision = 0
        self.session_id = app.session_id
        self.harness = copy.copy(app.harness)
        self.harness.session = copy.deepcopy(app.harness.session)
        self.harness.transcript = copy.deepcopy(app.harness.transcript)
        self.harness.turns = []
        self.harness.room = app.settings["room"] or None
        self.harness.object_text = app.object_text
        self.harness.draft_tag = tag
        self.harness.adapter = _GuardedAdapter(self, app.harness.adapter)
        self.harness.audit_log = _TableAudit(self, app.harness.audit_log)
        self.harness.decision_observer = self.observe

    def observe(self, record):
        self.record = record

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
            # Only this cancelled worker waits for its own receipt. The crisis
            # worker never waits for this file or takes its independent lock.
            if self.cancelled.is_set() and self.accepted and self.receipt is None and self.record:
                try:
                    self.app._cancelled_receipt(self)
                except Exception:
                    LOG.warning("A superseded decision receipt could not be saved.")
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
                job.model_calls += 1
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
            safe["actual_model_calls"] = job.model_calls
            if not job.model_calls:
                safe["declared_preferences"] = {}
                safe["preference_adjustments"] = []
                safe["presentation_instructions"] = {}
            safe = app._redact(safe)
        # An optional operator-review disk wait may not hold the card hostage.
        # The unchanged harness already returns its card when audit writing fails.
        if not app.audit_lock.acquire(blocking=not gate):
            raise OSError("The audit writer is busy.")
        try:
            if job.cancelled.is_set():
                raise _Cancelled()
            row_id = self.sink.append(safe)
            job.audit_row_id = row_id
        finally:
            app.audit_lock.release()
        names = {persona: profile.name_for(
            job.harness.presentation.get(persona, "as_written"),
            job.harness.chosen_names.get(persona))[0]
            for persona, profile in app.roster.items()}
        receipt = decision_receipt(safe, names)
        if not gate:
            receipt["at"] = safe.get("at", time.time())
            receipt = app._redact(receipt)
            receipt["audit_row_id"] = row_id
            # A slow receipt never owns the audit lock the card needs.
            with app.receipt_lock:
                receipt_id = app.receipts.append(receipt)
                receipt = app.receipts.read(receipt_id)
        job.receipt = receipt
        return row_id


class TableApp(TableFeatures):
    input_error = InputError

    def __init__(self, data_dir: Path | None = None,
                 harness_factory: Callable[[], Harness] | None = None,
                 speech_transport: Callable | None = None):
        self.data_dir = (data_dir or Path.home() / ".secondsignal" / "talking-table").resolve()
        if self.data_dir == ROOT or ROOT in self.data_dir.parents:
            raise InputError("The storage folder must be outside the repository.")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.data_dir / "settings.json"
        self.audit_path = self.data_dir / "audit.jsonl"
        self.receipt_path = self.data_dir / "receipts.jsonl"
        self.preferences_path = self.data_dir / "preferences.json"
        self.receipts = AuditLog(self.receipt_path)
        self.lock = threading.RLock()
        self.audit_lock = threading.Lock()
        self.receipt_lock = threading.Lock()
        self.model_slots = threading.BoundedSemaphore(4)
        self.speech_slots = threading.BoundedSemaphore(2)
        self.speech_transport = speech_transport or self._voice_transport
        self.speech_tokens = {}
        self.preview_snapshot = None
        self.voice_revision = time.time_ns() // 1_000_000
        self.jobs = set()
        self.session_id = secrets.token_hex(12)
        self.revision = 0
        self.object_text = ""
        self.object_notice = None
        self.deferred_ask = None
        self._handback_ready = False
        self._last_record = None
        self._last_released = False
        self._last_revision = 0
        self.pages = {}
        # Separate from turn revisions, which reset with each conversation.
        # Milliseconds fit exactly in browser integers and order server restarts.
        self.mode_revision = time.time_ns() // 1_000_000
        self.settings = {"adapter": "fake", "model": "fake-1", "url": "",
                         "remember": False, "operator_circle": False,
                         "presentation": "as_written", "chosen_names": {},
                         "voice_enabled": False, "voice_remember": False,
                         "lights_enabled": False, "lights_remember": False,
                         "voice_slots": {}, "locale": "",
                         "declared_preferences": {}, "humour_grief": False,
                         "language_style": "match", "house_name": "", "room": "",
                         "presentation_overrides": {}}
        self.key = ""
        self.voice_key = ""
        self.lights_key = ""
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
        self.pairing_records: dict[str, dict] = {}
        self.computer = {"scope": "computer"}
        self.pair_attempts: dict[str, list[float]] = {}
        self.lights = SceneWorker(self._lights_key)
        self._load_settings()
        self._load_preferences()
        self.harness = self._build_harness()
        self._samples = presentation_samples(self.roster, self.harness.codexes, PRESENTATIONS)
        self.state = self._idle_state()
        self._init_features()

    def _idle_state(self):
        return {"seated": None, "assist": None, "state": "idle",
                "presentation": self.settings["presentation"], "turn_count": 0,
                "session_id": self.session_id, "revision": self.revision,
                **self._extras_state(),
                **self._mode_state()}

    def _presentation_for(self, persona):
        return self.settings["presentation_overrides"].get(persona, self.settings["presentation"])

    def _name_for(self, persona):
        return self.roster[persona].name_for(
            self._presentation_for(persona), self.settings["chosen_names"].get(persona))[0]

    def _ask_control(self, persona, key):
        name = self._name_for(persona)
        return {"persona": persona,
                "label": HARNESS_LINES_EN[key].format(Asked=name, Assist=name, Name=name),
                "text": f"Could I talk to {name}?"}

    def _extras_state(self):
        """Only explicit controls and the already returned record feed the display."""
        record = self._last_record or {}
        seated = record.get("agent_id")
        eligible = eligible_agents(record)
        handback = (self._ask_control(self.deferred_ask, "handback_offer")
                    if self._handback_ready and self.deferred_ask in eligible
                    and self.deferred_ask != seated else None)
        assist = record.get("assist_agent_id")
        slip = (self._ask_control(assist, "assist_offer")
                if seated and assist in self.roster else None)
        opinions = []
        # The standing held-turn limit is shared across the optional house
        # offers; the always-available handback and assist use those slots first.
        opinion_limit = max(0, 2 - bool(handback) - bool(slip)) if record.get("held") else 3
        if self._last_released and opinion_limit:
            for persona in eligible:
                if persona in self.roster and persona != seated:
                    line = HARNESS_LINES_EN["second_opinion"].format(Name=self._name_for(persona))
                    opinions.append({"persona": persona, "label": line, "text": line,
                                     "source_revision": self._last_revision,
                                     "source_session": self.session_id})
                if len(opinions) == opinion_limit:
                    break
        if self._last_revision in self.pages:
            opinions = copy.deepcopy(self.pages[self._last_revision][2])
        return {"house_name": self.settings["house_name"],
                "presentation_overrides": dict(self.settings["presentation_overrides"]),
                "chosen_names": dict(self.settings["chosen_names"]),
                "deferred_ask": self.deferred_ask, "handback": handback,
                "assist_offer": slip, "second_opinions": opinions,
                "object_text": self.object_text, "object_notice": self.object_notice}

    @staticmethod
    def _one_line(value, limit, label):
        if (not isinstance(value, str) or len(value) > limit
                or any(unicodedata.category(char) in {"Cc", "Zl", "Zp"} for char in value)):
            raise InputError(HARNESS_LINES_EN["t2_one_line"].format(label=label, limit=limit))
        return value.strip()

    def set_object(self, text):
        with self.lock:
            if self.state["state"] == "card":
                return {"object_text": "", "object_notice": None, "state": dict(self.state)}
            if not isinstance(text, str):
                raise InputError(HARNESS_LINES_EN["t2_one_line"].format(label="Object on the table", limit=60))
            # The public pure crisis screen checks this declaration alone. It
            # never advances or annotates the real policy session.
            if crisis_screen(text).read != "MISS":
                self.object_text = ""
                self.object_notice = HARNESS_LINES_EN["object_refused"]
            else:
                value = self._one_line(text, 60, "Object on the table")
                if self._has_key(value):
                    raise InputError("Keep keys in the key field, outside the conversation.")
                self.object_text, self.object_notice = value, None
            self.state.update(self._extras_state())
            self._publish()
            return {"object_text": self.object_text, "object_notice": self.object_notice,
                    "state": dict(self.state)}

    def made_page(self, path):
        """Serve an already released turn, never text supplied by a browser."""
        with self.lock:
            prefix = "/api/pages/" + self.session_id + "/"
            index = path[len(prefix):] if path.startswith(prefix) else ""
            saved = self.pages.get(int(index)) if re.fullmatch(r"[0-9]{1,20}", index) else None
            if not saved or self.state["state"] == "card":
                return None
            turn, name, _ = saved
            if not turn.released or not turn.persona_text or self._contains_key((turn.persona_text, name)):
                return None
            return ("<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
                    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
                    "<title>" + html.escape(name) + "</title>"
                    "<link rel=\"stylesheet\" href=\"/static/table.css\">"
                    "<main class=\"made-page\"><p class=\"byline\">" + html.escape(name) + "</p>"
                    "<pre class=\"made-text\">" + html.escape(turn.persona_text) + "</pre>"
                    "<footer>" + html.escape(HARNESS_LINES_EN["made_page_footer"])
                    + "</footer></main></html>").encode("utf-8")

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
                "voice_ready": self._voice_ready() or self._preview_ready(),
                "voice_revision": self.voice_revision}

    def _preview_ready(self):
        return bool(self.settings["voice_enabled"] and self.voice_key
                    and self.preview_snapshot == self._speech_snapshot())

    def _voice_ready(self):
        # Operator-circle mode no longer silences the voice (ruling 6 of
        # 3 October 2026); the released kinds decide, in _finish_job.
        return bool(self.settings["voice_enabled"] and self.voice_key
                    and any(slots[self._presentation_for(persona)]
                            for persona, slots in self.settings["voice_slots"].items()))

    def _lights_key(self):
        with self.lock:
            return self.lights_key if self.settings["lights_enabled"] else None

    def _remember_key(self, key):
        if key:
            self.key_fingerprints.add((len(key), hashlib.sha256(key.encode("utf-8")).digest()))

    def _has_key(self, text):
        # Past credentials can be recognised without retaining their plaintext.
        if any(key and key in text for key in (self.key, self.voice_key, self.lights_key)):
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
        if (re.search(r"<\s*[!/?a-zA-Z]", text)
                or re.search(r"(?:javascript|vbscript|data):\S", text)
                or _reserved_reply_voice(reply.text)):
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
        if hasattr(self.lights, "cancel_check"):
            self.lights.cancel_check()
        self.voice_revision += 1
        self.speech_tokens.clear()
        self.preview_snapshot = None
        for job in self.jobs:
            job.cancelled.set()

    def _superseded(self):
        return {"kind": "withheld", "superseded": True, "persona": None,
                "assist": None, "text": "", "house_lines": [], "card": None,
                "verdict": None, "decision": {}, "speech_token": None,
                "state": dict(self.state)}

    def _cancelled_receipt(self, job):
        applied, adjustments = applied_preferences(job.record, job.harness.declared_preferences)
        names = {persona: profile.name_for(
            job.harness.presentation.get(persona, "as_written"),
            job.harness.chosen_names.get(persona))[0] for persona, profile in self.roster.items()}
        receipt = decision_receipt({
            "decision": job.record, "action": job.record["safety"]["action"],
            "turn_index": job.harness.session.turn_count, "adapter_calls": job.model_calls,
            "release_reason": "superseded", "released": False,
            "declared_preferences": applied if job.model_calls else {},
            "preference_adjustments": adjustments if job.model_calls else (),
            "presentation_instructions": ({
                "language_style": job.harness.language_style,
                **({"humour_grief_opt_in": True} if job.harness.humour_grief else {}),
            } if job.model_calls else {}),
        }, names)
        receipt["audit_row_id"] = None
        receipt["at"] = time.time()
        receipt = self._redact(receipt)
        with self.receipt_lock:
            receipt_id = self.receipts.append(receipt)
            job.receipt = self.receipts.read(receipt_id)

    def presentation_previews(self):
        previews = copy.deepcopy(self._samples)
        for presentation, personas in previews.items():
            for persona, sample in personas.items():
                sample["voice_available"] = bool(
                    self.settings["voice_enabled"] and self.voice_key
                    and self.settings["voice_slots"][persona][presentation]
                    and self.state["state"] != "card")
        return previews

    def preview(self, payload):
        """Issue a capability for a codex quotation, never browser-supplied text."""
        if not isinstance(payload, dict) or set(payload) != {"persona", "presentation"}:
            raise InputError("Choose a listed presentation preview.")
        persona, presentation = payload["persona"], payload["presentation"]
        if (not isinstance(persona, str) or persona not in self.roster
                or not isinstance(presentation, str) or presentation not in PRESENTATIONS):
            raise InputError("Choose a listed presentation preview.")
        with self.lock:
            sample = self.presentation_previews()[presentation][persona]
            if not sample["voice_available"]:
                raise InputError(VOICE_ERROR)
            self.speech_tokens.clear()
            token = secrets.token_urlsafe(32)
            voice_id = self.settings["voice_slots"][persona][presentation]
            if self._contains_key((voice_id, sample["text"])):
                raise InputError(VOICE_ERROR)
            self.speech_tokens[token] = (self._speech_snapshot(), voice_id, sample["text"], True)
            # Polling must not stop a preview merely because the currently
            # saved presentation has no slot. Every normal invalidation still
            # revokes this snapshot together with the single-use token.
            self.preview_snapshot = self._speech_snapshot()
            self.state.update(self._mode_state())
            self._publish()
            snapshot = dict(self.state)
            snapshot["voice_ready"] = True
            return {"kind": "reply", "speech_token": token, "state": snapshot,
                    "text": sample["text"], "preview": True}

    def _load_settings(self):
        if not self.settings_path.exists():
            return
        try:
            saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
            saved_settings = saved.get("settings", {})
            if not isinstance(saved_settings, dict):
                raise InputError("Saved settings could not be accepted.")
            if not self.operator_token_available():
                saved_settings = {**saved_settings, "operator_circle": False}
            # Presentation is visit-only in the current push, including when
            # loading a settings file written by an older Talking Table.
            settings = self._validate_settings({k: v for k, v in saved_settings.items()
                                                if k not in ("presentation", "chosen_names", *REMEMBERED_EXTRAS)})
            # Each key has its own opt-in; remembering one cannot save or
            # restore either of the other credentials.
            keys = {}
            for name, flag, blob_name in (("key", "remember", "key_blob"),
                                          ("voice_key", "voice_remember", "voice_key_blob"),
                                          ("lights_key", "lights_remember", "lights_key_blob")):
                keys[name] = (_secret_blob(base64.b64decode(saved[blob_name], validate=True),
                                          decrypt=True).decode("utf-8")
                              if settings[flag] and blob_name in saved else "")
            if self._contains_key(settings, keys.values()):
                raise InputError("Saved settings could not be accepted.")
            self.settings.update(settings)
            self.key, self.voice_key = keys["key"], keys["voice_key"]
            self.lights_key = keys["lights_key"]
            for key in keys.values():
                self._remember_key(key)
        except Exception:
            LOG.warning("Saved settings could not be read; using the pretend model.")

    def _load_preferences(self):
        # Separate from every credential blob and keyed only by this local file.
        if not self.preferences_path.exists():
            return
        try:
            saved = json.loads(self.preferences_path.read_text(encoding="utf-8"))
            if not isinstance(saved, dict) or set(saved) - {
                    "declared_preferences", "humour_grief", "language_style",
                    "presentation", "chosen_names", *REMEMBERED_EXTRAS}:
                raise InputError("Saved presentation settings could not be accepted.")
            settings = self._validate_settings(saved)
            if self._contains_key(settings):
                raise InputError("Saved presentation settings could not be accepted.")
            self.settings.update(settings)
            # The separate file is itself the remember opt-in. A missing or
            # unreadable credential blob cannot erase declared presentation.
            self.settings["remember"] = True
        except Exception:
            LOG.warning("Declared presentation settings could not be read; using defaults.")

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
        if "house_name" in proposed:
            result["house_name"] = self._one_line(proposed["house_name"], 40, "The table's name")
        if "room" in proposed:
            room = proposed["room"]
            if not isinstance(room, str) or room not in {"", *ROOM_LINES}:
                raise InputError(HARNESS_LINES_EN["t2_room_invalid"])
            result["room"] = room
        if "presentation_overrides" in proposed:
            overrides = proposed["presentation_overrides"]
            if (not isinstance(overrides, dict) or set(overrides) - set(self.roster)
                    or any(not isinstance(value, str) or value not in PRESENTATIONS
                           for value in overrides.values())):
                raise InputError(HARNESS_LINES_EN["t2_override_invalid"])
            result["presentation_overrides"] = dict(overrides)
        if "locale" in proposed:
            # The country for the crisis card's resource line (the operator's
            # answer 10 of 12, 4 October 2026). Declared here, never inferred;
            # the shipped default is none, which reads the directory line.
            value = proposed["locale"]
            if not isinstance(value, str) or (value and value not in LOCALES):
                raise InputError("Choose a listed country, or none.")
            result["locale"] = value
        if "declared_preferences" in proposed:
            declared = proposed["declared_preferences"]
            if (not isinstance(declared, dict) or set(declared) - set(STYLE_VALUES)
                    or any(not isinstance(value, str) or value not in STYLE_VALUES[key]
                           for key, value in declared.items())):
                raise InputError("Choose only listed reply presentation settings.")
            # Saving the settings form is the person's explicit confirmation.
            result["declared_preferences"] = dict(declared)
        if "language_style" in proposed:
            style = proposed["language_style"]
            if not isinstance(style, str) or style not in LANGUAGE_STYLES:
                raise InputError("Choose a listed language style.")
            result["language_style"] = style
        for name in ("remember", "operator_circle", "voice_enabled", "voice_remember",
                     "lights_enabled", "lights_remember", "humour_grief"):
            if name in proposed:
                if not isinstance(proposed[name], bool):
                    raise InputError("A switch must be on or off.")
                result[name] = proposed[name]
        if result["operator_circle"] and not self.operator_token_available():
            raise InputError(TOKEN_NOTE)
        if "lights_key" in proposed and (not isinstance(proposed["lights_key"], str)
                                          or len(proposed["lights_key"]) > 4096):
            raise InputError("The lights key must be text.")
        if "clear_lights_key" in proposed and not isinstance(proposed["clear_lights_key"], bool):
            raise InputError("A switch must be on or off.")
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
                       locale=setting["locale"] or None,
                       presentation={name: self._presentation_for(name) for name in self.roster},
                       chosen_names=setting["chosen_names"],
                       declared_preferences=setting["declared_preferences"],
                       humour_grief=setting["humour_grief"],
                       language_style=setting["language_style"],
                       room=setting["room"] or None,
                       operator_circle=setting["operator_circle"])

    def config(self, local=True):
        self.token_ready = self.operator_token_available()
        with self.lock:
            settings = copy.deepcopy(self.settings)
            settings["operator_circle"] = bool(self.harness.operator_circle)
            settings["key_set"] = bool(self.key)
            settings["voice_key_set"] = bool(self.voice_key)
            settings["lights_key_set"] = bool(self.lights_key)
            settings["voice_ready"] = self._voice_ready() or self._preview_ready()
            return {
                "settings": settings,
                "roster": [{"id": p.id, "plate": p.plate, "one_line": p.one_line,
                            "domains": sorted(p.domains), "modes": sorted(p.modes),
                            "contraindications": sorted(p.contraindications),
                            "handoffs": dict(p.handoffs),
                            "names": {v: p.name_for(v, self.settings["chosen_names"].get(p.id))
                                      for v in sorted(PRESENTATIONS)}} for p in self.roster.values()],
                "storage": (
                    f"Audit logs keep messages, accepted model output (including audit-withheld replies), "
                    f"and decisions in {self.audit_path}. Unsafe model output is discarded; known keys "
                    f"are redacted, and card records omit character-routing details. "
                    f"Non-crisis decision receipts are in {self.receipt_path}; they omit message text, "
                    f"raw stems and crisis patterns. Confirmed reply preferences are remembered in "
                    f"{self.preferences_path} under Remember, separately from credentials. "
                    f"Presentation and name choices are also remembered in {self.preferences_path} "
                    f"under Remember. Conversation state and pairing stay in memory. "
                    f"Remembered settings and independently encrypted model, voice and lights keys are kept in "
                    f"{self.settings_path} only for the corresponding remember switches. "
                    f"New session clears unremembered keys and keeps existing audit logs. "
                    f"review_queue.jsonl keeps explicitly flagged turn snapshots; terms.json keeps "
                    f"vendor confirmations only under Remember, separately from keys. "
                    f"operator.token enables the local operator-circle control and is generated "
                    f"only by the operator's local command. Temporary .tmp files stage settings saves."
                ),
                "phone": {"enabled": self.phone_server is not None,
                          "code": self.pairing_code if local else None,
                          "urls": self.phone_server.urls if self.phone_server and local else []},
                "local": local,
                "sigils_available": (STATIC / "sigils.html").is_file(),
                "presentation_previews": self.presentation_previews(),
                "t2_copy": {key: HARNESS_LINES_EN[key] for key in (
                    "room_note", "handback_offer", "assist_offer", "second_opinion",
                    "made_page_footer", "object_refused")},
                "resource": resources(self.settings["locale"] or None),
                "honesty": self.honesty(),
                "state": self.sitting(),
            }

    def update_settings(self, proposed):
        with self.terms_lock, self.lock:
            settings = self._validate_settings(proposed)
            candidate = proposed.get("key", "")
            if not isinstance(candidate, str) or len(candidate) > 4096:
                raise InputError("The key must be text.")
            voice_candidate = proposed.get("voice_key", "")
            if not isinstance(voice_candidate, str) or len(voice_candidate) > 4096:
                raise InputError("The voice key must be text.")
            lights_candidate = proposed.get("lights_key", "")
            changed_host = (settings["adapter"], settings["url"]) != (
                self.settings["adapter"], self.settings["url"])
            key = candidate.strip() or ("" if changed_host else self.key)
            if proposed.get("clear_key") is True:
                key = ""
            voice_key = voice_candidate.strip() or self.voice_key
            if proposed.get("clear_voice_key") is True:
                voice_key = ""
            lights_key = lights_candidate.strip() or self.lights_key
            if proposed.get("clear_lights_key") is True:
                lights_key = ""
            if self._contains_key(settings, (key, voice_key, lights_key, candidate.strip(),
                                            voice_candidate.strip(), lights_candidate.strip())):
                raise InputError("Put the key only in the key field.")
            # Complete the durable write before adopting the new settings.
            settings_payload = None
            if settings["remember"] or settings["voice_remember"] or settings["lights_remember"]:
                # Presentation and style belong in their separate local file,
                # never beside any encrypted credential blob.
                saved = {"settings": {k: copy.deepcopy(v) for k, v in settings.items()
                                      if k not in ("presentation", "chosen_names", "declared_preferences",
                                                   "humour_grief", "language_style", *REMEMBERED_EXTRAS)}}
                for secret, flag, blob_name in ((key, "remember", "key_blob"),
                                                (voice_key, "voice_remember", "voice_key_blob"),
                                                (lights_key, "lights_remember", "lights_key_blob")):
                    if settings[flag] and secret:
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
                if not settings["lights_remember"]:
                    saved["settings"]["lights_enabled"] = False
                settings_payload = json.dumps(saved, ensure_ascii=False)
            preferences_payload = None
            if settings["remember"]:
                preference_payload = {key: settings[key] for key in (
                    "declared_preferences", "humour_grief", "language_style",
                    "presentation", "chosen_names")}
                # Preserve the T1 file shape when every T2 control is unset.
                preference_payload.update({key: settings[key] for key in REMEMBERED_EXTRAS
                                           if settings[key]})
                preferences_payload = json.dumps(preference_payload)
            terms_payload = json.dumps(self.confirmations) if settings["remember"] and self.confirmations else None
            self._persist_settings(settings_payload, preferences_payload, terms_payload)
            self.settings = settings
            self.key = key
            self.voice_key = voice_key
            self.lights_key = lights_key
            self._remember_key(key)
            self._remember_key(voice_key)
            self._remember_key(lights_key)
            self._cancel_jobs()
            # Settings must never clear the policy latch or the conversation.
            previous = self.harness
            self.harness = self._build_harness()
            self.harness.session = previous.session
            # The country applies to the conversation in progress; the session
            # itself (latch, aftermath, holds) is never reset by a setting.
            self.harness.session.locale = settings["locale"] or None
            self.harness.transcript = previous.transcript
            self.harness.turns = previous.turns
            self.mode_revision += 1
            self.state["presentation"] = settings["presentation"]
            if self.state["state"] != "card":
                self.state.update(self._extras_state())
            self.state.update(self._mode_state())
            self.pending_turn = None
            self._publish()
            return self.config()

    def _persist_settings(self, settings_payload, preferences_payload, terms_payload=None):
        """Stage independent files; an ordinary I/O failure adopts none."""
        updates = ((self.preferences_path, preferences_payload),
                   (self.settings_path, settings_payload), (self.terms_path, terms_payload))
        originals = {path: path.read_bytes() if path.exists() else None for path, _ in updates}
        changed = []
        try:
            for path, payload in updates:
                if payload is not None:
                    path.with_suffix(".tmp").write_text(payload, encoding="utf-8")
            for path, payload in updates:
                if payload is None:
                    path.unlink(missing_ok=True)
                else:
                    path.with_suffix(".tmp").replace(path)
                changed.append(path)
        except OSError:
            for path in reversed(changed):
                previous = originals[path]
                if previous is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(previous)
            raise InputError("The computer could not save these settings; the previous settings remain.") from None
        finally:
            for path, _ in updates:
                path.with_suffix(".tmp").unlink(missing_ok=True)

    def reset(self, harness: Harness | None = None):
        with self.lock:
            self._cancel_jobs()
            self.session_id = secrets.token_hex(12)
            self.revision = 0
            if not self.settings["remember"]:
                self.key = ""
            if not self.settings["voice_remember"]:
                self.voice_key = ""
            if not self.settings["lights_remember"]:
                self.lights_key = ""
            self.settings["presentation"] = "as_written"
            self.settings["chosen_names"] = {}
            self.settings["presentation_overrides"] = {}
            self.object_text, self.object_notice = "", None
            self.deferred_ask = None
            self._handback_ready = False
            self._last_record = None
            self._last_released = False
            self._last_revision = 0
            self.pages.clear()
            self.harness = harness if harness is not None else self._build_harness()
            self.mode_revision += 1
            self.state = self._idle_state()
            self._reset_features()
            self.lights.submit(None, "idle")
            return self.config()

    def _control_error(self, text, action, target, source_revision, source_session):
        if action is None and target is None and source_revision is None and source_session is None:
            return None
        if (not isinstance(action, str) or action not in ("ask", "handback", "assist", "second_view")
                or not isinstance(target, str) or target not in self.roster):
            return HARNESS_LINES_EN["t2_control_unavailable"]
        if action == "ask":
            expected = f"Could I talk to {self._name_for(target)}?"
        else:
            fields = self._extras_state()
            choices = (fields["second_opinions"] if action == "second_view" else
                       [fields["handback" if action == "handback" else "assist_offer"]])
            if action == "second_view" and (source_revision is not None or source_session is not None):
                if (type(source_revision) is not int or source_session != self.session_id
                        or source_revision not in self.pages):
                    return HARNESS_LINES_EN["t2_control_unavailable"]
                choices = self.pages[source_revision][2]
            match = next((choice for choice in choices if choice and choice["persona"] == target), None)
            if match is None or self.state["state"] == "card":
                return HARNESS_LINES_EN["t2_control_unavailable"]
            expected = match["text"]
        return None if text == expected else HARNESS_LINES_EN["t2_control_unchanged"]

    def turn(self, text, *, tag="", action=None, target=None,
             source_revision=None, source_session=None):
        # Transport/type limits are needed to obtain text. Content checks happen
        # only AFTER the unchanged harness has run the policy gate on that text.
        if not isinstance(text, str):
            raise InputError("Write a message of 1 to 16000 characters.")
        with self.lock:
            tag_valid = isinstance(tag, str) and tag in DRAFT_TAGS
            # Bad metadata never prevents the raw message's crisis gate.
            control_error = self._control_error(text, action, target, source_revision, source_session)
            job = _TurnJob(self, text, tag=tag if tag_valid else "", action=action, target=target)
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
                if not tag_valid or control_error:
                    job.cancelled.set()
                    job.admitted.set()
                    raise InputError(control_error or HARNESS_LINES_EN["t2_tag_invalid"])
            terms = self.terms_summary() if not job.gate and job.record and job.record.get("agent_id") else None
            if not job.gate and job.record and job.record.get("agent_id") and terms and not terms["confirmed"]:
                job.cancelled.set()
                job.admitted.set()
                error = InputError("Read the vendor terms summary and confirm the key attestation before a live reply.")
                error.terms = terms
                raise error
            self._cancel_jobs()
            self.revision += 1
            job.revision = self.revision
            self.jobs.add(job)
            job.accepted = True
            if not job.gate and action == "handback":
                self.deferred_ask = None
                self._handback_ready = False
            # Commit only the routed session, before any optional model call.
            # Preserve identity for settings/session consumers. Completion must
            # never copy an old session back over a newer crisis latch.
            self.harness.session.__dict__.update(copy.deepcopy(job.harness.session.__dict__))
            self.harness.transcript.append({"role": "user", "content": self._redact(text)})
            self.state["turn_count"] = self.harness.session.turn_count
            self.state["revision"] = self.revision
            self.state.update(self._mode_state())
            self._posted(job)
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
        if (job.cancelled.is_set() or job.session_id != self.session_id
                or job.revision != self.revision):
            return self._superseded()
        if job.error or job.result is None:
            self.pending_turn = None
            self._publish()
            raise InputError("This message could not be processed. Send it again to try again.")
        turn = job.result
        gate = turn.action == "HUMAN_ESCALATION"
        kind = "card" if gate else "reply" if turn.released else (
            "withheld" if turn.agent_id else "house")
        persona = None if gate else turn.agent_id
        assist = None if gate else turn.decision.get("assist_agent_id")
        state = "card" if gate else "seated" if persona else "idle"
        public_decision = _card_decision(turn.decision) if gate else turn.decision
        receipt = job.receipt or decision_receipt({
            "action": turn.action, "decision": public_decision,
            "release_reason": turn.release_reason}, {})
        if not gate:
            declared = (job.target if job.action in {"ask", "assist"} else
                        asked_agent(turn.decision, self.roster))
            if declared and declared != persona:
                self.deferred_ask = declared
                self._handback_ready = False
            elif self.deferred_ask == persona:
                self.deferred_ask = None
                self._handback_ready = False
            else:
                self._handback_ready = True
            self._last_record = turn.decision
            self._last_released = turn.released
            self._last_revision = job.revision
            self.object_notice = None
        self.state = {"seated": persona, "assist": assist, "state": state,
                      "presentation": self.settings["presentation"],
                      "turn_count": self.harness.session.turn_count,
                      "session_id": self.session_id, "revision": job.revision,
                      "receipt": receipt, "card": turn.text if gate else None,
                      "card_revision": job.revision if gate else None,
                      "decision": public_decision if gate else None,
                      **({} if gate else self._extras_state()),
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
            "verdict": verdict, "decision": public_decision,
            "receipt": receipt,
            "effort_contract": (not gate and turn.released
                                and turn.declared_preferences.get("pace") == "one_step"),
            "action": turn.action, "adapter_calls": turn.adapter_calls,
            "display_name": self._name_for(persona) if persona else None,
            "presentation": self.settings["presentation"],
            "cultural_only": cultural,
            "notice": None if gate else turn.notice,
            "state": dict(self.state), "release_reason": turn.release_reason,
            "speech_token": None,
        }
        if not gate:
            result.update(self._extras_state())
            result["tag"] = job.harness.draft_tag
            result["second_view"] = bool(turn.released and job.action == "second_view")
            result["ask_acknowledgement"] = turn.ask_acknowledgement
            if turn.released:
                self.pages[job.revision] = (turn, result["display_name"],
                                            copy.deepcopy(result["second_opinions"]))
                result["page_url"] = f"/api/pages/{self.session_id}/{job.revision}"
        # The capability names an already released, audited character reply.
        # The browser never supplies text or a character to the speech engine.
        text = self._speech_text(turn, previous) if kind == "reply" else None
        if text is not None and self._voice_ready() and persona in self.roster:
            voice_id = self.settings["voice_slots"][persona][self._presentation_for(persona)]
            if voice_id and not self._contains_key(text):
                token = secrets.token_urlsafe(32)
                self.speech_tokens[token] = (self._speech_snapshot(), voice_id, text, False)
                result["speech_token"] = token
        result = result if gate else self._redact(result)
        self._displayed(job, result)
        return result

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
            preview = bool(issued and issued[3])
            ready = (self.settings["voice_enabled"] and self.voice_key
                     if preview else self._voice_ready())
            if (not issued or issued[0] != self._speech_snapshot()
                    or not ready or self.state["state"] == "card"
                    or (not preview and self.state["state"] != "seated")):
                raise InputError(VOICE_ERROR)
            snapshot, voice_id, text, _ = issued
            key = self.voice_key
            # Binary substring checks stay linear in the bounded audio size.
            # Credential rotation invalidates this snapshot before release.
            protected_audio = tuple(secret.encode("utf-8")
                                    for secret in (self.key, self.voice_key, self.lights_key) if secret)
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
            ready = (self.settings["voice_enabled"] and self.voice_key
                     if preview else self._voice_ready())
            if (snapshot != self._speech_snapshot() or not ready
                    or self.state["state"] == "card"
                    or (not preview and self.state["state"] != "seated")):
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
                self.pairing_records.clear()
                self.pair_attempts.clear()
                # Shutdown may wait for a poll; keep that out of the request lock.
                threading.Thread(target=lambda: (server.shutdown(), server.server_close()),
                                 daemon=True).start()
            self._publish()
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
            self.pairing_records[token] = {"scope": "phone"}
            return token

    def close(self):
        with self.lock:
            self.closed = True
            self._publish()
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


def _sigils_policy(content):
    """Allow only this shipped page's inline script and style blocks.

    The standalone lights view carries its own script and CSS. The Table's
    normal self-only policy blocks both, so authorize their exact contents
    for this response while keeping every connection on the local Table.
    HTML normalizes line endings before checking CSP hashes.
    """
    normalized = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

    def hashes(tag):
        blocks = re.findall(rb"<" + tag + rb"\b[^>]*>(.*?)</" + tag + rb">",
                            normalized, re.S | re.I)
        return " ".join("'sha256-" + base64.b64encode(hashlib.sha256(block).digest()).decode("ascii")
                        + "'" for block in blocks) or "'none'"

    return ("default-src 'none'; script-src 'self' " + hashes(b"script")
            + "; style-src " + hashes(b"style")
            + "; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'none'")


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

    def _send(self, status, payload, content_type="application/json; charset=utf-8", cookie=None,
              policy=None):
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
        self.send_header("Content-Security-Policy", policy or "default-src 'self'; script-src 'self'; style-src 'self'; "
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

    def _scope(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            if COOKIE in cookie:
                record = self.server.app.pairing_records.get(cookie[COOKIE].value)
                return record.get("scope") if record else None
            if self.is_local:
                return self.server.app.computer["scope"]
        except Exception:
            pass
        return None

    def _paired(self):
        return self._scope() == "computer" or (
            self.server is self.server.app.phone_server and self._scope() == "phone")

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
        if any(path == prefix or (prefix.endswith("/") and path.startswith(prefix))
               for prefix in COMPUTER_PATHS) and self._scope() != "computer":
            self._send(403, {"error": "Use this control on the computer."})
            return False
        return True

    def _events(self):
        app = self.server.app
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Connection", "close")
        self.end_headers()
        version = -1
        # Bound every fetch, including under constant activity. Chromium's
        # virtual-time captures wait for pending network requests to finish.
        deadline = time.monotonic() + 1.0
        reconnect = False
        try:
            self.wfile.write(b"retry: 1000\n\n")
            self.wfile.flush()
            while self._paired():
                with app.events:
                    if app.closed:
                        break
                    if version == app.session_version:
                        app.events.wait(timeout=max(0, deadline - time.monotonic()))
                    if app.closed or not self._paired():
                        break
                    if time.monotonic() >= deadline:
                        # Clients poll across this planned gap; EventSource
                        # itself reconnects and receives the current snapshot.
                        reconnect = True
                        break
                    snapshot = app.sitting() if version != app.session_version else None
                if snapshot is not None:
                    version = snapshot["session_version"]
                    data = json.dumps(snapshot, ensure_ascii=False)
                    frame = f"id: {version}\nevent: state\ndata: {data}\n\n".encode("utf-8")
                else:
                    frame = b": keep-alive\n\n"
                self.wfile.write(frame)
                self.wfile.flush()
            if reconnect:
                self.wfile.write(b"event: reconnect\ndata: {}\n\n")
                self.wfile.flush()
        except (OSError, ConnectionError):
            pass
        self.close_connection = True

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if not self._authorize(path):
            return
        app = self.server.app
        if path == "/api/config":
            self._send(200, app.config(self._scope() == "computer"))
        elif path == "/api/state":
            self._send(200, app.sitting())
        elif path == "/api/events":
            self._events()
        elif path in ("/api/operator/state", "/api/replay", "/api/receipts/week", "/api/receipts/export"):
            try:
                if path == "/api/operator/state":
                    value = app.correction_state()
                elif path == "/api/replay":
                    query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    value = app.logged_decision(query.get("row_id", [None])[0])
                else:
                    value = app.receipt_week() if path.endswith("export") else app.refused_seats()
                self._send(200, value)
            except InputError as exc:
                self._send(400, {"error": str(exc)})
        elif path == "/api/resources":
            with app.lock:
                self._send(200, resources(app.settings["locale"] or None))
        elif path.startswith("/api/pages/"):
            page = app.made_page(path)
            if page is None:
                self._send(404, {"error": HARNESS_LINES_EN["t2_page_missing"]})
            else:
                self._send(200, page, "text/html; charset=utf-8")
        elif path in ("/", "/sigils.html", "/operator.html", "/replay.html") or path.startswith("/static/"):
            relative = ("index.html" if path == "/" else "sigils.html" if path == "/sigils.html"
                        else urllib.parse.unquote(path[8:]))
            if path in ("/operator.html", "/replay.html"):
                relative = path[1:]
            target = (STATIC / relative).resolve()
            if STATIC.resolve() not in target.parents or target.suffix not in {".html", ".js", ".css", ".json", ".svg"}:
                self._send(404, {"error": "File not found."})
            elif relative == "voice.js" and not target.exists():
                self._send(200, b"/* Optional voice module is not installed. */\n", "text/javascript; charset=utf-8")
            elif target.name in ("operator.html", "replay.html") and self._scope() != "computer":
                self._send(403, {"error": "Open this page on the computer."})
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
                                              b"Operator-circle mode is ON. A prototype for the operator's circle." if enabled else
                                              b"Operator-circle mode is OFF.")
                policy = _sigils_policy(content) if target == (STATIC / "sigils.html").resolve() else None
                self._send(200, content, content_type + "; charset=utf-8", policy=policy)
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
        if path in ("/api/settings", "/api/network") and self._scope() != "computer":
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
                self._send(200, app.turn(payload.get("text"), tag=payload.get("tag", ""),
                                         action=payload.get("action"), target=payload.get("target"),
                                         source_revision=payload.get("source_revision"),
                                         source_session=payload.get("source_session")))
            elif path == "/api/terms/confirm":
                self._send(200, app.confirm_terms(payload))
            elif path == "/api/review/flag":
                self._send(200, app.flag_turn(payload, self._scope()))
            elif path == "/api/operator/clear-latch":
                self._send(200, app.clear_careful_read(payload))
            elif path == "/api/lights/check":
                self._send(200, app.check_lights())
            elif path == "/api/object":
                self._send(200, app.set_object(payload.get("text")))
            elif path == "/api/voice":
                self._send(200, app.voice(payload), "audio/mpeg")
            elif path == "/api/presentation/preview":
                self._send(200, app.preview(payload))
            elif path == "/api/settings":
                self._send(200, app.update_settings(payload))
            elif path == "/api/session/reset":
                app.reset()
                self._send(200, app.config(self._scope() == "computer"))
            elif path == "/api/network":
                self._send(200, app.set_network(payload.get("enabled")))
            elif path == "/api/pair":
                token = app.pair(payload.get("code"), self.client_address[0])
                self._send(200, {"ok": True}, cookie=token)
            else:
                self._send(404, {"error": "Endpoint not found."})
        except InputError as exc:
            if getattr(exc, "terms", None):
                self._send(428, {"error": str(exc), "terms_required": True, "terms": exc.terms})
            else:
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
