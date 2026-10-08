"""H1: the same output checkpoint for every harness caller."""
from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path

import pytest
import test_t2_table as t2_tests
import test_talking_table as table_tests
from test_harness_contract import GRIEF_REPLY

from apps.talking_table import server
from secondsignal import load_roster
from secondsignal.safety import HOUSE_LINES_EN
from secondsignal_harness import CodexStore, FakeAdapter, Harness
from secondsignal_harness import __main__ as cli
from secondsignal_harness import release_checks as checks
from secondsignal_harness.lines import HARNESS_LINES_EN

ROOT = Path(__file__).resolve().parents[1]


def _literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int)):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_literal(item) for item in node.elts]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _literal(node.left) * _literal(node.right)
    raise AssertionError(f"fixture expression needs review: {type(node).__name__}")


def _helper_fixtures():
    source = ast.parse(inspect.getsource(table_tests.assert_model_outputs_are_guarded))
    return [item for node in ast.walk(source) if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id in {"payloads", "normal_replies"}
                    for target in node.targets)
            for item in _literal(node.value)]


def _existing_guard_fixtures():
    payloads = _helper_fixtures()
    for name in (
        "test_grok_round4_seven_leftovers_are_rejected",
        "test_grok_round4_keeps_round3_claims_rejected",
        "test_grok_round4_controls_keep_original_text",
        "test_grok_round4_house_claim_families_are_rejected",
        "test_grok_round4_schemes_and_normalized_claims_are_rejected",
        "test_grok_round4_scheme_whitespace_controls_are_released",
    ):
        for mark in getattr(table_tests, name).pytestmark:
            if mark.name == "parametrize" and mark.args[0] == "payload":
                payloads.extend(mark.args[1])
    for mark in t2_tests.test_t2_fixed_house_copy_cannot_be_released_as_model_text.pytestmark:
        if mark.name == "parametrize" and mark.args[0] == "key,values":
            payloads.extend(HARNESS_LINES_EN[key].format(**values) for key, values in mark.args[1])
    return payloads


def test_h1_port_matches_the_table_on_every_existing_guard_fixture():
    """All existing role, handoff, label, Unicode, template and URL fixtures keep Table verdicts."""
    payloads = _existing_guard_fixtures()
    assert len(payloads) == 97
    for payload in payloads:
        assert checks._reply_surface(payload) == server._reply_surface(payload)
        assert checks._reply_words(payload) == server._reply_words(payload)
        assert checks._reserved_reply_voice(payload) == server._reserved_reply_voice(payload)
        assert checks.unsafe_url_scheme(payload) == bool(
            re.search(r"(?:javascript|vbscript|data):\S", server._reply_surface(payload))
        )


@pytest.mark.parametrize("through_cli", [False, True])
def test_h1_standalone_and_command_line_withhold_card_imitation(through_cli, capsys):
    """The standalone turn and real CLI turn path both withhold an existing forged-card fixture."""
    payload = next(p for p in _helper_fixtures() if p.startswith("CRISIS CARD:"))
    harness = Harness(load_roster(), FakeAdapter(script=(payload,)), CodexStore(ROOT / "docs/codex"),
                      operator_circle=True)
    if through_cli:
        # _run is the CLI's shared session/stdin/interactive turn path.
        assert cli._run(harness, [table_tests.PROMPT], trace=True) == 0
        assert payload not in capsys.readouterr().out
        turn = harness.turns[-1]
    else:
        turn = harness.speak(table_tests.PROMPT)
    assert not turn.released and payload not in turn.text
    assert "reserved_reply_voice" in turn.release_reason
    row = harness.audit_log.rows()[-1]
    assert row["release_checks"]["reserved_reply_voice"] == "FAIL"
    assert row["persona_text"] == payload
    assert row["verdict"] == turn.verdict


@pytest.mark.parametrize("line", [
    *(part for value in HOUSE_LINES_EN.values()
      for part in (value if isinstance(value, tuple) else (value,))),
    *HARNESS_LINES_EN.values(),
])
def test_h1_near_copy_detects_each_stored_house_line(line):
    """Every policy card part and harness house line is protected in its stored form."""
    assert checks.house_line_near_copy(line)


def test_h1_near_copy_detects_the_card_after_two_changed_words():
    """Changing two words of the existing card opener still leaves the required matching run."""
    words = HOUSE_LINES_EN["escalation_card"][0].split()
    words[:2] = ["Okay.", "Okay."]
    assert checks.house_line_near_copy(" ".join(words))
    assert checks.house_line_near_copy(" ".join(HOUSE_LINES_EN["escalation_card"]))


def test_h1_near_copy_detects_careful_side_text_inside_a_longer_reply():
    """Surrounding ordinary reply text cannot hide an embedded careful-side line."""
    assert checks.house_line_near_copy(
        GRIEF_REPLY + "\n" + HOUSE_LINES_EN["minor_inferred"] + "\n" + GRIEF_REPLY
    )


def test_h1_near_copy_obeys_contiguous_eighty_percent_and_short_line_thresholds():
    """Seven of eight consecutive words suffice; six do not; a short line must be complete."""
    words = HARNESS_LINES_EN["made_page_footer"].split()
    assert len(words) == 8
    assert checks.house_line_near_copy(" ".join(words[:7]))
    assert not checks.house_line_near_copy(" ".join(words[:6]))
    short = HARNESS_LINES_EN["t2_room_invalid"].split()
    assert checks.house_line_near_copy(" ".join(short))
    assert not checks.house_line_near_copy(" ".join(short[:-1]))
    # Separate small runs cannot be added together to cross the threshold.
    assert not checks.house_line_near_copy(" Okay. ".join(words))


def test_h1_near_copy_uses_public_unicode_and_lookalike_folds():
    """Case, spacing, punctuation and the policy's look-alike characters cannot hide a copy."""
    line = HOUSE_LINES_EN["minor_declared"]
    altered = "  ".join(line.upper().split()).replace("O", "О")
    assert checks.house_line_near_copy(altered)
    assert checks.house_line_near_copy(" / ".join(line.split()))


def test_h1_near_copy_has_zero_false_alarms_on_all_observed_baseline_fake_releases():
    """All 652 observed baseline releases, comprising 30 distinct replies, clear every new check."""
    corpus = json.loads((ROOT / "tests/fixtures/h1/fake_replies_before.json").read_text(encoding="utf-8"))
    assert corpus["pytest_status"] == 0
    assert len(corpus["replies"]) == 30
    assert sum(row["released_turns"] for row in corpus["replies"]) == 652
    for row in corpus["replies"]:
        assert not checks.house_line_near_copy(row["text"]), row["text"][:100]
        assert all(value == "PASS" for value in checks.release_checks(row["text"]).values())


def test_h1_house_checks_prevent_both_ship_and_operator_circle_release(monkeypatch):
    """A failed checkpoint bypasses both possible J.R. release doors."""
    from dataclasses import replace

    import secondsignal_harness.harness as module

    actual_audit = module.audit
    for status in ("SHIP", "WITHHOLD"):
        monkeypatch.setattr(module, "audit",
                            lambda req, status=status: replace(actual_audit(req), status=status))
        near_copy_only = " ".join(HARNESS_LINES_EN["made_page_footer"].split()[:7])
        harness = Harness(load_roster(), FakeAdapter(script=(near_copy_only,)),
                          CodexStore(ROOT / "docs/codex"), operator_circle=True)
        turn = harness.speak(table_tests.PROMPT)
        assert not turn.released
        assert harness.audit_log.rows()[-1]["release_checks"] == {
            "reserved_reply_voice": "PASS", "unsafe_url_scheme": "PASS",
            "house_line_near_copy": "FAIL",
        }
        assert turn.release_reason == "release_check:house_line_near_copy"
