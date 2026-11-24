"""기업 히스토리, 기업 구독 수집·알림 범위."""

import asyncio
import io
import zipfile
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from newsbot import auth, company
from newsbot.app import create_app
from newsbot.config import BASE_DIR, Settings
from newsbot.dart import Collector, DartClient
from newsbot.db import Database, now_iso
from newsbot.push import Alerter
from newsbot.rules import Rules

from .test_dart import RULES, item

CORP_XML = """<?xml version="1.0" encoding="UTF-8"?><result>
<list><corp_code>00126380</corp_code><corp_name>유한양행</corp_name><stock_code>000100</stock_code><modify_date>20260101</modify_date></list>
<list><corp_code>00999999</corp_code><corp_name>유한양행헬스케어</corp_name><stock_code> </stock_code><modify_date>20260101</modify_date></list>
<list><corp_code>00555555</corp_code><corp_name>한미약품</corp_name><stock_code>128940</stock_code><modify_date>20260101</modify_date></list>
</result>"""


def corp_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("CORPCODE.xml", CORP_XML)
    return buf.getvalue()


class FakeDart:
    def __init__(self):
        self.calls = []

    def handler(self, req: httpx.Request):
        p = req.url.path
        self.calls.append(p)
        if p.endswith("corpCode.xml"):
            return httpx.Response(200, content=corp_zip())
        if p.endswith("list.json"):
            assert req.url.params["corp_code"] == "00126380"
            page = int(req.url.params["page_no"])
            lst = [
                [{"rcept_no": "20240301000001", "corp_name": "유한양행", "report_nm": "투자판단관련주요경영사항(기술이전계약체결)",
                  "rcept_dt": "20240301", "flr_nm": "유한양행", "rm": ""},
                 {"rcept_no": "20240302000001", "corp_name": "유한양행", "report_nm": "임원ㆍ주요주주특정증권등소유상황보고서",
                  "rcept_dt": "20240302", "flr_nm": "홍길동", "rm": ""}],
                [{"rcept_no": "20250101000001", "corp_name": "유한양행", "report_nm": "기업설명회(IR)개최(안내공시)",
                  "rcept_dt": "20250101", "flr_nm": "유한양행", "rm": "유"}],
            ]
            return httpx.Response(200, json={"status": "000", "total_page": 2, "list": lst[page - 1]})
        if p.endswith("fnlttSinglAcnt.json"):
            rows = [{"fs_div": "CFS", "account_nm": a, "corp_name": "유한양행", "thstrm_amount": t, "frmtrm_amount": f,
                     "bfefrmtrm_amount": b} for a, t, f, b in (("매출액", "2,000,000,000,000", "1,900,000,000,000", "1,800,000,000,000"),
                                                               ("영업이익", "100,000,000,000", "50,000,000,000", "-1,000,000"))]
            return httpx.Response(200, json={"status": "000", "list": rows})
        return httpx.Response(404)


@pytest.fixture()
def ctx(tmp_path: Path):
    settings = Settings(db_path=tmp_path / "t.db", data_dir=tmp_path, rules_path=BASE_DIR / "config/rules.toml",
                        dart_api_key="k")
    db = Database(settings.db_path)
    auth.create_user(db, "admin", "관리자", "admin-password-1", role="admin")
    app = create_app(settings, db, start_poller=False)
    fake = FakeDart()
    app.state.poller.client.http = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    client = TestClient(app)
    assert client.post("/api/login", json={"username": "admin", "password": "admin-password-1"}).status_code == 200
    return client, db, fake


def test_find_companies_listed_first(ctx):
    client, _, _ = ctx
    items = client.get("/api/companies", params={"q": "유한"}).json()["items"]
    assert [i["corp_name"] for i in items] == ["유한양행", "유한양행헬스케어"]
    assert items[0]["stock_code"] == "000100"


def test_company_history_merges_and_caches(ctx):
    client, db, fake = ctx
    db.execute("""INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, is_correction, watched,
                  first_seen_at) VALUES('20250101000001','00126380','유한양행','기업설명회(IR)개최(안내공시)','20250101','yellow',0,1,?)""",
               (now_iso(),))
    h = client.get("/api/company", params={"name": "유한 양행", "years": 5}).json()
    assert h["company"]["corp_code"] == "00126380"
    assert [f["rcept_no"] for f in h["filings"]] == ["20250101000001", "20240302000001", "20240301000001"]
    assert h["filings"][0]["in_feed"] and not h["filings"][2]["in_feed"]
    assert h["filings"][2]["level"] == "red"
    assert h["financials"]["rows"][0]["values"][0]["amount"] == 2_000_000_000_000
    n = fake.calls.count("/api/list.json")
    client.get("/api/company", params={"name": "유한양행", "years": 5})
    assert fake.calls.count("/api/list.json") == n  # 6시간 안에는 다시 호출하지 않음
    prompt = company.summary_prompt(h)
    assert "20240301000001" in prompt and "임원ㆍ주요주주" not in prompt  # 기록성 공시는 요약에서 뺌


def test_company_not_found(ctx):
    client, _, _ = ctx
    h = client.get("/api/company", params={"name": "없는회사"}).json()
    assert h["company"] is None and "찾지 못했습니다" in h["notice"]


def test_subscribed_company_collected_regardless_of_industry():
    db = Database(":memory:")
    uid = auth.create_user(db, "kim", "김", "password-12345")
    db.set("bootstrapped", "1")
    db.execute("INSERT INTO subscriptions(user_id, kind, value, levels) VALUES(?, 'company', '삼성 전자', 'all')", (uid,))

    def handler(req):
        if req.url.path.endswith("company.json"):
            return httpx.Response(200, json={"status": "000", "induty_code": "264"})  # 보건의료 아님
        return httpx.Response(200, json={"status": "000", "total_page": 1,
                                         "list": [item("1", "삼성전자", "기업설명회(IR)개최"), item("2", "어떤전자", "기업설명회(IR)개최")]})

    col = Collector(DartClient("k", db, 1000, http=httpx.AsyncClient(transport=httpx.MockTransport(handler))), db, RULES)
    r = asyncio.run(col.poll())
    assert [x["rcept_no"] for x in r.new] == ["1"]


class Rec:
    def __init__(self):
        self.sent = []

    def send_to_user(self, uid, payload, force=False):
        self.sent.append((uid, payload["tag"], payload["title"]))
        return 1


def test_all_level_subscription_gets_general_disclosures():
    db = Database(":memory:")
    a = auth.create_user(db, "a", "A", "password-12345")
    b = auth.create_user(db, "b", "B", "password-12345")
    db.execute("INSERT INTO subscriptions(user_id, kind, value, levels) VALUES(?, 'company', '유한양행', 'all')", (a,))
    db.execute("INSERT INTO subscriptions(user_id, kind, value, levels) VALUES(?, 'company', '유한양행', 'red')", (b,))
    for no, level, corr in (("1", "yellow", 0), ("2", "red", 0), ("3", "yellow", 1)):
        db.execute("""INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, is_correction, watched,
                      first_seen_at) VALUES(?, 'X', '유한양행', '제목', '20261124', ?, ?, 0, ?)""", (no, level, corr, now_iso()))
    rec = Rec()
    asyncio.run(Alerter(db, Rules.load(BASE_DIR / "config/rules.toml"), rec, "http://x", notify=True).flush())
    assert sorted((u, t) for u, t, _ in rec.sent) == [(a, "1"), (a, "2"), (b, "2")]
    assert any(title.endswith("· 공시") for u, t, title in rec.sent if t == "1")


def test_subscription_levels_api(ctx):
    client, db, _ = ctx
    assert client.post("/api/subscriptions", json={"kind": "company", "value": "유한양행", "levels": "all"}).status_code == 200
    assert client.post("/api/subscriptions", json={"kind": "company", "value": "유한양행", "levels": "red"}).status_code == 200
    subs = client.get("/api/me").json()["subscriptions"]
    assert {"kind": "company", "value": "유한양행", "levels": "red"} in subs
    assert client.get("/api/company", params={"name": "유한양행"}).json()["company"]["subscription"] == "red"
