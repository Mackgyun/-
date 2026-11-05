# Codex 교차검증 요청 (2026-11-05 갱신)

너는 독립 검토자다. 아래는 한국 의료전문지(청년의사, 직원 30~40명, 기자 약 20명) 기자가 만드는 **자체 웹앱 '청년의사 브리핑'**의 설계와 1단계 코드다. 다른 AI(Claude)가 작성했고, 다른 Claude 에이전트가 이미 한 번 검토했다(그 결과는 반영됨). 칭찬하지 말고 **틀린 것, 위험한 것, 빠진 것**을 찾아라.

시스템 개요:
- Windows 여분 노트북에서 24시간 실행하는 FastAPI 서버 + SQLite
- OpenDART 공시를 5분마다 수집, 보건의료 기업만 골라 중요도 분류
- 자체 웹앱(PWA): PC는 웹 푸시로 Windows 알림(오른쪽 아래), 휴대폰은 홈 화면 앱 푸시
- 초대 링크 기반 다중 사용자, [내가 쓸게요](담당 표시)
- 다음 단계: 알리오, 보도자료 메일, LLM(Claude/OpenAI) 질문·기사 초안

검토할 것:
1. 보안: 인증·세션·초대 코드, 로그인 잠금, CSP·쿠키, XSS, CSRF(SameSite=Lax 쿠키 + JSON API로 충분한지), 인터넷 공개(터널) 시 위험, 비밀값 저장
2. 정확성: DART 수집 로직(15분 지연·순서 뒤섞임 대응, 부트스트랩, 자정 경계, 한도), 분류 규칙 오탐·누락, 동시성(SQLite + 스레드 + asyncio)
3. 웹 푸시: VAPID, 서비스 워커, Windows 알림 표시, iOS 제약
4. Windows 운영: 작업 스케줄러 스크립트, 전원 설정, PowerShell 인코딩
5. UX/접근성: 화면 구성, 키보드, 다크 모드, 모바일
6. 우선순위 Top 10 수정 제안 (구체적으로, 파일과 줄 수준)

답변은 한국어로, 항목마다 심각도(상/중/하)와 근거를 붙여라. 확실하지 않은 것은 "확인 필요"로 표시하라.

---

# [첨부] 1단계 설계

# 1단계 설계: DART 수집 + 자체 웹앱 (2026-11-05 갱신)

처음 설계(텔레그램 봇)에서 **자체 웹앱(PWA)**으로 바꿨고, 독립 검토(`review_independent.md`)의 지적을 반영했습니다.

## 바뀐 결정
| 항목 | 처음 | 지금 | 이유 |
| --- | --- | --- | --- |
| 알림 창구 | 텔레그램 | 자체 웹앱 + 웹 푸시 (PC 오른쪽 아래 팝업, 휴대폰 홈 화면 앱) | 독자 프로그램 원함, 한 코드로 PC·휴대폰 |
| DART 누락 방지 | 이미 본 공시 나오면 중단 | 매번 최근 3페이지(300건) 재확인 + 매시간 이틀치 전체 대조 | DART는 제출 후 약 15분 뒤 공개, 순서 뒤섞임 |
| 기업 판별 | 업종코드(KSIC) | 감시 기업 목록이 기준, 업종코드는 보조 | 지주사·의료 AI 기업이 업종코드로는 빠짐 |
| 정정공시 | 원공시처럼 다시 빨강 알림 | 등급은 유지하고 '정정' 표시, 팝업 없음 | 중복 알림 방지 |
| 오탐 | 단순 키워드 | red_exclude(합병등종료보고서, 주식분할 등)로 낮춤 | 검토 지적 |
| 알림 시작 | 바로 | 처음 2주 `ALERT_MODE=log`(기록만) | 알림량 실측 후 켜기 |
| 원격 관리 | Tailscale | 웹앱 관리자 화면 + `/healthz` 외부 감시 | 상업적 사용 제약, 회사망 VPN 문제 |
| 노트북 실행 | Docker Desktop | Python 직접 실행 + 작업 스케줄러(작업 폴더 지정) | Docker Desktop은 로그인해야 실행 |

## 구성
- `newsbot/dart.py`: OpenDART `list.json`(최근 2일, 100건씩), 처음 보는 회사만 `company.json`으로 업종코드 조회해 캐시. 상태 `020`이나 자체 일일 한도 도달 시 `DartLimitReached`. 첫 실행은 부트스트랩(저장만, 알림 없음).
- `newsbot/rules.py`: 제목 앞 `[...]` 접두어 분리, '정정' 포함 시 정정공시. red → red_exclude → gray → yellow 순.
- `newsbot/db.py`: SQLite(WAL), users / sessions / invites / subscriptions / companies / disclosures / claims / push_subs / events / kv.
- `newsbot/auth.py`: scrypt 비밀번호 해시, 30일 세션 쿠키(HttpOnly, SameSite=Lax, HTTPS면 Secure), 1회용 7일 초대 코드, 로그인 5회 실패 10분 잠금.
- `newsbot/push.py`: VAPID 키 자동 생성(`data/vapid_private.pem`), 구독 저장, 404/410이면 구독 삭제. 받는 사람 = 구독(전체 / 감시 기업 전체 / 기업 / 키워드)에 맞는 사용자.
- `newsbot/app.py`: FastAPI. 보안 헤더(CSP self, frame-ancestors none), API(로그인·가입·피드·요약·상세·담당·구독·푸시·관리자), 백그라운드 수집 루프(예외가 나도 멈추지 않고 기록).
- `newsbot/static/`: 프레임워크 없는 HTML/CSS/JS. 모든 텍스트는 textContent로 넣음(XSS 방지), 서비스 워커(sw.js)로 푸시 표시.

## UX (2026 트렌드 반영)
요약 먼저(오늘의 브리핑 벤토 카드) → 한 줄 피드 → 상세 패널, 출처 칩(DART 원문), 등급은 색+아이콘+글자, 키보드 J/K/Enter/C, 다크 모드 자동, 글자 크기 조절, 움직임 줄이기 존중, 반투명은 상단바·질문창에만.

## 알려진 한계
- 웹 푸시는 HTTPS 또는 localhost에서만. 다른 기기 알림은 터널 연결 후.
- 로그인 실패 잠금은 메모리 기준이라 재시작하면 초기화.
- Windows 스크립트는 실제 Windows에서 아직 실행해 보지 않음.
- 질문·초안·메일·알리오는 다음 단계.

---

# [첨부] config/rules.toml

```toml
# 공시 분류 규칙
#
# 등급
#   red    : 중요. notify 모드에서 구독자에게 팝업·푸시
#   yellow : 피드에만 조용히 표시
#   gray   : 기록만 (피드 기본 화면에서 숨김)
#
# 판단 순서 (공시 제목 report_nm 기준, 띄어쓰기 무시)
#   1. 정정공시([기재정정] 등)는 원래 등급을 매기되 팝업은 보내지 않음
#   2. red_exclude 에 걸리면 yellow
#   3. red 키워드 → red
#   4. gray 키워드 → gray
#   5. 나머지 → yellow

[watch]
# 감시 기업 목록 (DART 회사명). 이 목록이 기준이고 업종코드는 보조입니다.
# 아래는 예시이니 출입처에 맞게 고쳐 주세요. 회사명은 DART 표기와 같아야 합니다.
companies = [
  "삼성바이오로직스", "셀트리온", "유한양행", "한미약품", "한미사이언스",
  "종근당", "대웅제약", "대웅", "녹십자", "녹십자홀딩스",
  "JW중외제약", "JW홀딩스", "SK바이오팜", "SK바이오사이언스", "동아에스티",
  "동아쏘시오홀딩스", "보령", "일동제약", "광동제약", "HK이노엔",
  "알테오젠", "에이치엘비", "리가켐바이오사이언스", "에이비엘바이오", "휴젤",
  "메디톡스", "루닛", "뷰노", "제이엘케이", "큐렉소",
]

[health]
# 감시 목록 밖의 회사도 이 업종코드(KSIC) 앞자리면 보건의료로 보고 피드에 넣습니다.
# 21: 의약품 제조, 271: 의료용 기기 제조, 86: 보건업, 70113: 의학·약학 연구개발
industry_prefixes = ["21", "271", "86", "70113"]
always_exclude = []

[levels]
red = [
  "품목허가", "임상시험", "기술이전", "기술도입", "라이선스",
  "유상증자", "전환사채", "신주인수권부사채", "최대주주변경", "경영권",
  "회사합병결정", "회사분할결정", "영업양수", "영업양도", "공개매수",
  "단일판매", "공급계약", "횡령", "배임", "소송등의제기",
  "영업정지", "회생절차", "상장폐지", "관리종목", "매매거래정지",
  "감사의견", "불성실공시", "조회공시", "타법인주식및출자증권취득결정",
]

# red 키워드가 있어도 yellow 로 내리는 표현 (오탐 방지)
red_exclude = [
  "합병등종료보고서", "분할상환", "주식분할", "액면분할", "증권발행실적보고서",
]

gray = [
  "임원ㆍ주요주주특정증권등소유상황보고서",
  "주식등의대량보유상황보고서",
  "기업설명회",
  "투자설명서",
  "자기주식취득결과보고서",
  "기타경영사항(자율공시)",
]
```

---

# [첨부] newsbot/config.py

```py
"""환경변수(.env)에서 설정을 읽는다."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")
BASE_DIR = Path(__file__).resolve().parent.parent  # newsbot/ 폴더 (작업 스케줄러가 System32에서 띄워도 안전)


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else BASE_DIR / p


@dataclass(frozen=True)
class Settings:
    dart_api_key: str = ""
    alert_mode: str = "log"  # log | notify
    host: str = "127.0.0.1"
    port: int = 8000
    public_url: str = "http://localhost:8000"
    vapid_contact: str = "mailto:admin@example.com"
    db_path: Path = BASE_DIR / "data/newsbot.db"
    rules_path: Path = BASE_DIR / "config/rules.toml"
    data_dir: Path = BASE_DIR / "data"
    poll_interval_sec: int = 300
    dart_rescan_pages: int = 3
    dart_daily_call_limit: int = 18000

    @property
    def notify_enabled(self) -> bool:
        return self.alert_mode == "notify"

    @property
    def secure_cookies(self) -> bool:
        return self.public_url.startswith("https://")


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or BASE_DIR / ".env")
    mode = os.getenv("ALERT_MODE", "log").strip().lower()
    if mode not in ("log", "notify"):
        raise SystemExit("ALERT_MODE 는 log 또는 notify 여야 합니다.")
    db_path = _path(os.getenv("DB_PATH", "data/newsbot.db"))
    return Settings(
        dart_api_key=os.getenv("DART_API_KEY", "").strip(),
        alert_mode=mode,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        public_url=os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/"),
        vapid_contact=os.getenv("VAPID_CONTACT", "mailto:admin@example.com"),
        db_path=db_path,
        rules_path=_path(os.getenv("RULES_PATH", "config/rules.toml")),
        data_dir=db_path.parent,
        poll_interval_sec=max(60, int(os.getenv("POLL_INTERVAL_SEC", "300"))),
        dart_rescan_pages=max(1, int(os.getenv("DART_RESCAN_PAGES", "3"))),
        dart_daily_call_limit=int(os.getenv("DART_DAILY_CALL_LIMIT", "18000")),
    )
```

---

# [첨부] newsbot/rules.py

```py
"""공시 분류 규칙 (config/rules.toml)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

RED, YELLOW, GRAY = "red", "yellow", "gray"
LEVELS = (RED, YELLOW, GRAY)

_PREFIX = re.compile(r"^\s*\[([^\]]+)\]")


def _norm(text: str) -> str:
    """띄어쓰기 차이를 무시하기 위해 공백을 모두 지운다."""
    return "".join(text.split())


def split_prefix(report_nm: str) -> tuple[str | None, str]:
    """'[기재정정]주요사항보고서...' → ('기재정정', '주요사항보고서...')."""
    m = _PREFIX.match(report_nm)
    if not m:
        return None, report_nm.strip()
    return m.group(1).strip(), report_nm[m.end():].strip()


@dataclass(frozen=True)
class Classification:
    level: str
    keyword: str | None
    is_correction: bool
    prefix: str | None

    @property
    def should_alert(self) -> bool:
        return self.level == RED and not self.is_correction


@dataclass(frozen=True)
class Rules:
    watch: frozenset[str] = frozenset()
    industry_prefixes: tuple[str, ...] = ()
    always_exclude: frozenset[str] = frozenset()
    red: tuple[str, ...] = ()
    red_exclude: tuple[str, ...] = ()
    gray: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict) -> "Rules":
        levels = data.get("levels", {})
        health = data.get("health", {})
        return cls(
            watch=frozenset(_norm(c) for c in data.get("watch", {}).get("companies", [])),
            industry_prefixes=tuple(health.get("industry_prefixes", [])),
            always_exclude=frozenset(_norm(c) for c in health.get("always_exclude", [])),
            red=tuple(levels.get("red", [])),
            red_exclude=tuple(levels.get("red_exclude", [])),
            gray=tuple(levels.get("gray", [])),
        )

    @classmethod
    def load(cls, path: Path) -> "Rules":
        with open(path, "rb") as f:
            return cls.from_dict(tomllib.load(f))

    def is_watched(self, corp_name: str) -> bool:
        return _norm(corp_name) in self.watch

    def is_relevant(self, corp_name: str, induty_code: str | None) -> bool:
        """피드에 넣을 회사인가: 감시 목록이거나 보건의료 업종."""
        name = _norm(corp_name)
        if name in self.always_exclude:
            return False
        if name in self.watch:
            return True
        return bool(induty_code) and any(induty_code.startswith(p) for p in self.industry_prefixes)

    def needs_industry_lookup(self, corp_name: str) -> bool:
        return _norm(corp_name) not in self.watch and _norm(corp_name) not in self.always_exclude

    def classify(self, report_nm: str) -> Classification:
        prefix, body = split_prefix(report_nm)
        is_correction = bool(prefix) and "정정" in prefix
        title = _norm(body)

        level, keyword = YELLOW, None
        if not any(_norm(x) in title for x in self.red_exclude):
            for k in self.red:
                if _norm(k) in title:
                    level, keyword = RED, k
                    break
        if level == YELLOW:
            for k in self.gray:
                if _norm(k) in title:
                    level, keyword = GRAY, k
                    break
        return Classification(level, keyword, is_correction, prefix)
```

---

# [첨부] newsbot/db.py

```py
"""SQLite 저장소. 한 프로세스 안에서 여러 스레드가 공유한다."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .config import KST

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  pw_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'reporter',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invites (
  code TEXT PRIMARY KEY,
  role TEXT NOT NULL DEFAULT 'reporter',
  created_by INTEGER,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_by INTEGER,
  used_at TEXT
);
CREATE TABLE IF NOT EXISTS subscriptions (
  user_id INTEGER NOT NULL REFERENCES users(id),
  kind TEXT NOT NULL,           -- company | keyword | all
  value TEXT NOT NULL,
  PRIMARY KEY (user_id, kind, value)
);
CREATE TABLE IF NOT EXISTS companies (
  corp_code TEXT PRIMARY KEY,
  corp_name TEXT NOT NULL,
  induty_code TEXT,
  fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS disclosures (
  rcept_no TEXT PRIMARY KEY,
  corp_code TEXT NOT NULL,
  corp_name TEXT NOT NULL,
  stock_code TEXT,
  report_nm TEXT NOT NULL,
  rcept_dt TEXT NOT NULL,
  flr_nm TEXT,
  rm TEXT,
  level TEXT NOT NULL,
  keyword TEXT,
  is_correction INTEGER NOT NULL DEFAULT 0,
  watched INTEGER NOT NULL DEFAULT 0,
  first_seen_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_disc_seen ON disclosures(first_seen_at DESC);
CREATE TABLE IF NOT EXISTS claims (
  rcept_no TEXT PRIMARY KEY REFERENCES disclosures(rcept_no),
  user_id INTEGER NOT NULL REFERENCES users(id),
  claimed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS push_subs (
  endpoint TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  kind TEXT NOT NULL,           -- poll | error | alert | login ...
  detail TEXT
);
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


def now() -> datetime:
    return datetime.now(KST)


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(SCHEMA)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise

    def query(self, sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple | dict = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: tuple | dict = ()) -> int:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.rowcount

    # --- kv ---------------------------------------------------------------
    def get(self, key: str, default: str | None = None) -> str | None:
        row = self.one("SELECT value FROM kv WHERE key=?", (key,))
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        self.execute(
            "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def log(self, kind: str, detail: str = "") -> None:
        self.execute("INSERT INTO events(at, kind, detail) VALUES(?,?,?)", (now_iso(), kind, detail[:2000]))
        # 이벤트는 최근 5,000건만 보관
        self.execute("DELETE FROM events WHERE id <= (SELECT MAX(id) - 5000 FROM events)")
```

---

# [첨부] newsbot/dart.py

```py
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
```

---

# [첨부] newsbot/auth.py

```py
"""비밀번호 해시, 세션, 초대 코드, 로그인 실패 제한."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from datetime import timedelta

from .db import Database, now, now_iso

SESSION_DAYS = 30
INVITE_DAYS = 7
MAX_FAILS = 5
LOCK_SECONDS = 600

_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return hmac.compare_digest(actual, expected)


def validate_password(password: str) -> str | None:
    if len(password) < 10:
        return "비밀번호는 10자 이상이어야 합니다."
    return None


class LoginLimiter:
    """아이디·IP별 연속 실패 5회면 10분 잠금 (메모리 기준)."""

    def __init__(self):
        self._fails: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def locked(self, key: str) -> bool:
        with self._lock:
            count, since = self._fails.get(key, (0, 0.0))
            if count >= MAX_FAILS and time.monotonic() - since < LOCK_SECONDS:
                return True
            if count >= MAX_FAILS:
                self._fails.pop(key, None)
            return False

    def fail(self, key: str) -> None:
        with self._lock:
            count, _ = self._fails.get(key, (0, 0.0))
            self._fails[key] = (count + 1, time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


def create_user(db: Database, username: str, display_name: str, password: str, role: str = "reporter") -> int:
    with db.tx() as c:
        cur = c.execute(
            "INSERT INTO users(username, display_name, pw_hash, role, created_at) VALUES(?,?,?,?,?)",
            (username.strip().lower(), display_name.strip(), hash_password(password), role, now_iso()),
        )
        return int(cur.lastrowid)


def authenticate(db: Database, username: str, password: str) -> dict | None:
    user = db.one("SELECT * FROM users WHERE username=? AND active=1", (username.strip().lower(),))
    if user and verify_password(password, user["pw_hash"]):
        return user
    # 존재하지 않는 아이디도 같은 시간이 걸리도록 해시 한 번 계산
    if not user:
        verify_password(password, hash_password("timing-equalizer"))
    return None


def create_session(db: Database, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = (now() + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds")
    db.execute("INSERT INTO sessions(token, user_id, expires_at) VALUES(?,?,?)", (token, user_id, expires))
    db.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),))
    return token


def session_user(db: Database, token: str | None) -> dict | None:
    if not token:
        return None
    return db.one(
        """SELECT u.id, u.username, u.display_name, u.role FROM sessions s
           JOIN users u ON u.id = s.user_id
           WHERE s.token=? AND s.expires_at > ? AND u.active=1""",
        (token, now_iso()),
    )


def delete_session(db: Database, token: str) -> None:
    db.execute("DELETE FROM sessions WHERE token=?", (token,))


def create_invite(db: Database, created_by: int | None, role: str = "reporter") -> str:
    code = secrets.token_urlsafe(12)
    expires = (now() + timedelta(days=INVITE_DAYS)).isoformat(timespec="seconds")
    db.execute(
        "INSERT INTO invites(code, role, created_by, created_at, expires_at) VALUES(?,?,?,?,?)",
        (code, role, created_by, now_iso(), expires),
    )
    return code


def redeem_invite(db: Database, code: str, username: str, display_name: str, password: str) -> int:
    """초대 코드로 가입. 실패하면 ValueError(사용자에게 보여줄 문구)."""
    problem = validate_password(password)
    if problem:
        raise ValueError(problem)
    if not username.strip() or not display_name.strip():
        raise ValueError("아이디와 이름을 입력해 주세요.")
    with db.tx() as c:
        inv = c.execute(
            "SELECT * FROM invites WHERE code=? AND used_by IS NULL AND expires_at > ?", (code, now_iso())
        ).fetchone()
        if not inv:
            raise ValueError("초대 링크가 만료됐거나 이미 사용됐습니다.")
        if c.execute("SELECT 1 FROM users WHERE username=?", (username.strip().lower(),)).fetchone():
            raise ValueError("이미 있는 아이디입니다.")
        cur = c.execute(
            "INSERT INTO users(username, display_name, pw_hash, role, created_at) VALUES(?,?,?,?,?)",
            (username.strip().lower(), display_name.strip(), hash_password(password), inv["role"], now_iso()),
        )
        user_id = int(cur.lastrowid)
        c.execute("UPDATE invites SET used_by=?, used_at=? WHERE code=?", (user_id, now_iso(), code))
        return user_id
```

---

# [첨부] newsbot/push.py

```py
"""웹 푸시 (PC 오른쪽 아래 팝업, 휴대폰 홈 화면 앱 알림)."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from .db import Database, now_iso
from .rules import Rules

log = logging.getLogger(__name__)


class Pusher:
    def __init__(self, db: Database, data_dir: Path, contact: str, enabled: bool):
        self.db = db
        self.enabled = enabled
        self.contact = contact
        self.key_path = data_dir / "vapid_private.pem"
        if not self.key_path.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            v = Vapid()
            v.generate_keys()
            v.save_key(str(self.key_path))
        self.vapid = Vapid.from_file(str(self.key_path))

    @property
    def public_key(self) -> str:
        raw = self.vapid.public_key.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    def subscribe(self, user_id: int, sub: dict) -> None:
        keys = sub.get("keys") or {}
        if not sub.get("endpoint") or not keys.get("p256dh") or not keys.get("auth"):
            raise ValueError("잘못된 구독 정보")
        self.db.execute(
            """INSERT INTO push_subs(endpoint, user_id, p256dh, auth, created_at) VALUES(?,?,?,?,?)
               ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id, p256dh=excluded.p256dh,
               auth=excluded.auth""",
            (sub["endpoint"], user_id, keys["p256dh"], keys["auth"], now_iso()),
        )

    def unsubscribe(self, endpoint: str) -> None:
        self.db.execute("DELETE FROM push_subs WHERE endpoint=?", (endpoint,))

    def send_to_user(self, user_id: int, payload: dict, force: bool = False) -> int:
        """동기 함수. 이벤트 루프에서는 스레드로 돌린다. 보낸 기기 수를 돌려준다."""
        if not (self.enabled or force):
            return 0
        sent = 0
        for s in self.db.query("SELECT * FROM push_subs WHERE user_id=?", (user_id,)):
            info = {"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}}
            try:
                webpush(
                    info,
                    json.dumps(payload, ensure_ascii=False),
                    vapid_private_key=self.vapid,
                    vapid_claims={"sub": self.contact},
                    ttl=3600,
                    timeout=10,
                )
                sent += 1
            except WebPushException as e:
                status = getattr(e.response, "status_code", None)
                if status in (404, 410):  # 브라우저가 구독을 버림
                    self.unsubscribe(s["endpoint"])
                else:
                    log.warning("push failed: %s", e)
                    self.db.log("error", f"push: {e}")
        return sent


def recipients(db: Database, rules: Rules, row: dict) -> list[int]:
    """이 공시를 알림받을 사용자: 전체 구독, 기업 구독, 키워드 구독."""
    users = set()
    for s in db.query("SELECT s.user_id, s.kind, s.value FROM subscriptions s JOIN users u ON u.id=s.user_id WHERE u.active=1"):
        kind, value = s["kind"], s["value"]
        if kind == "all":
            users.add(s["user_id"])
        elif kind == "watch" and row.get("watched"):
            users.add(s["user_id"])
        elif kind == "company" and "".join(value.split()) == "".join(row["corp_name"].split()):
            users.add(s["user_id"])
        elif kind == "keyword" and "".join(value.split()) in "".join(row["report_nm"].split()):
            users.add(s["user_id"])
    return sorted(users)


def payload_for(row: dict, public_url: str) -> dict:
    return {
        "title": f"{row['corp_name']} · 중요 공시",
        "body": row["report_nm"],
        "url": f"{public_url}/#d/{row['rcept_no']}",
        "tag": row["rcept_no"],
    }
```

---

# [첨부] newsbot/app.py

```py
"""웹앱 서버 (FastAPI). 화면은 static/ 의 정적 파일로 제공한다."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth
from .config import Settings
from .dart import VIEW_URL, Collector, DartClient, DartError, DartLimitReached
from .db import Database, now, now_iso
from .push import Pusher, payload_for, recipients
from .rules import RED, Rules

log = logging.getLogger(__name__)
STATIC = Path(__file__).resolve().parent / "static"
COOKIE = "nb_session"


class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    code: str
    username: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=1, max_length=40)
    password: str


class SubIn(BaseModel):
    kind: str = Field(pattern=r"^(all|watch|company|keyword)$")
    value: str = Field(default="", max_length=60)


class PushIn(BaseModel):
    endpoint: str
    keys: dict


class InviteIn(BaseModel):
    role: str = Field(default="reporter", pattern=r"^(reporter|admin)$")


class Poller:
    """백그라운드 수집 루프."""

    def __init__(self, settings: Settings, db: Database, rules: Rules, pusher: Pusher):
        self.settings = settings
        self.db = db
        self.rules = rules
        self.pusher = pusher
        self.client = DartClient(settings.dart_api_key, db, settings.dart_daily_call_limit)
        self.collector = Collector(self.client, db, rules, settings.dart_rescan_pages)
        self._last_full = None

    async def run_forever(self) -> None:
        if not self.settings.dart_api_key:
            self.db.set("dart_status", "키 없음: .env 에 DART_API_KEY 를 넣으면 수집을 시작합니다")
            return
        while True:
            await self.run_once()
            await asyncio.sleep(self.settings.poll_interval_sec)

    async def run_once(self) -> None:
        full = self._last_full is None or now() - self._last_full > timedelta(hours=1)
        try:
            result = await self.collector.poll(full=full)
            if full:
                self._last_full = now()
            self.db.set("dart_status", "정상")
            self.db.set("dart_fail_count", "0")
            self.db.log("poll", f"pages={result.pages} scanned={result.scanned} new={len(result.new)}"
                                f"{' bootstrap' if result.bootstrap else ''}")
            if not result.bootstrap:
                await self._alert(result.new)
        except DartLimitReached as e:
            self.db.set("dart_status", f"호출 한도 도달 ({e}) - 내일 다시 시작")
            self.db.log("error", str(e))
        except (DartError, Exception) as e:  # noqa: BLE001 - 루프가 죽지 않게 모두 기록
            fails = int(self.db.get("dart_fail_count", "0") or 0) + 1
            self.db.set("dart_fail_count", str(fails))
            self.db.set("dart_status", f"오류 {fails}회 연속: {e}")
            self.db.log("error", f"poll: {e!r}")
            log.exception("poll failed")

    async def _alert(self, rows: list[dict]) -> None:
        for row in rows:
            c_alert = row["level"] == RED and not row["is_correction"]
            if not c_alert or not self.settings.notify_enabled:
                continue
            payload = payload_for(row, self.settings.public_url)
            for user_id in recipients(self.db, self.rules, row):
                sent = await asyncio.to_thread(self.pusher.send_to_user, user_id, payload)
                self.db.log("alert", f"{row['rcept_no']} -> user {user_id} ({sent} devices)")


def create_app(settings: Settings, db: Database | None = None, start_poller: bool = True) -> FastAPI:
    db = db or Database(settings.db_path)
    rules = Rules.load(settings.rules_path)
    pusher = Pusher(db, settings.data_dir, settings.vapid_contact, settings.notify_enabled)
    limiter = auth.LoginLimiter()
    poller = Poller(settings, db, rules, pusher)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(poller.run_forever()) if start_poller else None
        yield
        if task:
            task.cancel()

    app = FastAPI(title="청년의사 브리핑", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.db, app.state.settings, app.state.poller, app.state.pusher = db, settings, poller, pusher

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp: Response = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'"
        )
        return resp

    # --- 인증 -----------------------------------------------------------
    def current_user(request: Request) -> dict:
        user = auth.session_user(db, request.cookies.get(COOKIE))
        if not user:
            raise HTTPException(401, "로그인이 필요합니다.")
        return user

    def admin_user(user: dict = Depends(current_user)) -> dict:
        if user["role"] != "admin":
            raise HTTPException(403, "관리자만 할 수 있습니다.")
        return user

    def _set_cookie(resp: Response, token: str) -> None:
        resp.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=settings.secure_cookies,
                        max_age=auth.SESSION_DAYS * 86400)

    @app.post("/api/login")
    def login(body: LoginIn, request: Request, response: Response):
        key = f"{body.username.lower()}|{request.client.host if request.client else ''}"
        if limiter.locked(key):
            raise HTTPException(429, "로그인 실패가 많아 10분 동안 잠겼습니다.")
        user = auth.authenticate(db, body.username, body.password)
        if not user:
            limiter.fail(key)
            db.log("login_fail", body.username[:40])
            raise HTTPException(401, "아이디 또는 비밀번호가 맞지 않습니다.")
        limiter.reset(key)
        _set_cookie(response, auth.create_session(db, user["id"]))
        return {"ok": True}

    @app.post("/api/register")
    def register(body: RegisterIn, response: Response):
        try:
            user_id = auth.redeem_invite(db, body.code, body.username, body.display_name, body.password)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        db.execute("INSERT OR IGNORE INTO subscriptions(user_id, kind, value) VALUES(?, 'watch', '')", (user_id,))
        _set_cookie(response, auth.create_session(db, user_id))
        return {"ok": True}

    @app.post("/api/logout")
    def logout(request: Request, response: Response):
        token = request.cookies.get(COOKIE)
        if token:
            auth.delete_session(db, token)
        response.delete_cookie(COOKIE)
        return {"ok": True}

    @app.get("/api/me")
    def me(user: dict = Depends(current_user)):
        subs = db.query("SELECT kind, value FROM subscriptions WHERE user_id=? ORDER BY kind, value", (user["id"],))
        devices = db.one("SELECT COUNT(*) n FROM push_subs WHERE user_id=?", (user["id"],))["n"]
        return {**user, "subscriptions": subs, "push_devices": devices, "alert_mode": settings.alert_mode}

    # --- 피드 -----------------------------------------------------------
    def _decorate(rows: list[dict]) -> list[dict]:
        for r in rows:
            r["url"] = VIEW_URL.format(rcept_no=r["rcept_no"])
        return rows

    @app.get("/api/feed")
    def feed(level: str = "", q: str = "", watched: int = 0, mine: int = 0, include_gray: int = 0,
             before: str = "", limit: int = 50, user: dict = Depends(current_user)):
        sql = ["""SELECT d.*, c.user_id AS claimed_by, u.display_name AS claimed_name
                  FROM disclosures d LEFT JOIN claims c ON c.rcept_no=d.rcept_no
                  LEFT JOIN users u ON u.id=c.user_id WHERE 1=1"""]
        params: list = []
        if level in ("red", "yellow", "gray"):
            sql.append("AND d.level=?")
            params.append(level)
        elif not include_gray:
            sql.append("AND d.level!='gray'")
        if q:
            sql.append("AND (d.corp_name LIKE ? OR d.report_nm LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if watched:
            sql.append("AND d.watched=1")
        if mine:
            sql.append("AND c.user_id=?")
            params.append(user["id"])
        if before:
            sql.append("AND d.first_seen_at < ?")
            params.append(before)
        sql.append("ORDER BY d.first_seen_at DESC, d.rcept_no DESC LIMIT ?")
        params.append(max(1, min(limit, 200)))
        return {"items": _decorate(db.query(" ".join(sql), tuple(params)))}

    @app.get("/api/summary")
    def summary(user: dict = Depends(current_user)):
        since = now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
        counts = {r["level"]: r["n"] for r in db.query(
            "SELECT level, COUNT(*) n FROM disclosures WHERE first_seen_at >= ? GROUP BY level", (since,))}
        top = _decorate(db.query(
            """SELECT d.*, c.user_id AS claimed_by, u.display_name AS claimed_name FROM disclosures d
               LEFT JOIN claims c ON c.rcept_no=d.rcept_no LEFT JOIN users u ON u.id=c.user_id
               WHERE d.first_seen_at >= ? AND d.level='red' AND d.is_correction=0
               ORDER BY d.watched DESC, d.first_seen_at DESC LIMIT 5""", (since,)))
        unclaimed = sum(1 for t in top if not t["claimed_by"])
        mine = db.one("SELECT COUNT(*) n FROM claims WHERE user_id=? AND claimed_at >= ?", (user["id"], since))["n"]
        return {
            "date": now().strftime("%Y-%m-%d"),
            "red": counts.get("red", 0), "yellow": counts.get("yellow", 0), "gray": counts.get("gray", 0),
            "top": top, "unclaimed_top": unclaimed, "my_claims": mine,
            "last_poll_at": db.get("last_poll_at"), "dart_status": db.get("dart_status", "대기 중"),
            "alert_mode": settings.alert_mode,
        }

    @app.get("/api/disclosures/{rcept_no}")
    def disclosure(rcept_no: str, user: dict = Depends(current_user)):
        rows = _decorate(db.query(
            """SELECT d.*, c.user_id AS claimed_by, u.display_name AS claimed_name, c.claimed_at FROM disclosures d
               LEFT JOIN claims c ON c.rcept_no=d.rcept_no LEFT JOIN users u ON u.id=c.user_id
               WHERE d.rcept_no=?""", (rcept_no,)))
        if not rows:
            raise HTTPException(404, "없는 공시입니다.")
        return rows[0]

    @app.post("/api/claims/{rcept_no}")
    def claim(rcept_no: str, user: dict = Depends(current_user)):
        with db.tx() as c:
            if not c.execute("SELECT 1 FROM disclosures WHERE rcept_no=?", (rcept_no,)).fetchone():
                raise HTTPException(404, "없는 공시입니다.")
            row = c.execute("SELECT c.user_id, u.display_name FROM claims c JOIN users u ON u.id=c.user_id "
                            "WHERE rcept_no=?", (rcept_no,)).fetchone()
            if row and row["user_id"] != user["id"]:
                raise HTTPException(409, f"이미 {row['display_name']} 기자가 맡았습니다.")
            c.execute("INSERT OR IGNORE INTO claims(rcept_no, user_id, claimed_at) VALUES(?,?,?)",
                      (rcept_no, user["id"], now_iso()))
        return {"ok": True}

    @app.delete("/api/claims/{rcept_no}")
    def unclaim(rcept_no: str, user: dict = Depends(current_user)):
        db.execute("DELETE FROM claims WHERE rcept_no=? AND user_id=?", (rcept_no, user["id"]))
        return {"ok": True}

    # --- 구독·푸시 -------------------------------------------------------
    @app.post("/api/subscriptions")
    def add_sub(body: SubIn, user: dict = Depends(current_user)):
        value = body.value.strip() if body.kind in ("company", "keyword") else ""
        if body.kind in ("company", "keyword") and not value:
            raise HTTPException(400, "기업명이나 키워드를 입력해 주세요.")
        db.execute("INSERT OR IGNORE INTO subscriptions(user_id, kind, value) VALUES(?,?,?)",
                   (user["id"], body.kind, value))
        return {"ok": True}

    @app.delete("/api/subscriptions")
    def del_sub(kind: str, value: str = "", user: dict = Depends(current_user)):
        db.execute("DELETE FROM subscriptions WHERE user_id=? AND kind=? AND value=?", (user["id"], kind, value))
        return {"ok": True}

    @app.get("/api/push/key")
    def push_key():
        return {"key": pusher.public_key}

    @app.post("/api/push/subscribe")
    def push_subscribe(body: PushIn, user: dict = Depends(current_user)):
        try:
            pusher.subscribe(user["id"], body.model_dump())
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        return {"ok": True}

    @app.post("/api/push/test")
    async def push_test(user: dict = Depends(current_user)):
        payload = {"title": "청년의사 브리핑", "body": "알림이 잘 도착했어요. 중요 공시는 이렇게 뜹니다.",
                   "url": settings.public_url + "/", "tag": "test"}
        sent = await asyncio.to_thread(pusher.send_to_user, user["id"], payload, True)
        return {"sent": sent}

    # --- 관리자 ---------------------------------------------------------
    @app.get("/api/admin/users")
    def admin_users(user: dict = Depends(admin_user)):
        return {"users": db.query("SELECT id, username, display_name, role, active, created_at FROM users ORDER BY id")}

    @app.post("/api/admin/invites")
    def admin_invite(body: InviteIn, user: dict = Depends(admin_user)):
        code = auth.create_invite(db, user["id"], body.role)
        return {"code": code, "url": f"{settings.public_url}/#join/{code}", "expires_in_days": auth.INVITE_DAYS}

    @app.post("/api/admin/users/{user_id}/active")
    def admin_set_active(user_id: int, active: int, user: dict = Depends(admin_user)):
        if user_id == user["id"]:
            raise HTTPException(400, "자기 자신은 비활성화할 수 없습니다.")
        db.execute("UPDATE users SET active=? WHERE id=?", (1 if active else 0, user_id))
        if not active:
            db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        return {"ok": True}

    @app.get("/api/admin/status")
    def admin_status(user: dict = Depends(admin_user)):
        return {
            "dart_status": db.get("dart_status", "대기 중"),
            "last_poll_at": db.get("last_poll_at"),
            "dart_calls_today": poller.client.calls_today(),
            "alert_mode": settings.alert_mode,
            "events": db.query("SELECT at, kind, detail FROM events ORDER BY id DESC LIMIT 50"),
        }

    @app.get("/healthz")
    def healthz():
        """외부 감시 서비스용. 마지막 수집이 너무 오래되면 503."""
        last = db.get("last_poll_at")
        if settings.dart_api_key and last:
            from datetime import datetime
            age = (now() - datetime.fromisoformat(last)).total_seconds()
            if age > settings.poll_interval_sec * 4:
                return JSONResponse({"ok": False, "last_poll_at": last}, status_code=503)
        return {"ok": True, "last_poll_at": last}

    # --- 정적 파일 -------------------------------------------------------
    @app.get("/sw.js")
    def sw():
        return FileResponse(STATIC / "sw.js", media_type="text/javascript",
                            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

    @app.get("/manifest.webmanifest")
    def manifest():
        return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
```

---

# [첨부] newsbot/__main__.py

```py
"""실행 진입점.

  python -m newsbot                 웹앱 + 수집기 실행
  python -m newsbot create-admin    첫 관리자 계정 만들기
  python -m newsbot invite          기자 초대 링크 만들기
  python -m newsbot poll            DART 한 번 수집해 보기 (알림 없음)
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
import sys

from . import auth
from .config import load_settings
from .db import Database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="newsbot", description="청년의사 브리핑")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="웹앱 실행 (기본)")
    ca = sub.add_parser("create-admin", help="관리자 계정 만들기")
    ca.add_argument("username")
    ca.add_argument("--name", default="관리자")
    inv = sub.add_parser("invite", help="초대 링크 만들기")
    inv.add_argument("--admin", action="store_true", help="관리자 권한으로 초대")
    sub.add_parser("poll", help="DART 한 번 수집")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    db = Database(settings.db_path)

    if args.cmd == "create-admin":
        pw = getpass.getpass("비밀번호(10자 이상): ")
        if problem := auth.validate_password(pw):
            print(problem)
            return 1
        if pw != getpass.getpass("비밀번호 확인: "):
            print("비밀번호가 다릅니다.")
            return 1
        auth.create_user(db, args.username, args.name, pw, role="admin")
        db.execute("INSERT OR IGNORE INTO subscriptions(user_id, kind, value) "
                   "SELECT id, 'watch', '' FROM users WHERE username=?", (args.username.lower(),))
        print(f"관리자 '{args.username}' 계정을 만들었습니다. {settings.public_url} 에서 로그인하세요.")
        return 0

    if args.cmd == "invite":
        code = auth.create_invite(db, None, "admin" if args.admin else "reporter")
        print(f"초대 링크 ({auth.INVITE_DAYS}일 유효, 1회용):\n{settings.public_url}/#join/{code}")
        return 0

    if args.cmd == "poll":
        from .app import Poller
        from .push import Pusher
        from .rules import Rules

        if not settings.dart_api_key:
            print(".env 에 DART_API_KEY 가 없습니다.")
            return 1
        pusher = Pusher(db, settings.data_dir, settings.vapid_contact, enabled=False)
        poller = Poller(settings, db, Rules.load(settings.rules_path), pusher)
        asyncio.run(poller.run_once())
        print("상태:", db.get("dart_status"), "/ 오늘 호출:", poller.client.calls_today())
        return 0

    import uvicorn

    from .app import create_app

    app = create_app(settings, db)
    print(f"청년의사 브리핑: {settings.public_url}  (알림 모드: {settings.alert_mode})")
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

# [첨부] newsbot/static/index.html

```html
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#0b4a8b">
  <title>청년의사 브리핑</title>
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" href="/static/icon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/static/icon-192.png">
  <link rel="stylesheet" href="/static/app.css">
  <script src="/static/app.js" defer></script>
</head>
<body>
  <a class="skip" href="#main">본문으로 건너뛰기</a>

  <!-- 로그인 / 가입 -->
  <section id="auth" class="auth" hidden>
    <div class="auth-card">
      <div class="brand"><span class="brand-mark" aria-hidden="true">청</span><span>청년의사 브리핑</span></div>
      <form id="login-form" class="stack">
        <h1>로그인</h1>
        <label>아이디<input name="username" autocomplete="username" required></label>
        <label>비밀번호<input name="password" type="password" autocomplete="current-password" required></label>
        <button class="btn primary" type="submit">로그인</button>
        <p class="muted small">계정은 관리자에게 받은 초대 링크로 만듭니다.</p>
      </form>
      <form id="join-form" class="stack" hidden>
        <h1>초대받은 계정 만들기</h1>
        <label>이름 (화면에 표시)<input name="display_name" required maxlength="40" placeholder="홍길동"></label>
        <label>아이디 (영문·숫자)<input name="username" required pattern="[A-Za-z0-9._-]{2,32}" autocomplete="username"></label>
        <label>비밀번호 (10자 이상)<input name="password" type="password" minlength="10" required autocomplete="new-password"></label>
        <button class="btn primary" type="submit">계정 만들기</button>
      </form>
      <p id="auth-error" class="error" role="alert"></p>
    </div>
  </section>

  <!-- 앱 -->
  <div id="app" class="shell" hidden>
    <aside class="sidebar" aria-label="메뉴">
      <div class="brand"><span class="brand-mark" aria-hidden="true">청</span><span>브리핑</span></div>
      <nav class="nav">
        <a href="#feed" data-view="feed" class="nav-item"><span aria-hidden="true">◎</span>피드</a>
        <a href="#mine" data-view="mine" class="nav-item"><span aria-hidden="true">✓</span>내가 맡은 건</a>
        <a href="#settings" data-view="settings" class="nav-item"><span aria-hidden="true">⚙</span>내 설정</a>
        <a href="#admin" data-view="admin" class="nav-item admin-only" hidden><span aria-hidden="true">⌂</span>관리자</a>
      </nav>
      <div class="sidebar-foot">
        <div id="status-dot" class="status" title="수집 상태"><span class="dot"></span><span class="status-text">확인 중</span></div>
        <button id="theme-btn" class="btn ghost small" type="button" aria-label="화면 테마 바꾸기">테마</button>
        <button id="logout-btn" class="btn ghost small" type="button">로그아웃</button>
      </div>
    </aside>

    <header class="topbar">
      <div class="search">
        <input id="search" type="search" placeholder="기업명·공시 제목 검색  ( / )" aria-label="공시 검색">
      </div>
      <div class="filters" role="group" aria-label="등급 필터">
        <button class="chip" data-level="" aria-pressed="true">전체</button>
        <button class="chip" data-level="red" aria-pressed="false"><span class="lv lv-red" aria-hidden="true">●</span>중요</button>
        <button class="chip" data-level="yellow" aria-pressed="false"><span class="lv lv-yellow" aria-hidden="true">●</span>일반</button>
        <button class="chip" data-watched="1" aria-pressed="false">★ 감시 기업</button>
      </div>
      <button id="push-btn" class="btn primary small" type="button" hidden>PC·폰 알림 켜기</button>
    </header>

    <main id="main" class="main" tabindex="-1">
      <!-- 피드 -->
      <section id="view-feed" class="view">
        <div id="mode-banner" class="banner" hidden></div>
        <div class="bento" id="briefing" aria-live="polite"></div>
        <div class="feed-head">
          <h2 id="feed-title">오늘의 피드</h2>
          <span class="muted small kbd-hint">J/K 이동 · Enter 열기 · C 담당 · / 검색</span>
        </div>
        <ul id="feed" class="feed" role="listbox" aria-label="공시 목록"></ul>
        <button id="more-btn" class="btn ghost" type="button" hidden>더 보기</button>
        <p id="empty" class="empty" hidden></p>
      </section>

      <!-- 설정 -->
      <section id="view-settings" class="view" hidden>
        <h2>내 설정</h2>
        <div class="card stack">
          <h3>알림 받을 공시</h3>
          <p class="muted small">중요(빨강) 공시 가운데 아래에 해당하는 것만 팝업으로 받습니다. 일반 공시는 피드에만 쌓입니다.</p>
          <div id="subs" class="tags"></div>
          <form id="sub-form" class="row">
            <select name="kind" aria-label="종류">
              <option value="company">기업</option>
              <option value="keyword">키워드</option>
              <option value="watch">감시 기업 전체</option>
              <option value="all">보건의료 전체</option>
            </select>
            <input name="value" placeholder="예: 유한양행, 기술이전" aria-label="기업명 또는 키워드">
            <button class="btn" type="submit">추가</button>
          </form>
        </div>
        <div class="card stack">
          <h3>이 기기 알림</h3>
          <p id="push-state" class="muted small"></p>
          <div class="row">
            <button id="push-enable" class="btn primary" type="button">이 기기에서 알림 받기</button>
            <button id="push-test" class="btn" type="button">테스트 알림 보내기</button>
          </div>
          <p class="muted small">아이폰은 Safari 공유 버튼 → '홈 화면에 추가'로 설치한 뒤 그 앱에서 알림을 켜야 합니다.</p>
        </div>
        <div class="card stack">
          <h3>화면</h3>
          <label class="row">글자 크기
            <input id="font-size" type="range" min="14" max="20" step="1" aria-label="글자 크기">
          </label>
        </div>
      </section>

      <!-- 관리자 -->
      <section id="view-admin" class="view" hidden>
        <h2>관리자</h2>
        <div class="card stack">
          <h3>수집 상태</h3>
          <dl id="admin-status" class="kv"></dl>
        </div>
        <div class="card stack">
          <h3>기자 초대</h3>
          <div class="row">
            <button id="invite-btn" class="btn primary" type="button">초대 링크 만들기</button>
            <input id="invite-url" readonly aria-label="초대 링크" placeholder="버튼을 누르면 링크가 생깁니다">
          </div>
          <p class="muted small">링크는 7일간 1번만 쓸 수 있습니다. 메신저나 메일로 직접 전달하세요.</p>
        </div>
        <div class="card stack">
          <h3>사용자</h3>
          <table class="table"><thead><tr><th>이름</th><th>아이디</th><th>권한</th><th>상태</th><th></th></tr></thead>
            <tbody id="users"></tbody></table>
        </div>
        <div class="card stack">
          <h3>최근 기록</h3>
          <ol id="events" class="events"></ol>
        </div>
      </section>
    </main>

    <!-- 상세 -->
    <aside id="detail" class="detail" aria-label="공시 상세" hidden>
      <div class="detail-inner"></div>
    </aside>

    <!-- 질문창 (3~4주차에 연결) -->
    <form id="ask" class="ask" autocomplete="off">
      <input id="ask-input" placeholder="질문하기 (Ctrl+K) · 예: 오늘 기술이전 공시 있어?" aria-label="질문">
      <button class="btn primary" type="submit">묻기</button>
    </form>

    <nav class="tabbar" aria-label="하단 메뉴">
      <a href="#feed" data-view="feed">피드</a>
      <a href="#mine" data-view="mine">담당</a>
      <a href="#settings" data-view="settings">설정</a>
      <a href="#admin" data-view="admin" class="admin-only" hidden>관리</a>
    </nav>
  </div>

  <div id="toast" class="toast" role="status" aria-live="polite"></div>
</body>
</html>
```

---

# [첨부] newsbot/static/app.js

```js
// 청년의사 브리핑 — 화면 스크립트 (프레임워크 없음, 모든 글자는 textContent로 넣어 XSS 방지)
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const LEVEL = {
  red: { label: "중요", cls: "red", icon: "▲" },
  yellow: { label: "일반", cls: "yellow", icon: "●" },
  gray: { label: "기록", cls: "gray", icon: "○" },
};

const state = {
  me: null,
  view: "feed",
  filter: { level: "", watched: 0, q: "" },
  items: [],
  selected: -1,
  detail: null,
  seen: new Set(),
};

// ---------- 공통 ----------
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "style") node.style.cssText = v; // CSP: style 속성 대신 CSSOM 사용
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null) node.append(c instanceof Node ? c : document.createTextNode(c));
  return node;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401 && !path.startsWith("/api/login")) {
    showAuth();
    throw new Error("로그인이 필요합니다.");
  }
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : null;
  if (!res.ok) throw new Error((data && data.detail && (typeof data.detail === "string" ? data.detail : "입력값을 확인해 주세요.")) || `오류 ${res.status}`);
  return data;
}

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2800);
}

function fmtSeen(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const today = new Date();
  const hm = d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
  return d.toDateString() === today.toDateString() ? hm : `${d.getMonth() + 1}/${d.getDate()} ${hm}`;
}
const fmtDate = (s) => (s && s.length === 8 ? `${s.slice(0, 4)}.${s.slice(4, 6)}.${s.slice(6)}` : s || "");

function badge(item) {
  const lv = LEVEL[item.level] || LEVEL.yellow;
  const wrap = el("span", { class: "row", style: "gap:.25rem" });
  wrap.append(el("span", { class: `badge ${lv.cls}` }, el("span", { "aria-hidden": "true", text: lv.icon }), lv.label));
  if (item.is_correction) wrap.append(el("span", { class: "badge fix", text: "정정" }));
  return wrap;
}

// ---------- 인증 ----------
function showAuth(joinCode) {
  $("#app").hidden = true;
  $("#auth").hidden = false;
  $("#login-form").hidden = !!joinCode;
  $("#join-form").hidden = !joinCode;
  $("#join-form").dataset.code = joinCode || "";
  (joinCode ? $("#join-form input") : $("#login-form input")).focus();
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/login", { method: "POST", body: { username: f.get("username"), password: f.get("password") } });
    $("#auth-error").textContent = "";
    await boot();
  } catch (err) {
    $("#auth-error").textContent = err.message;
  }
});

$("#join-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/register", {
      method: "POST",
      body: { code: e.target.dataset.code, username: f.get("username"), display_name: f.get("display_name"), password: f.get("password") },
    });
    location.hash = "#settings";
    await boot();
    toast("계정을 만들었어요. 이 기기에서 알림을 켜 주세요.");
  } catch (err) {
    $("#auth-error").textContent = err.message;
  }
});

$("#logout-btn").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.hash = "";
  showAuth();
});

// ---------- 화면 전환 ----------
function setView(view) {
  if (view === "admin" && state.me?.role !== "admin") view = "feed";
  state.view = view;
  const section = view === "mine" ? "feed" : view;
  $$(".view").forEach((v) => (v.hidden = v.id !== `view-${section}`));
  $$("[data-view]").forEach((a) => a.setAttribute("aria-current", a.dataset.view === view ? "page" : "false"));
  $(".topbar").hidden = section !== "feed";
  $("#ask").hidden = section !== "feed";
  if (section === "feed") {
    $("#feed-title").textContent = view === "mine" ? "내가 맡은 건" : "오늘의 피드";
    $("#briefing").hidden = view === "mine";
    loadFeed(true);
  }
  if (view === "settings") renderSettings();
  if (view === "admin") renderAdmin();
}

function route() {
  const h = location.hash.slice(1);
  if (h.startsWith("join/")) return showAuth(h.slice(5));
  if (!state.me) return;
  if (h.startsWith("d/")) {
    if (state.view !== "feed") setView("feed");
    return openDetail(h.slice(2));
  }
  setView(["feed", "mine", "settings", "admin"].includes(h) ? h : "feed");
}
window.addEventListener("hashchange", route);

// ---------- 오늘의 브리핑 ----------
async function loadSummary() {
  const s = await api("/api/summary");
  const box = $("#briefing");
  box.replaceChildren(
    el("div", { class: "tile alert" }, el("div", { class: "label", text: "오늘 중요 공시" }), el("div", { class: "num", text: s.red })),
    el("div", { class: "tile" }, el("div", { class: "label", text: "오늘 일반 공시" }), el("div", { class: "num", text: s.yellow })),
    el("div", { class: "tile" }, el("div", { class: "label", text: "담당 미정 (중요)" }), el("div", { class: "num", text: s.unclaimed_top })),
    el("div", { class: "tile" }, el("div", { class: "label", text: "내가 맡은 건" }), el("div", { class: "num", text: s.my_claims })),
    el("div", { class: "tile wide" },
      el("div", { class: "label", text: "지금 확인할 것" }),
      s.top.length
        ? el("ul", { class: "top-list" }, s.top.map((t) =>
            el("li", {}, el("button", { type: "button", onclick: () => (location.hash = `#d/${t.rcept_no}`) },
              badge(t), el("strong", { text: t.corp_name }), el("span", { class: "muted t", text: t.report_nm }),
              t.claimed_name ? el("span", { class: "claimed small", text: `✓ ${t.claimed_name}` }) : null))))
        : el("p", { class: "muted small", text: "오늘은 아직 중요 공시가 없어요." })),
  );
  const banner = $("#mode-banner");
  banner.hidden = s.alert_mode !== "log";
  banner.textContent = "지금은 '기록만' 모드예요. 팝업 없이 수집하면서 알림량을 재고 있어요.";
  const st = $("#status-dot");
  st.classList.toggle("ok", s.dart_status === "정상");
  st.classList.toggle("bad", s.dart_status !== "정상" && s.dart_status !== "대기 중");
  $(".status-text", st).textContent = s.dart_status === "정상" ? `수집 정상 · ${fmtSeen(s.last_poll_at)}` : s.dart_status;
  st.title = s.dart_status;
}

// ---------- 피드 ----------
function feedQuery(before = "") {
  const p = new URLSearchParams();
  if (state.filter.level) p.set("level", state.filter.level);
  if (state.filter.watched) p.set("watched", "1");
  if (state.filter.q) p.set("q", state.filter.q);
  if (state.view === "mine") p.set("mine", "1");
  if (before) p.set("before", before);
  return `/api/feed?${p}`;
}

async function loadFeed(reset) {
  const before = reset ? "" : state.items.at(-1)?.first_seen_at || "";
  const { items } = await api(feedQuery(before));
  if (reset) {
    state.items = items;
    state.selected = -1;
  } else state.items.push(...items);
  items.forEach((i) => state.seen.add(i.rcept_no));
  renderFeed();
  $("#more-btn").hidden = items.length < 50;
  if (state.view === "feed") loadSummary().catch(() => {});
}

function renderFeed(freshIds = new Set()) {
  const list = $("#feed");
  list.replaceChildren(...state.items.map((it, idx) =>
    el("li", {
      class: `item${freshIds.has(it.rcept_no) ? " new" : ""}`, role: "option", id: `it-${idx}`,
      "aria-selected": idx === state.selected ? "true" : "false", onclick: () => select(idx, true),
    },
      badge(it),
      el("div", { style: "min-width:0" },
        el("div", { class: "row", style: "gap:.4rem" },
          it.watched ? el("span", { class: "star", title: "감시 기업", text: "★" }) : null,
          el("span", { class: "who", text: it.corp_name })),
        el("div", { class: "title", text: it.report_nm, title: it.report_nm })),
      el("div", { class: "meta" },
        it.claimed_name ? el("span", { class: "claimed", text: `✓ ${it.claimed_name}` }) : null,
        el("time", { datetime: it.first_seen_at, text: fmtSeen(it.first_seen_at) })))));
  const empty = $("#empty");
  empty.hidden = state.items.length > 0;
  empty.textContent = state.view === "mine" ? "맡은 공시가 없어요. 피드에서 C 키나 [내가 쓸게요]로 맡을 수 있어요." : "조건에 맞는 공시가 없어요.";
}

function select(idx, open) {
  if (idx < 0 || idx >= state.items.length) return;
  state.selected = idx;
  $$(".item").forEach((n, i) => n.setAttribute("aria-selected", i === idx ? "true" : "false"));
  $(`#it-${idx}`)?.scrollIntoView({ block: "nearest" });
  if (open) location.hash = `#d/${state.items[idx].rcept_no}`;
}

$("#more-btn").addEventListener("click", () => loadFeed(false));

$$(".filters .chip").forEach((chip) => chip.addEventListener("click", () => {
  if (chip.dataset.watched !== undefined) {
    state.filter.watched = state.filter.watched ? 0 : 1;
    chip.setAttribute("aria-pressed", state.filter.watched ? "true" : "false");
  } else {
    state.filter.level = chip.dataset.level;
    $$(".filters .chip[data-level]").forEach((c) => c.setAttribute("aria-pressed", c === chip ? "true" : "false"));
  }
  loadFeed(true);
}));

let searchTimer;
$("#search").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.filter.q = e.target.value.trim(); loadFeed(true); }, 250);
});

// ---------- 상세 ----------
async function openDetail(rceptNo) {
  let d;
  try { d = await api(`/api/disclosures/${encodeURIComponent(rceptNo)}`); }
  catch (err) { toast(err.message); return; }
  state.detail = d;
  const idx = state.items.findIndex((i) => i.rcept_no === rceptNo);
  if (idx >= 0) select(idx, false);
  const mine = d.claimed_by === state.me.id;
  const claimBtn = d.claimed_by && !mine
    ? el("button", { class: "btn", type: "button", disabled: true, text: `${d.claimed_name} 기자가 맡음` })
    : el("button", { class: mine ? "btn" : "btn primary", type: "button", onclick: toggleClaim, text: mine ? "맡기 취소" : "내가 쓸게요 (C)" });
  $("#detail .detail-inner").replaceChildren(
    el("div", { class: "row", style: "justify-content:space-between" }, badge(d),
      el("button", { class: "btn ghost small", type: "button", onclick: closeDetail, "aria-label": "닫기", text: "닫기 (Esc)" })),
    el("div", {}, el("div", { class: "muted small", text: d.watched ? "★ 감시 기업" : "보건의료 업종" }), el("h2", { text: d.corp_name })),
    el("p", { style: "margin:0;font-weight:600", text: d.report_nm }),
    el("a", { class: "source", href: d.url, target: "_blank", rel: "noopener noreferrer" }, "DART 원문 열기", el("span", { "aria-hidden": "true", text: "↗" })),
    el("dl", { class: "kv" },
      el("dt", { text: "접수일" }), el("dd", { text: fmtDate(d.rcept_dt) }),
      el("dt", { text: "접수번호" }), el("dd", { text: d.rcept_no }),
      el("dt", { text: "제출인" }), el("dd", { text: d.flr_nm || "-" }),
      el("dt", { text: "비고" }), el("dd", { text: d.rm || "-" }),
      el("dt", { text: "분류 근거" }), el("dd", { text: d.keyword ? `제목에 '${d.keyword}' 포함` : "키워드 없음 (일반)" }),
      el("dt", { text: "처음 확인" }), el("dd", { text: fmtSeen(d.first_seen_at) + " · DART 공개는 제출 후 약 15분 뒤" })),
    el("div", { class: "row" }, claimBtn,
      el("button", { class: "btn", type: "button", disabled: true, title: "AI API 키 연결 후 5~6주차에 켜집니다", text: "기사 초안 (준비 중)" })),
  );
  $("#detail").hidden = false;
  $("#app").classList.add("has-detail");
}

function closeDetail() {
  $("#detail").hidden = true;
  $("#app").classList.remove("has-detail");
  state.detail = null;
  if (location.hash.startsWith("#d/")) history.replaceState(null, "", state.view === "mine" ? "#mine" : "#feed");
}

async function toggleClaim() {
  const d = state.detail || state.items[state.selected];
  if (!d) return;
  const mine = d.claimed_by === state.me.id;
  try {
    await api(`/api/claims/${encodeURIComponent(d.rcept_no)}`, { method: mine ? "DELETE" : "POST" });
    toast(mine ? "맡기를 취소했어요." : "이 공시를 맡았어요.");
    await loadFeed(true);
    if (state.detail) openDetail(d.rcept_no);
  } catch (err) { toast(err.message); }
}

// ---------- 키보드 ----------
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); $("#ask-input").focus(); return; }
  const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
  if (e.key === "Escape") { if (typing) document.activeElement.blur(); else closeDetail(); return; }
  if (typing || state.view === "settings" || state.view === "admin") return;
  if (e.key === "/") { e.preventDefault(); $("#search").focus(); }
  else if (e.key === "j") select(Math.min(state.selected + 1, state.items.length - 1), false);
  else if (e.key === "k") select(Math.max(state.selected - 1, 0), false);
  else if (e.key === "Enter" && state.selected >= 0) select(state.selected, true);
  else if (e.key === "c" && (state.detail || state.selected >= 0)) toggleClaim();
});

// ---------- 질문창 ----------
$("#ask").addEventListener("submit", (e) => {
  e.preventDefault();
  toast("질문 기능은 AI API 키를 연결한 뒤 켜집니다 (3~4주차).");
});

// ---------- 설정 ----------
async function renderSettings() {
  const me = (state.me = await api("/api/me"));
  const kindName = { all: "보건의료 전체", watch: "감시 기업 전체", company: "기업", keyword: "키워드" };
  $("#subs").replaceChildren(...(me.subscriptions.length ? me.subscriptions.map((s) =>
    el("span", { class: "tag" }, `${kindName[s.kind]}${s.value ? ": " + s.value : ""}`,
      el("button", { type: "button", "aria-label": "삭제", text: "×", onclick: async () => {
        await api(`/api/subscriptions?kind=${s.kind}&value=${encodeURIComponent(s.value)}`, { method: "DELETE" });
        renderSettings();
      } }))) : [el("span", { class: "muted small", text: "아직 없어요. 아래에서 추가하세요." })]));
  $("#push-state").textContent = `알림 받는 기기 ${me.push_devices}대 · 서버 알림 모드: ${me.alert_mode === "notify" ? "알림 보냄" : "기록만 (관리자가 켜면 알림 시작)"}`;
  $("#font-size").value = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--fs")) || 15;
}

$("#sub-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/subscriptions", { method: "POST", body: { kind: f.get("kind"), value: f.get("value") || "" } });
    e.target.reset();
    renderSettings();
  } catch (err) { toast(err.message); }
});
$("#sub-form select").addEventListener("change", (e) => {
  $("#sub-form input").hidden = ["all", "watch"].includes(e.target.value);
});

$("#font-size").addEventListener("input", (e) => {
  document.documentElement.style.setProperty("--fs", `${e.target.value}px`);
  try { localStorage.setItem("nb-fs", e.target.value); } catch {}
});

// ---------- 푸시 알림 ----------
function b64ToBytes(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    toast("이 브라우저는 알림을 지원하지 않아요. 아이폰은 홈 화면에 추가한 앱에서 켜 주세요.");
    return;
  }
  const perm = await Notification.requestPermission();
  if (perm !== "granted") { toast("알림 권한이 거부됐어요. 브라우저 설정에서 허용해 주세요."); return; }
  const reg = await navigator.serviceWorker.register("/sw.js");
  const { key } = await api("/api/push/key");
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(key) });
  await api("/api/push/subscribe", { method: "POST", body: sub.toJSON() });
  $("#push-btn").hidden = true;
  toast("이 기기에서 알림을 받아요.");
  if (state.view === "settings") renderSettings();
}
$("#push-btn").addEventListener("click", () => enablePush().catch((e) => toast(e.message)));
$("#push-enable").addEventListener("click", () => enablePush().catch((e) => toast(e.message)));
$("#push-test").addEventListener("click", async () => {
  try {
    const { sent } = await api("/api/push/test", { method: "POST" });
    toast(sent ? `테스트 알림을 ${sent}대에 보냈어요.` : "알림 받는 기기가 없어요. 먼저 알림을 켜 주세요.");
  } catch (err) { toast(err.message); }
});

async function checkPushButton() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) return;
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = reg && (await reg.pushManager.getSubscription());
  $("#push-btn").hidden = !!sub && Notification.permission === "granted";
}

// ---------- 관리자 ----------
async function renderAdmin() {
  const [st, us] = await Promise.all([api("/api/admin/status"), api("/api/admin/users")]);
  $("#admin-status").replaceChildren(
    el("dt", { text: "수집 상태" }), el("dd", { text: st.dart_status }),
    el("dt", { text: "마지막 수집" }), el("dd", { text: st.last_poll_at ? fmtSeen(st.last_poll_at) : "-" }),
    el("dt", { text: "오늘 DART 호출" }), el("dd", { text: `${st.dart_calls_today}건` }),
    el("dt", { text: "알림 모드" }), el("dd", { text: st.alert_mode === "notify" ? "알림 보냄" : "기록만 (.env 의 ALERT_MODE=notify 로 변경)" }));
  $("#users").replaceChildren(...us.users.map((u) => el("tr", {},
    el("td", { text: u.display_name }), el("td", { text: u.username }), el("td", { text: u.role === "admin" ? "관리자" : "기자" }),
    el("td", { text: u.active ? "사용 중" : "비활성" }),
    el("td", {}, u.id === state.me.id ? null : el("button", { class: "btn small", type: "button", text: u.active ? "비활성화" : "다시 사용",
      onclick: async () => { await api(`/api/admin/users/${u.id}/active?active=${u.active ? 0 : 1}`, { method: "POST" }); renderAdmin(); } })))));
  $("#events").replaceChildren(...st.events.map((ev) => el("li", { text: `${fmtSeen(ev.at)} [${ev.kind}] ${ev.detail || ""}` })));
}
$("#invite-btn").addEventListener("click", async () => {
  const r = await api("/api/admin/invites", { method: "POST", body: { role: "reporter" } });
  $("#invite-url").value = r.url;
  $("#invite-url").select();
  try { await navigator.clipboard.writeText(r.url); toast("초대 링크를 복사했어요."); } catch { toast("초대 링크를 만들었어요."); }
});

// ---------- 테마 ----------
function applyTheme(t) {
  if (t === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", t);
  $("#theme-btn").textContent = { auto: "테마: 자동", light: "테마: 밝게", dark: "테마: 어둡게" }[t];
}
$("#theme-btn").addEventListener("click", () => {
  const order = ["auto", "light", "dark"];
  let cur = "auto";
  try { cur = localStorage.getItem("nb-theme") || "auto"; } catch {}
  const next = order[(order.indexOf(cur) + 1) % order.length];
  try { localStorage.setItem("nb-theme", next); } catch {}
  applyTheme(next);
});

// ---------- 실시간 갱신 (1분마다) ----------
async function refresh() {
  if (!state.me || state.view !== "feed" || document.hidden) return;
  try {
    const { items } = await api(feedQuery());
    const fresh = items.filter((i) => !state.seen.has(i.rcept_no));
    if (!fresh.length) return loadSummary();
    fresh.forEach((i) => state.seen.add(i.rcept_no));
    const keep = state.items.filter((i) => !fresh.some((f) => f.rcept_no === i.rcept_no));
    state.items = [...fresh, ...keep];
    if (state.selected >= 0) state.selected += fresh.length;
    renderFeed(new Set(fresh.map((f) => f.rcept_no)));
    toast(`새 공시 ${fresh.length}건`);
    loadSummary();
  } catch {}
}
setInterval(refresh, 60_000);
document.addEventListener("visibilitychange", refresh);

// ---------- 시작 ----------
async function boot() {
  try {
    state.me = await api("/api/me");
  } catch {
    return;
  }
  $("#auth").hidden = true;
  $("#app").hidden = false;
  $$(".admin-only").forEach((n) => (n.hidden = state.me.role !== "admin"));
  checkPushButton().catch(() => {});
  route();
}

(function init() {
  try {
    const fs = localStorage.getItem("nb-fs");
    if (fs) document.documentElement.style.setProperty("--fs", `${fs}px`);
    applyTheme(localStorage.getItem("nb-theme") || "auto");
  } catch { applyTheme("auto"); }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  if (location.hash.startsWith("#join/")) showAuth(location.hash.slice(6));
  else boot();
})();
```

---

# [첨부] newsbot/static/sw.js

```js
// 서비스 워커: 웹 푸시를 받아 PC 오른쪽 아래 팝업(Windows 알림)·휴대폰 알림으로 띄운다.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch { data = { body: event.data && event.data.text() }; }
  const title = data.title || "청년의사 브리핑";
  event.waitUntil(self.registration.showNotification(title, {
    body: data.body || "",
    tag: data.tag || undefined,
    renotify: !!data.tag,
    icon: "/static/icon-192.png",
    badge: "/static/icon-192.png",
    data: { url: data.url || "/" },
    requireInteraction: false,
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) {
      if (new URL(c.url).origin === self.location.origin) {
        await c.focus();
        c.navigate(url);
        return;
      }
    }
    await self.clients.openWindow(url);
  })());
});
```

---

# [첨부] newsbot/static/app.css

```css
/* 청년의사 브리핑 — 2026 원칙: 요약 먼저, 출처는 한눈에, 알림은 절제, 밀도는 높게, 장식은 적게 */
:root {
  --brand: #0b4a8b;
  --brand-ink: #ffffff;
  --bg: #f6f7f9;
  --surface: #ffffff;
  --surface-2: #eef1f5;
  --line: #dde2ea;
  --text: #121822;
  --text-2: #4d5866;
  --red: #c62828;
  --red-bg: #fdecec;
  --yellow: #8a6100;
  --yellow-bg: #fff4d6;
  --gray: #6b7480;
  --ok: #1d7a46;
  --focus: #2f6fe0;
  --radius: 12px;
  --fs: 15px;
  --shadow: 0 1px 2px rgba(16, 24, 40, .06), 0 4px 16px rgba(16, 24, 40, .06);
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --brand: #6ea8ff; --brand-ink: #0b1220;
    --bg: #0d1117; --surface: #151b23; --surface-2: #1c2430; --line: #2a3442;
    --text: #e8edf3; --text-2: #a3aebb;
    --red: #ff7b72; --red-bg: #3a1618; --yellow: #f2c14e; --yellow-bg: #33290f; --gray: #8b96a3; --ok: #56d364;
    --focus: #79b8ff; --shadow: none; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --brand: #6ea8ff; --brand-ink: #0b1220;
  --bg: #0d1117; --surface: #151b23; --surface-2: #1c2430; --line: #2a3442;
  --text: #e8edf3; --text-2: #a3aebb;
  --red: #ff7b72; --red-bg: #3a1618; --yellow: #f2c14e; --yellow-bg: #33290f; --gray: #8b96a3; --ok: #56d364;
  --focus: #79b8ff; --shadow: none; color-scheme: dark;
}

* { box-sizing: border-box; }
html { font-size: var(--fs); }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif;
  line-height: 1.5; -webkit-font-smoothing: antialiased; word-break: keep-all;
}
a { color: var(--brand); }
h1, h2, h3 { margin: 0; line-height: 1.3; }
h2 { font-size: 1.25rem; }
h3 { font-size: 1rem; }
button, input, select { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; border-radius: 6px; }
[hidden] { display: none !important; }
.muted { color: var(--text-2); }
.small { font-size: .867rem; }
.error { color: var(--red); min-height: 1.5em; margin: .5rem 0 0; }
.skip { position: absolute; left: -999px; top: 8px; background: var(--surface); padding: 8px 12px; z-index: 99; }
.skip:focus { left: 8px; }
.stack { display: flex; flex-direction: column; gap: .75rem; }
.row { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }

/* 버튼·입력 */
.btn {
  border: 1px solid var(--line); background: var(--surface); padding: .5rem .9rem; border-radius: 10px;
  cursor: pointer; font-weight: 600; white-space: nowrap;
}
.btn:hover { background: var(--surface-2); }
.btn.primary { background: var(--brand); color: var(--brand-ink); border-color: transparent; }
.btn.primary:hover { filter: brightness(1.08); }
.btn.ghost { background: transparent; border-color: transparent; color: var(--text-2); }
.btn.small { padding: .35rem .7rem; font-size: .867rem; }
input, select {
  border: 1px solid var(--line); background: var(--surface); border-radius: 10px; padding: .55rem .75rem; min-width: 0;
}
label { display: flex; flex-direction: column; gap: .3rem; font-weight: 600; font-size: .933rem; }
label.row { flex-direction: row; }

/* 로그인 */
.auth { min-height: 100vh; display: grid; place-items: center; padding: 16px; }
.auth-card { width: min(400px, 100%); background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 28px; box-shadow: var(--shadow); }
.auth-card h1 { font-size: 1.25rem; margin-top: 1rem; }
.brand { display: flex; align-items: center; gap: .55rem; font-weight: 800; letter-spacing: -.01em; }
.brand-mark {
  display: inline-grid; place-items: center; width: 30px; height: 30px; border-radius: 8px;
  background: #0b4a8b; color: #fff; font-weight: 800;
}

/* 앱 레이아웃: 고정 메뉴 | 본문 | 상세 */
.shell {
  display: grid; grid-template-columns: 216px minmax(0, 1fr); grid-template-rows: auto 1fr;
  grid-template-areas: "side top" "side main"; min-height: 100vh;
}
.shell.has-detail { grid-template-columns: 216px minmax(0, 1fr) 400px; grid-template-areas: "side top detail" "side main detail"; }
.sidebar {
  grid-area: side; position: sticky; top: 0; height: 100vh; display: flex; flex-direction: column; gap: 1.25rem;
  padding: 18px 14px; border-right: 1px solid var(--line); background: var(--surface);
}
.nav { display: flex; flex-direction: column; gap: 2px; }
.nav-item { display: flex; gap: .6rem; align-items: center; padding: .55rem .7rem; border-radius: 10px; color: var(--text); text-decoration: none; font-weight: 600; }
.nav-item span { width: 1.1em; text-align: center; color: var(--text-2); }
.nav-item:hover { background: var(--surface-2); }
.nav-item[aria-current="page"] { background: var(--surface-2); color: var(--brand); }
.sidebar-foot { margin-top: auto; display: flex; flex-direction: column; gap: .4rem; align-items: flex-start; }
.status { display: flex; align-items: center; gap: .45rem; font-size: .8rem; color: var(--text-2); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--gray); }
.status.ok .dot { background: var(--ok); }
.status.bad .dot { background: var(--red); }

/* 상단바: 반투명은 여기만 (절제된 Liquid Glass) */
.topbar {
  grid-area: top; position: sticky; top: 0; z-index: 5; display: flex; gap: .75rem; align-items: center; flex-wrap: wrap;
  padding: 12px 20px; background: color-mix(in srgb, var(--bg) 78%, transparent);
  backdrop-filter: saturate(1.4) blur(14px); -webkit-backdrop-filter: saturate(1.4) blur(14px);
  border-bottom: 1px solid var(--line);
}
.search { flex: 1 1 260px; }
.search input { width: 100%; }
.filters { display: flex; gap: .35rem; flex-wrap: wrap; }
.chip {
  border: 1px solid var(--line); background: var(--surface); border-radius: 999px; padding: .3rem .75rem;
  cursor: pointer; font-size: .867rem; font-weight: 600; display: inline-flex; gap: .35rem; align-items: center;
}
.chip[aria-pressed="true"] { background: var(--text); color: var(--bg); border-color: var(--text); }
.lv-red { color: var(--red); } .lv-yellow { color: var(--yellow); }

.main { grid-area: main; padding: 20px 20px 120px; outline: none; min-width: 0; }
.view { display: flex; flex-direction: column; gap: 16px; max-width: 1100px; }
.banner { background: var(--surface-2); border: 1px dashed var(--line); padding: .6rem .9rem; border-radius: 10px; font-size: .9rem; color: var(--text-2); }

/* 오늘의 브리핑: 벤토 그리드 */
.bento { display: grid; gap: 12px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.tile { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 14px 16px; box-shadow: var(--shadow); }
.tile .label { font-size: .8rem; color: var(--text-2); font-weight: 600; }
.tile .num { font-size: 1.9rem; font-weight: 800; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.tile.alert { border-color: color-mix(in srgb, var(--red) 40%, var(--line)); }
.tile.alert .num { color: var(--red); }
.tile.wide { grid-column: span 4; }
.top-list { list-style: none; margin: .5rem 0 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.top-list li button { all: unset; cursor: pointer; display: flex; gap: .6rem; align-items: baseline; padding: .35rem .25rem; border-radius: 8px; width: 100%; box-sizing: border-box; }
.top-list li button:hover { background: var(--surface-2); }
.top-list strong, .top-list .claimed, .top-list .badge { flex: 0 0 auto; }
.top-list .t { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.top-list li button:focus-visible { outline: 2px solid var(--focus); }

/* 피드 */
.feed-head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; }
.feed { list-style: none; margin: 0; padding: 0; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.item {
  display: grid; grid-template-columns: 64px minmax(0, 1fr) auto; gap: .25rem .75rem; align-items: center;
  padding: .7rem 1rem; border-bottom: 1px solid var(--line); cursor: pointer;
}
.item:last-child { border-bottom: 0; }
.item:hover { background: var(--surface-2); }
.item[aria-selected="true"] { background: color-mix(in srgb, var(--brand) 9%, var(--surface)); box-shadow: inset 3px 0 0 var(--brand); }
.item.new { animation: fresh 2.4s ease-out; }
@keyframes fresh { from { background: color-mix(in srgb, var(--brand) 18%, var(--surface)); } to { background: transparent; } }
.badge {
  display: inline-flex; align-items: center; justify-content: center; gap: .25rem; font-size: .75rem; font-weight: 700;
  border-radius: 6px; padding: .15rem .4rem; white-space: nowrap;
}
.badge.red { background: var(--red-bg); color: var(--red); }
.badge.yellow { background: var(--yellow-bg); color: var(--yellow); }
.badge.gray { background: var(--surface-2); color: var(--gray); }
.badge.fix { background: var(--surface-2); color: var(--text-2); }
.item .who { font-weight: 700; }
.item .title { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item .meta { display: flex; gap: .5rem; align-items: center; color: var(--text-2); font-size: .8rem; justify-self: end; font-variant-numeric: tabular-nums; }
.claimed { color: var(--ok); font-weight: 700; }
.star { color: #d39b00; }
.empty { text-align: center; color: var(--text-2); padding: 2rem; }
.kbd-hint { white-space: nowrap; }

/* 상세 */
.detail { grid-area: detail; position: sticky; top: 0; height: 100vh; overflow: auto; border-left: 1px solid var(--line); background: var(--surface); }
.detail-inner { padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.detail h2 { font-size: 1.15rem; }
.source {
  display: inline-flex; gap: .35rem; align-items: center; border: 1px solid var(--line); border-radius: 999px;
  padding: .2rem .6rem; font-size: .8rem; text-decoration: none; color: var(--text-2); width: fit-content;
}
.kv { display: grid; grid-template-columns: max-content 1fr; gap: .35rem 1rem; margin: 0; font-size: .9rem; }
.kv dt { color: var(--text-2); }
.kv dd { margin: 0; }

/* 카드·표 */
.card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px; }
.tags { display: flex; gap: .4rem; flex-wrap: wrap; }
.tag { display: inline-flex; gap: .4rem; align-items: center; background: var(--surface-2); border-radius: 999px; padding: .25rem .4rem .25rem .75rem; font-size: .867rem; }
.tag button { border: 0; background: transparent; cursor: pointer; color: var(--text-2); font-size: 1rem; line-height: 1; padding: 0 .3rem; }
.table { width: 100%; border-collapse: collapse; font-size: .9rem; }
.table th, .table td { text-align: left; padding: .5rem; border-bottom: 1px solid var(--line); }
.events { margin: 0; padding-left: 1.2rem; font-size: .82rem; color: var(--text-2); max-height: 320px; overflow: auto; font-variant-numeric: tabular-nums; }
#invite-url { flex: 1 1 280px; }

/* 질문창: 하단 고정 */
.ask {
  position: fixed; left: calc(216px + 20px); right: 20px; bottom: 16px; z-index: 6; display: flex; gap: .5rem;
  max-width: 1100px; padding: 8px; border-radius: 14px; border: 1px solid var(--line);
  background: color-mix(in srgb, var(--surface) 86%, transparent);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); box-shadow: var(--shadow);
}
.shell.has-detail .ask { right: calc(400px + 20px); }
.ask input { flex: 1; border: 0; background: transparent; }

.tabbar { display: none; }
.toast {
  position: fixed; left: 50%; bottom: 84px; transform: translateX(-50%); background: var(--text); color: var(--bg);
  padding: .6rem 1rem; border-radius: 10px; font-size: .9rem; opacity: 0; pointer-events: none; transition: opacity .2s; z-index: 50;
}
.toast.show { opacity: 1; }

/* 모바일: 하단 탭, 상세는 전체 화면 */
@media (max-width: 900px) {
  .shell, .shell.has-detail { grid-template-columns: minmax(0, 1fr); grid-template-areas: "top" "main"; }
  .sidebar { display: none; }
  .topbar { padding: 10px 16px; padding-top: max(10px, env(safe-area-inset-top)); }
  .main { padding: 16px 16px 150px; }
  .filters { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; max-width: 100%; }
  .chip { flex: 0 0 auto; }
  .bento { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .tile { padding: 10px 12px; }
  .tile .num { font-size: 1.5rem; }
  .top-list li button { flex-wrap: wrap; row-gap: 0; }
  .top-list .t { flex-basis: 100%; }
  .tile.wide { grid-column: span 2; }
  .item { grid-template-columns: 56px minmax(0, 1fr); }
  .item .meta { grid-column: 2; justify-self: start; }
  .kbd-hint { display: none; }
  .detail { position: fixed; inset: 0; z-index: 20; height: auto; border: 0; }
  .ask { left: 12px; right: 12px; bottom: calc(64px + env(safe-area-inset-bottom)); }
  .shell.has-detail .ask { right: 12px; }
  .tabbar {
    display: flex; position: fixed; left: 0; right: 0; bottom: 0; z-index: 7; justify-content: space-around;
    padding: 8px 0 calc(8px + env(safe-area-inset-bottom)); background: var(--surface); border-top: 1px solid var(--line);
  }
  .tabbar a { text-decoration: none; color: var(--text-2); font-weight: 700; font-size: .85rem; padding: .3rem .8rem; }
  .tabbar a[aria-current="page"] { color: var(--brand); }
}

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
```

---

# [첨부] scripts/windows/setup.ps1

```ps1
# 청년의사 브리핑 설치 (한 번만 실행)
# 사용법: newsbot 폴더에서 PowerShell을 열고  powershell -ExecutionPolicy Bypass -File scripts\windows\setup.ps1
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Python이 없습니다. https://www.python.org/downloads/ 에서 3.11 이상을 설치하고 'Add python.exe to PATH'를 체크한 뒤 다시 실행하세요." -ForegroundColor Red
    exit 1
}
py -3 -c "import sys; assert sys.version_info >= (3, 11), sys.version" 
if ($LASTEXITCODE -ne 0) { Write-Host "Python 3.11 이상이 필요합니다." -ForegroundColor Red; exit 1 }

if (-not (Test-Path ".venv")) { py -3 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env 파일을 만들었습니다. 메모장으로 열어 DART_API_KEY 를 넣어 주세요." -ForegroundColor Yellow
}
New-Item -ItemType Directory -Force -Path "data" | Out-Null

Write-Host ""
Write-Host "설치 완료. 다음 순서로 진행하세요:" -ForegroundColor Green
Write-Host "  1) 관리자 계정:  .\.venv\Scripts\python.exe -m newsbot create-admin 내아이디 --name 내이름"
Write-Host "  2) 실행:         scripts\windows\start.bat"
Write-Host "  3) 브라우저:     http://localhost:8000"
```

---

# [첨부] scripts/windows/install-autostart.ps1

```ps1
# 부팅하면 로그인하지 않아도 자동으로 실행되게 등록 (관리자 권한 PowerShell에서 실행)
# 사용법: powershell -ExecutionPolicy Bypass -File scripts\windows\install-autostart.ps1
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { Write-Host "먼저 setup.ps1 을 실행하세요." -ForegroundColor Red; exit 1 }

$taskName = "ChungnyunBriefing"
$cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message "로그인 없이 실행하려면 이 PC의 Windows 비밀번호가 필요합니다"

# 작업 폴더를 지정해야 상대 경로(.env, data)가 깨지지 않습니다 (기본값은 System32)
$action = New-ScheduledTaskAction -Execute $python -Argument "-m newsbot" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -User $cred.UserName -Password $cred.GetNetworkCredential().Password -RunLevel Limited -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "등록 완료: 부팅 때마다 자동 실행됩니다. 지금도 시작했습니다. (작업 스케줄러 > $taskName)" -ForegroundColor Green
```

---

# [첨부] scripts/windows/power-settings.ps1

```ps1
# 노트북을 서버로 쓰기 위한 전원 설정 (전원 연결 시에만 적용, 배터리일 때는 기존 절전 유지)
# 관리자 권한 PowerShell에서 실행
powercfg /change standby-timeout-ac 0      # 전원 연결 시 절전 안 함
powercfg /change hibernate-timeout-ac 0    # 전원 연결 시 최대 절전 안 함
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0   # 전원 연결 시 덮개 닫아도 아무것도 안 함
powercfg /setactive SCHEME_CURRENT
Write-Host "전원 설정 완료. 덮개를 닫을 때는 반드시 전원을 연결해 두세요."
Write-Host "Windows Update는 '사용 시간'을 설정해 업무 시간 재부팅을 피하고, 재부팅돼도 자동 실행이 다시 켭니다."
```

---

# [첨부] tests/test_dart.py

```py
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
```

---

# [첨부] tests/test_app.py

```py
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
```
