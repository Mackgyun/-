"""OpenDART 수집기.

OpenDART 공시검색 API는 공시 제출 후 약 15분 뒤에 반영되고, 반영 순서가 접수 순서와
다를 수 있다. 그래서 '이미 본 공시가 나오면 중단'하지 않고, 매번 최근 몇 페이지를 다시
훑고 한 시간에 한 번은 이틀치 전체를 대조한다. 중복은 rcept_no 기본키로 막는다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

import httpx

from .db import Database, now, now_iso
from .rules import Rules

log = logging.getLogger(__name__)

BASE = "https://opendart.fss.or.kr/api"
VIEW_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
PAGE_COUNT = 100
FULL_SCAN_MAX_PAGES = 50


class DartError(Exception):
    def __init__(self, status: str, message: str):
        super().__init__(f"DART {status}: {message}")
        self.status = status


class DartLimitReached(DartError):
    pass


class DartClient:
    def __init__(self, api_key: str, db: Database, daily_limit: int, http: httpx.AsyncClient | None = None):
        self.api_key = api_key
        self.db = db
        self.daily_limit = daily_limit
        self.http = http or httpx.AsyncClient(timeout=20)

    def _count_key(self) -> str:
        return "dart_calls:" + now().strftime("%Y%m%d")

    def calls_today(self) -> int:
        return int(self.db.get(self._count_key(), "0") or 0)

    async def _get(self, path: str, params: dict) -> dict:
        if self.calls_today() >= self.daily_limit:
            raise DartLimitReached("LOCAL", f"오늘 호출 {self.daily_limit}건 한도 도달")
        self.db.set(self._count_key(), str(self.calls_today() + 1))
        resp = await self.http.get(f"{BASE}/{path}", params={"crtfc_key": self.api_key, **params})
        resp.raise_for_status()
        data = resp.json()
        status = str(data.get("status", ""))
        if status == "020":
            raise DartLimitReached(status, data.get("message", "요청 제한 초과"))
        if status not in ("000", "013"):
            raise DartError(status, data.get("message", ""))
        return data

    async def list_page(self, bgn_de: str, end_de: str, page_no: int) -> dict:
        return await self._get(
            "list.json",
            {"bgn_de": bgn_de, "end_de": end_de, "page_no": page_no, "page_count": PAGE_COUNT},
        )

    async def company(self, corp_code: str) -> dict:
        return await self._get("company.json", {"corp_code": corp_code})


@dataclass
class PollResult:
    new: list[dict]
    pages: int
    scanned: int
    bootstrap: bool


class Collector:
    def __init__(self, client: DartClient, db: Database, rules: Rules, rescan_pages: int = 3):
        self.client = client
        self.db = db
        self.rules = rules
        self.rescan_pages = rescan_pages

    async def _industry(self, corp_code: str, corp_name: str) -> str | None:
        row = self.db.one("SELECT induty_code FROM companies WHERE corp_code=?", (corp_code,))
        if row is not None:
            return row["induty_code"]
        data = await self.client.company(corp_code)
        code = data.get("induty_code") if data.get("status") == "000" else None
        self.db.execute(
            "INSERT OR REPLACE INTO companies(corp_code, corp_name, induty_code, fetched_at) VALUES(?,?,?,?)",
            (corp_code, corp_name, code, now_iso()),
        )
        return code

    async def poll(self, full: bool = False) -> PollResult:
        today = now()
        bgn = (today - timedelta(days=1)).strftime("%Y%m%d")
        end = today.strftime("%Y%m%d")
        bootstrap = self.db.get("bootstrapped") != "1"

        new: list[dict] = []
        pages = scanned = 0
        max_pages = FULL_SCAN_MAX_PAGES if (full or bootstrap) else self.rescan_pages
        page_no = 1
        while page_no <= max_pages:
            data = await self.client.list_page(bgn, end, page_no)
            pages += 1
            items = data.get("list") or []
            for item in items:
                scanned += 1
                row = await self._ingest(item)
                if row:
                    new.append(row)
            total_page = int(data.get("total_page") or 0)
            if page_no >= total_page or not items:
                break
            page_no += 1

        if bootstrap:
            self.db.set("bootstrapped", "1")
        self.db.set("last_poll_at", now_iso())
        return PollResult(new=new, pages=pages, scanned=scanned, bootstrap=bootstrap)

    async def _ingest(self, item: dict) -> dict | None:
        rcept_no = item.get("rcept_no")
        if not rcept_no:
            return None
        if self.db.one("SELECT 1 FROM disclosures WHERE rcept_no=?", (rcept_no,)):
            return None
        corp_name = item.get("corp_name", "")
        corp_code = item.get("corp_code", "")
        watched = self.rules.is_watched(corp_name)
        induty = None
        if not watched and self.rules.needs_industry_lookup(corp_name):
            induty = await self._industry(corp_code, corp_name)
        if not self.rules.is_relevant(corp_name, induty):
            return None

        c = self.rules.classify(item.get("report_nm", ""))
        row = {
            "rcept_no": rcept_no,
            "corp_code": corp_code,
            "corp_name": corp_name,
            "stock_code": item.get("stock_code") or None,
            "report_nm": item.get("report_nm", "").strip(),
            "rcept_dt": item.get("rcept_dt", ""),
            "flr_nm": item.get("flr_nm"),
            "rm": item.get("rm"),
            "level": c.level,
            "keyword": c.keyword,
            "is_correction": int(c.is_correction),
            "watched": int(watched),
            "first_seen_at": now_iso(),
        }
        inserted = self.db.execute(
            """INSERT OR IGNORE INTO disclosures
               (rcept_no, corp_code, corp_name, stock_code, report_nm, rcept_dt, flr_nm, rm,
                level, keyword, is_correction, watched, first_seen_at)
               VALUES (:rcept_no, :corp_code, :corp_name, :stock_code, :report_nm, :rcept_dt, :flr_nm, :rm,
                       :level, :keyword, :is_correction, :watched, :first_seen_at)""",
            row,
        )
        return row if inserted else None
