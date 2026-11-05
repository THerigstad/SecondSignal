"""Machine-readable harness records, separate from policy (ADR-0035 (Proposed)).

Snapshots are content addressed with J.R.'s existing payload hash. Only that
function's top-level ``ranked`` exclusion applies; no clock or random run ID
is placed in a snapshot. Intervals use sitting turn ordinals. Storage and
logical change records are append-only; closing an interval appends a receipt.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import threading
from collections import Counter
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import unquote, urlsplit

from secondsignal.jr import payload_hash
from secondsignal.lexicon import PACK_DIR
from secondsignal.profiles import DEFAULT_PROFILE_DIR, AgentProfile
from secondsignal.safety import CRISIS_CARD

from .adapters import DEFAULT_TIMEOUT_SECONDS, AdapterReply, ModelAdapter
from .audit_log import canonical_row
from .codex import CodexStore
from .configuration import _CREDENTIAL, adapter_identity, safe_identifier
from .event_log import (
    MaterialChangeLog,
    SpecificationError,
    _file_identity,
    _read_bytes,
    _stream_identity,
    _write_handle,
    event_digest,
)


class SpecificationStampError(SpecificationError):
    """A turn stamp contradicts its active specification; this is not an I/O fault."""


SPEC_SCHEMA_VERSION = 1
AUDIT_ROW_SCHEMA = "secondsignal_harness.audit_row.v2"
COMPONENT_NAMES = (
    "orchestration and planning",
    "context and memory",
    "tool and action interfaces",
    "operational knowledge",
    "sandboxing",
    "permission model",
    "verification, evaluation and observability",
    "execution runtime and lifecycle management",
)
RECORD_NAMES = ("release", "declared_changeable", "run_start", "material_change_events", "run_end")
_STATUSES = ("implemented", "partial", "not-implemented", "implemented", "not-implemented",
             "implemented", "implemented", "partial")
_REASONS = (
    "",
    "The sitting keeps state and bounded prior turns. The Table persists latch and soft state; "
    "holds last this sitting only. There is no long-term conversation memory across sittings.",
    "No model is given tools or actions. Adapters accept text and return text; replies are never executed.",
    "",
    "No agent-executed code exists. Model output is text only; there is no execution sandbox to claim.",
    "",
    "",
    "The Table has sitting expiry, latch persistence, reload recovery, a response wait and model "
    "concurrency control. The harness has bounded retries and adapter transport timeouts. "
    "There is no durable full transcript checkpoint or resume of an interrupted model call. "
    "The plain harness relies on its caller for sitting expiry and concurrency control.",
)
_EVIDENCE = (
    ("src/secondsignal/router.py", "src/secondsignal_harness/table_extras.py", "apps/talking_table/server.py"),
    ("src/secondsignal_harness/harness.py", "src/secondsignal/safety.py", "apps/talking_table/t3.py"),
    ("src/secondsignal_harness/adapters.py", "src/secondsignal_harness/harness.py"),
    ("src/secondsignal_harness/codex.py", "src/secondsignal_harness/prompt.py", "src/secondsignal/profiles.py"),
    ("src/secondsignal_harness/adapters.py", "src/secondsignal_harness/harness.py"),
    ("src/secondsignal/safety.py", "src/secondsignal/router.py", "apps/talking_table/t3.py", "apps/talking_table/server.py"),
    ("src/secondsignal/jr.py", "src/secondsignal_harness/audit_log.py", "src/secondsignal_harness/spec.py",
     "src/secondsignal_harness/event_log.py", "evals/run_fixtures.py", "tests/test_h1_replay.py"),
    ("src/secondsignal_harness/harness.py", "src/secondsignal_harness/adapters.py", "apps/talking_table/server.py",
     "apps/talking_table/t3.py"),
)
_HEX = re.compile(r"[a-f0-9]{64}")
_JSON_SCALARS = (str, int)  # bool is an int subclass.
_JSON_SEQUENCES = (tuple, list)


def _json_copy(value: Any) -> Any:
    """Require actual JSON types, finite floats and string dictionary keys."""
    if value is None or isinstance(value, _JSON_SCALARS):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise SpecificationError("specification keys must be strings")
        return {key: _json_copy(item) for key, item in value.items()}
    if isinstance(value, _JSON_SEQUENCES):
        return [_json_copy(item) for item in value]
    raise SpecificationError("specification values must be finite JSON data")


def _normalized_hash(body: dict[str, Any]) -> str:
    return payload_hash({key: value for key, value in body.items()
                         if key != "specification_hash"}, "")


def specification_hash(document: Mapping[str, Any]) -> str:
    """Use the existing sorted-JSON payload hash, excluding only our own digest."""
    return _normalized_hash(_json_copy(dict(document)))


def _check_components(components: Any) -> None:
    if not isinstance(components, list) or [item.get("name") if isinstance(item, dict) else None
                                          for item in components] != list(COMPONENT_NAMES):
        raise SpecificationError("all eight components must have their exact names and order")
    for component in components:
        if component.get("status") not in {"implemented", "partial", "not-implemented"}:
            raise SpecificationError("invalid component status")
        if (component["status"] != "implemented"
                and (not isinstance(component.get("reason"), str) or not component["reason"].strip())):
            raise SpecificationError("partial and not-implemented components need a reason")
        if not isinstance(component.get("versions"), dict) or not all(
            isinstance(key, str) and isinstance(value, str) and value
            for key, value in component["versions"].items()
        ):
            raise SpecificationError("component versions must be strings read from configuration")
        if not isinstance(component.get("evidence"), list) or not component["evidence"]:
            raise SpecificationError("component evidence paths are required")
        if any(not isinstance(path, str) or not path for path in component["evidence"]):
            raise SpecificationError("component evidence paths must be nonempty strings")


def _validate_normalized_structure(body: dict[str, Any]) -> None:
    if type(body.get("schema_version")) is not int or body["schema_version"] != SPEC_SCHEMA_VERSION:
        raise SpecificationError("unknown specification schema version")
    records = body.get("records")
    if not isinstance(records, dict) or set(records) != set(RECORD_NAMES):
        raise SpecificationError("all five specification records are required")
    try:
        _check_components(records["release"]["components"])
        _check_components(records["run_start"]["components"])
        _check_components(body["active_configuration"]["components"])
        if records["run_end"]:
            _check_components(records["run_end"]["configuration"]["components"])
        declared = records["declared_changeable"]
        if declared["personas_and_model_calls"] != []:
            raise SpecificationError("personas and model calls have no change authority")
        for control in declared["operator"]:
            if not all(control.get(field) for field in ("field", "actor", "authorization", "evidence")):
                raise SpecificationError("operator controls require actor, authorization and evidence")
        pairing = body["model_pairing"]
        if set(pairing) != {"adapter", "requested", "host_reported"}:
            raise SpecificationError("requested and host-reported identities must remain separate")
        for identity in (pairing["requested"], pairing["host_reported"]):
            if not isinstance(identity, dict) or set(identity) != {"model_id", "model_version"}:
                raise SpecificationError("invalid model identity")
        for path, digest in records["release"]["governing_files"].items():
            if not isinstance(path, str) or not isinstance(digest, str) or not _HEX.fullmatch(digest):
                raise SpecificationError("governing files require SHA-256 hashes")
        if not isinstance(records["material_change_events"], list):
            raise SpecificationError("material changes must be a list")
        for event in records["material_change_events"]:
            if event.get("event_id") != event_digest({k: v for k, v in event.items() if k != "event_id"}):
                raise SpecificationError("material event identity differs")
            if not all(event.get(key) for key in ("requested_by", "authorized_by", "field")):
                raise SpecificationError("material events require requester and authorization")
            if not all(key in event for key in ("old_value", "new_value", "interval", "reversed")):
                raise SpecificationError("material events require values, interval and reversal status")
        if not body["recorder"] or body["startup_attestation"]["recorder"] != body["recorder"]:
            raise SpecificationError("startup attestation must name its recorder")
    except (KeyError, TypeError, AttributeError) as exc:
        raise SpecificationError("incomplete specification record") from exc


def validate_specification(document: Mapping[str, Any]) -> None:
    body = _json_copy(dict(document))
    _validate_normalized_structure(body)
    if body.get("specification_hash") != _normalized_hash(body):
        raise SpecificationError("specification hash does not match its contents")


@lru_cache(maxsize=32)
def _governing_files(codex_directory: str) -> dict[str, str]:
    """Release inputs are captured once per loaded codex store location.

    These files are not runtime-editable. Reuse keeps a quiet sitting boundary
    from scanning files before a crisis card. A new process reads the release
    again; custom stores hash only files they actually contain.
    """
    codex = Path(codex_directory)
    files: list[tuple[str, Path]] = []
    files.extend(("docs/codex/" + path.name, path) for path in sorted(codex.glob("*.md")))
    lock = codex / "house-block.lock.json"
    if lock.exists():
        files.append(("docs/codex/house-block.lock.json", lock))
    files.extend(("src/secondsignal/packs/" + path.name, path) for path in sorted(PACK_DIR.glob("*.json")))
    files.extend(("src/secondsignal/profiles/" + path.name, path)
                 for path in sorted(DEFAULT_PROFILE_DIR.glob("*.json")))
    for name in ("corrected_confusables.json", "reviewed_skeleton_remainder.json",
                 "crisis_words.txt", "everyday_words.txt"):
        files.append(("src/secondsignal/" + name, PACK_DIR.parent / name))
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sorted(files)}


def _transport_endpoint(adapter: ModelAdapter) -> dict[str, Any] | None:
    """Bind the transport destination without userinfo, queries or fragments.

    Paths that resemble credentials are not copied. Their digest still binds
    the chosen route without placing that credential-shaped text in a record.
    No key, environment variable or arbitrary adapter state is read.
    """
    current: Any = adapter
    seen: set[int] = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        raw = getattr(current, "url", None)
        if isinstance(raw, str) and raw:
            try:
                parsed = urlsplit(raw)
                host = safe_identifier(parsed.hostname)
                if parsed.scheme not in {"http", "https"} or host is None:
                    return None
                route = parsed.path or "/"
                decoded = unquote(route, errors="strict")
                unsafe = (len(route) > 2048 or _CREDENTIAL.search(route) or _CREDENTIAL.search(decoded)
                          or any(ord(char) < 32 or ord(char) == 127 for char in decoded))
                return {"scheme": parsed.scheme, "host": host, "port": parsed.port,
                        "path": None if unsafe else route,
                        "path_sha256": hashlib.sha256(route.encode("utf-8")).hexdigest()}
            except (ValueError, UnicodeError):
                return None
        current = getattr(current, "adapter", None)
    return None


def _static_configuration(configuration: Mapping[str, Any]) -> dict[str, Any]:
    result = _json_copy(dict(configuration))
    # H1's per-call receipt is not the configuration at sitting start. Model
    # identities are represented explicitly in the independent pairing fields.
    for key in ("prompt_sha256", "model_id", "model_version"):
        result.pop(key, None)
    return result


def _components(configuration: dict[str, Any], runtime: dict[str, Any]) -> list[dict[str, Any]]:
    versions = {name: str(configuration[key]) for name, key in
                (("harness", "harness_version"), ("policy", "policy_version"))
                if configuration.get(key) is not None}
    versions["crisis_card"] = str(CRISIS_CARD["version"])
    versions["specification_schema"] = str(SPEC_SCHEMA_VERSION)
    versions["harness_audit_schema"] = AUDIT_ROW_SCHEMA
    versions.update({"pack:" + key: str(value) for key, value in
                     configuration.get("pack_versions", {}).items() if value is not None})
    generation = configuration.get("generation", {})
    controls = configuration.get("harness_controls", {})
    values = (
        {"roster_hash": configuration.get("roster_hash")},
        {"max_turns": generation.get("max_turns"), "long_term_conversation_memory": False,
         "holds_survive_restart": False, "latch_persistence": runtime.get("latch_persistence", False)},
        {"model_tools": [], "input": "text", "output": "text"},
        {"house_block_sha256": configuration.get("house_block_sha256"),
         "presentation": configuration.get("presentation", {}), "codex_load": "first_use"},
        {"agent_code_execution": False},
        {"harness_controls": controls, "runtime_controls": runtime.get("permissions", {})},
        {"h1_configuration": configuration},
        {"generation": generation, "adapter_transport_timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
         "runtime": runtime, "durable_full_transcript": False, "interrupted_model_call_resume": False},
    )
    return [{"name": name, "status": _STATUSES[index], "versions": dict(versions),
             "evidence": list(_EVIDENCE[index]), "reason": _REASONS[index],
             "configuration": copy.deepcopy(values[index])}
            for index, name in enumerate(COMPONENT_NAMES)]


def _declared_changeable() -> dict[str, Any]:
    server, t3 = "apps/talking_table/server.py", "apps/talking_table/t3.py"
    return {"operator": [
        {"field": "host_terms", "actor": "operator", "authorization":
         "computer scope and a local operator token; update_settings validates a bounded HTTP(S) URL",
         "evidence": [server]},
        {"field": "latch_clearance", "actor": "operator", "authorization":
         "nonempty reason, current sitting revision and local operator token for a Table-owned latch; "
         "an explicitly injected caller-owned session retains the caller's clearance authority",
         "evidence": [t3]},
        {"field": "pairing_scopes", "actor": "operator and pairing client", "authorization":
         "computer scope controls phone access; a matching bounded-rate pairing code grants only phone scope",
         "evidence": [server, t3]},
        {"field": "adapter_and_model", "actor": "operator or embedding application", "authorization":
         "explicit start parameters, or validated computer-scope update_settings during the same sitting",
         "evidence": [server, "src/secondsignal_harness/__main__.py"]},
        {"field": "presentation_and_runtime_settings", "actor": "operator or embedding application",
         "authorization": "explicit harness parameters or validated computer-scope update_settings; "
         "operator-circle mode additionally requires a local operator token at the Table",
         "evidence": [server, t3, "src/secondsignal_harness/harness.py"]},
    ], "personas_and_model_calls": []}


class _Storage:
    def __init__(self, audit_path: Path | None) -> None:
        self.path = audit_path.with_name(audit_path.stem + ".specifications.jsonl") if audit_path else None
        events = audit_path.with_name(audit_path.stem + ".material-changes.jsonl") if audit_path else None
        self.events = MaterialChangeLog(events)
        self.lock = threading.RLock()
        self.committed: set[object] = set()
        self.snapshots: dict[str, dict[str, Any]] = {}
        self._validated_lines: dict[bytes, tuple[dict[str, Any], Counter[str]]] = {}
        self._verified_snapshots: dict[str, dict[str, Any]] = {}
        self._requirements: Counter[str] = Counter()
        self._loaded = False
        self._signature: Any = None
        self._event_revision: tuple[int, int] | None = None

    @staticmethod
    def _required_events(snapshot: dict[str, Any]) -> Counter[str]:
        # Validation binds each ID to all event contents. Count occurrences
        # without copying or recounting the physical event history.
        return Counter(event["event_id"] for event in snapshot["records"]["material_change_events"])

    @staticmethod
    def _merge_requirements(combined: Counter[str], required: Counter[str]) -> None:
        for event_id, count in required.items():
            if count > combined[event_id]:
                combined[event_id] = count

    def _disk_signature(self, *, stream: BinaryIO | None = None) -> Any:
        if self.path is None:
            return None
        try:
            identity = _file_identity(self.path)
            if identity is None:
                return None
            tail = _read_bytes(self.path, identity, offset=max(0, identity[2] - 96),
                               size=96, stream=stream)
            return identity, tail
        except (OSError, ValueError) as exc:
            raise SpecificationError("specification snapshot metadata could not be read") from exc

    def _sync_events(self) -> None:
        revision = id(self.events), self.events.verification_revision
        if revision != self._event_revision:
            # An internal append cannot invalidate prior backing. A reopened,
            # replaced or externally changed log must prove every known receipt.
            checked = self.events.require_events(self._requirements)
            self._event_revision = id(self.events), checked

    def read(self, digest: str) -> dict[str, Any] | None:
        with self.lock:
            self._sync_events()
            if self.path is None:
                value = self.snapshots.get(digest)
                return copy.deepcopy(value) if value is not None else None
            try:
                signature = self._disk_signature()
            except SpecificationError:
                self._loaded = False
                raise
            if self._loaded and signature == self._signature:
                value = self._verified_snapshots.get(digest)
                return copy.deepcopy(value) if value is not None else None
            self._loaded = False
            if signature is None:
                if self.snapshots or self._verified_snapshots:
                    raise SpecificationError("specification snapshot log is missing")
                self._signature, self._loaded = signature, True
                return None
            documents: dict[str, dict[str, Any]] = {}
            requirements: Counter[str] = Counter()
            try:
                raw = self.path.read_bytes()
                if raw and not raw.endswith(b"\n"):
                    raise SpecificationError("specification snapshot log has an incomplete record")
                for line in raw.splitlines():
                    cached = self._validated_lines.get(line)
                    if cached is None:
                        candidate = json.loads(line)
                        validate_specification(candidate)
                        required = self._required_events(candidate)
                        self._validated_lines[line] = candidate, required
                    else:
                        candidate, required = cached
                    self._merge_requirements(requirements, required)
                    documents[candidate["specification_hash"]] = candidate
                if (set(self.snapshots) | set(self._verified_snapshots)) - set(documents):
                    raise SpecificationError("a previously committed specification snapshot is missing")
                checked_revision = self.events.require_events(requirements)
                after = self._disk_signature()
                if signature != after:
                    raise SpecificationError("specification snapshot log changed during verification")
            except (OSError, ValueError, UnicodeError, TypeError) as exc:
                raise SpecificationError("specification snapshot log could not be verified") from exc
            self._verified_snapshots = documents
            self._requirements = requirements
            self._signature, self._loaded = after, True
            self._event_revision = id(self.events), checked_revision
            value = documents.get(digest)
            return copy.deepcopy(value) if value is not None else None

    def commit(self, snapshot: dict[str, Any], pending: list[tuple[object, dict[str, Any]]]) -> None:
        with self.lock:
            self.read("verify_existing_history")
            digest = snapshot.get("specification_hash")
            encoded = None
            already_validated = False
            if (self.path is not None and isinstance(digest, str)
                    and (digest in self.snapshots or digest in self._verified_snapshots)):
                try:
                    encoded = canonical_row(snapshot).encode("utf-8")
                except (TypeError, ValueError) as exc:
                    raise SpecificationError("specification must contain valid JSON data") from exc
                # Exact bytes preserve distinctions such as True/1 and -0.0/0.0.
                already_validated = encoded in self._validated_lines
                if (already_validated and digest in self.snapshots
                        and all(token in self.committed for token, _ in pending)):
                    return
            if not already_validated:
                validate_specification(snapshot)
            for token, event in pending:
                if token not in self.committed:
                    self.events.append(event)
                    self.committed.add(token)
            required = self._required_events(snapshot)
            checked = self.events.require_events(required)
            if self._event_revision != (id(self.events), checked):
                # Own verified appends preserve old receipts. An external
                # revision must prove both old and new backing atomically.
                combined = self._requirements.copy()
                self._merge_requirements(combined, required)
                checked = self.events.require_events(combined)
                self._event_revision = id(self.events), checked
            digest = snapshot["specification_hash"]
            if digest not in self.snapshots:
                if self.path is not None and digest not in self._verified_snapshots:
                    self._loaded = False
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    line = (encoded if encoded is not None else canonical_row(snapshot).encode("utf-8")) + b"\n"
                    before_identity = self._signature[0] if self._signature is not None else None
                    before_size = before_identity[2] if before_identity is not None else 0
                    if self._disk_signature() != self._signature:
                        raise SpecificationError("specification snapshot log changed before append")
                    with _write_handle(self.path, append=True, expected_identity=before_identity) as stream:
                        opened_identity = _stream_identity(stream)
                        start = stream.seek(0, os.SEEK_END)
                        if start != before_size:
                            raise SpecificationError("specification snapshot log changed before append")
                        stream.write(line)
                        stream.flush()
                        stream.seek(start)
                        written = stream.read(len(line) + 1)
                        after = self._disk_signature(stream=stream)
                        if (written != line or after is None
                                or after[0][:2] != opened_identity[:2]
                                or after[0][2] != start + len(line)):
                            raise SpecificationError("specification append could not be verified")
                    stored = copy.deepcopy(snapshot)
                    self._verified_snapshots[digest] = stored
                    self._validated_lines[line[:-1]] = stored, required
                    self._signature, self._loaded = after, True
                self.snapshots[digest] = copy.deepcopy(snapshot)
                self._merge_requirements(self._requirements, required)


_STORAGES: dict[str, _Storage] = {}
_STORAGE_LOCK = threading.RLock()


def _storage(audit_path: Path | None) -> _Storage:
    if audit_path is None:
        return _Storage(None)
    key = str(audit_path.resolve())
    with _STORAGE_LOCK:
        if key not in _STORAGES:
            _STORAGES[key] = _Storage(audit_path)
        return _STORAGES[key]


class HarnessSpecification:
    """Five records for one sitting, with side-effect-free staging and explicit commit."""

    def __init__(self, configuration: Mapping[str, Any], *, adapter: ModelAdapter,
                 roster: Mapping[str, AgentProfile], codexes: CodexStore,
                 runtime: Mapping[str, Any] | None = None,
                 initial_state: Mapping[str, Any] | None = None,
                 audit_path: Path | str | None = None) -> None:
        self.configuration = _static_configuration(configuration)
        self.configuration["transport_endpoint"] = _transport_endpoint(adapter)
        self._initial_endpoint = copy.deepcopy(self.configuration["transport_endpoint"])
        self.runtime = _json_copy(dict(runtime or {}))
        self.audit_path = Path(audit_path) if audit_path is not None else None
        self._storage = _storage(self.audit_path)
        self._pending: list[tuple[object, dict[str, Any]]] = []
        self._event_tokens: dict[str, object] = {}
        self._active: dict[str, dict[str, Any]] = {}
        self._last_event: str | None = None
        self._stamped_ordinal = 0
        self._closed = False
        self._observed = False
        pairing = {"adapter": safe_identifier(getattr(adapter, "name", "unknown")),
                   "requested": adapter_identity(adapter, None),
                   "host_reported": {"model_id": None, "model_version": None}}
        components = _components(self.configuration, self.runtime)
        initial = _json_copy(dict(initial_state or {}))
        recorder = {"name": "secondsignal_harness", "version": configuration.get("harness_version")}
        self._body: dict[str, Any] = {
            "schema_version": SPEC_SCHEMA_VERSION,
            "model_pairing": pairing,
            "recorder": recorder,
            "startup_attestation": {"recorder": copy.deepcopy(recorder), "initial_state": initial},
            "active_configuration": {"components": copy.deepcopy(components), "controls": {}},
            "records": {
                "release": {"components": copy.deepcopy(components),
                            "governing_files": dict(_governing_files(str(codexes.directory.resolve()))),
                            "loaded_roster_source_hashes": {name: profile.source_hash or None
                                                            for name, profile in sorted(roster.items())}},
                "declared_changeable": _declared_changeable(),
                "run_start": {"components": copy.deepcopy(components),
                              "model_pairing": copy.deepcopy(pairing), "initial_state": copy.deepcopy(initial)},
                "material_change_events": [], "run_end": {},
            },
        }

    @property
    def event_log(self) -> MaterialChangeLog:
        return self._storage.events

    @property
    def material_change_event_id(self) -> str | None:
        return self._last_event

    def fork(self) -> HarnessSpecification:
        result = copy.copy(self)
        result.configuration = copy.deepcopy(self.configuration)
        result.runtime = copy.deepcopy(self.runtime)
        result._body = copy.deepcopy(self._body)
        result._active = copy.deepcopy(self._active)
        result._event_tokens = dict(self._event_tokens)
        # Tokens identify pending writes across forks; preserve their identity.
        result._pending = [(token, copy.deepcopy(event)) for token, event in self._pending]
        return result

    def __deepcopy__(self, memo: dict[int, Any]) -> HarnessSpecification:
        result = self.fork()
        memo[id(self)] = result
        if self.audit_path is None:
            storage = _Storage(None)
            storage.snapshots = copy.deepcopy(self._storage.snapshots, memo)
            storage.committed = set(self._storage.committed)
            storage.events = copy.deepcopy(self._storage.events, memo)
            storage._requirements = self._storage._requirements.copy()
            result._storage = storage
        return result

    def new_run(self, configuration: Mapping[str, Any], *, adapter: ModelAdapter,
                roster: Mapping[str, AgentProfile], codexes: CodexStore,
                runtime: Mapping[str, Any] | None = None,
                initial_state: Mapping[str, Any] | None = None) -> HarnessSpecification:
        result = HarnessSpecification(configuration, adapter=adapter, roster=roster, codexes=codexes,
                                      runtime=runtime, initial_state=initial_state, audit_path=self.audit_path)
        result._storage = self._storage
        return result

    def _current_hash(self) -> str:
        normalized = _json_copy(self._body)
        _validate_normalized_structure(normalized)
        return _normalized_hash(normalized)

    def snapshot(self) -> dict[str, Any]:
        document = _json_copy(self._body)
        _validate_normalized_structure(document)
        document["specification_hash"] = _normalized_hash(document)
        return document

    def read_snapshot(self, digest: str) -> dict[str, Any] | None:
        return self._storage.read(digest)

    def _append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event = _json_copy(event)
        event["event_id"] = event_digest(event)
        self._body["records"]["material_change_events"].append(event)
        token = object()
        self._event_tokens[event["event_id"]] = token
        self._pending.append((token, copy.deepcopy(event)))
        return event

    def _close_interval(self, field: str, ordinal: int, *, reversed: bool = False) -> None:
        previous = self._active.pop(field, None)
        if previous is None:
            return
        self._append_event({"kind": "interval_end", "field": field,
                            "old_value": previous["old_value"], "new_value": previous["new_value"],
                            "requested_by": "recorder", "authorized_by": "successor change or sitting end",
                            "interval": {"from_turn": previous["interval"]["from_turn"],
                                         "until_turn": ordinal},
                            "reversed": reversed, "closes_event_id": previous["event_id"]})

    def record_change(self, field: str, old: Any, new: Any, *, actor: str,
                      authorization: str | Mapping[str, Any], ordinal: int) -> None:
        if self._closed:
            raise SpecificationError("a closed sitting cannot change")
        if not isinstance(field, str) or not field or not actor or not authorization:
            raise SpecificationError("material changes require a field, actor and authorization")
        if type(ordinal) is not int or ordinal < 1:
            raise SpecificationError("a material change needs a positive effective turn ordinal")
        old, new = _json_copy(old), _json_copy(new)
        if old == new:
            return
        previous = self._active.get(field)
        reversal = bool(previous is not None and previous["old_value"] == new)
        self._close_interval(field, ordinal, reversed=reversal)
        event = self._append_event({"kind": "change", "field": field,
                                    "old_value": old, "new_value": new,
                                    "requested_by": actor, "authorized_by": authorization,
                                    "interval": {"from_turn": ordinal, "until_turn": None},
                                    "reversed": False,
                                    "reverses_event_id": previous["event_id"] if reversal and previous else None})
        self._active[field] = event
        self._last_event = event["event_id"]
        self._body["active_configuration"]["controls"][field] = copy.deepcopy(new)

    def observe_model(self, reply: AdapterReply | None, *, ordinal: int) -> None:
        if reply is None:
            return
        reported = adapter_identity_adapter_reply(reply)
        current = self._body["model_pairing"]["host_reported"]
        if (self._observed or self._stamped_ordinal > 0) and reported != current:
            self.record_change("host_reported_model", current, reported, actor="adapter_response",
                               authorization="identity reported by the adapter response; evidence only",
                               ordinal=ordinal)
        self._body["model_pairing"]["host_reported"] = reported
        initial_pairing = self._body["records"]["run_start"]["model_pairing"]
        pairing = self._body["model_pairing"]
        if (not self._observed and self._stamped_ordinal == 0
                and initial_pairing["adapter"] == pairing["adapter"]
                and initial_pairing["requested"] == pairing["requested"]
                and self.configuration["transport_endpoint"] == self._initial_endpoint):
            initial_pairing["host_reported"] = copy.deepcopy(reported)
        self._observed = True

    def merge_model_observation(self, source: HarnessSpecification, *, ordinal: int) -> None:
        """Keep controls recorded during a call while adopting its host receipt.

        An old requested model cannot overwrite a newer pairing. Matching
        logical observations reuse the source write token, including after its
        commit, so this merge does not duplicate an accepted turn's event.
        """
        own, other = self._body["model_pairing"], source._body["model_pairing"]
        if (not source._observed or own["adapter"] != other["adapter"]
                or own["requested"] != other["requested"]
                or self.configuration["transport_endpoint"] != source.configuration["transport_endpoint"]):
            return
        count = len(self._pending)
        reported = other["host_reported"]
        self.observe_model(AdapterReply("", reported["model_id"] or "",
                                       model_version=reported["model_version"]), ordinal=ordinal)
        for index in range(count, len(self._pending)):
            token, event = self._pending[index]
            source_token = source._event_tokens.get(event["event_id"])
            if source_token is not None:
                self._pending[index] = (source_token, event)
                self._event_tokens[event["event_id"]] = source_token
        self._stamped_ordinal = max(self._stamped_ordinal, source._stamped_ordinal)

    def change(self, configuration: Mapping[str, Any], *, runtime: Mapping[str, Any] | None = None,
               adapter: ModelAdapter | None = None, actor: str, authorization: str | Mapping[str, Any], ordinal: int) -> None:
        incoming = _static_configuration(configuration)
        old_endpoint = self.configuration["transport_endpoint"]
        incoming["transport_endpoint"] = (_transport_endpoint(adapter) if adapter is not None else old_endpoint)
        endpoint_changed = incoming["transport_endpoint"] != old_endpoint
        incoming_runtime = self.runtime if runtime is None else _json_copy(dict(runtime))
        if incoming != self.configuration or incoming_runtime != self.runtime:
            previous = {"configuration": self.configuration, "runtime": self.runtime}
            updated = {"configuration": incoming, "runtime": incoming_runtime}
            self.record_change("component_configuration", previous, updated, actor=actor,
                               authorization=authorization, ordinal=ordinal)
            self.configuration, self.runtime = copy.deepcopy(incoming), copy.deepcopy(incoming_runtime)
            self._body["active_configuration"]["components"] = _components(self.configuration, self.runtime)
        if adapter is not None:
            pairing = self._body["model_pairing"]
            requested = {"adapter": safe_identifier(getattr(adapter, "name", "unknown")),
                         "requested": adapter_identity(adapter, None)}
            previous = {"adapter": pairing["adapter"], "requested": pairing["requested"]}
            if requested != previous or endpoint_changed:
                changed_pairing = {**copy.deepcopy(requested),
                                   "host_reported": {"model_id": None, "model_version": None}}
                self._close_interval("host_reported_model", ordinal)
                self.record_change("requested_model",
                                   {**copy.deepcopy(pairing), "transport_endpoint": old_endpoint},
                                   {**copy.deepcopy(changed_pairing),
                                    "transport_endpoint": incoming["transport_endpoint"]},
                                   actor=actor, authorization=authorization, ordinal=ordinal)
                pairing.update(changed_pairing)
                self._observed = False

    def end(self, outcome: Any, *, ordinal: int) -> None:
        if self._closed:
            return
        if type(ordinal) is not int or ordinal < 0:
            raise SpecificationError("run end needs a nonnegative final turn ordinal")
        for field in list(self._active):
            self._close_interval(field, max(ordinal + 1, self._active[field]["interval"]["from_turn"]))
        self._body["records"]["run_end"] = {
            "configuration": copy.deepcopy(self._body["active_configuration"]),
            "model_pairing": copy.deepcopy(self._body["model_pairing"]),
            "outcome": _json_copy(outcome), "final_turn_ordinal": ordinal,
        }
        self._closed = True

    def event_in_force(self, ordinal: int) -> str | None:
        """The latest material change whose half-open interval contains this turn."""
        events = self._body["records"]["material_change_events"]
        endings = {event["closes_event_id"]: event["interval"]["until_turn"]
                   for event in events if event["kind"] == "interval_end"}
        candidates = []
        for index, event in enumerate(events):
            if event["kind"] != "change" or event["interval"]["from_turn"] > ordinal:
                continue
            until = endings.get(event["event_id"], event["interval"]["until_turn"])
            if until is None or ordinal < until:
                candidates.append((event["interval"]["from_turn"], index, event["event_id"]))
        return str(max(candidates)[2]) if candidates else None

    def stamp(self, row: dict[str, Any], *, ordinal: int) -> None:
        if self._closed or type(ordinal) is not int or ordinal < 1:
            raise SpecificationError("an open sitting needs a positive turn ordinal")
        row["specification_hash"] = self._current_hash()
        row["sitting_turn_ordinal"] = ordinal
        row["material_change_event_id"] = self.event_in_force(ordinal)
        self._stamped_ordinal = max(self._stamped_ordinal, ordinal)

    def assert_row(self, row: Mapping[str, Any]) -> None:
        if row.get("specification_hash") != self._current_hash():
            raise SpecificationStampError("audit row specification hash does not match the active specification")
        if type(row.get("sitting_turn_ordinal")) is not int or row["sitting_turn_ordinal"] < 1:
            raise SpecificationStampError("audit row needs a positive sitting turn ordinal")
        if ("material_change_event_id" not in row
                or row["material_change_event_id"] != self.event_in_force(row["sitting_turn_ordinal"])):
            raise SpecificationStampError("audit row material event does not match the active specification")

    def commit(self) -> None:
        self._storage.commit(self.snapshot(), self._pending)
        self._pending = []


def adapter_identity_adapter_reply(reply: AdapterReply) -> dict[str, str | None]:
    if not getattr(reply, "model_id_reported", True):
        return {"model_id": None, "model_version": None}
    return {"model_id": safe_identifier(reply.model_id), "model_version": safe_identifier(reply.model_version)}


__all__ = ["AUDIT_ROW_SCHEMA", "COMPONENT_NAMES", "HarnessSpecification", "SPEC_SCHEMA_VERSION",
           "SpecificationError", "SpecificationStampError", "specification_hash", "validate_specification"]
