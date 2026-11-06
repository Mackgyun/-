"""웹앱 서버 (FastAPI). 화면은 static/ 의 정적 파일로 제공한다."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import auth, mail, qa, writing
from .alio import AlioClient, AlioCollector, AlioConfig, finance_overview, parse_tables
from .articles import ArticleCollector
from .config import KST, Settings
from .dart import VIEW_URL, Collector, DartClient, DartLimitReached, redact
from .db import Database, now, now_iso
from .llm import LLM, LLMError
from .push import Alerter, Pusher
from .rules import Rules

log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)  # 요청 URL에 인증키가 들어 있어 INFO 로그를 끔
STATIC = Path(__file__).resolve().parent / "static"
COOKIE = "nb_session"


# --- 입력 모델 ---------------------------------------------------------------
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


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class DraftIn(BaseModel):
    source_kind: str = Field(pattern=r"^(disclosure|mail|text)$")
    source_ref: str | None = None
    title: str = Field(default="", max_length=200)
    text: str = Field(default="", max_length=40000)
    kind: str = Field(default="스트레이트", max_length=20)


class StylebookIn(BaseModel):
    content: str = Field(min_length=10, max_length=30000)


class ReporterIn(BaseModel):
    reporter_id: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")


class MailAccountIn(BaseModel):
    host: str = Field(default="imap.gmail.com", max_length=100, pattern=r"^[A-Za-z0-9.-]+$")
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=4, max_length=200)
    folder: str = Field(default="보도자료", min_length=1, max_length=100)


class WrittenIn(BaseModel):
    url: str = Field(default="", max_length=500)

    @field_validator("url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        v = v.strip()
        if v and not v.lower().startswith(("http://", "https://")):
            raise ValueError("기사 주소는 http:// 또는 https:// 로 시작해야 합니다.")
        return v


class LimitIn(BaseModel):
    krw: int = Field(ge=0, le=10_000_000)


# --- 백그라운드 작업 ---------------------------------------------------------
class Poller:
    """DART 수집 루프."""

    def __init__(self, settings: Settings, db: Database, rules: Rules, alerter: Alerter):
        self.settings = settings
        self.db = db
        self.rules = rules
        self.alerter = alerter
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

    def paused(self) -> bool:
        until = self.db.get("dart_paused_until")
        return bool(until) and now().isoformat(timespec="seconds") < until

    async def run_once(self) -> None:
        if self.paused():  # 일일 한도 초과: 자정(한국 시간)까지 호출하지 않음
            await self._flush()
            return
        full = self._last_full is None or now() - self._last_full > timedelta(hours=1)
        try:
            result = await self.collector.poll(full=full)
            if full:
                self._last_full = now()
            self.db.set("dart_status", "정상")
            self.db.set("dart_fail_count", "0")
            self.db.log("poll", f"pages={result.pages} scanned={result.scanned} new={len(result.new)}"
                                f"{' bootstrap' if result.bootstrap else ''}")
        except DartLimitReached as e:
            tomorrow = (now() + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
            self.db.set("dart_paused_until", tomorrow.isoformat(timespec="seconds"))
            self.db.set("dart_status", f"호출 한도 도달 ({redact(e)}) - {tomorrow:%m월 %d일 0시 5분}에 다시 시작")
            self.db.log("error", redact(e))
        except Exception as e:  # noqa: BLE001 - 루프가 죽지 않게 모두 기록
            fails = int(self.db.get("dart_fail_count", "0") or 0) + 1
            self.db.set("dart_fail_count", str(fails))
            self.db.set("dart_status", f"오류 {fails}회 연속: {redact(e)[:200]}")
            self.db.log("error", f"poll: {redact(repr(e))}")
            log.error("poll failed: %s", redact(repr(e)))
        await self._flush()

    async def _flush(self) -> None:
        """저장됐지만 아직 알리지 않은 공시를 보낸다 (수집이 실패한 회차에도)."""
        try:
            await self.alerter.flush()
        except Exception as e:  # noqa: BLE001
            self.db.log("error", f"alert: {e!r}")
            log.exception("alert failed")


async def alio_loop(settings: Settings, db: Database, alerter: Alerter, collector: AlioCollector):
    while True:
        try:
            new = await collector.poll()
            db.set("alio_status", "정상")
            db.log("alio", f"new={len(new)}")
        except Exception as e:  # noqa: BLE001
            hint = " (SSL 오류면 .env 에 ALIO_VERIFY_SSL=false)" if "SSL" in repr(e) or "certificate" in repr(e) else ""
            db.set("alio_status", f"오류: {str(e)[:200]}{hint}")
            db.log("error", f"alio: {e!r}")
            log.exception("alio poll failed")
        try:
            await alerter.flush()
        except Exception as e:  # noqa: BLE001
            db.log("error", f"alert: {e!r}")
        await asyncio.sleep(settings.alio_poll_hours * 3600)


async def mail_loop(settings: Settings, db: Database, vault: mail.Vault, llm: LLM):
    summarize = None
    if settings.mail_ai_summary and llm.available:
        def summarize(user_id: int, subject: str, body: str) -> str:
            text, _ = llm.complete(mail.SUMMARY_SYSTEM, f"제목: {subject}\n\n{body[:6000]}", tier="fast",
                                   user_id=user_id, purpose="mail_summary")
            return text.strip()
    while True:
        try:
            await asyncio.to_thread(mail.poll_all, db, vault, summarize)
        except Exception as e:  # noqa: BLE001
            db.log("error", f"mail loop: {e!r}")
            log.exception("mail loop failed")
        await asyncio.sleep(settings.mail_poll_minutes * 60)


async def digest_loop(settings: Settings, db: Database, llm: LLM):
    while True:
        try:
            t = now()
            for hhmm in settings.digest_times:
                h, m = (int(x) for x in hhmm.split(":"))
                due = t.replace(hour=h, minute=m, second=0, microsecond=0)
                slot = due.strftime("%Y-%m-%d ") + hhmm
                if due <= t < due + timedelta(minutes=30) and not db.one("SELECT 1 FROM briefings WHERE slot=?", (slot,)):
                    prev = db.one("SELECT created_at FROM briefings ORDER BY id DESC LIMIT 1")
                    since = prev["created_at"] if prev else (t - timedelta(hours=12)).isoformat(timespec="seconds")
                    await asyncio.to_thread(qa.make_digest, db, llm, slot, since)
            db.set("digest_checked_at", now_iso())
        except Exception as e:  # noqa: BLE001 - 설정 오류 등으로 조용히 멈추지 않게 기록하고 계속
            db.set("digest_status", f"오류: {str(e)[:200]}")
            db.log("error", f"digest: {e!r}")
            log.exception("digest failed")
        await asyncio.sleep(60)


async def backup_loop(settings: Settings, db: Database, keep: int = 14):
    """매일 새벽 4시 data/backups 에 DB 복사본(VACUUM INTO). 최근 keep 개만 남긴다."""
    while True:
        try:
            t = now()
            target = settings.data_dir / "backups" / f"newsbot-{t:%Y%m%d}.db"
            if t.hour >= 4 and not target.exists():
                await asyncio.to_thread(db.backup, target)
                db.log("backup", str(target.name))
                olds = sorted(target.parent.glob("newsbot-*.db"))[:-keep]
                for old in olds:
                    old.unlink(missing_ok=True)
        except Exception as e:  # noqa: BLE001
            db.log("error", f"backup: {e!r}")
            log.exception("backup failed")
        await asyncio.sleep(1800)


# --- 앱 ---------------------------------------------------------------------
def create_app(settings: Settings, db: Database | None = None, start_poller: bool = True,
               llm: LLM | None = None) -> FastAPI:
    db = db or Database(settings.db_path)
    rules = Rules.load(settings.rules_path)
    pusher = Pusher(db, settings.data_dir, settings.vapid_contact, settings.notify_enabled)
    alerter = Alerter(db, rules, pusher, settings.public_url, settings.notify_enabled)
    limiter = auth.LoginLimiter()
    poller = Poller(settings, db, rules, alerter)
    started_at = now()
    llm = llm or LLM(settings, db)
    vault = mail.Vault(settings.data_dir)
    alio_cfg = AlioConfig.load(settings.alio_path) if settings.alio_path.exists() else AlioConfig()
    alio_client = AlioClient(verify=settings.alio_verify_ssl)
    alio_collector = AlioCollector(alio_client, db, alio_cfg)
    articles = ArticleCollector(db, settings.docdoc_base)
    jobs: dict[str, asyncio.Task] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tasks = []
        if start_poller:
            tasks.append(asyncio.create_task(poller.run_forever()))
            tasks.append(asyncio.create_task(digest_loop(settings, db, llm)))
            tasks.append(asyncio.create_task(backup_loop(settings, db)))
            if settings.alio_enabled:
                tasks.append(asyncio.create_task(alio_loop(settings, db, alerter, alio_collector)))
            if settings.mail_enabled:
                tasks.append(asyncio.create_task(mail_loop(settings, db, vault, llm)))
        yield
        for t in tasks + list(jobs.values()):
            t.cancel()

    app = FastAPI(title="청년의사 브리핑", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.db, app.state.settings, app.state.poller, app.state.pusher = db, settings, poller, pusher
    app.state.alerter = alerter
    app.state.llm, app.state.alio = llm, alio_collector

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

    @app.exception_handler(LLMError)
    async def llm_error(_: Request, exc: LLMError):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    # --- 인증 -----------------------------------------------------------
    def current_user(request: Request) -> dict:
        user = auth.session_user(db, request.cookies.get(COOKIE))
        if not user:
            raise HTTPException(401, "로그인이 필요합니다.")
        full = db.one("SELECT reporter_id, monthly_limit_krw FROM users WHERE id=?", (user["id"],))
        return {**user, **(full or {})}

    def admin_user(user: dict = Depends(current_user)) -> dict:
        if user["role"] != "admin":
            raise HTTPException(403, "관리자만 할 수 있습니다.")
        return user

    def _set_cookie(resp: Response, token: str) -> None:
        resp.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=settings.secure_cookies,
                        max_age=auth.SESSION_DAYS * 86400)

    def client_ip(request: Request) -> str:
        """같은 PC의 보안 터널(cloudflared 등)을 거쳐 온 요청은 터널이 붙인 원래 IP를 쓴다."""
        host = request.client.host if request.client else ""
        if host in ("127.0.0.1", "::1"):
            fwd = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "").split(",")[0]
            if fwd.strip():
                return fwd.strip()[:64]
        return host

    @app.post("/api/login")
    def login(body: LoginIn, request: Request, response: Response):
        key = f"{body.username.lower()}|{client_ip(request)}"
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
        articles_n = db.one("SELECT COUNT(*) n FROM articles WHERE author_id=?",
                            ((user.get("reporter_id") or "").lower(),))["n"]
        sb = db.one("SELECT updated_at, source_count FROM stylebooks WHERE user_id=?", (user["id"],))
        acc = db.one("SELECT host, username, folder, enabled, last_error, updated_at FROM mail_accounts WHERE user_id=?",
                     (user["id"],))
        return {**user, "subscriptions": subs, "push_devices": devices, "alert_mode": settings.alert_mode,
                "llm_ready": llm.available, "llm_provider": settings.llm_provider,
                "mail_enabled": settings.mail_enabled, "mail_account": acc,
                "my_articles": articles_n, "stylebook": sb,
                "spent_krw": round(llm.month_spent(user["id"])), "limit_krw": llm.limit_for(user["id"])}

    @app.post("/api/me/reporter")
    def set_reporter(body: ReporterIn, user: dict = Depends(current_user)):
        db.execute("UPDATE users SET reporter_id=? WHERE id=?", (body.reporter_id.lower(), user["id"]))
        return {"ok": True}

    # --- 피드 -----------------------------------------------------------
    def _decorate(rows: list[dict]) -> list[dict]:
        for r in rows:
            r["url"] = r.get("link") or VIEW_URL.format(rcept_no=r["rcept_no"])
        return rows

    FEED_SELECT = """SELECT d.*, c.user_id AS claimed_by, u.display_name AS claimed_name, c.written_url, c.written_at
                     FROM disclosures d LEFT JOIN claims c ON c.rcept_no=d.rcept_no
                     LEFT JOIN users u ON u.id=c.user_id"""
    SPLITS = ("inbox", "red", "beat", "alio", "unclaimed", "mine", "all")

    def _like(text: str) -> str:
        return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    def _beat_sql(user_id: int) -> tuple[str, list]:
        """내 출입처: 구독(전체·감시 기업·기업·키워드)에 맞는 공시."""
        parts, params = [], []
        for sub in db.query("SELECT kind, value FROM subscriptions WHERE user_id=?", (user_id,)):
            if sub["kind"] == "all":
                return "1=1", []
            if sub["kind"] == "watch":
                parts.append("d.watched=1")
            elif sub["kind"] == "company":
                parts.append("REPLACE(d.corp_name,' ','')=?")
                params.append("".join(sub["value"].split()))
            elif sub["kind"] == "keyword":
                parts.append("REPLACE(d.report_nm,' ','') LIKE ? ESCAPE '\\'")
                params.append(_like("".join(sub["value"].split())))
        return ("(" + " OR ".join(parts) + ")" if parts else "0=1"), params

    def _split_where(split: str, user_id: int) -> tuple[list[str], list]:
        recent = (now() - timedelta(days=3)).isoformat(timespec="seconds")
        if split == "inbox":
            return ["d.level!='gray'", "t.done_at IS NULL", "d.first_seen_at >= ?"], [recent]
        if split == "red":
            return ["d.level='red'", "d.is_correction=0", "t.done_at IS NULL"], []
        if split == "beat":
            cond, params = _beat_sql(user_id)
            return ["d.level!='gray'", "t.done_at IS NULL", cond], params
        if split == "alio":
            return ["d.source='alio'", "d.level!='gray'"], []
        if split == "unclaimed":
            return ["d.level='red'", "d.is_correction=0", "c.user_id IS NULL", "d.first_seen_at >= ?"], [recent]
        if split == "mine":
            return ["c.user_id=?"], [user_id]
        return [], []

    def _feed_sql(user_id: int) -> str:
        return ("SELECT d.*, c.user_id AS claimed_by, u.display_name AS claimed_name, c.written_url, c.written_at, "
                "t.done_at FROM disclosures d LEFT JOIN claims c ON c.rcept_no=d.rcept_no "
                "LEFT JOIN users u ON u.id=c.user_id "
                f"LEFT JOIN triage t ON t.rcept_no=d.rcept_no AND t.user_id={int(user_id)}")

    @app.get("/api/feed")
    def feed(split: str = "", level: str = "", q: str = "", watched: int = 0, mine: int = 0, include_gray: int = 0,
             source: str = "", before: str = "", limit: int = 50, user: dict = Depends(current_user)):
        where, params = ["1=1"], []
        if split in SPLITS:
            w, p = _split_where(split, user["id"])
            where += w
            params += p
        if level in ("red", "yellow", "gray"):
            where.append("d.level=?")
            params.append(level)
        elif not include_gray and split not in ("all", "mine"):
            where.append("d.level!='gray'")
        if source in ("dart", "alio"):
            where.append("d.source=?")
            params.append(source)
        if q:
            where.append("(d.corp_name LIKE ? ESCAPE '\\' OR d.report_nm LIKE ? ESCAPE '\\')")
            params += [_like(q), _like(q)]
        if watched:
            where.append("d.watched=1")
        if mine:
            where.append("c.user_id=?")
            params.append(user["id"])
        if before:
            seen_at, _, after_no = before.partition("|")
            if after_no:
                where.append("(d.first_seen_at < ? OR (d.first_seen_at = ? AND d.rcept_no < ?))")
                params += [seen_at, seen_at, after_no]
            else:
                where.append("d.first_seen_at < ?")
                params.append(seen_at)
        sql = (_feed_sql(user["id"]) + " WHERE " + " AND ".join(where)
               + " ORDER BY d.first_seen_at DESC, d.rcept_no DESC LIMIT ?")
        params.append(max(1, min(limit, 200)))
        return {"items": _decorate(db.query(sql, tuple(params)))}

    @app.get("/api/counts")
    def counts(user: dict = Depends(current_user)):
        out = {}
        for split in SPLITS[:-1]:
            w, p = _split_where(split, user["id"])
            if split != "mine":
                w = w + ["d.level!='gray'"]
            row = db.one(f"SELECT COUNT(*) n FROM ({_feed_sql(user['id'])} WHERE {' AND '.join(w)})", tuple(p))
            out[split] = row["n"]
        return out

    @app.post("/api/done/{rcept_no:path}")
    def mark_done(rcept_no: str, user: dict = Depends(current_user)):
        if not db.one("SELECT 1 FROM disclosures WHERE rcept_no=?", (rcept_no,)):
            raise HTTPException(404, "없는 공시입니다.")
        db.execute("INSERT OR IGNORE INTO triage(user_id, rcept_no, done_at) VALUES(?,?,?)",
                   (user["id"], rcept_no, now_iso()))
        return {"ok": True}

    @app.delete("/api/done/{rcept_no:path}")
    def undo_done(rcept_no: str, user: dict = Depends(current_user)):
        db.execute("DELETE FROM triage WHERE user_id=? AND rcept_no=?", (user["id"], rcept_no))
        return {"ok": True}

    @app.post("/api/done-all")
    def done_all(split: str = "inbox", user: dict = Depends(current_user)):
        if split not in ("inbox", "red", "beat"):
            raise HTTPException(400, "이 목록은 전체 확인 처리를 지원하지 않습니다.")
        w, p = _split_where(split, user["id"])
        rows = db.query(f"{_feed_sql(user['id'])} WHERE {' AND '.join(w)} LIMIT 500", tuple(p))
        with db.tx() as c:
            for r in rows:
                c.execute("INSERT OR IGNORE INTO triage(user_id, rcept_no, done_at) VALUES(?,?,?)",
                          (user["id"], r["rcept_no"], now_iso()))
        return {"done": len(rows), "ids": [r["rcept_no"] for r in rows]}

    @app.get("/api/summary")
    def summary(user: dict = Depends(current_user)):
        since = now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
        counts = {r["level"]: r["n"] for r in db.query(
            "SELECT level, COUNT(*) n FROM disclosures WHERE first_seen_at >= ? GROUP BY level", (since,))}
        top = _decorate(db.query(FEED_SELECT + """ WHERE d.first_seen_at >= ? AND d.level='red' AND d.is_correction=0
                                                   ORDER BY d.watched DESC, d.first_seen_at DESC LIMIT 5""", (since,)))
        mine = db.one("SELECT COUNT(*) n FROM claims WHERE user_id=? AND claimed_at >= ?", (user["id"], since))["n"]
        mails_today = db.one("SELECT COUNT(*) n FROM mails WHERE user_id=? AND first_seen_at >= ?",
                             (user["id"], since))["n"] if settings.mail_enabled else None
        brief = db.one("SELECT slot, content, model, created_at FROM briefings ORDER BY id DESC LIMIT 1")
        return {
            "date": now().strftime("%Y-%m-%d"),
            "red": counts.get("red", 0), "yellow": counts.get("yellow", 0), "gray": counts.get("gray", 0),
            "top": top, "unclaimed_top": sum(1 for t in top if not t["claimed_by"]), "my_claims": mine,
            "mails_today": mails_today, "briefing": brief,
            "last_poll_at": db.get("last_poll_at"), "dart_status": redact(db.get("dart_status", "대기 중")),
            "alio_status": db.get("alio_status", "대기 중") if settings.alio_enabled else "꺼짐",
            "alert_mode": settings.alert_mode,
        }

    @app.get("/api/disclosures/{rcept_no:path}")
    def disclosure(rcept_no: str, user: dict = Depends(current_user)):
        rows = _decorate(db.query(FEED_SELECT.replace("c.written_at", "c.written_at, c.claimed_at")
                                  + " WHERE d.rcept_no=?", (rcept_no,)))
        if not rows:
            raise HTTPException(404, "없는 공시입니다.")
        return rows[0]

    @app.post("/api/claims/{rcept_no:path}/written")
    def mark_written(rcept_no: str, body: WrittenIn, user: dict = Depends(current_user)):
        n = db.execute("UPDATE claims SET written_url=?, written_at=? WHERE rcept_no=? AND user_id=?",
                       (body.url or None, now_iso(), rcept_no, user["id"]))
        if not n:
            raise HTTPException(400, "담당으로 지정한 공시만 기사화로 기록할 수 있습니다.")
        return {"ok": True}

    @app.post("/api/claims/{rcept_no:path}")
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

    @app.delete("/api/claims/{rcept_no:path}")
    def unclaim(rcept_no: str, user: dict = Depends(current_user)):
        db.execute("DELETE FROM claims WHERE rcept_no=? AND user_id=?", (rcept_no, user["id"]))
        return {"ok": True}

    # --- 질문 -----------------------------------------------------------
    @app.post("/api/ask")
    async def ask(body: AskIn, user: dict = Depends(current_user)):
        loop = asyncio.get_running_loop()
        return await asyncio.to_thread(qa.ask, settings, db, llm, user, body.question.strip(),
                                       poller.client if settings.dart_api_key else None, loop)

    @app.get("/api/chats")
    def chats(user: dict = Depends(current_user)):
        rows = db.query("SELECT id, question, answer, trace_json, model, created_at FROM chats WHERE user_id=? "
                        "ORDER BY id DESC LIMIT 30", (user["id"],))
        for r in rows:
            r["trace"] = [{"tool": t["tool"], "input": t["input"]} for t in json.loads(r.pop("trace_json"))]
        return {"items": rows}

    # --- 초안 -----------------------------------------------------------
    @app.post("/api/drafts")
    async def create_draft(body: DraftIn, user: dict = Depends(current_user)):
        title, text, ref = body.title.strip(), body.text.strip(), body.source_ref
        if body.source_kind == "disclosure":
            d = db.one("SELECT * FROM disclosures WHERE rcept_no=?", (ref or "",))
            if not d:
                raise HTTPException(404, "없는 공시입니다.")
            title = f"{d['corp_name']} {d['report_nm']}"
            meta = f"회사/기관: {d['corp_name']}\n공시 제목: {d['report_nm']}\n접수일: {d['rcept_dt']}\n"
            doc = ""
            try:
                if d.get("source", "dart") == "dart" and settings.dart_api_key:
                    doc = await poller.client.document_text(d["rcept_no"])
                elif d.get("source") == "alio" and d.get("link") and "disclosureNo=" in d["link"]:
                    html = await alio_client.report_html(d["link"].split("disclosureNo=")[1])
                    doc = "\n".join(" | ".join(r) for t in parse_tables(html) for r in t)[:15000]
            except Exception as e:  # noqa: BLE001
                db.log("error", f"draft source {ref}: {e!r}")
            if not doc and not text:
                raise HTTPException(400, "공시 원문을 불러오지 못했습니다. DART 인증키와 연결을 확인하거나 원자료를 직접 입력하세요.")
            text = meta + (f"\n원문:\n{doc}" if doc else "") + (f"\n\n기자 메모:\n{text}" if text else "")
        elif body.source_kind == "mail":
            if not (ref or "").isdigit():
                raise HTTPException(400, "메일 번호가 올바르지 않습니다.")
            m = db.one("SELECT * FROM mails WHERE id=? AND user_id=?", (int(ref), user["id"]))
            if not m:
                raise HTTPException(404, "없는 메일입니다.")
            if not settings.mail_ai_summary:
                raise HTTPException(400, "메일 본문을 AI로 보내는 기능은 법무 검토 후 관리자가 켭니다.")
            title, text = m["subject"], f"보낸 사람: {m['sender']}\n{m['body']}"
        if not title:
            title = text.split("\n", 1)[0][:80]
        return await asyncio.to_thread(writing.make_draft, db, llm, user, body.source_kind, ref, title, text, body.kind)

    @app.get("/api/drafts")
    def drafts(user: dict = Depends(current_user)):
        return {"items": db.query("SELECT id, source_kind, source_ref, source_title, model, created_at FROM drafts "
                                  "WHERE user_id=? ORDER BY id DESC LIMIT 50", (user["id"],))}

    @app.get("/api/drafts/{draft_id}")
    def draft(draft_id: int, user: dict = Depends(current_user)):
        d = db.one("SELECT * FROM drafts WHERE id=? AND user_id=?", (draft_id, user["id"]))
        if not d:
            raise HTTPException(404, "없는 초안입니다.")
        d["checks"] = json.loads(d.pop("checks_json"))
        d["examples"] = json.loads(d.pop("examples_json"))
        return d

    # --- 스타일북·자사 기사 ------------------------------------------------
    @app.get("/api/stylebook")
    def get_stylebook(user: dict = Depends(current_user)):
        return db.one("SELECT content, source_count, model, updated_at FROM stylebooks WHERE user_id=?",
                      (user["id"],)) or {"content": "", "source_count": 0}

    @app.put("/api/stylebook")
    def put_stylebook(body: StylebookIn, user: dict = Depends(current_user)):
        db.execute("""INSERT INTO stylebooks(user_id, content, source_count, model, updated_at) VALUES(?,?,0,'직접 수정',?)
                      ON CONFLICT(user_id) DO UPDATE SET content=excluded.content, model='직접 수정',
                      updated_at=excluded.updated_at""", (user["id"], body.content, now_iso()))
        return {"ok": True}

    @app.post("/api/stylebook/build")
    async def build_stylebook(user: dict = Depends(current_user)):
        return await asyncio.to_thread(writing.build_stylebook, db, llm, user)

    @app.post("/api/articles/collect")
    async def collect_articles(user: dict = Depends(current_user)):
        rid = (user.get("reporter_id") or "").strip()
        if not rid:
            raise HTTPException(400, "설정에서 기자 ID(이메일 @ 앞부분)를 먼저 등록하세요.")
        key = f"articles:{user['id']}"
        if key in jobs and not jobs[key].done():
            return {"started": False, "message": "이미 수집 중입니다."}

        async def job():
            db.set(key, json.dumps({"state": "running", "added": 0, "checked": 0, "at": now_iso()}))
            try:
                res = await articles.collect_reporter(
                    rid, progress=lambda p, a, c: db.set(key, json.dumps(
                        {"state": "running", "page": p, "added": a, "checked": c, "at": now_iso()})))
                db.set(key, json.dumps({"state": "done", **res, "at": now_iso()}))
            except Exception as e:  # noqa: BLE001
                db.set(key, json.dumps({"state": "error", "error": str(e)[:300], "at": now_iso()}))
                db.log("error", f"articles {rid}: {e!r}")

        jobs[key] = asyncio.create_task(job())
        return {"started": True}

    @app.get("/api/articles/status")
    def articles_status(user: dict = Depends(current_user)):
        raw = db.get(f"articles:{user['id']}")
        n = db.one("SELECT COUNT(*) n FROM articles WHERE author_id=?", ((user.get("reporter_id") or "").lower(),))["n"]
        return {"job": json.loads(raw) if raw else None, "count": n}

    # --- 알리오 ---------------------------------------------------------
    @app.get("/api/alio")
    def alio_view(user: dict = Depends(current_user)):
        return {
            "enabled": settings.alio_enabled, "status": db.get("alio_status", "대기 중"),
            "last_poll_at": db.get("alio_last_poll_at"),
            "orgs": db.query("SELECT apba_id, name, inst_type, dept FROM alio_orgs ORDER BY name"),
            "missing": json.loads(db.get("alio_missing", "[]") or "[]"),
            "finance": finance_overview(db),
        }

    # --- 메일 -----------------------------------------------------------
    def _mail_on():
        if not settings.mail_enabled:
            raise HTTPException(400, "메일 기능은 법무·IT 검토 후 관리자가 켭니다 (.env 의 MAIL_ENABLED).")

    @app.get("/api/mail")
    def mails(q: str = "", user: dict = Depends(current_user)):
        _mail_on()
        sql = "SELECT id, sender, subject, sent_at, embargo, summary, first_seen_at FROM mails WHERE user_id=?"
        params: list = [user["id"]]
        if q:
            sql += " AND (subject LIKE ? ESCAPE '\\' OR sender LIKE ? ESCAPE '\\')"
            params += [_like(q), _like(q)]
        return {"items": db.query(sql + " ORDER BY first_seen_at DESC LIMIT 100", tuple(params))}

    @app.get("/api/mail/{mail_id}")
    def mail_one(mail_id: int, user: dict = Depends(current_user)):
        _mail_on()
        m = db.one("SELECT * FROM mails WHERE id=? AND user_id=?", (mail_id, user["id"]))
        if not m:
            raise HTTPException(404, "없는 메일입니다.")
        return m

    @app.put("/api/mail/account")
    async def mail_account(body: MailAccountIn, user: dict = Depends(current_user)):
        _mail_on()
        acc = {"user_id": user["id"], "host": body.host.strip(), "username": body.username.strip(),
               "secret_enc": vault.seal(body.password), "folder": body.folder.strip(), "last_uid": 0,
               "updated_at": now_iso()}
        try:  # 저장 전에 접속 확인
            await asyncio.to_thread(_probe_mail, acc)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"메일 접속 실패: {e}") from e
        db.execute("""INSERT INTO mail_accounts(user_id, host, username, secret_enc, folder, enabled, last_uid, updated_at)
                      VALUES(:user_id,:host,:username,:secret_enc,:folder,1,0,:updated_at)
                      ON CONFLICT(user_id) DO UPDATE SET host=excluded.host, username=excluded.username,
                      secret_enc=excluded.secret_enc, folder=excluded.folder, enabled=1, last_uid=0,
                      last_error=NULL, updated_at=excluded.updated_at""", acc)
        asyncio.create_task(asyncio.to_thread(mail.poll_all, db, vault))
        return {"ok": True}

    def _probe_mail(acc: dict) -> None:
        import imaplib

        imap = imaplib.IMAP4_SSL(acc["host"])
        try:
            imap.login(acc["username"], vault.open(acc["secret_enc"]))
            status, _ = imap.select(mail.quote_mailbox(acc["folder"]), readonly=True)
            if status != "OK":
                raise RuntimeError(f"메일함 '{acc['folder']}'이 없습니다")
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass

    @app.delete("/api/mail/account")
    def mail_disconnect(user: dict = Depends(current_user)):
        db.execute("DELETE FROM mail_accounts WHERE user_id=?", (user["id"],))
        db.execute("DELETE FROM mails WHERE user_id=?", (user["id"],))
        return {"ok": True}

    # --- 구독·푸시 -------------------------------------------------------
    @app.post("/api/subscriptions")
    def add_sub(body: SubIn, user: dict = Depends(current_user)):
        value = body.value.strip() if body.kind in ("company", "keyword") else ""
        if body.kind in ("company", "keyword") and not value:
            raise HTTPException(400, "기업명 또는 키워드를 입력하세요.")
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
        payload = {"title": "청년의사 브리핑", "body": "테스트 알림입니다. 중요 공시는 이 형식으로 표시됩니다.",
                   "url": settings.public_url + "/", "tag": "test"}
        sent = await asyncio.to_thread(pusher.send_to_user, user["id"], payload, True)
        return {"sent": sent}

    # --- 관리자 ---------------------------------------------------------
    @app.get("/api/admin/users")
    def admin_users(user: dict = Depends(admin_user)):
        rows = db.query("SELECT id, username, display_name, role, active, reporter_id, monthly_limit_krw, created_at "
                        "FROM users ORDER BY id")
        for r in rows:
            r["spent_krw"] = round(llm.month_spent(r["id"]))
            r["limit_krw"] = llm.limit_for(r["id"])
        return {"users": rows}

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

    @app.post("/api/admin/users/{user_id}/limit")
    def admin_limit(user_id: int, body: LimitIn, user: dict = Depends(admin_user)):
        db.execute("UPDATE users SET monthly_limit_krw=? WHERE id=?", (body.krw, user_id))
        return {"ok": True}

    @app.get("/api/admin/status")
    def admin_status(user: dict = Depends(admin_user)):
        return {
            "dart_status": redact(db.get("dart_status", "대기 중")),
            "last_poll_at": db.get("last_poll_at"),
            "dart_calls_today": poller.client.calls_today(),
            "alio_status": db.get("alio_status", "대기 중") if settings.alio_enabled else "꺼짐",
            "alio_last_poll_at": db.get("alio_last_poll_at"),
            "llm": f"{settings.llm_provider} (준비됨)" if llm.available else "키 없음",
            "mail": "켜짐" if settings.mail_enabled else "꺼짐 (법무 검토 후)",
            "alert_mode": settings.alert_mode,
            "digest_status": db.get("digest_status"),
            "backups": sorted(p.name for p in (settings.data_dir / "backups").glob("newsbot-*.db"))[-3:]
            if (settings.data_dir / "backups").exists() else [],
            "events": [{**e, "detail": redact(e["detail"] or "")} for e in
                       db.query("SELECT at, kind, detail FROM events ORDER BY id DESC LIMIT 50")],
        }

    @app.get("/api/admin/metrics")
    def admin_metrics(days: int = 30, user: dict = Depends(admin_user)):
        since = (now() - timedelta(days=max(1, min(days, 365)))).isoformat(timespec="seconds")
        per_user = db.query(
            """SELECT u.id, u.display_name,
                 (SELECT COUNT(*) FROM claims c WHERE c.user_id=u.id AND c.claimed_at>=?) claims,
                 (SELECT COUNT(*) FROM claims c WHERE c.user_id=u.id AND c.written_at>=?) written,
                 (SELECT COUNT(*) FROM chats h WHERE h.user_id=u.id AND h.created_at>=?) questions,
                 (SELECT COUNT(*) FROM drafts d WHERE d.user_id=u.id AND d.created_at>=?) drafts,
                 (SELECT COALESCE(SUM(cost_krw),0) FROM llm_usage l WHERE l.user_id=u.id AND l.at>=?) cost_krw
               FROM users u WHERE u.active=1 ORDER BY u.id""", (since,) * 5)
        totals = {
            "disclosures": db.one("SELECT COUNT(*) n FROM disclosures WHERE first_seen_at>=?", (since,))["n"],
            "red": db.one("SELECT COUNT(*) n FROM disclosures WHERE first_seen_at>=? AND level='red'", (since,))["n"],
            "alerts": db.one("SELECT COUNT(*) n FROM events WHERE kind='alert' AND at>=?", (since,))["n"],
            "poll_errors": db.one("SELECT COUNT(*) n FROM events WHERE kind='error' AND at>=?", (since,))["n"],
            "polls": db.one("SELECT COUNT(*) n FROM events WHERE kind='poll' AND at>=?", (since,))["n"],
            "cost_krw": round(db.one("SELECT COALESCE(SUM(cost_krw),0) s FROM llm_usage WHERE at>=?", (since,))["s"]),
        }
        expected = days * 86400 / settings.poll_interval_sec
        totals["uptime_pct"] = round(min(100.0, totals["polls"] / expected * 100), 1) if settings.dart_api_key else None
        for r in per_user:
            r["cost_krw"] = round(r["cost_krw"])
        return {"days": days, "totals": totals, "users": per_user}

    @app.get("/healthz")
    def healthz():
        """외부 감시 서비스용. 수집·브리핑이 멈췄으면 503과 문제 목록."""
        problems = []
        t = now()

        def age(key: str) -> float | None:
            v = db.get(key)
            return (t - datetime.fromisoformat(v)).total_seconds() if v else None

        uptime = (t - started_at).total_seconds()
        if settings.dart_api_key and not poller.paused():
            a = age("last_poll_at")
            if (a is None and uptime > settings.poll_interval_sec * 4) or (a is not None and a > settings.poll_interval_sec * 4):
                problems.append("dart")
        if settings.alio_enabled and start_poller:
            a = age("alio_last_poll_at")
            limit = settings.alio_poll_hours * 3600 * 2 + 600
            if (a is None and uptime > 1800) or (a is not None and a > limit):
                problems.append("alio")
        if start_poller:
            a = age("digest_checked_at")
            if (a is None and uptime > 600) or (a is not None and a > 600):
                problems.append("digest")
        body = {"ok": not problems, "problems": problems, "last_poll_at": db.get("last_poll_at"),
                "dart": "no_key" if not settings.dart_api_key else ("paused" if poller.paused() else "on")}
        return JSONResponse(body, status_code=503 if problems else 200)

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


__all__ = ["create_app", "Poller", "KST"]
