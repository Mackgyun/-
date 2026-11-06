"""독립 검토(2026-11)에서 확인된 버그의 회귀 테스트."""

import asyncio
import base64
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from newsbot import auth
from newsbot.app import create_app
from newsbot.config import BASE_DIR, Settings, _times
from newsbot.dart import Collector, DartClient, DartError, redact
from newsbot.db import Database, now, now_iso
from newsbot.llm import LLM, OpenAIBackend
from newsbot.mail import Vault, fetch_new, imap_utf7, quote_mailbox
from newsbot.push import Alerter, validate_subscription
from newsbot.rules import Rules
from newsbot.writing import check_numbers

from .test_dart import RULES, FakeDart, item


def _disc(db, no, level="red", seen=None, corr=0, alerted=None):
    db.execute("""INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, keyword,
                  is_correction, watched, first_seen_at, alerted_at) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
               (no, "A", f"회사{no}", "기술이전계약체결", "20261105", level, "기술이전", corr, seen or now_iso(), alerted))


@pytest.fixture()
def app_ctx(tmp_path: Path):
    settings = Settings(db_path=tmp_path / "t.db", data_dir=tmp_path, rules_path=BASE_DIR / "config/rules.toml")
    db = Database(settings.db_path)
    auth.create_user(db, "admin", "관리자", "admin-password-1", role="admin")
    client = TestClient(create_app(settings, db, start_poller=False))
    assert client.post("/api/login", json={"username": "admin", "password": "admin-password-1"}).status_code == 200
    return client, db


# --- B1 인증키 노출 -------------------------------------------------------
def test_dart_http_error_hides_key():
    db = Database(":memory:")
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    client = DartClient("SECRET-KEY-123", db, 1000, http=http)
    with pytest.raises(DartError) as e:
        asyncio.run(client.list_page("20261104", "20261105", 1))
    assert "SECRET-KEY-123" not in str(e.value) and "HTTP500" in str(e.value)
    assert redact("https://x/list.json?crtfc_key=abc&page=1") == "https://x/list.json?crtfc_key=***&page=1"


# --- B2 알림 아웃박스: 기기 하나의 오류·수집 중단에도 알림이 남음 ----------------
class BoomPusher:
    def __init__(self):
        self.sent = []

    def send_to_user(self, uid, payload, force=False):
        self.sent.append((uid, payload["tag"]))
        return 1


def test_alerter_sends_pending_and_marks(tmp_path):
    db = Database(":memory:")
    uid = auth.create_user(db, "kim", "김", "password-12345")
    db.execute("INSERT INTO subscriptions VALUES(?, 'all', '')", (uid,))
    _disc(db, "1")
    _disc(db, "2", level="yellow")
    _disc(db, "3", corr=1)
    _disc(db, "4", alerted="bootstrap")
    p = BoomPusher()
    a = Alerter(db, Rules.load(BASE_DIR / "config/rules.toml"), p, "http://x", notify=True)
    assert asyncio.run(a.flush()) == 1
    assert p.sent == [(uid, "1")]
    assert db.one("SELECT COUNT(*) n FROM disclosures WHERE alerted_at IS NULL")["n"] == 0
    assert asyncio.run(a.flush()) == 0  # 다시 보내지 않음


def test_alerter_batches_many(tmp_path):
    db = Database(":memory:")
    uid = auth.create_user(db, "kim", "김", "password-12345")
    db.execute("INSERT INTO subscriptions VALUES(?, 'all', '')", (uid,))
    for i in range(8):
        _disc(db, str(i))
    p = BoomPusher()
    asyncio.run(Alerter(db, Rules.load(BASE_DIR / "config/rules.toml"), p, "http://x", notify=True).flush())
    assert p.sent == [(uid, "batch")]


def test_pusher_survives_bad_subscription(tmp_path):
    from newsbot.push import Pusher

    db = Database(":memory:")
    uid = auth.create_user(db, "kim", "김", "password-12345")
    pusher = Pusher(db, tmp_path, "mailto:a@b.c", enabled=True)
    # 검증을 거치지 않은 옛 데이터(잘못된 키)가 있어도 예외가 밖으로 나오지 않아야 한다
    db.execute("INSERT INTO push_subs VALUES('https://fcm.googleapis.com/x', ?, '!!bad', '!!bad', 't')", (uid,))
    assert pusher.send_to_user(uid, {"title": "t"}) == 0


def test_partial_poll_rows_still_alerted():
    """1페이지 저장 후 2페이지에서 실패해도 저장된 공시는 아웃박스에 남는다."""
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        page = int(req.url.params["page_no"])
        if page == 2:
            return httpx.Response(503)
        return httpx.Response(200, json={"status": "000", "total_page": 2,
                                         "list": [item("9", "유한양행", "기술이전계약체결")]})

    db = Database(":memory:")
    db.set("bootstrapped", "1")
    col = Collector(DartClient("k", db, 1000, http=httpx.AsyncClient(transport=httpx.MockTransport(handler))), db, RULES)
    with pytest.raises(DartError):
        asyncio.run(col.poll(full=True))
    assert db.one("SELECT alerted_at FROM disclosures WHERE rcept_no='9'")["alerted_at"] is None


def test_bootstrap_rows_are_quiet():
    fake = FakeDart([[item("1", "유한양행", "기술이전계약체결")]])
    db = Database(":memory:")
    col = Collector(DartClient("k", db, 1000, http=httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))), db, RULES)
    asyncio.run(col.poll())
    assert db.one("SELECT alerted_at FROM disclosures")["alerted_at"] == "bootstrap"


# --- B3 같은 시각 공시의 페이지 넘김 ----------------------------------------
def test_feed_cursor_includes_same_timestamp(app_ctx):
    client, db = app_ctx
    t = now_iso()
    for i in range(75):
        _disc(db, f"{i:03d}", seen=t)
    first = client.get("/api/feed?split=all&limit=50").json()["items"]
    last = first[-1]
    rest = client.get("/api/feed", params={"split": "all", "limit": 50,
                                           "before": f"{last['first_seen_at']}|{last['rcept_no']}"}).json()["items"]
    assert len(first) == 50 and len(rest) == 25
    assert not {r["rcept_no"] for r in first} & {r["rcept_no"] for r in rest}


# --- B4 이벤트 보관은 기간 기준 -----------------------------------------------
def test_events_kept_by_age_not_count():
    db = Database(":memory:")
    for _ in range(6000):
        db.log("poll", "x")
    assert db.one("SELECT COUNT(*) n FROM events")["n"] == 6000


# --- B5·B6 메일 ---------------------------------------------------------------
def test_imap_utf7():
    assert imap_utf7("Entwürfe") == "Entw&APw-rfe"
    assert imap_utf7("台北") == "&U,BTFw-"
    assert imap_utf7("A&B") == "A&-B"
    assert quote_mailbox("보도자료").isascii()


class ManyIMAP:
    selected = None

    def __init__(self, host):
        self.uids = list(range(1, 131))

    def login(self, u, p):
        pass

    def select(self, folder, readonly=False):
        ManyIMAP.selected = folder
        return "OK", [b"130"]

    def uid(self, cmd, *args):
        if cmd == "search":
            lo = int(args[1].split()[1].split(":")[0])
            return "OK", [b" ".join(str(u).encode() for u in self.uids if u >= lo)]
        return "OK", [(b"x", b"Subject: s\r\n\r\nbody")]

    def logout(self):
        pass


def test_mail_backlog_not_skipped(tmp_path):
    db = Database(":memory:")
    db.execute("INSERT INTO users(id, username, display_name, pw_hash, created_at) VALUES(1,'a','A','x','t')")
    v = Vault(tmp_path)
    db.execute("INSERT INTO mail_accounts(user_id, host, username, secret_enc, folder, last_uid, updated_at) "
               "VALUES(1,'h','u',?,'보도자료',10,'t')", (v.seal("pw"),))
    acc = lambda: db.one("SELECT * FROM mail_accounts WHERE user_id=1")  # noqa: E731
    assert fetch_new(db, v, acc(), imap_factory=ManyIMAP) == 50
    assert acc()["last_uid"] == 60
    assert fetch_new(db, v, acc(), imap_factory=ManyIMAP) == 50
    assert fetch_new(db, v, acc(), imap_factory=ManyIMAP) == 20
    assert db.one("SELECT COUNT(*) n FROM mails")["n"] == 120
    assert ManyIMAP.selected.isascii()


# --- B7 숫자 대조 -------------------------------------------------------------
def test_check_numbers_exact():
    checks = {c["number"]: c["found"] for c in check_numbers("100억원, 25년, 1,000억", "계약금 1,000억원, 2025년")}
    assert checks == {"100": False, "25": False, "1,000": True}


# --- B8 한도 0원 --------------------------------------------------------------
def test_zero_limit_is_respected(app_ctx):
    client, db = app_ctx
    llm = LLM(Settings(), db)
    db.execute("UPDATE users SET monthly_limit_krw=0 WHERE username='admin'")
    assert llm.limit_for(1) == 0


# --- B11 푸시 주소 검증 -------------------------------------------------------
def _keys():
    p = base64.urlsafe_b64encode(b"\x04" + b"a" * 64).decode().rstrip("=")
    a = base64.urlsafe_b64encode(b"b" * 16).decode().rstrip("=")
    return {"p256dh": p, "auth": a}


def test_push_subscription_validation():
    validate_subscription({"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": _keys()})
    validate_subscription({"endpoint": "https://wns2-sg2p.notify.windows.com/w/?token=x", "keys": _keys()})
    for bad in ("http://127.0.0.1:8000/x", "https://evil.example.com/x", "https://fcm.googleapis.com.evil.com/x"):
        with pytest.raises(ValueError):
            validate_subscription({"endpoint": bad, "keys": _keys()})
    with pytest.raises(ValueError):
        validate_subscription({"endpoint": "https://fcm.googleapis.com/x", "keys": {"p256dh": "AAAA", "auth": "AAAA"}})


# --- B12 알리오 기관·항목 추가 시 과거 공시 조용히 -----------------------------
def test_alio_new_pair_is_quiet():
    from .test_alio import make
    from newsbot.alio import AlioItem

    col, db, fake = make()
    asyncio.run(col.poll())
    fake.susi_rows[("R2", "A1")].append({"title": "이사회 회의록(4차)", "idate": "2026-11-01", "idx": 78})
    assert [r["report_nm"] for r in asyncio.run(col.poll())] == ["[이사회 회의록] 이사회 회의록(4차)"]
    # 감시 항목을 새로 추가: 과거 공시는 알림 없이 저장
    col.config.items.append(AlioItem("기타", "red"))
    fake.susi_rows[("R3", "A1")] = [{"title": "옛 공시", "idate": "2020-01-01", "idx": 1}]
    db.set("alio_items_at", "2000-01-01T00:00:00+09:00")
    assert asyncio.run(col.poll()) == []
    assert db.one("SELECT alerted_at FROM disclosures WHERE report_nm LIKE '%옛 공시%'")["alerted_at"] == "bootstrap"


# --- B15~B19 API 입력 ---------------------------------------------------------
def test_api_input_checks(app_ctx):
    client, db = app_ctx
    _disc(db, "X1")
    _disc(db, "G1", level="gray")
    assert client.post("/api/done/NOPE").status_code == 404
    client.post("/api/claims/X1")
    r = client.post("/api/claims/X1/written", json={"url": "javascript:alert(1)"})
    assert r.status_code == 422
    assert client.post("/api/claims/X1/written", json={"url": "https://www.docdocdoc.co.kr/news/1"}).status_code == 200
    r = client.post("/api/drafts", json={"source_kind": "mail", "source_ref": "abc"})
    assert r.status_code == 400
    # '%' 는 글자 그대로 검색
    assert client.get("/api/feed?split=all&q=%25").json()["items"] == []
    # 내 담당: 기록 등급도 개수와 목록이 같아야 함
    client.post("/api/claims/G1")
    assert client.get("/api/counts").json()["mine"] == len(client.get("/api/feed?split=mine").json()["items"]) == 2


# --- B20 터널 뒤 로그인 잠금은 실제 IP 기준 ----------------------------------
def test_login_lock_uses_forwarded_ip(app_ctx):
    client, db = app_ctx
    inner = client.app

    async def from_loopback(scope, receive, send):  # 같은 PC의 터널(cloudflared)을 거쳐 온 요청
        if scope["type"] == "http":
            scope = {**scope, "client": ("127.0.0.1", 50000)}
        await inner(scope, receive, send)

    tunnel = TestClient(from_loopback)
    for _ in range(5):
        tunnel.post("/api/login", json={"username": "admin", "password": "wrong-password"},
                    headers={"CF-Connecting-IP": "203.0.113.9"})
    bad = tunnel.post("/api/login", json={"username": "admin", "password": "admin-password-1"},
                      headers={"CF-Connecting-IP": "203.0.113.9"})
    assert bad.status_code == 429  # 공격한 IP는 잠김
    ok = tunnel.post("/api/login", json={"username": "admin", "password": "admin-password-1"},
                     headers={"CF-Connecting-IP": "198.51.100.1"})
    assert ok.status_code == 200  # 다른 곳의 진짜 사용자는 로그인됨


# --- B10 설정 오류 -----------------------------------------------------------
def test_digest_times_validated():
    assert _times("8:00, 13:30") == ("08:00", "13:30")
    with pytest.raises(SystemExit):
        _times("8시")


# --- B21 일일 한도 초과 시 자정까지 쉼 ---------------------------------------
def test_limit_pauses_until_tomorrow(tmp_path):
    from newsbot.app import Poller
    from newsbot.push import Pusher

    db = Database(":memory:")
    fake = FakeDart([], status="020")
    s = Settings(dart_api_key="k", data_dir=tmp_path)
    rules = Rules.load(BASE_DIR / "config/rules.toml")
    poller = Poller(s, db, rules, Alerter(db, rules, Pusher(db, tmp_path, "mailto:a@b.c", False), "http://x", False))
    poller.client.http = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    asyncio.run(poller.run_once())
    assert poller.paused() and len(fake.calls) == 1
    asyncio.run(poller.run_once())
    assert len(fake.calls) == 1  # 쉬는 동안 호출하지 않음


# --- B25 꺼져 있던 기간 이어서 수집 ------------------------------------------
def test_catch_up_from_last_ok_date():
    seen = []

    def handler(req):
        seen.append(req.url.params["bgn_de"])
        return httpx.Response(200, json={"status": "013", "list": []})

    db = Database(":memory:")
    db.set("bootstrapped", "1")
    db.set("dart_last_ok_date", (now() - timedelta(days=4)).strftime("%Y%m%d"))
    col = Collector(DartClient("k", db, 1000, http=httpx.AsyncClient(transport=httpx.MockTransport(handler))), db, RULES)
    asyncio.run(col.poll())
    assert seen[0] == (now() - timedelta(days=4)).strftime("%Y%m%d")
    assert db.get("dart_last_ok_date") == now().strftime("%Y%m%d")


# --- B26 기자당 동시 AI 요청 1건 ----------------------------------------------
def test_one_llm_request_per_user(app_ctx):
    _, db = app_ctx
    import threading

    gate = threading.Event()

    class Slow:
        name = "claude"

        def complete(self, model, system, prompt, tier):
            gate.wait(2)
            from newsbot.llm import Usage
            return "ok", [Usage(1, 1)]

    llm = LLM(Settings(llm_provider="claude", anthropic_api_key="x"), db, backend=Slow())
    t = threading.Thread(target=lambda: llm.complete("s", "p", "fast", 1, "t"))
    t.start()
    import time
    time.sleep(0.1)
    from newsbot.llm import LLMError
    with pytest.raises(LLMError):
        llm.complete("s", "p", "fast", 1, "t")
    gate.set()
    t.join()


# --- 무료 API (Gemini 무료 등급·Ollama) --------------------------------------
class FakeOpenAI:
    def __init__(self):
        self.kwargs = None
        outer = self

        class Completions:
            def create(self, **kw):
                outer.kwargs = kw

                class Msg:
                    content = "답"
                    tool_calls = None

                class Choice:
                    message = Msg()

                class U:
                    prompt_tokens, completion_tokens = 10, 5

                class R:
                    choices = [Choice()]
                    usage = U()
                return R()

        class Chat:
            completions = Completions()

        self.chat = Chat()


def test_gemini_free_provider(tmp_path):
    db = Database(":memory:")
    s = Settings(llm_provider="gemini", gemini_api_key="g")
    assert s.llm_ready
    fake = FakeOpenAI()
    llm = LLM(s, db, backend=OpenAIBackend("g", client=fake, name="gemini"))
    text, model = llm.complete("sys", "질문", "main", None, "test")
    assert text == "답" and model == "gemini-3.8-flash"
    assert "max_tokens" in fake.kwargs and "max_completion_tokens" not in fake.kwargs
    assert db.one("SELECT cost_krw FROM llm_usage")["cost_krw"] == 0


def test_ollama_needs_no_key():
    s = Settings(llm_provider="ollama")
    assert s.llm_ready
    llm = LLM(s, Database(":memory:"))
    assert llm.backend.name == "ollama" and llm.model_for("fast") == "qwen3:8b"
