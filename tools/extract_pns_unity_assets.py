#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import zipfile
from collections import Counter
from pathlib import Path

PACKED_PREFIX = "assets/ABAsset.pkglzma_"
SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_name(value: str, fallback: str) -> str:
    name = SAFE.sub("_", str(value or "").strip()).strip("._")
    return name or fallback


def unpack_embedded_bundles(apk: Path, out_dir: Path, max_packages: int = 0) -> list[dict]:
    bundles_dir = out_dir / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    with zipfile.ZipFile(apk) as zf:
        names = sorted(
            (name for name in zf.namelist() if name.startswith(PACKED_PREFIX)),
            key=lambda name: int(name.rsplit("_", 1)[1]),
        )
        if max_packages > 0:
            names = names[:max_packages]
        for name in names:
            data = zf.read(name)
            if len(data) < 12:
                raise RuntimeError(f"{name}: Datei zu klein")
            declared = struct.unpack("<I", data[:4])[0]
            payload = data[4:]
            if declared != len(payload):
                raise RuntimeError(f"{name}: Header-Länge {declared} != Payload {len(payload)}")
            if not payload.startswith(b"UnityFS\x00"):
                raise RuntimeError(f"{name}: Payload beginnt nicht mit UnityFS")
            number = int(name.rsplit("_", 1)[1])
            target = bundles_dir / f"ABAsset.pkg_{number}.bundle"
            target.write_bytes(payload)
            rows.append(
                {
                    "source": name,
                    "package": number,
                    "declared_size": declared,
                    "bundle": str(target),
                    "unityfs": True,
                }
            )
    return rows


def export_unity_images(bundle_rows: list[dict], out_dir: Path, export_images: bool) -> dict:
    try:
        import UnityPy
    except ImportError as exc:
        raise RuntimeError("UnityPy fehlt. Installiere: python -m pip install UnityPy Pillow") from exc

    images_dir = out_dir / "images"
    if export_images:
        images_dir.mkdir(parents=True, exist_ok=True)
    type_counts = Counter()
    image_rows = []
    failures = []

    for row in bundle_rows:
        bundle = Path(row["bundle"])
        try:
            env = UnityPy.load(str(bundle))
        except Exception as exc:
            failures.append({"bundle": str(bundle), "stage": "load", "error": repr(exc)})
            continue
        for obj in env.objects:
            type_name = obj.type.name
            type_counts[type_name] += 1
            if type_name not in {"Texture2D", "Sprite"}:
                continue
            try:
                data = obj.read()
                obj_name = safe_name(getattr(data, "m_Name", ""), f"{type_name}_{obj.path_id}")
                entry = {
                    "bundle": bundle.name,
                    "package": row["package"],
                    "type": type_name,
                    "path_id": obj.path_id,
                    "name": obj_name,
                }
                if export_images:
                    image = data.image
                    folder = images_dir / f"pkg_{row['package']:02d}" / type_name
                    folder.mkdir(parents=True, exist_ok=True)
                    target = folder / f"{obj_name}__{obj.path_id}.png"
                    image.save(target)
                    entry["file"] = str(target)
                image_rows.append(entry)
            except Exception as exc:
                failures.append(
                    {
                        "bundle": bundle.name,
                        "type": type_name,
                        "path_id": obj.path_id,
                        "stage": "read/export",
                        "error": repr(exc),
                    }
                )

    return {
        "object_types": dict(type_counts.most_common()),
        "image_object_count": len(image_rows),
        "images": image_rows,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrahiert die in PNS-APK eingebetteten ABAsset.pkglzma_N als echte UnityFS-Bundles und optional Texture2D/Sprite-PNGs."
    )
    parser.add_argument("apk", type=Path)
    parser.add_argument("--out", type=Path, default=Path("runtime/pns-unity-assets"))
    parser.add_argument("--export-images", action="store_true", help="Texture2D und Sprite als PNG exportieren")
    parser.add_argument("--max-packages", type=int, default=0, help="0 = alle; sonst nur erste N Pakete")
    parser.add_argument("--no-unity-inventory", action="store_true", help="nur UnityFS-Dateien entpacken, nicht mit UnityPy öffnen")
    args = parser.parse_args()

    if not args.apk.exists():
        raise SystemExit(f"APK fehlt: {args.apk}")
    if not zipfile.is_zipfile(args.apk):
        raise SystemExit(f"Kein APK/ZIP: {args.apk}")

    args.out.mkdir(parents=True, exist_ok=True)
    bundles = unpack_embedded_bundles(args.apk, args.out, args.max_packages)
    report = {"apk": str(args.apk), "bundle_count": len(bundles), "bundles": bundles}
    if not args.no_unity_inventory:
        report["unity"] = export_unity_images(bundles, args.out, args.export_images)

    report_path = args.out / "extract-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Bundles: {len(bundles)}")
    if "unity" in report:
        unity = report["unity"]
        print(f"Texture2D/Sprite objects: {unity['image_object_count']}")
        print("Object types:", json.dumps(unity["object_types"], ensure_ascii=False, sort_keys=True))
        if unity["failures"]:
            print(f"Failures: {len(unity['failures'])}", file=sys.stderr)
    print(report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
