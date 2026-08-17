from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath

from .util import GREEN, WARN, log, write_json

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:$")


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name or ""))


def safe_archive_path(name: str) -> str | None:
    """Normalize an archive member to a relative POSIX path or reject it."""
    normalized = str(name or "").replace("\\", "/").strip()
    if not normalized or normalized.startswith("/"):
        return None
    parts = PurePosixPath(normalized).parts
    if not parts or ".." in parts or _DRIVE_PREFIX.fullmatch(parts[0]):
        return None
    return "/".join(parts)


def list_sources(root: Path) -> list[Path]:
    sprite_dir = root / "sprites"
    sprite_dir.mkdir(exist_ok=True)
    names = [
        "pas.xapk",
        "pas.apkx",
        "pas.apk",
        "pns.xapk",
        "pns.apk",
        "PuzzleAndSurvival.xapk",
        "PuzzleAndSurvival.apk",
    ]
    found: list[Path] = []
    for name in names:
        path = sprite_dir / name
        if path.exists():
            found.append(path)
    # Also accept any apk/xapk/apkx dropped directly into /sprites.
    for path in sprite_dir.iterdir():
        if path.is_file() and path.suffix.lower() in (".xapk", ".apk", ".apkx") and path not in found:
            found.append(path)
    return found


def extract_zip(src: Path, dst: Path) -> int:
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(src, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = safe_archive_path(info.filename)
            if not name:
                continue
            target = dst / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            count += 1
    return count


def extract_images_from_archive(src: Path, dst: Path, index: list[dict]) -> None:
    try:
        with zipfile.ZipFile(src, "r") as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = safe_archive_path(info.filename)
                if not name:
                    continue
                ext = PurePosixPath(name).suffix.lower()
                if ext not in IMAGE_EXTS:
                    continue
                lname = name.lower()
                # Keep safe folder hints if present, otherwise flatten safely.
                if lname.startswith("pas/"):
                    rel = name
                elif "/pas/" in lname:
                    rel = name[lname.find("/pas/") + 1 :]
                elif any(term in lname for term in ("pas", "back", "menu", "dispatch", "search")):
                    rel = "pas/_auto/" + safe_name(name)
                else:
                    rel = "_all_images/" + safe_name(name)
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                index.append({"source": str(src), "entry": name, "target": str(target)})
    except zipfile.BadZipFile:
        return


def best_copy_back_arrow(root: Path, image_index: list[dict]) -> dict:
    assets_back = root / "assets" / "pas" / "menu" / "back.png"
    if assets_back.exists():
        return {"status": "exists", "path": str(assets_back)}
    candidates = []
    for item in image_index:
        low = (item.get("entry", "") + " " + item.get("target", "")).lower()
        if ("back" in low or "arrow" in low) and Path(item["target"]).suffix.lower() == ".png":
            score = 0
            if "back" in low:
                score += 10
            if "arrow" in low:
                score += 5
            if "menu" in low:
                score += 3
            candidates.append((score, item))
    if not candidates:
        return {"status": "missing", "path": str(assets_back)}
    candidates.sort(key=lambda item: item[0], reverse=True)
    chosen = Path(candidates[0][1]["target"])
    assets_back.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(chosen, assets_back)
    return {"status": "copied", "path": str(assets_back), "from": str(chosen)}


def ensure_pas_sprites(root: Path, _cfg: dict) -> dict:
    """
    Accepts raw /sprites/pas.xapk, /sprites/pas.apkx or /sprites/pas.apk.
    XAPK/APK is only a source archive. Runtime still uses extracted PNG/WEBP files.
    Existing config does not need to be recreated.
    """
    sprite_dir = root / "sprites"
    out_dir = sprite_dir / "_extracted"
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = list_sources(root)
    if not sources:
        log("SPRITES", "keine pas.xapk/pas.apkx/pas.apk in ./sprites gefunden", WARN)
        return {"sources": [], "images": [], "back_arrow": {"status": "missing"}}

    image_index: list[dict] = []
    source_rows: list[dict] = []
    for src in sources:
        log("SPRITES", f"Quelle gefunden: {src}", GREEN)
        raw_out = out_dir / src.stem
        try:
            extracted = extract_zip(src, raw_out)
        except zipfile.BadZipFile:
            log("SPRITES", f"kein ZIP/APK/XAPK Archiv: {src}", WARN)
            continue
        source_rows.append({"source": str(src), "raw_extract": str(raw_out), "files": extracted})

        # Extract images from the outer archive.
        extract_images_from_archive(src, sprite_dir, image_index)

        # XAPK usually contains APK files. Extract image files inside nested APKs too.
        for nested in raw_out.rglob("*"):
            if nested.is_file() and nested.suffix.lower() in (".apk", ".zip"):
                extract_images_from_archive(nested, sprite_dir, image_index)

    back = best_copy_back_arrow(root, image_index)
    report = {
        "sources": source_rows,
        "image_count": len(image_index),
        "images": image_index[:5000],
        "back_arrow": back,
        "expected_runtime_asset": str(root / "assets" / "pas" / "menu" / "back.png"),
    }
    write_json(sprite_dir / "SPRITE_EXTRACT_REPORT.json", report)
    log("SPRITES", f"Report: {sprite_dir / 'SPRITE_EXTRACT_REPORT.json'}", GREEN)
    log("SPRITES", f"Images extrahiert: {len(image_index)}", GREEN)
    log("SPRITES", f"back_arrow: {back.get('status')}", GREEN if back.get("status") != "missing" else WARN)
    return report
