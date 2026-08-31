"""Agent profiles: declarative, data-only agent definitions.

An agent in this system is not a prompt. It is a record describing what the
agent is competent at, what affective range it is safe within, what it must
*not* be routed for, and where it hands off when it reaches its edge.

Keeping this as data rather than prose has three consequences that matter:

1. Profiles are diffable. A change to an agent's contraindications shows up in
   version control as a reviewable line, not as a paragraph edit buried in a
   prompt.
2. Profiles are testable. `tests/test_profiles.py` asserts invariants across
   the whole roster (e.g. every handoff target resolves to a real agent).
3. Profiles are portable. The same roster drives any underlying model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["AgentProfile", "load_profile", "load_roster", "DEFAULT_PROFILE_DIR"]

DEFAULT_PROFILE_DIR = Path(__file__).resolve().parents[2] / "profiles"


@dataclass(frozen=True)
class AgentProfile:
    """A single agent's routing contract.

    Attributes:
        id: Stable identifier used in handoff targets and logs.
        display_name: Human-facing name.
        one_line: Short description for operator-facing tooling.
        domains: Topic tags this agent is competent in.
        modes: Interaction modes this agent performs well.
        regulation_window: (low, high) bounds on the caller's regulation
            estimate within which this agent is appropriate. An agent whose
            value is challenge or humor has a high floor; a stabilizing agent
            has a low floor and is safe across the whole range.
        contraindications: Domain or mode tags that veto this agent outright,
            regardless of score. This is the field that encodes "never route
            here," and it is the reason the roster is auditable.
        handoffs: condition -> agent id. Conditions are free-form tags emitted
            by the router when it detects that an active agent has reached the
            edge of its window.
        serves: Populations the agent is designed for. Documentation only.
        risks: Known failure modes for this agent. Documentation only, but
            deliberately colocated with the routing contract so that the risk
            analysis cannot drift away from the definition.
    """

    id: str
    display_name: str
    one_line: str
    domains: frozenset[str] = frozenset()
    modes: frozenset[str] = frozenset()
    regulation_window: tuple[float, float] = (0.0, 1.0)
    contraindications: frozenset[str] = frozenset()
    handoffs: dict[str, str] = field(default_factory=dict)
    serves: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()

    def accepts(self, regulation: float) -> bool:
        low, high = self.regulation_window
        return low <= regulation <= high


def _profile_from_dict(data: dict) -> AgentProfile:
    window = data.get("regulation_window", [0.0, 1.0])
    return AgentProfile(
        id=data["id"],
        display_name=data["display_name"],
        one_line=data["one_line"],
        domains=frozenset(data.get("domains", ())),
        modes=frozenset(data.get("modes", ())),
        regulation_window=(float(window[0]), float(window[1])),
        contraindications=frozenset(data.get("contraindications", ())),
        handoffs=dict(data.get("handoffs", {})),
        serves=tuple(data.get("serves", ())),
        risks=tuple(data.get("risks", ())),
    )


def load_profile(path: str | Path) -> AgentProfile:
    """Load a single agent profile from a JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        return _profile_from_dict(json.load(fh))


def load_roster(directory: str | Path | None = None) -> dict[str, AgentProfile]:
    """Load every ``*.json`` profile in `directory` into an id -> profile map.

    Raises:
        ValueError: if two profiles declare the same id, or if any handoff
            target does not resolve to a loaded agent. Failing loudly at load
            time is preferred over discovering a dangling handoff mid-session.
    """
    directory = Path(directory or DEFAULT_PROFILE_DIR)
    roster: dict[str, AgentProfile] = {}

    for path in sorted(directory.glob("*.json")):
        profile = load_profile(path)
        if profile.id in roster:
            raise ValueError(f"duplicate agent id {profile.id!r} in {path}")
        roster[profile.id] = profile

    for profile in roster.values():
        for condition, target in profile.handoffs.items():
            if target not in roster:
                raise ValueError(
                    f"agent {profile.id!r} declares handoff {condition!r} -> "
                    f"{target!r}, which is not a loaded agent"
                )

    return roster
