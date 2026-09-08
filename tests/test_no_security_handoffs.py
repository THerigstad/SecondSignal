"""No profile may hand a person to a security character.

The security characters (the intake function, the ledger and interlock, the
audit harness) are not routable and have no seat: ADR-0014 and
ADR-0019 (Proposed).  A handoff row that names one of them is a promise the runtime
refuses, and a persona that believes it can make that handoff can be talked
into announcing it.  This test walks every profile the tree carries, in any
format, and fails on the first such row.  It exists because a pre-roster YAML
profile carried one for a week without anything noticing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ROOTS = (ROOT / "agents", ROOT / "src" / "secondsignal" / "profiles")
SECURITY_IDS = {"orrin", "aya", "jr", "j.r.", "j_r"}
YAML_HANDOFF = re.compile(r"^\s*-?\s*to:\s*['\"]?([A-Za-z_.]+)['\"]?\s*$", re.M)


def _profile_files() -> list[Path]:
    files: list[Path] = []
    for root in PROFILE_ROOTS:
        if root.is_dir():
            files.extend(p for p in root.rglob("*") if p.suffix in {".json", ".yaml", ".yml"})
    return files


def _handoff_targets(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
        handoffs = data.get("handoffs", {})
        if isinstance(handoffs, dict):
            return [str(v) for v in handoffs.values()]
        if isinstance(handoffs, list):
            return [str(h.get("to", "")) for h in handoffs if isinstance(h, dict)]
        return []
    return YAML_HANDOFF.findall(text)


def test_no_profile_hands_off_to_a_security_character() -> None:
    offenders = []
    for path in _profile_files():
        for target in _handoff_targets(path):
            if target.strip().lower() in SECURITY_IDS:
                offenders.append(f"{path.relative_to(ROOT)}: handoff to {target!r}")
    assert not offenders, "\n".join(offenders)


def test_no_profile_file_is_named_for_a_security_character() -> None:
    named = [
        str(path.relative_to(ROOT))
        for path in _profile_files()
        if path.stem.lower() in SECURITY_IDS or path.parent.name.lower() in SECURITY_IDS
    ]
    assert not named, f"security characters have no profile: {named}"
