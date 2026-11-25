"""원격 MCP: OAuth 연결(등록 → 로그인·허용 → 토큰)과 도구 호출."""

import base64
import hashlib
import json
import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

# Claude·ChatGPT 커넥터가 널리 쓰는 initialize 방식 버전 (2026-07-28 판은 요청마다 _meta 봉투를 붙인다)
LATEST_PROTOCOL_VERSION = "2025-11-25"

from newsbot import auth
from newsbot.app import create_app
from newsbot.config import BASE_DIR, Settings
from newsbot.db import Database, now_iso

BASE = "http://localhost:8000"
REDIRECT = "http://localhost:3333/callback"


@pytest.fixture()
def env(tmp_path: Path):
    settings = Settings(db_path=tmp_path / "t.db", data_dir=tmp_path, rules_path=BASE_DIR / "config/rules.toml",
                        public_url=BASE)
    db = Database(settings.db_path)
    uid = auth.create_user(db, "reporter", "기자", "reporter-password-1")
    db.execute(
        """INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, keyword,
           is_correction, watched, first_seen_at) VALUES('20261105000001','A','유한양행','기술이전계약체결',
           '20261105','red','기술이전',0,1,?)""", (now_iso(),))
    app = create_app(settings, db, start_poller=False)
    with TestClient(app, base_url=BASE) as client:
        yield client, db, uid


def register(client, redirect=REDIRECT):
    return client.post("/register", json={"redirect_uris": [redirect], "client_name": "Claude",
                                          "token_endpoint_auth_method": "none",
                                          "grant_types": ["authorization_code", "refresh_token"],
                                          "response_types": ["code"]})


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def start_authorize(client, client_id, challenge):
    r = client.get("/authorize", params={"response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
                                         "code_challenge": challenge, "code_challenge_method": "S256",
                                         "state": "st-1", "scope": "briefing"}, follow_redirects=False)
    assert r.status_code == 302, r.text
    loc = urlparse(r.headers["location"])
    assert loc.path == "/oauth/consent"
    return parse_qs(loc.query)["req"][0]


def connect(client, password="reporter-password-1"):
    """등록부터 토큰까지. (토큰 응답, client_id)"""
    client_id = register(client).json()["client_id"]
    verifier, challenge = pkce()
    req = start_authorize(client, client_id, challenge)
    r = client.post("/oauth/consent", data={"req": req, "action": "allow", "username": "reporter",
                                            "password": password}, follow_redirects=False)
    assert r.status_code == 302, r.text
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["state"] == ["st-1"]
    tok = client.post("/token", data={"grant_type": "authorization_code", "code": q["code"][0],
                                      "redirect_uri": REDIRECT, "client_id": client_id, "code_verifier": verifier})
    assert tok.status_code == 200, tok.text
    return tok.json(), client_id, q["code"][0], verifier


def rpc(client, token, method, params=None, id_=1):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream",
               "Content-Type": "application/json", "MCP-Protocol-Version": LATEST_PROTOCOL_VERSION}
    body = {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}
    return client.post("/mcp", headers=headers, content=json.dumps(body))


def init(client, token):
    return rpc(client, token, "initialize", {"protocolVersion": LATEST_PROTOCOL_VERSION, "capabilities": {},
                                             "clientInfo": {"name": "test", "version": "1"}})


def test_metadata_and_unauthenticated(env):
    client, _, _ = env
    meta = client.get("/.well-known/oauth-authorization-server").json()
    assert meta["registration_endpoint"].endswith("/register")
    assert "S256" in meta["code_challenge_methods_supported"]
    prm = client.get("/.well-known/oauth-protected-resource/mcp")
    assert prm.status_code == 200 and prm.json()["resource"] == BASE + "/mcp"
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401
    assert "resource_metadata" in r.headers.get("www-authenticate", "")
    # 기존 화면 경로는 그대로
    assert client.get("/").status_code == 200
    assert client.get("/api/feed").status_code == 401


def test_register_rejects_unknown_redirect(env):
    client, _, _ = env
    assert register(client, "https://evil.example/cb").status_code == 400
    assert register(client, "http://claude.ai/cb").status_code == 400  # 외부 주소는 https 만
    assert register(client, "https://claude.ai/api/mcp/auth_callback").status_code == 201


def test_full_flow_and_tools(env):
    client, db, uid = env
    tok, _, _, _ = connect(client)
    assert tok["token_type"] == "Bearer" and tok["refresh_token"]
    # 토큰 원문은 DB에 남지 않는다
    assert not db.one("SELECT 1 FROM oauth_tokens WHERE token_hash=?", (tok["access_token"],))

    access = tok["access_token"]
    r = init(client, access)
    assert r.status_code == 200, r.text
    assert r.json()["result"]["serverInfo"]["name"] == "chungnyun-briefing"

    names = {t["name"] for t in rpc(client, access, "tools/list").json()["result"]["tools"]}
    assert {"search_disclosures", "get_disclosure", "company_history", "writing_guide",
            "check_draft_numbers", "today_overview"} <= names

    r = rpc(client, access, "tools/call", {"name": "search_disclosures", "arguments": {"query": "유한양행"}})
    text = r.json()["result"]["content"][0]["text"]
    assert "유한양행" in text and "기술이전계약체결" in text

    r = rpc(client, access, "tools/call", {"name": "check_draft_numbers",
                                           "arguments": {"draft": "계약금 300억원, 총 1,200억원", "source": "총 1,200억원"}})
    out = json.loads(r.json()["result"]["content"][0]["text"])
    assert [m["number"] for m in out["not_in_source"]] == ["300"]

    r = rpc(client, access, "tools/call", {"name": "writing_guide", "arguments": {"topic": "기술이전"}})
    assert "스타일북" in json.loads(r.json()["result"]["content"][0]["text"])["stylebook"]

    # 사용 기록과 연결 목록
    assert db.one("SELECT COUNT(*) n FROM events WHERE kind='mcp'")["n"] >= 3
    client.post("/api/login", json={"username": "reporter", "password": "reporter-password-1"})
    info = client.get("/api/mcp").json()
    assert info["url"] == BASE + "/mcp" and info["connections"][0]["client_name"] == "Claude"


def test_new_protocol_without_initialize(env):
    """2026-07-28 판: initialize 없이 요청마다 _meta 봉투를 붙인다."""
    client, _, _ = env
    tok, *_ = connect(client)
    meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientCapabilities": {}}
    h = {"Authorization": "Bearer " + tok["access_token"], "Accept": "application/json, text/event-stream",
         "Content-Type": "application/json", "MCP-Protocol-Version": "2026-07-28",
         "Mcp-Method": "tools/call", "Mcp-Name": "search_disclosures"}
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"_meta": meta, "name": "search_disclosures", "arguments": {"query": "유한양행"}}}
    r = client.post("/mcp", headers=h, content=json.dumps(body))
    assert r.status_code == 200, r.text
    assert "유한양행" in r.json()["result"]["content"][0]["text"]


def test_code_single_use_and_wrong_verifier(env):
    client, _, _ = env
    _, client_id, code, verifier = connect(client)
    again = client.post("/token", data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
                                        "client_id": client_id, "code_verifier": verifier})
    assert again.status_code == 400

    v2, c2 = pkce()
    req = start_authorize(client, client_id, c2)
    r = client.post("/oauth/consent", data={"req": req, "action": "allow", "username": "reporter",
                                            "password": "reporter-password-1"}, follow_redirects=False)
    code2 = parse_qs(urlparse(r.headers["location"]).query)["code"][0]
    bad = client.post("/token", data={"grant_type": "authorization_code", "code": code2, "redirect_uri": REDIRECT,
                                      "client_id": client_id, "code_verifier": "x" * 50})
    assert bad.status_code == 400


def test_wrong_password_and_deny(env):
    client, _, _ = env
    client_id = register(client).json()["client_id"]
    _, challenge = pkce()
    req = start_authorize(client, client_id, challenge)
    page = client.get("/oauth/consent", params={"req": req})
    assert page.status_code == 200 and "Claude" in page.text and "localhost" in page.text
    r = client.post("/oauth/consent", data={"req": req, "action": "allow", "username": "reporter",
                                            "password": "wrong-password"}, follow_redirects=False)
    assert r.status_code == 401
    r = client.post("/oauth/consent", data={"req": req, "action": "deny"}, follow_redirects=False)
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["error"] == ["access_denied"] and q["state"] == ["st-1"]
    # 한 번 처리한 요청은 다시 못 씀
    assert client.get("/oauth/consent", params={"req": req}).status_code == 410


def test_refresh_rotation_and_revocation(env):
    client, db, uid = env
    tok, client_id, _, _ = connect(client)
    new = client.post("/token", data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                                      "client_id": client_id})
    assert new.status_code == 200, new.text
    # 옛 새로고침 토큰·접근 토큰은 함께 폐기
    old = client.post("/token", data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                                      "client_id": client_id})
    assert old.status_code == 400
    assert init(client, tok["access_token"]).status_code == 401
    access = new.json()["access_token"]
    assert init(client, access).status_code == 200

    # 계정을 비활성화하면 바로 막힘
    db.execute("UPDATE users SET active=0 WHERE id=?", (uid,))
    assert init(client, access).status_code == 401
    db.execute("UPDATE users SET active=1 WHERE id=?", (uid,))
    assert init(client, access).status_code == 200

    # 설정 화면의 '연결 끊기'
    client.post("/api/login", json={"username": "reporter", "password": "reporter-password-1"})
    assert client.delete("/api/mcp/connections").json()["removed"] >= 2
    assert init(client, access).status_code == 401


def test_mcp_disabled(tmp_path: Path):
    settings = Settings(db_path=tmp_path / "t.db", data_dir=tmp_path, rules_path=BASE_DIR / "config/rules.toml",
                        mcp_enabled=False)
    with TestClient(create_app(settings, Database(settings.db_path), start_poller=False)) as client:
        assert client.post("/mcp", json={}).status_code in (404, 405)
        assert client.get("/.well-known/oauth-authorization-server").status_code == 404
