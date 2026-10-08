"""H1: every harness row carries truthful, reproducible configuration metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from test_harness_contract import GRIEF_REPLY

import secondsignal
import secondsignal_harness
from secondsignal import load_roster
from secondsignal_harness import AdapterReply, AuditLog, CodexStore, FakeAdapter, Harness
from secondsignal_harness.configuration import pack_revision, prompt_sha256

ROOT = Path(__file__).resolve().parents[1]
GRIEF = "my sister died in March and I keep not sleeping"


@pytest.fixture(scope="module")
def roster():
    return load_roster()


@pytest.fixture(scope="module")
def codexes():
    return CodexStore(ROOT / "docs/codex")


def speak(roster, codexes, text=GRIEF, adapter=None, **kwargs):
    harness = Harness(roster, adapter or FakeAdapter(script=(GRIEF_REPLY,)), codexes,
                      operator_circle=True, **kwargs)
    turn = harness.speak(text)
    return harness, turn, harness.audit_log.rows()[-1]


@pytest.mark.parametrize("text,script,kind", [
    ("I want to kill myself", GRIEF_REPLY, "gate"),
    ("hey", GRIEF_REPLY, "unresolved"),
    (GRIEF, RuntimeError("unavailable"), "failure"),
    (GRIEF, GRIEF_REPLY, "seated"),
])
def test_h1_every_row_kind_carries_complete_configuration(roster, codexes, text, script, kind):
    """Gate, unresolved, failed-model and seated rows retain the same configuration schema."""
    adapter = FakeAdapter(script=(script,))
    harness, turn, row = speak(roster, codexes, text, adapter)
    config = row["configuration"]
    assert row["kind"] == kind
    assert set(config) == {
        "model_id", "model_version", "prompt_sha256", "harness_version", "policy_version",
        "pack_versions", "roster_hash", "house_block_sha256", "presentation", "generation",
    }
    assert config["model_id"] == "fake-1" and config["model_version"] == "1"
    assert config["harness_version"] == secondsignal_harness.__version__
    assert config["policy_version"] == secondsignal.__version__
    assert config["pack_versions"] == {"en": 1, "es-419": 1, "resources": 2}
    assert config["roster_hash"] == turn.decision["roster_hash"]
    lock = json.loads((codexes.directory / "house-block.lock.json").read_text(encoding="utf-8"))
    assert config["house_block_sha256"] == lock["sha256"]
    assert config["presentation"]["order"] == "sorted_roster_ids"
    assert len(config["presentation"]["slots"]) == len(roster)
    for agent_id, slot in zip(sorted(roster), config["presentation"]["slots"], strict=True):
        profile = roster[agent_id]
        forms = (profile.display_name, profile.plate[0][0], profile.plate[1][0])
        assert slot["setting"] == "as_written"
        assert (forms[slot["name_form"]], slot["pronoun"]) == profile.name_for("as_written")
    if kind == "gate":
        from test_talking_table import assert_nameless_gate
        assert_nameless_gate(row, roster, turn.text)
    assert config["generation"] == {"max_turns": 12, "max_tokens": 600, "retries": 1}
    if adapter.calls:
        call = adapter.calls[-1]
        material = json.dumps({"system": call["system"], "messages": call["messages"]},
                              sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        assert config["prompt_sha256"] == hashlib.sha256(material.encode()).hexdigest()
    else:
        assert config["prompt_sha256"] is None
    assert "configuration" not in turn.decision


def test_h1_gate_audit_failure_receipt_still_carries_configuration(roster, codexes):
    """A successful second gate receipt includes configuration and cannot suppress or alter the card."""
    class OnceBroken(AuditLog):
        attempts = 0

        def append(self, row):
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("write unavailable")
            return super().append(row)

    log = OnceBroken()
    harness, turn, row = speak(roster, codexes, "I want to kill myself", audit_log=log)
    assert row["kind"] == "gate_audit_failure"
    assert row["configuration"]["roster_hash"] == turn.decision["roster_hash"]
    assert row["configuration"]["prompt_sha256"] is None
    assert turn.text == "\n".join(turn.house_lines) and turn.audit_error
    assert not harness.adapter.calls


def test_h1_same_case_and_configuration_repeat_identically(roster, codexes):
    """Clock changes affect row timestamps but never the reproducibility block."""
    _, a, row_a = speak(roster, codexes, clock=lambda: 1.0)
    _, b, row_b = speak(roster, codexes, clock=lambda: 2.0)
    assert row_a["at"] != row_b["at"] and row_a["row_id"] != row_b["row_id"]
    assert row_a["configuration"] == row_b["configuration"]
    assert a.decision == b.decision


@pytest.mark.parametrize("text", ["hey", "I want to kill myself", GRIEF])
def test_h1_presentation_changes_only_its_field_and_any_actual_prompt_hash(roster, codexes, text):
    """Presentation alone changes on no-call rows; seated prompts also get their accurate new hash."""
    _, base, row_a = speak(roster, codexes, text)
    _, changed, row_b = speak(roster, codexes, text, presentation={"willow": "men"})
    a, b = row_a["configuration"], row_b["configuration"]
    difference = {key for key in a if a[key] != b[key]}
    assert difference == ({"presentation", "prompt_sha256"} if text == GRIEF else {"presentation"})
    assert base.decision == changed.decision and base.house_lines == changed.house_lines
    # Both accepted name choices and fallback can be reconstructed without names in metadata.
    profile = roster["willow"]
    forms = (profile.display_name, profile.plate[0][0], profile.plate[1][0])
    for setting in ("as_written", "women", "men", "neither"):
        for chosen in (*forms, None):
            _, turn, row = speak(roster, codexes, text,
                                 presentation={"willow": setting}, chosen_names={"willow": chosen})
            slot = row["configuration"]["presentation"]["slots"][sorted(roster).index("willow")]
            assert slot["setting"] == setting
            assert (forms[slot["name_form"]], slot["pronoun"]) == profile.name_for(setting, chosen)
            if text == "I want to kill myself":
                from test_talking_table import assert_nameless_gate
                assert_nameless_gate(row, roster, turn.text)


def test_h1_prompt_hash_binds_roles_boundaries_and_full_history():
    """Changing message roles, segmentation or system text changes the full prompt hash."""
    base = prompt_sha256("a", [{"role": "user", "content": "bc"}])
    assert base != prompt_sha256("ab", [{"role": "user", "content": "c"}])
    assert base != prompt_sha256("a", [{"role": "assistant", "content": "bc"}])
    assert base != prompt_sha256("a", [{"role": "user", "content": "b"},
                                     {"role": "user", "content": "c"}])


def test_h1_reported_model_metadata_wins_and_missing_version_stays_null(roster, codexes):
    """Returned identity overrides requested identity without inventing a vendor model version."""
    class Reported(FakeAdapter):
        def complete(self, system, messages, *, max_tokens):
            return AdapterReply(GRIEF_REPLY, "reported-model", model_version=None)

    _, _, row = speak(roster, codexes, adapter=Reported(model_id="requested-model"))
    assert row["configuration"]["model_id"] == row["model_id"] == "reported-model"
    assert row["configuration"]["model_version"] is None


@pytest.mark.parametrize("secret", [
    "sk-PLANTED-KEY", "xai-PLANTED-KEY", "ghp_PLANTED_KEY",
    "github_pat_PLANTED_KEY", "Bearer PLANTED_KEY", "api_key=PLANTED_KEY",
    "AKIA0123456789ABCDEF", "AIza" + "X" * 35,
    'gsk_PLANTED_KEY', 'hf_PLANTED_KEY', 'xoxb-PLANTED_KEY',
    "eyJ" + "X" * 12 + "." + "Y" * 16 + "." + "Z" * 16,
])
def test_h1_key_shaped_metadata_cannot_enter_configuration(roster, codexes, secret):
    """Planted credentials in identity or presentation inputs never reach the configuration."""
    adapter = FakeAdapter(script=(GRIEF_REPLY,), name=secret, model_id=secret, model_version=secret)
    adapter.api_key = secret
    _, _, row = speak(roster, codexes, adapter=adapter,
                      presentation={secret: secret, "willow": "neither"},
                      chosen_names={"willow": secret})
    assert secret not in json.dumps(row["configuration"])
    assert row["configuration"]["model_id"] is None
    assert row["configuration"]["model_version"] is None
    assert row["model_id"] is None and row["adapter"] is None


def test_h1_unversioned_pack_uses_full_file_sha256():
    """A missing source version uses 64 hex digits, even if the policy loader defaulted to one."""
    raw = b'{"pack":"unversioned"}'
    assert pack_revision(raw, 1) == hashlib.sha256(raw).hexdigest()
    assert pack_revision(b'{"version":2}', 2) == 2


def test_h1_wrapped_fake_adapter_reports_identity_on_no_call_rows(roster, codexes):
    """The untouched Table-style wrapper cannot hide the configured fake identity."""
    class Wrapper:
        name = "fake"

        def __init__(self):
            self.adapter = FakeAdapter()

        def complete(self, *args, **kwargs):
            raise AssertionError("gate must not call adapter")

    _, _, row = speak(roster, codexes, "I want to kill myself", adapter=Wrapper())
    assert row["configuration"]["model_id"] == "fake-1"
    assert row["configuration"]["model_version"] == "1"


def test_h1_custom_codex_directory_without_lock_reports_absence(tmp_path, roster, codexes):
    """Existing caller-supplied codex directories still work without claiming an unrelated lock hash."""
    for name in ("house-block.md", "willow.md"):
        (tmp_path / name).write_bytes((codexes.directory / name).read_bytes())
    _, turn, row = speak(roster, CodexStore(tmp_path))
    assert turn.released
    assert row["configuration"]["house_block_sha256"] is None
