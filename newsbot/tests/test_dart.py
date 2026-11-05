import asyncio

import httpx
import pytest

from newsbot.dart import Collector, DartClient, DartLimitReached
from newsbot.db import Database
from newsbot.rules import Rules

RULES = Rules.from_dict({
    "watch": {"companies": ["유한양행"]},
    "health": {"industry_prefixes": ["21"]},
    "levels": {"red": ["기술이전"], "gray": ["대량보유"]},
})


def item(no, corp, title, code="00000001"):
    return {"rcept_no": no, "corp_code": code, "corp_name": corp, "report_nm": title, "rcept_dt": "20261105",
            "flr_nm": corp, "rm": "", "stock_code": "000100"}


class FakeDart:
    def __init__(self, pages, industries=None, status="000"):
        self.pages = pages          # list of lists
        self.industries = industries or {}
        self.status = status
        self.calls = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request.url.path)
        if self.status != "000":
            return httpx.Response(200, json={"status": self.status, "message": "제한"})
        if request.url.path.endswith("company.json"):
            code = request.url.params["corp_code"]
            return httpx.Response(200, json={"status": "000", "induty_code": self.industries.get(code, "64121")})
        page = int(request.url.params["page_no"])
        lst = self.pages[page - 1] if page <= len(self.pages) else []
        return httpx.Response(200, json={"status": "000", "page_no": page, "total_page": len(self.pages), "list": lst})


def make(fake, db=None, rescan=2):
    db = db or Database(":memory:")
    http = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    client = DartClient("key", db, daily_limit=1000, http=http)
    return Collector(client, db, RULES, rescan_pages=rescan), db


def test_bootstrap_then_new_items():
    fake = FakeDart([[item("1", "유한양행", "기술이전계약체결")]])
    col, db = make(fake)
    r1 = asyncio.run(col.poll())
    assert r1.bootstrap and len(r1.new) == 1          # 첫 실행: 저장은 하되
    fake.pages = [[item("2", "유한양행", "분기보고서"), item("1", "유한양행", "기술이전계약체결")]]
    r2 = asyncio.run(col.poll())
    assert not r2.bootstrap and [r["rcept_no"] for r in r2.new] == ["2"]


def test_late_arrival_on_second_page_is_caught():
    """DART 반영 지연으로 오래된 접수번호가 나중에 2페이지에 나타나도 놓치지 않는다."""
    fake = FakeDart([[item("10", "유한양행", "a")], [item("9", "유한양행", "b")]])
    col, db = make(fake)
    asyncio.run(col.poll())
    fake.pages = [[item("11", "유한양행", "c"), item("10", "유한양행", "a")],
                  [item("8", "유한양행", "늦게 반영된 기술이전"), item("9", "유한양행", "b")]]
    r = asyncio.run(col.poll())
    assert sorted(x["rcept_no"] for x in r.new) == ["11", "8"]
    late = db.one("SELECT level FROM disclosures WHERE rcept_no='8'")
    assert late["level"] == "red"


def test_industry_filter_and_cache():
    fake = FakeDart([[item("1", "어떤제약", "분기보고서", code="A"), item("2", "어떤은행", "분기보고서", code="B")]],
                    industries={"A": "21102", "B": "64121"})
    col, db = make(fake)
    r = asyncio.run(col.poll())
    assert [x["corp_name"] for x in r.new] == ["어떤제약"]
    company_calls = sum(1 for c in fake.calls if c.endswith("company.json"))
    asyncio.run(col.poll())
    assert sum(1 for c in fake.calls if c.endswith("company.json")) == company_calls  # 캐시


def test_limit_status_raises():
    fake = FakeDart([[]], status="020")
    col, _ = make(fake)
    with pytest.raises(DartLimitReached):
        asyncio.run(col.poll())


def test_local_daily_limit():
    fake = FakeDart([[item("1", "유한양행", "a")]])
    db = Database(":memory:")
    http = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
    col = Collector(DartClient("key", db, daily_limit=0, http=http), db, RULES)
    with pytest.raises(DartLimitReached):
        asyncio.run(col.poll())
    assert fake.calls == []
