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

Two invariants are enforced at load time rather than left to tests, because a
roster that violates them must not be able to start (ADR-0012):

* every handoff target resolves to a loaded agent;
* the roster contains a **stabilizer**: an agent whose regulation window
  reaches 0.0 and who carries no contraindications, so that there is always
  someone the router may hand any caller to. A wide window alone does not
  qualify -- an agent who vetoes humor cannot be the floor for a caller who
  asked for humor.

Every profile is hashed when loaded, and the roster hash travels with each
routing decision, so a replayed trace can be matched to the exact profiles
that produced it and a silent profile edit is visible.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "AgentProfile",
    "load_profile",
    "load_roster",
    "roster_hash",
    "find_stabilizers",
    "DEFAULT_PROFILE_DIR",
]

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
            estimate within which this agent is appropriate. The low bound is
            a hard eligibility floor: a caller below it is never routed to
            this agent. An agent whose value is challenge or humor has a high
            floor; a stabilizing agent has a floor of 0.0 and is safe across
            the whole range.
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
        voice: Declared voice register of the persona ("f", "m" or ""), used
            only to honour a *declared* affinity such as prefers_female_voice.
            Never inferred about the caller; never a routing score.
        source_hash: First 12 hex digits of the SHA-256 of the profile file as
            loaded. Empty for profiles built in memory.
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
    voice: str = ""
    source_hash: str = ""

    def accepts(self, regulation: float) -> bool:
        low, high = self.regulation_window
        return low <= regulation <= high

    @property
    def is_stabilizer(self) -> bool:
        """Safe at full dysregulation and cannot be vetoed by any request."""
        return self.regulation_window[0] <= 0.0 and not self.contraindications


def _profile_from_dict(data: dict, source_hash: str = "") -> AgentProfile:
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
        voice=str(data.get("voice", "")),
        source_hash=source_hash,
    )


def load_profile(path: str | Path) -> AgentProfile:
    """Load a single agent profile from a JSON file, hashing its bytes."""
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    return _profile_from_dict(json.loads(raw.decode("utf-8")), source_hash=digest)


def find_stabilizers(roster: dict[str, AgentProfile]) -> list[str]:
    """Ids of agents that satisfy the roster floor: window reaches 0.0 and no
    contraindications."""
    return sorted(p.id for p in roster.values() if p.is_stabilizer)


def roster_hash(roster: dict[str, AgentProfile]) -> str:
    """Stable digest of the loaded roster (ids and per-profile hashes)."""
    material = "|".join(f"{pid}:{roster[pid].source_hash}" for pid in sorted(roster))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def validate_roster(roster: dict[str, AgentProfile]) -> None:
    """Raise ValueError if the roster violates a load-time invariant."""
    if not roster:
        raise ValueError("roster is empty")
    for profile in roster.values():
        for condition, target in profile.handoffs.items():
            if target not in roster:
                raise ValueError(
                    f"agent {profile.id!r} declares handoff {condition!r} -> "
                    f"{target!r}, which is not a loaded agent"
                )
    if not find_stabilizers(roster):
        raise ValueError(
            "roster has no stabilizer: at least one agent must have a regulation "
            "floor of 0.0 and no contraindications, so that any caller can always "
            "be routed somewhere safe (ADR-0012)"
        )


def load_roster(directory: str | Path | None = None) -> dict[str, AgentProfile]:
    """Load every ``*.json`` profile in `directory` into an id -> profile map.

    Raises:
        ValueError: if two profiles declare the same id, if any handoff target
            does not resolve to a loaded agent, or if the roster has no
            stabilizer. Failing loudly at load time is preferred over
            discovering a dangling handoff -- or a missing floor -- mid-session.
    """
    directory = Path(directory or DEFAULT_PROFILE_DIR)
    roster: dict[str, AgentProfile] = {}

    for path in sorted(directory.glob("*.json")):
        profile = load_profile(path)
        if profile.id in roster:
            raise ValueError(f"duplicate agent id {profile.id!r} in {path}")
        roster[profile.id] = profile

    validate_roster(roster)
    return roster
