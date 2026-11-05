"""보도자료 메일 브리핑 (기자 본인만 봄).

- 기본은 꺼져 있음(MAIL_ENABLED=false). 개인정보 국외 이전 등 법무·IT 검토 후 켠다.
- 기자가 지정한 메일함(라벨) 하나만 읽기 전용으로 연다(EXAMINE, BODY.PEEK: 읽음 표시도 안 바뀜).
- 비밀번호(앱 비밀번호)는 data/secret.key 로 암호화해 저장한다.
- AI 요약은 MAIL_AI_SUMMARY=true 일 때만 (메일 본문이 해외 AI API로 나가기 때문).
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from pathlib import Path

from cryptography.fernet import Fernet

from .config import KST
from .db import Database, now_iso

log = logging.getLogger(__name__)
EMBARGO = re.compile(r"(엠바고|보도\s*시점|보도\s*일시|보도\s*가능|보도\s*유예)[^\n]{0,60}")


class Vault:
    def __init__(self, data_dir: Path):
        path = data_dir / "secret.key"
        if not path.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(Fernet.generate_key())
        self.f = Fernet(path.read_bytes())

    def seal(self, text: str) -> str:
        return self.f.encrypt(text.encode()).decode()

    def open(self, token: str) -> str:
        return self.f.decrypt(token.encode()).decode()


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001
        return value


def _body(msg: email.message.Message) -> str:
    parts = msg.walk() if msg.is_multipart() else [msg]
    plain, html = "", ""
    for part in parts:
        ctype = part.get_content_type()
        if part.get_content_disposition() == "attachment":
            continue
        try:
            payload = part.get_payload(decode=True)
        except Exception:  # noqa: BLE001
            continue
        if not payload:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if ctype == "text/plain" and not plain:
            plain = text
        elif ctype == "text/html" and not html:
            html = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", text, flags=re.I)
            html = re.sub(r"<br\s*/?>|</p>|</div>", "\n", html, flags=re.I)
            html = re.sub(r"<[^>]+>", " ", html)
    text = plain or html
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def find_embargo(subject: str, body: str) -> str:
    m = EMBARGO.search(subject) or EMBARGO.search(body[:3000])
    return m.group(0).strip() if m else ""


def parse_message(raw: bytes) -> dict:
    msg = email.message_from_bytes(raw)
    subject = _decode(msg.get("Subject"))
    body = _body(msg)
    sent = ""
    try:
        dt = parsedate_to_datetime(msg.get("Date"))
        sent = dt.astimezone(KST).isoformat(timespec="seconds") if dt else ""
    except (TypeError, ValueError):
        pass
    return {"sender": _decode(msg.get("From")), "subject": subject, "sent_at": sent, "body": body[:30000],
            "embargo": find_embargo(subject, body)}


def fetch_new(db: Database, vault: Vault, account: dict, imap_factory=imaplib.IMAP4_SSL, max_new: int = 50) -> int:
    """동기 함수(스레드에서 실행). 새 메일 수를 돌려준다."""
    password = vault.open(account["secret_enc"])
    imap = imap_factory(account["host"])
    try:
        imap.login(account["username"], password)
        status, _ = imap.select(f'"{account["folder"]}"', readonly=True)
        if status != "OK":
            raise RuntimeError(f"메일함 '{account['folder']}'을 열 수 없습니다")
        last = int(account["last_uid"] or 0)
        status, data = imap.uid("search", None, f"UID {last + 1}:*")
        uids = [int(u) for u in (data[0] or b"").split() if int(u) > last]
        if last == 0:
            uids = uids[-max_new:]  # 처음 연결 때는 최근 메일만
        added = 0
        for uid in uids[:max_new]:
            status, parts = imap.uid("fetch", str(uid), "(BODY.PEEK[])")
            raw = next((p[1] for p in parts if isinstance(p, tuple)), None)
            if not raw:
                continue
            m = parse_message(raw)
            n = db.execute("""INSERT OR IGNORE INTO mails(user_id, uid, sender, subject, sent_at, embargo, body,
                              first_seen_at) VALUES(?,?,?,?,?,?,?,?)""",
                           (account["user_id"], uid, m["sender"], m["subject"], m["sent_at"], m["embargo"],
                            m["body"], now_iso()))
            added += n
        if uids:
            db.execute("UPDATE mail_accounts SET last_uid=?, last_error=NULL, updated_at=? WHERE user_id=?",
                       (max(uids), now_iso(), account["user_id"]))
        else:
            db.execute("UPDATE mail_accounts SET last_error=NULL, updated_at=? WHERE user_id=?",
                       (now_iso(), account["user_id"]))
        return added
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass


def poll_all(db: Database, vault: Vault) -> None:
    for acc in db.query("SELECT * FROM mail_accounts WHERE enabled=1"):
        try:
            fetch_new(db, vault, acc)
        except Exception as e:  # noqa: BLE001 - 한 사람 오류가 전체를 막지 않게
            msg = str(e)[:300]
            db.execute("UPDATE mail_accounts SET last_error=?, updated_at=? WHERE user_id=?",
                       (msg, now_iso(), acc["user_id"]))
            db.log("error", f"mail user {acc['user_id']}: {msg}")


def today_start() -> str:
    return datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
