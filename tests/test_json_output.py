"""Machine-readable routing decisions and the compact JSON CLI."""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from secondsignal import load_roster, route

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def roster():
    return load_roster()


def _run_cli(*args: str) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    source_dir = str(ROOT / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (source_dir, env.get("PYTHONPATH", "")) if part
    )
    return subprocess.run(
        [sys.executable, "-m", "secondsignal", *args],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _assert_string_keys(value: object) -> None:
    if isinstance(value, dict):
        assert all(isinstance(key, str) for key in value)
        for nested in value.values():
            _assert_string_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_string_keys(nested)


def test_decision_dict_round_trips_through_standard_json(roster) -> None:
    decision = route("help me plan the launch", roster)
    payload = cast(dict[str, Any], decision.to_dict())
    assert json.loads(json.dumps(payload)) == payload


def test_every_key_in_a_decision_dict_is_a_string(roster) -> None:
    payload = route("this deadline is killing me; help me plan the launch", roster).to_dict()
    _assert_string_keys(payload)


def test_decision_dict_starts_at_schema_version_one(roster) -> None:
    assert route("hello", roster).to_dict()["schema_version"] == 1


def test_decision_dict_explicitly_covers_every_stored_field(roster) -> None:
    decision = route("this deadline is killing me; help me plan the launch", roster)
    payload = cast(dict[str, Any], decision.to_dict())

    assert {field.name for field in dataclasses.fields(decision)} <= payload.keys()
    assert {field.name for field in dataclasses.fields(decision.signals)} <= payload["signals"].keys()
    assert {field.name for field in dataclasses.fields(decision.safety)} <= payload["safety"].keys()
    assert {field.name for field in dataclasses.fields(decision.ranked[0])} <= payload["ranked"][0].keys()
    assert {field.name for field in dataclasses.fields(decision.safety.masked_spans[0])} <= (
        payload["safety"]["masked_spans"][0].keys()
    )
    escalated = route("I want to die", roster)
    escalated_payload = cast(dict[str, Any], escalated.to_dict())
    assert {field.name for field in dataclasses.fields(escalated.safety.hit_spans[0])} <= (
        escalated_payload["safety"]["hit_spans"][0].keys()
    )
    assert payload["outcome"] == decision.outcome.name
    assert payload["safety"]["action"] == decision.safety.action.name
    assert payload["explain"] == decision.explain()


@pytest.mark.parametrize(
    "text,expected_outcome,expected_action",
    [
        ("help me plan the launch", "ROUTED", "PROCEED"),
        ("I want to die", "PREEMPTED", "HUMAN_ESCALATION"),
        ("hello", "UNRESOLVED", "PROCEED"),
    ],
)
def test_json_cli_emits_one_parseable_object_for_each_outcome(
    text: str,
    expected_outcome: str,
    expected_action: str,
) -> None:
    result = _run_cli("--json", text)
    assert result.returncode == 0, result.stderr.decode()
    assert result.stderr == b""
    assert result.stdout.count(b"\n") == 1

    payload = json.loads(result.stdout)
    assert payload["outcome"] == expected_outcome
    assert payload["safety"]["action"] == expected_action
    assert result.stdout == (
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        + os.linesep.encode()
    )


def test_json_session_emits_one_object_per_nonblank_routed_line(tmp_path: Path) -> None:
    session_file = tmp_path / "session.txt"
    session_file.write_text(
        "help me plan the launch\n\n# a comment, not a turn\nI want to die\n",
        encoding="utf-8",
    )

    result = _run_cli("--json", "--session", str(session_file))
    assert result.returncode == 0, result.stderr.decode()
    assert result.stderr == b""
    lines = result.stdout.splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["outcome"] for line in lines] == ["ROUTED", "PREEMPTED"]


def test_json_cli_routes_direct_text_that_starts_with_a_comment_marker() -> None:
    result = _run_cli("--json", "# synthetic turn")
    assert result.returncode == 0, result.stderr.decode()
    assert len(result.stdout.splitlines()) == 1
    assert json.loads(result.stdout)["outcome"] == "UNRESOLVED"


def test_json_cli_is_byte_identical_across_processes() -> None:
    first = _run_cli("--json", "help me plan the launch")
    second = _run_cli("--json", "help me plan the launch")
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout
