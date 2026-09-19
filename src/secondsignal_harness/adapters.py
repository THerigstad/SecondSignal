"""Model adapters: text in, text out, nothing else (ADR-0029 (Proposed), rules 4 and 9).

An adapter receives a system text, a bounded list of messages and a token
ceiling, and returns one reply with the model identifier the vendor reported.
It has no tools, no memory and no way to reach the policy layer. The real
adapters (Anthropic's Messages API; OpenAI's, xAI's, Google's Gemini and any
other host of the chat-completions dialect, by address) use the standard
library's HTTP client
so the distribution keeps its zero-dependency promise; keys come from the
environment and are never logged, never written to a row and never returned.

Every real adapter takes a ``transport`` callable so tests can stand in for
the network: ``transport(url, headers, body_bytes) -> (status, response_bytes)``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

Message = dict[str, str]  # {"role": "user" | "assistant", "content": str}
Transport = Callable[[str, dict[str, str], bytes], tuple[int, bytes]]

DEFAULT_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class AdapterReply:
    """One reply. ``model_id`` is what the vendor said answered, not what was asked for."""

    text: str
    model_id: str
    usage: dict[str, int] = field(default_factory=dict)


class AdapterError(RuntimeError):
    """The adapter could not produce a reply. The message never carries a key."""


class ModelAdapter(Protocol):
    """The whole surface a model has: text in, text out."""

    name: str

    def complete(
        self, system: str, messages: Sequence[Message], *, max_tokens: int
    ) -> AdapterReply: ...


@dataclass
class FakeAdapter:
    """A scripted adapter for tests.

    ``script`` is either a list of replies consumed in order (the last one
    repeats), or a callable ``(system, messages) -> str``. An item that is an
    exception instance is raised instead of returned. Every call is recorded
    in ``calls`` so a test can prove the adapter was, or was not, called.
    """

    script: Sequence[str | BaseException] | Callable[[str, Sequence[Message]], str] = ("Okay.",)
    name: str = "fake"
    model_id: str = "fake-1"
    calls: list[dict[str, Any]] = field(default_factory=list)

    def complete(
        self, system: str, messages: Sequence[Message], *, max_tokens: int
    ) -> AdapterReply:
        self.calls.append(
            {"system": system, "messages": [dict(m) for m in messages], "max_tokens": max_tokens}
        )
        if callable(self.script):
            return AdapterReply(text=self.script(system, messages), model_id=self.model_id)
        index = min(len(self.calls) - 1, len(self.script) - 1)
        item = self.script[index]
        if isinstance(item, BaseException):
            raise item
        return AdapterReply(text=str(item), model_id=self.model_id)


def _urllib_transport(url: str, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as error:
        return int(error.code), error.read()
    except urllib.error.URLError as error:
        raise AdapterError(f"network error: {error.reason}") from None


def _key_from_env(variable: str) -> str:
    key = os.environ.get(variable, "")
    if not key:
        raise AdapterError(f"no key in the environment variable {variable}")
    return key


def _parse_json(raw: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AdapterError("the vendor returned something that is not JSON") from None
    if not isinstance(parsed, dict):
        raise AdapterError("the vendor returned JSON that is not an object")
    return parsed


class AnthropicAdapter:
    """The Messages API over the standard library. Key: ``ANTHROPIC_API_KEY``."""

    name = "anthropic"
    url = "https://api.anthropic.com/v1/messages"
    api_version = "2023-06-01"
    key_variable = "ANTHROPIC_API_KEY"

    def __init__(self, model: str, *, transport: Transport | None = None) -> None:
        if not model:
            raise ValueError("a model identifier is required; there is no default (ADR-0029 (Proposed), rule 9)")
        self.model = model
        self._transport = transport or _urllib_transport

    def complete(
        self, system: str, messages: Sequence[Message], *, max_tokens: int
    ) -> AdapterReply:
        headers = {
            "content-type": "application/json",
            "x-api-key": _key_from_env(self.key_variable),
            "anthropic-version": self.api_version,
        }
        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": int(max_tokens),
                "system": system,
                "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            }
        ).encode("utf-8")
        status, raw = self._transport(self.url, headers, body)
        parsed = _parse_json(raw)
        if status != 200:
            kind = str((parsed.get("error") or {}).get("type") or status)
            raise AdapterError(f"the vendor refused the call ({kind})")
        blocks = parsed.get("content") or []
        text = "".join(str(b.get("text", "")) for b in blocks if isinstance(b, dict))
        usage = {k: int(v) for k, v in (parsed.get("usage") or {}).items() if isinstance(v, int)}
        return AdapterReply(text=text, model_id=str(parsed.get("model") or self.model), usage=usage)


class OpenAICompatibleAdapter:
    """Any host that speaks the chat-completions dialect, by address.

    OpenAI's own endpoint, xAI's (Grok), Google's compatibility endpoint for
    Gemini, Meta's Llama API and the services that host Meta's models all
    take the same request shape, so one adapter serves them with a different
    address, key variable and name. Meta is reached by address rather than
    by a preset here because its published address has moved at least once;
    the operator takes it from Meta's own page on the day. Every preset's
    field names are to be confirmed against the vendor's current reference
    with a live key before that adapter is considered done.
    """

    name = "openai-compatible"
    url = ""
    key_variable = ""
    # The token-ceiling field. ``max_tokens`` is the field every host of the
    # dialect accepts; OpenAI's own endpoint now prefers ``max_completion_tokens``.
    token_field = "max_tokens"

    def __init__(
        self,
        model: str,
        *,
        url: str | None = None,
        key_variable: str | None = None,
        name: str | None = None,
        token_field: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        if not model:
            raise ValueError("a model identifier is required; there is no default (ADR-0029 (Proposed), rule 9)")
        self.model = model
        if url is not None:
            self.url = url
        if key_variable is not None:
            self.key_variable = key_variable
        if name is not None:
            self.name = name
        if token_field is not None:
            self.token_field = token_field
        if not self.url or not self.key_variable:
            raise ValueError("an OpenAI-compatible adapter needs a url and a key variable")
        self._transport = transport or _urllib_transport

    def complete(
        self, system: str, messages: Sequence[Message], *, max_tokens: int
    ) -> AdapterReply:
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {_key_from_env(self.key_variable)}",
        }
        body = json.dumps(
            {
                "model": self.model,
                self.token_field: int(max_tokens),
                "messages": [{"role": "system", "content": system}]
                + [{"role": m["role"], "content": m["content"]} for m in messages],
            }
        ).encode("utf-8")
        status, raw = self._transport(self.url, headers, body)
        parsed = _parse_json(raw)
        if status != 200:
            kind = str((parsed.get("error") or {}).get("type") or status)
            raise AdapterError(f"the vendor refused the call ({kind})")
        choices = parsed.get("choices") or []
        text = ""
        if choices and isinstance(choices[0], dict):
            text = str(((choices[0].get("message") or {}).get("content")) or "")
        usage = {k: int(v) for k, v in (parsed.get("usage") or {}).items() if isinstance(v, int)}
        return AdapterReply(text=text, model_id=str(parsed.get("model") or self.model), usage=usage)


class OpenAIAdapter(OpenAICompatibleAdapter):
    """OpenAI's chat completions endpoint. Key: ``OPENAI_API_KEY``."""

    name = "openai"
    url = "https://api.openai.com/v1/chat/completions"
    key_variable = "OPENAI_API_KEY"
    token_field = "max_completion_tokens"


class XAIAdapter(OpenAICompatibleAdapter):
    """xAI's (Grok) chat completions endpoint, the same dialect. Key: ``XAI_API_KEY``."""

    name = "xai"
    url = "https://api.x.ai/v1/chat/completions"
    key_variable = "XAI_API_KEY"


class GeminiAdapter(OpenAICompatibleAdapter):
    """Google's OpenAI-compatible endpoint for the Gemini API, which its own
    documentation calls beta and says silently ignores fields it does not
    list. Key: ``GEMINI_API_KEY``."""

    name = "gemini"
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    key_variable = "GEMINI_API_KEY"


__all__ = [
    "AdapterError",
    "AdapterReply",
    "AnthropicAdapter",
    "FakeAdapter",
    "GeminiAdapter",
    "Message",
    "ModelAdapter",
    "OpenAIAdapter",
    "OpenAICompatibleAdapter",
    "Transport",
    "XAIAdapter",
]
