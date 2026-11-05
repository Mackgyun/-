# Codex 교차검증 요청 (2026-11-05 갱신)

너는 독립 검토자다. 아래는 한국 의료전문지(청년의사, 직원 30~40명, 기자 약 20명) 기자가 만드는 **자체 웹앱 '청년의사 브리핑'**의 설계와 코드 전체다(시범사업 기능 전체: DART, 알리오, 웹 푸시, 질문 답변, 기사 초안, 스타일북, 메일, 성과 지표). 다른 AI(Claude)가 작성했고, 다른 Claude 에이전트가 이미 한 번 검토했다(그 결과는 반영됨). 칭찬하지 말고 **틀린 것, 위험한 것, 빠진 것**을 찾아라.

시스템 개요:
- Windows 여분 노트북에서 24시간 실행하는 FastAPI 서버 + SQLite
- OpenDART 공시를 5분마다 수집, 보건의료 기업만 골라 중요도 분류
- 자체 웹앱(PWA): PC는 웹 푸시로 Windows 알림(오른쪽 아래), 휴대폰은 홈 화면 앱 푸시
- 초대 링크 기반 다중 사용자, [내가 쓸게요](담당 표시)
- 알리오 수시공시·결산 비교, 보도자료 메일(기본 꺼짐), LLM(Claude/OpenAI) 질문 답변·기사 초안·스타일북, 성과 지표

검토할 것:
1. 보안: 인증·세션·초대, CSP·쿠키, XSS, CSRF, 메일 비밀번호 암호화·권한 분리, LLM 도구가 다른 사용자 데이터에 접근할 여지, 프롬프트 인젝션(공시·메일 본문에 지시문이 섞인 경우), 인터넷 공개 시 위험
2. 정확성: DART 수집(지연·순서·자정·한도), 알리오 조회 방식(엔드포인트·파라미터·결산표 해석), 자사 기사 파서, FTS 검색, 분류 규칙
3. LLM: Claude·OpenAI 호출 형식, 도구 루프, 비용 계산, 한도, 거절 처리, 숫자 대조의 한계
4. 동시성: SQLite + 스레드 + asyncio, 백그라운드 작업들
5. 웹 푸시·Windows 운영·UX/접근성
6. 법·운영: 개인정보 국외 이전, 저작권, 알리오·자사 사이트 수집의 적절성
7. 우선순위 Top 10 수정 제안 (파일·줄 수준)

답변은 한국어로, 항목마다 심각도(상/중/하)와 근거를 붙여라. 확실하지 않은 것은 "확인 필요"로 표시하라.

---

# [첨부] 설계

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

# 2차: 시범사업 제안서 기능 전체 (2026-11-05)

| 모듈 | 내용 | 안전장치 |
| --- | --- | --- |
| `alio.py` | 기관 이름 → apbaId(주 1회), 항목 이름 → reportFormRootNo(formList, 주 1회), 기관×항목별 itemReportListSusi 1페이지 확인(6시간마다), 결산은 itemReportRight 표를 읽어 전년 대비 | 요청 간 1초, 첫 실행은 저장만, 실패는 기관별로 기록하고 계속 |
| `articles.py` | docdocdoc 기자 목록 페이지 → 기사 본문(JSON-LD → og → 본문 영역), 본문의 기자 이메일로 본인 기사만 저장, SQLite FTS5(trigram) 검색 | 요청 간 2초, 이미 모은 구간이면 중단 |
| `llm.py` | Claude(beta messages, effort, 시스템 프롬프트 캐시, Sonnet/Opus는 `fallbacks: "default"`)·OpenAI(chat completions) 공통 인터페이스, 도구 호출 루프(최대 6회), 사용량·원화 비용 기록, 기자별 월 한도 | 강제 tool_choice·temperature 미사용, 거절 시 안내 문구 |
| `qa.py` | 질문 도구: 공시 검색, 공시 원문, DART 재무(fnlttSinglAcnt), 알리오 결산, 과거 기사, (켜면) 내 메일. 정기 브리핑(AI 없으면 목록형) | 모두 읽기 전용, 메일은 본인 것만 |
| `writing.py` | 스타일북(내 기사 최대 30편 분석), 초안(스타일북 + 내 비슷한 기사 3편 + 원자료), 숫자 대조 | 원자료에 없는 숫자 표시, [확인 필요]/[취재 필요] 표기 지시 |
| `mail.py` | IMAP EXAMINE(읽기 전용) + BODY.PEEK, UID 증분, 엠바고 문구 추출, Fernet 암호화 | 기본 꺼짐, AI 전송은 별도 스위치 |

남은 한계: 실제 DART·알리오·AI·메일 연결은 키·접속 제한으로 클라우드에서 확인하지 못함(가짜 응답 테스트만). 알리오 결산표의 실제 형식은 첫 수집 때 확인 필요. 자사 기사 페이지 구조도 첫 수집 때 확인 필요.

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

# [첨부] config/alio.toml

```toml
# 알리오(공공기관 경영정보 공개시스템) 감시 설정
#
# 알리오는 경영공시용 공식 API가 없어 사이트의 조회 방식을 그대로 씁니다.
# 사이트가 바뀌면 수집이 실패할 수 있고, 그때는 관리자 화면에 오류가 표시됩니다.
# 요청 사이에 1초씩 쉬어 서버에 부담을 주지 않습니다.

# 감시할 기관 (알리오 표기와 같아야 합니다. 못 찾은 이름은 관리자 화면에 표시됩니다)
organizations = [
  # 국립대학병원
  "서울대학교병원", "강원대학교병원", "경북대학교병원", "경상국립대학교병원", "부산대학교병원",
  "전남대학교병원", "전북대학교병원", "제주대학교병원", "충남대학교병원", "충북대학교병원",
  "서울대학교치과병원", "부산대학교치과병원", "경북대학교치과병원", "강릉원주대학교치과병원",
  # 국립·공공 의료기관
  "국립암센터", "국립중앙의료원", "한국원자력의학원", "한국보훈복지의료공단",
  # 보건의료 주요 기관
  "국민건강보험공단", "건강보험심사평가원", "한국보건산업진흥원", "한국보건의료연구원",
  "한국의료분쟁조정중재원", "한국보건의료인국가시험원", "대한적십자사",
]

# 감시할 공시 항목 (알리오 항목 이름에 이 단어가 들어가면 감시)
# level: red = 중요, yellow = 일반
[[items]]
match = "손익계산서"
level = "red"
finance = true   # 결산 표를 읽어 전년 대비 비교

[[items]]
match = "임원 현황"
level = "red"

[[items]]
match = "이사회 회의록"
level = "yellow"

[[items]]
match = "감사원 지적사항"
level = "red"

[[items]]
match = "주무부처 지적사항"
level = "red"

[[items]]
match = "징계처분"
level = "yellow"

[[items]]
match = "경영실적 평가"
level = "yellow"

[[items]]
match = "내부감사"
level = "yellow"

# 결산 비교에서 찾을 줄 이름 (앞의 것부터)
[finance]
rows = ["매출액", "영업수익", "의료수익", "영업이익", "의료이익", "법인세비용차감전순이익", "당기순이익"]
```

---

# [첨부] newsbot/config.py

```py
"""환경변수(.env)에서 설정을 읽는다."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")
BASE_DIR = Path(__file__).resolve().parent.parent  # newsbot/ 폴더 (작업 스케줄러가 System32에서 띄워도 안전)


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else BASE_DIR / p


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _times(raw: str) -> tuple[str, ...]:
    return tuple(t.strip() for t in raw.split(",") if t.strip())


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
    alio_path: Path = BASE_DIR / "config/alio.toml"
    data_dir: Path = BASE_DIR / "data"
    poll_interval_sec: int = 300
    dart_rescan_pages: int = 3
    dart_daily_call_limit: int = 18000

    # AI
    llm_provider: str = ""  # claude | openai | "" (꺼짐)
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    claude_models: dict = field(default_factory=lambda: {
        "fast": "claude-haiku-5-5", "main": "claude-sonnet-5-5", "draft": "claude-opus-5-5"})
    openai_models: dict = field(default_factory=lambda: {
        "fast": "gpt-6-luna", "main": "gpt-6.1-sol", "draft": "gpt-6.1-sol"})
    usd_krw: float = 1400.0
    default_monthly_limit_krw: int = 30000

    # 알리오·메일·자사 기사·브리핑
    alio_enabled: bool = True
    alio_poll_hours: int = 6
    alio_verify_ssl: bool = True
    mail_enabled: bool = False  # 법무·IT 검토 후 켬
    mail_ai_summary: bool = False  # 메일 본문을 해외 AI API로 보내 요약 (국외 이전 검토 필요)
    mail_poll_minutes: int = 5
    docdoc_base: str = "https://www.docdocdoc.co.kr"
    digest_times: tuple = ("08:00", "13:00", "18:00", "23:00")

    @property
    def notify_enabled(self) -> bool:
        return self.alert_mode == "notify"

    @property
    def secure_cookies(self) -> bool:
        return self.public_url.startswith("https://")

    @property
    def llm_ready(self) -> bool:
        return (self.llm_provider == "claude" and bool(self.anthropic_api_key)) or (
            self.llm_provider == "openai" and bool(self.openai_api_key))


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or BASE_DIR / ".env")
    mode = os.getenv("ALERT_MODE", "log").strip().lower()
    if mode not in ("log", "notify"):
        raise SystemExit("ALERT_MODE 는 log 또는 notify 여야 합니다.")
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider not in ("", "claude", "openai"):
        raise SystemExit("LLM_PROVIDER 는 claude 또는 openai 여야 합니다.")
    db_path = _path(os.getenv("DB_PATH", "data/newsbot.db"))
    d = Settings()
    return Settings(
        dart_api_key=os.getenv("DART_API_KEY", "").strip(),
        alert_mode=mode,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        public_url=os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/"),
        vapid_contact=os.getenv("VAPID_CONTACT", "mailto:admin@example.com"),
        db_path=db_path,
        rules_path=_path(os.getenv("RULES_PATH", "config/rules.toml")),
        alio_path=_path(os.getenv("ALIO_PATH", "config/alio.toml")),
        data_dir=db_path.parent,
        poll_interval_sec=max(60, int(os.getenv("POLL_INTERVAL_SEC", "300"))),
        dart_rescan_pages=max(1, int(os.getenv("DART_RESCAN_PAGES", "3"))),
        dart_daily_call_limit=int(os.getenv("DART_DAILY_CALL_LIMIT", "18000")),
        llm_provider=provider,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        claude_models={k: os.getenv(f"CLAUDE_MODEL_{k.upper()}", v) for k, v in d.claude_models.items()},
        openai_models={k: os.getenv(f"OPENAI_MODEL_{k.upper()}", v) for k, v in d.openai_models.items()},
        usd_krw=float(os.getenv("USD_KRW", "1400")),
        default_monthly_limit_krw=int(os.getenv("MONTHLY_LIMIT_KRW", "30000")),
        alio_enabled=_bool("ALIO_ENABLED", True),
        alio_poll_hours=max(1, int(os.getenv("ALIO_POLL_HOURS", "6"))),
        alio_verify_ssl=_bool("ALIO_VERIFY_SSL", True),
        mail_enabled=_bool("MAIL_ENABLED", False),
        mail_ai_summary=_bool("MAIL_AI_SUMMARY", False),
        mail_poll_minutes=max(1, int(os.getenv("MAIL_POLL_MINUTES", "5"))),
        docdoc_base=os.getenv("DOCDOC_BASE", "https://www.docdocdoc.co.kr").rstrip("/"),
        digest_times=_times(os.getenv("DIGEST_TIMES", "08:00,13:00,18:00,23:00")),
    )
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
-- 알리오
CREATE TABLE IF NOT EXISTS alio_orgs (
  apba_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  inst_type TEXT,
  dept TEXT,
  resolved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alio_finance (
  disclosure_no TEXT PRIMARY KEY,
  apba_id TEXT NOT NULL,
  org_name TEXT NOT NULL,
  item_name TEXT NOT NULL,
  title TEXT,
  idate TEXT,
  table_json TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);
-- 보도자료 메일 (기자 본인만)
CREATE TABLE IF NOT EXISTS mail_accounts (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  host TEXT NOT NULL,
  username TEXT NOT NULL,
  secret_enc TEXT NOT NULL,
  folder TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  last_uid INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mails (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  uid INTEGER NOT NULL,
  sender TEXT,
  subject TEXT,
  sent_at TEXT,
  embargo TEXT,
  body TEXT,
  summary TEXT,
  first_seen_at TEXT NOT NULL,
  UNIQUE(user_id, uid)
);
-- 자사 기사 (스타일북·유사 기사 검색용)
CREATE TABLE IF NOT EXISTS articles (
  idxno INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  author_id TEXT,
  section TEXT,
  published_at TEXT,
  body TEXT NOT NULL,
  url TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(title, body, tokenize='trigram');
CREATE TABLE IF NOT EXISTS stylebooks (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  content TEXT NOT NULL,
  source_count INTEGER NOT NULL DEFAULT 0,
  model TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  source_kind TEXT NOT NULL,      -- disclosure | mail | text
  source_ref TEXT,
  source_title TEXT,
  source_text TEXT NOT NULL,
  draft TEXT NOT NULL,
  checks_json TEXT NOT NULL,
  examples_json TEXT NOT NULL,
  model TEXT,
  created_at TEXT NOT NULL
);
-- 질문 답변
CREATE TABLE IF NOT EXISTS chats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  trace_json TEXT NOT NULL,
  model TEXT,
  created_at TEXT NOT NULL
);
-- 정기 브리핑 (하루 3~4회, 조용히)
CREATE TABLE IF NOT EXISTS briefings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slot TEXT UNIQUE NOT NULL,
  content TEXT NOT NULL,
  model TEXT,
  created_at TEXT NOT NULL
);
-- AI 사용량 (비용 한도·월간 리포트)
CREATE TABLE IF NOT EXISTS llm_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  at TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  purpose TEXT NOT NULL,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  cost_krw REAL NOT NULL
);
"""

# 기존 DB에 나중에 추가한 열 (없으면 ALTER TABLE)
MIGRATIONS = [
    ("disclosures", "source", "TEXT NOT NULL DEFAULT 'dart'"),
    ("disclosures", "link", "TEXT"),
    ("claims", "written_url", "TEXT"),
    ("claims", "written_at", "TEXT"),
    ("users", "reporter_id", "TEXT"),
    ("users", "monthly_limit_krw", "INTEGER"),
]


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
            for table, column, decl in MIGRATIONS:
                cols = {r[1] for r in self._conn.execute(f"PRAGMA table_info({table})")}
                if column not in cols:
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

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

# [첨부] newsbot/dart.py

```py
"""OpenDART 수집기.

OpenDART 공시검색 API는 공시 제출 후 약 15분 뒤에 반영되고, 반영 순서가 접수 순서와
다를 수 있다. 그래서 '이미 본 공시가 나오면 중단'하지 않고, 매번 최근 몇 페이지를 다시
훑고 한 시간에 한 번은 이틀치 전체를 대조한다. 중복은 rcept_no 기본키로 막는다.
"""

from __future__ import annotations

import html
import io
import logging
import re
import zipfile
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

    async def document_text(self, rcept_no: str, limit: int = 15000) -> str:
        """공시 원문(zip 안의 XML)을 글자만 뽑아 돌려준다. 초안·질문의 근거 자료용."""
        if self.calls_today() >= self.daily_limit:
            raise DartLimitReached("LOCAL", "오늘 호출 한도 도달")
        self.db.set(self._count_key(), str(self.calls_today() + 1))
        resp = await self.http.get(f"{BASE}/document.xml", params={"crtfc_key": self.api_key, "rcept_no": rcept_no})
        resp.raise_for_status()
        if not resp.content.startswith(b"PK"):
            raise DartError("DOC", "원문을 받지 못했습니다")
        texts = []
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            for name in z.namelist():
                raw = z.read(name)
                for enc in ("utf-8", "euc-kr", "cp949"):
                    try:
                        xml = raw.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    continue
                text = re.sub(r"<[^>]+>", " ", xml)
                text = html.unescape(re.sub(r"[ \t\r\f\v]+", " ", text))
                texts.append(re.sub(r"\n\s*\n+", "\n", text).strip())
        return "\n".join(texts)[:limit]

    async def corp_code(self, name: str, cache_path) -> str | None:
        """회사명 → DART 고유번호. 전체 목록(corpCode.xml)을 주 1회 받아 파일로 캐시한다."""
        import json
        import time
        from pathlib import Path

        row = self.db.one("SELECT corp_code FROM companies WHERE corp_name=?", (name,))
        if row:
            return row["corp_code"]
        path = Path(cache_path)
        if not path.exists() or time.time() - path.stat().st_mtime > 7 * 86400:
            self.db.set(self._count_key(), str(self.calls_today() + 1))
            resp = await self.http.get(f"{BASE}/corpCode.xml", params={"crtfc_key": self.api_key})
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                xml = z.read(z.namelist()[0]).decode("utf-8", errors="replace")
            mapping = {}
            for m in re.finditer(r"<corp_code>(\d+)</corp_code>\s*<corp_name>([^<]+)</corp_name>", xml):
                mapping[m.group(2).strip()] = m.group(1)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
        mapping = json.loads(path.read_text(encoding="utf-8"))
        key = "".join(name.split())
        for n, code in mapping.items():
            if "".join(n.split()) == key:
                return code
        return None

    async def financials(self, corp_code: str, year: int, reprt_code: str = "11011") -> list[dict]:
        """단일회사 주요계정 (사업보고서 기준). 매출액·영업이익·당기순이익 등."""
        data = await self._get("fnlttSinglAcnt.json", {"corp_code": corp_code, "bsns_year": str(year),
                                                       "reprt_code": reprt_code})
        return data.get("list") or []


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

# [첨부] newsbot/alio.py

```py
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
```

---

# [첨부] newsbot/articles.py

```py
"""청년의사(docdocdoc.co.kr) 자사 기사 수집과 검색.

- 기자 본인 기사만 모아 스타일북을 만들고, 초안 쓸 때 비슷한 과거 기사를 찾는다.
- 사내 분석용이며, 요청 사이에 2초씩 쉰다. 회사가 ND소프트에서 DB를 받으면 이 수집은 대체한다.
- 페이지 구조가 바뀌어도 버티도록 JSON-LD → og 메타 → 본문 영역 순으로 읽는다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .db import Database, now_iso

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChungnyunBriefing/0.2 (internal)"}
IDX = re.compile(r"articleView\.html\?idxno=(\d+)")
EMAIL = re.compile(r"([A-Za-z0-9._-]+)@docdocdoc\.co\.kr")
DATE = re.compile(r"(20\d{2})[.\-](\d{2})[.\-](\d{2})\s+(\d{2}):(\d{2})")
BODY_SELECTORS = ["#article-view-content-div", "[itemprop=articleBody]", "article.article-veiw-body",
                  "article.article-view-body", "#articleBody", "article"]


@dataclass
class Article:
    idxno: int
    title: str
    author: str
    author_id: str
    section: str
    published_at: str
    body: str
    url: str


def parse_list(html: str) -> list[int]:
    seen, out = set(), []
    for m in IDX.finditer(html):
        n = int(m.group(1))
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _jsonld(soup: BeautifulSoup) -> dict:
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for d in data if isinstance(data, list) else [data]:
            if isinstance(d, dict) and "Article" in str(d.get("@type", "")):
                return d
    return {}


def _meta(soup: BeautifulSoup, *names: str) -> str:
    for n in names:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""


def parse_article(html: str, idxno: int, url: str) -> Article | None:
    soup = BeautifulSoup(html, "html.parser")
    ld = _jsonld(soup)
    title = (ld.get("headline") or _meta(soup, "og:title") or (soup.title.string if soup.title else "") or "").strip()
    title = re.sub(r"\s*[-|]\s*청년의사.*$", "", title)

    body_el = None
    for sel in BODY_SELECTORS:
        body_el = soup.select_one(sel)
        if body_el:
            break
    if body_el:
        for junk in body_el.select("script, style, figure, .ad, .ads, iframe"):
            junk.decompose()
        body = "\n".join(p.get_text(" ", strip=True) for p in body_el.find_all(["p", "div"]) if p.get_text(strip=True))
        if not body:
            body = body_el.get_text("\n", strip=True)
    else:
        body = ld.get("articleBody") or ""
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if not title or len(body) < 100:
        return None

    text = soup.get_text(" ", strip=True)
    email = EMAIL.search(body[-400:]) or EMAIL.search(text)
    author = ""
    a = ld.get("author")
    if isinstance(a, dict):
        author = a.get("name", "")
    elif isinstance(a, list) and a and isinstance(a[0], dict):
        author = a[0].get("name", "")
    if not author:
        m = re.search(r"([가-힣]{2,4})\s*기자", text)
        author = m.group(1) if m else ""
    published = ld.get("datePublished") or _meta(soup, "article:published_time")
    if not published:
        m = DATE.search(text)
        published = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:00+09:00" if m else ""
    section = _meta(soup, "article:section") or ""
    return Article(idxno, title, author.replace("기자", "").strip(), email.group(1).lower() if email else "",
                   section, published, body, url)


class ArticleCollector:
    def __init__(self, db: Database, base: str, http: httpx.AsyncClient | None = None, delay: float = 2.0):
        self.db = db
        self.base = base
        self.http = http or httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True)
        self.delay = delay

    async def _get(self, url: str) -> str:
        await asyncio.sleep(self.delay)
        r = await self.http.get(url)
        r.raise_for_status()
        return r.text

    async def collect_reporter(self, reporter_id: str, max_pages: int = 20, progress=None) -> dict:
        """기자 ID(이메일 앞부분)의 기사를 모은다. 목록 필터가 안 먹어도 본문의 이메일로 다시 거른다."""
        reporter_id = reporter_id.strip().lower()
        added = checked = 0
        for page in range(1, max_pages + 1):
            list_url = (f"{self.base}/news/articleList.html?sc_area=I&sc_word={reporter_id}"
                        f"&view_type=sm&page={page}")
            ids = parse_list(await self._get(list_url))
            new_ids = [i for i in ids if not self.db.one("SELECT 1 FROM articles WHERE idxno=?", (i,))]
            if not ids:
                break
            for idxno in new_ids:
                url = urljoin(self.base, f"/news/articleView.html?idxno={idxno}")
                checked += 1
                try:
                    art = parse_article(await self._get(url), idxno, url)
                except httpx.HTTPError as e:
                    self.db.log("error", f"article {idxno}: {e!r}")
                    continue
                if art and art.author_id == reporter_id:
                    self.save(art)
                    added += 1
                if progress:
                    progress(page, added, checked)
            if not new_ids:
                break  # 이미 모은 구간에 도달
        return {"added": added, "checked": checked}

    def save(self, a: Article) -> None:
        with self.db.tx() as c:
            c.execute("""INSERT OR REPLACE INTO articles(idxno, title, author, author_id, section, published_at,
                         body, url, fetched_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                      (a.idxno, a.title, a.author, a.author_id, a.section, a.published_at, a.body, a.url, now_iso()))
            c.execute("DELETE FROM articles_fts WHERE rowid=?", (a.idxno,))
            c.execute("INSERT INTO articles_fts(rowid, title, body) VALUES(?,?,?)", (a.idxno, a.title, a.body))


def _fts_query(text: str) -> str:
    """검색어에서 3글자 이상 덩어리를 뽑아 OR 검색어로 만든다 (trigram 색인)."""
    words = re.findall(r"[가-힣A-Za-z0-9]{3,}", text)
    uniq = []
    for w in words:
        if w not in uniq:
            uniq.append(w)
    return " OR ".join(f'"{w}"' for w in uniq[:12])


def search_articles(db: Database, text: str, author_id: str | None = None, limit: int = 5) -> list[dict]:
    q = _fts_query(text)
    if not q:
        return []
    sql = """SELECT a.idxno, a.title, a.author, a.published_at, a.url, substr(a.body, 1, 1500) AS body
             FROM articles_fts f JOIN articles a ON a.idxno = f.rowid
             WHERE articles_fts MATCH ?"""
    params: list = [q]
    if author_id:
        sql += " AND a.author_id = ?"
        params.append(author_id)
    sql += " ORDER BY bm25(articles_fts) LIMIT ?"
    params.append(limit)
    try:
        return db.query(sql, tuple(params))
    except Exception:  # noqa: BLE001 - FTS 문법 오류 시 빈 결과
        log.exception("fts search failed")
        return []
```

---

# [첨부] newsbot/llm.py

```py
"""AI(LLM) 호출 계층. Claude와 OpenAI를 같은 방식으로 쓰고, 사용량·비용을 기록한다.

등급(tier)
  fast  : 정기 브리핑 요약 등 대량·단순 작업
  main  : 질문 답변
  draft : 스타일북 분석, 기사 초안
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Settings
from .db import Database, now, now_iso

log = logging.getLogger(__name__)

# 100만 토큰당 달러 (입력, 출력). Claude는 Anthropic 요금표(2026-10 기준),
# OpenAI는 공개 요금 정리 글 기준이라 실제 청구서와 대조가 필요하다.
PRICES_USD = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6.1-terra": (1.0, 5.0),
    "gpt-6.1-sol": (2.0, 10.0),
    "gpt-6-astra": (10.0, 50.0),
}
UNKNOWN_PRICE = (4.0, 20.0)  # 모르는 모델은 비싸게 잡아 한도를 넘지 않게
EFFORT = {"fast": "low", "main": "medium", "draft": "high"}
MAX_TOKENS = {"fast": 2000, "main": 4000, "draft": 8000}


class LLMError(Exception):
    """사용자에게 그대로 보여줄 수 있는 문구를 담는다."""


class BudgetExceeded(LLMError):
    pass


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    func: Callable[[dict], Any]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0


@dataclass
class AgentResult:
    text: str
    trace: list = field(default_factory=list)
    model: str = ""


def _run_tool(tools: dict[str, Tool], name: str, args: dict) -> str:
    tool = tools.get(name)
    if not tool:
        return json.dumps({"error": f"없는 도구: {name}"}, ensure_ascii=False)
    try:
        result = tool.func(args or {})
    except Exception as e:  # noqa: BLE001 - 도구 오류는 모델에게 알려 다시 시도하게 함
        log.exception("tool %s failed", name)
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
    return text[:20000]


class ClaudeBackend:
    name = "claude"

    def __init__(self, api_key: str, client=None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=180.0)
        self.client = client

    @staticmethod
    def _extra(model: str) -> dict:
        # Sonnet 5.5 / Opus 5.5는 안전 분류기가 거절하면 서버가 다른 모델로 다시 돌려준다.
        if "sonnet-5-5" in model or "opus-5" in model or "fable" in model:
            return {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        return {}

    def _call(self, model, system, messages, tools, tier):
        kwargs = dict(
            model=model,
            max_tokens=MAX_TOKENS[tier],
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            output_config={"effort": EFFORT[tier]},
            **self._extra(model),
        )
        if tools:
            kwargs["tools"] = [{"name": t.name, "description": t.description, "input_schema": t.schema}
                               for t in tools]
        resp = self.client.beta.messages.create(**kwargs)
        u = resp.usage
        usage = Usage(u.input_tokens, u.output_tokens,
                      getattr(u, "cache_read_input_tokens", 0) or 0,
                      getattr(u, "cache_creation_input_tokens", 0) or 0)
        if resp.stop_reason == "refusal":
            raise LLMError("AI가 이 요청을 처리하지 않았어요. 표현을 바꿔 다시 시도해 주세요.")
        return resp, usage

    def complete(self, model, system, prompt, tier):
        resp, usage = self._call(model, system, [{"role": "user", "content": prompt}], None, tier)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return text, [usage]

    def agent(self, model, system, history, tools, tier, max_steps):
        by_name = {t.name: t for t in tools}
        messages = list(history)
        usages, trace = [], []
        for _ in range(max_steps):
            resp, usage = self._call(model, system, messages, tools, tier)
            usages.append(usage)
            if resp.stop_reason != "tool_use":
                text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                return text, trace, usages
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for b in resp.content:
                if getattr(b, "type", "") == "tool_use":
                    out = _run_tool(by_name, b.name, b.input)
                    trace.append({"tool": b.name, "input": b.input, "output": out[:2000]})
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            messages.append({"role": "user", "content": results})
        return "조회를 여러 번 했지만 답을 정리하지 못했어요. 질문을 좁혀 주세요.", trace, usages


class OpenAIBackend:
    name = "openai"

    def __init__(self, api_key: str, client=None):
        if client is None:
            import openai

            client = openai.OpenAI(api_key=api_key, max_retries=3, timeout=180.0)
        self.client = client

    def _call(self, model, messages, tools, tier):
        kwargs = dict(model=model, messages=messages, max_completion_tokens=MAX_TOKENS[tier])
        if tools:
            kwargs["tools"] = [{"type": "function", "function": {
                "name": t.name, "description": t.description, "parameters": t.schema}} for t in tools]
        resp = self.client.chat.completions.create(**kwargs)
        u = resp.usage
        return resp, Usage(getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0)

    def complete(self, model, system, prompt, tier):
        resp, usage = self._call(model, [{"role": "system", "content": system},
                                         {"role": "user", "content": prompt}], None, tier)
        return resp.choices[0].message.content or "", [usage]

    def agent(self, model, system, history, tools, tier, max_steps):
        by_name = {t.name: t for t in tools}
        messages = [{"role": "system", "content": system}, *history]
        usages, trace = [], []
        for _ in range(max_steps):
            resp, usage = self._call(model, messages, tools, tier)
            usages.append(usage)
            msg = resp.choices[0].message
            calls = msg.tool_calls or []
            if not calls:
                return msg.content or "", trace, usages
            messages.append({"role": "assistant", "content": msg.content,
                             "tool_calls": [c.model_dump() if hasattr(c, "model_dump") else c for c in calls]})
            for c in calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                out = _run_tool(by_name, c.function.name, args)
                trace.append({"tool": c.function.name, "input": args, "output": out[:2000]})
                messages.append({"role": "tool", "tool_call_id": c.id, "content": out})
        return "조회를 여러 번 했지만 답을 정리하지 못했어요. 질문을 좁혀 주세요.", trace, usages


class LLM:
    def __init__(self, settings: Settings, db: Database, backend=None):
        self.settings = settings
        self.db = db
        self._backend = backend

    @property
    def available(self) -> bool:
        return self._backend is not None or self.settings.llm_ready

    @property
    def backend(self):
        if self._backend is None:
            if not self.settings.llm_ready:
                raise LLMError("AI API 키가 아직 없어요. 관리자가 .env 에 키를 넣으면 켜집니다.")
            if self.settings.llm_provider == "claude":
                self._backend = ClaudeBackend(self.settings.anthropic_api_key)
            else:
                self._backend = OpenAIBackend(self.settings.openai_api_key)
        return self._backend

    def model_for(self, tier: str) -> str:
        models = self.settings.openai_models if self.backend.name == "openai" else self.settings.claude_models
        return models[tier]

    # --- 비용 -----------------------------------------------------------
    def cost_krw(self, model: str, usage: Usage) -> float:
        pin, pout = PRICES_USD.get(model, UNKNOWN_PRICE)
        usd = (usage.input_tokens * pin + usage.cache_write * pin * 1.25 + usage.cache_read * pin * 0.1
               + usage.output_tokens * pout) / 1_000_000
        return round(usd * self.settings.usd_krw, 2)

    def month_spent(self, user_id: int | None = None) -> float:
        start = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
        if user_id is None:
            row = self.db.one("SELECT COALESCE(SUM(cost_krw),0) s FROM llm_usage WHERE at >= ?", (start,))
        else:
            row = self.db.one("SELECT COALESCE(SUM(cost_krw),0) s FROM llm_usage WHERE at >= ? AND user_id=?",
                              (start, user_id))
        return float(row["s"])

    def limit_for(self, user_id: int) -> int:
        row = self.db.one("SELECT monthly_limit_krw FROM users WHERE id=?", (user_id,))
        return int(row["monthly_limit_krw"]) if row and row["monthly_limit_krw"] else \
            self.settings.default_monthly_limit_krw

    def _check_budget(self, user_id: int | None) -> None:
        if user_id is None:
            return
        if self.month_spent(user_id) >= self.limit_for(user_id):
            raise BudgetExceeded("이번 달 AI 사용 한도를 다 썼어요. 관리자에게 한도 조정을 요청해 주세요.")

    def _record(self, user_id, model, purpose, usages: list[Usage]) -> None:
        for u in usages:
            self.db.execute(
                """INSERT INTO llm_usage(user_id, at, provider, model, purpose, input_tokens, output_tokens, cost_krw)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (user_id, now_iso(), self.backend.name, model, purpose,
                 u.input_tokens + u.cache_read + u.cache_write, u.output_tokens, self.cost_krw(model, u)))

    # --- 호출 -----------------------------------------------------------
    def complete(self, system: str, prompt: str, tier: str, user_id: int | None, purpose: str) -> tuple[str, str]:
        self._check_budget(user_id)
        model = self.model_for(tier)
        try:
            text, usages = self.backend.complete(model, system, prompt, tier)
        except LLMError:
            raise
        except Exception as e:  # noqa: BLE001
            log.exception("llm complete failed")
            raise LLMError(f"AI 호출에 실패했어요: {type(e).__name__}") from e
        self._record(user_id, model, purpose, usages)
        return text, model

    def agent(self, system: str, history: list[dict], tools: list[Tool], tier: str, user_id: int | None,
              purpose: str, max_steps: int = 6) -> AgentResult:
        self._check_budget(user_id)
        model = self.model_for(tier)
        try:
            text, trace, usages = self.backend.agent(model, system, history, tools, tier, max_steps)
        except LLMError:
            raise
        except Exception as e:  # noqa: BLE001
            log.exception("llm agent failed")
            raise LLMError(f"AI 호출에 실패했어요: {type(e).__name__}") from e
        self._record(user_id, model, purpose, usages)
        return AgentResult(text=text, trace=trace, model=model)
```

---

# [첨부] newsbot/qa.py

```py
"""질문 답변: AI가 도구로 수집 데이터를 찾아보고 출처를 붙여 답한다.

도구는 모두 읽기 전용이다. 메일·내 기사 도구는 질문한 사람 본인 것만 본다.
"""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta

from .alio import finance_overview
from .articles import search_articles
from .config import Settings
from .dart import VIEW_URL, DartClient
from .db import Database, now, now_iso
from .llm import LLM, Tool

SYSTEM = """당신은 한국 의료전문지 '청년의사' 기자를 돕는 취재 보조원입니다. 오늘은 {today}입니다.
- 반드시 도구로 찾은 자료만 근거로 답합니다. 찾지 못하면 "수집된 자료에서 확인되지 않았습니다"라고 말합니다.
- 숫자, 날짜, 회사·기관명은 자료에 있는 그대로 씁니다. 추정하지 않습니다.
- 답변 끝에 '출처' 목록을 붙이고, 자료마다 제목과 링크를 적습니다.
- 짧고 정확하게, 기자가 바로 쓸 수 있게 한국어로 답합니다.
- 메일 내용은 질문한 기자 본인의 메일입니다. 다른 사람에게 공유하라고 권하지 않습니다."""


def _disc_out(r: dict) -> dict:
    url = r.get("link") or VIEW_URL.format(rcept_no=r["rcept_no"])
    return {"id": r["rcept_no"], "source": "알리오" if r.get("source") == "alio" else "DART",
            "company": r["corp_name"], "title": r["report_nm"], "date": r["rcept_dt"],
            "level": r["level"], "url": url}


def build_tools(settings: Settings, db: Database, user: dict, dart: DartClient | None,
                loop: asyncio.AbstractEventLoop | None) -> list[Tool]:
    def run(coro):
        if loop is None:
            return asyncio.run(coro)
        return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=120)

    def search_disclosures(a: dict):
        days = max(1, min(int(a.get("days", 7) or 7), 365))
        since = (now() - timedelta(days=days)).isoformat(timespec="seconds")
        sql = "SELECT * FROM disclosures WHERE first_seen_at >= ?"
        params: list = [since]
        q = (a.get("query") or "").strip()
        for word in q.split()[:4]:
            sql += " AND (corp_name LIKE ? OR report_nm LIKE ?)"
            params += [f"%{word}%", f"%{word}%"]
        if a.get("level") in ("red", "yellow", "gray"):
            sql += " AND level=?"
            params.append(a["level"])
        if a.get("source") in ("dart", "alio"):
            sql += " AND source=?"
            params.append(a["source"])
        sql += " ORDER BY first_seen_at DESC LIMIT 30"
        return [_disc_out(r) for r in db.query(sql, tuple(params))]

    def get_disclosure(a: dict):
        r = db.one("SELECT * FROM disclosures WHERE rcept_no=?", (a.get("id", ""),))
        if not r:
            return {"error": "없는 공시"}
        out = _disc_out(r)
        if r.get("source", "dart") == "dart" and dart and settings.dart_api_key:
            try:
                out["text"] = run(dart.document_text(r["rcept_no"], limit=8000))
            except Exception as e:  # noqa: BLE001
                out["text_error"] = str(e)
        return out

    def company_financials(a: dict):
        if not (dart and settings.dart_api_key):
            return {"error": "DART 키가 없어 재무 정보를 조회할 수 없습니다"}
        name = (a.get("company") or "").strip()
        year = int(a.get("year") or now().year - 1)
        code = run(dart.corp_code(name, settings.data_dir / "corpcode.json"))
        if not code:
            return {"error": f"DART에서 '{name}' 회사를 찾지 못했습니다"}
        rows = run(dart.financials(code, year))
        keep = [{"account": x.get("account_nm"), "fs": x.get("fs_nm"), "this_year": x.get("thstrm_amount"),
                 "last_year": x.get("frmtrm_amount"), "currency": x.get("currency")} for x in rows]
        return {"company": name, "year": year, "report": "사업보고서", "rows": keep[:40],
                "url": f"https://dart.fss.or.kr/dsab007/main.do?textCrpNm={name}"}

    def alio_finance(a: dict):
        org = (a.get("organization") or "").replace(" ", "")
        data = [x for x in finance_overview(db) if not org or org in x["org"].replace(" ", "")]
        return data or {"error": "해당 기관의 결산 자료가 아직 수집되지 않았습니다"}

    def search_my_mail(a: dict):
        if not settings.mail_enabled:
            return {"error": "메일 기능이 꺼져 있습니다"}
        days = max(1, min(int(a.get("days", 14) or 14), 90))
        since = (now() - timedelta(days=days)).isoformat(timespec="seconds")
        sql = "SELECT id, sender, subject, sent_at, embargo, substr(body,1,2500) body FROM mails WHERE user_id=? AND first_seen_at>=?"
        params: list = [user["id"], since]
        for word in (a.get("query") or "").split()[:4]:
            sql += " AND (subject LIKE ? OR body LIKE ? OR sender LIKE ?)"
            params += [f"%{word}%"] * 3
        sql += " ORDER BY first_seen_at DESC LIMIT 10"
        return db.query(sql, tuple(params))

    def search_newsroom_articles(a: dict):
        mine = bool(a.get("mine_only"))
        rid = (user.get("reporter_id") or "").lower() or None
        rows = search_articles(db, a.get("query", ""), author_id=rid if mine else None, limit=6)
        return [{"title": r["title"], "author": r["author"], "date": (r["published_at"] or "")[:10],
                 "url": r["url"], "excerpt": r["body"][:600]} for r in rows]

    S = lambda props, req=(): {"type": "object", "properties": props, "required": list(req)}  # noqa: E731
    tools = [
        Tool("search_disclosures", "수집된 DART·알리오 공시를 기업명·제목 키워드로 찾는다. 최근 며칠인지 정할 수 있다.",
             S({"query": {"type": "string", "description": "기업명이나 제목 키워드, 띄어쓰기로 여러 개"},
                "days": {"type": "integer", "description": "최근 며칠 (기본 7)"},
                "level": {"type": "string", "enum": ["red", "yellow", "gray"]},
                "source": {"type": "string", "enum": ["dart", "alio"]}}), search_disclosures),
        Tool("get_disclosure", "공시 하나의 상세와 DART 원문 일부를 가져온다. id는 search_disclosures 결과의 id.",
             S({"id": {"type": "string"}}, ["id"]), get_disclosure),
        Tool("company_financials", "상장사의 사업보고서 주요 계정(매출액, 영업이익, 당기순이익 등)을 DART에서 조회한다.",
             S({"company": {"type": "string", "description": "DART 회사명"},
                "year": {"type": "integer", "description": "사업연도 (예: 2025)"}}, ["company"]), company_financials),
        Tool("alio_finance", "알리오에서 수집한 공공기관·국립대병원 결산(손익계산서) 전년 대비 비교를 가져온다.",
             S({"organization": {"type": "string", "description": "기관명 일부 (비우면 전체)"}}), alio_finance),
        Tool("search_newsroom_articles", "청년의사 과거 기사를 검색한다. mine_only=true면 질문한 기자 본인 기사만.",
             S({"query": {"type": "string"}, "mine_only": {"type": "boolean"}}, ["query"]), search_newsroom_articles),
    ]
    if settings.mail_enabled:
        tools.append(Tool("search_my_mail", "질문한 기자 본인의 보도자료 메일을 검색한다 (제목·본문·보낸 사람).",
                          S({"query": {"type": "string"}, "days": {"type": "integer"}}), search_my_mail))
    return tools


def ask(settings: Settings, db: Database, llm: LLM, user: dict, question: str, dart: DartClient | None,
        loop: asyncio.AbstractEventLoop | None) -> dict:
    """동기 함수 (스레드에서 실행)."""
    recent = db.query("SELECT question, answer FROM chats WHERE user_id=? ORDER BY id DESC LIMIT 3", (user["id"],))
    history: list[dict] = []
    for c in reversed(recent):
        history += [{"role": "user", "content": c["question"]}, {"role": "assistant", "content": c["answer"][:3000]}]
    history.append({"role": "user", "content": question})
    tools = build_tools(settings, db, user, dart, loop)
    system = SYSTEM.format(today=now().strftime("%Y년 %m월 %d일 %H:%M"))
    result = llm.agent(system, history, tools, tier="main", user_id=user["id"], purpose="question")
    db.execute("INSERT INTO chats(user_id, question, answer, trace_json, model, created_at) VALUES(?,?,?,?,?,?)",
               (user["id"], question, result.text, json.dumps(result.trace, ensure_ascii=False), result.model,
                now_iso()))
    return {"answer": result.text, "trace": [{"tool": t["tool"], "input": t["input"]} for t in result.trace],
            "model": result.model}


# --- 정기 브리핑 -------------------------------------------------------------
DIGEST_SYSTEM = """당신은 의료전문지 편집국의 아침·점심·저녁 브리핑 담당입니다. 주어진 공시 목록만 근거로,
기자가 30초 안에 읽을 수 있게 핵심 5줄 이내로 정리합니다. 목록에 없는 내용은 쓰지 않습니다."""


def make_digest(db: Database, llm: LLM | None, slot: str, since: str) -> dict | None:
    rows = db.query("""SELECT corp_name, report_nm, level, source FROM disclosures
                       WHERE first_seen_at >= ? AND level != 'gray' ORDER BY level='red' DESC, first_seen_at DESC
                       LIMIT 60""", (since,))
    red = [r for r in rows if r["level"] == "red"]
    lines = [f"- {'[중요] ' if r['level'] == 'red' else ''}{r['corp_name']}: {r['report_nm']}" for r in rows]
    base = f"지난 브리핑 이후 공시 {len(rows)}건 (중요 {len(red)}건)"
    content, model = base + ("\n" + "\n".join(lines[:8]) if lines else "\n새 공시가 없습니다."), None
    if llm and llm.available and rows:
        try:
            content, model = llm.complete(DIGEST_SYSTEM, base + "\n" + "\n".join(lines), tier="fast",
                                          user_id=None, purpose="digest")
            content = base + "\n" + content.strip()
        except Exception as e:  # noqa: BLE001 - AI 실패 시 목록형으로
            db.log("error", f"digest llm: {e}")
    db.execute("INSERT OR IGNORE INTO briefings(slot, content, model, created_at) VALUES(?,?,?,?)",
               (slot, content, model, now_iso()))
    return db.one("SELECT * FROM briefings WHERE slot=?", (slot,))
```

---

# [첨부] newsbot/writing.py

```py
"""스타일북 만들기와 기사 초안 작성.

파인튜닝은 하지 않는다. 기자 본인 기사에서 뽑은 '스타일북'과 비슷한 과거 기사 몇 편을
매번 함께 넘기고, 초안의 숫자가 원자료에 있는지 대조해 표시한다. 출고는 항상 기자가 한다.
"""

from __future__ import annotations

import json
import re

from .articles import search_articles
from .db import Database, now_iso
from .llm import LLM, LLMError

STYLEBOOK_SYSTEM = """당신은 한국 의료전문지 '청년의사'의 편집 데스크입니다.
한 기자가 쓴 기사들을 읽고, 이 기자의 문체를 다른 사람이 따라 쓸 수 있도록 '스타일북'을 만듭니다.
기사 내용(사실)을 요약하지 말고, 쓰는 방식만 정리하세요. 기사 원문 문장을 길게 베끼지 마세요."""

STYLEBOOK_PROMPT = """아래는 {author} 기자의 기사 {n}편입니다.

다음 항목으로 스타일북을 한국어 마크다운으로 써 주세요. 각 항목에 짧은 예시 표현을 붙이세요.
1. 기사 유형별 구조 (스트레이트, 해설, 인터뷰 등 실제로 보이는 유형만)
2. 제목과 부제 쓰는 법 (길이, 따옴표 사용, 숫자 표기)
3. 리드 문장 패턴 (첫 문장에 무엇을 먼저 쓰는지)
4. 인용 방식 (직접·간접 인용 비율, '~고 말했다/밝혔다' 등 서술어)
5. 문장 길이와 리듬, 단락 길이
6. 자주 쓰는 표현과 피하는 표현
7. 숫자·단위·기관명·직함 표기 규칙
8. 마무리 방식

{articles}"""

DRAFT_SYSTEM = """당신은 한국 의료전문지 '청년의사'의 기자를 돕는 초안 작성 도우미입니다.
반드시 지킬 것:
- 원자료에 있는 사실만 씁니다. 원자료에 없는 숫자, 인명, 기관명, 인용문을 만들지 않습니다.
- 확인이 필요한 부분은 [확인 필요]라고 표시합니다. 취재가 필요한 부분은 [취재 필요: 무엇]으로 남깁니다.
- 아래 기자 스타일북을 따르고, 참고 기사의 문장을 그대로 베끼지 않습니다.
- 형식: 첫 줄 제목, 둘째 줄 부제(선택), 빈 줄, 본문. 마지막 줄에 '○○○ 기자' 대신 [기자명]을 둡니다.

# 기자 스타일북
{stylebook}"""

DRAFT_PROMPT = """다음 원자료로 {kind} 기사 초안을 써 주세요. 분량은 600~1,000자.

# 원자료 ({source_title})
{source}

# 참고: 이 기자가 예전에 쓴 비슷한 기사 (문체 참고용, 사실 근거로 쓰지 말 것)
{examples}"""

DEFAULT_STYLEBOOK = """(아직 이 기자의 스타일북이 없습니다. 청년의사 일반 스트레이트 기사 형식을 따릅니다:
제목은 핵심 사실을 30자 안팎으로, 리드는 누가·무엇을·언제를 한 문장에, 둘째 단락부터 배경과 수치,
인용은 '~고 밝혔다/말했다'로 맺습니다.)"""

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def build_stylebook(db: Database, llm: LLM, user: dict, max_articles: int = 30) -> dict:
    reporter_id = (user.get("reporter_id") or "").strip().lower()
    if not reporter_id:
        raise LLMError("설정에서 기자 ID(이메일 앞부분)를 먼저 입력해 주세요.")
    arts = db.query("SELECT title, body, published_at FROM articles WHERE author_id=? "
                    "ORDER BY published_at DESC LIMIT ?", (reporter_id, max_articles))
    if len(arts) < 5:
        raise LLMError(f"스타일북을 만들려면 기사가 5편 이상 필요해요 (지금 {len(arts)}편). 먼저 '내 기사 가져오기'를 하세요.")
    joined = "\n\n".join(f"## {a['title']} ({(a['published_at'] or '')[:10]})\n{a['body'][:1800]}" for a in arts)
    text, model = llm.complete(STYLEBOOK_SYSTEM,
                               STYLEBOOK_PROMPT.format(author=user["display_name"], n=len(arts), articles=joined),
                               tier="draft", user_id=user["id"], purpose="stylebook")
    db.execute("""INSERT INTO stylebooks(user_id, content, source_count, model, updated_at) VALUES(?,?,?,?,?)
                  ON CONFLICT(user_id) DO UPDATE SET content=excluded.content, source_count=excluded.source_count,
                  model=excluded.model, updated_at=excluded.updated_at""",
               (user["id"], text.strip(), len(arts), model, now_iso()))
    return {"content": text.strip(), "source_count": len(arts), "model": model}


def _digits(s: str) -> str:
    return s.replace(",", "")


def check_numbers(draft: str, source: str) -> list[dict]:
    """초안의 숫자가 원자료에 있는지 대조. 연도·날짜처럼 짧은 숫자도 포함한다."""
    src = _digits(source)
    out, seen = [], set()
    for m in _NUM.finditer(draft):
        raw = m.group(0)
        n = _digits(raw).rstrip(".")
        if n in seen or len(n) < 2:
            continue
        seen.add(n)
        start = max(0, m.start() - 12)
        out.append({"number": raw, "found": n in src, "context": draft[start:m.end() + 12].replace("\n", " ")})
    return out


def make_draft(db: Database, llm: LLM, user: dict, source_kind: str, source_ref: str | None, source_title: str,
               source_text: str, kind: str = "스트레이트") -> dict:
    if len(source_text.strip()) < 50:
        raise LLMError("원자료가 너무 짧아요. 보도자료나 공시 본문을 붙여 넣어 주세요.")
    sb = db.one("SELECT content FROM stylebooks WHERE user_id=?", (user["id"],))
    stylebook = sb["content"] if sb else DEFAULT_STYLEBOOK
    reporter_id = (user.get("reporter_id") or "").strip().lower() or None
    examples = search_articles(db, f"{source_title} {source_text[:500]}", author_id=reporter_id, limit=3)
    if not examples and reporter_id:
        examples = search_articles(db, f"{source_title} {source_text[:500]}", limit=3)
    ex_text = "\n\n".join(f"## {e['title']}\n{e['body'][:1200]}" for e in examples) or "(없음)"
    text, model = llm.complete(DRAFT_SYSTEM.format(stylebook=stylebook),
                               DRAFT_PROMPT.format(kind=kind, source_title=source_title,
                                                   source=source_text[:15000], examples=ex_text),
                               tier="draft", user_id=user["id"], purpose="draft")
    checks = check_numbers(text, source_text)
    ex_meta = [{"title": e["title"], "url": e["url"]} for e in examples]
    cur = db.execute(
        """INSERT INTO drafts(user_id, source_kind, source_ref, source_title, source_text, draft, checks_json,
           examples_json, model, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (user["id"], source_kind, source_ref, source_title, source_text[:20000], text,
         json.dumps(checks, ensure_ascii=False), json.dumps(ex_meta, ensure_ascii=False), model, now_iso()))
    del cur
    row = db.one("SELECT id FROM drafts WHERE user_id=? ORDER BY id DESC LIMIT 1", (user["id"],))
    return {"id": row["id"], "draft": text, "checks": checks, "examples": ex_meta, "model": model}
```

---

# [첨부] newsbot/mail.py

```py
"""보도자료 메일 브리핑 (기자 본인만 봄).

- 기본은 꺼져 있음(MAIL_ENABLED=false). 개인정보 국외 이전 등 법무·IT 검토 후 켠다.
- 기자가 지정한 메일함(라벨) 하나만 읽기 전용으로 연다(EXAMINE, BODY.PEEK: 읽음 표시도 안 바뀜).
- 비밀번호(앱 비밀번호)는 data/secret.key 로 암호화해 저장한다.
- AI 요약은 MAIL_AI_SUMMARY=true 일 때만 (메일 본문이 해외 AI API로 나가기 때문).
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from pathlib import Path

from cryptography.fernet import Fernet

from .config import KST
from .db import Database, now_iso

log = logging.getLogger(__name__)
EMBARGO = re.compile(r"(엠바고|보도\s*시점|보도\s*일시|보도\s*가능|보도\s*유예)[^\n]{0,60}")


class Vault:
    def __init__(self, data_dir: Path):
        path = data_dir / "secret.key"
        if not path.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(Fernet.generate_key())
        self.f = Fernet(path.read_bytes())

    def seal(self, text: str) -> str:
        return self.f.encrypt(text.encode()).decode()

    def open(self, token: str) -> str:
        return self.f.decrypt(token.encode()).decode()


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001
        return value


def _body(msg: email.message.Message) -> str:
    parts = msg.walk() if msg.is_multipart() else [msg]
    plain, html = "", ""
    for part in parts:
        ctype = part.get_content_type()
        if part.get_content_disposition() == "attachment":
            continue
        try:
            payload = part.get_payload(decode=True)
        except Exception:  # noqa: BLE001
            continue
        if not payload:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if ctype == "text/plain" and not plain:
            plain = text
        elif ctype == "text/html" and not html:
            html = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", text, flags=re.I)
            html = re.sub(r"<br\s*/?>|</p>|</div>", "\n", html, flags=re.I)
            html = re.sub(r"<[^>]+>", " ", html)
    text = plain or html
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def find_embargo(subject: str, body: str) -> str:
    m = EMBARGO.search(subject) or EMBARGO.search(body[:3000])
    return m.group(0).strip() if m else ""


def parse_message(raw: bytes) -> dict:
    msg = email.message_from_bytes(raw)
    subject = _decode(msg.get("Subject"))
    body = _body(msg)
    sent = ""
    try:
        dt = parsedate_to_datetime(msg.get("Date"))
        sent = dt.astimezone(KST).isoformat(timespec="seconds") if dt else ""
    except (TypeError, ValueError):
        pass
    return {"sender": _decode(msg.get("From")), "subject": subject, "sent_at": sent, "body": body[:30000],
            "embargo": find_embargo(subject, body)}


def fetch_new(db: Database, vault: Vault, account: dict, imap_factory=imaplib.IMAP4_SSL, max_new: int = 50) -> int:
    """동기 함수(스레드에서 실행). 새 메일 수를 돌려준다."""
    password = vault.open(account["secret_enc"])
    imap = imap_factory(account["host"])
    try:
        imap.login(account["username"], password)
        status, _ = imap.select(f'"{account["folder"]}"', readonly=True)
        if status != "OK":
            raise RuntimeError(f"메일함 '{account['folder']}'을 열 수 없습니다")
        last = int(account["last_uid"] or 0)
        status, data = imap.uid("search", None, f"UID {last + 1}:*")
        uids = [int(u) for u in (data[0] or b"").split() if int(u) > last]
        if last == 0:
            uids = uids[-max_new:]  # 처음 연결 때는 최근 메일만
        added = 0
        for uid in uids[:max_new]:
            status, parts = imap.uid("fetch", str(uid), "(BODY.PEEK[])")
            raw = next((p[1] for p in parts if isinstance(p, tuple)), None)
            if not raw:
                continue
            m = parse_message(raw)
            n = db.execute("""INSERT OR IGNORE INTO mails(user_id, uid, sender, subject, sent_at, embargo, body,
                              first_seen_at) VALUES(?,?,?,?,?,?,?,?)""",
                           (account["user_id"], uid, m["sender"], m["subject"], m["sent_at"], m["embargo"],
                            m["body"], now_iso()))
            added += n
        if uids:
            db.execute("UPDATE mail_accounts SET last_uid=?, last_error=NULL, updated_at=? WHERE user_id=?",
                       (max(uids), now_iso(), account["user_id"]))
        else:
            db.execute("UPDATE mail_accounts SET last_error=NULL, updated_at=? WHERE user_id=?",
                       (now_iso(), account["user_id"]))
        return added
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass


def poll_all(db: Database, vault: Vault) -> None:
    for acc in db.query("SELECT * FROM mail_accounts WHERE enabled=1"):
        try:
            fetch_new(db, vault, acc)
        except Exception as e:  # noqa: BLE001 - 한 사람 오류가 전체를 막지 않게
            msg = str(e)[:300]
            db.execute("UPDATE mail_accounts SET last_error=?, updated_at=? WHERE user_id=?",
                       (msg, now_iso(), acc["user_id"]))
            db.log("error", f"mail user {acc['user_id']}: {msg}")


def today_start() -> str:
    return datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
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
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth, mail, qa, writing
from .alio import AlioClient, AlioCollector, AlioConfig, finance_overview, parse_tables
from .articles import ArticleCollector
from .config import KST, Settings
from .dart import VIEW_URL, Collector, DartClient, DartLimitReached
from .db import Database, now, now_iso
from .llm import LLM, LLMError
from .push import Pusher, payload_for, recipients
from .rules import RED, Rules

log = logging.getLogger(__name__)
STATIC = Path(__file__).resolve().parent / "static"
COOKIE = "nb_session"


# --- 입력 모델 ---------------------------------------------------------------
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


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class DraftIn(BaseModel):
    source_kind: str = Field(pattern=r"^(disclosure|mail|text)$")
    source_ref: str | None = None
    title: str = Field(default="", max_length=200)
    text: str = Field(default="", max_length=40000)
    kind: str = Field(default="스트레이트", max_length=20)


class StylebookIn(BaseModel):
    content: str = Field(min_length=10, max_length=30000)


class ReporterIn(BaseModel):
    reporter_id: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")


class MailAccountIn(BaseModel):
    host: str = Field(default="imap.gmail.com", max_length=100)
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=4, max_length=200)
    folder: str = Field(default="보도자료", min_length=1, max_length=100)


class WrittenIn(BaseModel):
    url: str = Field(default="", max_length=500)


class LimitIn(BaseModel):
    krw: int = Field(ge=0, le=10_000_000)


# --- 백그라운드 작업 ---------------------------------------------------------
class Poller:
    """DART 수집 루프."""

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
                await alert(self.settings, self.db, self.rules, self.pusher, result.new)
        except DartLimitReached as e:
            self.db.set("dart_status", f"호출 한도 도달 ({e}) - 내일 다시 시작")
            self.db.log("error", str(e))
        except Exception as e:  # noqa: BLE001 - 루프가 죽지 않게 모두 기록
            fails = int(self.db.get("dart_fail_count", "0") or 0) + 1
            self.db.set("dart_fail_count", str(fails))
            self.db.set("dart_status", f"오류 {fails}회 연속: {e}")
            self.db.log("error", f"poll: {e!r}")
            log.exception("poll failed")


async def alert(settings: Settings, db: Database, rules: Rules, pusher: Pusher, rows: list[dict]) -> None:
    if not settings.notify_enabled:
        return
    for row in rows:
        if row["level"] != RED or row["is_correction"]:
            continue
        payload = payload_for(row, settings.public_url)
        for user_id in recipients(db, rules, row):
            sent = await asyncio.to_thread(pusher.send_to_user, user_id, payload)
            db.log("alert", f"{row['rcept_no']} -> user {user_id} ({sent} devices)")


async def alio_loop(settings: Settings, db: Database, rules: Rules, pusher: Pusher, collector: AlioCollector):
    while True:
        try:
            new = await collector.poll()
            db.set("alio_status", "정상")
            db.log("alio", f"new={len(new)}")
            await alert(settings, db, rules, pusher, new)
        except Exception as e:  # noqa: BLE001
            hint = " (SSL 오류면 .env 에 ALIO_VERIFY_SSL=false)" if "SSL" in repr(e) or "certificate" in repr(e) else ""
            db.set("alio_status", f"오류: {e}{hint}")
            db.log("error", f"alio: {e!r}")
            log.exception("alio poll failed")
        await asyncio.sleep(settings.alio_poll_hours * 3600)


async def mail_loop(settings: Settings, db: Database, vault: mail.Vault):
    while True:
        await asyncio.to_thread(mail.poll_all, db, vault)
        await asyncio.sleep(settings.mail_poll_minutes * 60)


async def digest_loop(settings: Settings, db: Database, llm: LLM):
    while True:
        t = now()
        for hhmm in settings.digest_times:
            h, m = (int(x) for x in hhmm.split(":"))
            due = t.replace(hour=h, minute=m, second=0, microsecond=0)
            slot = due.strftime("%Y-%m-%d ") + hhmm
            if due <= t < due + timedelta(minutes=30) and not db.one("SELECT 1 FROM briefings WHERE slot=?", (slot,)):
                prev = db.one("SELECT created_at FROM briefings ORDER BY id DESC LIMIT 1")
                since = prev["created_at"] if prev else (t - timedelta(hours=12)).isoformat(timespec="seconds")
                await asyncio.to_thread(qa.make_digest, db, llm, slot, since)
        await asyncio.sleep(60)


# --- 앱 ---------------------------------------------------------------------
def create_app(settings: Settings, db: Database | None = None, start_poller: bool = True,
               llm: LLM | None = None) -> FastAPI:
    db = db or Database(settings.db_path)
    rules = Rules.load(settings.rules_path)
    pusher = Pusher(db, settings.data_dir, settings.vapid_contact, settings.notify_enabled)
    limiter = auth.LoginLimiter()
    poller = Poller(settings, db, rules, pusher)
    llm = llm or LLM(settings, db)
    vault = mail.Vault(settings.data_dir)
    alio_cfg = AlioConfig.load(settings.alio_path) if settings.alio_path.exists() else AlioConfig()
    alio_client = AlioClient(verify=settings.alio_verify_ssl)
    alio_collector = AlioCollector(alio_client, db, alio_cfg)
    articles = ArticleCollector(db, settings.docdoc_base)
    jobs: dict[str, asyncio.Task] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tasks = []
        if start_poller:
            tasks.append(asyncio.create_task(poller.run_forever()))
            tasks.append(asyncio.create_task(digest_loop(settings, db, llm)))
            if settings.alio_enabled:
                tasks.append(asyncio.create_task(alio_loop(settings, db, rules, pusher, alio_collector)))
            if settings.mail_enabled:
                tasks.append(asyncio.create_task(mail_loop(settings, db, vault)))
        yield
        for t in tasks + list(jobs.values()):
            t.cancel()

    app = FastAPI(title="청년의사 브리핑", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.db, app.state.settings, app.state.poller, app.state.pusher = db, settings, poller, pusher
    app.state.llm, app.state.alio = llm, alio_collector

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

    @app.exception_handler(LLMError)
    async def llm_error(_: Request, exc: LLMError):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    # --- 인증 -----------------------------------------------------------
    def current_user(request: Request) -> dict:
        user = auth.session_user(db, request.cookies.get(COOKIE))
        if not user:
            raise HTTPException(401, "로그인이 필요합니다.")
        full = db.one("SELECT reporter_id, monthly_limit_krw FROM users WHERE id=?", (user["id"],))
        return {**user, **(full or {})}

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
        articles_n = db.one("SELECT COUNT(*) n FROM articles WHERE author_id=?",
                            ((user.get("reporter_id") or "").lower(),))["n"]
        sb = db.one("SELECT updated_at, source_count FROM stylebooks WHERE user_id=?", (user["id"],))
        acc = db.one("SELECT host, username, folder, enabled, last_error, updated_at FROM mail_accounts WHERE user_id=?",
                     (user["id"],))
        return {**user, "subscriptions": subs, "push_devices": devices, "alert_mode": settings.alert_mode,
                "llm_ready": llm.available, "llm_provider": settings.llm_provider,
                "mail_enabled": settings.mail_enabled, "mail_account": acc,
                "my_articles": articles_n, "stylebook": sb,
                "spent_krw": round(llm.month_spent(user["id"])), "limit_krw": llm.limit_for(user["id"])}

    @app.post("/api/me/reporter")
    def set_reporter(body: ReporterIn, user: dict = Depends(current_user)):
        db.execute("UPDATE users SET reporter_id=? WHERE id=?", (body.reporter_id.lower(), user["id"]))
        return {"ok": True}

    # --- 피드 -----------------------------------------------------------
    def _decorate(rows: list[dict]) -> list[dict]:
        for r in rows:
            r["url"] = r.get("link") or VIEW_URL.format(rcept_no=r["rcept_no"])
        return rows

    FEED_SELECT = """SELECT d.*, c.user_id AS claimed_by, u.display_name AS claimed_name, c.written_url, c.written_at
                     FROM disclosures d LEFT JOIN claims c ON c.rcept_no=d.rcept_no
                     LEFT JOIN users u ON u.id=c.user_id"""

    @app.get("/api/feed")
    def feed(level: str = "", q: str = "", watched: int = 0, mine: int = 0, include_gray: int = 0,
             source: str = "", before: str = "", limit: int = 50, user: dict = Depends(current_user)):
        sql = [FEED_SELECT, "WHERE 1=1"]
        params: list = []
        if level in ("red", "yellow", "gray"):
            sql.append("AND d.level=?")
            params.append(level)
        elif not include_gray:
            sql.append("AND d.level!='gray'")
        if source in ("dart", "alio"):
            sql.append("AND d.source=?")
            params.append(source)
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
        top = _decorate(db.query(FEED_SELECT + """ WHERE d.first_seen_at >= ? AND d.level='red' AND d.is_correction=0
                                                   ORDER BY d.watched DESC, d.first_seen_at DESC LIMIT 5""", (since,)))
        mine = db.one("SELECT COUNT(*) n FROM claims WHERE user_id=? AND claimed_at >= ?", (user["id"], since))["n"]
        mails_today = db.one("SELECT COUNT(*) n FROM mails WHERE user_id=? AND first_seen_at >= ?",
                             (user["id"], since))["n"] if settings.mail_enabled else None
        brief = db.one("SELECT slot, content, model, created_at FROM briefings ORDER BY id DESC LIMIT 1")
        return {
            "date": now().strftime("%Y-%m-%d"),
            "red": counts.get("red", 0), "yellow": counts.get("yellow", 0), "gray": counts.get("gray", 0),
            "top": top, "unclaimed_top": sum(1 for t in top if not t["claimed_by"]), "my_claims": mine,
            "mails_today": mails_today, "briefing": brief,
            "last_poll_at": db.get("last_poll_at"), "dart_status": db.get("dart_status", "대기 중"),
            "alio_status": db.get("alio_status", "대기 중") if settings.alio_enabled else "꺼짐",
            "alert_mode": settings.alert_mode,
        }

    @app.get("/api/disclosures/{rcept_no:path}")
    def disclosure(rcept_no: str, user: dict = Depends(current_user)):
        rows = _decorate(db.query(FEED_SELECT.replace("c.written_at", "c.written_at, c.claimed_at")
                                  + " WHERE d.rcept_no=?", (rcept_no,)))
        if not rows:
            raise HTTPException(404, "없는 공시입니다.")
        return rows[0]

    @app.post("/api/claims/{rcept_no:path}/written")
    def mark_written(rcept_no: str, body: WrittenIn, user: dict = Depends(current_user)):
        n = db.execute("UPDATE claims SET written_url=?, written_at=? WHERE rcept_no=? AND user_id=?",
                       (body.url.strip() or None, now_iso(), rcept_no, user["id"]))
        if not n:
            raise HTTPException(400, "먼저 '내가 쓸게요'로 맡아 주세요.")
        return {"ok": True}

    @app.post("/api/claims/{rcept_no:path}")
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

    @app.delete("/api/claims/{rcept_no:path}")
    def unclaim(rcept_no: str, user: dict = Depends(current_user)):
        db.execute("DELETE FROM claims WHERE rcept_no=? AND user_id=?", (rcept_no, user["id"]))
        return {"ok": True}

    # --- 질문 -----------------------------------------------------------
    @app.post("/api/ask")
    async def ask(body: AskIn, user: dict = Depends(current_user)):
        loop = asyncio.get_running_loop()
        return await asyncio.to_thread(qa.ask, settings, db, llm, user, body.question.strip(),
                                       poller.client if settings.dart_api_key else None, loop)

    @app.get("/api/chats")
    def chats(user: dict = Depends(current_user)):
        rows = db.query("SELECT id, question, answer, trace_json, model, created_at FROM chats WHERE user_id=? "
                        "ORDER BY id DESC LIMIT 30", (user["id"],))
        for r in rows:
            r["trace"] = [{"tool": t["tool"], "input": t["input"]} for t in json.loads(r.pop("trace_json"))]
        return {"items": rows}

    # --- 초안 -----------------------------------------------------------
    @app.post("/api/drafts")
    async def create_draft(body: DraftIn, user: dict = Depends(current_user)):
        title, text, ref = body.title.strip(), body.text.strip(), body.source_ref
        if body.source_kind == "disclosure":
            d = db.one("SELECT * FROM disclosures WHERE rcept_no=?", (ref or "",))
            if not d:
                raise HTTPException(404, "없는 공시입니다.")
            title = f"{d['corp_name']} {d['report_nm']}"
            meta = f"회사/기관: {d['corp_name']}\n공시 제목: {d['report_nm']}\n접수일: {d['rcept_dt']}\n"
            doc = ""
            try:
                if d.get("source", "dart") == "dart" and settings.dart_api_key:
                    doc = await poller.client.document_text(d["rcept_no"])
                elif d.get("source") == "alio" and d.get("link") and "disclosureNo=" in d["link"]:
                    html = await alio_client.report_html(d["link"].split("disclosureNo=")[1])
                    doc = "\n".join(" | ".join(r) for t in parse_tables(html) for r in t)[:15000]
            except Exception as e:  # noqa: BLE001
                db.log("error", f"draft source {ref}: {e!r}")
            if not doc and not text:
                raise HTTPException(400, "공시 원문을 가져오지 못했어요(DART 키·연결 확인). 보도자료나 메모를 붙여 넣으면 함께 씁니다.")
            text = meta + (f"\n원문:\n{doc}" if doc else "") + (f"\n\n기자 메모:\n{text}" if text else "")
        elif body.source_kind == "mail":
            m = db.one("SELECT * FROM mails WHERE id=? AND user_id=?", (int(ref or 0), user["id"]))
            if not m:
                raise HTTPException(404, "없는 메일입니다.")
            if not settings.mail_ai_summary:
                raise HTTPException(400, "메일 본문을 AI로 보내는 기능은 법무 검토 후 관리자가 켭니다.")
            title, text = m["subject"], f"보낸 사람: {m['sender']}\n{m['body']}"
        if not title:
            title = text.split("\n", 1)[0][:80]
        return await asyncio.to_thread(writing.make_draft, db, llm, user, body.source_kind, ref, title, text, body.kind)

    @app.get("/api/drafts")
    def drafts(user: dict = Depends(current_user)):
        return {"items": db.query("SELECT id, source_kind, source_ref, source_title, model, created_at FROM drafts "
                                  "WHERE user_id=? ORDER BY id DESC LIMIT 50", (user["id"],))}

    @app.get("/api/drafts/{draft_id}")
    def draft(draft_id: int, user: dict = Depends(current_user)):
        d = db.one("SELECT * FROM drafts WHERE id=? AND user_id=?", (draft_id, user["id"]))
        if not d:
            raise HTTPException(404, "없는 초안입니다.")
        d["checks"] = json.loads(d.pop("checks_json"))
        d["examples"] = json.loads(d.pop("examples_json"))
        return d

    # --- 스타일북·자사 기사 ------------------------------------------------
    @app.get("/api/stylebook")
    def get_stylebook(user: dict = Depends(current_user)):
        return db.one("SELECT content, source_count, model, updated_at FROM stylebooks WHERE user_id=?",
                      (user["id"],)) or {"content": "", "source_count": 0}

    @app.put("/api/stylebook")
    def put_stylebook(body: StylebookIn, user: dict = Depends(current_user)):
        db.execute("""INSERT INTO stylebooks(user_id, content, source_count, model, updated_at) VALUES(?,?,0,'직접 수정',?)
                      ON CONFLICT(user_id) DO UPDATE SET content=excluded.content, model='직접 수정',
                      updated_at=excluded.updated_at""", (user["id"], body.content, now_iso()))
        return {"ok": True}

    @app.post("/api/stylebook/build")
    async def build_stylebook(user: dict = Depends(current_user)):
        return await asyncio.to_thread(writing.build_stylebook, db, llm, user)

    @app.post("/api/articles/collect")
    async def collect_articles(user: dict = Depends(current_user)):
        rid = (user.get("reporter_id") or "").strip()
        if not rid:
            raise HTTPException(400, "설정에서 기자 ID(이메일 앞부분)를 먼저 입력해 주세요.")
        key = f"articles:{user['id']}"
        if key in jobs and not jobs[key].done():
            return {"started": False, "message": "이미 가져오는 중이에요."}

        async def job():
            db.set(key, json.dumps({"state": "running", "added": 0, "checked": 0, "at": now_iso()}))
            try:
                res = await articles.collect_reporter(
                    rid, progress=lambda p, a, c: db.set(key, json.dumps(
                        {"state": "running", "page": p, "added": a, "checked": c, "at": now_iso()})))
                db.set(key, json.dumps({"state": "done", **res, "at": now_iso()}))
            except Exception as e:  # noqa: BLE001
                db.set(key, json.dumps({"state": "error", "error": str(e)[:300], "at": now_iso()}))
                db.log("error", f"articles {rid}: {e!r}")

        jobs[key] = asyncio.create_task(job())
        return {"started": True}

    @app.get("/api/articles/status")
    def articles_status(user: dict = Depends(current_user)):
        raw = db.get(f"articles:{user['id']}")
        n = db.one("SELECT COUNT(*) n FROM articles WHERE author_id=?", ((user.get("reporter_id") or "").lower(),))["n"]
        return {"job": json.loads(raw) if raw else None, "count": n}

    # --- 알리오 ---------------------------------------------------------
    @app.get("/api/alio")
    def alio_view(user: dict = Depends(current_user)):
        return {
            "enabled": settings.alio_enabled, "status": db.get("alio_status", "대기 중"),
            "last_poll_at": db.get("alio_last_poll_at"),
            "orgs": db.query("SELECT apba_id, name, inst_type, dept FROM alio_orgs ORDER BY name"),
            "missing": json.loads(db.get("alio_missing", "[]") or "[]"),
            "finance": finance_overview(db),
        }

    # --- 메일 -----------------------------------------------------------
    def _mail_on():
        if not settings.mail_enabled:
            raise HTTPException(400, "메일 기능은 법무·IT 검토 후 관리자가 켭니다 (.env 의 MAIL_ENABLED).")

    @app.get("/api/mail")
    def mails(q: str = "", user: dict = Depends(current_user)):
        _mail_on()
        sql = "SELECT id, sender, subject, sent_at, embargo, summary, first_seen_at FROM mails WHERE user_id=?"
        params: list = [user["id"]]
        if q:
            sql += " AND (subject LIKE ? OR sender LIKE ?)"
            params += [f"%{q}%", f"%{q}%"]
        return {"items": db.query(sql + " ORDER BY first_seen_at DESC LIMIT 100", tuple(params))}

    @app.get("/api/mail/{mail_id}")
    def mail_one(mail_id: int, user: dict = Depends(current_user)):
        _mail_on()
        m = db.one("SELECT * FROM mails WHERE id=? AND user_id=?", (mail_id, user["id"]))
        if not m:
            raise HTTPException(404, "없는 메일입니다.")
        return m

    @app.put("/api/mail/account")
    async def mail_account(body: MailAccountIn, user: dict = Depends(current_user)):
        _mail_on()
        acc = {"user_id": user["id"], "host": body.host.strip(), "username": body.username.strip(),
               "secret_enc": vault.seal(body.password), "folder": body.folder.strip(), "last_uid": 0,
               "updated_at": now_iso()}
        try:  # 저장 전에 접속 확인
            await asyncio.to_thread(_probe_mail, acc)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"메일 접속 실패: {e}") from e
        db.execute("""INSERT INTO mail_accounts(user_id, host, username, secret_enc, folder, enabled, last_uid, updated_at)
                      VALUES(:user_id,:host,:username,:secret_enc,:folder,1,0,:updated_at)
                      ON CONFLICT(user_id) DO UPDATE SET host=excluded.host, username=excluded.username,
                      secret_enc=excluded.secret_enc, folder=excluded.folder, enabled=1, last_uid=0,
                      last_error=NULL, updated_at=excluded.updated_at""", acc)
        asyncio.create_task(asyncio.to_thread(mail.poll_all, db, vault))
        return {"ok": True}

    def _probe_mail(acc: dict) -> None:
        import imaplib

        imap = imaplib.IMAP4_SSL(acc["host"])
        try:
            imap.login(acc["username"], vault.open(acc["secret_enc"]))
            status, _ = imap.select(f'"{acc["folder"]}"', readonly=True)
            if status != "OK":
                raise RuntimeError(f"메일함 '{acc['folder']}'이 없습니다")
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass

    @app.delete("/api/mail/account")
    def mail_disconnect(user: dict = Depends(current_user)):
        db.execute("DELETE FROM mail_accounts WHERE user_id=?", (user["id"],))
        db.execute("DELETE FROM mails WHERE user_id=?", (user["id"],))
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
        rows = db.query("SELECT id, username, display_name, role, active, reporter_id, monthly_limit_krw, created_at "
                        "FROM users ORDER BY id")
        for r in rows:
            r["spent_krw"] = round(llm.month_spent(r["id"]))
            r["limit_krw"] = llm.limit_for(r["id"])
        return {"users": rows}

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

    @app.post("/api/admin/users/{user_id}/limit")
    def admin_limit(user_id: int, body: LimitIn, user: dict = Depends(admin_user)):
        db.execute("UPDATE users SET monthly_limit_krw=? WHERE id=?", (body.krw, user_id))
        return {"ok": True}

    @app.get("/api/admin/status")
    def admin_status(user: dict = Depends(admin_user)):
        return {
            "dart_status": db.get("dart_status", "대기 중"),
            "last_poll_at": db.get("last_poll_at"),
            "dart_calls_today": poller.client.calls_today(),
            "alio_status": db.get("alio_status", "대기 중") if settings.alio_enabled else "꺼짐",
            "alio_last_poll_at": db.get("alio_last_poll_at"),
            "llm": f"{settings.llm_provider} (준비됨)" if llm.available else "키 없음",
            "mail": "켜짐" if settings.mail_enabled else "꺼짐 (법무 검토 후)",
            "alert_mode": settings.alert_mode,
            "events": db.query("SELECT at, kind, detail FROM events ORDER BY id DESC LIMIT 50"),
        }

    @app.get("/api/admin/metrics")
    def admin_metrics(days: int = 30, user: dict = Depends(admin_user)):
        since = (now() - timedelta(days=max(1, min(days, 365)))).isoformat(timespec="seconds")
        per_user = db.query(
            """SELECT u.id, u.display_name,
                 (SELECT COUNT(*) FROM claims c WHERE c.user_id=u.id AND c.claimed_at>=?) claims,
                 (SELECT COUNT(*) FROM claims c WHERE c.user_id=u.id AND c.written_at>=?) written,
                 (SELECT COUNT(*) FROM chats h WHERE h.user_id=u.id AND h.created_at>=?) questions,
                 (SELECT COUNT(*) FROM drafts d WHERE d.user_id=u.id AND d.created_at>=?) drafts,
                 (SELECT COALESCE(SUM(cost_krw),0) FROM llm_usage l WHERE l.user_id=u.id AND l.at>=?) cost_krw
               FROM users u WHERE u.active=1 ORDER BY u.id""", (since,) * 5)
        totals = {
            "disclosures": db.one("SELECT COUNT(*) n FROM disclosures WHERE first_seen_at>=?", (since,))["n"],
            "red": db.one("SELECT COUNT(*) n FROM disclosures WHERE first_seen_at>=? AND level='red'", (since,))["n"],
            "alerts": db.one("SELECT COUNT(*) n FROM events WHERE kind='alert' AND at>=?", (since,))["n"],
            "poll_errors": db.one("SELECT COUNT(*) n FROM events WHERE kind='error' AND at>=?", (since,))["n"],
            "polls": db.one("SELECT COUNT(*) n FROM events WHERE kind='poll' AND at>=?", (since,))["n"],
            "cost_krw": round(db.one("SELECT COALESCE(SUM(cost_krw),0) s FROM llm_usage WHERE at>=?", (since,))["s"]),
        }
        expected = days * 86400 / settings.poll_interval_sec
        totals["uptime_pct"] = round(min(100.0, totals["polls"] / expected * 100), 1) if settings.dart_api_key else None
        for r in per_user:
            r["cost_krw"] = round(r["cost_krw"])
        return {"days": days, "totals": totals, "users": per_user}

    @app.get("/healthz")
    def healthz():
        """외부 감시 서비스용. 마지막 수집이 너무 오래되면 503."""
        last = db.get("last_poll_at")
        if settings.dart_api_key and last:
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


__all__ = ["create_app", "Poller", "KST"]
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
        <a href="#ask" data-view="ask" class="nav-item"><span aria-hidden="true">?</span>질문</a>
        <a href="#draft" data-view="draft" class="nav-item"><span aria-hidden="true">✎</span>기사 초안</a>
        <a href="#mail" data-view="mail" class="nav-item"><span aria-hidden="true">✉</span>보도자료 메일</a>
        <a href="#alio" data-view="alio" class="nav-item"><span aria-hidden="true">▤</span>알리오·결산</a>
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
        <button class="chip" data-source="alio" aria-pressed="false">알리오</button>
      </div>
      <button id="push-btn" class="btn primary small" type="button" hidden>PC·폰 알림 켜기</button>
    </header>

    <main id="main" class="main" tabindex="-1">
      <!-- 피드 -->
      <section id="view-feed" class="view">
        <div id="mode-banner" class="banner" hidden></div>
        <div class="bento" id="briefing" aria-live="polite"></div>
        <div id="digest" class="card digest" hidden></div>
        <div class="feed-head">
          <h2 id="feed-title">오늘의 피드</h2>
          <span class="muted small kbd-hint">J/K 이동 · Enter 열기 · C 담당 · / 검색</span>
        </div>
        <ul id="feed" class="feed" role="listbox" aria-label="공시 목록"></ul>
        <button id="more-btn" class="btn ghost" type="button" hidden>더 보기</button>
        <p id="empty" class="empty" hidden></p>
      </section>

      <!-- 질문 -->
      <section id="view-ask" class="view" hidden>
        <h2>질문</h2>
        <p class="muted small">수집된 공시·알리오 결산·과거 기사(메일 기능이 켜지면 내 보도자료 메일)에서 찾아 출처와 함께 답합니다. 답의 숫자는 꼭 원문으로 확인하세요.</p>
        <div id="chat" class="chat" aria-live="polite"></div>
      </section>

      <!-- 기사 초안 -->
      <section id="view-draft" class="view" hidden>
        <h2>기사 초안</h2>
        <div class="card stack">
          <h3>원자료</h3>
          <p id="draft-source" class="muted small">보도자료나 메모를 붙여 넣거나, 피드의 공시 상세에서 [기사 초안]을 누르세요.</p>
          <form id="draft-form" class="stack">
            <input name="title" placeholder="제목 (선택)" maxlength="200" aria-label="원자료 제목">
            <textarea name="text" rows="8" placeholder="보도자료 본문, 취재 메모 등" aria-label="원자료 본문"></textarea>
            <div class="row">
              <select name="kind" aria-label="기사 유형"><option>스트레이트</option><option>해설</option><option>단신</option></select>
              <button class="btn primary" type="submit">초안 쓰기</button>
              <span id="draft-busy" class="muted small" hidden>쓰는 중… (30초~1분)</span>
            </div>
          </form>
        </div>
        <div id="draft-result" class="card stack" hidden>
          <div class="row between"><h3>초안 <span class="badge fix">AI 작성 · 출고 전 검수</span></h3>
            <button id="draft-copy" class="btn" type="button">복사</button></div>
          <textarea id="draft-text" rows="16" aria-label="초안"></textarea>
          <div id="draft-checks"></div>
          <div id="draft-examples" class="muted small"></div>
        </div>
        <div class="card stack"><h3>지난 초안</h3><ul id="draft-list" class="plain-list"></ul></div>
      </section>

      <!-- 메일 -->
      <section id="view-mail" class="view" hidden>
        <h2>보도자료 메일</h2>
        <p id="mail-off" class="banner" hidden>메일 기능은 개인정보 국외 이전 등 법무·IT 검토 후 관리자가 켭니다.</p>
        <div id="mail-wrap" class="stack">
          <p class="muted small">본인이 지정한 메일함만 읽기 전용으로 가져옵니다. 다른 사람은 볼 수 없습니다. 연결은 '내 설정'에서 합니다.</p>
          <ul id="mail-list" class="feed"></ul>
          <div id="mail-detail" class="card stack" hidden></div>
        </div>
      </section>

      <!-- 알리오 -->
      <section id="view-alio" class="view" hidden>
        <h2>알리오 · 공공기관 결산</h2>
        <p id="alio-status" class="muted small"></p>
        <div id="alio-finance" class="stack"></div>
        <div class="card stack"><h3>감시 기관</h3><p id="alio-orgs" class="small"></p><p id="alio-missing" class="error small"></p></div>
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
          <h3>내 기사와 스타일북</h3>
          <p class="muted small">청년의사 기자 ID(이메일 @ 앞부분)를 넣고 내 기사를 가져오면, AI가 문체를 분석해 스타일북을 만듭니다. 스타일북은 직접 고칠 수 있고 초안에 쓰입니다.</p>
          <form id="reporter-form" class="row">
            <input name="reporter_id" placeholder="예: soo331" pattern="[A-Za-z0-9._-]{2,40}" aria-label="기자 ID" required>
            <button class="btn" type="submit">저장</button>
            <button id="articles-btn" class="btn" type="button">내 기사 가져오기</button>
          </form>
          <p id="articles-state" class="muted small"></p>
          <div class="row"><button id="stylebook-build" class="btn primary" type="button">스타일북 만들기 (AI)</button>
            <span id="stylebook-meta" class="muted small"></span></div>
          <textarea id="stylebook" rows="10" placeholder="스타일북이 여기에 표시됩니다. 직접 써도 됩니다." aria-label="스타일북"></textarea>
          <div class="row"><button id="stylebook-save" class="btn" type="button">스타일북 저장</button></div>
        </div>
        <div id="mail-settings" class="card stack">
          <h3>보도자료 메일 연결</h3>
          <p id="mail-account-state" class="muted small"></p>
          <form id="mail-form" class="stack">
            <div class="row">
              <input name="host" value="imap.gmail.com" aria-label="IMAP 서버">
              <input name="username" placeholder="메일 주소" aria-label="메일 주소" required>
            </div>
            <div class="row">
              <input name="password" type="password" placeholder="앱 비밀번호" aria-label="앱 비밀번호" required autocomplete="off">
              <input name="folder" value="보도자료" aria-label="메일함(라벨) 이름">
              <button class="btn" type="submit">연결</button>
              <button id="mail-disconnect" class="btn ghost" type="button">연결 해제</button>
            </div>
          </form>
          <p class="muted small">Gmail은 2단계 인증을 켠 뒤 '앱 비밀번호'를 만들어 넣습니다. 비밀번호는 암호화해 저장하고, 지정한 라벨 하나만 읽습니다.</p>
        </div>
        <div class="card stack">
          <h3>AI 사용량</h3>
          <p id="usage" class="muted small"></p>
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
          <h3>시범사업 성과 (최근 30일)</h3>
          <dl id="metrics-totals" class="kv"></dl>
          <table class="table"><thead><tr><th>기자</th><th>담당</th><th>기사화</th><th>질문</th><th>초안</th><th>AI 비용</th></tr></thead>
            <tbody id="metrics-users"></tbody></table>
        </div>
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
          <table class="table"><thead><tr><th>이름</th><th>아이디</th><th>권한</th><th>이번 달 AI</th><th>상태</th><th></th></tr></thead>
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
      <input id="ask-input" placeholder="질문하기 (Ctrl+K) · 예: 오늘 기술이전 공시 있어?" aria-label="질문" maxlength="2000">
      <button class="btn primary" type="submit">묻기</button>
    </form>

    <nav class="tabbar" aria-label="하단 메뉴">
      <a href="#feed" data-view="feed">피드</a>
      <a href="#mine" data-view="mine">담당</a>
      <a href="#ask" data-view="ask">질문</a>
      <a href="#draft" data-view="draft">초안</a>
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
  filter: { level: "", watched: 0, q: "", source: "" },
  draftSource: null,
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
  if (item.source === "alio") wrap.append(el("span", { class: "badge src", text: "알리오" }));
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
  $("#ask").hidden = !["feed", "ask"].includes(section);
  if (section === "feed") {
    $("#feed-title").textContent = view === "mine" ? "내가 맡은 건" : "오늘의 피드";
    $("#briefing").hidden = view === "mine";
    loadFeed(true);
  }
  if (view === "settings") renderSettings();
  if (view === "admin") renderAdmin();
  if (view === "ask") renderChats();
  if (view === "draft") renderDrafts();
  if (view === "mail") renderMail();
  if (view === "alio") renderAlio();
}

function route() {
  const h = location.hash.slice(1);
  if (h.startsWith("join/")) return showAuth(h.slice(5));
  if (!state.me) return;
  if (h.startsWith("d/")) {
    if (state.view !== "feed") setView("feed");
    return openDetail(decodeURIComponent(h.slice(2)));
  }
  if (h.startsWith("draft/")) {
    const [kind, ...rest] = h.slice(6).split("/");
    state.draftSource = { kind: kind === "m" ? "mail" : "disclosure", ref: decodeURIComponent(rest.join("/")) };
    closeDetail();
    return setView("draft");
  }
  if (h === "draft") state.draftSource = null; // 메뉴로 들어오면 붙여 넣기 모드
  setView(["feed", "mine", "settings", "admin", "ask", "draft", "mail", "alio"].includes(h) ? h : "feed");
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
  const dg = $("#digest");
  dg.hidden = !s.briefing || state.view === "mine";
  if (s.briefing) {
    dg.replaceChildren(el("div", { class: "label", text: `정기 브리핑 · ${s.briefing.slot}${s.briefing.model ? " · AI 요약" : ""}` }),
      el("div", { text: s.briefing.content }));
  }
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
  if (state.filter.source) p.set("source", state.filter.source);
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
  if (chip.dataset.source !== undefined) {
    state.filter.source = state.filter.source ? "" : chip.dataset.source;
    chip.setAttribute("aria-pressed", state.filter.source ? "true" : "false");
  } else if (chip.dataset.watched !== undefined) {
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
  const writtenBtn = mine
    ? el("button", { class: "btn", type: "button", text: d.written_at ? "✓ 기사화 기록됨" : "기사 썼어요",
        onclick: async () => {
          const url = prompt("쓴 기사 주소가 있으면 붙여 넣으세요 (없으면 비워 두기)", d.written_url || "") ?? null;
          if (url === null) return;
          try { await api(`/api/claims/${encodeURIComponent(d.rcept_no)}/written`, { method: "POST", body: { url } });
            toast("기사화로 기록했어요. 시범사업 성과에 반영됩니다."); openDetail(d.rcept_no); } catch (err) { toast(err.message); }
        } })
    : null;
  const claimBtn = d.claimed_by && !mine
    ? el("button", { class: "btn", type: "button", disabled: true, text: `${d.claimed_name} 기자가 맡음` })
    : el("button", { class: mine ? "btn" : "btn primary", type: "button", onclick: toggleClaim, text: mine ? "맡기 취소" : "내가 쓸게요 (C)" });
  $("#detail .detail-inner").replaceChildren(
    el("div", { class: "row", style: "justify-content:space-between" }, badge(d),
      el("button", { class: "btn ghost small", type: "button", onclick: closeDetail, "aria-label": "닫기", text: "닫기 (Esc)" })),
    el("div", {}, el("div", { class: "muted small", text: d.source === "alio" ? "알리오 · 공공기관" : d.watched ? "★ 감시 기업" : "보건의료 업종" }), el("h2", { text: d.corp_name })),
    el("p", { style: "margin:0;font-weight:600", text: d.report_nm }),
    el("a", { class: "source", href: d.url, target: "_blank", rel: "noopener noreferrer" }, d.source === "alio" ? "알리오 원문 열기" : "DART 원문 열기", el("span", { "aria-hidden": "true", text: "↗" })),
    el("dl", { class: "kv" },
      el("dt", { text: "접수일" }), el("dd", { text: fmtDate(d.rcept_dt) }),
      el("dt", { text: "접수번호" }), el("dd", { text: d.rcept_no }),
      el("dt", { text: "제출인" }), el("dd", { text: d.flr_nm || "-" }),
      el("dt", { text: "비고" }), el("dd", { text: d.rm || "-" }),
      el("dt", { text: "분류 근거" }), el("dd", { text: d.keyword ? `제목에 '${d.keyword}' 포함` : "키워드 없음 (일반)" }),
      el("dt", { text: "처음 확인" }), el("dd", { text: fmtSeen(d.first_seen_at) + (d.source === "alio" ? "" : " · DART 공개는 제출 후 약 15분 뒤") })),
    el("div", { class: "row" }, claimBtn, writtenBtn,
      el("button", { class: "btn", type: "button", text: "기사 초안",
        title: state.me.llm_ready ? "이 공시로 초안 쓰기" : "AI API 키가 연결되면 켜집니다",
        disabled: !state.me.llm_ready, onclick: () => (location.hash = `#draft/d/${encodeURIComponent(d.rcept_no)}`) })),
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
  if (typing || !["feed", "mine"].includes(state.view)) return;
  if (e.key === "/") { e.preventDefault(); $("#search").focus(); }
  else if (e.key === "j") select(Math.min(state.selected + 1, state.items.length - 1), false);
  else if (e.key === "k") select(Math.max(state.selected - 1, 0), false);
  else if (e.key === "Enter" && state.selected >= 0) select(state.selected, true);
  else if (e.key === "c" && (state.detail || state.selected >= 0)) toggleClaim();
});

// ---------- 질문창 ----------
$("#ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#ask-input");
  const q = input.value.trim();
  if (!q) return;
  if (!state.me.llm_ready) { toast("AI API 키가 연결되면 질문할 수 있어요."); return; }
  if (state.view !== "ask") location.hash = "#ask";
  input.value = "";
  input.disabled = true;
  const pending = el("div", { class: "bubble a", text: "자료를 찾아보는 중…" });
  $("#chat").append(el("div", { class: "bubble q", text: q }), pending);
  pending.scrollIntoView({ block: "end" });
  try {
    const r = await api("/api/ask", { method: "POST", body: { question: q } });
    pending.replaceWith(answerBubble(r.answer, r.trace));
  } catch (err) {
    pending.textContent = err.message;
  } finally {
    input.disabled = false;
    input.focus();
  }
});

const TOOL_NAMES = { search_disclosures: "공시 검색", get_disclosure: "공시 원문", company_financials: "DART 재무",
  alio_finance: "알리오 결산", search_newsroom_articles: "기사 검색", search_my_mail: "내 메일" };

function linkify(text) {
  // URL만 링크로 만들고 나머지는 글자 그대로 (innerHTML 사용 안 함)
  const frag = document.createDocumentFragment();
  let last = 0;
  for (const m of text.matchAll(/https?:\/\/[^\s)\]>]+/g)) {
    frag.append(text.slice(last, m.index));
    frag.append(el("a", { href: m[0], target: "_blank", rel: "noopener noreferrer", text: m[0] }));
    last = m.index + m[0].length;
  }
  frag.append(text.slice(last));
  return frag;
}

function answerBubble(answer, trace = []) {
  const b = el("div", { class: "bubble a" }, linkify(answer));
  if (trace.length) b.append(el("div", { class: "tools", text: "찾아본 자료: " + [...new Set(trace.map((t) => TOOL_NAMES[t.tool] || t.tool))].join(", ") }));
  return b;
}

async function renderChats() {
  const box = $("#chat");
  if (!state.me.llm_ready) {
    box.replaceChildren(el("p", { class: "banner", text: "AI API 키가 아직 연결되지 않았어요. 관리자가 .env 에 키를 넣으면 질문할 수 있어요." }));
    return;
  }
  const { items } = await api("/api/chats");
  box.replaceChildren(...items.reverse().flatMap((c) => [el("div", { class: "bubble q", text: c.question }), answerBubble(c.answer, c.trace)]));
  if (!items.length) box.append(el("p", { class: "muted", text: "예: \"이번 주 기술이전 공시 정리해줘\", \"서울대병원 작년 의료수익 전년 대비?\", \"유한양행 2025년 매출과 영업이익\"" }));
  $("#ask-input").focus();
}

// ---------- 기사 초안 ----------
async function renderDrafts() {
  const src = state.draftSource;
  const form = $("#draft-form");
  if (src) {
    let label = "";
    if (src.kind === "disclosure") {
      try { const d = await api(`/api/disclosures/${encodeURIComponent(src.ref)}`); label = `공시: ${d.corp_name} · ${d.report_nm}`; }
      catch { label = "공시"; }
      $("#draft-source").textContent = `${label} — 원문은 자동으로 가져옵니다. 취재 메모가 있으면 아래에 덧붙이세요.`;
    } else {
      $("#draft-source").textContent = "메일을 원자료로 씁니다.";
    }
    form.elements.namedItem("title").hidden = true;
  } else {
    $("#draft-source").textContent = "보도자료나 메모를 붙여 넣거나, 피드의 공시 상세에서 [기사 초안]을 누르세요.";
    form.elements.namedItem("title").hidden = false;
  }
  const { items } = await api("/api/drafts");
  $("#draft-list").replaceChildren(...items.map((d) => el("li", {},
    el("button", { type: "button", onclick: () => showDraft(d.id) }, `${fmtSeen(d.created_at)} · ${d.source_title || "(제목 없음)"}`))));
  if (!items.length) $("#draft-list").append(el("li", { class: "muted small", text: "아직 없어요." }));
}

function renderDraftResult(d) {
  $("#draft-result").hidden = false;
  $("#draft-text").value = d.draft;
  const miss = d.checks.filter((c) => !c.found);
  $("#draft-checks").replaceChildren(
    el("p", { class: "small", text: miss.length ? `원자료에서 찾지 못한 숫자 ${miss.length}개 — 반드시 확인하세요.` : "초안의 숫자는 모두 원자료에 있어요." }),
    el("ul", { class: "checks" }, d.checks.map((c) => el("li", { class: c.found ? "" : "miss", title: c.context, text: `${c.found ? "✓" : "✗"} ${c.number}` }))));
  $("#draft-examples").textContent = d.examples?.length ? "참고한 내 기사: " + d.examples.map((e) => e.title).join(" / ") : "";
  $("#draft-result").scrollIntoView({ block: "start" });
}

async function showDraft(id) {
  try { renderDraftResult(await api(`/api/drafts/${id}`)); } catch (err) { toast(err.message); }
}

$("#draft-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.me.llm_ready) { toast("AI API 키가 연결되면 초안을 쓸 수 있어요."); return; }
  const f = new FormData(e.target);
  const src = state.draftSource;
  const body = src
    ? { source_kind: src.kind, source_ref: src.ref, text: f.get("text") || "", kind: f.get("kind") }
    : { source_kind: "text", title: f.get("title") || "", text: f.get("text") || "", kind: f.get("kind") };
  $("#draft-busy").hidden = false;
  e.target.querySelector("button[type=submit]").disabled = true;
  try {
    const d = await api("/api/drafts", { method: "POST", body });
    renderDraftResult(d);
    renderDrafts();
  } catch (err) { toast(err.message); }
  finally { $("#draft-busy").hidden = true; e.target.querySelector("button[type=submit]").disabled = false; }
});
$("#draft-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("#draft-text").value); toast("초안을 복사했어요. 검수 후 CMS에 붙여 넣으세요."); }
  catch { $("#draft-text").select(); toast("Ctrl+C로 복사하세요."); }
});

// ---------- 메일 ----------
async function renderMail() {
  const off = !state.me.mail_enabled;
  $("#mail-off").hidden = !off;
  $("#mail-wrap").hidden = off;
  if (off) return;
  const { items } = await api("/api/mail");
  $("#mail-list").replaceChildren(...items.map((m) => el("li", { class: "item", onclick: () => openMail(m.id) },
    el("span", { class: "badge yellow", text: "메일" }),
    el("div", { style: "min-width:0" }, el("div", { class: "who", text: m.sender }), el("div", { class: "title", text: m.subject })),
    el("div", { class: "meta" }, m.embargo ? el("span", { class: "mail-embargo", text: "엠바고" }) : null,
      el("time", { text: fmtSeen(m.sent_at || m.first_seen_at) })))));
  if (!items.length) $("#mail-list").append(el("li", { class: "empty", text: "가져온 메일이 없어요. '내 설정'에서 메일을 연결하세요." }));
}

async function openMail(id) {
  const m = await api(`/api/mail/${id}`);
  const box = $("#mail-detail");
  box.hidden = false;
  box.replaceChildren(
    el("div", { class: "muted small", text: `${m.sender} · ${fmtSeen(m.sent_at)}` }), el("h3", { text: m.subject }),
    m.embargo ? el("p", { class: "mail-embargo", text: m.embargo }) : null,
    el("div", { class: "pre", text: m.body }),
    el("div", { class: "row" }, el("button", { class: "btn", type: "button", text: "이 메일로 초안",
      onclick: () => (location.hash = `#draft/m/${m.id}`) })));
  box.scrollIntoView({ block: "start" });
}

// ---------- 알리오 ----------
const won = (v) => (v == null ? "-" : Math.round(v).toLocaleString("ko-KR"));
async function renderAlio() {
  const a = await api("/api/alio");
  $("#alio-status").textContent = a.enabled ? `상태: ${a.status}${a.last_poll_at ? " · 마지막 확인 " + fmtSeen(a.last_poll_at) : ""}` : "알리오 수집이 꺼져 있어요.";
  $("#alio-orgs").textContent = a.orgs.length ? a.orgs.map((o) => o.name).join(", ") : "아직 기관 목록을 받지 못했어요.";
  $("#alio-missing").textContent = a.missing.length ? `알리오에서 찾지 못한 이름: ${a.missing.join(", ")} (config/alio.toml 확인)` : "";
  $("#alio-finance").replaceChildren(...(a.finance.length ? a.finance.map((f) => el("div", { class: "card stack" },
    el("div", { class: "row between" }, el("h3", { text: f.org }),
      el("a", { class: "source", href: f.url, target: "_blank", rel: "noopener noreferrer" }, "알리오 원문 ↗")),
    el("div", { class: "muted small", text: `${f.title || ""} ${f.unit ? "· " + f.unit : ""}` }),
    el("table", { class: "fin" }, el("thead", {}, el("tr", {}, ["항목", "올해", "전년", "증감", "증감률"].map((h) => el("th", { text: h })))),
      el("tbody", {}, f.items.map((i) => el("tr", {},
        el("td", { text: i.label + (i.year ? ` (${i.year})` : "") }), el("td", { text: won(i.value) }), el("td", { text: won(i.prev) }),
        el("td", { class: i.change > 0 ? "up" : i.change < 0 ? "down" : "", text: i.change == null ? "-" : (i.change > 0 ? "+" : "") + won(i.change) }),
        el("td", { class: i.pct > 0 ? "up" : i.pct < 0 ? "down" : "", text: i.pct == null ? "-" : `${i.pct > 0 ? "+" : ""}${i.pct}%` }))))))) :
    [el("p", { class: "muted", text: "아직 수집된 결산이 없어요. 결산 공시가 올라오면(보통 3~4월) 전년 대비 표가 여기에 생깁니다." })]));
}

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
  $("#reporter-form").reporter_id.value = me.reporter_id || "";
  $("#articles-state").textContent = `가져온 내 기사 ${me.my_articles}편`;
  $("#stylebook-meta").textContent = me.stylebook ? `마지막 수정 ${fmtSeen(me.stylebook.updated_at)} · 기사 ${me.stylebook.source_count}편 분석` : "아직 없음";
  const sb = await api("/api/stylebook");
  $("#stylebook").value = sb.content || "";
  $("#stylebook-build").disabled = !me.llm_ready;
  $("#mail-settings").hidden = !me.mail_enabled;
  const acc = me.mail_account;
  $("#mail-account-state").textContent = acc
    ? `연결됨: ${acc.username} · 메일함 '${acc.folder}'${acc.last_error ? " · 오류: " + acc.last_error : ""}`
    : "연결된 메일이 없어요.";
  $("#usage").textContent = me.llm_ready
    ? `이번 달 AI 사용 ${me.spent_krw.toLocaleString("ko-KR")}원 / 한도 ${me.limit_krw.toLocaleString("ko-KR")}원 (${me.llm_provider})`
    : "AI API 키가 아직 연결되지 않았어요.";
  pollArticles();
}

$("#reporter-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try { await api("/api/me/reporter", { method: "POST", body: { reporter_id: e.target.reporter_id.value.trim() } });
    toast("기자 ID를 저장했어요."); renderSettings(); } catch (err) { toast(err.message); }
});
let articlesTimer;
async function pollArticles() {
  clearTimeout(articlesTimer);
  const st = await api("/api/articles/status");
  const j = st.job;
  let msg = `가져온 내 기사 ${st.count}편`;
  if (j?.state === "running") msg += ` · 가져오는 중 (확인 ${j.checked || 0}건, 추가 ${j.added || 0}건)`;
  else if (j?.state === "done") msg += ` · 마지막 가져오기 ${fmtSeen(j.at)} (추가 ${j.added}건)`;
  else if (j?.state === "error") msg += ` · 오류: ${j.error}`;
  $("#articles-state").textContent = msg;
  if (j?.state === "running" && state.view === "settings") articlesTimer = setTimeout(pollArticles, 4000);
}
$("#articles-btn").addEventListener("click", async () => {
  try { const r = await api("/api/articles/collect", { method: "POST" }); toast(r.started ? "내 기사를 가져오기 시작했어요. 몇 분 걸려요." : r.message); pollArticles(); }
  catch (err) { toast(err.message); }
});
$("#stylebook-build").addEventListener("click", async (e) => {
  e.target.disabled = true;
  toast("스타일북을 만드는 중이에요. 1~2분 걸려요.");
  try { const r = await api("/api/stylebook/build", { method: "POST" }); $("#stylebook").value = r.content; toast("스타일북을 만들었어요. 읽어 보고 고쳐 주세요."); renderSettings(); }
  catch (err) { toast(err.message); }
  finally { e.target.disabled = false; }
});
$("#stylebook-save").addEventListener("click", async () => {
  try { await api("/api/stylebook", { method: "PUT", body: { content: $("#stylebook").value } }); toast("스타일북을 저장했어요."); }
  catch (err) { toast(err.message); }
});
$("#mail-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api("/api/mail/account", { method: "PUT", body: Object.fromEntries(f.entries()) });
    e.target.password.value = "";
    toast("메일을 연결했어요."); renderSettings();
  } catch (err) { toast(err.message); }
});
$("#mail-disconnect").addEventListener("click", async () => {
  if (!confirm("메일 연결을 해제하고 가져온 메일을 지울까요?")) return;
  await api("/api/mail/account", { method: "DELETE" }); toast("연결을 해제했어요."); renderSettings();
});

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
  const [st, us, mt] = await Promise.all([api("/api/admin/status"), api("/api/admin/users"), api("/api/admin/metrics")]);
  const t = mt.totals;
  $("#metrics-totals").replaceChildren(
    el("dt", { text: "수집 공시" }), el("dd", { text: `${t.disclosures}건 (중요 ${t.red}건)` }),
    el("dt", { text: "보낸 알림" }), el("dd", { text: `${t.alerts}건` }),
    el("dt", { text: "수집 가동률" }), el("dd", { text: t.uptime_pct == null ? "DART 키 없음" : `${t.uptime_pct}% (오류 ${t.poll_errors}건)` }),
    el("dt", { text: "AI 비용" }), el("dd", { text: `${t.cost_krw.toLocaleString("ko-KR")}원` }));
  $("#metrics-users").replaceChildren(...mt.users.map((u) => el("tr", {},
    el("td", { text: u.display_name }), el("td", { text: u.claims }), el("td", { text: u.written }),
    el("td", { text: u.questions }), el("td", { text: u.drafts }), el("td", { text: `${u.cost_krw.toLocaleString("ko-KR")}원` }))));
  $("#admin-status").replaceChildren(
    el("dt", { text: "수집 상태" }), el("dd", { text: st.dart_status }),
    el("dt", { text: "마지막 수집" }), el("dd", { text: st.last_poll_at ? fmtSeen(st.last_poll_at) : "-" }),
    el("dt", { text: "오늘 DART 호출" }), el("dd", { text: `${st.dart_calls_today}건` }),
    el("dt", { text: "알림 모드" }), el("dd", { text: st.alert_mode === "notify" ? "알림 보냄" : "기록만 (.env 의 ALERT_MODE=notify 로 변경)" }),
    el("dt", { text: "알리오" }), el("dd", { text: st.alio_status }),
    el("dt", { text: "AI" }), el("dd", { text: st.llm }),
    el("dt", { text: "메일" }), el("dd", { text: st.mail }));
  $("#users").replaceChildren(...us.users.map((u) => el("tr", {},
    el("td", { text: u.display_name }), el("td", { text: u.username }), el("td", { text: u.role === "admin" ? "관리자" : "기자" }),
    el("td", {}, `${u.spent_krw.toLocaleString("ko-KR")} / `,
      el("input", { class: "limit-input", type: "number", min: "0", step: "1000", value: u.limit_krw, "aria-label": `${u.display_name} 월 한도(원)`,
        onchange: async (e) => { await api(`/api/admin/users/${u.id}/limit`, { method: "POST", body: { krw: Number(e.target.value) } }); toast("한도를 바꿨어요."); } }), "원"),
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

# [첨부] tests/test_llm.py

```py
import json
from types import SimpleNamespace as NS

import pytest

from newsbot.config import Settings
from newsbot.db import Database
from newsbot.llm import LLM, BudgetExceeded, ClaudeBackend, LLMError, OpenAIBackend, Tool
from newsbot.writing import check_numbers

TOOL = Tool("lookup", "찾기", {"type": "object", "properties": {"q": {"type": "string"}}},
            lambda a: {"found": a.get("q", "") + "!"})


class FakeClaude:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        return self.responses.pop(0)


def c_resp(content, stop="end_turn"):
    return NS(content=content, stop_reason=stop,
              usage=NS(input_tokens=1000, output_tokens=200, cache_read_input_tokens=0, cache_creation_input_tokens=0))


def test_claude_tool_loop_and_fallback_params():
    fake = FakeClaude([
        c_resp([NS(type="tool_use", id="t1", name="lookup", input={"q": "유한"})], stop="tool_use"),
        c_resp([NS(type="text", text="답: 유한!")]),
    ])
    b = ClaudeBackend("k", client=fake)
    text, trace, usages = b.agent("claude-sonnet-5-5", "sys", [{"role": "user", "content": "질문"}], [TOOL], "main", 5)
    assert text == "답: 유한!" and trace[0]["tool"] == "lookup" and len(usages) == 2
    first, second = fake.calls
    assert first["fallbacks"] == "default" and first["betas"] == ["server-side-fallback-2026-07-01"]
    assert first["output_config"] == {"effort": "medium"}
    assert "temperature" not in first and "tool_choice" not in first
    tool_result = second["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and json.loads(tool_result["content"]) == {"found": "유한!"}


def test_haiku_has_no_fallbacks_and_refusal_raises():
    fake = FakeClaude([c_resp([], stop="refusal")])
    with pytest.raises(LLMError):
        ClaudeBackend("k", client=fake).complete("claude-haiku-5-5", "s", "p", "fast")
    assert "fallbacks" not in fake.calls[0]


def test_openai_tool_loop():
    calls = []

    def create(**kw):
        calls.append(kw)
        if len(calls) == 1:
            tc = NS(id="c1", function=NS(name="lookup", arguments='{"q":"한미"}'),
                    model_dump=lambda: {"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": '{"q":"한미"}'}})
            msg = NS(content=None, tool_calls=[tc])
        else:
            msg = NS(content="답: 한미!", tool_calls=None)
        return NS(choices=[NS(message=msg)], usage=NS(prompt_tokens=500, completion_tokens=50))

    b = OpenAIBackend("k", client=NS(chat=NS(completions=NS(create=create))))
    text, trace, _ = b.agent("gpt-6.1-sol", "sys", [{"role": "user", "content": "q"}], [TOOL], "main", 5)
    assert text == "답: 한미!" and calls[1]["messages"][-1]["role"] == "tool"


def test_budget_and_cost(tmp_path):
    db = Database(":memory:")
    db.execute("INSERT INTO users(id, username, display_name, pw_hash, created_at, monthly_limit_krw) VALUES(1,'a','A','x','t',100)")
    fake = FakeClaude([c_resp([NS(type="text", text="ok")])] * 3)
    llm = LLM(Settings(llm_provider="claude", anthropic_api_key="k", data_dir=tmp_path), db, backend=ClaudeBackend("k", client=fake))
    text, model = llm.complete("s", "p", "main", user_id=1, purpose="t")
    # sonnet 5.5: 1000*2 + 200*10 = 4000 / 1e6 USD = 0.004 USD = 5.6원
    assert model == "claude-sonnet-5-5" and llm.month_spent(1) == pytest.approx(5.6)
    db.execute("UPDATE users SET monthly_limit_krw=5 WHERE id=1")
    with pytest.raises(BudgetExceeded):
        llm.complete("s", "p", "main", user_id=1, purpose="t")


def test_check_numbers():
    checks = check_numbers("매출 1,234억원, 15% 증가, 2026년", "매출액 1234억원 ... 2026년 실적")
    found = {c["number"]: c["found"] for c in checks}
    assert found == {"1,234": True, "15": False, "2026": True}
```

---

# [첨부] tests/test_alio.py

```py
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
```
