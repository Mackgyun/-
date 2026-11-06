"""SQLite 저장소. 한 프로세스 안에서 여러 스레드가 공유한다."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
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
-- 기자별 '확인 완료' (받은편지함 비우기)
CREATE TABLE IF NOT EXISTS triage (
  user_id INTEGER NOT NULL REFERENCES users(id),
  rcept_no TEXT NOT NULL,
  done_at TEXT NOT NULL,
  PRIMARY KEY (user_id, rcept_no)
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
-- 알리오
CREATE TABLE IF NOT EXISTS alio_orgs (
  apba_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  inst_type TEXT,
  dept TEXT,
  resolved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alio_finance (
  disclosure_no TEXT PRIMARY KEY,
  apba_id TEXT NOT NULL,
  org_name TEXT NOT NULL,
  item_name TEXT NOT NULL,
  title TEXT,
  idate TEXT,
  table_json TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);
-- 보도자료 메일 (기자 본인만)
CREATE TABLE IF NOT EXISTS mail_accounts (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  host TEXT NOT NULL,
  username TEXT NOT NULL,
  secret_enc TEXT NOT NULL,
  folder TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  last_uid INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mails (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  uid INTEGER NOT NULL,
  sender TEXT,
  subject TEXT,
  sent_at TEXT,
  embargo TEXT,
  body TEXT,
  summary TEXT,
  first_seen_at TEXT NOT NULL,
  UNIQUE(user_id, uid)
);
-- 자사 기사 (스타일북·유사 기사 검색용)
CREATE TABLE IF NOT EXISTS articles (
  idxno INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  author_id TEXT,
  section TEXT,
  published_at TEXT,
  body TEXT NOT NULL,
  url TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(title, body, tokenize='trigram');
CREATE TABLE IF NOT EXISTS stylebooks (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  content TEXT NOT NULL,
  source_count INTEGER NOT NULL DEFAULT 0,
  model TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  source_kind TEXT NOT NULL,      -- disclosure | mail | text
  source_ref TEXT,
  source_title TEXT,
  source_text TEXT NOT NULL,
  draft TEXT NOT NULL,
  checks_json TEXT NOT NULL,
  examples_json TEXT NOT NULL,
  model TEXT,
  created_at TEXT NOT NULL
);
-- 질문 답변
CREATE TABLE IF NOT EXISTS chats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  trace_json TEXT NOT NULL,
  model TEXT,
  created_at TEXT NOT NULL
);
-- 정기 브리핑 (하루 3~4회, 조용히)
CREATE TABLE IF NOT EXISTS briefings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slot TEXT UNIQUE NOT NULL,
  content TEXT NOT NULL,
  model TEXT,
  created_at TEXT NOT NULL
);
-- AI 사용량 (비용 한도·월간 리포트)
CREATE TABLE IF NOT EXISTS llm_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  at TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  purpose TEXT NOT NULL,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  cost_krw REAL NOT NULL
);
"""

# 기존 DB에 나중에 추가한 열 (없으면 ALTER TABLE)
MIGRATIONS = [
    ("disclosures", "source", "TEXT NOT NULL DEFAULT 'dart'"),
    ("disclosures", "link", "TEXT"),
    ("claims", "written_url", "TEXT"),
    ("claims", "written_at", "TEXT"),
    ("users", "reporter_id", "TEXT"),
    ("users", "monthly_limit_krw", "INTEGER"),
    # 알림 발송 여부 (아웃박스). 기존 공시는 이미 처리된 것으로 본다.
    ("disclosures", "alerted_at", "TEXT"),
]
BACKFILL = {
    ("disclosures", "alerted_at"): "UPDATE disclosures SET alerted_at='migrated' WHERE alerted_at IS NULL",
}
EVENT_KEEP_DAYS = 120


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
            for table, column, decl in MIGRATIONS:
                cols = {r[1] for r in self._conn.execute(f"PRAGMA table_info({table})")}
                if column not in cols:
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
                    if (table, column) in BACKFILL:
                        self._conn.execute(BACKFILL[(table, column)])
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_disc_pending ON disclosures(alerted_at) "
                               "WHERE alerted_at IS NULL")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_kind_at ON events(kind, at)")

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
        with self._lock:
            cur = self._conn.execute("INSERT INTO events(at, kind, detail) VALUES(?,?,?)",
                                     (now_iso(), kind, detail[:2000]))
            # 시범사업 지표(가동률·알림 수)를 기간으로 계산하므로 건수가 아니라 기간으로 보관한다
            if cur.lastrowid % 200 == 0:
                cutoff = (now() - timedelta(days=EVENT_KEEP_DAYS)).isoformat(timespec="seconds")
                self._conn.execute("DELETE FROM events WHERE at < ?", (cutoff,))

    def backup(self, dest: Path | str) -> Path:
        """실행 중에도 안전한 복사본(VACUUM INTO). WAL 파일을 그대로 복사하면 깨질 수 있다."""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        with self._lock:
            self._conn.execute("VACUUM INTO ?", (str(dest),))
        return dest
