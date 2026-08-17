from __future__ import annotations

import json
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .adb import ADBDevice
from .configuration import CLICK_EXAMPLE, CLICK_FILE
from .constants import VERSION
from .paths import PROJECT_ROOT, expand_path
from .screenshots import capture_destination, capture_runtime
from .template_capture import crop_template, safe_event_name
from .util import BAD, GREEN, WARN, load_json, log, write_json


@dataclass
class ClickResolution:
    resolved: bool
    target: str
    x: int | None = None
    y: int | None = None
    source: str = ""
    reason: str = ""
    score: float | None = None
    template: str | None = None
    skipped: bool = False


class ClickEventRegistry:
    def __init__(self, path: Path = CLICK_FILE):
        self.path = path
        self.ensure()

    def ensure(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if CLICK_EXAMPLE.exists():
                shutil.copyfile(CLICK_EXAMPLE, self.path)
            else:
                write_json(self.path, {"version": VERSION, "events": {}})

    def load(self) -> dict:
        data = load_json(self.path, {"version": VERSION, "events": {}})
        data.setdefault("events", {})
        return data

    def save(self, data: dict) -> None:
        data["version"] = VERSION
        write_json(self.path, data)

    def list(self) -> dict:
        return self.load().get("events", {})

    def get(self, name: str) -> dict:
        return self.list().get(name, {})

    def set_coordinate(self, name: str, x: int, y: int) -> dict:
        asset_name = safe_event_name(name)
        data = self.load()
        event = data.setdefault("events", {}).setdefault(name, {})
        event["coordinate"] = {"x": int(x), "y": int(y)}
        event.setdefault("template", f"assets/click-events/{asset_name}.png")
        self.save(data)
        return event

    def set_template(self, name: str, file: str, threshold: float | None = None) -> dict:
        source = expand_path(file)
        if not source.exists():
            raise FileNotFoundError(source)
        asset_name = safe_event_name(name)
        destination = PROJECT_ROOT / "assets" / "click-events" / f"{asset_name}.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != destination.resolve():
            shutil.copyfile(source, destination)
        data = self.load()
        event = data.setdefault("events", {}).setdefault(name, {})
        event["template"] = str(destination.relative_to(PROJECT_ROOT)).replace("\\", "/")
        if threshold is not None:
            event["threshold"] = float(threshold)
        self.save(data)
        return event

    def create_template_from_screenshot(
        self,
        name: str,
        screenshot: str | Path,
        region: tuple[int, int, int, int] | None = None,
        threshold: float | None = None,
    ) -> dict:
        source = expand_path(screenshot)
        target, selected, source_size = crop_template(source, name, region)
        self.set_template(name, str(target), threshold)
        data = self.load()
        event = data.setdefault("events", {}).setdefault(name, {})
        event.pop("coordinate", None)
        event["capture"] = {
            "source": str(source),
            "region": list(selected),
            "source_size": list(source_size),
        }
        self.save(data)
        return event

    def remove(self, name: str) -> bool:
        data = self.load()
        removed = data.setdefault("events", {}).pop(name, None) is not None
        self.save(data)
        return removed

    @staticmethod
    def target_for_step(step: dict) -> str:
        return str(step.get("target") or step.get("name") or step.get("event") or "unnamed_click_event")

    def resolve(self, step: dict, screenshot: Path, default_threshold: float = 0.86) -> ClickResolution:
        target = self.target_for_step(step)
        if step.get("x") is not None and step.get("y") is not None:
            return ClickResolution(True, target, int(step["x"]), int(step["y"]), "step-coordinate")

        event = self.get(target)
        coordinate = event.get("coordinate") or {}
        if coordinate.get("x") is not None and coordinate.get("y") is not None:
            return ClickResolution(True, target, int(coordinate["x"]), int(coordinate["y"]), "registry-coordinate")

        template_value = step.get("template") or event.get("template")
        if not template_value:
            try:
                template_value = f"assets/click-events/{safe_event_name(target)}.png"
            except ValueError as exc:
                return ClickResolution(False, target, source="template", reason=f"Ungültiger Event-Name: {exc}")
        template = expand_path(template_value)
        if not template.exists():
            return ClickResolution(
                False,
                target,
                source="template",
                reason=f"PNG-Vorlage fehlt: {template}",
                template=str(template),
            )
        try:
            import cv2
        except ImportError:
            return ClickResolution(
                False,
                target,
                source="template",
                reason='OpenCV fehlt. Installiere: pip install -e ".[vision]"',
                template=str(template),
            )

        screen_image = cv2.imread(str(screenshot), cv2.IMREAD_COLOR)
        template_image = cv2.imread(str(template), cv2.IMREAD_COLOR)
        if screen_image is None or template_image is None:
            return ClickResolution(False, target, source="template", reason="Screenshot oder Vorlage ist kein lesbares Bild", template=str(template))

        offset_x = 0
        offset_y = 0
        region = step.get("search_region") or event.get("search_region")
        if region and len(region) == 4:
            offset_x, offset_y, width, height = [int(value) for value in region]
            screen_image = screen_image[offset_y : offset_y + height, offset_x : offset_x + width]

        sh, sw = screen_image.shape[:2]
        th, tw = template_image.shape[:2]
        if th > sh or tw > sw:
            return ClickResolution(False, target, source="template", reason="Vorlage ist größer als der Suchbereich", template=str(template))

        result = cv2.matchTemplate(screen_image, template_image, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(result)
        threshold = float(step.get("threshold", event.get("threshold", default_threshold)))
        if score < threshold:
            return ClickResolution(
                False,
                target,
                source="template",
                reason=f"Klickbedingung nicht gefunden: score={score:.4f}, threshold={threshold:.4f}",
                score=float(score),
                template=str(template),
            )
        x = offset_x + int(location[0]) + tw // 2
        y = offset_y + int(location[1]) + th // 2
        return ClickResolution(True, target, x, y, "template", score=float(score), template=str(template))


class ClickEventAbort(RuntimeError):
    pass


class PauseController:
    def __init__(self, config: dict, device: ADBDevice, registry: ClickEventRegistry):
        self.config = config
        self.device = device
        self.registry = registry
        self.pause_state = expand_path(config.get("pause_state_file", "runtime/pause-state.json"))

    def _write_state(self, task: dict, step: dict, resolution: ClickResolution, screenshot: Path) -> None:
        write_json(
            self.pause_state,
            {
                "version": VERSION,
                "status": "paused",
                "time": time.time(),
                "task_id": task.get("id"),
                "task_name": task.get("name"),
                "step": step,
                "resolution": asdict(resolution),
                "screenshot": str(screenshot),
                "commands": {
                    "desktop": "./pns-bot screenshot --destination Desktop",
                    "userhome": "./pns-bot screenshot --destination Userhome",
                    "coordinate": f"./pns-bot click-event set {resolution.target} --x X --y Y",
                },
            },
        )

    def clear(self) -> None:
        if self.pause_state.exists():
            self.pause_state.unlink()

    def _capture_and_resolve(self, step: dict) -> tuple[Path, ClickResolution]:
        screenshot = capture_runtime(self.device, self.config.get("screenshots_dir"), prefix="click-event")
        return screenshot, self.registry.resolve(
            step,
            screenshot,
            float(self.config.get("click_match_threshold", 0.86)),
        )

    def pause(self, task: dict, step: dict, initial_screenshot: Path, initial: ClickResolution) -> ClickResolution:
        self._write_state(task, step, initial, initial_screenshot)
        log("PAUSED", f"{task.get('id')}: {initial.reason}", WARN)
        print("\nKlick-Event wurde pausiert. Verfügbare Wege:")
        print("  ./pns-bot screenshot --destination Desktop")
        print("  ./pns-bot screenshot --destination Userhome")
        print(f"  ./pns-bot click-event set {initial.target} --x X --y Y")
        print(f"  PNG-Ziel: {initial.template or f'assets/click-events/{safe_event_name(initial.target)}.png'}\n")

        poll = max(0.5, float(self.config.get("pause_poll_seconds", 3)))
        timeout = float(self.config.get("pause_timeout_seconds", 0) or 0)
        started = time.time()

        if not sys.stdin.isatty():
            log("PAUSED", "Nicht-interaktiver Modus: Registry/PNG wird regelmäßig erneut geprüft", WARN)
            while timeout <= 0 or time.time() - started < timeout:
                time.sleep(poll)
                screenshot, resolution = self._capture_and_resolve(step)
                self._write_state(task, step, resolution, screenshot)
                if resolution.resolved:
                    self.clear()
                    log("RESUME", f"{resolution.target} via {resolution.source}", GREEN)
                    return resolution
            raise ClickEventAbort("Pause-Timeout erreicht")

        while True:
            command = input("paused> ").strip()
            lower = command.lower()
            if lower in ("help", "?"):
                print("retry | screenshot Desktop | screenshot Userhome | coords X Y | skip | abort")
                continue
            if lower.startswith("screenshot "):
                destination = command.split(maxsplit=1)[1]
                try:
                    capture_destination(self.device, destination)
                except Exception as exc:
                    log("SCREENSHOT", exc, BAD)
                continue
            if lower.startswith("coords "):
                parts = command.split()
                if len(parts) != 3:
                    print("Syntax: coords X Y")
                    continue
                self.registry.set_coordinate(initial.target, int(parts[1]), int(parts[2]))
                screenshot, resolution = self._capture_and_resolve(step)
                if resolution.resolved:
                    self.clear()
                    log("RESUME", f"{resolution.target} via {resolution.source}", GREEN)
                    return resolution
                self._write_state(task, step, resolution, screenshot)
                continue
            if lower == "retry" or lower == "":
                screenshot, resolution = self._capture_and_resolve(step)
                if resolution.resolved:
                    self.clear()
                    log("RESUME", f"{resolution.target} via {resolution.source}", GREEN)
                    return resolution
                self._write_state(task, step, resolution, screenshot)
                log("PAUSED", resolution.reason, WARN)
                continue
            if lower == "skip":
                self.clear()
                return ClickResolution(False, initial.target, source="manual", reason="manuell übersprungen", skipped=True)
            if lower in ("abort", "quit", "exit"):
                self.clear()
                raise ClickEventAbort(f"Klick-Event abgebrochen: {initial.target}")
            print("Unbekannt. Nutze: retry | screenshot Desktop | screenshot Userhome | coords X Y | skip | abort")
