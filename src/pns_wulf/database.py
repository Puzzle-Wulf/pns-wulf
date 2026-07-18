from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .paths import expand_path
from .util import GREEN, log


def safe_name(name: str) -> str:
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in str(name or "UNKNOWN"))


def open_character_db(config: dict, character: str):
    path = expand_path(config.get("character_db_dir", "runtime/characters")) / f"{safe_name(character)}.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("create table if not exists cooldowns(task_id text primary key, last_success real, next_run_at real, status text)")
    connection.execute("create table if not exists task_events(ts real, task_id text, event text, details text)")
    connection.commit()
    return connection, path


def cooldown_ready(connection, task_id: str) -> bool:
    row = connection.execute("select next_run_at from cooldowns where task_id=?", (task_id,)).fetchone()
    return not row or time.time() >= float(row[0])


def set_cooldown(connection, task_id: str, seconds: int) -> None:
    now = time.time()
    connection.execute("insert or replace into cooldowns values(?,?,?,?)", (task_id, now, now + int(seconds), "ok"))
    connection.execute("insert into task_events values(?,?,?,?)", (now, task_id, "success", json.dumps({"cooldown_seconds": seconds})))
    connection.commit()


def list_cooldowns(config: dict, character: str) -> None:
    connection, path = open_character_db(config, character)
    rows = connection.execute("select task_id,last_success,next_run_at,status from cooldowns order by next_run_at").fetchall()
    print("DB:", path)
    for task_id, _last, next_run, status in rows:
        formatted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_run))
        print(f"{task_id:32} status={status:8} next_run_at={formatted}")
    connection.close()


def finalize_character_db(connection, character: str) -> None:
    now = time.time()
    connection.execute("create table if not exists meta(key text primary key, value text)")
    connection.execute("insert or replace into meta values(?,?)", ("finalized_at", str(now)))
    connection.execute("insert or replace into meta values(?,?)", ("finalized_character", str(character)))
    connection.execute("insert into task_events values(?,?,?,?)", (now, "__character__", "finalized", json.dumps({"character": character})))
    connection.commit()
    connection.close()
    log("DB FINALIZE", f"{character}.db finalisiert", GREEN)
