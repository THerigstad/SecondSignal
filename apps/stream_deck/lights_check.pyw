"""Ask the running Table to show its lights check; a .pyw opens no console.

The key never talks to the lamps and never carries the lights key. It asks
the Table, through the Table's own existing lights-check request, and the
Table decides: when its lights are off or not set up, or while the crisis
card holds the floor, nothing is shown and the Table's settings page says
why. A stopped Table makes the key do nothing at all.
"""

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
            f"http://127.0.0.1:{port}/api/lights/check", data=b"{}",
            headers={"Content-Type": "application/json"}, method="POST")
        # The request must stay local even on a machine with an HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=20) as response:
            response.read()
    except (urllib.error.URLError, OSError, ValueError):
        # A missing or restarting Table should not open a dialog or console.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
