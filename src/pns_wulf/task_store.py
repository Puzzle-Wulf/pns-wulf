from __future__ import annotations

import json
import shlex
import shutil
from pathlib import Path

from .configuration import QUEUE_EXAMPLE, QUEUE_FILE
from .constants import VERSION
from .paths import PROJECT_ROOT, RECORDINGS_DIR, expand_path
from .util import GREEN, load_json, log, write_json


def task_tree_path(config: dict) -> Path:
    return expand_path(config.get("task_tree_file", "data/pns_tasks_areas_screens_full.json"))


def load_tree(config: dict) -> dict:
    return load_json(task_tree_path(config), {"version": VERSION, "areas": {}, "screens": {}, "tasks": []})


def save_tree(config: dict, tree: dict) -> None:
    tree["version"] = VERSION
    write_json(task_tree_path(config), tree)


def ensure_queue_store() -> None:
    if QUEUE_FILE.exists():
        return
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if QUEUE_EXAMPLE.exists():
        shutil.copyfile(QUEUE_EXAMPLE, QUEUE_FILE)
    else:
        write_json(QUEUE_FILE, {"version": VERSION, "active_queue": "default", "queues": {"default": {"enabled": True, "tasks": []}}})


def load_queues() -> dict:
    ensure_queue_store()
    return load_json(QUEUE_FILE, {"version": VERSION, "active_queue": "default", "queues": {}})


def save_queues(data: dict) -> None:
    data["version"] = VERSION
    write_json(QUEUE_FILE, data)


def find_task(tree: dict, task_id: str) -> dict | None:
    for task in tree.get("tasks", []):
        if task.get("id") == task_id or task.get("name", "").lower() == str(task_id).lower():
            return task
    return None


def list_tasks(config: dict, area: str = "") -> None:
    for task in load_tree(config).get("tasks", []):
        if not area or task.get("area") == area:
            print(f"{task['id']}: {task['name']} [{task.get('area', '')}]")


def show_task(config: dict, task_id: str) -> None:
    task = find_task(load_tree(config), task_id)
    print(json.dumps(task or {"error": "task not found"}, ensure_ascii=False, indent=2))


def edit_task(config: dict, task_id: str, name: str | None, area: str | None, cooldown: int | None) -> None:
    tree = load_tree(config)
    task = find_task(tree, task_id)
    if not task:
        raise SystemExit("Task nicht gefunden: " + task_id)
    if name:
        task["name"] = name
    if area:
        task["area"] = area
    if cooldown is not None:
        task["cooldown_seconds"] = int(cooldown)
    task["version"] = VERSION
    save_tree(config, tree)
    log("TASK EDIT", task_id, GREEN)


def import_task(config: dict, file: str) -> None:
    path = expand_path(file)
    task = load_json(path, None)
    if not task or not task.get("id"):
        raise SystemExit("Ungültige Task-Datei: " + str(path))
    task["version"] = VERSION
    tree = load_tree(config)
    tree["tasks"] = [item for item in tree.get("tasks", []) if item.get("id") != task["id"]]
    tree["tasks"].append(task)
    save_tree(config, tree)
    log("TASK IMPORT", task["id"], GREEN)


def queue_list() -> None:
    queues = load_queues()
    print("active_queue:", queues.get("active_queue"))
    for name, item in queues.get("queues", {}).items():
        marker = "*" if name == queues.get("active_queue") else " "
        print(f"{marker} {name}: {len(item.get('tasks', []))} tasks - {item.get('description', '')}")


def queue_show(name: str | None = None) -> None:
    queues = load_queues()
    name = name or queues.get("active_queue")
    item = queues.get("queues", {}).get(name)
    if not item:
        raise SystemExit("Queue nicht gefunden: " + str(name))
    print(json.dumps({name: item}, ensure_ascii=False, indent=2))


def queue_new(name: str, description: str = "") -> None:
    queues = load_queues()
    queues.setdefault("queues", {})[name] = {"enabled": True, "description": description, "tasks": []}
    queues["active_queue"] = name
    save_queues(queues)
    log("QUEUE NEW", name, GREEN)


def queue_use(name: str) -> None:
    queues = load_queues()
    if name not in queues.get("queues", {}):
        raise SystemExit("Queue nicht gefunden: " + name)
    queues["active_queue"] = name
    save_queues(queues)
    log("QUEUE USE", name, GREEN)


def queue_add(name: str | None, task_id: str) -> None:
    queues = load_queues()
    name = name or queues.get("active_queue")
    item = queues.setdefault("queues", {}).setdefault(name, {"enabled": True, "description": "", "tasks": []})
    item.setdefault("tasks", []).append(task_id)
    save_queues(queues)
    log("QUEUE ADD", f"{name} <- {task_id}", GREEN)


def queue_remove(name: str | None, index: int) -> None:
    queues = load_queues()
    name = name or queues.get("active_queue")
    item = queues.get("queues", {}).get(name)
    if not item:
        raise SystemExit("Queue nicht gefunden: " + str(name))
    removed = item.get("tasks", []).pop(int(index))
    save_queues(queues)
    log("QUEUE REMOVE", f"{name}[{index}] {removed}", GREEN)


def queue_clear(name: str | None) -> None:
    queues = load_queues()
    name = name or queues.get("active_queue")
    queues.setdefault("queues", {}).setdefault(name, {"enabled": True, "description": "", "tasks": []})["tasks"] = []
    save_queues(queues)
    log("QUEUE CLEAR", name, GREEN)


def numeric_text_value(value: str) -> str:
    value = str(value or "").strip()
    if not value or not value.isdigit():
        raise ValueError("Text-Input muss ausschließlich aus Ziffern bestehen")
    return value


def make_scroll_step(
    direction: str,
    distance: float = 0.60,
    duration_ms: int = 450,
) -> dict:
    direction = str(direction or "down").strip().lower()
    if direction not in {"up", "down", "left", "right"}:
        raise ValueError("Scroll-Richtung muss up, down, left oder right sein")
    distance = float(distance)
    if not 0.10 <= distance <= 0.80:
        raise ValueError("Scroll-Distanz muss zwischen 0.10 und 0.80 liegen")
    return {
        "type": "scroll",
        "direction": direction,
        "distance": distance,
        "duration_ms": max(1, int(duration_ms)),
    }


def _ensure_guided_identity(record: dict, empty) -> dict:
    if record.get("id"):
        return record
    task_id = input("Task-ID: ").strip()
    if not task_id:
        raise ValueError("Task-ID darf nicht leer sein")
    record = empty(task_id)
    name = input("Task-Name (optional): ").strip()
    area = input("Area (optional): ").strip()
    if name:
        record["name"] = name
    if area:
        record["area"] = area.upper()
    return record


def _save_record(record: dict) -> Path:
    if not record.get("id"):
        raise ValueError("Task-ID fehlt")
    path = RECORDINGS_DIR / (record["id"] + ".task.json")
    write_json(path, record)
    print("saved", path)
    return path


def _guided_tap(config: dict | None, record: dict) -> None:
    if not config:
        raise RuntimeError("Tap-Aufnahme benötigt eine geladene PNS-Wulf-Konfiguration")

    from .adb import ADBDevice
    from .click_events import ClickEventRegistry
    from .screenshots import capture_runtime
    from .touch_capture import TouchCaptureUnavailable, capture_two_finger_region

    target = input("Tap-Asset/Target: ").strip()
    if not target:
        raise ValueError("Tap-Target darf nicht leer sein")

    device = ADBDevice(config["adb_path"], config["serial"])
    registry = ClickEventRegistry(
        expand_path(config.get("click_events_file", "config/click_events.json"))
    )

    try:
        screenshot, region, touch_meta = capture_two_finger_region(
            device,
            config.get("screenshots_dir"),
            prefix="task-touch-template",
        )
        event = registry.create_template_from_screenshot(target, screenshot, region)
        data = registry.load()
        capture = data.setdefault("events", {}).setdefault(target, {}).setdefault("capture", {})
        capture.update(touch_meta)
        registry.save(data)
        event = registry.get(target)
        print("2-finger image saved", event.get("template"), "-> tap_area", target)
    except (TouchCaptureUnavailable, ValueError) as exc:
        print("2-Finger-Auswahl nicht verfügbar:", exc)
        print("Fallback: Screenshot wird geöffnet; Bereich mit der Maus markieren und Enter drücken.")
        screenshot = capture_runtime(
            device,
            config.get("screenshots_dir"),
            prefix="task-template-fallback",
        )
        event = registry.create_template_from_screenshot(target, screenshot, None)
        print("image saved", event.get("template"), "-> tap_area", target)

    record["query_loop"].append({"type": "tap_area", "target": target})


def _guided_scroll(record: dict) -> None:
    direction = input("Scroll-Richtung [down/up/left/right] (down): ").strip().lower() or "down"
    record["query_loop"].append(make_scroll_step(direction))
    print("scroll added", direction)


def _guided_text(record: dict) -> None:
    value = numeric_text_value(input("Zahl eingeben: "))
    record["query_loop"].append({"type": "text_input", "value": value})
    print("text_input added", value)


def task_recorder(config: dict | None = None) -> None:
    def empty(task_id: str = "") -> dict:
        return {
            "version": VERSION,
            "id": task_id,
            "name": "",
            "area": "",
            "aliases": [],
            "cooldown_seconds": 3600,
            "prechecks": ["where_am_i", "cooldown_ready"],
            "query_loop": [],
        }

    record = empty()
    RECORDINGS_DIR.mkdir(exist_ok=True)

    print("Geführter Task Builder: tap | scroll | text")
    print("Für den bisherigen Kommandomodus: advanced")
    try:
        first = input("Was soll der erste Schritt tun? [tap/scroll/text/advanced]: ").strip().lower()
    except KeyboardInterrupt:
        print()
        return

    guided = first in {"tap", "scroll", "text"}
    pending = first if guided else ""
    print("task-recorder> new <id> | name <text> | area <AREA> | alias <text> | cooldown <sec>")
    print("               screen <SCREEN> | check <name> | tap <x> <y> <name> | tap-event <target>")
    print("               image <target> [screenshot] [x,y,w,h] | scroll <dir> [distance] [ms] | text <digits>")
    print("               tap | scroll | text | advanced | note <text> | show | save | done | quit")

    while True:
        try:
            if pending:
                command = pending
                pending = ""
            else:
                prompt = "next-step> " if guided else "task-recorder> "
                command = input(prompt).strip()
        except KeyboardInterrupt:
            print()
            continue

        lower = command.lower()
        if lower in ("quit", "q", "exit"):
            break
        if lower == "advanced":
            guided = False
            continue
        if lower == "done":
            try:
                _save_record(record)
            except Exception as exc:
                print("save error:", exc)
            break

        if lower in {"tap", "scroll", "text"}:
            guided = True
            try:
                record = _ensure_guided_identity(record, empty)
                if lower == "tap":
                    _guided_tap(config, record)
                elif lower == "scroll":
                    _guided_scroll(record)
                else:
                    _guided_text(record)
            except Exception as exc:
                print(f"{lower} error:", exc)
            continue

        if lower.startswith("new "):
            record = empty(command[4:].strip())
        elif lower.startswith("name "):
            record["name"] = command[5:].strip()
        elif lower.startswith("area "):
            record["area"] = command[5:].strip().upper()
        elif lower.startswith("alias "):
            record.setdefault("aliases", []).append(command[6:].strip())
        elif lower.startswith("cooldown "):
            record["cooldown_seconds"] = int(command.split()[1])
        elif lower.startswith("screen "):
            record["query_loop"].append({"type": "expect_screen", "screen": command[7:].strip().upper()})
        elif lower.startswith("check "):
            record["query_loop"].append({"type": "check", "name": command[6:].strip()})
        elif lower.startswith("tap-event "):
            record["query_loop"].append({"type": "tap_area", "target": command[10:].strip()})
        elif lower.startswith("tap "):
            parts = command.split(maxsplit=3)
            record["query_loop"].append({"type": "tap", "x": int(parts[1]), "y": int(parts[2]), "name": parts[3] if len(parts) > 3 else ""})
        elif lower.startswith("scroll "):
            try:
                parts = command.split()
                direction = parts[1]
                distance = float(parts[2]) if len(parts) > 2 else 0.60
                duration_ms = int(parts[3]) if len(parts) > 3 else 450
                record["query_loop"].append(make_scroll_step(direction, distance, duration_ms))
            except Exception as exc:
                print("scroll error:", exc)
        elif lower.startswith("text "):
            try:
                value = numeric_text_value(command[5:])
                record["query_loop"].append({"type": "text_input", "value": value})
            except Exception as exc:
                print("text error:", exc)
        elif lower.startswith("image "):
            try:
                from .adb import ADBDevice
                from .click_events import ClickEventRegistry
                from .screenshots import capture_runtime
                from .template_capture import parse_region

                parts = shlex.split(command)
                if len(parts) < 2 or len(parts) > 4:
                    raise ValueError("Syntax: image <target> [screenshot|-] [x,y,w,h]")
                target = parts[1]
                screenshot = None if len(parts) < 3 or parts[2] == "-" else expand_path(parts[2])
                region = parse_region(parts[3]) if len(parts) == 4 else None
                if screenshot is None:
                    if not config:
                        raise RuntimeError("Live-Screenshot benötigt eine geladene PNS-Wulf-Konfiguration")
                    device = ADBDevice(config["adb_path"], config["serial"])
                    screenshot = capture_runtime(device, config.get("screenshots_dir"), prefix="task-template")
                registry_path = expand_path(config.get("click_events_file", "config/click_events.json")) if config else None
                registry = ClickEventRegistry(registry_path) if registry_path else ClickEventRegistry()
                event = registry.create_template_from_screenshot(target, screenshot, region)
                record["query_loop"].append({"type": "tap_area", "target": target})
                print("image saved", event.get("template"), "-> tap_area", target)
            except Exception as exc:
                print("image error:", exc)
        elif lower.startswith("note "):
            record["query_loop"].append({"type": "note", "text": command[5:].strip()})
        elif lower == "show":
            print(json.dumps(record, ensure_ascii=False, indent=2))
        elif lower == "save":
            try:
                _save_record(record)
            except Exception as exc:
                print("save error:", exc)
        elif lower == "":
            continue
        else:
            print("unknown")
