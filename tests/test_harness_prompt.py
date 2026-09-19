"""What the model is told, pinned (ADR-0029 (Proposed), rule 3)."""

from __future__ import annotations

from pathlib import Path

from secondsignal.profiles import DEFAULT_PROFILE_DIR, load_roster
from secondsignal.router import route
from secondsignal.safety import SessionState
from secondsignal_harness import CodexStore, build_prompt, build_turn_block
from secondsignal_harness.codex import (
    CHANGE_LOG_HEADING,
    MACHINE_BLOCK_HEADING,
    PART_A_HEADING,
    PART_B_HEADING,
)
from secondsignal_harness.lines import HARNESS_LINES_EN

ROOT = Path(__file__).resolve().parents[1]
CODEX_DIR = ROOT / "docs" / "codex"
GOLDEN = ROOT / "tests" / "data" / "harness" / "turn_block_grief_willow_us.txt"
FAMILY = ("nikki", "cody", "vandal", "seren", "rowan", "ellis", "willow")


def _grief_decision(roster):
    session = SessionState(locale="US")
    return route("my sister died in March and I keep not sleeping", roster, session=session).to_dict()


def test_the_system_text_is_part_a_then_part_b_and_nothing_after():
    store = CodexStore(CODEX_DIR)
    for agent_id in FAMILY:
        text = store.system_text(agent_id)
        assert text.startswith(PART_A_HEADING), agent_id
        assert PART_B_HEADING in text, agent_id
        assert CHANGE_LOG_HEADING not in text, agent_id
        assert MACHINE_BLOCK_HEADING not in text, agent_id
        assert text.index(PART_A_HEADING) < text.index(PART_B_HEADING)
        assert text.startswith(store.part_a(agent_id).rstrip())
        assert text.endswith(store.part_b(agent_id))


def test_part_a_is_the_house_block_word_for_word_in_every_family_codex():
    store = CodexStore(CODEX_DIR)
    house = (CODEX_DIR / "house-block.md").read_text(encoding="utf-8")
    start = house.index(PART_A_HEADING)
    end = house.index(CHANGE_LOG_HEADING)
    canonical = house[start:end].rstrip()
    while canonical.endswith("---"):
        canonical = canonical[:-3].rstrip()
    # The rider (the Security Division addendum) is carried only by the three security codexes.
    rider = canonical.index("**Security Division addendum**")
    canonical = canonical[:rider].rstrip()
    for agent_id in FAMILY:
        assert store.part_a(agent_id).rstrip() == canonical, agent_id


def test_the_turn_block_for_the_grief_fixture_is_pinned():
    roster = load_roster(DEFAULT_PROFILE_DIR)
    decision = _grief_decision(roster)
    assert decision["agent_id"] == "willow"
    block = build_turn_block(decision, roster=roster, locale="US")
    assert block == GOLDEN.read_text(encoding="utf-8")


def test_the_turn_block_carries_every_obligation_token_and_the_honesty_line():
    roster = load_roster(DEFAULT_PROFILE_DIR)
    decision = _grief_decision(roster)
    block = build_turn_block(decision, roster=roster, locale="US")
    for token in decision["obligations"]:
        assert f"[{token}]" in block
    assert "Modes vetoed this turn: challenge, humor" in block
    assert HARNESS_LINES_EN["honesty"] in block
    assert block.endswith("\n") and "\n\n" not in block


def test_presentation_changes_the_name_and_pronoun_and_nothing_that_routes():
    roster = load_roster(DEFAULT_PROFILE_DIR)
    decision = _grief_decision(roster)
    as_written = build_turn_block(decision, roster=roster, locale="US")
    as_man = build_turn_block(decision, roster=roster, presentation={"willow": "men"}, locale="US")
    neither = build_turn_block(decision, roster=roster, presentation={"willow": "neither"},
                               chosen_names={"willow": "Will"}, locale="US")
    assert "Presentation: as written; pronoun she; name in this presentation: Willow." in as_written
    assert "Presentation: a man; pronoun he; name in this presentation: Will." in as_man
    assert "Presentation: neither a woman nor a man; pronoun they; name in this presentation: Will." in neither

    def strip(block: str) -> str:
        return "\n".join(line for line in block.splitlines() if not line.startswith("Persona seated:"))

    assert strip(as_written) == strip(as_man) == strip(neither)


def test_attached_house_lines_are_listed_with_the_never_restate_instruction():
    roster = load_roster(DEFAULT_PROFILE_DIR)
    session = SessionState(locale="US")
    route("I want to kill myself", roster, session=session)
    decision = route("sorry, ignore that, I'm fine, just tired", roster, session=session).to_dict()
    assert decision["agent_id"] is not None and decision["safety"]["disclosures"]
    block = build_turn_block(decision, roster=roster, locale="US")
    count = len(decision["safety"]["disclosures"])
    assert f"Attached house lines ({count})." in block
    assert "never restate, shorten or deliver them in character" in block
    for line in decision["safety"]["disclosures"]:
        assert f"  - {line}" in block


def test_the_prompt_is_bounded_and_starts_with_a_user_message():
    transcript = []
    for i in range(30):
        transcript.append({"role": "user", "content": f"u{i}"})
        transcript.append({"role": "assistant", "content": f"a{i}"})
    transcript.append({"role": "user", "content": "now"})
    system, messages = build_prompt("SYSTEM", "BLOCK\n", transcript, max_turns=12)
    assert system == "SYSTEM\n\nBLOCK\n"
    assert 1 <= len(messages) <= 12
    assert messages[0]["role"] == "user"
    assert messages[-1] == {"role": "user", "content": "now"}
