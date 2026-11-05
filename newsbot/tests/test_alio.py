import asyncio
import json

import httpx

from newsbot.alio import AlioClient, AlioCollector, AlioConfig, AlioItem, compare, extract_finance, parse_tables, finance_overview
from newsbot.db import Database

FIN_HTML = """<table><tr><th>구분</th><th>2025년</th><th>2024년</th></tr>
<tr><td>(단위: 백만원)</td><td></td><td></td></tr>
<tr><td>매출액(의료수익)</td><td>1,234,500</td><td>1,100,000</td></tr>
<tr><td>영업이익</td><td>(12,000)</td><td>△3,000</td></tr>
<tr><td>당기순이익</td><td>5,000</td><td>10,000</td></tr></table>"""


def test_extract_and_compare():
    fin = extract_finance(parse_tables(FIN_HTML), ["매출액", "영업이익", "당기순이익"])
    items = {i["label"]: i for i in compare(fin)}
    assert items["매출액"]["value"] == 1234500 and items["매출액"]["prev"] == 1100000
    assert items["매출액"]["pct"] == 12.2
    assert items["영업이익"]["value"] == -12000 and items["영업이익"]["prev"] == -3000
    assert items["당기순이익"]["pct"] == -50.0


def test_ascending_years_sorted_latest_first():
    html = FIN_HTML.replace("2025년", "X").replace("2024년", "2025년").replace("X", "2024년")
    fin = extract_finance(parse_tables(html), ["매출액"])
    assert fin["rows"][0]["values"][0]["year"] == "2025"


class FakeAlio:
    def __init__(self):
        self.calls = []
        self.susi_rows = {("R1", "A1"): [{"title": "2025년 결산", "idate": "2026-03-30", "disclosureNo": "D1"}],
                          ("R2", "A1"): [{"title": "이사회 회의록(3차)", "idate": "2026-10-01", "idx": 77}]}

    def handler(self, req: httpx.Request):
        self.calls.append(req.url.path)
        p = req.url.path
        if p.endswith("findOrganApbaList.json"):
            return httpx.Response(200, json={"data": {"organList": {"page": {"totalPage": 1}, "result": [
                {"apbaId": "A1", "apbaNa": "서울대학교병원", "typeNa": "기타공공기관", "jidtNa": "교육부"},
                {"apbaId": "B9", "apbaNa": "어떤공사"}]}}})
        if p.endswith("formList.json"):
            return httpx.Response(200, json={"status": "success", "data": [
                {"mcdnm": "요약 손익계산서", "reportNos": "R1"}, {"mcdnm": "이사회 회의록", "reportNos": "R2"},
                {"mcdnm": "기타", "reportNos": "R3"}]})
        if p.endswith("itemReportListSusi.json"):
            body = json.loads(req.content)
            return httpx.Response(200, json={"data": {"result": self.susi_rows.get((body["reportFormRootNo"], body["apbaId"]), [])}})
        if p.endswith("itemReportRight.do"):
            return httpx.Response(200, text=FIN_HTML)
        return httpx.Response(404)


def make():
    fake = FakeAlio()
    db = Database(":memory:")
    client = AlioClient(http=httpx.AsyncClient(transport=httpx.MockTransport(fake.handler)), delay=0)
    cfg = AlioConfig(organizations=["서울대학교 병원", "없는병원"],
                     items=[AlioItem("손익계산서", "red", True), AlioItem("이사회 회의록", "yellow")],
                     finance_rows=["매출액", "당기순이익"])
    return AlioCollector(client, db, cfg), db, fake


def test_poll_bootstrap_then_new():
    col, db, fake = make()
    assert asyncio.run(col.poll()) == []                       # 첫 실행: 저장만
    assert json.loads(db.get("alio_missing")) == ["없는병원"]
    assert db.one("SELECT COUNT(*) n FROM disclosures WHERE source='alio'")["n"] == 2
    fin = finance_overview(db)
    assert fin[0]["org"] == "서울대학교병원" and fin[0]["items"][0]["label"] == "매출액"
    fake.susi_rows[("R2", "A1")].append({"title": "이사회 회의록(4차)", "idate": "2026-11-01", "idx": 78})
    new = asyncio.run(col.poll())
    assert [r["report_nm"] for r in new] == ["[이사회 회의록] 이사회 회의록(4차)"]
    assert new[0]["level"] == "yellow" and new[0]["source"] == "alio"
