"""Ask a character through the running Table; a .pyw opens no console."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# These are the supplied roster's display names, not routing instructions.
NAMES = {
    "vandal": "Vandal", "willow": "Willow", "cody": "Cody", "seren": "Seren",
    "rowan": "Rowan", "nikki": "Nikki", "ellis": "Ellis",
}


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    character = arguments[0] if arguments else Path(__file__).stem.removeprefix("ask_")
    name = NAMES.get(character.casefold())
    if name is None or len(arguments) > 2:
        return 2
    try:
        port = int(arguments[1] if len(arguments) == 2 else
                   os.environ.get("SECONDSIGNAL_TABLE_PORT", "8765"))
        if not 0 < port < 65536:
            return 2
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/turn",
            data=json.dumps({"text": f"Could I talk to {name}?"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        # Local asks must remain local even on a machine with an HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=20) as response:
            response.read()
    except (urllib.error.URLError, OSError, ValueError):
        # A missing or restarting Table should not open a dialog or console.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
