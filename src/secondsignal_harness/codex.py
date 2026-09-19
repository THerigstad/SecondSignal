"""The codex store: the system text a persona is spoken from, byte for byte.

A codex (``docs/codex/<id>.md``) has Part A, the house block, identical in
every codex; Part B, the character's own text; a machine-readable block that
mirrors the profile the router reads; and a change log. The model is given
Part A and Part B exactly as written and nothing after them (ADR-0029 (Proposed)
(Proposed), rule 3). The machine-readable block is data for a test, not
words for a voice, and the change log is history; both are cut.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

PART_A_HEADING = "## Part A. What the house owns"
PART_B_HEADING = "## Part B. What the character owns"
MACHINE_BLOCK_HEADING = "### Machine-readable block"
CHANGE_LOG_HEADING = "## Change log"


def default_codex_dir() -> Path:
    """``docs/codex`` of the repository this package was imported from, when present."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "codex"
        if (candidate / "house-block.md").exists():
            return candidate
    raise FileNotFoundError(
        "no docs/codex directory above this package; pass CodexStore(directory) explicitly"
    )


class CodexStore:
    """Reads codexes from one directory and cuts them to what a voice is given."""

    def __init__(self, directory: Path | str | None = None) -> None:
        self.directory = Path(directory) if directory is not None else default_codex_dir()
        if not (self.directory / "house-block.md").exists():
            raise FileNotFoundError(f"{self.directory} holds no house-block.md")
        self._raw: dict[str, str] = {}

    def path(self, agent_id: str) -> Path:
        candidate = self.directory / f"{agent_id}.md"
        if not candidate.exists():
            raise FileNotFoundError(f"no codex for {agent_id!r} in {self.directory}")
        return candidate

    def raw(self, agent_id: str) -> str:
        if agent_id not in self._raw:
            self._raw[agent_id] = self.path(agent_id).read_text(encoding="utf-8")
        return self._raw[agent_id]

    def system_text(self, agent_id: str) -> str:
        """Part A then Part B, verbatim; the machine-readable block and the change log cut."""
        text = self.raw(agent_id)
        start = text.find(PART_A_HEADING)
        if start < 0:
            raise ValueError(f"{agent_id}: codex has no Part A heading")
        if PART_B_HEADING not in text:
            raise ValueError(f"{agent_id}: codex has no Part B heading")
        end = text.find(CHANGE_LOG_HEADING, start)
        body = text[start:] if end < 0 else text[start:end]
        machine = body.find(MACHINE_BLOCK_HEADING)
        if machine >= 0:
            body = body[:machine]
        body = body.rstrip()
        # Part B may end in the horizontal rule that preceded the machine block; drop it.
        while body.endswith("---"):
            body = body[:-3].rstrip()
        return body + "\n"

    def part_a(self, agent_id: str) -> str:
        """The house block as this codex carries it (a test holds it equal across codexes)."""
        body = self.system_text(agent_id)
        cut = body.find(PART_B_HEADING)
        head = body[:cut].rstrip()
        while head.endswith("---"):
            head = head[:-3].rstrip()
        return head + "\n"

    def part_b(self, agent_id: str) -> str:
        body = self.system_text(agent_id)
        cut = body.find(PART_B_HEADING)
        return body[cut:]

    def digest(self, agent_id: str) -> str:
        """SHA-256 of the system text, for the audit row (which codex edition spoke)."""
        return hashlib.sha256(self.system_text(agent_id).encode("utf-8")).hexdigest()


__all__ = ["CodexStore", "default_codex_dir"]
