"""PC 알림 프로그램: 로그인 → 롱폴링으로 알림 받기 → 연결 해제."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from newsbot import auth
from newsbot.app import create_app
from newsbot.config import BASE_DIR, Settings
from newsbot.db import Database, now_iso

BASE = "http://localhost:8000"


@pytest.fixture()
def env(tmp_path: Path):
    settings = Settings(db_path=tmp_path / "t.db", data_dir=tmp_path, rules_path=BASE_DIR / "config/rules.toml",
                        public_url=BASE, alert_mode="notify")
    db = Database(settings.db_path)
    uid = auth.create_user(db, "reporter", "기자", "reporter-password-1")
    other = auth.create_user(db, "other", "다른기자", "other-password-12")
    app = create_app(settings, db, start_poller=False)
    with TestClient(app, base_url=BASE) as client:
        yield client, db, uid, other, app


def device_login(client, username="reporter", password="reporter-password-1"):
    return client.post("/api/device/login", json={"username": username, "password": password, "name": "편집국 PC"})


def test_login_and_receive_alerts(env):
    client, db, uid, other, _ = env
    assert device_login(client, password="wrong-password").status_code == 401
    r = device_login(client)
    assert r.status_code == 200
    token, last = r.json()["token"], r.json()["last_id"]
    h = {"Authorization": f"Bearer {token}"}
    # 토큰은 해시로만 저장
    assert db.one("SELECT token_hash FROM devices")["token_hash"] != token

    # 알림이 없으면 기다렸다가 빈 목록
    r = client.get(f"/api/device/alerts?after={last}&wait=0", headers=h)
    assert r.status_code == 200 and r.json()["items"] == []

    # 브라우저 구독이 없어도 PC 프로그램에는 간다 (웹 '테스트 발송'과 같은 경로)
    client.post("/api/login", json={"username": "reporter", "password": "reporter-password-1"})
    assert client.post("/api/push/test").json()["sent"] == 1
    items = client.get(f"/api/device/alerts?after={last}&wait=0", headers=h).json()["items"]
    assert len(items) == 1 and items[0]["title"] == "청년의사 브리핑" and items[0]["url"].startswith(BASE)

    # 이미 받은 것은 다시 오지 않음
    r = client.get(f"/api/device/alerts?after={items[0]['id']}&wait=0", headers=h).json()
    assert r["items"] == [] and r["last_id"] == items[0]["id"]

    # 설정 화면에 기기가 보이고, 다른 사람 알림은 섞이지 않음
    me = client.get("/api/me").json()
    assert [d["name"] for d in me["pc_devices"]] == ["편집국 PC"] and me["pc_devices"][0]["last_seen_at"]
    other_token = device_login(client, "other", "other-password-12").json()["token"]
    assert client.get("/api/device/alerts?after=0&wait=0",
                      headers={"Authorization": f"Bearer {other_token}"}).json()["items"] == []


def test_real_disclosure_alert_reaches_pc_program(env):
    client, db, uid, _, app = env
    token = device_login(client).json()["token"]
    db.execute("INSERT OR IGNORE INTO subscriptions(user_id, kind, value) VALUES(?, 'watch', '')", (uid,))
    db.execute(
        """INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, keyword,
           is_correction, watched, first_seen_at) VALUES('20261125000009','A','유한양행','기술이전계약체결',
           '20261125','red','기술이전',0,1,?)""", (now_iso(),))
    alerter = app.state.alerter if hasattr(app.state, "alerter") else None
    if alerter is None:
        pytest.skip("alerter 를 app.state 에서 찾지 못함")
    client.portal.call(alerter.flush)
    items = client.get("/api/device/alerts?after=0&wait=0", headers={"Authorization": f"Bearer {token}"}).json()["items"]
    assert items and items[0]["title"].startswith("유한양행") and items[0]["body"] == "기술이전계약체결"


def test_logout_and_revoke(env):
    client, db, *_ = env
    token = device_login(client).json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/device/alerts?wait=0").status_code == 401
    # 프로그램 메뉴의 '테스트 알림 받기'
    assert client.post("/api/device/test", headers=h).json()["sent"] == 1
    assert client.get("/api/device/alerts?after=0&wait=0", headers=h).json()["items"][0]["tag"] == "test"
    assert client.delete("/api/device", headers=h).status_code == 200
    assert client.get("/api/device/alerts?wait=0", headers=h).status_code == 401

    token = device_login(client).json()["token"]
    client.post("/api/login", json={"username": "reporter", "password": "reporter-password-1"})
    dev = client.get("/api/me").json()["pc_devices"][0]
    assert client.delete(f"/api/devices/{dev['id']}").status_code == 200
    assert client.get("/api/device/alerts?wait=0", headers={"Authorization": f"Bearer {token}"}).status_code == 401
