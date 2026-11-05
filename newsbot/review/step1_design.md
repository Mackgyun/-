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
