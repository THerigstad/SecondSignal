"""Command-line inspector for routing decisions.

    python -m secondsignal "I can't get out of my own way on this painting"
    python -m secondsignal --session examples/dependency_session.txt
    python -m secondsignal --roster

The point of the CLI is that a reviewer can see the policy operate, and see the
trace behind each decision, without reading the source first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .profiles import DEFAULT_PROFILE_DIR, load_roster
from .router import route
from .safety import SessionState


def _print_roster(profile_dir: Path) -> int:
    roster = load_roster(profile_dir)
    print(f"{len(roster)} agents loaded from {profile_dir}\n")
    for profile in roster.values():
        low, high = profile.regulation_window
        print(f"  {profile.display_name:<8} [{low:.2f}–{high:.2f}]  {profile.one_line}")
        if profile.contraindications:
            print(f"           vetoed for: {', '.join(sorted(profile.contraindications))}")
    return 0


def _run_session(lines: list[str], profile_dir: Path) -> int:
    roster = load_roster(profile_dir)
    session = SessionState()
    for i, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        decision = route(line, roster, session=session)
        print(f"--- turn {i} " + "-" * 52)
        print(f"> {line}\n")
        print(decision.explain())
        for disclosure in decision.safety.disclosures:
            print(f"\n  [required disclosure] {disclosure}")
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="secondsignal",
        description="Inspect SecondSignal routing decisions.",
    )
    parser.add_argument("text", nargs="*", help="A single turn of input to route.")
    parser.add_argument(
        "--session", metavar="FILE",
        help="Route a multi-turn session, one turn per line. Use '-' for stdin.",
    )
    parser.add_argument("--roster", action="store_true", help="Print the loaded agent roster and exit.")
    parser.add_argument(
        "--profiles", metavar="DIR", default=str(DEFAULT_PROFILE_DIR),
        help="Directory of agent profile JSON files.",
    )
    args = parser.parse_args(argv)
    profile_dir = Path(args.profiles)

    if args.roster:
        return _print_roster(profile_dir)

    if args.session:
        source = sys.stdin if args.session == "-" else open(args.session, encoding="utf-8")
        with source as fh:
            return _run_session(fh.readlines(), profile_dir)

    if not args.text:
        parser.print_help()
        return 1

    return _run_session([" ".join(args.text)], profile_dir)


if __name__ == "__main__":
    raise SystemExit(main())
