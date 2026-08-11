from __future__ import annotations

import os
import socket
import ssl
import time

from .util import WARN, log


class IRCRelay:
    def __init__(self, config: dict):
        self.config = config or {}
        self.socket = None
        self.sent: list[float] = []

    def enabled(self) -> bool:
        return bool(self.config.get("enabled", False))

    def password(self) -> str:
        return os.environ.get(self.config.get("password_env", "IRC_PASSWORD"), "") or self.config.get("password", "")

    def raw(self, line: str) -> None:
        if self.socket:
            self.socket.sendall((line + "\r\n").encode("utf-8", errors="replace"))

    def connect(self) -> None:
        if self.socket or not self.enabled():
            return
        raw = socket.create_connection((self.config["server"], int(self.config["port"])), timeout=15)
        try:
            if self.config.get("use_tls"):
                context = ssl.create_default_context() if self.config.get("tls_verify") else ssl._create_unverified_context()
                self.socket = context.wrap_socket(raw, server_hostname=self.config.get("server"))
            else:
                self.socket = raw
        except Exception:
            raw.close()
            raise
        if self.password():
            self.raw("PASS " + self.password())
        self.raw("NICK " + self.config.get("nick", "PNSWulf"))
        self.raw("USER %s 0 * :%s" % (self.config.get("username", "pns-wulf"), self.config.get("realname", "PNS-Wulf Relay")))
        time.sleep(1)
        for channel in self.config.get("channels", []):
            self.raw("JOIN " + channel)

    def send(self, message: str) -> None:
        if not self.enabled():
            return
        now = time.time()
        self.sent = [stamp for stamp in self.sent if now - stamp < 60]
        if len(self.sent) >= int(self.config.get("rate_limit_messages_per_minute", 90)):
            return
        try:
            self.connect()
            message = str(message)[: int(self.config.get("message_max_len", 390))]
            for channel in self.config.get("channels", []):
                self.raw(f"PRIVMSG {channel} :{message}")
            self.sent.append(now)
        except Exception as exc:
            log("IRC WARN", exc, WARN)
            try:
                if self.socket:
                    self.socket.close()
            finally:
                self.socket = None
