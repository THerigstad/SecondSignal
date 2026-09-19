"""SecondSignal harness: the voice behind the policy layer (ADR-0029 (Proposed)).

The policy layer (``secondsignal``) decides which persona may answer, whether
anyone should, and which fixed lines are attached. This package is the part
that speaks: it takes one decision record, calls exactly one model adapter for
exactly one reply when, and only when, the record seats a persona, composes
the reply with the house lines the record attached, audits the composed text
through ``secondsignal.jr.audit``, writes the audit row, and releases or
withholds by the rule in ADR-0029 (Proposed).

Direction of dependency: this package imports ``secondsignal``. Nothing in
``secondsignal`` imports this package; ``tests/test_harness_contract.py``
holds that line.
"""

from .adapters import (
    AdapterReply,
    AnthropicAdapter,
    FakeAdapter,
    GeminiAdapter,
    ModelAdapter,
    OpenAIAdapter,
    OpenAICompatibleAdapter,
    XAIAdapter,
)
from .audit_log import AuditLog
from .codex import CodexStore
from .harness import HARNESS_LINES_EN, Harness, Turn
from .prompt import build_prompt, build_turn_block
from .view import audit_view

__version__ = "0.0.1"

__all__ = [
    "AdapterReply",
    "AnthropicAdapter",
    "AuditLog",
    "CodexStore",
    "FakeAdapter",
    "GeminiAdapter",
    "HARNESS_LINES_EN",
    "Harness",
    "ModelAdapter",
    "OpenAIAdapter",
    "OpenAICompatibleAdapter",
    "Turn",
    "XAIAdapter",
    "audit_view",
    "build_prompt",
    "build_turn_block",
    "__version__",
]
