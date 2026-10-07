"""Start a new sitting through the running Table without a console."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) > 1:
        return 2
    try:
        port = int(arguments[0] if arguments else
                   os.environ.get("SECONDSIGNAL_TABLE_PORT", "8765"))
        if not 0 < port < 65536:
            return 2
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/session/reset", data=b"{}",
            headers={"Content-Type": "application/json"}, method="POST")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=20) as response:
            response.read()
    except (urllib.error.URLError, OSError, ValueError):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
