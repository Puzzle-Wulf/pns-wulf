from __future__ import annotations

import shutil
import time
from pathlib import Path

from .paths import expand_path
from .util import BAD, WARN, log, run_cmd


class ADBDevice:
    def __init__(self, adb_path: str, serial: str):
        configured = str(adb_path or "adb")
        expanded = expand_path(configured)
        discovered = shutil.which(configured) if configured and not expanded.exists() else None
        self.adb = Path(discovered).resolve() if discovered else expanded
        self.serial = serial

    def run(self, args: list[str], timeout: int = 30):
        command = [str(self.adb), "-s", self.serial, *args]
        log("ADB", " ".join(command))
        if not self.adb.exists():
            raise FileNotFoundError(
                f"ADB nicht gefunden: {self.adb}. Setze adb_path in config/pns_bot_config.json."
            )
        result = run_cmd(command, timeout=timeout)
        if result.returncode != 0:
            log("ADB ERROR", result.stderr.strip() or result.stdout.strip(), BAD)
        return result

    def shell(self, args: list[str], timeout: int = 30):
        return self.run(["shell", *args], timeout)

    def tap(self, x: int, y: int, wait: float = 0.25) -> bool:
        result = self.shell(["input", "tap", str(int(x)), str(int(y))], 10)
        time.sleep(wait)
        return result.returncode == 0

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
