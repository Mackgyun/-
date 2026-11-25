"""웹 푸시 (PC 오른쪽 아래 팝업, 휴대폰 홈 화면 앱 알림)."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import logging
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from .db import Database, now, now_iso
from .rules import Rules

log = logging.getLogger(__name__)

# 브라우저 푸시 서비스 주소만 받는다 (임의 주소로 서버가 요청을 보내지 않게)
PUSH_HOSTS = ("fcm.googleapis.com", "android.googleapis.com", "updates.push.services.mozilla.com",
              "web.push.apple.com")
PUSH_HOST_SUFFIXES = (".push.services.mozilla.com", ".notify.windows.com", ".push.apple.com")
SUMMARY_OVER = 5  # 한 번에 이보다 많으면 기자별로 묶어 한 통만 보냄
DEVICE_ALERT_DAYS = 7  # PC 프로그램이 꺼져 있던 동안의 알림을 이 기간까지 보관


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _b64(value: str) -> bytes:
    value = value.strip()
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def validate_subscription(sub: dict) -> tuple[str, str, str]:
    """구독 정보를 검사해 (endpoint, p256dh, auth)를 돌려준다. 잘못되면 ValueError."""
    keys = sub.get("keys") or {}
    endpoint = str(sub.get("endpoint") or "").strip()
    p256dh, auth = str(keys.get("p256dh") or ""), str(keys.get("auth") or "")
    if not endpoint or not p256dh or not auth or len(endpoint) > 1000:
        raise ValueError("잘못된 구독 정보입니다.")
    u = urlparse(endpoint)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or not (host in PUSH_HOSTS or host.endswith(PUSH_HOST_SUFFIXES)):
        raise ValueError("지원하지 않는 알림 주소입니다. Chrome, Edge, Firefox, Safari에서 다시 설정하세요.")
    try:
        key, secret = _b64(p256dh), _b64(auth)
    except (ValueError, binascii.Error):
        raise ValueError("잘못된 구독 키입니다.") from None
    if len(key) != 65 or key[0] != 4 or len(secret) != 16:
        raise ValueError("잘못된 구독 키입니다.")
    return endpoint, p256dh, auth


class Pusher:
    def __init__(self, db: Database, data_dir: Path, contact: str, enabled: bool):
        self.db = db
        self.enabled = enabled
        self.contact = contact
        self.key_path = data_dir / "vapid_private.pem"
        if not self.key_path.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            v = Vapid()
            v.generate_keys()
            v.save_key(str(self.key_path))
        self.vapid = Vapid.from_file(str(self.key_path))

    @property
    def public_key(self) -> str:
        raw = self.vapid.public_key.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    def subscribe(self, user_id: int, sub: dict) -> None:
        endpoint, p256dh, auth = validate_subscription(sub)
        prev = self.db.one("SELECT user_id FROM push_subs WHERE endpoint=?", (endpoint,))
        if prev and prev["user_id"] != user_id:  # 같은 브라우저를 다른 기자가 쓰게 된 경우
            self.db.log("push", f"device moved user {prev['user_id']} -> {user_id}")
        self.db.execute(
            """INSERT INTO push_subs(endpoint, user_id, p256dh, auth, created_at) VALUES(?,?,?,?,?)
               ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id, p256dh=excluded.p256dh,
               auth=excluded.auth""",
            (endpoint, user_id, p256dh, auth, now_iso()),
        )

    def unsubscribe(self, endpoint: str) -> None:
        self.db.execute("DELETE FROM push_subs WHERE endpoint=?", (endpoint,))

    # --- PC 알림 프로그램 ------------------------------------------------
    def add_device(self, user_id: int, name: str) -> str:
        token = "nbd_" + secrets.token_urlsafe(32)
        self.db.execute("INSERT INTO devices(token_hash, user_id, name, created_at) VALUES(?,?,?,?)",
                        (_hash(token), user_id, name.strip()[:60] or "PC", now_iso()))
        return token

    def device_user(self, token: str | None) -> dict | None:
        if not token:
            return None
        row = self.db.one("""SELECT d.id device_id, d.name, u.id, u.username, u.display_name FROM devices d
                             JOIN users u ON u.id=d.user_id WHERE d.token_hash=? AND u.active=1""", (_hash(token),))
        if row:
            self.db.execute("UPDATE devices SET last_seen_at=? WHERE id=?", (now_iso(), row["device_id"]))
        return row

    def remove_device(self, user_id: int, device_id: int) -> int:
        return self.db.execute("DELETE FROM devices WHERE id=? AND user_id=?", (device_id, user_id))

    def devices(self, user_id: int) -> list[dict]:
        return self.db.query("SELECT id, name, created_at, last_seen_at FROM devices WHERE user_id=? ORDER BY id",
                             (user_id,))

    def last_alert_id(self, user_id: int) -> int:
        row = self.db.one("SELECT COALESCE(MAX(id), 0) m FROM device_alerts WHERE user_id=?", (user_id,))
        return int(row["m"])

    def device_alerts(self, user_id: int, after: int, limit: int = 50) -> list[dict]:
        rows = self.db.query("SELECT id, payload, created_at FROM device_alerts WHERE user_id=? AND id>? "
                             "ORDER BY id LIMIT ?", (user_id, after, limit))
        return [{"id": r["id"], "created_at": r["created_at"], **json.loads(r["payload"])} for r in rows]

    def _queue_for_devices(self, user_id: int, payload: dict) -> int:
        n = self.db.one("SELECT COUNT(*) n FROM devices WHERE user_id=?", (user_id,))["n"]
        if not n:
            return 0
        self.db.execute("INSERT INTO device_alerts(user_id, payload, created_at) VALUES(?,?,?)",
                        (user_id, json.dumps(payload, ensure_ascii=False), now_iso()))
        cutoff = (now() - timedelta(days=DEVICE_ALERT_DAYS)).isoformat(timespec="seconds")
        self.db.execute("DELETE FROM device_alerts WHERE created_at < ?", (cutoff,))
        return int(n)

    def send_to_user(self, user_id: int, payload: dict, force: bool = False) -> int:
        """동기 함수. 이벤트 루프에서는 스레드로 돌린다. 보낸 기기 수(브라우저 + PC 프로그램)를 돌려준다."""
        if not (self.enabled or force):
            return 0
        sent = self._queue_for_devices(user_id, payload)
        for s in self.db.query("SELECT * FROM push_subs WHERE user_id=?", (user_id,)):
            info = {"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}}
            try:
                webpush(
                    info,
                    json.dumps(payload, ensure_ascii=False),
                    vapid_private_key=self.vapid,
                    vapid_claims={"sub": self.contact},
                    ttl=3600,
                    timeout=10,
                )
                sent += 1
            except WebPushException as e:
                status = getattr(e.response, "status_code", None)
                if status in (404, 410):  # 브라우저가 구독을 버림
                    self.unsubscribe(s["endpoint"])
                else:
                    log.warning("push failed: %s", e)
                    self.db.log("error", f"push user {user_id}: {str(e)[:300]}")
            except Exception as e:  # noqa: BLE001 - 기기 하나의 문제로 다른 알림이 멈추지 않게
                log.warning("push failed: %r", e)
                self.db.log("error", f"push user {user_id}: {type(e).__name__}: {str(e)[:200]}")
        return sent


def recipients(db: Database, rules: Rules, row: dict) -> list[int]:
    """이 공시를 알림받을 사용자: 전체 구독, 기업 구독, 키워드 구독."""
    users = set()
    for s in db.query("SELECT s.user_id, s.kind, s.value FROM subscriptions s JOIN users u ON u.id=s.user_id WHERE u.active=1"):
        kind, value = s["kind"], s["value"]
        if kind == "all":
            users.add(s["user_id"])
        elif kind == "watch" and row.get("watched"):
            users.add(s["user_id"])
        elif kind == "company" and "".join(value.split()) == "".join(row["corp_name"].split()):
            users.add(s["user_id"])
        elif kind == "keyword" and "".join(value.split()) in "".join(row["report_nm"].split()):
            users.add(s["user_id"])
    return sorted(users)


def all_level_recipients(db: Database, row: dict) -> list[int]:
    """'모든 공시'로 이 회사를 구독한 사용자 (중요가 아닌 공시용)."""
    rows = db.query("""SELECT DISTINCT s.user_id FROM subscriptions s JOIN users u ON u.id=s.user_id
                       WHERE u.active=1 AND s.kind='company' AND s.levels='all' AND REPLACE(s.value,' ','')=?""",
                    ("".join(row["corp_name"].split()),))
    return sorted(r["user_id"] for r in rows)


def payload_for(row: dict, public_url: str) -> dict:
    return {
        "title": f"{row['corp_name']} · {'중요 공시' if row.get('level') == 'red' else '공시'}",
        "body": row["report_nm"],
        "url": f"{public_url}/#d/{row['rcept_no']}",
        "tag": row["rcept_no"],
    }


class Alerter:
    """알림 아웃박스. 저장된 공시 중 alerted_at 이 비어 있는 것을 보내고 표시한다.

    수집이 도중에 실패해도 이미 저장된 공시는 다음 회차에 보낸다. DART·알리오 루프가 함께 쓰므로 잠근다.
    """

    def __init__(self, db: Database, rules: Rules, pusher: Pusher, public_url: str, notify: bool):
        self.db, self.rules, self.pusher = db, rules, pusher
        self.public_url, self.notify = public_url, notify
        self._lock = asyncio.Lock()

    def mark_quiet(self, rcept_nos: list[str], reason: str) -> None:
        for r in rcept_nos:
            self.db.execute("UPDATE disclosures SET alerted_at=? WHERE rcept_no=? AND alerted_at IS NULL", (reason, r))

    async def flush(self) -> int:
        async with self._lock:
            pending = self.db.query("SELECT * FROM disclosures WHERE alerted_at IS NULL ORDER BY first_seen_at")
            if not pending:
                return 0
            targets = [r for r in pending if not r["is_correction"]]
            quiet = [r["rcept_no"] for r in pending if r["is_correction"]]
            self.mark_quiet(quiet, "skip")
            if not self.notify:
                self.mark_quiet([r["rcept_no"] for r in targets], "log")
                return 0
            per_user: dict[int, list[dict]] = {}
            for row in targets:
                # 중요 공시는 구독 조건 전체, 그 밖의 공시는 '모든 공시'로 기업을 구독한 사람에게만
                uids = recipients(self.db, self.rules, row) if row["level"] == "red" else all_level_recipients(self.db, row)
                for uid in uids:
                    per_user.setdefault(uid, []).append(row)
            for uid, rows in per_user.items():
                if len(rows) > SUMMARY_OVER:
                    payload = {"title": f"공시 {len(rows)}건", "body": " / ".join(r["corp_name"] for r in rows[:6]),
                               "url": f"{self.public_url}/#s/red", "tag": "batch"}
                    sent = await asyncio.to_thread(self.pusher.send_to_user, uid, payload)
                    self.db.log("alert", f"batch {len(rows)} -> user {uid} ({sent} devices)")
                    continue
                for row in rows:
                    sent = await asyncio.to_thread(self.pusher.send_to_user, uid, payload_for(row, self.public_url))
                    self.db.log("alert", f"{row['rcept_no']} -> user {uid} ({sent} devices)")
            self.mark_quiet([r["rcept_no"] for r in targets], now_iso())
            return len(targets)
