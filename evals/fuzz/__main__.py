"""``python -m evals.fuzz``: run the crisis-gate fuzz and print its one line,
then every variant that does not escalate, one per line, with the text's
invisible characters written as escapes."""

from __future__ import annotations

import sys

from .run import run


def main() -> int:
    result = run()
    try:
        print(result.line())
        for name, rows in result.failures.items():
            for case_id, text, action, agent in rows:
                seat = f" seats {agent}" if agent else ""
                print(f"  {name}: {case_id} -> {action}{seat}: {text!r}")
    except BrokenPipeError:  # piped into head; the line was printed
        pass
    return 1 if result.regressions or result.closed_gaps else 0


if __name__ == "__main__":
    sys.exit(main())
