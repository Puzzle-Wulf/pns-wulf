from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

from .paths import expand_path
from .util import BAD, WARN, log, run_cmd


def scroll_swipe_coordinates(
    width: int,
    height: int,
    direction: str,
    distance: float = 0.60,
) -> tuple[int, int, int, int]:
    """Translate semantic content-scroll direction to an ADB finger swipe."""
    width = int(width)
    height = int(height)
    if width <= 1 or height <= 1:
        raise ValueError("Ungültige Displaygröße")

    direction = str(direction or "").strip().lower()
    if direction not in {"up", "down", "left", "right"}:
        raise ValueError("Scroll-Richtung muss up, down, left oder right sein")

    distance = float(distance)
    if not 0.10 <= distance <= 0.80:
        raise ValueError("Scroll-Distanz muss zwischen 0.10 und 0.80 liegen")

    center_x = width // 2
    center_y = height // 2
    if direction in {"up", "down"}:
        span = max(2, round(height * distance))
        top = max(1, center_y - span // 2)
        bottom = min(height - 2, center_y + span // 2)
        # Content down => finger moves up; content up => finger moves down.
        if direction == "down":
            return center_x, bottom, center_x, top
        return center_x, top, center_x, bottom

    span = max(2, round(width * distance))
    left = max(1, center_x - span // 2)
    right = min(width - 2, center_x + span // 2)
    # Content right => finger moves left; content left => finger moves right.
    if direction == "right":
        return right, center_y, left, center_y
    return left, center_y, right, center_y


class ADBDevice:
    def __init__(self, adb_path: str, serial: str):
        configured = str(adb_path or "adb")
        expanded = expand_path(configured)
        discovered = shutil.which(configured) if configured and not expanded.exists() else None
        self.adb = Path(discovered).resolve() if discovered else expanded
        self.serial = serial

    def _command(self, args: list[str]) -> list[str]:
        return [str(self.adb), "-s", self.serial, *args]

    def _require_adb(self) -> None:
        if not self.adb.exists():
            raise FileNotFoundError(
                f"ADB nicht gefunden: {self.adb}. Setze adb_path in config/pns_bot_config.json."
            )

    def run(self, args: list[str], timeout: int = 30):
        command = self._command(args)
        log("ADB", " ".join(command))
        self._require_adb()
        result = run_cmd(command, timeout=timeout)
        if result.returncode != 0:
            log("ADB ERROR", result.stderr.strip() or result.stdout.strip(), BAD)
        return result

    def shell(self, args: list[str], timeout: int = 30):
        return self.run(["shell", *args], timeout)

    def stream_shell(self, args: list[str]) -> subprocess.Popen:
        """Start a streaming adb shell command, used for live input-event capture."""
        command = self._command(["shell", *args])
        log("ADB STREAM", " ".join(command))
        self._require_adb()
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def tap(self, x: int, y: int, wait: float = 0.25) -> bool:
        result = self.shell(["input", "tap", str(int(x)), str(int(y))], 10)
        time.sleep(wait)
        return result.returncode == 0

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 450,
        wait: float = 0.25,
    ) -> bool:
        result = self.shell(
            [
                "input",
                "swipe",
                str(int(x1)),
                str(int(y1)),
                str(int(x2)),
                str(int(y2)),
                str(max(1, int(duration_ms))),
            ],
            15,
        )
        time.sleep(wait)
        return result.returncode == 0

    def screen_size(self) -> tuple[int, int]:
        result = self.shell(["wm", "size"], 10)
        if result.returncode != 0:
            raise RuntimeError("Displaygröße konnte nicht über 'wm size' gelesen werden")
        sizes = re.findall(r"(\d+)\s*x\s*(\d+)", result.stdout or "")
        if not sizes:
            raise RuntimeError("ADB 'wm size' lieferte keine Displaygröße")
        width, height = sizes[-1]
        return int(width), int(height)

    def scroll(
        self,
        direction: str,
        distance: float = 0.60,
        duration_ms: int = 450,
        wait: float = 0.25,
    ) -> bool:
        width, height = self.screen_size()
        x1, y1, x2, y2 = scroll_swipe_coordinates(width, height, direction, distance)
        return self.swipe(x1, y1, x2, y2, duration_ms, wait)

    def keyevent(self, key: str) -> bool:
        return self.shell(["input", "keyevent", str(key)], 10).returncode == 0

    def text(self, text: str) -> bool:
        return self.shell(["input", "text", text.replace(" ", "%s")], 15).returncode == 0

    def screenshot(self, path: Path) -> Path | None:
        path.parent.mkdir(parents=True, exist_ok=True)
        remote = f"/sdcard/pns_wulf_{int(time.time() * 1000)}.png"
        capture = self.shell(["screencap", "-p", remote], 15)
        if capture.returncode != 0:
            return None
        pull = self.run(["pull", remote, str(path)], 30)
        self.shell(["rm", remote], 10)
        if pull.returncode != 0 or not path.exists():
            log("SCREENSHOT", f"Screenshot konnte nicht gespeichert werden: {path}", WARN)
            return None
        return path

    def list_packages(self) -> list[str]:
        return self.shell(["pm", "list", "packages"], 20).stdout.splitlines()


class AppController:
    def __init__(self, device: ADBDevice, package_name: str | None):
        self.device = device
        self.package = package_name

    def detect_package(self) -> list[str]:
        terms = ["zmt", "puzzle", "survival", "global", "zombie"]
        candidates: list[str] = []
        for line in self.device.list_packages():
            package = line.replace("package:", "").strip()
            if any(term in package.lower() for term in terms):
                candidates.append(package)
        return candidates

    def start(self) -> bool:
        package = self.package
        if not package:
            candidates = self.detect_package()
            package = candidates[0] if candidates else None
        if not package:
            raise RuntimeError("PNS-Paket unbekannt. Setze package_name in der Konfiguration.")
        self.package = package
        return self.device.shell(
            ["monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"], 30
        ).returncode == 0
