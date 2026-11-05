"""SQLite 저장소. 한 프로세스 안에서 여러 스레드가 공유한다."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .config import KST

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  pw_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'reporter',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invites (
  code TEXT PRIMARY KEY,
  role TEXT NOT NULL DEFAULT 'reporter',
  created_by INTEGER,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_by INTEGER,
  used_at TEXT
);
CREATE TABLE IF NOT EXISTS subscriptions (
  user_id INTEGER NOT NULL REFERENCES users(id),
  kind TEXT NOT NULL,           -- company | keyword | all
  value TEXT NOT NULL,
  PRIMARY KEY (user_id, kind, value)
);
CREATE TABLE IF NOT EXISTS companies (
  corp_code TEXT PRIMARY KEY,
  corp_name TEXT NOT NULL,
  induty_code TEXT,
  fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS disclosures (
  rcept_no TEXT PRIMARY KEY,
  corp_code TEXT NOT NULL,
  corp_name TEXT NOT NULL,
  stock_code TEXT,
  report_nm TEXT NOT NULL,
  rcept_dt TEXT NOT NULL,
  flr_nm TEXT,
  rm TEXT,
  level TEXT NOT NULL,
  keyword TEXT,
  is_correction INTEGER NOT NULL DEFAULT 0,
  watched INTEGER NOT NULL DEFAULT 0,
  first_seen_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_disc_seen ON disclosures(first_seen_at DESC);
CREATE TABLE IF NOT EXISTS claims (
  rcept_no TEXT PRIMARY KEY REFERENCES disclosures(rcept_no),
  user_id INTEGER NOT NULL REFERENCES users(id),
  claimed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS push_subs (
  endpoint TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  kind TEXT NOT NULL,           -- poll | error | alert | login ...
  detail TEXT
);
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


def now() -> datetime:
    return datetime.now(KST)


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(SCHEMA)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise

    def query(self, sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple | dict = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: tuple | dict = ()) -> int:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.rowcount

    # --- kv ---------------------------------------------------------------
    def get(self, key: str, default: str | None = None) -> str | None:
        row = self.one("SELECT value FROM kv WHERE key=?", (key,))
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        self.execute(
            "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def log(self, kind: str, detail: str = "") -> None:
        self.execute("INSERT INTO events(at, kind, detail) VALUES(?,?,?)", (now_iso(), kind, detail[:2000]))
        # 이벤트는 최근 5,000건만 보관
        self.execute("DELETE FROM events WHERE id <= (SELECT MAX(id) - 5000 FROM events)")
