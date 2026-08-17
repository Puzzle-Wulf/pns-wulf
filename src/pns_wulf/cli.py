from __future__ import annotations

import argparse
import json

from .adb import ADBDevice
from .automation import play
from .click_events import ClickEventRegistry
from .configuration import load_config, setup
from .constants import REPOSITORY_URL, VERSION
from .database import list_cooldowns
from .paths import expand_path
from .runtime import initialize_runtime, read_character, where_am_i
from .screenshots import capture_destination, capture_runtime
from .task_store import (
    edit_task,
    import_task,
    list_tasks,
    load_tree,
    queue_add,
    queue_clear,
    queue_list,
    queue_new,
    queue_remove,
    queue_show,
    queue_use,
    show_task,
    task_recorder,
)
from .template_capture import parse_region
from .util import GREEN, log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pns-bot",
        description=f"PNS-Wulf {VERSION}: ADB Runtime, Task-Queues, Screenshots und Click-Event-Kalibrierung.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("version")
    sub.add_parser("setup")
    sub.add_parser("start")

    play_parser = sub.add_parser("play")
    play_parser.add_argument("--queue", default="")
    play_parser.add_argument("--execute", action="store_true")
    play_parser.add_argument("--one-character", action="store_true")

    screenshot = sub.add_parser("screenshot")
    screenshot.add_argument("--destination", required=True, choices=["Desktop", "Userhome"], type=str)

    sub.add_parser("whereami")
    sub.add_parser("areas")
    sub.add_parser("screens")
    sub.add_parser("task-recorder")
    sub.add_parser("cooldowns")

    tasks = sub.add_parser("tasks")
    tasks.add_argument("--area", default="")
    task_show = sub.add_parser("task-show")
    task_show.add_argument("task_id")
    task_edit = sub.add_parser("task-edit")
    task_edit.add_argument("task_id")
    task_edit.add_argument("--name")
    task_edit.add_argument("--area")
    task_edit.add_argument("--cooldown", type=int)
    task_import = sub.add_parser("task-import")
    task_import.add_argument("file")

    queue = sub.add_parser("queue")
    queue_sub = queue.add_subparsers(dest="qcmd")
    queue_sub.add_parser("list")
    queue_show_parser = queue_sub.add_parser("show")
    queue_show_parser.add_argument("name", nargs="?")
    queue_new_parser = queue_sub.add_parser("new")
    queue_new_parser.add_argument("name")
    queue_new_parser.add_argument("--description", default="")
    queue_use_parser = queue_sub.add_parser("use")
    queue_use_parser.add_argument("name")
    queue_add_parser = queue_sub.add_parser("add")
    queue_add_parser.add_argument("task_id")
    queue_add_parser.add_argument("--queue", default="")
    queue_remove_parser = queue_sub.add_parser("remove")
    queue_remove_parser.add_argument("index", type=int)
    queue_remove_parser.add_argument("--queue", default="")
    queue_clear_parser = queue_sub.add_parser("clear")
    queue_clear_parser.add_argument("--queue", default="")

    click = sub.add_parser("click-event")
    click_sub = click.add_subparsers(dest="ecmd")
    click_sub.add_parser("list")
    click_show = click_sub.add_parser("show")
    click_show.add_argument("name")
    click_set = click_sub.add_parser("set")
    click_set.add_argument("name")
    click_set.add_argument("--x", required=True, type=int)
    click_set.add_argument("--y", required=True, type=int)
    click_template = click_sub.add_parser("template")
    click_template.add_argument("name")
    click_template.add_argument("--file", required=True)
    click_template.add_argument("--threshold", type=float)
    click_crop = click_sub.add_parser("crop")
    click_crop.add_argument("name")
    click_crop.add_argument("--file", required=True, help="vollständiger Screenshot")
    click_crop.add_argument("--region", default="", help="optional x,y,width,height; leer öffnet die Auswahl")
    click_crop.add_argument("--threshold", type=float)
    click_capture = click_sub.add_parser("capture")
    click_capture.add_argument("name")
    click_capture.add_argument("--region", default="", help="optional x,y,width,height; leer öffnet die Auswahl")
    click_capture.add_argument("--threshold", type=float)
    click_remove = click_sub.add_parser("remove")
    click_remove.add_argument("name")

    sub.add_parser("validate")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    if args.cmd == "version":
        print(VERSION)
        print(REPOSITORY_URL)
        return 0
    if args.cmd == "setup":
        setup()
        return 0

    if args.cmd == "click-event":
        local_config = None
        try:
            local_config = load_config(auto_setup=False)
            registry = ClickEventRegistry(expand_path(local_config.get("click_events_file", "config/click_events.json")))
        except FileNotFoundError:
            registry = ClickEventRegistry()
        if args.ecmd == "list":
            print(json.dumps(registry.list(), ensure_ascii=False, indent=2))
        elif args.ecmd == "show":
            print(json.dumps(registry.get(args.name), ensure_ascii=False, indent=2))
        elif args.ecmd == "set":
            print(json.dumps(registry.set_coordinate(args.name, args.x, args.y), ensure_ascii=False, indent=2))
        elif args.ecmd == "template":
            print(json.dumps(registry.set_template(args.name, args.file, args.threshold), ensure_ascii=False, indent=2))
        elif args.ecmd == "crop":
            region = parse_region(args.region)
            print(json.dumps(registry.create_template_from_screenshot(args.name, args.file, region, args.threshold), ensure_ascii=False, indent=2))
        elif args.ecmd == "capture":
            if not local_config:
                raise SystemExit("click-event capture benötigt eine vorhandene config/pns_bot_config.json")
            device = ADBDevice(local_config["adb_path"], local_config["serial"])
            screenshot = capture_runtime(device, local_config.get("screenshots_dir"), prefix="template-source")
            region = parse_region(args.region)
            print(json.dumps(registry.create_template_from_screenshot(args.name, screenshot, region, args.threshold), ensure_ascii=False, indent=2))
        elif args.ecmd == "remove":
            print("removed" if registry.remove(args.name) else "not found")
        else:
            parser.parse_args(["click-event", "--help"])
        return 0

    config = load_config()
    if args.cmd == "start":
        initialize_runtime(config, start_app=True)
        return 0
    if args.cmd == "play":
        return play(config, args.queue or None, args.execute, args.one_character)
    if args.cmd == "screenshot":
        device = ADBDevice(config["adb_path"], config["serial"])
        print(capture_destination(device, args.destination))
        return 0
    if args.cmd == "tasks":
        list_tasks(config, args.area)
        return 0
    if args.cmd == "task-show":
        show_task(config, args.task_id)
        return 0
    if args.cmd == "task-edit":
        edit_task(config, args.task_id, args.name, args.area, args.cooldown)
        return 0
    if args.cmd == "task-import":
        import_task(config, args.file)
        return 0
    if args.cmd == "areas":
        for area in load_tree(config).get("areas", {}):
            print(area)
        return 0
    if args.cmd == "screens":
        for screen in load_tree(config).get("screens", {}):
            print(screen)
        return 0
    if args.cmd == "whereami":
        print(json.dumps(where_am_i(config, ADBDevice(config["adb_path"], config["serial"])), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "cooldowns":
        device = ADBDevice(config["adb_path"], config["serial"])
        list_cooldowns(config, read_character(config, device))
        return 0
    if args.cmd == "task-recorder":
        task_recorder(config)
        return 0
    if args.cmd == "queue":
        if args.qcmd == "list":
            queue_list()
        elif args.qcmd == "show":
            queue_show(args.name)
        elif args.qcmd == "new":
            queue_new(args.name, args.description)
        elif args.qcmd == "use":
            queue_use(args.name)
        elif args.qcmd == "add":
            queue_add(args.queue or None, args.task_id)
        elif args.qcmd == "remove":
            queue_remove(args.queue or None, args.index)
        elif args.qcmd == "clear":
            queue_clear(args.queue or None)
        return 0
    if args.cmd == "validate":
        tree = load_tree(config)
        registry = ClickEventRegistry()
        log("VALIDATE", f"version={VERSION} tasks={len(tree.get('tasks', []))} click-events={len(registry.list())}", GREEN)
        return 0
    return 0
