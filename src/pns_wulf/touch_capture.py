from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .screenshots import capture_runtime


class TouchCaptureUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class TouchDeviceInfo:
    path: str
    min_x: int
    max_x: int
    min_y: int
    max_y: int
    name: str = ""
    direct: bool = False


_DEVICE_BLOCK = re.compile(
    r"add device \d+:\s*(?P<path>/dev/input/event\d+)\s*(?P<body>.*?)(?=add device \d+:|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_AXIS = {
    "x": re.compile(
        r"ABS_MT_POSITION_X\s*:\s*value\s+-?\d+,\s*min\s+(-?\d+),\s*max\s+(-?\d+)",
        re.IGNORECASE,
    ),
    "y": re.compile(
        r"ABS_MT_POSITION_Y\s*:\s*value\s+-?\d+,\s*min\s+(-?\d+),\s*max\s+(-?\d+)",
        re.IGNORECASE,
    ),
}
_NAME = re.compile(r'name:\s*"([^"]+)"', re.IGNORECASE)


def parse_touch_devices(listing: str) -> list[TouchDeviceInfo]:
    """Return direct multitouch devices exposed by `adb shell getevent -lp`."""
    devices: list[TouchDeviceInfo] = []
    for match in _DEVICE_BLOCK.finditer(listing or ""):
        body = match.group("body")
        x_match = _AXIS["x"].search(body)
        y_match = _AXIS["y"].search(body)
        if not x_match or not y_match:
            continue
        # INPUT_PROP_DIRECT strongly identifies a touchscreen. Some vendor builds
        # omit the property in getevent output, so MT axes are still accepted.
        name_match = _NAME.search(body)
        devices.append(
            TouchDeviceInfo(
                path=match.group("path"),
                min_x=int(x_match.group(1)),
                max_x=int(x_match.group(2)),
                min_y=int(y_match.group(1)),
                max_y=int(y_match.group(2)),
                name=name_match.group(1) if name_match else "",
                direct="INPUT_PROP_DIRECT" in body,
            )
        )
    devices.sort(key=lambda item: (not item.direct, item.path))
    return devices


def _hex_value(value: str) -> int:
    raw = value.strip().lower()
    number = int(raw, 16)
    if number == 0xFFFFFFFF:
        return -1
    return number


class MultiTouchState:
    """Parser for Linux multitouch protocol-B getevent lines."""

    def __init__(self):
        self.current_slot = 0
        self.slots: dict[int, dict[str, int]] = {}
        self._lock = threading.Lock()

    def feed(self, line: str) -> None:
        parts = str(line).strip().split()
        if "EV_ABS" not in parts or len(parts) < 2:
            return
        label = parts[-2]
        value = parts[-1]
        try:
            parsed = _hex_value(value)
        except ValueError:
            return

        with self._lock:
            if label == "ABS_MT_SLOT":
                self.current_slot = parsed
                return
            if label == "ABS_MT_TRACKING_ID":
                if parsed < 0:
                    self.slots.pop(self.current_slot, None)
                else:
                    self.slots.setdefault(self.current_slot, {})["tracking_id"] = parsed
                return

            slot = self.slots.setdefault(self.current_slot, {})
            if label == "ABS_MT_POSITION_X":
                slot["x"] = parsed
            elif label == "ABS_MT_POSITION_Y":
                slot["y"] = parsed

    def active_points(self) -> list[tuple[int, int, int]]:
        with self._lock:
            points = []
            for slot_id, state in sorted(self.slots.items()):
                if state.get("tracking_id", -1) >= 0 and "x" in state and "y" in state:
                    points.append((slot_id, state["x"], state["y"]))
            return points


def _scale_axis(value: int, minimum: int, maximum: int, pixels: int) -> int:
    if maximum <= minimum or pixels <= 1:
        raise ValueError("Ungültiger Touch-Achsenbereich")
    ratio = (int(value) - minimum) / (maximum - minimum)
    ratio = max(0.0, min(1.0, ratio))
    return round(ratio * (pixels - 1))


def region_from_touch_points(
    points: list[tuple[int, int, int]],
    info: TouchDeviceInfo,
    screenshot_size: tuple[int, int],
) -> tuple[tuple[int, int, int, int], list[tuple[int, int]]]:
    if len(points) < 2:
        raise ValueError("Für die Auswahl müssen zwei Finger gleichzeitig gehalten werden")
    width, height = screenshot_size
    mapped = [
        (
            _scale_axis(raw_x, info.min_x, info.max_x, width),
            _scale_axis(raw_y, info.min_y, info.max_y, height),
        )
        for _, raw_x, raw_y in points[:2]
    ]
    (x0, y0), (x1, y1) = mapped
    left, right = sorted((x0, x1))
    top, bottom = sorted((y0, y1))
    if right <= left or bottom <= top:
        raise ValueError("Die zwei Finger müssen gegenüberliegende Ecken eines Bereichs markieren")
    return (left, top, right - left + 1, bottom - top + 1), mapped


def capture_two_finger_region(
    device,
    screenshots_dir: str | Path | None = None,
    prefix: str = "task-touch-template",
) -> tuple[Path, tuple[int, int, int, int], dict]:
    """
    Observe two real fingers through getevent. The user holds both fingers and
    confirms with Enter on the host keyboard; the screenshot is taken while the
    fingers remain down.
    """
    listing = device.shell(["getevent", "-lp"], 10)
    if listing.returncode != 0:
        raise TouchCaptureUnavailable("getevent-Geräteliste ist über ADB nicht lesbar")
    devices = parse_touch_devices(listing.stdout)
    if not devices:
        raise TouchCaptureUnavailable("Kein Multitouch-Gerät mit ABS_MT_POSITION_X/Y gefunden")

    info = devices[0]
    state = MultiTouchState()
    process = device.stream_shell(["getevent", "-lt", info.path])

    def reader() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            state.feed(line)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        time.sleep(0.20)
        if process.poll() is not None:
            error = process.stderr.read().strip() if process.stderr else ""
            raise TouchCaptureUnavailable(
                "Live-Touchdaten sind nicht lesbar"
                + (f": {error}" if error else " (häufig fehlende /dev/input-Berechtigung)")
            )

        print(
            "Lege zwei Finger auf gegenüberliegende Ecken des gewünschten Bereichs, "
            "halte beide Finger liegen und drücke dann Enter am PC."
        )
        input("2-Finger-Auswahl> ")
        points = state.active_points()
        if len(points) < 2:
            raise TouchCaptureUnavailable(
                "Beim Bestätigen waren keine zwei gleichzeitig aktiven Touch-Punkte verfügbar"
            )

        screenshot = capture_runtime(device, screenshots_dir, prefix=prefix)
        try:
            from PIL import Image
        except ImportError as exc:
            raise TouchCaptureUnavailable(
                'Zwei-Finger-Capture benötigt Pillow. Installiere: pip install -e ".[vision]"'
            ) from exc

        with Image.open(screenshot) as image:
            screenshot_size = image.size
        region, mapped = region_from_touch_points(points, info, screenshot_size)
        metadata = {
            "method": "adb-getevent-two-finger",
            "touch_device": info.path,
            "touch_device_name": info.name,
            "touch_device_direct": info.direct,
            "raw_points": [[slot, x, y] for slot, x, y in points[:2]],
            "screenshot_points": [list(point) for point in mapped],
        }
        return screenshot, region, metadata
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except Exception:
                process.kill()
