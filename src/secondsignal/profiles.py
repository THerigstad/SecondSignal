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

Names are an alias layer (ADR-0026 (Proposed) motivated it; the layer itself
is built). A profile has one canonical ``id`` and may declare ``aliases``:
earlier names it was known by, and its short form. The roster resolves an
alias anywhere it accepts an id, so a fixture written by an external reviewer
under an earlier name still names the same persona, byte for byte, and the
decision record always carries the canonical id. Two profiles may never share
a name in any form; the roster refuses to load if they do.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

__all__ = [
    "AgentProfile",
    "Roster",
    "load_profile",
    "load_roster",
    "roster_hash",
    "find_stabilizers",
    "known_persona_names",
    "default_aliases",
    "canonical_id",
    "canonicalize_expectation",
    "DEFAULT_PROFILE_DIR",
]

DEFAULT_PROFILE_DIR = Path(__file__).resolve().parent / "profiles"


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
            Never inferred about the caller; never a routing score. Under
            ADR-0026 (Proposed) this becomes the "as written" default of a
            presentation block rather than a routing input of any kind.
        aliases: Other names that resolve to this profile: earlier canonical
            names and the short form. Lower-case, unique across the roster.
        short_name: The short form of the display name, if the persona has
            one ("Nik", "Will", "Elli"). Presentation only.
        presentation: The name forms of the persona's presentations under
            ADR-0026 (Proposed) as amended 2026-09-11: ``she`` and ``he`` name the woman's
            and the man's form of the one name (``Elli`` / ``Ellis``; the same
            word twice when the name does not shorten), ``they`` is the policy
            word ``either`` (the neutral presentation goes by either form, the
            person's choice), and ``as_written`` says which of ``she`` and
            ``he`` the codex was written in. Read by nothing that routes;
            ``tests/test_presentations.py`` pins that.
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
    aliases: tuple[str, ...] = ()
    short_name: str = ""
    presentation: dict[str, str] = field(default_factory=dict)
    source_hash: str = ""

    @property
    def names(self) -> tuple[str, ...]:
        """Every name that resolves to this profile: the id first, then aliases."""
        return (self.id, *self.aliases)

    @property
    def plate(self) -> tuple[tuple[str, str], tuple[str, str]]:
        """The name plate: two (name, label) pairs, always two, in the order
        the operator ruled on 2026-09-11: the full name first and the
        shortened form second, each with its label (``she`` or ``he``), so a
        reader can see the two forms are one person. A name that does not
        shorten is printed twice, ``she`` then ``he``. A profile without a
        presentation block plates its display name twice the same way.

        >>> ellis.plate
        (('Ellis', 'he'), ('Elli', 'she'))
        >>> nikki.plate
        (('Nikki', 'she'), ('Nik', 'he'))
        >>> cody.plate
        (('Cody', 'she'), ('Cody', 'he'))
        """
        she = self.presentation.get("she") or self.display_name
        he = self.presentation.get("he") or self.display_name
        if she == he:
            return ((she, "she"), (he, "he"))
        first, second = ((she, "she"), (he, "he")) if len(she) >= len(he) else ((he, "he"), (she, "she"))
        return (first, second)

    def name_for(self, presentation: str, chosen: str | None = None) -> tuple[str, str]:
        """The (name, pronoun label) a surface shows for one presentation
        setting: ``"as_written"``, ``"women"``, ``"men"`` or ``"neither"``.
        Under ``"neither"`` the label is ``they`` and the name is ``chosen``
        when it is one of this persona's two forms, else the display name
        (the full form) until the person picks. Presentation only: nothing
        that routes calls this."""
        she = self.presentation.get("she") or self.display_name
        he = self.presentation.get("he") or self.display_name
        if presentation == "women":
            return (she, "she")
        if presentation == "men":
            return (he, "he")
        if presentation == "neither":
            return (chosen if chosen in (she, he) else self.display_name, "they")
        written = self.presentation.get("as_written") or {"f": "she", "m": "he"}.get(self.voice, "")
        return (he, "he") if written == "he" else (she, "she") if written == "she" else (self.display_name, "")

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
        aliases=tuple(str(a).strip().lower() for a in data.get("aliases", ()) if str(a).strip()),
        short_name=str(data.get("short_name", "")),
        presentation={str(k): str(v) for k, v in dict(data.get("presentation", {})).items()},
        source_hash=source_hash,
    )


def load_profile(path: str | Path) -> AgentProfile:
    """Load a single agent profile from a JSON file, hashing its bytes."""
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    return _profile_from_dict(json.loads(raw.decode("utf-8")), source_hash=digest)


class Roster(dict):
    """An id -> profile map that also answers to every profile's aliases.

    ``roster["calder"]`` and ``roster["cody"]`` are the same profile once
    ``cody`` declares ``calder`` as an alias; iteration, ``keys()``,
    ``values()`` and ``len()`` see canonical ids only, so nothing is counted
    twice. ``resolve`` turns any known name into the canonical id and is the
    one place a name is normalized; an unknown name raises ``KeyError`` unless
    ``strict`` is false, in which case it is returned unchanged so a fixture
    that names a persona that does not exist fails on the comparison, not on
    the lookup.
    """

    def _index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for pid, profile in dict.items(self):
            index[pid] = pid
            for alias in getattr(profile, "aliases", ()):
                index.setdefault(alias, pid)
        return index

    def resolve(self, name: str | None, *, strict: bool = True) -> str | None:
        if name is None:
            return None
        key = str(name).strip().lower()
        index = self._index()
        if key in index:
            return index[key]
        if strict:
            raise KeyError(name)
        return name

    def __getitem__(self, name: str) -> AgentProfile:
        return dict.__getitem__(self, self.resolve(name))

    def __contains__(self, name: object) -> bool:  # type: ignore[override]
        if not isinstance(name, str):
            return False
        return self.resolve(name, strict=False) in dict.keys(self)

    def get(self, name: object, default: Any = None) -> Any:  # type: ignore[override]
        try:
            return self[str(name)]
        except KeyError:
            return default

    def aliases(self) -> dict[str, str]:
        """alias -> canonical id, for every alias in the roster."""
        return {alias: pid for alias, pid in self._index().items() if alias != pid}


def known_persona_names(directory: str | Path | None = None) -> tuple[str, ...]:
    """Every name any persona in the profile directory answers to, sorted,
    lower-case: canonical ids, aliases and short forms. Used by pattern
    builders that must recognise a persona named in a message (for example a
    request to always seat one), without loading or validating the roster."""
    directory = Path(directory or DEFAULT_PROFILE_DIR)
    names: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        names.add(str(data["id"]).lower())
        names.update(str(a).strip().lower() for a in data.get("aliases", ()) if str(a).strip())
        short = str(data.get("short_name", "")).strip().lower()
        if short:
            names.add(short)
    return tuple(sorted(names))


def default_aliases(directory: str | Path | None = None) -> dict[str, str]:
    """alias -> canonical id for the profile directory, read without loading
    or validating the roster. The fixture runners use it so a case written
    under an earlier name compares against the canonical id the decision
    record carries."""
    directory = Path(directory or DEFAULT_PROFILE_DIR)
    aliases: dict[str, str] = {}
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        pid = str(data["id"]).lower()
        for alias in data.get("aliases", ()):
            alias = str(alias).strip().lower()
            if alias:
                aliases[alias] = pid
    return aliases


def canonical_id(name: Any, aliases: dict[str, str] | None = None) -> Any:
    """The canonical id for `name` if it is a known alias, else `name` unchanged
    (including None). Unknown names pass through so a fixture that names a
    persona that does not exist fails on the comparison, visibly."""
    if not isinstance(name, str):
        return name
    table = default_aliases() if aliases is None else aliases
    return table.get(name.strip().lower(), name)


_EXPECTATION_NAME_FIELDS = ("agent", "assist")
_EXPECTATION_NAME_LISTS = ("agent_any_of", "not_seated", "ineligible")


def canonicalize_expectation(expect: dict, aliases: dict[str, str] | None = None) -> dict:
    """Return a copy of a fixture's ``expect`` block with every persona name
    resolved to its canonical id. The fixture file itself is never rewritten:
    external reviewers' fixtures stay byte for byte as they were returned."""
    table = default_aliases() if aliases is None else aliases
    out = dict(expect)
    for key in _EXPECTATION_NAME_FIELDS:
        if key in out:
            out[key] = canonical_id(out[key], table)
    for key in _EXPECTATION_NAME_LISTS:
        if key in out and isinstance(out[key], (list, tuple)):
            out[key] = [canonical_id(v, table) for v in out[key]]
    return out


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
    seen: dict[str, str] = {}
    for profile in roster.values():
        for name in profile.names:
            if name in seen and seen[name] != profile.id:
                raise ValueError(
                    f"name {name!r} is claimed by both {seen[name]!r} and {profile.id!r}; "
                    "no two agents may share a name in any form"
                )
            seen[name] = profile.id
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
    roster = Roster()

    for path in sorted(directory.glob("*.json")):
        profile = load_profile(path)
        if profile.id in dict.keys(roster):
            raise ValueError(f"duplicate agent id {profile.id!r} in {path}")
        dict.__setitem__(roster, profile.id, profile)

    validate_roster(roster)
    # Handoff targets may be written under an alias; the loaded contract
    # carries canonical ids so the decision record never shows two names for
    # one persona.
    for pid, profile in list(dict.items(roster)):
        normalized = {condition: roster.resolve(target) for condition, target in profile.handoffs.items()}
        if normalized != profile.handoffs:
            dict.__setitem__(roster, pid, replace(profile, handoffs=normalized))
    return roster
