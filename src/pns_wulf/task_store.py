from __future__ import annotations

import json
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


def task_recorder() -> None:
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
    print("task-recorder> new <id> | name <text> | area <AREA> | alias <text> | cooldown <sec>")
    print("               screen <SCREEN> | check <name> | tap <x> <y> <name> | tap-event <target> | note <text> | show | save | quit")
    while True:
        try:
            command = input("task-recorder> ").strip()
        except KeyboardInterrupt:
            print()
            continue
        lower = command.lower()
        if lower in ("quit", "q", "exit"):
            break
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
        elif lower.startswith("note "):
            record["query_loop"].append({"type": "note", "text": command[5:].strip()})
        elif lower == "show":
            print(json.dumps(record, ensure_ascii=False, indent=2))
        elif lower == "save":
            if not record["id"]:
                print("new <id> zuerst ausführen")
                continue
            path = RECORDINGS_DIR / (record["id"] + ".task.json")
            write_json(path, record)
            print("saved", path)
        else:
            print("unknown")
