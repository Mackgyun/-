"""알리오 수집기: 공공기관·국립대병원의 수시공시 감시와 결산(손익계산서) 비교.

알리오는 경영공시용 공식 API가 없어서, 사이트 화면이 쓰는 조회 주소를 그대로 쓴다
(공개 오픈소스 alio-mcp가 쓰는 것과 같은 주소). 사이트 개편 시 고쳐야 할 수 있다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .db import Database, now, now_iso

log = logging.getLogger(__name__)
BASE = "https://www.alio.go.kr"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChungnyunBriefing/0.2",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json;charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE}/item/itemList.do",
}
REFRESH_DAYS = 7


def _norm(s: str) -> str:
    return "".join((s or "").split())


@dataclass
class AlioItem:
    match: str
    level: str = "yellow"
    finance: bool = False


@dataclass
class AlioConfig:
    organizations: list[str] = field(default_factory=list)
    items: list[AlioItem] = field(default_factory=list)
    finance_rows: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "AlioConfig":
        with open(path, "rb") as f:
            d = tomllib.load(f)
        return cls(
            organizations=d.get("organizations", []),
            items=[AlioItem(i["match"], i.get("level", "yellow"), bool(i.get("finance"))) for i in d.get("items", [])],
            finance_rows=d.get("finance", {}).get("rows", []),
        )


class AlioClient:
    def __init__(self, verify: bool = True, http: httpx.AsyncClient | None = None, delay: float = 1.0):
        self.http = http or httpx.AsyncClient(headers=HEADERS, verify=verify, timeout=30, follow_redirects=True)
        self.delay = delay

    async def _post(self, path: str, body: dict) -> dict:
        await asyncio.sleep(self.delay)
        r = await self.http.post(f"{BASE}{path}", json=body)
        r.raise_for_status()
        return r.json()

    async def organs_page(self, page: int) -> tuple[list[dict], int]:
        d = await self._post("/organ/findOrganApbaList.json",
                             {"apbaType": [], "jidtDptm": [], "area": [], "apba_id": "", "pageNo": page})
        node = (d.get("data") or {}).get("organList") or {}
        result = node.get("result", []) if isinstance(node, dict) else node
        total = (node.get("page") or {}).get("totalPage", 1) if isinstance(node, dict) else 1
        return result or [], int(total or 1)

    async def form_list(self) -> list[dict]:
        d = await self._post("/item/formList.json", {})
        return d.get("data") or []

    async def susi(self, root_no: str, apba_id: str, page: int = 1) -> list[dict]:
        d = await self._post("/item/itemReportListSusi.json", {
            "pageNo": page, "apbaId": apba_id, "apbaType": "", "reportFormRootNo": root_no,
            "search_word": "", "search_flag": "title", "bid_type": "", "enfc_istt": ""})
        return (d.get("data") or {}).get("result") or []

    async def report_html(self, disclosure_no: str) -> str:
        await asyncio.sleep(self.delay)
        r = await self.http.get(f"{BASE}/item/itemReportRight.do", params={"disclosureNo": disclosure_no},
                                headers={"Accept": "text/html"})
        r.raise_for_status()
        return r.text


# --- 결산표 해석 ------------------------------------------------------------
_NUM = re.compile(r"^[\(△▲\-−]?\s*[\d,]+(\.\d+)?\)?$")
_YEAR = re.compile(r"(20\d{2})")


def parse_tables(html: str) -> list[list[list[str]]]:
    soup = BeautifulSoup(html, "html.parser")
    tables = []
    for t in soup.find_all("table"):
        rows = []
        for tr in t.find_all("tr"):
            cells = [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["th", "td"])]
            if any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def to_number(cell: str) -> float | None:
    s = cell.replace(" ", "")
    if not s or not _NUM.match(s):
        return None
    neg = s.startswith(("(", "△", "-", "−")) or s.endswith(")")
    s = re.sub(r"[^\d.]", "", s)
    if not s:
        return None
    v = float(s)
    return -v if neg else v


def extract_finance(tables: list[list[list[str]]], row_names: list[str]) -> dict | None:
    """손익계산서 표에서 지정한 줄의 연도별 값을 뽑는다. 최신 연도가 앞으로 오게 정렬."""
    wanted = [_norm(r) for r in row_names]
    best, best_hits = None, 0
    for t in tables:
        hits = sum(1 for row in t if row and any(w in _norm(row[0]) for w in wanted))
        if hits > best_hits:
            best, best_hits = t, hits
    if not best:
        return None
    header = next((r for r in best if sum(1 for c in r if _YEAR.search(c)) >= 2), None)
    years = [(_YEAR.search(c).group(1) if _YEAR.search(c) else None) for c in header] if header else []
    rows = []
    for name, w in zip(row_names, wanted):
        row = next((r for r in best if r and w in _norm(r[0])), None)
        if not row:
            continue
        values = []
        for idx, cell in enumerate(row[1:], start=1):
            v = to_number(cell)
            if v is None:
                continue
            year = years[idx] if idx < len(years) else None
            values.append({"year": year, "value": v})
        if values:
            rows.append({"label": name, "values": values})
    if not rows:
        return None
    if all(v["year"] for r in rows for v in r["values"]):
        for r in rows:
            r["values"].sort(key=lambda v: v["year"], reverse=True)
    unit = next((c for r in best[:3] for c in r if "단위" in c), "")
    return {"rows": rows, "unit": unit}


def compare(finance: dict) -> list[dict]:
    out = []
    for r in finance.get("rows", []):
        vals = r["values"]
        if not vals:
            continue
        cur = vals[0]
        prev = vals[1] if len(vals) > 1 else None
        item = {"label": r["label"], "year": cur.get("year"), "value": cur["value"],
                "prev_year": prev.get("year") if prev else None, "prev": prev["value"] if prev else None}
        if prev and prev["value"]:
            item["change"] = cur["value"] - prev["value"]
            item["pct"] = round((cur["value"] - prev["value"]) / abs(prev["value"]) * 100, 1)
        out.append(item)
    return out


# --- 수집기 -----------------------------------------------------------------
class AlioCollector:
    def __init__(self, client: AlioClient, db: Database, config: AlioConfig):
        self.client = client
        self.db = db
        self.config = config

    def _stale(self, key: str) -> bool:
        at = self.db.get(key)
        return not at or now() - datetime.fromisoformat(at) > timedelta(days=REFRESH_DAYS)

    async def resolve_orgs(self) -> list[dict]:
        if self._stale("alio_orgs_at") or not self.db.one("SELECT 1 FROM alio_orgs"):
            want = {_norm(n): n for n in self.config.organizations}
            found: dict[str, dict] = {}
            first, total = await self.client.organs_page(1)
            pages = [first]
            for p in range(2, min(total, 60) + 1):
                pages.append((await self.client.organs_page(p))[0])
            for result in pages:
                for o in result:
                    key = _norm(o.get("apbaNa", ""))
                    if key in want and o.get("apbaId"):
                        found[key] = o
            with self.db.tx() as c:
                c.execute("DELETE FROM alio_orgs")
                for o in found.values():
                    c.execute("INSERT INTO alio_orgs(apba_id, name, inst_type, dept, resolved_at) VALUES(?,?,?,?,?)",
                              (o["apbaId"], o.get("apbaNa", ""), o.get("typeNa"), o.get("jidtNa"), now_iso()))
            missing = [n for k, n in want.items() if k not in found]
            self.db.set("alio_missing", json.dumps(missing, ensure_ascii=False))
            self.db.set("alio_orgs_at", now_iso())
        return self.db.query("SELECT * FROM alio_orgs ORDER BY name")

    async def resolve_items(self) -> list[dict]:
        cached = self.db.get("alio_items")
        if cached and not self._stale("alio_items_at"):
            return json.loads(cached)
        forms = await self.client.form_list()
        resolved = []
        for cfg in self.config.items:
            key = _norm(cfg.match)
            for f in forms:
                name = (f.get("scdnm") or f.get("mcdnm") or "").strip()
                root = (f.get("reportNos") or f.get("mcd") or "").split(",")[0].strip()
                if root and key in _norm(name):
                    resolved.append({"root": root, "name": name, "level": cfg.level, "finance": cfg.finance})
        # 같은 root가 여러 번 잡히면 하나만
        uniq = {r["root"]: r for r in resolved}
        items = list(uniq.values())
        self.db.set("alio_items", json.dumps(items, ensure_ascii=False))
        self.db.set("alio_items_at", now_iso())
        return items

    async def poll(self) -> list[dict]:
        orgs = await self.resolve_orgs()
        items = await self.resolve_items()
        bootstrap = self.db.get("alio_bootstrapped") != "1"
        new_rows: list[dict] = []
        for org in orgs:
            for item in items:
                try:
                    results = await self.client.susi(item["root"], org["apba_id"])
                except (httpx.HTTPError, ValueError) as e:
                    self.db.log("error", f"alio {org['name']} {item['name']}: {e!r}")
                    continue
                for v in results:
                    row = await self._ingest(org, item, v)
                    if row:
                        new_rows.append(row)
        if bootstrap:
            self.db.set("alio_bootstrapped", "1")
        self.db.set("alio_last_poll_at", now_iso())
        return [] if bootstrap else new_rows

    async def _ingest(self, org: dict, item: dict, v: dict) -> dict | None:
        ref = (v.get("disclosureNo") or str(v.get("idx") or "")).strip()
        if not ref:
            return None
        key = f"alio:{item['root']}:{ref}"
        if self.db.one("SELECT 1 FROM disclosures WHERE rcept_no=?", (key,)):
            return None
        idate = re.sub(r"\D", "", str(v.get("idate") or ""))[:8]
        disclosure_no = (v.get("disclosureNo") or "").strip()
        link = (f"{BASE}/item/itemReportRight.do?disclosureNo={disclosure_no}" if disclosure_no
                else f"{BASE}/item/itemList.do")
        row = {
            "rcept_no": key, "corp_code": org["apba_id"], "corp_name": org["name"], "stock_code": None,
            "report_nm": f"[{item['name']}] {(v.get('title') or '').strip()}".strip(),
            "rcept_dt": idate or now().strftime("%Y%m%d"), "flr_nm": org["name"], "rm": None,
            "level": item["level"], "keyword": item["name"], "is_correction": 0, "watched": 1,
            "first_seen_at": now_iso(), "source": "alio", "link": link,
        }
        self.db.execute(
            """INSERT OR IGNORE INTO disclosures(rcept_no, corp_code, corp_name, stock_code, report_nm, rcept_dt,
               flr_nm, rm, level, keyword, is_correction, watched, first_seen_at, source, link)
               VALUES(:rcept_no,:corp_code,:corp_name,:stock_code,:report_nm,:rcept_dt,:flr_nm,:rm,:level,:keyword,
                      :is_correction,:watched,:first_seen_at,:source,:link)""", row)
        if item.get("finance") and disclosure_no:
            await self._finance(org, item, v, disclosure_no)
        return row

    async def _finance(self, org: dict, item: dict, v: dict, disclosure_no: str) -> None:
        try:
            html = await self.client.report_html(disclosure_no)
        except httpx.HTTPError as e:
            self.db.log("error", f"alio finance {org['name']}: {e!r}")
            return
        fin = extract_finance(parse_tables(html), self.config.finance_rows)
        if not fin:
            self.db.log("error", f"alio finance parse failed: {org['name']} {disclosure_no}")
            return
        self.db.execute(
            """INSERT OR REPLACE INTO alio_finance(disclosure_no, apba_id, org_name, item_name, title, idate,
               table_json, fetched_at) VALUES(?,?,?,?,?,?,?,?)""",
            (disclosure_no, org["apba_id"], org["name"], item["name"], v.get("title"),
             str(v.get("idate") or ""), json.dumps(fin, ensure_ascii=False), now_iso()))


def finance_overview(db: Database) -> list[dict]:
    """기관별 가장 최근 결산 비교."""
    rows = db.query("""SELECT f.* FROM alio_finance f
                       WHERE f.fetched_at = (SELECT MAX(fetched_at) FROM alio_finance g WHERE g.apba_id=f.apba_id)
                       ORDER BY f.org_name""")
    out = []
    for r in rows:
        fin = json.loads(r["table_json"])
        out.append({"org": r["org_name"], "apba_id": r["apba_id"], "title": r["title"], "idate": r["idate"],
                    "unit": fin.get("unit", ""), "items": compare(fin),
                    "url": f"{BASE}/item/itemReportRight.do?disclosureNo={r['disclosure_no']}"})
    return out
