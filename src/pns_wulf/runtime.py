from __future__ import annotations

import time
from pathlib import Path

from .adb import ADBDevice, AppController
from .cluster import ensure_cluster
from .configuration import expected_character, get_characters, save_config
from .constants import VERSION
from .database import open_character_db
from .paths import PROJECT_ROOT, expand_path
from .screenshots import capture_runtime
from .sprites import ensure_pas_sprites
from .util import GREEN, WARN, log, write_json


def where_am_i(config: dict, device: ADBDevice) -> dict:
    screenshot = capture_runtime(device, config.get("screenshots_dir"), prefix="whereami")
    return {"screen": "UNKNOWN", "screenshot": str(screenshot)}


def screenshot_signature(path: str | Path | None) -> dict:
    try:
        data = Path(path).read_bytes() if path else b""
        return {"size": len(data), "head": data[:4096], "tail": data[-4096:]}
    except Exception:
        return {"size": 0, "head": b"", "tail": b""}


def signatures_changed(first: dict | None, second: dict | None) -> bool:
    if not first or not second:
        return True
    return first.get("size") != second.get("size") or first.get("head") != second.get("head") or first.get("tail") != second.get("tail")


def wait_app_ready(config: dict, device: ADBDevice) -> bool:
    back = PROJECT_ROOT / "assets" / "pas" / "menu" / "back.png"
    timeout = float(config.get("startup_wait_timeout_sec", 45))
    interval = float(config.get("startup_wait_interval_sec", 1.0))
    minimum = int(config.get("startup_wait_min_screenshots", 2))
    stable_needed = int(config.get("startup_wait_stable_screenshots", 2))
    started = time.time()
    last = None
    stable = 0
    shots = 0
    if not back.exists():
        log("WARN", "assets/pas/menu/back.png fehlt; nutze Screenshot-Stabilisierung", WARN)
    while time.time() - started < timeout:
        info = where_am_i(config, device)
        shots += 1
        signature = screenshot_signature(info.get("screenshot"))
        if signature.get("size", 0) > 0:
            stable = stable + 1 if last is not None and not signatures_changed(last, signature) else 0
            last = signature
        if shots >= minimum and stable >= stable_needed:
            log("READY", "App-Screen ist stabil", GREEN)
            return True
        time.sleep(interval)
    log("WARN", "Startup-Ready Timeout; fahre mit Screenshot-Modus fort", WARN)
    return False


def open_character_window(config: dict, device: ADBDevice) -> bool:
    steps = ((config.get("character_identify") or {}).get("open_character_window") or {}).get("steps", [])
    if not steps:
        log("CHARACTER", "Keine Schritte für open_character_window; Config-Fallback", WARN)
        return False
    for step in steps:
        if step.get("type") == "tap":
            device.tap(int(step["x"]), int(step["y"]))
        elif step.get("type") == "keyevent":
            device.keyevent(str(step["key"]))
        time.sleep(float(step.get("wait", 0.25)))
    return True


def read_character(config: dict, device: ADBDevice, expected: str | None = None) -> str:
    where_am_i(config, device)
    manual = (config.get("character_identify") or {}).get("manual_current_character")
    if manual:
        return manual
    if config.get("character_name") in get_characters(config):
        return config["character_name"]
    return expected or expected_character(config)


def identify_character(config: dict, device: ADBDevice, expected: str | None = None) -> tuple[str, bool]:
    target = expected or expected_character(config)
    open_character_window(config, device)
    actual = read_character(config, device, expected=target)
    ok = str(actual).strip().lower() == str(target).strip().lower()
    log("CHARACTER", f"expected={target} actual={actual} ok={ok}", GREEN if ok else WARN)
    return actual, ok


def switch_character(config: dict, device: ADBDevice, target: str) -> bool:
    steps = (((config.get("character_identify") or {}).get("switch_character") or {}).get("recorded_steps", []))
    log("CHARACTER SWITCH", f"Ziel={target}", GREEN)
    if not steps:
        log("CHARACTER SWITCH", "Keine recorded_steps vorhanden", WARN)
        return False
    for step in steps:
        if step.get("type") == "tap":
            device.tap(int(step["x"]), int(step["y"]))
        elif step.get("type") == "text":
            device.text(str(step.get("text", "")).replace("$CHARACTER", target))
        elif step.get("type") == "keyevent":
            device.keyevent(str(step["key"]))
        elif step.get("type") == "wait":
            time.sleep(float(step.get("seconds", 1)))
        time.sleep(float(step.get("wait", 0.25)))
    config["character_name"] = target
    save_config(config)
    wait_app_ready(config, device)
    return True


def initialize_runtime(config: dict, start_app: bool = True, expected: str | None = None):
    ensure_cluster(config)
    device = ADBDevice(config["adb_path"], config["serial"])
    ensure_pas_sprites(PROJECT_ROOT, config)
    if start_app:
        AppController(device, config.get("package_name") or None).start()
        wait_app_ready(config, device)
    target = expected or expected_character(config)
    actual, ok = identify_character(config, device, expected=target)
    if not ok:
        switch_character(config, device, target)
        actual, ok = identify_character(config, device, expected=target)
    character = target if ok else actual
    config["character_name"] = character
    config["account"] = character
    save_config(config)
    connection, db_path = open_character_db(config, character)
    state_path = expand_path(config.get("runtime_state_file", "runtime/state.json"))
    write_json(
        state_path,
        {
            "version": VERSION,
            "serial": config["serial"],
            "character": character,
            "expected_character": target,
            "db": str(db_path),
            "started_at": time.time(),
            "queue_playing": False,
        },
    )
    log("START", "Runtime bereit. Queue startet nur mit: pns-bot play", GREEN)
    log("CHARACTER", character, GREEN)
    log("DB", db_path, GREEN)
    return device, character, connection, db_path
