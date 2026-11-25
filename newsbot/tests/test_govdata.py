"""식약처·국회 수집: 첫 수집은 조용히, 이후 새 항목은 알림 대상. 피드 하나가 실패해도 나머지는 돈다."""

import asyncio
import json
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from newsbot import auth
from newsbot.app import create_app
from newsbot.config import BASE_DIR, Settings
from newsbot.db import Database, now
from newsbot.govdata import GovClient, GovCollector, company_key
from newsbot.rules import Rules

TODAY = now().strftime("%Y%m%d")
OLD = (now() - timedelta(days=60)).strftime("%Y%m%d")
WEEK = (now() - timedelta(days=5)).strftime("%Y%m%d")


def dash(ymd):
    return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"


class Fake:
    """공공데이터포털·열린국회정보 흉내. self.data 를 바꾸면 다음 수집에 반영된다."""

    def __init__(self):
        self.fail = set()
        self.data = {
            "getMdcinRtrvlSleStpgelList05": [
                {"item": {"PRDUCT": "가나정", "ENTRPS": "유한양행(주)", "RTRVL_RESN": "용출 부적합", "ENFRC_YN": "N",
                          "RECALL_COMMAND_DATE": WEEK, "ITEM_SEQ": "1", "BIZRNO": "1"}},
                {"item": {"PRDUCT": "오래된약", "ENTRPS": "옛회사", "RTRVL_RESN": "-", "ENFRC_YN": "Y",
                          "RECALL_COMMAND_DATE": OLD, "ITEM_SEQ": "2"}},
            ],
            "getDrugSafeLetterList02": [],
            "getMdcinExaathrList04": [
                {"ADM_DISPS_SEQ": "9", "ENTP_NAME": "화장품회사", "ITEM_NAME": None, "BEF_APPLY_LAW": "화장품법 위반",
                 "EXPOSE_CONT": "원료", "ADM_DISPS_NAME": "판매업무정지", "LAST_SETTLE_DATE": WEEK, "ITEM_SEQ": ""}],
            "getMdcinPrdctnIncmeSuplyList": [],
            "getMdcinClincTestInfoList02": [
                {"APPLY_ENTP_NAME": "에이치케이이노엔주식회사 ", "APPROVAL_TIME": WEEK, "GOODS_NAME": "IN-A", "CLINIC_STEP_NAME": "3상",
                 "CLINIC_EXAM_TITLE": "제3상", "LAB_NAME": "서울대병원", "CLNC_TEST_SN": "t1"},
                {"APPLY_ENTP_NAME": "복제약사", "APPROVAL_TIME": WEEK, "GOODS_NAME": "BE-1", "CLINIC_STEP_NAME": "생동",
                 "CLINIC_EXAM_TITLE": "생물학적 동등성", "LAB_NAME": "병원", "CLNC_TEST_SN": "t2"}],
            "getItemNameList04": [],
            "getCompanyNameList04": [],
            "nzmimeepazxkubdpn": [
                {"BILL_ID": "B1", "BILL_NO": "1", "BILL_NAME": "의료법 일부개정법률안", "COMMITTEE": "보건복지위원회",
                 "PROPOSE_DT": dash(WEEK), "PROPOSER": "홍길동의원 등 10인", "DETAIL_LINK": "https://likms/b1"}],
            "nwbpacrgavhjryiph": [
                {"BILL_ID": "P1", "BILL_NM": "약사법 일부개정법률안(대안)", "COMMITTEE_NM": "보건복지위원회", "PROC_RESULT_CD": "원안가결",
                 "RGS_PROC_DT": dash(WEEK), "VOTE_TCNT": "250", "YES_TCNT": "240", "NO_TCNT": "0", "BLANK_TCNT": "10"},
                {"BILL_ID": "P2", "BILL_NM": "도로법", "COMMITTEE_NM": "국토교통위원회", "PROC_RESULT_CD": "원안가결",
                 "RGS_PROC_DT": dash(WEEK)}],
            "nfcoioopazrwmjrgs": [
                {"TITLE": "필수의료 살리기 토론회", "NAME": "○○의원실", "DESCRIPTION": "", "SDATE": "2027-01-10", "LINK": "https://s/1"},
                {"TITLE": "반도체 산업 세미나", "NAME": "△△의원실", "DESCRIPTION": "", "SDATE": "2027-01-11", "LINK": "https://s/2"}],
        }

    def handler(self, request: httpx.Request) -> httpx.Response:
        name = request.url.path.rstrip("/").split("/")[-1]
        if name in self.fail:
            return httpx.Response(500, text="boom")
        rows = self.data.get(name, [])
        if request.url.host == "open.assembly.go.kr":
            return httpx.Response(200, json={name: [{"head": [{"list_total_count": len(rows)}]}, {"row": rows}]})
        q = request.url.params
        n, page = int(q.get("numOfRows", 100)), int(q.get("pageNo", 1))
        chunk = rows[(page - 1) * n: page * n]
        return httpx.Response(200, json={"header": {"resultCode": "00"},
                                         "body": {"totalCount": len(rows), "items": chunk}})


@pytest.fixture()
def env(tmp_path: Path):
    db = Database(tmp_path / "t.db")
    rules = Rules.load(BASE_DIR / "config/rules.toml")
    fake = Fake()
    client = GovClient("dg", "na", http=httpx.AsyncClient(transport=httpx.MockTransport(fake.handler)), delay=0)
    return GovCollector(client, db, rules), db, fake


def rows(db, source=None):
    q = "SELECT * FROM disclosures" + (" WHERE source=?" if source else "") + " ORDER BY rcept_no"
    return {r["rcept_no"]: r for r in db.query(q, (source,) if source else ())}


def test_company_key_matches_watch_list():
    assert company_key("유한양행(주)") == "유한양행"
    assert company_key("에이치케이이노엔주식회사 ") == "HK이노엔"
    assert company_key("㈜ 한미약품") == "한미약품"


def test_first_poll_is_quiet_and_recent_only(env):
    col, db, _ = env
    new, status = asyncio.run(col.poll())
    assert new == [] and all(v.startswith("정상") for v in status.values())
    r = rows(db)
    # 60일 지난 회수는 들어오지 않음, 처음 들여온 것은 알림 없이(bootstrap)
    assert not any("오래된약" in x["report_nm"] for x in r.values())
    assert all(x["alerted_at"] == "bootstrap" for x in r.values())
    recall = next(x for x in r.values() if x["keyword"] == "의약품 회수")
    assert recall["source"] == "mfds" and recall["watched"] == 1 and recall["level"] == "red"  # 감시 기업 유한양행
    assert recall["first_seen_at"].startswith(dash(WEEK))  # 과거 날짜는 그날 수집된 것처럼
    # 감시 기업 별칭(에이치케이이노엔 → HK이노엔), 생동은 기록(gray), 화장품 처분은 gray
    trials = {x["corp_name"].strip(): x for x in r.values() if x["keyword"] == "임상시험 승인"}
    assert trials["에이치케이이노엔주식회사"]["level"] == "red" and trials["복제약사"]["level"] == "gray"
    assert next(x for x in r.values() if x["keyword"] == "의약품 행정처분")["level"] == "gray"
    # 국회: 보건복지위 소관만, 가결은 red, 보건의료 토론회만
    plen = [x for x in r.values() if x["keyword"] == "본회의 처리"]
    assert len(plen) == 1 and plen[0]["level"] == "red" and "찬성 240" in plen[0]["rm"]
    sem = [x for x in r.values() if x["keyword"] == "토론회"]
    assert [s["report_nm"] for s in sem] == ["[토론회 1/10] 필수의료 살리기 토론회"] and sem[0]["rcept_dt"] == TODAY


def test_later_items_alert_and_failures_are_isolated(env):
    col, db, fake = env
    asyncio.run(col.poll())
    fake.data["getMdcinRtrvlSleStpgelList05"].insert(0, {"item": {
        "PRDUCT": "다라주", "ENTRPS": "작은제약", "RTRVL_RESN": "무균 부적합", "ENFRC_YN": "Y",
        "RECALL_COMMAND_DATE": TODAY, "ITEM_SEQ": "3"}})
    fake.data["nzmimeepazxkubdpn"].insert(0, {"BILL_ID": "B2", "BILL_NAME": "약사법 일부개정법률안", "PROPOSE_DT": dash(TODAY),
                                              "PROPOSER": "김의원의원 등 12인"})
    fake.fail.add("getDrugSafeLetterList02")
    new, status = asyncio.run(col.poll())
    names = sorted(r["report_nm"] for r in new)
    assert names == ["[법안 발의] 약사법 일부개정법률안", "[의약품 회수] 다라주"]
    assert all(r["alerted_at"] is None for r in new)
    recall = next(r for r in new if "다라주" in r["report_nm"])
    assert recall["level"] == "red" and "회수 명령(강제)" in recall["rm"]  # 강제 회수는 감시 기업이 아니어도 중요
    assert status["mfds:letter"].startswith("오류") and status["mfds:recall"].startswith("정상")
    # 같은 항목은 다시 넣지 않음
    again, _ = asyncio.run(col.poll())
    assert again == []


def test_feed_tabs_and_status(tmp_path: Path):
    settings = Settings(db_path=tmp_path / "t.db", data_dir=tmp_path, rules_path=BASE_DIR / "config/rules.toml",
                        data_go_kr_api_key="dg", assembly_api_key="")
    db = Database(settings.db_path)
    auth.create_user(db, "rep", "기자", "reporter-password-1")
    db.execute("""INSERT INTO disclosures(rcept_no, corp_code, corp_name, report_nm, rcept_dt, level, keyword,
                  is_correction, watched, first_seen_at, source, link, rm) VALUES('mfds:recall:x','','작은제약',
                  '[의약품 회수] 다라주',?, 'red','의약품 회수',0,0,?,'mfds','https://nedrug','회수 사유: 무균')""",
               (TODAY, now().isoformat(timespec="seconds")))
    app = create_app(settings, db, start_poller=False)
    with TestClient(app) as c:
        c.post("/api/login", json={"username": "rep", "password": "reporter-password-1"})
        feed = c.get("/api/feed?split=mfds").json()
        items = feed["items"] if isinstance(feed, dict) else feed
        assert [i["report_nm"] for i in items] == ["[의약품 회수] 다라주"] and items[0]["url"] == "https://nedrug"
        assert c.get("/api/feed?split=assembly").json()["items"] == []
        assert c.get("/api/counts").json()["mfds"] == 1
        # DART 키 없이 공공데이터 키만 있어도 수집 상태가 보임
        assert c.get("/api/summary").json()["gov_status"] == "대기 중"


def test_mask_recall_is_not_red(env):
    col, db, fake = env
    asyncio.run(col.poll())
    fake.data["getMdcinRtrvlSleStpgelList05"].insert(0, {"item": {
        "PRDUCT": "방역마스크(KF94)", "ENTRPS": "마스크사", "RTRVL_RESN": "분진포집효율 부적합", "ENFRC_YN": "Y",
        "RECALL_COMMAND_DATE": TODAY, "ITEM_SEQ": "4"}})
    new, _ = asyncio.run(col.poll())
    assert [r["level"] for r in new] == ["yellow"]


def test_old_items_seen_later_stay_quiet(env):
    """수집 시작 뒤에 처음 보이는 옛 항목(14일 넘은 것 등)은 알림 없이 그날짜로 저장한다."""
    col, db, fake = env
    asyncio.run(col.poll())
    late = (now() - timedelta(days=20)).strftime("%Y%m%d")
    fake.data["getMdcinClincTestInfoList02"].append(
        {"APPLY_ENTP_NAME": "유한양행", "APPROVAL_TIME": late, "GOODS_NAME": "YH-1", "CLINIC_STEP_NAME": "2상",
         "CLINIC_EXAM_TITLE": "2상", "LAB_NAME": "병원", "CLNC_TEST_SN": "t-late"})
    new, _ = asyncio.run(col.poll())
    assert new == []
    row = db.one("SELECT * FROM disclosures WHERE rcept_no='mfds:trial:t-late'")
    assert row["alerted_at"] == "bootstrap" and row["first_seen_at"].startswith(dash(late))
