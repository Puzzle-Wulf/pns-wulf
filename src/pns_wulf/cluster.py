from __future__ import annotations

import http.server
import json
import threading
import time
import urllib.request

from .util import GREEN, WARN, log


class HostState:
    def __init__(self, config: dict):
        self.config = config
        self.data = {"devices": {}, "events": []}


class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, code: int, payload: object) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        return json.loads(self.rfile.read(length).decode("utf-8", errors="replace")) if length else {}

    def do_GET(self):
        if self.path in ("/status", "/events"):
            return self._json(200, self.server.state.data)
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        data = self._body()
        state = self.server.state.data
        if self.path == "/connect":
            state["devices"][data.get("serial", "unknown")] = data
            state["events"].append({"kind": "connect", "data": data, "time": time.time()})
            return self._json(200, {"ok": True, "role": "host"})
        if self.path in ("/heartbeat", "/task/event", "/resource/request"):
            state["events"].append({"kind": self.path.strip("/"), "data": data, "time": time.time()})
            return self._json(200, {"ok": True})
        return self._json(404, {"error": "not found"})

    def log_message(self, *_args):
        pass


def can_reach(url: str) -> bool:
    try:
        urllib.request.urlopen(url.rstrip("/") + "/status", timeout=2)
        return True
    except Exception:
        return False


def start_host(config: dict):
    class Server(http.server.ThreadingHTTPServer):
        pass

    server = Server(("0.0.0.0", int(config.get("host_port", 8789))), Handler)
    server.state = HostState(config)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log("CLUSTER", "Host-Rolle aktiv; verwaltet Verbindungen und Events", GREEN)
    return server


def connect_host(config: dict, url_override: str | None = None) -> None:
    url = (url_override or config["host_url"]).rstrip("/") + "/connect"
    data = json.dumps(
        {
            "serial": config["serial"],
            "label": config["instance_label"],
            "account": config.get("account", ""),
        }
    ).encode()
    try:
        urllib.request.urlopen(
            urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}),
            timeout=5,
        ).read()
    except Exception as exc:
        log("CLUSTER", f"Verbindung fehlgeschlagen: {exc}", WARN)


def ensure_cluster(config: dict):
    if can_reach(config["host_url"]):
        connect_host(config)
        return None
    host = start_host(config)
    connect_host(config, f"http://127.0.0.1:{int(config.get('host_port', 8789))}")
    return host
