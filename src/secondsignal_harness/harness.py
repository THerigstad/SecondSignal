"""The turn: policy decides, one model speaks if seated, the house composes, J.R. judges, a row is written, then release or withhold (ADR-0029 (Proposed)).

``Harness.speak(text)`` is the whole request path. Read it top to bottom: the
policy layer's ``route`` is called first and its record is the only input the
rest of the function takes; the adapter is reached only inside the seated
branch; the audit row is written before anything is released; the reply is a
string that is composed, hashed, judged and returned, and nothing in it is
executed, parsed for commands or written to any state the policy layer owns.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from secondsignal.jr import AuditRequest, audit, payload_hash
from secondsignal.profiles import AgentProfile
from secondsignal.router import route
from secondsignal.safety import HOUSE_LINES_EN, SessionState

from .adapters import AdapterError, AdapterReply, Message, ModelAdapter
from .audit_log import AuditLog
from .codex import CodexStore
from .lines import HARNESS_LINES_EN
from .prompt import ChosenNames, Presentation, build_prompt, build_turn_block
from .view import audit_view

FAILURE_LINE: str = HOUSE_LINES_EN["failure"]
HOUSE_PREFIX = "[the house] "

RELEASE_GATE = "gate"
RELEASE_UNRESOLVED = "unresolved"
RELEASE_SHIP = "ship"
RELEASE_OPERATOR_CIRCLE = "operator_circle"
RELEASE_WITHHELD = "withheld"
RELEASE_FAILURE = "failure"


@dataclass(frozen=True)
class Turn:
    """What one call to ``speak`` produced. ``text`` is the only thing a person sees."""

    text: str
    outcome: str
    action: str
    agent_id: str | None
    released: bool
    release_reason: str
    persona_text: str | None
    house_lines: tuple[str, ...]
    verdict: dict[str, Any] | None
    row_id: str
    adapter_calls: int
    decision: dict[str, Any]
    notice: str | None = None


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Harness:
    """One session of the voice. Build one per conversation."""

    def __init__(
        self,
        roster: Mapping[str, AgentProfile],
        adapter: ModelAdapter,
        codexes: CodexStore,
        *,
        audit_log: AuditLog | None = None,
        session: SessionState | None = None,
        locale: str | None = None,
        presentation: Presentation | None = None,
        chosen_names: ChosenNames | None = None,
        operator_circle: bool = False,
        max_turns: int = 12,
        max_tokens: int = 600,
        retries: int = 1,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.roster = dict(roster)
        self.adapter = adapter
        self.codexes = codexes
        self.audit_log = audit_log if audit_log is not None else AuditLog()
        self.session = session if session is not None else SessionState(locale=locale)
        self.presentation = dict(presentation or {})
        self.chosen_names = dict(chosen_names or {})
        self.operator_circle = bool(operator_circle)
        self.max_turns = int(max_turns)
        self.max_tokens = int(max_tokens)
        self.retries = max(0, int(retries))
        self.clock = clock
        self.transcript: list[Message] = []
        self.turns: list[Turn] = []

    # ------------------------------------------------------------------ helpers

    def _row(self, user_text: str, **fields: Any) -> str:
        """One row per turn. It carries the person's words, because a log the
        operator cannot read the conversation from is not an audit log."""
        row: dict[str, Any] = {
            "schema": "secondsignal_harness.audit_row.v1",
            "at": float(self.clock()),
            "turn_index": int(self.session.turn_count),
            "operator_circle": self.operator_circle,
            "adapter": getattr(self.adapter, "name", "unknown"),
            "user_text": user_text,
        }
        row.update(fields)
        return self.audit_log.append(row)

    def _remember(self, text: str, *, spoken_by_house: bool) -> None:
        content = (HOUSE_PREFIX + text) if spoken_by_house else text
        self.transcript.append({"role": "assistant", "content": content})

    def _complete(self, system: str, messages: list[Message]) -> tuple[AdapterReply | None, int, str]:
        """Call the adapter, at most ``1 + retries`` times. Returns (reply, calls, error)."""
        calls = 0
        error = ""
        for _ in range(1 + self.retries):
            calls += 1
            try:
                reply = self.adapter.complete(system, messages, max_tokens=self.max_tokens)
            except AdapterError as exc:
                error = f"adapter error: {exc}"
                continue
            except Exception as exc:  # a vendor library must never take the house down
                error = f"adapter raised {type(exc).__name__}"
                continue
            if reply.text.strip():
                return reply, calls, ""
            error = "adapter returned an empty reply"
        return None, calls, error

    # -------------------------------------------------------------------- speak

    def speak(self, text: str) -> Turn:
        decision = route(text, self.roster, session=self.session)
        record: dict[str, Any] = decision.to_dict()
        raw_safety = record.get("safety")
        safety: dict[str, Any] = dict(raw_safety) if isinstance(raw_safety, dict) else {}
        action = str(safety.get("action") or "")
        outcome = str(record.get("outcome") or "")
        agent_id = record.get("agent_id")
        house_lines = tuple(str(d) for d in (safety.get("disclosures") or ()))
        first_turn = self.session.turn_count == 1
        notice = HARNESS_LINES_EN["operator_circle"] if (self.operator_circle and first_turn) else None

        self.transcript.append({"role": "user", "content": text})

        # 1. The gate fired: the card goes out verbatim; no model; the row says so.
        if action == "HUMAN_ESCALATION":
            out = "\n".join(house_lines)
            row_id = self._row(
                text, kind="gate", outcome=outcome, action=action, agent_id=None,
                house_lines=list(house_lines), released=False, release_reason=RELEASE_GATE,
                decision=_json_safe(record),
            )
            self._remember(out, spoken_by_house=True)
            turn = Turn(
                text=out, outcome=outcome, action=action, agent_id=None, released=False,
                release_reason=RELEASE_GATE, persona_text=None, house_lines=house_lines,
                verdict=None, row_id=row_id, adapter_calls=0, decision=record, notice=notice,
            )
            self.turns.append(turn)
            return turn

        # 2. Nobody seated: the house asks for one more sentence; no model.
        if not isinstance(agent_id, str) or not agent_id:
            out = "\n".join([*house_lines, HARNESS_LINES_EN["ask"]])
            row_id = self._row(
                text, kind="unresolved", outcome=outcome, action=action, agent_id=None,
                house_lines=list(house_lines), released=False,
                release_reason=RELEASE_UNRESOLVED, decision=_json_safe(record),
            )
            self._remember(out, spoken_by_house=True)
            turn = Turn(
                text=out, outcome=outcome, action=action, agent_id=None, released=False,
                release_reason=RELEASE_UNRESOLVED, persona_text=None, house_lines=house_lines,
                verdict=None, row_id=row_id, adapter_calls=0, decision=record, notice=notice,
            )
            self.turns.append(turn)
            return turn

        # 3. Seated: prompt, one model, compose, audit, row, release or withhold.
        system_text = self.codexes.system_text(agent_id)
        turn_block = build_turn_block(
            record, roster=self.roster, presentation=self.presentation,
            chosen_names=self.chosen_names, locale=self.session.locale,
        )
        system, messages = build_prompt(system_text, turn_block, self.transcript, max_turns=self.max_turns)
        prompt_digest = _digest(system + "\n".join(m["content"] for m in messages))
        codex_digest = self.codexes.digest(agent_id)

        reply, calls, error = self._complete(system, messages)
        if reply is None:
            out = "\n".join([*house_lines, FAILURE_LINE])
            row_id = self._row(
                text, kind="failure", outcome=outcome, action=action, agent_id=agent_id,
                house_lines=list(house_lines), released=False, release_reason=RELEASE_FAILURE,
                error=error, adapter_calls=calls, prompt_digest=prompt_digest,
                codex_digest=codex_digest, decision=_json_safe(record),
            )
            self._remember(out, spoken_by_house=True)
            turn = Turn(
                text=out, outcome=outcome, action=action, agent_id=agent_id, released=False,
                release_reason=RELEASE_FAILURE, persona_text=None, house_lines=house_lines,
                verdict=None, row_id=row_id, adapter_calls=calls, decision=record, notice=notice,
            )
            self.turns.append(turn)
            return turn

        persona_text = reply.text.strip()
        composed = persona_text + ("\n\n" + "\n".join(house_lines) if house_lines else "")
        view = audit_view(record, self.session)
        bound = payload_hash(view, composed)
        verdict = audit(
            AuditRequest(
                decision=view, reply=composed, payload_hash=bound,
                tools=("append_audit_row",), rubric_locked=False, human_token_valid=False,
            )
        )
        released, reason = self._release(verdict.status, verdict.layers.as_dict(), verdict.risk_class)
        out = composed if released else ("\n".join(house_lines) if house_lines else FAILURE_LINE)

        row_id = self._row(
            text, kind="seated", outcome=outcome, action=action, agent_id=agent_id,
            model_id=reply.model_id, usage=dict(reply.usage), adapter_calls=calls,
            prompt_digest=prompt_digest, codex_digest=codex_digest,
            persona_text=persona_text, house_lines=list(house_lines), composed=composed,
            bound_hash=bound, verdict=verdict.as_dict(), released=released,
            release_reason=reason, decision=_json_safe(record),
        )
        self._remember(out, spoken_by_house=not released)
        turn = Turn(
            text=out, outcome=outcome, action=action, agent_id=agent_id, released=released,
            release_reason=reason, persona_text=persona_text, house_lines=house_lines,
            verdict=verdict.as_dict(), row_id=row_id, adapter_calls=calls, decision=record,
            notice=notice,
        )
        self.turns.append(turn)
        return turn

    def _release(self, status: str, layers: Mapping[str, str], risk_class: str) -> tuple[bool, str]:
        """ADR-0029 (Proposed) rule 6 and rule 7, and nothing else."""
        if status == "SHIP":
            return True, RELEASE_SHIP
        if (
            status == "WITHHOLD"
            and self.operator_circle
            and risk_class == "normal"
            and layers.get("logical") == "PASS"
            and layers.get("semantic") == "PASS"
            and layers.get("ethical") == "PASS"
            and layers.get("cultural") == "INCONCLUSIVE"
        ):
            return True, RELEASE_OPERATOR_CIRCLE
        return False, RELEASE_WITHHELD


def _json_safe(value: Any) -> Any:
    """The decision record with nothing but JSON-native values, so a row never fails to write."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        if isinstance(value, (set, frozenset)):
            items = sorted(items, key=repr)
        return [_json_safe(v) for v in items]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "name"):
        return str(value.name)
    return str(value)


__all__ = [
    "FAILURE_LINE",
    "HARNESS_LINES_EN",
    "HOUSE_PREFIX",
    "Harness",
    "RELEASE_FAILURE",
    "RELEASE_GATE",
    "RELEASE_OPERATOR_CIRCLE",
    "RELEASE_SHIP",
    "RELEASE_UNRESOLVED",
    "RELEASE_WITHHELD",
    "Turn",
]
