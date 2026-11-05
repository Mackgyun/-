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
