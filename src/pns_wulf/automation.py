from __future__ import annotations

import json
import time

from .click_events import ClickEventAbort, ClickEventRegistry, PauseController
from .configuration import active_character_index, get_characters, save_config
from .database import cooldown_ready, finalize_character_db, set_cooldown
from .irc import IRCRelay
from .runtime import initialize_runtime, switch_character, where_am_i
from .paths import expand_path
from .screenshots import capture_runtime
from .task_store import find_task, load_queues, load_tree
from .util import GREEN, WARN, log

CLICK_TYPES = {"tap", "tap_area", "tap_if_visible", "tap_repeat_until"}


def _resolve_click(config: dict, device, registry: ClickEventRegistry, pause: PauseController, task: dict, step: dict):
    screenshot = capture_runtime(device, config.get("screenshots_dir"), prefix="click-event")
    resolution = registry.resolve(step, screenshot, float(config.get("click_match_threshold", 0.86)))
    if resolution.resolved:
        return resolution
    if step.get("optional"):
        log("CLICK SKIP", f"{resolution.target}: {resolution.reason}", WARN)
        resolution.skipped = True
        return resolution
    if not config.get("pause_on_missing_click_event", True):
        raise ClickEventAbort(resolution.reason)
    return pause.pause(task, step, screenshot, resolution)


def _run_click(config: dict, device, registry: ClickEventRegistry, pause: PauseController, task: dict, step: dict) -> bool:
    step_type = step.get("type")
    resolution = _resolve_click(config, device, registry, pause, task, step)
    if resolution.skipped:
        return True
    if not resolution.resolved:
        return False
    if not device.tap(int(resolution.x), int(resolution.y)):
        return False
    log("CLICK", f"{resolution.target} @ {resolution.x},{resolution.y} via {resolution.source}", GREEN)

    if step_type != "tap_repeat_until":
        return True

    maximum = int(step.get("max_repeats", config.get("click_repeat_max", 10)))
    delay = float(step.get("repeat_delay_seconds", config.get("click_repeat_delay_seconds", 0.75)))
    for repeat in range(1, maximum):
        time.sleep(delay)
        screenshot = capture_runtime(device, config.get("screenshots_dir"), prefix="click-repeat")
        next_resolution = registry.resolve(step, screenshot, float(config.get("click_match_threshold", 0.86)))
        if not next_resolution.resolved:
            if step.get("until"):
                log("REPEAT DONE", f"{resolution.target}: {step.get('until')} nach {repeat} Klicks", GREEN)
                return True
            next_resolution = pause.pause(task, step, screenshot, next_resolution)
            if next_resolution.skipped:
                return True
        if not device.tap(int(next_resolution.x), int(next_resolution.y)):
            return False
    log("REPEAT LIMIT", f"{resolution.target}: max_repeats={maximum}", WARN)
    return True


def _run_scroll(device, step: dict) -> bool:
    direction = str(step.get("direction", "down")).lower()
    distance = float(step.get("distance", 0.60))
    duration_ms = int(step.get("duration_ms", 450))
    ok = device.scroll(direction, distance, duration_ms)
    if ok:
        log("SCROLL", f"{direction} distance={distance:.2f} duration_ms={duration_ms}", GREEN)
    return ok


def _run_text_input(device, step: dict) -> bool:
    value = str(step.get("value", ""))
    if not value or not value.isdigit():
        log("TEXT INPUT", "Nur numerische Werte sind erlaubt", WARN)
        return False
    ok = device.text(value)
    if ok:
        log("TEXT INPUT", value, GREEN)
    return ok


def run_task(config: dict, device, connection, task: dict, irc: IRCRelay) -> bool:
    if not cooldown_ready(connection, task["id"]):
        log("SKIP", task["id"] + " cooldown")
        return False
    log("TASK", task["name"], GREEN)
    registry = ClickEventRegistry(expand_path(config.get("click_events_file", "config/click_events.json")))
    pause = PauseController(config, device, registry)
    ok = True
    for step in task.get("query_loop", []):
        step_type = step.get("type")
        log("QUERY", json.dumps(step, ensure_ascii=False))
        if step_type == "check" and step.get("name") == "where_am_i":
            where_am_i(config, device)
        elif step_type == "check" and step.get("name") == "cooldown_ready":
            ok = cooldown_ready(connection, task["id"])
        elif step_type in CLICK_TYPES:
            if not config.get("execute_clicks") and not config.get("validate_click_events_in_dry_run", False):
                log("DRY", "not tapping " + str(step.get("target") or step.get("name")))
            else:
                ok = _run_click(config, device, registry, pause, task, step)
        elif step_type == "scroll":
            if not config.get("execute_clicks"):
                log(
                    "DRY",
                    f"not scrolling {step.get('direction', 'down')} "
                    f"distance={step.get('distance', 0.60)}",
                )
            else:
                ok = _run_scroll(device, step)
        elif step_type == "text_input":
            value = str(step.get("value", ""))
            if not value.isdigit():
                log("TEXT INPUT", "Ungültiger Task: value muss eine Zahl sein", WARN)
                ok = False
            elif not config.get("execute_clicks"):
                log("DRY", "not entering numeric text " + value)
            else:
                ok = _run_text_input(device, step)
        elif step_type in (
            "open_area",
            "open_screen",
            "run_task_branch",
            "select_resource",
            "dispatch_if_march_slot_available",
            "select_option",
            "confirm",
        ):
            log("HOOK", f"Konzeptioneller Step: {step_type}; benötigt bei echter Ausführung einen aufgenommenen Click-Event-Step")
        elif step_type == "on_success":
            pass
        if not ok:
            break
    if ok:
        set_cooldown(connection, task["id"], task.get("cooldown_seconds", 3600))
        irc.send("[TASK OK] " + task["name"])
    return ok


def play(config: dict, queue_name: str | None = None, execute: bool = False, one_character: bool = False) -> int:
    config["execute_clicks"] = bool(execute or config.get("execute_clicks"))
    tree = load_tree(config)
    queues = load_queues()
    queue_name = queue_name or queues.get("active_queue")
    queue = queues.get("queues", {}).get(queue_name)
    if not queue:
        raise SystemExit("Queue nicht gefunden: " + str(queue_name))
    relay = IRCRelay(config.get("irc", {}))
    characters = get_characters(config)
    start_index = active_character_index(config)
    indices = [start_index] if one_character else list(range(start_index, len(characters))) + list(range(0, start_index))
    log("PLAY", f"queue={queue_name} characters={len(indices)} tasks={len(queue.get('tasks', []))}", GREEN)

    try:
        for index in indices:
            config["active_character_index"] = index
            save_config(config)
            target = characters[index]
            device, character, connection, _ = initialize_runtime(config, start_app=True, expected=target)
            log("PLAY", f"character={character} queue={queue_name}", GREEN)
            for task_id in queue.get("tasks", []):
                task = find_task(tree, task_id)
                if task:
                    run_task(config, device, connection, task, relay)
                else:
                    log("WARN", "Task nicht gefunden: " + str(task_id), WARN)
            finalize_character_db(connection, character)
            next_index = (index + 1) % len(characters)
            config["active_character_index"] = next_index
            config["character_name"] = characters[next_index]
            config["account"] = characters[next_index]
            save_config(config)
            if len(characters) > 1:
                log("NEXT CHARACTER", f"{characters[next_index]} ist als nächster Account gesetzt", GREEN)
                if not one_character:
                    switch_character(config, device, characters[next_index])
            if one_character:
                break
    except ClickEventAbort as exc:
        log("ABORT", exc, WARN)
        return 75
    return 0
