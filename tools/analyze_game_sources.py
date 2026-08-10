#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

URL_RE = re.compile(rb"https?://[^\x00-\x20\"'<>\\]{4,500}")
TEXT_URL_RE = re.compile(r"https?://[^\s\"'<>\\]{4,1000}")
RESOURCE_RE = re.compile(r"(?:src|href)=[\"']([^\"']+)[\"']", re.IGNORECASE)
DOWNLOAD_RE = re.compile(r"https?://[^\s\"'<>]+\.(?:apk|xapk|exe|msi|dmg|zip)(?:\?[^\s\"'<>]*)?", re.IGNORECASE)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".svg"}
BUNDLE_EXTS = {".bundle", ".unity3d", ".ab", ".assetbundle", ".pak", ".obb", ".cpk", ".bytes", ".bin"}
TEXT_EXTS = {".json", ".txt", ".xml", ".ini", ".cfg", ".conf", ".js", ".css", ".html", ".htm", ".lua", ".plist", ".manifest"}
ENGINE_MARKERS = {
    "unity": ["libunity.so", "globalgamemanagers", "assets/bin/data", "streamingassets", "addressables", "unitybuiltinshaders"],
    "cocos": ["libcocos", "assets/src/", "assets/res/", "project.json", "main.jsc", "main.js"],
    "unreal": ["libue4.so", ".pak", "ue4game", "unrealengine"],
}
PATH_HINTS = [
    "persistentdatapath", "streamingassets", "assetbundle", "addressable", "download", "hotupdate",
    "files/", "cache/", "externalfiles", "android/data", "resources", "cdn", "patch", "version",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_url(raw: bytes) -> str:
    value = raw.decode("utf-8", errors="replace").replace("\\/", "/")
    return html.unescape(value).rstrip(".,;)]}")


def scan_binary_strings(data: bytes, entry: str, url_hits: dict[str, set[str]], hint_hits: list[dict]) -> None:
    for match in URL_RE.finditer(data):
        url = decode_url(match.group(0))
        if len(url) <= 1000:
            url_hits[url].add(entry)
    lower = data.lower()
    for hint in PATH_HINTS:
        needle = hint.encode("ascii")
        pos = lower.find(needle)
        if pos >= 0:
            start = max(0, pos - 120)
            end = min(len(data), pos + len(needle) + 240)
            context = data[start:end].decode("utf-8", errors="replace")
            context = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in context)
            hint_hits.append({"entry": entry, "hint": hint, "context": re.sub(r"\s+", " ", context)[:360]})


def sample_zip_entry(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    # Full scan for normal files. Very large files get first/last samples to keep the job bounded.
    limit = 32 * 1024 * 1024
    with zf.open(info) as handle:
        if info.file_size <= limit:
            return handle.read()
        head = handle.read(8 * 1024 * 1024)
    # zipfile does not offer cheap tail seeks on compressed streams; head is enough for path/URL markers.
    return head


def analyze_apk(path: Path) -> dict:
    result: dict = {
        "path": str(path),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
        "zip": zipfile.is_zipfile(path),
    }
    if not result["zip"]:
        return result

    prefix_counts = collections.Counter()
    extension_counts = collections.Counter()
    extension_bytes = collections.Counter()
    largest = []
    image_entries = []
    bundle_candidates = []
    marker_entries = []
    url_hits: dict[str, set[str]] = collections.defaultdict(set)
    hint_hits: list[dict] = []
    all_names_lower = []
    total_uncompressed = 0
    total_compressed = 0

    with zipfile.ZipFile(path) as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        for info in infos:
            name = info.filename.replace("\\", "/")
            low = name.lower()
            all_names_lower.append(low)
            parts = [part for part in name.split("/") if part]
            prefix = "/".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "")
            prefix_counts[prefix] += 1
            ext = Path(name).suffix.lower() or "<none>"
            extension_counts[ext] += 1
            extension_bytes[ext] += info.file_size
            total_uncompressed += info.file_size
            total_compressed += info.compress_size
            largest.append((info.file_size, info.compress_size, name))
            if ext in IMAGE_EXTS:
                image_entries.append(name)
            if ext in BUNDLE_EXTS or any(token in low for token in ("assetbundle", "streamingassets", "addressable", "/assets/aa/")):
                bundle_candidates.append(name)
            if any(token in low for token in ("assets/", "res/raw", "streamingassets", "bundle", "patch", "download", "resource", "version", "cdn")):
                marker_entries.append(name)

            should_scan = (
                ext in TEXT_EXTS
                or info.file_size <= 4 * 1024 * 1024
                or any(token in low for token in ("manifest", "config", "version", "url", "cdn", "bundle", "resource", "patch"))
            )
            if should_scan:
                try:
                    scan_binary_strings(sample_zip_entry(zf, info), name, url_hits, hint_hits)
                except (OSError, RuntimeError, zipfile.BadZipFile):
                    pass

    engines = {}
    joined = "\n".join(all_names_lower)
    for engine, markers in ENGINE_MARKERS.items():
        hits = [marker for marker in markers if marker in joined]
        engines[engine] = {"detected": bool(hits), "markers": hits}

    largest.sort(reverse=True)
    ext_rows = sorted(
        ({"extension": ext, "count": extension_counts[ext], "bytes": extension_bytes[ext]} for ext in extension_counts),
        key=lambda row: (row["bytes"], row["count"]),
        reverse=True,
    )
    result.update(
        {
            "file_count": sum(prefix_counts.values()),
            "total_uncompressed": total_uncompressed,
            "total_compressed_entries": total_compressed,
            "engines": engines,
            "prefix_counts": prefix_counts.most_common(250),
            "extensions": ext_rows[:250],
            "largest_entries": [
                {"name": name, "size": size, "compressed": compressed}
                for size, compressed, name in largest[:250]
            ],
            "image_entry_count": len(image_entries),
            "image_entries": image_entries[:10000],
            "bundle_candidate_count": len(bundle_candidates),
            "bundle_candidates": bundle_candidates[:10000],
            "asset_marker_entries": marker_entries[:10000],
            "urls": [
                {"url": url, "entries": sorted(entries)[:30]}
                for url, entries in sorted(url_hits.items())
            ][:3000],
            "path_hint_hits": hint_hits[:3000],
        }
    )
    return result


def fetch_text(url: str, timeout: int = 30) -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/javascript,text/css,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        raw = response.read(8 * 1024 * 1024)
        charset = response.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace"), final_url


def normalize_text(text: str) -> str:
    return html.unescape(text.replace("\\/", "/").replace("\\u002F", "/"))


def analyze_site(url: str) -> dict:
    html_text, final_url = fetch_text(url)
    resources = []
    downloads = set(DOWNLOAD_RE.findall(normalize_text(html_text)))
    urls = set(TEXT_URL_RE.findall(normalize_text(html_text)))
    fetched = []
    seen = set()

    for ref in RESOURCE_RE.findall(html_text):
        absolute = urllib.parse.urljoin(final_url, html.unescape(ref))
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if not parsed.path.lower().endswith((".js", ".css")):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        resources.append(absolute)

    for resource in resources[:80]:
        try:
            text, resolved = fetch_text(resource)
        except Exception as exc:
            fetched.append({"url": resource, "error": str(exc)})
            continue
        normalized = normalize_text(text)
        found_downloads = sorted(set(DOWNLOAD_RE.findall(normalized)))
        found_urls = sorted(set(TEXT_URL_RE.findall(normalized)))
        downloads.update(found_downloads)
        urls.update(found_urls)
        fetched.append(
            {
                "url": resource,
                "resolved": resolved,
                "chars": len(text),
                "download_urls": found_downloads[:500],
                "url_count": len(found_urls),
            }
        )

    return {
        "url": url,
        "final_url": final_url,
        "html_chars": len(html_text),
        "resource_urls": resources,
        "fetched_resources": fetched,
        "download_urls": sorted(downloads),
        "all_urls": sorted(urls)[:5000],
    }


def inspect_client(download_urls: list[str], out_dir: Path) -> dict:
    exe_urls = [url for url in download_urls if re.search(r"\.(exe|msi)(?:\?|$)", url, re.IGNORECASE)]
    if not exe_urls:
        return {"status": "no-windows-client-url-found"}
    url = exe_urls[0]
    target = out_dir / "official-client.bin"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    except Exception as exc:
        return {"status": "download-failed", "url": url, "error": str(exc)}

    report = {
        "status": "downloaded",
        "url": url,
        "path": str(target),
        "size": target.stat().st_size,
        "sha256": sha256_file(target),
    }
    extract_dir = out_dir / "official-client-extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            ["7z", "x", "-y", f"-o{extract_dir}", str(target)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            check=False,
        )
        report["seven_zip_returncode"] = proc.returncode
        report["seven_zip_output_tail"] = proc.stdout[-12000:]
    except Exception as exc:
        report["seven_zip_error"] = str(exc)
        return report

    files = [path for path in extract_dir.rglob("*") if path.is_file()]
    report["extracted_file_count"] = len(files)
    report["largest_extracted"] = [
        {"path": str(path.relative_to(extract_dir)), "size": path.stat().st_size}
        for path in sorted(files, key=lambda item: item.stat().st_size, reverse=True)[:250]
    ]
    interesting = []
    for path in files:
        low = str(path.relative_to(extract_dir)).lower()
        if any(token in low for token in ("asar", "resource", "asset", "bundle", "data", "config", "package.json", "unity", "cocos", "download")):
            interesting.append(str(path.relative_to(extract_dir)))
    report["interesting_paths"] = interesting[:5000]
    return report


def markdown_report(report: dict) -> str:
    apk = report.get("apk", {})
    site = report.get("site", {})
    client = report.get("client", {})
    lines = ["# PNS game source analysis", ""]
    if apk:
        lines += [
            "## APK",
            f"- Size: {apk.get('size')} bytes",
            f"- SHA-256: `{apk.get('sha256', '')}`",
            f"- Entries: {apk.get('file_count', 0)}",
            f"- Image entries: {apk.get('image_entry_count', 0)}",
            f"- Bundle candidates: {apk.get('bundle_candidate_count', 0)}",
            f"- Engines: `{json.dumps(apk.get('engines', {}), ensure_ascii=False)}`",
            "",
            "### Largest APK entries",
        ]
        for item in apk.get("largest_entries", [])[:40]:
            lines.append(f"- `{item['name']}` — {item['size']} bytes")
        lines += ["", "### APK asset/bundle candidates"]
        for name in apk.get("bundle_candidates", [])[:100]:
            lines.append(f"- `{name}`")
        lines += ["", "### APK URLs"]
        for item in apk.get("urls", [])[:100]:
            lines.append(f"- `{item['url']}` — {', '.join(item['entries'][:3])}")
    if site:
        lines += ["", "## Official website", f"- Final URL: `{site.get('final_url')}`", "", "### Download URLs"]
        for url in site.get("download_urls", [])[:100]:
            lines.append(f"- `{url}`")
    if client:
        lines += ["", "## Official Windows client", f"- Status: `{client.get('status')}`"]
        if client.get("url"):
            lines.append(f"- URL: `{client['url']}`")
        if client.get("size"):
            lines.append(f"- Size: {client['size']} bytes")
        lines += ["", "### Interesting extracted paths"]
        for name in client.get("interesting_paths", [])[:150]:
            lines.append(f"- `{name}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--site-url", default="")
    parser.add_argument("--inspect-client", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    report = {}
    if args.apk:
        report["apk"] = analyze_apk(args.apk)
    if args.site_url:
        report["site"] = analyze_site(args.site_url)
        if args.inspect_client:
            report["client"] = inspect_client(report["site"].get("download_urls", []), args.out)

    (args.out / "analysis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "analysis.md").write_text(markdown_report(report), encoding="utf-8")
    print(args.out / "analysis.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
