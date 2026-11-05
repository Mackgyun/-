"""웹앱 서버 (FastAPI). 화면은 static/ 의 정적 파일로 제공한다."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth
from .config import Settings
from .dart import VIEW_URL, Collector, DartClient, DartError, DartLimitReached
from .db import Database, now, now_iso
from .push import Pusher, payload_for, recipients
from .rules import RED, Rules

log = logging.getLogger(__name__)
STATIC = Path(__file__).resolve().parent / "static"
COOKIE = "nb_session"


class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    code: str
    username: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=1, max_length=40)
    password: str


class SubIn(BaseModel):
    kind: str = Field(pattern=r"^(all|watch|company|keyword)$")
    value: str = Field(default="", max_length=60)


class PushIn(BaseModel):
    endpoint: str
    keys: dict


class InviteIn(BaseModel):
    role: str = Field(default="reporter", pattern=r"^(reporter|admin)$")


class Poller:
    """백그라운드 수집 루프."""

    def __init__(self, settings: Settings, db: Database, rules: Rules, pusher: Pusher):
        self.settings = settings
        self.db = db
        self.rules = rules
        self.pusher = pusher
        self.client = DartClient(settings.dart_api_key, db, settings.dart_daily_call_limit)
        self.collector = Collector(self.client, db, rules, settings.dart_rescan_pages)
        self._last_full = None

    async def run_forever(self) -> None:
        if not self.settings.dart_api_key:
            self.db.set("dart_status", "키 없음: .env 에 DART_API_KEY 를 넣으면 수집을 시작합니다")
            return
        while True:
            await self.run_once()
            await asyncio.sleep(self.settings.poll_interval_sec)

    async def run_once(self) -> None:
        full = self._last_full is None or now() - self._last_full > timedelta(hours=1)
        try:
            result = await self.collector.poll(full=full)
            if full:
                self._last_full = now()
            self.db.set("dart_status", "정상")
            self.db.set("dart_fail_count", "0")
            self.db.log("poll", f"pages={result.pages} scanned={result.scanned} new={len(result.new)}"
                                f"{' bootstrap' if result.bootstrap else ''}")
            if not result.bootstrap:
                await self._alert(result.new)
        except DartLimitReached as e:
            self.db.set("dart_status", f"호출 한도 도달 ({e}) - 내일 다시 시작")
            self.db.log("error", str(e))
        except (DartError, Exception) as e:  # noqa: BLE001 - 루프가 죽지 않게 모두 기록
            fails = int(self.db.get("dart_fail_count", "0") or 0) + 1
            self.db.set("dart_fail_count", str(fails))
            self.db.set("dart_status", f"오류 {fails}회 연속: {e}")
            self.db.log("error", f"poll: {e!r}")
            log.exception("poll failed")

    async def _alert(self, rows: list[dict]) -> None:
        for row in rows:
            c_alert = row["level"] == RED and not row["is_correction"]
            if not c_alert or not self.settings.notify_enabled:
                continue
            payload = payload_for(row, self.settings.public_url)
            for user_id in recipients(self.db, self.rules, row):
                sent = await asyncio.to_thread(self.pusher.send_to_user, user_id, payload)
                self.db.log("alert", f"{row['rcept_no']} -> user {user_id} ({sent} devices)")


def create_app(settings: Settings, db: Database | None = None, start_poller: bool = True) -> FastAPI:
    db = db or Database(settings.db_path)
    rules = Rules.load(settings.rules_path)
    pusher = Pusher(db, settings.data_dir, settings.vapid_contact, settings.notify_enabled)
    limiter = auth.LoginLimiter()
    poller = Poller(settings, db, rules, pusher)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(poller.run_forever()) if start_poller else None
        yield
        if task:
            task.cancel()

    app = FastAPI(title="청년의사 브리핑", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.db, app.state.settings, app.state.poller, app.state.pusher = db, settings, poller, pusher

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp: Response = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'"
        )
        return resp

    # --- 인증 -----------------------------------------------------------
    def current_user(request: Request) -> dict:
        user = auth.session_user(db, request.cookies.get(COOKIE))
        if not user:
            raise HTTPException(401, "로그인이 필요합니다.")
        return user

    def admin_user(user: dict = Depends(current_user)) -> dict:
        if user["role"] != "admin":
            raise HTTPException(403, "관리자만 할 수 있습니다.")
        return user

    def _set_cookie(resp: Response, token: str) -> None:
        resp.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=settings.secure_cookies,
                        max_age=auth.SESSION_DAYS * 86400)

    @app.post("/api/login")
    def login(body: LoginIn, request: Request, response: Response):
        key = f"{body.username.lower()}|{request.client.host if request.client else ''}"
        if limiter.locked(key):
            raise HTTPException(429, "로그인 실패가 많아 10분 동안 잠겼습니다.")
        user = auth.authenticate(db, body.username, body.password)
        if not user:
            limiter.fail(key)
            db.log("login_fail", body.username[:40])
            raise HTTPException(401, "아이디 또는 비밀번호가 맞지 않습니다.")
        limiter.reset(key)
        _set_cookie(response, auth.create_session(db, user["id"]))
        return {"ok": True}

    @app.post("/api/register")
    def register(body: RegisterIn, response: Response):
        try:
            user_id = auth.redeem_invite(db, body.code, body.username, body.display_name, body.password)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        db.execute("INSERT OR IGNORE INTO subscriptions(user_id, kind, value) VALUES(?, 'watch', '')", (user_id,))
        _set_cookie(response, auth.create_session(db, user_id))
        return {"ok": True}

    @app.post("/api/logout")
    def logout(request: Request, response: Response):
        token = request.cookies.get(COOKIE)
        if token:
            auth.delete_session(db, token)
        response.delete_cookie(COOKIE)
        return {"ok": True}

    @app.get("/api/me")
    def me(user: dict = Depends(current_user)):
        subs = db.query("SELECT kind, value FROM subscriptions WHERE user_id=? ORDER BY kind, value", (user["id"],))
        devices = db.one("SELECT COUNT(*) n FROM push_subs WHERE user_id=?", (user["id"],))["n"]
        return {**user, "subscriptions": subs, "push_devices": devices, "alert_mode": settings.alert_mode}

    # --- 피드 -----------------------------------------------------------
    def _decorate(rows: list[dict]) -> list[dict]:
        for r in rows:
            r["url"] = VIEW_URL.format(rcept_no=r["rcept_no"])
        return rows

    @app.get("/api/feed")
    def feed(level: str = "", q: str = "", watched: int = 0, mine: int = 0, include_gray: int = 0,
             before: str = "", limit: int = 50, user: dict = Depends(current_user)):
        sql = ["""SELECT d.*, c.user_id AS claimed_by, u.display_name AS claimed_name
                  FROM disclosures d LEFT JOIN claims c ON c.rcept_no=d.rcept_no
                  LEFT JOIN users u ON u.id=c.user_id WHERE 1=1"""]
        params: list = []
        if level in ("red", "yellow", "gray"):
            sql.append("AND d.level=?")
            params.append(level)
        elif not include_gray:
            sql.append("AND d.level!='gray'")
        if q:
            sql.append("AND (d.corp_name LIKE ? OR d.report_nm LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if watched:
            sql.append("AND d.watched=1")
        if mine:
            sql.append("AND c.user_id=?")
            params.append(user["id"])
        if before:
            sql.append("AND d.first_seen_at < ?")
            params.append(before)
        sql.append("ORDER BY d.first_seen_at DESC, d.rcept_no DESC LIMIT ?")
        params.append(max(1, min(limit, 200)))
        return {"items": _decorate(db.query(" ".join(sql), tuple(params)))}

    @app.get("/api/summary")
    def summary(user: dict = Depends(current_user)):
        since = now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
        counts = {r["level"]: r["n"] for r in db.query(
            "SELECT level, COUNT(*) n FROM disclosures WHERE first_seen_at >= ? GROUP BY level", (since,))}
        top = _decorate(db.query(
            """SELECT d.*, c.user_id AS claimed_by, u.display_name AS claimed_name FROM disclosures d
               LEFT JOIN claims c ON c.rcept_no=d.rcept_no LEFT JOIN users u ON u.id=c.user_id
               WHERE d.first_seen_at >= ? AND d.level='red' AND d.is_correction=0
               ORDER BY d.watched DESC, d.first_seen_at DESC LIMIT 5""", (since,)))
        unclaimed = sum(1 for t in top if not t["claimed_by"])
        mine = db.one("SELECT COUNT(*) n FROM claims WHERE user_id=? AND claimed_at >= ?", (user["id"], since))["n"]
        return {
            "date": now().strftime("%Y-%m-%d"),
            "red": counts.get("red", 0), "yellow": counts.get("yellow", 0), "gray": counts.get("gray", 0),
            "top": top, "unclaimed_top": unclaimed, "my_claims": mine,
            "last_poll_at": db.get("last_poll_at"), "dart_status": db.get("dart_status", "대기 중"),
            "alert_mode": settings.alert_mode,
        }

    @app.get("/api/disclosures/{rcept_no}")
    def disclosure(rcept_no: str, user: dict = Depends(current_user)):
        rows = _decorate(db.query(
            """SELECT d.*, c.user_id AS claimed_by, u.display_name AS claimed_name, c.claimed_at FROM disclosures d
               LEFT JOIN claims c ON c.rcept_no=d.rcept_no LEFT JOIN users u ON u.id=c.user_id
               WHERE d.rcept_no=?""", (rcept_no,)))
        if not rows:
            raise HTTPException(404, "없는 공시입니다.")
        return rows[0]

    @app.post("/api/claims/{rcept_no}")
    def claim(rcept_no: str, user: dict = Depends(current_user)):
        with db.tx() as c:
            if not c.execute("SELECT 1 FROM disclosures WHERE rcept_no=?", (rcept_no,)).fetchone():
                raise HTTPException(404, "없는 공시입니다.")
            row = c.execute("SELECT c.user_id, u.display_name FROM claims c JOIN users u ON u.id=c.user_id "
                            "WHERE rcept_no=?", (rcept_no,)).fetchone()
            if row and row["user_id"] != user["id"]:
                raise HTTPException(409, f"이미 {row['display_name']} 기자가 맡았습니다.")
            c.execute("INSERT OR IGNORE INTO claims(rcept_no, user_id, claimed_at) VALUES(?,?,?)",
                      (rcept_no, user["id"], now_iso()))
        return {"ok": True}

    @app.delete("/api/claims/{rcept_no}")
    def unclaim(rcept_no: str, user: dict = Depends(current_user)):
        db.execute("DELETE FROM claims WHERE rcept_no=? AND user_id=?", (rcept_no, user["id"]))
        return {"ok": True}

    # --- 구독·푸시 -------------------------------------------------------
    @app.post("/api/subscriptions")
    def add_sub(body: SubIn, user: dict = Depends(current_user)):
        value = body.value.strip() if body.kind in ("company", "keyword") else ""
        if body.kind in ("company", "keyword") and not value:
            raise HTTPException(400, "기업명이나 키워드를 입력해 주세요.")
        db.execute("INSERT OR IGNORE INTO subscriptions(user_id, kind, value) VALUES(?,?,?)",
                   (user["id"], body.kind, value))
        return {"ok": True}

    @app.delete("/api/subscriptions")
    def del_sub(kind: str, value: str = "", user: dict = Depends(current_user)):
        db.execute("DELETE FROM subscriptions WHERE user_id=? AND kind=? AND value=?", (user["id"], kind, value))
        return {"ok": True}

    @app.get("/api/push/key")
    def push_key():
        return {"key": pusher.public_key}

    @app.post("/api/push/subscribe")
    def push_subscribe(body: PushIn, user: dict = Depends(current_user)):
        try:
            pusher.subscribe(user["id"], body.model_dump())
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        return {"ok": True}

    @app.post("/api/push/test")
    async def push_test(user: dict = Depends(current_user)):
        payload = {"title": "청년의사 브리핑", "body": "알림이 잘 도착했어요. 중요 공시는 이렇게 뜹니다.",
                   "url": settings.public_url + "/", "tag": "test"}
        sent = await asyncio.to_thread(pusher.send_to_user, user["id"], payload, True)
        return {"sent": sent}

    # --- 관리자 ---------------------------------------------------------
    @app.get("/api/admin/users")
    def admin_users(user: dict = Depends(admin_user)):
        return {"users": db.query("SELECT id, username, display_name, role, active, created_at FROM users ORDER BY id")}

    @app.post("/api/admin/invites")
    def admin_invite(body: InviteIn, user: dict = Depends(admin_user)):
        code = auth.create_invite(db, user["id"], body.role)
        return {"code": code, "url": f"{settings.public_url}/#join/{code}", "expires_in_days": auth.INVITE_DAYS}

    @app.post("/api/admin/users/{user_id}/active")
    def admin_set_active(user_id: int, active: int, user: dict = Depends(admin_user)):
        if user_id == user["id"]:
            raise HTTPException(400, "자기 자신은 비활성화할 수 없습니다.")
        db.execute("UPDATE users SET active=? WHERE id=?", (1 if active else 0, user_id))
        if not active:
            db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        return {"ok": True}

    @app.get("/api/admin/status")
    def admin_status(user: dict = Depends(admin_user)):
        return {
            "dart_status": db.get("dart_status", "대기 중"),
            "last_poll_at": db.get("last_poll_at"),
            "dart_calls_today": poller.client.calls_today(),
            "alert_mode": settings.alert_mode,
            "events": db.query("SELECT at, kind, detail FROM events ORDER BY id DESC LIMIT 50"),
        }

    @app.get("/healthz")
    def healthz():
        """외부 감시 서비스용. 마지막 수집이 너무 오래되면 503."""
        last = db.get("last_poll_at")
        if settings.dart_api_key and last:
            from datetime import datetime
            age = (now() - datetime.fromisoformat(last)).total_seconds()
            if age > settings.poll_interval_sec * 4:
                return JSONResponse({"ok": False, "last_poll_at": last}, status_code=503)
        return {"ok": True, "last_poll_at": last}

    # --- 정적 파일 -------------------------------------------------------
    @app.get("/sw.js")
    def sw():
        return FileResponse(STATIC / "sw.js", media_type="text/javascript",
                            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

    @app.get("/manifest.webmanifest")
    def manifest():
        return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
