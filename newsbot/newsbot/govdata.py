"""식약처(공공데이터포털)와 국회(열린국회정보) 수집.

수집한 항목은 DART·알리오와 같은 disclosures 표에 넣는다(source='mfds' / 'assembly').
그래서 분류 등급, 알림, 목록, 검색, AI 도구가 그대로 적용된다.

- 피드마다 처음 수집할 때는 최근 BOOTSTRAP_DAYS 일 것만 알림 없이 저장한다(과거 자료가 알림으로 쏟아지지 않게).
- 그 뒤로는 새로 보이는 항목을 저장하고, 등급이 red 면 알림을 보낸다.
- 오래된 순으로 주는 API(행정처분·공급중단·임상 등)는 마지막 페이지를 읽는다.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

import httpx

from .db import Database, now, now_iso
from .rules import GRAY, RED, YELLOW, Rules

log = logging.getLogger(__name__)

DG_BASE = "https://apis.data.go.kr/1471000"
NA_BASE = "https://open.assembly.go.kr/portal/openapi"
NEDRUG_ITEM = "https://nedrug.mfds.go.kr/pbp/CCBBB01/getItemDetail?itemSeq={}"
NEDRUG_HOME = "https://nedrug.mfds.go.kr/index"
BOOTSTRAP_DAYS = 14
KEEP_DAYS = 45  # 이보다 오래된 날짜의 항목은 새로 보여도 넣지 않는다

# 토론회·세미나 중 보건의료 관련만 고르는 낱말 (제목·주최·설명)
HEALTH_WORDS = (
    "의료", "의사", "의대", "의학", "병원", "간호", "보건", "건강", "환자", "질병", "감염", "백신", "제약", "바이오",
    "약사", "의약", "약가", "신약", "복지부", "정신건강", "돌봄", "요양", "치매", "응급", "필수의료", "공공의료",
    "건보", "건강보험", "암 ", "희귀질환", "헬스케어", "디지털헬스", "의료기기", "한의", "치과", "마약",
)

# 식약처 표기 ↔ DART 표기 (감시 기업 판단용)
ALIASES = {
    "제이더블유중외제약": "JW중외제약", "제이더블유홀딩스": "JW홀딩스", "에이치케이이노엔": "HK이노엔",
    "지씨녹십자": "녹십자", "GC녹십자": "녹십자", "에스케이바이오팜": "SK바이오팜", "에스케이바이오사이언스": "SK바이오사이언스",
}
_LEGAL = re.compile(r"\(주\)|㈜|주식회사|\(유\)|유한회사|\(재\)|재단법인|\(사\)|사단법인|\s+")


def company_key(name: str) -> str:
    key = _LEGAL.sub("", name or "")
    return ALIASES.get(key, key)


def _ymd(value: Any) -> str:
    """'2026-11-23', '20261123111140', '2026.11.23.' → '20261123' (없으면 '')."""
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[:8] if len(digits) >= 8 else ""


def _clip(text: Any, n: int) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _h(*parts: Any) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


class GovClient:
    def __init__(self, dg_key: str, na_key: str, http: httpx.AsyncClient | None = None, delay: float = 0.3):
        self.dg_key, self.na_key = dg_key, na_key
        self.http = http or httpx.AsyncClient(timeout=30, headers={"User-Agent": "chungnyun-newsbot"})
        self.delay = delay

    async def data_go(self, path: str, page: int = 1, rows: int = 100, **params) -> tuple[int, list[dict]]:
        r = await self.http.get(f"{DG_BASE}/{path}", params={"serviceKey": self.dg_key, "type": "json",
                                                             "numOfRows": rows, "pageNo": page, **params})
        r.raise_for_status()
        await asyncio.sleep(self.delay)
        try:
            d = r.json()
        except ValueError:
            raise RuntimeError(f"공공데이터포털 응답 오류: {_clip(r.text, 160)}") from None
        header = d.get("header") or d.get("response", {}).get("header") or {}
        if header.get("resultCode") not in (None, "00"):
            raise RuntimeError(f"공공데이터포털 {header.get('resultCode')}: {header.get('resultMsg')}")
        body = d.get("body") or d.get("response", {}).get("body") or {}
        items = body.get("items") or []
        if isinstance(items, dict):
            items = items.get("item") or []
        if isinstance(items, dict):
            items = [items]
        # 일부 API는 [{"item": {...}}] 모양으로 준다
        items = [i.get("item", i) if isinstance(i, dict) and set(i) == {"item"} else i for i in items]
        return int(body.get("totalCount") or 0), items

    async def data_go_latest(self, path: str, rows: int = 100, pages: int = 2, **params) -> list[dict]:
        """오래된 순으로 주는 API에서 가장 최근 rows*pages 건."""
        total, _ = await self.data_go(path, 1, 1, **params)
        last = max(1, math.ceil(total / rows))
        out: list[dict] = []
        for p in range(max(1, last - pages + 1), last + 1):
            out += (await self.data_go(path, p, rows, **params))[1]
        return out

    async def assembly(self, code: str, page: int = 1, size: int = 100, **params) -> list[dict]:
        r = await self.http.get(f"{NA_BASE}/{code}", params={"KEY": self.na_key, "Type": "json",
                                                             "pIndex": page, "pSize": size, **params})
        r.raise_for_status()
        await asyncio.sleep(self.delay)
        d = r.json()
        v = d.get(code)
        if not v:
            res = d.get("RESULT") or {}
            if res.get("CODE") == "INFO-200":  # 자료 없음
                return []
            raise RuntimeError(f"열린국회정보 {res.get('CODE')}: {res.get('MESSAGE')}")
        return v[1].get("row", []) if len(v) > 1 else []


@dataclass
class Feed:
    key: str
    source: str            # mfds | assembly
    label: str             # 목록·분류 근거에 표시 (keyword)
    fetch: Callable[[GovClient], Any]
    convert: Callable[[dict, Rules], dict | None]
    needs: str = "dg"      # dg | na


def _row(feed: str, ref: str, corp: str, title: str, date: str, level: str, rm: str, link: str,
         watched: bool, corp_code: str = "") -> dict:
    return {"ref": f"{feed}:{ref}", "corp_code": corp_code or "", "corp_name": _clip(corp, 60) or "-",
            "report_nm": _clip(title, 200), "rcept_dt": date or now().strftime("%Y%m%d"), "level": level,
            "rm": rm.strip()[:2000] or None, "link": link, "watched": int(watched)}


# --- 식약처 -------------------------------------------------------------------------------
async def _recall(c: GovClient):
    return (await c.data_go("MdcinRtrvlSleStpgeInfoService05/getMdcinRtrvlSleStpgelList05", 1, 100))[1]


def _recall_row(v: dict, rules: Rules) -> dict | None:
    corp, seq, date = v.get("ENTRPS") or "", v.get("ITEM_SEQ") or "", _ymd(v.get("RECALL_COMMAND_DATE"))
    forced = (v.get("ENFRC_YN") or "").upper() == "Y"
    watched = rules.is_watched(company_key(corp))
    # 보건용 마스크(의약외품) 성능 부적합 회수는 잦고 기사 가치가 낮아 감시 기업이 아니면 일반으로
    mask = "마스크" in (v.get("PRDUCT") or "")
    return _row("mfds:recall", f"{seq}:{date}:{_h(v.get('PRDUCT'))}", corp, f"[의약품 회수] {v.get('PRDUCT') or ''}",
                date, RED if watched or (forced and not mask) else YELLOW,
                f"회수 사유: {v.get('RTRVL_RESN') or '-'} · {'회수 명령(강제)' if forced else '자진 회수'}",
                NEDRUG_ITEM.format(seq) if seq else NEDRUG_HOME, watched, v.get("BIZRNO") or "")


async def _letter(c: GovClient):
    return (await c.data_go("DrugSafeLetterService02/getDrugSafeLetterList02", 1, 50))[1]


def _letter_row(v: dict, rules: Rules) -> dict | None:
    body = v.get("PBANC_CONT") or ""
    # 제목이 '안전성 서한 배포 알림'처럼 같은 경우가 많아 본문의 약 이름을 앞에 붙인다
    m = re.search(r"[\"“'‘]([^\"”'’]{2,40})[\"”'’]", body) or re.search(r"\(([^()]{2,40})\)에 대한 안전성", body)
    title = v.get("TITLE") or "안전성 서한"
    if m and m.group(1) not in title:
        title = f"{title} ({m.group(1)})"
    return _row("mfds:letter", v.get("SAFT_LETT_NO") or _h(title), "식약처", f"[{v.get('PBANC_DIVS_NM') or '안전성서한'}] {title}",
                _ymd(v.get("PBANC_YMD")), RED, _clip(body, 800), v.get("ATTACH_FILE_URL") or NEDRUG_HOME, False)


async def _admin(c: GovClient):
    return await c.data_go_latest("MdcinExaathrService04/getMdcinExaathrList04", 100, 2)


def _admin_row(v: dict, rules: Rules) -> dict | None:
    corp, law = v.get("ENTP_NAME") or "", (v.get("BEF_APPLY_LAW") or "") + (v.get("EXPOSE_CONT") or "")
    cosmetic = "화장품법" in law and not v.get("ITEM_NAME")
    watched = rules.is_watched(company_key(corp))
    seq = (v.get("ITEM_SEQ") or "").split(",")[0].strip()
    what = _clip(v.get("ITEM_NAME") or "", 60)
    return _row("mfds:admin", v.get("ADM_DISPS_SEQ") or _h(corp, law), corp,
                f"[행정처분] {what + ' · ' if what else ''}{_clip(v.get('ADM_DISPS_NAME'), 90)}",
                _ymd(v.get("LAST_SETTLE_DATE")), GRAY if cosmetic else (RED if watched else YELLOW),
                f"{_clip(v.get('EXPOSE_CONT'), 600)}\n처분: {_clip(v.get('ADM_DISPS_NAME'), 300)}",
                NEDRUG_ITEM.format(seq) if seq else NEDRUG_HOME, watched, v.get("BIZRNO") or "")


async def _shortage(c: GovClient):
    return await c.data_go_latest("MdcinPrdctnIncmeSuplyService2/getMdcinPrdctnIncmeSuplyList", 100, 2)


def _shortage_row(v: dict, rules: Rules) -> dict | None:
    corp, seq = v.get("ENTP_NAME") or "", v.get("ITEM_SEQ") or ""
    watched = rules.is_watched(company_key(corp))
    reason = v.get("SUSPEND_REASON") or "-"
    return _row("mfds:shortage", v.get("SUSPEND_REPORT_SEQ") or _h(corp, seq), corp,
                f"[공급중단 보고] {v.get('ITEM_NAME') or ''} ({v.get('SUSPEND_REPORT_FLAG') or ''})",
                _ymd(v.get("REPORT_DATE")), RED if watched else YELLOW,
                f"중단(예정)일 {v.get('SUSPEND_DATE') or '-'} · 사유: {_clip(reason, 300)} · 처리 상태: {v.get('REPORT_PGS_CODE') or '-'}",
                NEDRUG_ITEM.format(seq) if seq else NEDRUG_HOME, watched, v.get("BIZRNO") or "")


async def _trial(c: GovClient):
    return await c.data_go_latest("MdcinClincTestInfoService02/getMdcinClincTestInfoList02", 100, 2)


def _trial_row(v: dict, rules: Rules) -> dict | None:
    corp, step = (v.get("APPLY_ENTP_NAME") or "").strip(), (v.get("CLINIC_STEP_NAME") or "").strip()
    watched = rules.is_watched(company_key(corp))
    be = step in ("생동", "생물학적동등성") or "생물학적 동등성" in (v.get("CLINIC_EXAM_TITLE") or "")
    level = GRAY if be else (RED if watched else YELLOW)
    return _row("mfds:trial", v.get("CLNC_TEST_SN") or _h(corp, v.get("GOODS_NAME")), corp,
                f"[임상 승인] {v.get('GOODS_NAME') or ''} {step}".strip(), _ymd(v.get("APPROVAL_TIME")), level,
                f"{_clip(v.get('CLINIC_EXAM_TITLE'), 500)}\n실시기관: {_clip(v.get('LAB_NAME'), 300)}",
                NEDRUG_HOME, watched)


async def _device_recall(c: GovClient):
    items = await c.data_go_latest("MdlpRtrvlSleStpgeInfoService04/getItemNameList04", 100, 1)
    firms = await c.data_go_latest("MdlpRtrvlSleStpgeInfoService04/getCompanyNameList04", 100, 1)
    by_time = {f.get("REPORT_SUBMIT_DATE"): f for f in firms}
    for i in items:  # 품목 목록에는 업체명이 없어 같은 보고 시각의 업체 목록과 맞춘다
        i["_firm"] = by_time.get(i.get("REPORT_SUBMIT_DATE")) or {}
    return items


def _device_recall_row(v: dict, rules: Rules) -> dict | None:
    firm = v.get("_firm") or {}
    corp = firm.get("ENTP_NAME") or "(업체 미상)"
    watched = rules.is_watched(company_key(corp))
    return _row("mfds:devrecall", f"{v.get('DEPT_RECEIPT_NO')}:{v.get('RECALL_ITEM_SEQ')}", corp,
                f"[의료기기 회수] {v.get('ITEM_NAME') or ''} ({v.get('RECALL_REPORT_NAME') or '보고'})",
                _ymd(v.get("REPORT_SUBMIT_DATE")), RED if watched else YELLOW,
                f"{v.get('GRADE') or '-'}등급 · 품목 {v.get('MEA_CLASS_NAME') or '-'} · {firm.get('REPORT_KIND_NAME') or ''}"
                f"{' · 사유: ' + _clip(firm.get('RTRVL_RESN_CN'), 300) if firm.get('RTRVL_RESN_CN') else ''}",
                NEDRUG_HOME, watched, firm.get("BRNO") or "")


# --- 국회 -----------------------------------------------------------------------------------
COMMITTEE = "보건복지위원회"


async def _bills(c: GovClient):
    return await c.assembly("nzmimeepazxkubdpn", 1, 100, AGE=22, COMMITTEE=COMMITTEE)


def _bill_row(v: dict, rules: Rules) -> dict | None:
    proposer = v.get("PROPOSER") or ""
    lead = re.sub(r"의원.*$", "", proposer).strip()
    return _row("assembly:bill", v.get("BILL_ID") or v.get("BILL_NO"), f"{lead} 의원" if lead else proposer or "국회",
                f"[법안 발의] {v.get('BILL_NAME') or ''}", _ymd(v.get("PROPOSE_DT")), YELLOW,
                f"제안: {proposer} · 소관: {v.get('COMMITTEE') or COMMITTEE} · 의안번호 {v.get('BILL_NO') or '-'}",
                v.get("DETAIL_LINK") or "https://likms.assembly.go.kr/bill/", False)


async def _plenary(c: GovClient):
    rows = await c.assembly("nwbpacrgavhjryiph", 1, 100, AGE=22)
    return [r for r in rows if (r.get("COMMITTEE_NM") or "") == COMMITTEE]


def _plenary_row(v: dict, rules: Rules) -> dict | None:
    result = v.get("PROC_RESULT_CD") or "처리"
    passed = "가결" in result
    votes = (f"재석 {v.get('VOTE_TCNT')} · 찬성 {v.get('YES_TCNT')} · 반대 {v.get('NO_TCNT')} · 기권 {v.get('BLANK_TCNT')}"
             if v.get("VOTE_TCNT") else "표결 정보 없음")
    return _row("assembly:plenary", v.get("BILL_ID") or v.get("BILL_NO"), "국회 본회의",
                f"[본회의 {result}] {v.get('BILL_NM') or ''}", _ymd(v.get("RGS_PROC_DT")), RED if passed else YELLOW,
                f"{votes} · 제안: {v.get('PROPOSER') or '-'} · 소관: {COMMITTEE}",
                v.get("LINK_URL") or "https://likms.assembly.go.kr/bill/", False)


async def _seminars(c: GovClient):
    rows = await c.assembly("nfcoioopazrwmjrgs", 1, 100)
    return [r for r in rows if any(w in f"{r.get('TITLE')} {r.get('NAME')} {r.get('DESCRIPTION')}" for w in HEALTH_WORDS)]


def _seminar_row(v: dict, rules: Rules) -> dict | None:
    day = _ymd(v.get("SDATE"))
    if not day:
        return None
    md = f"{int(day[4:6])}/{int(day[6:8])}"
    row = _row("assembly:seminar", f"{day}:{_h(v.get('TITLE'))}", v.get("NAME") or "국회",
               f"[토론회 {md}] {v.get('TITLE') or ''}", day, YELLOW,
               f"일시 {v.get('SDATE')} {v.get('STIME') or ''} · 장소 {v.get('LOCATION') or '-'}\n{_clip(v.get('DESCRIPTION'), 600)}",
               v.get("LINK") or "https://ampos.nanet.go.kr:7443/seminarList.do", False)
    row["event"] = True  # 날짜가 행사일이라 '접수일'로는 오늘을 쓴다
    return row


FEEDS: list[Feed] = [
    Feed("mfds:recall", "mfds", "의약품 회수", _recall, _recall_row),
    Feed("mfds:letter", "mfds", "안전성서한", _letter, _letter_row),
    Feed("mfds:admin", "mfds", "의약품 행정처분", _admin, _admin_row),
    Feed("mfds:shortage", "mfds", "공급중단 보고", _shortage, _shortage_row),
    Feed("mfds:trial", "mfds", "임상시험 승인", _trial, _trial_row),
    Feed("mfds:devrecall", "mfds", "의료기기 회수", _device_recall, _device_recall_row),
    Feed("assembly:bill", "assembly", "법안 발의", _bills, _bill_row, "na"),
    Feed("assembly:plenary", "assembly", "본회의 처리", _plenary, _plenary_row, "na"),
    Feed("assembly:seminar", "assembly", "토론회", _seminars, _seminar_row, "na"),
]


@dataclass
class GovCollector:
    client: GovClient
    db: Database
    rules: Rules
    feeds: list[Feed] = field(default_factory=lambda: list(FEEDS))

    def enabled_feeds(self) -> list[Feed]:
        return [f for f in self.feeds if (self.client.dg_key if f.needs == "dg" else self.client.na_key)]

    async def poll(self) -> tuple[list[dict], dict[str, str]]:
        """모든 피드를 한 번 돈다. (새로 저장한 알림 대상 행, 피드별 상태)."""
        new_rows: list[dict] = []
        status: dict[str, str] = {}
        for feed in self.enabled_feeds():
            try:
                raw = await feed.fetch(self.client)
                rows, added = self._ingest(feed, raw)
                new_rows += rows
                status[feed.key] = f"정상 · {added}건 추가"
            except Exception as e:  # noqa: BLE001 - 한 피드가 실패해도 나머지는 돈다
                status[feed.key] = f"오류: {_clip(repr(e), 180)}"
                self.db.log("error", f"gov {feed.key}: {e!r}"[:400])
                log.warning("gov feed %s failed: %r", feed.key, e)
        return new_rows, status

    def _ingest(self, feed: Feed, raw: list[dict]) -> tuple[list[dict], int]:
        boot_key = f"gov_boot:{feed.key}"
        boot = self.db.get(boot_key) or ""
        first = not boot
        today = now().strftime("%Y%m%d")
        # 수집을 시작한 날(전날까지 여유). 그보다 앞선 날짜의 항목은 늦게 보여도 새 소식이 아니므로 알리지 않는다
        boot_day = boot if len(boot) == 8 else today
        watch_from = (datetime.strptime(boot_day, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
        boot_cut = (now() - timedelta(days=BOOTSTRAP_DAYS)).strftime("%Y%m%d")
        keep_cut = (now() - timedelta(days=KEEP_DAYS)).strftime("%Y%m%d")
        alerts, added = [], 0
        for v in raw:
            try:
                r = feed.convert(v, self.rules)
            except Exception as e:  # noqa: BLE001 - 형식이 다른 한 건 때문에 피드 전체가 멈추지 않게
                self.db.log("error", f"gov {feed.key} convert: {e!r}"[:300])
                continue
            if not r:
                continue
            event = r.pop("event", False)
            date = r["rcept_dt"]
            if not event and date < (boot_cut if first else keep_cut):
                continue
            key = r.pop("ref")
            if self.db.one("SELECT 1 FROM disclosures WHERE rcept_no=?", (key,)):
                continue
            quiet = first or (not event and date < watch_from)
            seen_at = now_iso()
            if quiet and not event and date < today:
                # 처음 들여온 과거 항목은 그날 수집된 것처럼 둔다 ('미확인' 3일 창에 몰리지 않게)
                seen_at = f"{date[:4]}-{date[4:6]}-{date[6:8]}T09:00:00+09:00"
            row = {**r, "rcept_no": key, "stock_code": None, "flr_nm": "식약처" if feed.source == "mfds" else "국회",
                   "keyword": feed.label, "is_correction": 0, "first_seen_at": seen_at, "source": feed.source,
                   "alerted_at": "bootstrap" if quiet else None}
            if event:
                row["rcept_dt"] = today
            self.db.execute(
                """INSERT OR IGNORE INTO disclosures(rcept_no, corp_code, corp_name, stock_code, report_nm, rcept_dt,
                   flr_nm, rm, level, keyword, is_correction, watched, first_seen_at, source, link, alerted_at)
                   VALUES(:rcept_no,:corp_code,:corp_name,:stock_code,:report_nm,:rcept_dt,:flr_nm,:rm,:level,:keyword,
                          :is_correction,:watched,:first_seen_at,:source,:link,:alerted_at)""", row)
            added += 1
            if not quiet:
                alerts.append(row)
        if first:
            self.db.set(boot_key, today)
        return alerts, added
