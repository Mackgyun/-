"""실행 진입점.

  python -m newsbot                 웹앱 + 수집기 실행
  python -m newsbot create-admin    첫 관리자 계정 만들기
  python -m newsbot invite          기자 초대 링크 만들기
  python -m newsbot poll            DART 한 번 수집해 보기 (알림 없음)
  python -m newsbot reset-password  비밀번호 다시 정하기
  python -m newsbot backup [폴더]    DB·키 백업 (실행 중에도 안전)
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
import logging.handlers
import re
import shutil
import sys

from . import auth
from .config import load_settings
from .db import Database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="newsbot", description="청년의사 브리핑")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="웹앱 실행 (기본)")
    ca = sub.add_parser("create-admin", help="관리자 계정 만들기")
    ca.add_argument("username")
    ca.add_argument("--name", default="관리자")
    inv = sub.add_parser("invite", help="초대 링크 만들기")
    inv.add_argument("--admin", action="store_true", help="관리자 권한으로 초대")
    sub.add_parser("poll", help="DART 한 번 수집")
    rp = sub.add_parser("reset-password", help="비밀번호 다시 정하기")
    rp.add_argument("username")
    bk = sub.add_parser("backup", help="DB·암호화 키 백업")
    bk.add_argument("dest", nargs="?", default=None, help="백업 폴더 (기본: data/backups)")
    args = parser.parse_args(argv)

    settings = load_settings()
    setup_logging(settings.data_dir / "logs" if args.cmd in (None, "serve") else None)
    db = Database(settings.db_path)

    if args.cmd == "create-admin":
        if db.one("SELECT 1 FROM users WHERE username=?", (args.username.lower(),)):
            print(f"'{args.username}' 계정이 이미 있습니다. 비밀번호를 바꾸려면: python -m newsbot reset-password {args.username}")
            return 1
        pw = _ask_password()
        if not pw:
            return 1
        auth.create_user(db, args.username, args.name, pw, role="admin")
        db.execute("INSERT OR IGNORE INTO subscriptions(user_id, kind, value) "
                   "SELECT id, 'watch', '' FROM users WHERE username=?", (args.username.lower(),))
        print(f"관리자 '{args.username}' 계정을 만들었습니다. {settings.public_url} 에서 로그인하세요.")
        return 0

    if args.cmd == "reset-password":
        user = db.one("SELECT id FROM users WHERE username=?", (args.username.lower(),))
        if not user:
            print(f"'{args.username}' 계정이 없습니다.")
            return 1
        pw = _ask_password()
        if not pw:
            return 1
        db.execute("UPDATE users SET pw_hash=? WHERE id=?", (auth.hash_password(pw), user["id"]))
        db.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
        print("비밀번호를 바꿨습니다. 기존 로그인은 모두 끊겼습니다.")
        return 0

    if args.cmd == "backup":
        from pathlib import Path

        from .db import now

        dest = Path(args.dest) if args.dest else settings.data_dir / "backups"
        stamp = now().strftime("%Y%m%d-%H%M")
        out = db.backup(dest / f"newsbot-{stamp}.db")
        copied = []
        for name in ("secret.key", "vapid_private.pem"):
            if (settings.data_dir / name).exists():
                shutil.copy2(settings.data_dir / name, dest / name)
                copied.append(name)
        print(f"백업했습니다: {out}")
        if copied:
            print(f"암호화 키({', '.join(copied)})도 같은 폴더에 복사했습니다. 외부에 공유하지 마세요.")
        return 0

    if args.cmd == "invite":
        code = auth.create_invite(db, None, "admin" if args.admin else "reporter")
        print(f"초대 링크 ({auth.INVITE_DAYS}일 유효, 1회용):\n{settings.public_url}/#join/{code}")
        return 0

    if args.cmd == "poll":
        from .app import Poller
        from .push import Pusher
        from .rules import Rules

        if not settings.dart_api_key:
            print(".env 에 DART_API_KEY 가 없습니다.")
            return 1
        from .push import Alerter

        rules = Rules.load(settings.rules_path)
        pusher = Pusher(db, settings.data_dir, settings.vapid_contact, enabled=False)
        poller = Poller(settings, db, rules, Alerter(db, rules, pusher, settings.public_url, notify=False))
        asyncio.run(poller.run_once())
        print("상태:", db.get("dart_status"), "/ 오늘 호출:", poller.client.calls_today())
        return 0

    import uvicorn

    from .app import create_app

    app = create_app(settings, db)
    print(f"청년의사 브리핑: {settings.public_url}  (알림 모드: {settings.alert_mode})")
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info", log_config=None)
    return 0


def _ask_password() -> str | None:
    pw = getpass.getpass("비밀번호(10자 이상): ")
    if problem := auth.validate_password(pw):
        print(problem)
        return None
    if pw != getpass.getpass("비밀번호 확인: "):
        print("비밀번호가 다릅니다.")
        return None
    return pw


class _Redact(logging.Filter):
    """로그에 인증키가 남지 않게 가린다."""

    PATTERN = re.compile(r"(crtfc_key=|api[_-]?key=|key=)[^&\s'\"]+|sk-[A-Za-z0-9_-]{10,}", re.I)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        clean = self.PATTERN.sub(lambda m: (m.group(1) or "") + "***", msg)
        if clean != msg:
            record.msg, record.args = clean, ()
        return True


def setup_logging(log_dir) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handlers = [logging.StreamHandler()]
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        # 작업 스케줄러로 돌리면 화면 출력이 사라지므로 파일에도 남긴다 (5MB × 5개 순환)
        handlers.append(logging.handlers.RotatingFileHandler(log_dir / "newsbot.log", maxBytes=5_000_000,
                                                             backupCount=5, encoding="utf-8"))
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(_Redact())
        root.addHandler(h)
    # httpx 는 요청 URL(인증키 포함)을 INFO 로 찍으므로 경고 이상만
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


if __name__ == "__main__":
    sys.exit(main())
