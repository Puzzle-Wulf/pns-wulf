"""Compatibility entry point for older launch scripts."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pns_wulf.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
