# Codex 교차검증 요청

너는 독립 검토자다. 아래는 한국 의료전문지(청년의사, 직원 30~40명, 기자 약 20명)의 기자가 만들려는 시스템의 **회사 제안 기획서**와 **1단계 코드 설계/일부 코드**다. 다른 AI(Claude)가 작성했다. 칭찬하지 말고 **틀린 것**과 **빠진 것**을 찾아라.

시스템 개요:
- 24시간 도는 텔레그램 봇: OpenDART 공시, 알리오(공공기관·국립대병원 경영공시), 보도자료 Gmail을 수집해 알림·브리핑
- 질문 기능: Claude 또는 OpenAI API의 tool use로 수집 데이터를 조회해 출처와 함께 답변
- 기사 초안: 기자별 과거 기사로 만든 스타일북 + 유사 기사 검색(RAG). 파인튜닝은 하지 않음
- 실행: 여분 Windows 노트북 → 나중에 회사 NAS(Docker) 또는 서울 리전 클라우드
- 다중 사용자: 초대 코드 등록, 편집국 공용 그룹 + 기자별 1:1, [내가 쓸게요] 버튼

검토할 것:
1. 사실 오류: OpenDART API(파라미터, 상태코드, 일일 한도, company.json의 induty_code), KSIC 업종코드로 보건의료 기업 판별(21, 271, 86, 70113, 4644)이 맞는지와 누락, 알리오 공식 API 범위, 텔레그램 Bot API 제약(그룹 privacy mode, 전송 한도), Gmail 접근 방식(IMAP 앱 비밀번호, OAuth), Tailscale 요금·약관, 비용 계산
2. 설계 결함: 중복 제거·첫 실행 처리, 자정 경계, 정정공시, 키워드 오탐(예: "분할"이 "분할상환"에, "임상"이 일상 공시에), 알림 과다, 개인정보·비밀값 저장, SQLite, 시간대, Windows 상시 실행
3. 빠진 것: 법·규정(개인정보 국외 이전, 저작권, 동료 기사 문체 분석 동의), 운영(백업, 모니터링, 장애 대응), 승인권자가 물어볼 질문
4. 우선순위 Top 10 수정 제안 (구체적으로)

답변은 한국어로, 항목마다 심각도(상/중/하)와 근거를 붙여라. 확실하지 않은 것은 "확인 필요"로 표시하라.

---

# [첨부 1] 기획서

# 편집국 AI 브리핑·기사 보조 봇 시범사업 제안 (2026-11-05 기준)

## 제안 요약

DART 공시, 알리오 공공기관·병원 공시, 보도자료 메일을 24시간 자동으로 확인해 텔레그램으로 알리고, 질문에 답하고, 기자별 문체로 기사 초안까지 돕는 봇을 2개월간 시범 운영하겠습니다. 첫 달은 제안자 1인이 기존 여분 노트북으로 운영해 추가 장비 비용이 없고, 성과를 확인한 뒤 편집국 전체 확대를 결정합니다.

- **기간**: 시범 8주, 이후 확대 여부 결정
- **비용**: 시범 기간 월 1~5만 원, 편집국 전체 확대 시 월 10~30만 원 수준(AI API 사용료 중심)
- **회사 요청**: 회사 NAS 사용 승인, ND소프트에 기사 DB 추출 요청, API 비용 지원

## 배경과 문제

기사거리가 되는 자료는 세 곳에 흩어져 있고, 지금은 기자가 각자 수시로 들여다봐야 합니다. 밤이나 취재 중에 올라온 건은 늦게 발견하거나 놓치기 쉽습니다.

| 자료 | 내용 | 지금 확인 방식 |
| --- | --- | --- |
| OpenDART | 제약·바이오·의료기기 상장사의 허가, 기술이전, 증자, 최대주주 변경 등 | 사이트를 수시로 검색 |
| 알리오(ALIO) | 국립대병원 등 공공기관 병원의 결산(의료수익), 임원 변동, 이사회 등 수시공시 | 기관별 페이지를 직접 방문 |
| 보도자료 메일 | 정부·제약사·단체 보도자료, 엠바고 시각 | 기자별 메일함에서 각자 확인 |

같은 공시를 두 기자가 동시에 취재하거나, 아무도 못 본 채 넘어가는 일도 생깁니다. 기사 초안을 보도자료에서 매번 처음부터 쓰는 시간도 줄일 여지가 있습니다.

## 제안 내용

봇은 알림·질문·초안 세 가지 일을 하고, 모두 기자가 확인한 뒤 쓰는 보조 도구입니다. 출고는 항상 기자와 데스크가 합니다.

| 기능 | 하는 일 | 사용 예시 |
| --- | --- | --- |
| 알림·브리핑 | DART는 5분, 메일은 5분, 알리오는 1시간마다 확인. 중요한 건은 즉시, 나머지는 하루 3~4회 요약 | "OO제약 기술이전 계약 공시(계약금 ○○억)" 알림 + 원문 링크 |
| 질문 답변 | 모아둔 공시·메일·기사를 찾아보고 출처를 붙여 답함 | "서울대병원 작년 의료수익 전년 대비 얼마나 늘었어?" |
| 기사 초안 보조 | 기자별 과거 기사를 분석한 스타일북과 비슷한 기사를 참고해 스트레이트 초안 작성. 숫자·인명은 원문과 대조 표시 | 알림의 [초안 작성] 버튼 → 초안 답장 |

편집국용 장치도 넣습니다.

- **공용 그룹과 개인 알림 분리**: 속보급은 편집국 공용 그룹으로, 출입처별 공시와 본인 메일 브리핑은 각자 1:1 대화로 보냅니다.
- **[내가 쓸게요] 버튼**: 공용 그룹 알림에서 누가 그 건을 맡았는지 표시해 중복 취재를 막습니다.
- **기자별 설정**: 출입처·키워드, 스타일북, 메일 연결을 기자마다 따로 둡니다.

AI는 Claude와 OpenAI 중 하나를 쓰되, 시범 기간에 같은 보도자료로 두 쪽 초안을 비교해 고릅니다. 언제든 교체할 수 있는 구조로 만듭니다.

## 구조와 운영 환경

시범은 기존 여분 노트북 한 대에서 24시간 돌리고, 확대할 때는 같은 프로그램을 회사 NAS나 클라우드로 옮깁니다.

(구조도) 자료 3곳(OpenDART 5분마다 / 알리오 1시간마다 / 보도자료 메일 Gmail 5분마다) → 봇 서버[수집·중복 제거 → 저장소(공시·메일·기사·스타일북) → 판단·작성(중요도 분류, 질문 답변, 초안)] ↔ AI API(Claude 또는 OpenAI) → 텔레그램(편집국 공용 그룹: 속보, [내가 쓸게요] / 기자별 1:1 대화: 맞춤 알림, 질문, 초안). 관리자 휴대폰은 Tailscale로 봇 서버 원격 관리.

- **서버**: Windows 노트북을 덮개를 닫아도 꺼지지 않게 설정하고, 재부팅하면 자동으로 다시 켭니다. 프로그램은 Docker로 묶어 다른 장비로 그대로 옮길 수 있습니다.
- **방화벽 설정 불필요**: 봇이 텔레그램 서버에 먼저 접속하는 방식이라 공유기나 회사 방화벽을 바꾸지 않습니다.
- **질문 흐름**: 기자가 1:1 대화로 물으면 봇이 저장소와 DART를 찾아보고 출처를 붙여 같은 대화로 답합니다.
- **국내 장비 실행**: 국내 공공 사이트 접속이 안정적이도록 해외 서버가 아닌 국내 장비에서 돌립니다.

## 보안·개인정보·저작권

봇은 읽기 전용이고, 등록된 직원에게만 응답하며, 기자의 메일은 본인만 볼 수 있습니다.

- **사용자 제한**: 관리자가 발급한 초대 코드로 등록한 직원에게만 응답합니다. 퇴사자는 즉시 삭제합니다.
- **읽기 전용**: 메일 발송·삭제, 기사 출고 같은 쓰기 기능은 만들지 않습니다.
- **메일 분리**: 메일 연결은 기자가 선택하고, 비밀번호는 암호화해 저장합니다. 다른 사람의 메일은 질문으로도 조회할 수 없습니다.
- **AI 전송 범위**: 공시·보도자료·자사 기사 요약에 필요한 내용만 AI API로 보냅니다. 취재원 개인정보가 담긴 메일은 기자가 제외 라벨을 지정할 수 있게 합니다.
- **저작권**: 청년의사 기사는 사내 분석에만 씁니다. 특정 기자의 문체 분석은 본인 동의를 받은 경우만 하고, 스타일북은 본인만 수정합니다.
- **외부 사이트 부담**: DART는 공식 API 한도(하루 약 2만 건) 안에서, 알리오·자사 사이트는 요청 간격을 두고 조회합니다.
- **원격 관리**: 회사 네트워크에는 VPN을 설치하지 않습니다. 원격 관리용 Tailscale은 관리자 노트북과 휴대폰에만 설치합니다.

## 비용

시범 기간에는 월 1~5만 원, 편집국 전체로 넓히면 월 10~30만 원 수준입니다. 대부분 AI API 사용료이고 쓴 만큼 내므로, 기자별 월 한도를 걸어 관리합니다.

| 항목 | 시범 (1인, 8주) | 편집국 확대 (기자 약 20명) |
| --- | --- | --- |
| 서버 | 0원 (여분 노트북) | 0원 (회사 NAS) 또는 월 약 7천 원 (서울 리전 클라우드) |
| AI API: 브리핑 분류·요약 | 월 수천 원 | 월 1만 원 이내 |
| AI API: 질문 답변·초안 | 월 1~4만 원 | 월 10~30만 원 |
| 스타일북 분석 (1회) | 약 1만 원 | 기자당 약 1만 원 |
| 원격 관리 (Tailscale, 관리자 1명) | 월 약 1만 원 | 월 약 1만 원 |
| 텔레그램 | 무료 | 무료 |
| 기사 DB 추출 (ND소프트) | 문의 필요 | 문의 필요 |

1달러는 1,400원으로 계산했습니다. API 단가는 Anthropic 기준(2026년 10월)으로 브리핑은 Claude Haiku 5.5(입력 100만 토큰당 0.1달러), 질문·초안은 Sonnet 5.5(2달러)·Opus 5.5(4달러)를 가정했고, OpenAI도 비슷한 가격대입니다. 편집국 확대 비용은 기자 1인당 하루 질문 10건을 가정한 추정이며, 시범 기간 실측치로 다시 산정합니다.

## 회사에 요청하는 사항

시범 시작에는 첫 번째 항목만 있으면 되고, 나머지는 확대 결정 전까지 준비하면 됩니다.

- [ ] 시범 운영 승인과 API 비용 지원 (월 5만 원 한도, 법인카드 또는 비용 처리)
- [ ] 회사 명의로 ND소프트에 기사 DB 추출 문의 (기사 본문·제목·기자·섹션·작성일, 비용과 절차 확인)
- [ ] 회사 NAS 사용 승인: 시범 중에는 백업 저장소, 확대 시 봇 실행 서버 (NAS 모델이 Docker를 지원하는지 확인 필요)
- [ ] 편집국 공용 텔레그램 그룹 개설 동의
- [ ] 기자별 문체 분석 동의 절차 (확대 시)

## 일정과 성과 지표

8주 동안 2주마다 기능을 하나씩 켜고, 마지막 주에 아래 지표로 편집국 확대 여부를 결정합니다. 시작일은 승인 후 정합니다.

(로드맵) 1~2주차 DART 알림(공시 알림 시작, 사용자 등록) → 3~4주차 메일·질문(메일 브리핑, 질문 답변) → 5~6주차 기사 초안(스타일북 생성, AI 두 곳 비교) → 7~8주차 알리오·평가(병원 결산 비교, 성과 정리) → 확대 결정(지표 검토 후)

| 지표 | 측정 방법 |
| --- | --- |
| 기사화 건수 | 봇 알림에서 시작된 기사 수 |
| 먼저 잡은 자료 | 기자가 알기 전에 봇이 먼저 알린 공시·보도자료 건수 |
| 알림 정확도 | 알림 중 실제로 볼 가치가 있었던 비율, 주 1회 표본 점검 |
| 절약 시간 | 자료 확인에 쓰던 시간, 시범 전후 주간 자가 기록 |
| 초안 수정량 | 초안에서 기자가 고친 비율, AI 두 곳 비교에도 사용 |
| 가동률 | 봇이 멈춘 시간, 하루 1회 가동 확인 메시지로 기록 |
| 월 API 비용 | 사용자별 사용량 로그 |

## 리스크와 대응

가장 큰 리스크는 AI가 사실을 잘못 쓰는 것이고, 출처 표시와 기자 검수로 막습니다.

| 리스크 | 대응 |
| --- | --- |
| AI가 숫자·인명을 지어냄 | 모든 숫자에 공시번호·원문 링크 표시, 못 찾으면 "확인 안 됨" 답변, 초안은 항상 기자 검수 후 사용 |
| 노트북 정전·재부팅으로 중단 | 자동 재시작, 하루 1회 가동 확인 메시지, 확대 시 NAS나 클라우드로 이전 |
| 알리오 개편으로 수집 중단 | 공식 API가 없는 항목이라 수집 실패 시 관리자에게 즉시 알림, 수집기만 고치면 되도록 분리 |
| API 비용 초과 | 기자별 월 한도, 한도 도달 시 저렴한 모델로 전환, 월간 사용량 리포트 |
| 알림 과다로 피로 | 중요도 3단계(즉시/정기 브리핑/기록만), 기자별 키워드 조정 |
| 개인 메일 노출 | 본인만 조회, 비밀번호 암호화, 제외 라벨 기능 |
| 개발·운영이 한 사람에게 의존 | 설치·운영 문서를 남기고, Docker로 묶어 다른 장비로 쉽게 옮길 수 있게 함 |

---

# [첨부 2] 1단계 설계

# 1단계 코드 설계 (DART → 텔레그램, 다중 사용자) — 작성 중

이 파일은 검토용 설계 메모입니다. 현재 `config.py`, `rules.py`, `config/rules.toml`, `requirements.txt`, `.env.example`까지만 작성되어 있고, 나머지는 아래 설계대로 작성할 예정입니다.

## 환경
- 실행: 기자의 여분 Windows 노트북, 24시간 가동. 나중에 회사 NAS(Docker)나 서울 리전 클라우드로 이전.
- Python 3.11+ (표준 `tomllib` 사용), 의존성: python-telegram-bot[job-queue] 21.6, httpx 0.27.2, python-dotenv, tzdata(Windows의 zoneinfo용).
- 1단계는 AI(LLM)를 쓰지 않음. 규칙 기반 분류만.
- 실행 방식: Windows 작업 스케줄러 "시작 시" 등록(로그인 없이), 또는 Docker Compose.

## DART 수집 (newsbot/dart.py, 예정)
- `list.json`을 5분마다 호출: `bgn_de`=어제, `end_de`=오늘, `page_count=100`, 최신순. 이미 본 `rcept_no`가 나오는 페이지에서 중단.
- 첫 실행(빈 DB)은 "부트스트랩": 기존 공시는 알림 없이 기록만 해서 알림 폭주 방지.
- 상태코드: `000` 정상, `013` 데이터 없음, `020` 한도 초과(하루 약 2만 건) → 그날 수집 중단 + 관리자 알림.
- 하루 호출 수를 DB에 세서 `DART_DAILY_CALL_LIMIT`(기본 18,000)에서 멈춤.
- 보건의료 기업 판별: 처음 보는 `corp_code`는 `company.json`(기업개황)으로 `induty_code`(KSIC)를 받아 캐시. rules.toml의 접두어(21, 271, 86, 70113, 4644)로 판별 + 항상 포함/제외 목록.
- 원문 링크: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}`.

## 중요도 분류 (newsbot/rules.py, 작성됨)
- 공시 제목(report_nm)에서 공백을 지운 뒤 키워드 포함 여부: red 키워드 → red, gray 키워드 → gray, 나머지 yellow.
- red: 즉시 알림 (공용 그룹 + 그 기업·키워드를 구독한 기자 개인).
- yellow: 구독한 기자에게 정기 브리핑(기본 08:00, 13:00, 18:00, 23:00 KST)으로 묶어서.
- gray: 기록만.

## DB (SQLite, newsbot/db.py, 예정)
- users(chat_id PK, name, role admin|reporter, active, created_at)
- invites(code PK, created_by, created_at, used_by, used_at) — 일회용 초대 코드
- subscriptions(chat_id, kind company|keyword|all, value)
- companies(corp_code PK, corp_name, induty_code, is_health, fetched_at)
- disclosures(rcept_no PK, corp_code, corp_name, report_nm, rcept_dt, flr_nm, rm, level, keyword, created_at)
- digest_queue(chat_id, rcept_no) — 정기 브리핑 대기열
- claims(rcept_no PK, chat_id, claimed_at) — [내가 쓸게요]
- kv(key PK, value) — 공용 그룹 chat_id, 일별 DART 호출 수, 부트스트랩 여부 등

## 텔레그램 봇 (newsbot/bot.py, 예정)
- 롱 폴링(외부 포트 개방 불필요).
- 명령어: `/start <초대코드>` 등록, `/sub 기업명|키워드`, `/sub all`(보건의료 전체), `/unsub`, `/mysubs`, `/status`, `/help`.
- 관리자: `/invite`(초대 코드 발급), `/users`, `/remove <id>`, `/setgroup`(공용 그룹에서 실행해 그룹 지정).
- 미등록 사용자: `/start`에만 "초대 코드 필요 + 내 ID" 안내, 나머지는 무시.
- 공용 그룹의 red 알림에 [내가 쓸게요] 인라인 버튼 → 누가 맡았는지 메시지에 표시, 이미 다른 사람이 맡았으면 거절.
- 매일 09:00 관리자에게 가동 확인(지난 24시간 수집 건수, DART 호출 수). DART 연속 실패 시 관리자 알림(1시간에 1번까지).

## 다음 단계 (이번 범위 아님)
- Gmail 브리핑(IMAP + 앱 비밀번호), 질문 기능(LLM tool use), 기자 기사 수집·스타일북, 초안, 알리오.
- LLM은 Claude/OpenAI 교체 가능하게 어댑터로 분리.

---

# [첨부] config/rules.toml

```
# 공시 중요도 규칙
#
# 등급
#   red    : 즉시 알림 (편집국 공용 그룹 + 해당 기업·키워드를 구독한 기자)
#   yellow : 정기 브리핑에 포함 (구독한 기자에게만)
#   gray   : 기록만 하고 알리지 않음
#
# 판단 순서: red 키워드 → gray 키워드 → 나머지는 yellow
# 키워드는 공시 제목(report_nm)에 들어 있는지로 판단합니다. 띄어쓰기는 무시합니다.

[health]
# 보건의료 기업으로 볼 업종코드(KSIC) 앞자리.
# 21: 의약품 제조, 271: 의료기기 제조, 86: 보건업,
# 70113: 의학·약학 연구개발, 4644: 의약품·의료용품 도매
industry_prefixes = ["21", "271", "86", "70113", "4644"]

# 업종코드와 상관없이 항상 감시할 기업 (DART 회사명 그대로)
always_include = []

# 업종코드가 맞아도 제외할 기업
always_exclude = []

[levels]
red = [
  "품목허가", "임상", "기술이전", "기술도입", "라이선스",
  "유상증자", "무상증자", "전환사채", "최대주주변경", "경영권",
  "합병", "분할", "영업양수", "영업양도", "공개매수",
  "단일판매", "공급계약", "횡령", "배임", "소송",
  "영업정지", "회생", "상장폐지", "관리종목", "거래정지",
  "감사의견", "불성실공시",
]

gray = [
  "임원ㆍ주요주주특정증권등소유상황보고서",
  "주식등의대량보유상황보고서",
  "기업설명회",
  "증권발행실적보고서",
  "투자설명서",
  "자기주식취득결과보고서",
]
```

---

# [첨부] newsbot/rules.py

```
"""공시 중요도 규칙 (config/rules.toml)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RED, YELLOW, GRAY = "red", "yellow", "gray"
LEVEL_EMOJI = {RED: "🔴", YELLOW: "🟡", GRAY: "⚪"}


def _norm(text: str) -> str:
    """띄어쓰기와 대괄호 접두어 차이를 무시하기 위해 공백을 모두 지운다."""
    return "".join(text.split())


@dataclass(frozen=True)
class Rules:
    industry_prefixes: tuple[str, ...] = ()
    always_include: frozenset[str] = frozenset()
    always_exclude: frozenset[str] = frozenset()
    red: tuple[str, ...] = ()
    gray: tuple[str, ...] = ()
    _red_norm: tuple[str, ...] = field(default=(), repr=False)
    _gray_norm: tuple[str, ...] = field(default=(), repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Rules":
        health = data.get("health", {})
        levels = data.get("levels", {})
        red = tuple(levels.get("red", []))
        gray = tuple(levels.get("gray", []))
        return cls(
            industry_prefixes=tuple(health.get("industry_prefixes", [])),
            always_include=frozenset(health.get("always_include", [])),
            always_exclude=frozenset(health.get("always_exclude", [])),
            red=red,
            gray=gray,
            _red_norm=tuple(_norm(k) for k in red),
            _gray_norm=tuple(_norm(k) for k in gray),
        )

    @classmethod
    def load(cls, path: Path) -> "Rules":
        with open(path, "rb") as f:
            return cls.from_dict(tomllib.load(f))

    def is_health(self, corp_name: str, induty_code: str | None) -> bool:
        if corp_name in self.always_exclude:
            return False
        if corp_name in self.always_include:
            return True
        if not induty_code:
            return False
        return any(induty_code.startswith(p) for p in self.industry_prefixes)

    def classify(self, report_nm: str) -> tuple[str, str | None]:
        """(등급, 걸린 키워드)를 돌려준다."""
        title = _norm(report_nm)
        for raw, key in zip(self.red, self._red_norm):
            if key in title:
                return RED, raw
        for raw, key in zip(self.gray, self._gray_norm):
            if key in title:
                return GRAY, raw
        return YELLOW, None
```

---

# [첨부] newsbot/config.py

```
"""환경변수(.env)에서 설정을 읽는다."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")


def _parse_times(raw: str) -> list[time]:
    times = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        hour, minute = part.split(":")
        times.append(time(int(hour), int(minute), tzinfo=KST))
    return times


def _parse_ids(raw: str) -> set[int]:
    return {int(x) for x in raw.replace(" ", "").split(",") if x}


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    dart_api_key: str
    admin_chat_ids: set[int] = field(default_factory=set)
    db_path: Path = Path("data/newsbot.db")
    rules_path: Path = Path("config/rules.toml")
    poll_interval_sec: int = 300
    digest_times: list[time] = field(default_factory=list)
    heartbeat_time: time = time(9, 0, tzinfo=KST)
    dart_daily_call_limit: int = 18000


def load_settings(env_file: str | None = ".env") -> Settings:
    if env_file:
        load_dotenv(env_file)

    missing = [k for k in ("TELEGRAM_BOT_TOKEN", "DART_API_KEY") if not os.getenv(k)]
    if missing:
        raise SystemExit(
            f".env 에 {', '.join(missing)} 값이 없습니다. .env.example 을 참고해 채워주세요."
        )

    return Settings(
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        dart_api_key=os.environ["DART_API_KEY"],
        admin_chat_ids=_parse_ids(os.getenv("ADMIN_CHAT_IDS", "")),
        db_path=Path(os.getenv("DB_PATH", "data/newsbot.db")),
        rules_path=Path(os.getenv("RULES_PATH", "config/rules.toml")),
        poll_interval_sec=int(os.getenv("POLL_INTERVAL_SEC", "300")),
        digest_times=_parse_times(os.getenv("DIGEST_TIMES", "08:00,13:00,18:00,23:00")),
        heartbeat_time=_parse_times(os.getenv("HEARTBEAT_TIME", "09:00"))[0],
        dart_daily_call_limit=int(os.getenv("DART_DAILY_CALL_LIMIT", "18000")),
    )
```

---

# [첨부] requirements.txt

```
python-telegram-bot[job-queue]==21.6
httpx==0.27.2
python-dotenv==1.0.1
tzdata>=2024.1
```

---

# [첨부] .env.example

```
# 텔레그램 BotFather에서 받은 토큰
TELEGRAM_BOT_TOKEN=
# OpenDART(https://opendart.fss.or.kr) 인증키
DART_API_KEY=
# 관리자 텔레그램 ID (봇에게 /start 를 보내면 알려줍니다). 여러 명이면 쉼표로 구분
ADMIN_CHAT_IDS=

# 이하 선택 항목 (기본값이 있음)
DB_PATH=data/newsbot.db
RULES_PATH=config/rules.toml
POLL_INTERVAL_SEC=300
DIGEST_TIMES=08:00,13:00,18:00,23:00
HEARTBEAT_TIME=09:00
DART_DAILY_CALL_LIMIT=18000
```
