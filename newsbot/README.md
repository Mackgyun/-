# 청년의사 브리핑

DART 공시와 알리오(공공기관·국립대병원) 공시를 24시간 모아 보건의료 관련 건만 보여주고, 중요한 건은 PC 오른쪽 아래 팝업과 휴대폰 푸시로 알리는 자체 웹앱입니다. AI로 질문에 답하고, 기자별 문체로 기사 초안을 쓰고, 보도자료 메일을 모아 봅니다. 시범사업 제안서의 기능을 모두 담았습니다.

## 기능

| 기능 | 내용 | 필요한 것 |
| --- | --- | --- |
| DART 공시 | 5분마다 최근 300건 재확인 + 매시간 이틀치 대조(공개 지연·순서 뒤섞임 대응). 감시 기업 목록 + 보건의료 업종코드로 선별, 중요·일반·기록 3단계, 정정공시 표시 | DART 키 |
| 알리오 | 국립대병원·공공 의료기관 25곳의 수시공시(임원, 이사회, 감사, 징계, 경영평가) 감시, 결산(손익계산서) 전년 대비 표 | 없음 (`config/alio.toml`) |
| 알림 | PC는 Windows 알림(오른쪽 아래), 휴대폰은 홈 화면 앱 푸시. 중요 공시만, 정정은 제외. 처음엔 '기록만' 모드 | HTTPS 또는 localhost |
| 오늘의 브리핑 | 요약 카드, 지금 확인할 것, 하루 4번 정기 브리핑(AI 키가 있으면 AI 요약) | - |
| 담당 표시 | [내가 쓸게요]로 중복 취재 방지, [기사 썼어요]로 기사화 기록 | - |
| 질문 | 공시·알리오 결산·DART 재무·과거 기사·(켜면) 내 메일을 AI가 찾아보고 출처와 함께 답 | AI 키 |
| 기사 초안 | 공시 원문·보도자료·메모로 초안. 내 스타일북 + 비슷한 내 기사 참고. 원자료에 없는 숫자는 빨간색 표시 | AI 키 |
| 스타일북 | 내 기사(docdocdoc.co.kr)를 가져와 AI가 문체를 분석. 직접 고칠 수 있음 | AI 키 |
| 보도자료 메일 | 지정한 메일함 하나만 읽기 전용으로 가져옴, 엠바고 문구 자동 표시. **기본은 꺼짐** | 법무·IT 검토 후 `MAIL_ENABLED=true` |
| 관리자 | 초대 링크, 사용자 관리, 기자별 월 AI 한도, 수집 상태, **시범사업 성과**(담당·기사화·질문·초안·AI 비용·가동률) | - |

## 노트북(Windows)에 설치하기

1. **Python 3.11 이상** 설치: https://www.python.org/downloads/ (설치 화면에서 'Add python.exe to PATH' 체크)
2. 저장소를 받습니다.
   ```bash
   git clone -b claude/eloquent-fermi-pj12x0 https://github.com/Mackgyun/-.git chungnyun-bot
   ```
3. `chungnyun-bot\newsbot` 폴더에서 PowerShell을 열고 설치합니다.
   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\windows\setup.ps1
   ```
4. `.env` 파일을 메모장으로 열어 키를 넣습니다. 비워 둔 기능은 꺼진 채로 나머지가 동작합니다.
   - `DART_API_KEY=` OpenDART 인증키
   - `LLM_PROVIDER=claude` 와 `ANTHROPIC_API_KEY=` (또는 `openai` 와 `OPENAI_API_KEY=`)
5. 관리자 계정을 만듭니다.
   ```bash
   .\.venv\Scripts\python.exe -m newsbot create-admin 내아이디 --name 내이름
   ```
6. 실행하고 브라우저에서 http://localhost:8000 을 엽니다.
   ```bash
   scripts\windows\start.bat
   ```
7. **24시간 실행** (관리자 권한 PowerShell): 덮개를 닫아도 안 꺼지게, 부팅하면 로그인 없이 자동 시작.
   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\windows\power-settings.ps1
   ```
   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\windows\install-autostart.ps1
   ```

> Windows 스크립트, 실제 DART·알리오·AI·메일 연결은 클라우드 환경에서 실행해 보지 못했습니다(키·접속 제한). 자동 테스트는 가짜 응답으로 검증했습니다. 처음 실행할 때 오류가 나면 메시지를 그대로 알려주세요.

## 처음 쓰는 순서 (권장)
1. DART 키만 넣고 2주간 **기록만 모드**로 돌리며 알림량 확인 → 관리자 화면 '시범사업 성과'
2. `config/rules.toml` 감시 기업과 키워드를 출입처에 맞게 조정 → `ALERT_MODE=notify`
3. AI 키를 넣고 '내 설정'에서 기자 ID 입력 → 내 기사 가져오기 → 스타일북 만들기 → 직접 다듬기
4. 동료 초대: 관리자 화면에서 초대 링크
5. 다른 PC·휴대폰 알림: 보안 터널(아래)
6. 메일: 법무·IT 검토가 끝나면 `MAIL_ENABLED=true`

## 다른 PC·휴대폰에서 쓰기 (보안 터널)
웹 푸시는 HTTPS에서만 동작합니다. 노트북을 인터넷에 직접 열지 않고 Cloudflare Tunnel 같은 보안 터널로 HTTPS 주소를 붙이는 방식을 권장합니다.
- 도메인 1개(연 1~2만 원)를 Cloudflare에 연결하고, 노트북에 `cloudflared`를 설치해 `http://localhost:8000`을 `https://briefing.도메인`으로 연결합니다.
- `.env`의 `PUBLIC_URL`을 그 주소로 바꾸면 쿠키가 HTTPS 전용으로 바뀌고, 초대 링크·푸시 링크도 그 주소를 씁니다.
- 인터넷에 열리는 만큼, 처음 2주는 사내에서만 쓰고 보안 점검 뒤 엽니다.
- 외부 감시 서비스(UptimeRobot 등)에 `https://briefing.도메인/healthz`를 등록하면 수집이 멈췄을 때 알려줍니다.

## 명령
| 명령 | 하는 일 |
| --- | --- |
| `python -m newsbot` | 웹앱 + 수집 실행 |
| `python -m newsbot create-admin 아이디` | 관리자 계정 만들기 |
| `python -m newsbot invite` | 초대 링크 만들기 (관리자 화면에서도 가능) |
| `python -m newsbot poll` | DART 한 번 수집해 보기 (알림 없음) |

## 알아둘 점
- **아이폰**은 Safari '홈 화면에 추가'로 설치한 앱에서만 알림을 받습니다 (iOS 16.4 이상).
- `config/rules.toml`의 감시 기업, `config/alio.toml`의 기관 이름은 예시입니다. 표기가 다르면 관리자 화면 '알리오'에 '찾지 못한 이름'으로 표시됩니다.
- 알리오는 경영공시용 공식 API가 없어 사이트의 조회 방식을 씁니다. 사이트가 바뀌면 수집이 멈추고 관리자 화면에 오류가 뜹니다. 복지부가 국립대병원의 공공기관 지정 해제를 추진 중이라는 보도가 있어 공시 범위가 바뀔 수 있습니다.
- 자사 기사 수집은 사내 분석용이며 요청 사이 2초씩 쉽니다. 회사가 ND소프트에서 기사 DB를 받으면 그쪽으로 바꾸는 것이 좋습니다.
- AI가 쓴 초안과 답변은 반드시 원문으로 확인한 뒤 씁니다. 원자료에 없는 숫자는 빨간색으로 표시됩니다.
- 데이터는 `data/` 폴더(SQLite, 암호화 키 포함)에 있습니다. 주기적으로 NAS에 백업하고, 이 폴더는 외부에 공유하지 마세요.
- Claude Sonnet·Opus 호출에는 안전 분류기가 요청을 거절하면 서버가 다른 모델로 다시 처리하는 옵션(`fallbacks: "default"`)을 켜 두었습니다.

## 개발
```bash
pip install -r requirements-dev.txt
```
```bash
python -m pytest
```

## 폴더
- `newsbot/` 서버: `dart.py` DART, `alio.py` 알리오, `articles.py` 자사 기사, `mail.py` 메일, `llm.py` AI 호출·비용, `qa.py` 질문·정기 브리핑, `writing.py` 스타일북·초안, `rules.py` 분류, `auth.py` 로그인, `push.py` 웹 푸시, `app.py` API, `static/` 화면
- `config/` 감시 기업·키워드(`rules.toml`), 알리오 기관·항목(`alio.toml`)
- `scripts/windows/` 설치·자동 실행·전원 설정
- `review/` 기획서, 독립 검토 보고서, Codex 교차검증 요청문
- `docs/screenshots/` 화면 캡처 (예시 데이터)
