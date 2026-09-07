"""Command-line inspector for routing decisions.

    python -m secondsignal "I can't get out of my own way on this painting"
    python -m secondsignal --session examples/dependency_session.txt
    python -m secondsignal --roster

The point of the CLI is that a reviewer can see the policy operate, and see the
trace behind each decision, without reading the source first.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
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


def _run_session(
    lines: Iterable[str],
    profile_dir: Path,
    locale: str | None = None,
    json_output: bool = False,
    skip_comments: bool = True,
) -> int:
    roster = load_roster(profile_dir)
    session = SessionState(locale=locale)
    for i, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or (skip_comments and line.startswith("#")):
            continue
        decision = route(line, roster, session=session)
        if json_output:
            print(json.dumps(decision.to_dict(), sort_keys=True, separators=(",", ":")))
            continue
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
        help="Directory of agent profile JSON files (defaults to the bundled roster).",
    )
    parser.add_argument(
        "--locale", metavar="CODE", default=None,
        help="Declared locale for crisis resources (e.g. US). Unset means the "
             "generic directory is used; the locale is never inferred.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print one compact JSON routing decision per turn.",
    )
    args = parser.parse_args(argv)
    profile_dir = Path(args.profiles)

    if args.roster:
        if args.json:
            parser.error("--json cannot be combined with --roster")
        return _print_roster(profile_dir)

    if args.session:
        if args.session == "-":
            return _run_session(sys.stdin, profile_dir, args.locale, args.json)
        with open(args.session, encoding="utf-8") as source:
            return _run_session(source, profile_dir, args.locale, args.json)

    if not args.text:
        if args.json:
            parser.error("--json requires text or --session")
        parser.print_help()
        return 1

    return _run_session(
        [" ".join(args.text)],
        profile_dir,
        args.locale,
        args.json,
        skip_comments=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
