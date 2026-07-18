from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from .constants import VERSION
from .paths import CONFIG_DIR, PROJECT_ROOT
from .util import GREEN, load_json, log, write_json

CONFIG_FILE = CONFIG_DIR / "pns_bot_config.json"
CONFIG_EXAMPLE = CONFIG_DIR / "pns_bot_config.example.json"
QUEUE_FILE = CONFIG_DIR / "task_queues.json"
QUEUE_EXAMPLE = CONFIG_DIR / "task_queues.example.json"
CLICK_FILE = CONFIG_DIR / "click_events.json"
CLICK_EXAMPLE = CONFIG_DIR / "click_events.example.json"


def normalize_host_url(value: str, port: int | None = None) -> tuple[str, int]:
    raw = str(value or "").strip() or "http://10.0.10.1:8789"
    if "://" not in raw:
        raw = "http://" + raw
    bad = re.match(r"^(https?://)(\d+\.\d+\.\d+\.\d+)\.(\d+)$", raw)
    if bad:
        raw = bad.group(1) + bad.group(2) + ":" + bad.group(3)
    match = re.match(r"^(https?://[^/:]+):(\d+)$", raw)
    if match:
        return raw, int(match.group(2))
    final_port = int(port or 8789)
    return raw.rstrip("/"), final_port


def parse_character_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;|]+", str(value or "")) if item.strip()]


def get_characters(config: dict) -> list[str]:
    characters = config.get("characters") or []
    if isinstance(characters, str):
        characters = parse_character_list(characters)
    if not characters and config.get("account"):
        characters = [config["account"]]
    if not characters and config.get("character_name"):
        characters = [config["character_name"]]
    return characters or [str(config.get("serial", "UNKNOWN")).replace(":", "_")]


def active_character_index(config: dict) -> int:
    characters = get_characters(config)
    index = max(0, int(config.get("active_character_index", 0) or 0))
    return index if index < len(characters) else 0


def expected_character(config: dict) -> str:
    return get_characters(config)[active_character_index(config)]


def save_config(config: dict) -> None:
    config["version"] = VERSION
    write_json(CONFIG_FILE, config)


def ensure_mutable_files() -> None:
    for source, destination in (
        (QUEUE_EXAMPLE, QUEUE_FILE),
        (CLICK_EXAMPLE, CLICK_FILE),
    ):
        if not destination.exists() and source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)


def default_adb_path() -> str:
    if os.name == "nt":
        return "vendor/platform-tools/windows/adb.exe"
    return "adb"


def setup() -> dict:
    example = load_json(CONFIG_EXAMPLE, {})
    example["version"] = VERSION
    print(f"PNS-Wulf Setup {VERSION}")
    print("pns-bot start initialisiert nur; eine Queue startet ausschließlich mit pns-bot play.")
    example["subnet"] = input("Subnet [10.0.10.0/24]: ").strip() or "10.0.10.0/24"
    host_raw = input("Host URL [http://10.0.10.1:8789]: ").strip() or "http://10.0.10.1:8789"
    normalized, detected_port = normalize_host_url(host_raw)
    host_port = int(input(f"Host Port [{detected_port}]: ").strip() or detected_port)
    normalized, host_port = normalize_host_url(normalized, host_port)
    if re.match(r"^https?://[^/:]+$", normalized):
        normalized += f":{host_port}"
    example["host_url"] = normalized
    example["host_port"] = host_port
    example["adb_path"] = input(f"ADB path [{default_adb_path()}]: ").strip() or default_adb_path()
    example["serial"] = input("ADB Serial [emulator-5554]: ").strip() or "emulator-5554"
    example["instance_label"] = input("Instanzlabel [Farmen-0]: ").strip() or "Farmen-0"
    old_account = example.get("account") or "Shadow-Claws"
    characters = parse_character_list(
        input(f"Charaktere kommagetrennt [{old_account}]: ").strip() or old_account
    )
    example["characters"] = characters
    example["active_character_index"] = 0
    example["account"] = characters[0]
    example["character_name"] = characters[0]
    example["package_name"] = input("Puzzle & Survival package, leer=auto-detect: ").strip()
    example["setup_done"] = True
    save_config(example)
    ensure_mutable_files()
    log("SETUP", f"geschrieben: {CONFIG_FILE}", GREEN)
    return example


def load_config(auto_setup: bool = True) -> dict:
    if not CONFIG_FILE.exists():
        if auto_setup:
            return setup()
        raise FileNotFoundError(f"Konfiguration fehlt: {CONFIG_FILE}")
    config = load_json(CONFIG_FILE, {})
    if not config.get("setup_done") and auto_setup:
        return setup()
    if config.get("version") != VERSION:
        config["version"] = VERSION
        save_config(config)
    ensure_mutable_files()
    return config
