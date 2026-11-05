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
