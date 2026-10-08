"""Explicit, non-secret configuration facts for each harness audit row.

The full prompt hash is SHA-256 of canonical JSON containing system text and
ordered message dictionaries, including roles. No-call turns have no prompt
hash. Unreported model versions stay null; an API protocol version is not a
model version. Metadata never introspects arbitrary adapter state or reads
environment variables. Identifier-shaped credentials and authentication
assignments are replaced by null rather than copied to the configuration.

Presentation slots follow sorted roster IDs, bound by roster_hash. Each name_form
is an index into (display_name, first plate name, second plate name), choosing the
first matching form. This records effective choices without putting character
names or IDs on a nameless gate row. It does not identify a seated character.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

from secondsignal import __version__ as policy_version
from secondsignal.lexicon import PACK_DIR, PACKS, RESOURCES
from secondsignal.profiles import AgentProfile

from .adapters import AdapterReply, Message, ModelAdapter
from .audit_log import canonical_row
from .codex import CodexStore
from .prompt import PRESENTATION_WORDS

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}")
_CREDENTIAL = re.compile(
    r"(?:^|[^a-z0-9])(?:sk|xai|gh[pousr]|github_pat|gsk|hf|xox[baprs]|api[_-]?key|access[_-]?token)"
    r"[-_:=]|(?:AKIA|ASIA)[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{20,}|"
    r"(?i:bearer|authorization|secret|password)[ :=]|"
    r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}", re.IGNORECASE,
)


def safe_identifier(value: Any) -> str | None:
    """Accept a small identifier grammar, excluding recognized credential shapes."""
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        return None
    return None if _CREDENTIAL.search(value) else value


def prompt_sha256(system: str, messages: Sequence[Message]) -> str:
    material = canonical_row({"system": system, "messages": [dict(m) for m in messages]})
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def pack_revision(raw: bytes, loaded_version: Any = None) -> int | str | None:
    """Use the version field when present, otherwise the full source-file SHA-256."""
    document = json.loads(raw)
    if "version" not in document:
        return hashlib.sha256(raw).hexdigest()
    version = document["version"] if loaded_version is None else loaded_version
    if type(version) is int:
        return version
    return safe_identifier(version)


@lru_cache(maxsize=1)
def _pack_versions() -> dict[str, int | str | None]:
    result: dict[str, int | str | None] = {}
    for path in sorted(PACK_DIR.glob("*.json")):
        raw = path.read_bytes()
        document = json.loads(raw)
        if path.name == "resources.json":
            loaded = RESOURCES
            source_hash = loaded.get("_source_hash")
            name, version = "resources", loaded.get("version")
        else:
            pack = PACKS.get(document.get("pack"))
            if pack is None:
                continue
            source_hash = pack.source_hash
            name, version = pack.id, pack.version
        if hashlib.sha256(raw).hexdigest()[:12] != source_hash:
            raise ValueError("pack file no longer matches the loaded policy pack")
        safe_name = safe_identifier(name)
        if safe_name is None:
            raise ValueError("pack name is not safe configuration metadata")
        result[safe_name] = pack_revision(raw, version)
    return result


def adapter_identity(adapter: ModelAdapter, reply: AdapterReply | None) -> dict[str, str | None]:
    if reply is not None:
        return {"model_id": safe_identifier(reply.model_id),
                "model_version": safe_identifier(reply.model_version)}
    current: Any = adapter
    seen: set[int] = set()
    for _ in range(8):
        if id(current) in seen:
            break
        seen.add(id(current))
        model = getattr(current, "model_id", None)
        if model is None:
            model = getattr(current, "model", None)
        if model is not None:
            return {"model_id": safe_identifier(model),
                    "model_version": safe_identifier(getattr(current, "model_version", None))}
        current = getattr(current, "adapter", None)
        if current is None:
            break
    return {"model_id": None, "model_version": None}


def configuration(
    *, adapter: ModelAdapter, reply: AdapterReply | None, prompt_hash: str | None,
    record: Mapping[str, Any], roster: Mapping[str, AgentProfile], codexes: CodexStore,
    presentation: Mapping[str, str], chosen_names: Mapping[str, str],
    max_turns: int, max_tokens: int, retries: int,
) -> dict[str, Any]:
    from . import __version__ as harness_version

    lock_path = codexes.directory / "house-block.lock.json"
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        # CodexStore also accepts caller-supplied directories without a lock.
        # Null is truthful; borrowing the bundled lock would attest the wrong text.
        house_hash = None
    else:
        house_hash = lock.get("sha256")
        if not isinstance(house_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", house_hash):
            raise ValueError("house-block lock has no SHA-256")
    settings = []
    for agent_id, profile in sorted(roster.items()):
        setting = presentation.get(agent_id, "as_written")
        if setting not in PRESENTATION_WORDS:
            setting = "as_written"
        name, pronoun = profile.name_for(setting, chosen_names.get(agent_id))
        forms = (profile.display_name, profile.plate[0][0], profile.plate[1][0])
        settings.append({"setting": setting, "name_form": forms.index(name),
                         "pronoun": pronoun if pronoun in {"she", "he", "they", ""} else None})
    return {
        **adapter_identity(adapter, reply),
        "prompt_sha256": prompt_hash,
        "harness_version": safe_identifier(harness_version),
        "policy_version": safe_identifier(policy_version),
        "pack_versions": dict(_pack_versions()),
        "roster_hash": safe_identifier(record.get("roster_hash")),
        "house_block_sha256": house_hash,
        "presentation": {"order": "sorted_roster_ids", "slots": settings},
        "generation": {"max_turns": max_turns, "max_tokens": max_tokens, "retries": retries},
    }
