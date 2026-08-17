from __future__ import annotations

import os
import re
import time
from pathlib import Path

from .adb import ADBDevice
from .paths import RUNTIME_DIR, expand_path
from .util import GREEN, log


def _xdg_desktop(home: Path) -> Path:
    config = home / ".config" / "user-dirs.dirs"
    if config.exists():
        for line in config.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("XDG_DESKTOP_DIR="):
                value = line.split("=", 1)[1].strip().strip('"')
                value = value.replace("$HOME", str(home))
                return Path(os.path.expandvars(value)).expanduser()
    return home / "Desktop"


def resolve_destination(destination: str, home: Path | None = None) -> Path:
    home = (home or Path.home()).expanduser().resolve()
    key = destination.strip().lower()
    if key == "desktop":
        return _xdg_desktop(home).resolve()
    if key == "userhome":
        return (home / "Pictures" / "Screenshots").resolve()
    raise ValueError("destination muss Desktop oder Userhome sein")


def _safe_serial(serial: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", serial)


def _capture_stamp() -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1_000_000_000:09d}"


def capture_destination(device: ADBDevice, destination: str) -> Path:
    target_dir = resolve_destination(destination)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"pns-wulf_{_safe_serial(device.serial)}_{_capture_stamp()}.png"
    result = device.screenshot(target)
    if not result:
        raise RuntimeError("ADB-Screenshot fehlgeschlagen")
    log("SCREENSHOT", result, GREEN)
    return result


def capture_runtime(device: ADBDevice, configured_dir: str | None = None, prefix: str = "runtime") -> Path:
    directory = expand_path(configured_dir) if configured_dir else RUNTIME_DIR / "screenshots"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{prefix}_{_safe_serial(device.serial)}_{_capture_stamp()}.png"
    result = device.screenshot(target)
    if not result:
        raise RuntimeError("ADB-Screenshot fehlgeschlagen")
    return result
