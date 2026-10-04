"""The operator's local Talking Table; no installed package is required."""

import sys
from pathlib import Path

_source = str(Path(__file__).resolve().parents[2] / "src")
if _source not in sys.path:
    sys.path.insert(0, _source)
