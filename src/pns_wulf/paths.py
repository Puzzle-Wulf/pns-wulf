from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("PNS_WULF_ROOT", Path(__file__).resolve().parents[2])).resolve()
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
RECORDINGS_DIR = PROJECT_ROOT / "recordings"

_PERCENT_VAR = re.compile(r"%([^%]+)%")


def expand_path(value: str | os.PathLike[str]) -> Path:
    raw = str(value)

    def repl(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), match.group(0))

    raw = _PERCENT_VAR.sub(repl, raw)
    raw = os.path.expandvars(os.path.expanduser(raw))
    if os.name != "nt":
        raw = raw.replace("\\", "/")
    path = Path(raw)
    if not path.is_absolute() and not re.match(r"^[A-Za-z]:[\\/]", raw):
        path = PROJECT_ROOT / path
    return path.resolve()
