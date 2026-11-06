from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from newsbot import auth
from newsbot.app import create_app
from newsbot.config import BASE_DIR, Settings
from newsbot.db import Database, now_iso


@pytest.fixture()
def ctx(tmp_path: Path):
    settings = Settings(db_path=tmp_path / "t.db", data_dir=tmp_path, rules_path=BASE_DIR / "config/rules.toml")
    db = Database(settings.db_path)
    admin_id = auth.create_user(db, "admin", "관리자", "admin-password-1", role="admin")
    app = create_app(settings, db, start_poller=False)
    db.execute(
        """INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, keyword,
           is_correction, watched, first_seen_at) VALUES('20261105000001','A','유한양행','기술이전계약체결',
           '20261105','red','기술이전',0,1,?)""", (now_iso(),))
    return TestClient(app), db, admin_id


def login(client, username="admin", password="admin-password-1"):
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r


def test_requires_login(ctx):
    client, _, _ = ctx
    assert client.get("/api/feed").status_code == 401
    assert client.get("/").status_code == 200  # 화면은 열림


def test_feed_summary_and_claim(ctx):
    client, db, _ = ctx
    login(client)
    feed = client.get("/api/feed").json()["items"]
    assert feed[0]["corp_name"] == "유한양행" and feed[0]["url"].endswith("rcpNo=20261105000001")
    s = client.get("/api/summary").json()
    assert s["red"] == 1 and s["unclaimed_top"] == 1
    assert client.post("/api/claims/20261105000001").status_code == 200
    assert client.get("/api/summary").json()["my_claims"] == 1
    assert client.get("/api/feed?mine=1").json()["items"][0]["claimed_name"] == "관리자"


def test_invite_register_and_claim_conflict(ctx):
    client, db, _ = ctx
    login(client)
    url = client.post("/api/admin/invites", json={"role": "reporter"}).json()["url"]
    code = url.rsplit("/", 1)[1]
    client.post("/api/claims/20261105000001")

    other = TestClient(client.app)
    r = other.post("/api/register", json={"code": code, "username": "kim", "display_name": "김기자",
                                          "password": "short"})
    assert r.status_code == 400  # 비밀번호 너무 짧음
    r = other.post("/api/register", json={"code": code, "username": "kim", "display_name": "김기자",
                                          "password": "reporter-pass-1"})
    assert r.status_code == 200
    assert other.post("/api/claims/20261105000001").status_code == 409
    assert other.get("/api/admin/users").status_code == 403
    # 같은 초대 코드는 다시 못 씀
    third = TestClient(client.app)
    r = third.post("/api/register", json={"code": code, "username": "lee", "display_name": "이기자",
                                          "password": "reporter-pass-2"})
    assert r.status_code == 400
    me = other.get("/api/me").json()
    assert {"kind": "watch", "value": ""} in me["subscriptions"]


def test_login_lockout(ctx):
    client, _, _ = ctx
    for _ in range(5):
        assert client.post("/api/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"username": "admin", "password": "admin-password-1"}).status_code == 429


def test_subscriptions_and_push_key(ctx):
    client, _, _ = ctx
    login(client)
    assert client.post("/api/subscriptions", json={"kind": "company", "value": ""}).status_code == 400
    assert client.post("/api/subscriptions", json={"kind": "keyword", "value": "기술이전"}).status_code == 200
    assert {"kind": "keyword", "value": "기술이전"} in client.get("/api/me").json()["subscriptions"]
    key = client.get("/api/push/key").json()["key"]
    assert len(key) > 80
    assert client.post("/api/push/test").json()["sent"] == 0  # 등록 기기 없음


def test_security_headers_and_health(ctx):
    client, _, _ = ctx
    r = client.get("/")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert client.get("/healthz").json()["ok"] is True
    assert client.get("/sw.js").status_code == 200
    assert client.get("/manifest.webmanifest").status_code == 200


def test_recipients():
    from newsbot.push import recipients
    from newsbot.rules import Rules

    db = Database(":memory:")
    a = auth.create_user(db, "a", "A", "password-123")
    b = auth.create_user(db, "b", "B", "password-123")
    c = auth.create_user(db, "c", "C", "password-123")
    db.execute("INSERT INTO subscriptions VALUES(?, 'company', '유한 양행')", (a,))
    db.execute("INSERT INTO subscriptions VALUES(?, 'keyword', '기술이전')", (b,))
    db.execute("INSERT INTO subscriptions VALUES(?, 'company', '한미약품')", (c,))
    row = {"corp_name": "유한양행", "report_nm": "기술이전계약체결", "watched": 1}
    assert recipients(db, Rules(), row) == [a, b]


class FakeBackend:
    name = "claude"

    def __init__(self):
        self.prompts = []

    def complete(self, model, system, prompt, tier):
        from newsbot.llm import Usage
        self.prompts.append((system, prompt))
        return "제목\n\n유한양행이 기술이전 계약을 맺었다. 계약금은 500억원이다.", [Usage(1000, 300)]

    def agent(self, model, system, history, tools, tier, max_steps):
        from newsbot.llm import Usage
        names = [t.name for t in tools]
        out = next(t for t in tools if t.name == "search_disclosures").func({"query": "유한양행"})
        return f"찾은 공시 {len(out)}건 (도구: {','.join(names)})", [{"tool": "search_disclosures", "input": {}, "output": ""}], [Usage(10, 10)]


@pytest.fixture()
def ai(tmp_path: Path):
    from newsbot.llm import LLM

    settings = Settings(db_path=tmp_path / "t.db", data_dir=tmp_path, rules_path=BASE_DIR / "config/rules.toml",
                        alio_path=BASE_DIR / "config/alio.toml", llm_provider="claude")
    db = Database(settings.db_path)
    auth.create_user(db, "admin", "관리자", "admin-password-1", role="admin")
    backend = FakeBackend()
    app = create_app(settings, db, start_poller=False, llm=LLM(settings, db, backend=backend))
    db.execute("""INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, keyword,
               is_correction, watched, first_seen_at) VALUES('20261105000001','A','유한양행','기술이전계약체결',
               '20261105','red','기술이전',0,1,?)""", (now_iso(),))
    client = TestClient(app)
    login(client)
    return client, db, backend


def test_ask_and_history(ai):
    client, db, _ = ai
    r = client.post("/api/ask", json={"question": "유한양행 오늘 공시?"})
    assert r.status_code == 200, r.text
    assert "찾은 공시 1건" in r.json()["answer"] and "search_my_mail" not in r.json()["answer"]
    assert client.get("/api/chats").json()["items"][0]["question"] == "유한양행 오늘 공시?"


def test_draft_from_text_with_checks(ai):
    client, db, backend = ai
    r = client.post("/api/drafts", json={"source_kind": "text", "title": "보도자료",
                                         "text": "유한양행은 오늘 기술이전 계약을 체결했다고 밝혔다. 계약 규모는 공개하지 않았다. " * 2})
    assert r.status_code == 200, r.text
    d = r.json()
    assert {"number": "500", "found": False} == {k: d["checks"][0][k] for k in ("number", "found")}
    assert "아직 이 기자의 스타일북이 없습니다" in backend.prompts[-1][0]
    assert client.get(f"/api/drafts/{d['id']}").json()["source_title"] == "보도자료"


def test_draft_from_disclosure_and_written(ai):
    client, db, _ = ai
    r = client.post("/api/drafts", json={"source_kind": "disclosure", "source_ref": "20261105000001"})
    assert r.status_code == 400 and "원문" in r.json()["detail"]  # DART 키 없고 메모도 없음
    r = client.post("/api/drafts", json={"source_kind": "disclosure", "source_ref": "20261105000001",
                                         "text": "회사 IR팀 확인: 계약 상대는 미국 바이오텍, 임상 1상 단계"})
    assert r.status_code == 200, r.text
    assert client.post("/api/claims/20261105000001/written", json={"url": "https://x/1"}).status_code == 400
    client.post("/api/claims/20261105000001")
    assert client.post("/api/claims/20261105000001/written", json={"url": "https://x/1"}).status_code == 200
    m = client.get("/api/admin/metrics").json()
    assert m["users"][0]["written"] == 1 and m["users"][0]["drafts"] == 1 and m["users"][0]["cost_krw"] > 0


def test_stylebook_put_and_build_requires_articles(ai):
    client, _, _ = ai
    assert client.post("/api/stylebook/build").status_code == 400  # 기자 ID 없음
    client.post("/api/me/reporter", json={"reporter_id": "admin1"})
    r = client.post("/api/stylebook/build")
    assert r.status_code == 400 and "5편" in r.json()["detail"]
    assert client.put("/api/stylebook", json={"content": "리드는 짧게 쓴다. 인용은 밝혔다로."}).status_code == 200
    assert "리드는 짧게" in client.get("/api/stylebook").json()["content"]


def test_mail_disabled_and_alio_view(ai):
    client, _, _ = ai
    assert client.get("/api/mail").status_code == 400
    v = client.get("/api/alio").json()
    assert v["enabled"] is True and v["finance"] == []
    assert client.get("/api/me").json()["llm_ready"] is True


def test_alio_ids_with_colons_work(ai):
    client, db, _ = ai
    db.execute("""INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, first_seen_at,
               source, link) VALUES('alio:R1:D1','A1','서울대학교병원','[손익계산서] 결산','20261101','red',?, 'alio','https://www.alio.go.kr/x')""",
               (now_iso(),))
    assert client.get("/api/disclosures/alio:R1:D1").json()["url"] == "https://www.alio.go.kr/x"
    assert client.post("/api/claims/alio:R1:D1").status_code == 200


def test_splits_done_and_counts(ctx):
    client, db, _ = ctx
    login(client)
    db.execute("""INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, is_correction,
               watched, first_seen_at) VALUES('2','B','한미약품','분기보고서','20261105','yellow',0,0,?)""", (now_iso(),))
    c = client.get("/api/counts").json()
    assert c["inbox"] == 2 and c["red"] == 1 and c["unclaimed"] == 1 and c["beat"] == 0
    client.post("/api/subscriptions", json={"kind": "company", "value": "한미 약품"})
    assert [i["corp_name"] for i in client.get("/api/feed?split=beat").json()["items"]] == ["한미약품"]
    assert client.post("/api/done/20261105000001").status_code == 200
    assert [i["rcept_no"] for i in client.get("/api/feed?split=inbox").json()["items"]] == ["2"]
    assert client.get("/api/counts").json()["red"] == 0
    client.delete("/api/done/20261105000001")  # 되돌리기
    assert client.get("/api/counts").json()["inbox"] == 2
    r = client.post("/api/done-all?split=inbox").json()
    assert r["done"] == 2 and client.get("/api/counts").json()["inbox"] == 0
    assert len(client.get("/api/feed?split=all").json()["items"]) == 2
