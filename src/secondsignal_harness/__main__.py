"""Talk to the house from a terminal.

    python -m secondsignal_harness --adapter fake --model fake-1
    python -m secondsignal_harness --adapter anthropic --model <model id> --locale US --operator-circle
    python -m secondsignal_harness --adapter openai --model <model id> --session examples/escalation.txt
    python -m secondsignal_harness --adapter xai --model <model id> --locale US --operator-circle
    python -m secondsignal_harness --adapter gemini --model <model id> --locale US --operator-circle
    python -m secondsignal_harness --adapter compatible --url <chat-completions address> --key-variable MY_KEY --model <model id>

Keys come from the environment (``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``,
``XAI_API_KEY``, ``GEMINI_API_KEY``, or the variable named for a compatible
host such as one serving Meta's models) and are never printed. Every turn writes an audit row; ``--audit-log`` names
the file (default: ``secondsignal-audit.jsonl`` in the working directory).
The fake adapter answers "Okay." to everything and exists so the wiring can
be watched without a key.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

from secondsignal.profiles import DEFAULT_PROFILE_DIR, load_roster

from .adapters import (
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
from .harness import Harness
from .prompt import PRESENTATION_WORDS


def _adapter(name: str, model: str, *, url: str | None, key_variable: str | None) -> ModelAdapter:
    if name == "fake":
        return FakeAdapter(name="fake", model_id=model or "fake-1")
    if name == "anthropic":
        return AnthropicAdapter(model)
    if name == "openai":
        return OpenAIAdapter(model)
    if name == "xai":
        return XAIAdapter(model)
    if name == "gemini":
        return GeminiAdapter(model)
    if name == "compatible":
        if not url or not key_variable:
            raise SystemExit("--adapter compatible needs --url and --key-variable")
        return OpenAICompatibleAdapter(model, url=url, key_variable=key_variable, name="compatible")
    raise SystemExit(f"unknown adapter {name!r}")


def _presentation(pairs: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--present takes id=setting, got {pair!r}")
        agent_id, setting = pair.split("=", 1)
        if setting not in PRESENTATION_WORDS:
            raise SystemExit(f"unknown presentation {setting!r}; one of {', '.join(PRESENTATION_WORDS)}")
        out[agent_id.strip()] = setting.strip()
    return out


def _run(harness: Harness, lines: Iterable[str], *, trace: bool) -> int:
    for raw in lines:
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        turn = harness.speak(text)
        if turn.notice:
            print(f"[notice] {turn.notice}")
        speaker = (
            harness.roster[turn.agent_id].display_name if (turn.released and turn.agent_id) else "the house"
        )
        print(f"[{speaker}] {turn.text}")
        if trace:
            verdict = (turn.verdict or {}).get("composed", "-")
            print(f"  (outcome {turn.outcome}; action {turn.action}; release {turn.release_reason}; "
                  f"audit {verdict}; row {turn.row_id[:12]})")
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="secondsignal_harness", description="Talk to the house.")
    parser.add_argument("--adapter", choices=("fake", "anthropic", "openai", "xai", "gemini", "compatible"), required=True)
    parser.add_argument("--model", default="", help="The model identifier. Required for a real adapter.")
    parser.add_argument("--url", default=None, help="For --adapter compatible: the chat-completions address of the host.")
    parser.add_argument("--key-variable", default=None, help="For --adapter compatible: the environment variable holding the key.")
    parser.add_argument("--locale", default=None, help="Declared locale for crisis resources, e.g. US.")
    parser.add_argument("--operator-circle", action="store_true", help="ADR-0029 (Proposed) rule 7. Not for strangers.")
    parser.add_argument("--present", action="append", default=[], metavar="ID=SETTING",
                        help="Presentation per persona: as_written, women, men or neither.")
    parser.add_argument("--audit-log", default="secondsignal-audit.jsonl", metavar="FILE")
    parser.add_argument("--codex-dir", default=None, metavar="DIR")
    parser.add_argument("--profiles", default=str(DEFAULT_PROFILE_DIR), metavar="DIR")
    parser.add_argument("--session", default=None, metavar="FILE", help="Turns from a file, one per line; '-' for stdin.")
    parser.add_argument("--max-turns", type=int, default=12)
    parser.add_argument("--max-tokens", type=int, default=600)
    parser.add_argument("--trace", action="store_true", help="Print the decision and the verdict after each turn.")
    args = parser.parse_args(argv)

    if args.adapter != "fake" and not args.model:
        parser.error("--model is required for a real adapter (ADR-0029 (Proposed), rule 9)")

    harness = Harness(
        load_roster(Path(args.profiles)),
        _adapter(args.adapter, args.model, url=args.url, key_variable=args.key_variable),
        CodexStore(args.codex_dir),
        audit_log=AuditLog(args.audit_log),
        locale=args.locale,
        presentation=_presentation(args.present),
        operator_circle=args.operator_circle,
        max_turns=args.max_turns,
        max_tokens=args.max_tokens,
    )

    if args.session == "-":
        return _run(harness, sys.stdin, trace=args.trace)
    if args.session:
        with open(args.session, encoding="utf-8") as source:
            return _run(harness, source, trace=args.trace)

    print("Talk to the house. Empty line to leave.")
    try:
        while True:
            text = input("> ").strip()
            if not text:
                return 0
            _run(harness, [text], trace=args.trace)
    except (EOFError, KeyboardInterrupt):
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
