from __future__ import annotations

import re
from pathlib import Path

from .paths import PROJECT_ROOT, expand_path

_REGION_SPLIT = re.compile(r"[,:xX;\s]+")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


def parse_region(value: str | None) -> tuple[int, int, int, int] | None:
    """Parse x,y,width,height. Empty input means interactive selection."""
    if not value:
        return None
    parts = [part for part in _REGION_SPLIT.split(str(value).strip()) if part]
    if len(parts) != 4:
        raise ValueError("Region muss x,y,width,height enthalten")
    region = tuple(int(part) for part in parts)
    if region[2] <= 0 or region[3] <= 0:
        raise ValueError("Region braucht positive Breite und Höhe")
    return region


def _safe_name(value: str) -> str:
    name = _SAFE_NAME.sub("_", str(value or "").strip()).strip("._")
    if not name:
        raise ValueError("Event-Name ist leer")
    return name


def _require_pillow():
    try:
        from PIL import Image, ImageTk
    except ImportError as exc:
        raise RuntimeError('Bildauswahl benötigt Pillow. Installiere: pip install -e ".[vision]"') from exc
    return Image, ImageTk


def _normalize_region(region: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    x, y, w, h = [int(value) for value in region]
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    w = min(w, width - x)
    h = min(h, height - y)
    if w <= 0 or h <= 0:
        raise ValueError("Auswahl liegt außerhalb des Screenshots")
    return x, y, w, h


def select_region(screenshot: str | Path) -> tuple[int, int, int, int]:
    """Open a small Tk crop window and return x,y,width,height in original pixels."""
    source = expand_path(screenshot)
    if not source.exists():
        raise FileNotFoundError(source)

    Image, ImageTk = _require_pillow()
    try:
        import tkinter as tk
    except ImportError as exc:
        raise RuntimeError("Tkinter fehlt. Nutze --region x,y,width,height als Fallback.") from exc

    image = Image.open(source).convert("RGB")
    max_width, max_height = 1400, 820
    scale = min(1.0, max_width / image.width, max_height / image.height)
    display = image
    if scale < 1.0:
        display = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.Resampling.LANCZOS,
        )

    try:
        root = tk.Tk()
    except Exception as exc:
        raise RuntimeError("Kein GUI-Display verfügbar. Nutze --region x,y,width,height als Fallback.") from exc

    root.title("PNS-Wulf: Bildbereich auswählen – ziehen, Enter speichern, Esc abbrechen")
    canvas = tk.Canvas(root, width=display.width, height=display.height, cursor="crosshair", highlightthickness=0)
    canvas.pack()
    photo = ImageTk.PhotoImage(display)
    canvas.create_image(0, 0, anchor="nw", image=photo)
    state: dict[str, object] = {"start": None, "rect": None, "region": None}

    def point(event):
        return max(0, min(event.x, display.width - 1)), max(0, min(event.y, display.height - 1))

    def on_down(event):
        state["start"] = point(event)
        if state["rect"] is not None:
            canvas.delete(state["rect"])
        x, y = state["start"]
        state["rect"] = canvas.create_rectangle(x, y, x, y, outline="red", width=2)

    def on_move(event):
        if state["start"] is None or state["rect"] is None:
            return
        x0, y0 = state["start"]
        x1, y1 = point(event)
        canvas.coords(state["rect"], x0, y0, x1, y1)

    def on_up(event):
        if state["start"] is None:
            return
        x0, y0 = state["start"]
        x1, y1 = point(event)
        left, top = min(x0, x1), min(y0, y1)
        right, bottom = max(x0, x1), max(y0, y1)
        if right <= left or bottom <= top:
            state["region"] = None
            return
        state["region"] = (
            round(left / scale),
            round(top / scale),
            max(1, round((right - left) / scale)),
            max(1, round((bottom - top) / scale)),
        )

    def accept(_event=None):
        if state["region"] is not None:
            root.quit()

    def cancel(_event=None):
        state["region"] = None
        root.quit()

    canvas.bind("<ButtonPress-1>", on_down)
    canvas.bind("<B1-Motion>", on_move)
    canvas.bind("<ButtonRelease-1>", on_up)
    root.bind("<Return>", accept)
    root.bind("<Escape>", cancel)
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.mainloop()
    root.destroy()

    region = state["region"]
    if region is None:
        raise RuntimeError("Bildauswahl abgebrochen")
    return _normalize_region(region, image.width, image.height)


def crop_template(
    screenshot: str | Path,
    event_name: str,
    region: tuple[int, int, int, int] | None = None,
    destination: str | Path | None = None,
) -> tuple[Path, tuple[int, int, int, int], tuple[int, int]]:
    """Crop a screenshot region into the click-event assets directory."""
    source = expand_path(screenshot)
    if not source.exists():
        raise FileNotFoundError(source)
    Image, _ = _require_pillow()
    image = Image.open(source).convert("RGB")
    selected = region or select_region(source)
    selected = _normalize_region(selected, image.width, image.height)
    x, y, w, h = selected

    target = expand_path(destination) if destination else PROJECT_ROOT / "assets" / "click-events" / f"{_safe_name(event_name)}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image.crop((x, y, x + w, y + h)).save(target, format="PNG", optimize=True)
    return target, selected, (image.width, image.height)
