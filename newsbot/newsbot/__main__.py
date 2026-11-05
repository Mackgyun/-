"""실행 진입점.

  python -m newsbot                 웹앱 + 수집기 실행
  python -m newsbot create-admin    첫 관리자 계정 만들기
  python -m newsbot invite          기자 초대 링크 만들기
  python -m newsbot poll            DART 한 번 수집해 보기 (알림 없음)
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
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
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    db = Database(settings.db_path)

    if args.cmd == "create-admin":
        pw = getpass.getpass("비밀번호(10자 이상): ")
        if problem := auth.validate_password(pw):
            print(problem)
            return 1
        if pw != getpass.getpass("비밀번호 확인: "):
            print("비밀번호가 다릅니다.")
            return 1
        auth.create_user(db, args.username, args.name, pw, role="admin")
        db.execute("INSERT OR IGNORE INTO subscriptions(user_id, kind, value) "
                   "SELECT id, 'watch', '' FROM users WHERE username=?", (args.username.lower(),))
        print(f"관리자 '{args.username}' 계정을 만들었습니다. {settings.public_url} 에서 로그인하세요.")
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
        pusher = Pusher(db, settings.data_dir, settings.vapid_contact, enabled=False)
        poller = Poller(settings, db, Rules.load(settings.rules_path), pusher)
        asyncio.run(poller.run_once())
        print("상태:", db.get("dart_status"), "/ 오늘 호출:", poller.client.calls_today())
        return 0

    import uvicorn

    from .app import create_app

    app = create_app(settings, db)
    print(f"청년의사 브리핑: {settings.public_url}  (알림 모드: {settings.alert_mode})")
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
