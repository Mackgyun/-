"""비밀번호 해시, 세션, 초대 코드, 로그인 실패 제한."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from datetime import timedelta

from .db import Database, now, now_iso

SESSION_DAYS = 30
INVITE_DAYS = 7
MAX_FAILS = 5
LOCK_SECONDS = 600

_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return hmac.compare_digest(actual, expected)


def validate_password(password: str) -> str | None:
    if len(password) < 10:
        return "비밀번호는 10자 이상이어야 합니다."
    return None


class LoginLimiter:
    """아이디·IP별 연속 실패 5회면 10분 잠금 (메모리 기준)."""

    def __init__(self):
        self._fails: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def locked(self, key: str) -> bool:
        with self._lock:
            count, since = self._fails.get(key, (0, 0.0))
            if count >= MAX_FAILS and time.monotonic() - since < LOCK_SECONDS:
                return True
            if count >= MAX_FAILS:
                self._fails.pop(key, None)
            return False

    def fail(self, key: str) -> None:
        with self._lock:
            count, _ = self._fails.get(key, (0, 0.0))
            self._fails[key] = (count + 1, time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


def create_user(db: Database, username: str, display_name: str, password: str, role: str = "reporter") -> int:
    with db.tx() as c:
        cur = c.execute(
            "INSERT INTO users(username, display_name, pw_hash, role, created_at) VALUES(?,?,?,?,?)",
            (username.strip().lower(), display_name.strip(), hash_password(password), role, now_iso()),
        )
        return int(cur.lastrowid)


def authenticate(db: Database, username: str, password: str) -> dict | None:
    user = db.one("SELECT * FROM users WHERE username=? AND active=1", (username.strip().lower(),))
    if user and verify_password(password, user["pw_hash"]):
        return user
    # 존재하지 않는 아이디도 같은 시간이 걸리도록 해시 한 번 계산
    if not user:
        verify_password(password, hash_password("timing-equalizer"))
    return None


def create_session(db: Database, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = (now() + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds")
    db.execute("INSERT INTO sessions(token, user_id, expires_at) VALUES(?,?,?)", (token, user_id, expires))
    db.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),))
    return token


def session_user(db: Database, token: str | None) -> dict | None:
    if not token:
        return None
    return db.one(
        """SELECT u.id, u.username, u.display_name, u.role FROM sessions s
           JOIN users u ON u.id = s.user_id
           WHERE s.token=? AND s.expires_at > ? AND u.active=1""",
        (token, now_iso()),
    )


def delete_session(db: Database, token: str) -> None:
    db.execute("DELETE FROM sessions WHERE token=?", (token,))


def create_invite(db: Database, created_by: int | None, role: str = "reporter") -> str:
    code = secrets.token_urlsafe(12)
    expires = (now() + timedelta(days=INVITE_DAYS)).isoformat(timespec="seconds")
    db.execute(
        "INSERT INTO invites(code, role, created_by, created_at, expires_at) VALUES(?,?,?,?,?)",
        (code, role, created_by, now_iso(), expires),
    )
    return code


def redeem_invite(db: Database, code: str, username: str, display_name: str, password: str) -> int:
    """초대 코드로 가입. 실패하면 ValueError(사용자에게 보여줄 문구)."""
    problem = validate_password(password)
    if problem:
        raise ValueError(problem)
    if not username.strip() or not display_name.strip():
        raise ValueError("아이디와 이름을 입력하세요.")
    with db.tx() as c:
        inv = c.execute(
            "SELECT * FROM invites WHERE code=? AND used_by IS NULL AND expires_at > ?", (code, now_iso())
        ).fetchone()
        if not inv:
            raise ValueError("초대 링크가 만료됐거나 이미 사용됐습니다.")
        if c.execute("SELECT 1 FROM users WHERE username=?", (username.strip().lower(),)).fetchone():
            raise ValueError("이미 있는 아이디입니다.")
        cur = c.execute(
            "INSERT INTO users(username, display_name, pw_hash, role, created_at) VALUES(?,?,?,?,?)",
            (username.strip().lower(), display_name.strip(), hash_password(password), inv["role"], now_iso()),
        )
        user_id = int(cur.lastrowid)
        c.execute("UPDATE invites SET used_by=?, used_at=? WHERE code=?", (user_id, now_iso(), code))
        return user_id
