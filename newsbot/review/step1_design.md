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
