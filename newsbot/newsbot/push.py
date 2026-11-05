"""웹 푸시 (PC 오른쪽 아래 팝업, 휴대폰 홈 화면 앱 알림)."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from .db import Database, now_iso
from .rules import Rules

log = logging.getLogger(__name__)


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
        keys = sub.get("keys") or {}
        if not sub.get("endpoint") or not keys.get("p256dh") or not keys.get("auth"):
            raise ValueError("잘못된 구독 정보")
        self.db.execute(
            """INSERT INTO push_subs(endpoint, user_id, p256dh, auth, created_at) VALUES(?,?,?,?,?)
               ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id, p256dh=excluded.p256dh,
               auth=excluded.auth""",
            (sub["endpoint"], user_id, keys["p256dh"], keys["auth"], now_iso()),
        )

    def unsubscribe(self, endpoint: str) -> None:
        self.db.execute("DELETE FROM push_subs WHERE endpoint=?", (endpoint,))

    def send_to_user(self, user_id: int, payload: dict, force: bool = False) -> int:
        """동기 함수. 이벤트 루프에서는 스레드로 돌린다. 보낸 기기 수를 돌려준다."""
        if not (self.enabled or force):
            return 0
        sent = 0
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
                    self.db.log("error", f"push: {e}")
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


def payload_for(row: dict, public_url: str) -> dict:
    return {
        "title": f"{row['corp_name']} · 중요 공시",
        "body": row["report_nm"],
        "url": f"{public_url}/#d/{row['rcept_no']}",
        "tag": row["rcept_no"],
    }
