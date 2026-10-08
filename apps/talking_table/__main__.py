"""Start the local Talking Table without any runtime dependencies."""

from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path

NOTICE = "A prototype for the operator and adults the operator knows. Not a crisis service."


def _open_page(url: str) -> None:
    try:
        if not webbrowser.open(url, new=2):
            print("Open the local address shown above in your browser.", flush=True)
    except Exception:
        print("Open the local address shown above in your browser.", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the local Talking Table.")
    parser.add_argument("--port", type=int, default=8765, help="Local port (default: 8765).")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser.")
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="Storage folder outside the repository; mainly for isolated tests.")
    parser.add_argument("--make-operator-token", action="store_true",
                        help="Create the local operator token without starting the Table.")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("the port must be between 0 and 65535")

    app = None
    server = None
    try:
        from .server import TableApp, make_server

        if args.make_operator_token:
            from .t3 import make_operator_token
            created = make_operator_token(args.data_dir or Path.home() / ".secondsignal" / "talking-table")
            print("The local operator token was created." if created else
                  "The local operator token already exists.", flush=True)
            return 0
        app = TableApp(data_dir=args.data_dir)
        server = make_server(app, host="127.0.0.1", port=args.port)
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        print(NOTICE, flush=True)
        print(f"Talking Table: {url}", flush=True)
        print("Keep this window open while using the table. Close it to stop.", flush=True)
        if not args.no_browser:
            threading.Thread(target=_open_page, args=(url,), daemon=True).start()
        server.serve_forever(poll_interval=0.2)
        return 0
    except KeyboardInterrupt:
        print("\nThe table has stopped.", flush=True)
        return 0
    except Exception:
        # Exceptions can contain request data or credentials. Never echo them.
        print("The table could not start or continue; close its other window and try again.",
              file=sys.stderr, flush=True)
        return 1
    finally:
        if app is not None:
            app.close()
        if server is not None:
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
