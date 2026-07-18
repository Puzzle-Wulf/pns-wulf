from __future__ import annotations

import datetime
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _enable_windows_ansi() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


COLOR = _enable_windows_ansi()
RST = "\033[0m" if COLOR else ""
TURQ = "\033[38;2;64;224;208m" if COLOR else ""
WHITE = "\033[1;97m" if COLOR else ""
GRAY = "\033[38;2;178;178;178m" if COLOR else ""
DIM = "\033[38;2;135;135;135m" if COLOR else ""
BLUE = "\033[38;2;88;166;255m" if COLOR else ""
GREEN = "\033[38;2;90;255;165m" if COLOR else ""
WARN = "\033[38;2;255;207;102m" if COLOR else ""
BAD = "\033[38;2;255;107;107m" if COLOR else ""


def color(text: str, code: str) -> str:
    return f"{code}{text}{RST}" if COLOR else text


def log(label: str, message: object, code: str = GRAY) -> None:
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(
        f"{color('[', TURQ)}{color(now, DIM)}{color(']', TURQ)} "
        f"{color(label, WHITE)}{color(':', TURQ)} {color(str(message), code)}",
        flush=True,
    )


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log("WARN", f"JSON konnte nicht gelesen werden: {path}: {exc}", WARN)
    return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_cmd(args: list[str], timeout: int = 30, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd, shell=False)
