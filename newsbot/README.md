# 청년의사 브리핑

DART 공시와 알리오(공공기관·국립대병원) 공시를 24시간 모아 보건의료 관련 건만 보여주고, 중요한 건은 PC 오른쪽 아래 팝업과 휴대폰 푸시로 알리는 자체 웹앱입니다. AI로 질문에 답하고, 기자별 문체로 기사 초안을 쓰고, 보도자료 메일을 모아 봅니다. 시범사업 제안서의 기능을 모두 담았습니다.

## 기능

| 기능 | 내용 | 필요한 것 |
| --- | --- | --- |
| DART 공시 | 5분마다 최근 300건 재확인 + 매시간 이틀치 대조(공개 지연·순서 뒤섞임 대응). 감시 기업 목록 + 보건의료 업종코드로 선별, 중요·일반·기록 3단계, 정정공시 표시 | DART 키 |
| 알리오 | 국립대병원·공공 의료기관 25곳의 수시공시(임원, 이사회, 감사, 징계, 경영평가) 감시, 결산(손익계산서) 전년 대비 표 | 없음 (`config/alio.toml`) |
| 알림 | PC는 Windows 알림(오른쪽 아래), 휴대폰은 홈 화면 앱 푸시. 중요 공시만, 정정은 제외. 처음엔 '기록만' 모드 | HTTPS 또는 localhost |
| 오늘 요약 | 한 문장 요약과 숫자 한 줄, 하루 4번 정기 브리핑(AI 키가 있으면 AI 요약), 명령 팔레트(Ctrl K) | - |
| 분류·담당 | 미확인·중요·내 출입처·담당 미지정·알리오 목록, 키보드 분류(J/K·E·C·Z), 담당 지정으로 중복 취재 방지, 기사화 기록 | - |
| 질문 | 공시·알리오 결산·DART 재무·과거 기사·(켜면) 내 메일을 AI가 찾아보고 출처와 함께 답 | AI 키 (시험은 무료 Gemini·Ollama) |
| 기사 초안 | 공시 원문·보도자료·메모로 초안. 내 스타일북 + 비슷한 내 기사 참고. 원자료에 같은 숫자가 없으면 빨간색 표시(숫자 단위로 정확히 대조) | AI 키 |
| 스타일북 | 내 기사(docdocdoc.co.kr)를 가져와 AI가 문체를 분석. 직접 고칠 수 있음 | AI 키 |
| 보도자료 메일 | 지정한 메일함 하나만 읽기 전용으로 가져옴, 엠바고 문구 자동 표시. **기본은 꺼짐** | 법무·IT 검토 후 `MAIL_ENABLED=true` |
| 관리자 | 초대 링크, 사용자 관리, 기자별 월 AI 한도(0원은 사용 금지), 수집 상태, **시범사업 성과**(담당·기사화·질문·초안·AI 비용·가동률) | - |
| 운영 | 매일 새벽 4시 자동 백업(최근 14일), 로그 파일(`data/logs`, 인증키 가림), 알림 재시도, 노트북이 꺼져 있던 기간 이어서 수집 | - |

## 노트북(Windows)에 설치하기

1. **Python 3.11 이상** 설치: https://www.python.org/downloads/ (설치 화면에서 'Add python.exe to PATH' 체크)
2. 저장소를 받습니다. git이 없으면 GitHub 저장소 화면의 'Code → Download ZIP'으로 받아 압축을 풀어도 됩니다(브랜치 `claude/eloquent-fermi-pj12x0` 선택).
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
   - 돈 들이지 않고 시험하려면 아래 '무료 AI로 시험하기'를 보세요.
5. 관리자 계정을 만듭니다.
   ```bash
   .\.venv\Scripts\python.exe -m newsbot create-admin 내아이디 --name 내이름
   ```
6. 실행하고 브라우저에서 http://localhost:8000 을 엽니다. 창을 닫으면 멈춥니다. 7번 자동 실행을 등록한 뒤에는 `start.bat`를 함께 켜지 마세요(같은 포트를 씁니다).
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

## 무료 AI로 시험하기
유료 키 없이 질문·초안·스타일북·AI 브리핑을 시험할 수 있습니다. 비용은 0원으로 기록됩니다.

| 방식 | 설정 | 장단점 |
| --- | --- | --- |
| **Gemini 무료 등급** (권장) | [Google AI Studio](https://aistudio.google.com/apikey)에서 키 발급(카드 불필요) → `.env`에 `LLM_PROVIDER=gemini`, `GEMINI_API_KEY=발급한키` | 설치 없음, 품질 좋음. 분당·하루 요청 수 제한이 있고, **무료 등급은 입력 내용이 Google 제품 개선에 쓰일 수 있음** → 공개 공시처럼 외부에 나가도 되는 자료로만 시험 |
| **Ollama** (이 PC에서 실행) | [ollama.com](https://ollama.com) 설치 → `ollama pull qwen3:8b` → `.env`에 `LLM_PROVIDER=ollama` | 키 없음, 자료가 밖으로 나가지 않음. 메모리 16GB 이상 권장, 노트북에서는 느리고 품질이 낮음 |

모델 이름은 `.env`의 `GEMINI_MODEL_*`, `OLLAMA_MODEL_*`로 바꿀 수 있습니다(기본값은 2026년 11월 Google 요금표의 무료 모델). 보도자료 메일 요약(`MAIL_AI_SUMMARY`)은 무료 등급으로 켜지 마세요.

DART 인증키도 무료입니다. [OpenDART](https://opendart.fss.or.kr)에서 인증키 신청을 하면 바로 나옵니다(하루 2만 건).

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
- 외부 감시 서비스(UptimeRobot 등)에 `https://briefing.도메인/healthz`를 등록하면 DART·알리오 수집이나 정기 브리핑이 멈췄을 때 알려줍니다(503과 함께 멈춘 항목 표시).
- 로그인 잠금은 터널이 알려 주는 실제 접속 IP 기준입니다(`CF-Connecting-IP`). 터널 없이 공유기 포트를 직접 여는 방식은 쓰지 마세요.

## 명령
| 명령 | 하는 일 |
| --- | --- |
| `python -m newsbot` | 웹앱 + 수집 실행 |
| `python -m newsbot create-admin 아이디` | 관리자 계정 만들기 |
| `python -m newsbot invite` | 초대 링크 만들기 (관리자 화면에서도 가능) |
| `python -m newsbot poll` | DART 한 번 수집해 보기 (알림 없음) |
| `python -m newsbot reset-password 아이디` | 비밀번호 다시 정하기 (기존 로그인은 끊김) |
| `python -m newsbot backup [폴더]` | DB와 암호화 키 백업 (실행 중에도 안전) |

## 알아둘 점
- **아이폰**은 Safari '홈 화면에 추가'로 설치한 앱에서만 알림을 받습니다 (iOS 16.4 이상).
- `config/rules.toml`의 감시 기업, `config/alio.toml`의 기관 이름은 예시입니다. 표기가 다르면 '공공기관 결산' 화면 아래 '감시 기관 목록'에 '찾지 못한 이름'으로 표시됩니다. 설정 파일을 바꾸면 프로그램을 다시 시작하세요. 기관·항목을 새로 추가하면 그 기관의 과거 공시는 알림 없이 목록에만 들어갑니다.
- 알리오는 경영공시용 공식 API가 없어 사이트의 조회 방식을 씁니다. 사이트가 바뀌면 수집이 멈추고 관리자 화면에 오류가 뜹니다. 복지부가 국립대병원의 공공기관 지정 해제를 추진 중이라는 보도가 있어 공시 범위가 바뀔 수 있습니다.
- 자사 기사 수집은 사내 분석용이며 요청 사이 2초씩 쉽니다. 회사가 ND소프트에서 기사 DB를 받으면 그쪽으로 바꾸는 것이 좋습니다.
- AI가 쓴 초안과 답변은 반드시 원문으로 확인한 뒤 씁니다. 원자료에 없는 숫자는 빨간색으로 표시됩니다.
- 데이터는 `data/` 폴더(SQLite, 암호화 키 포함)에 있습니다. 매일 새벽 4시 `data/backups`에 DB 복사본이 생기니(최근 14개), 이 폴더와 `secret.key`·`vapid_private.pem`을 NAS에 주기적으로 복사하세요. 실행 중인 `newsbot.db` 파일을 직접 복사하면 깨질 수 있으니 백업 폴더나 `backup` 명령을 쓰세요. 이 폴더는 외부에 공유하지 마세요.
- 로그는 `data/logs/newsbot.log`(5MB씩 5개 순환)에 남고, 인증키는 `***`로 가려집니다.
- DART 하루 호출 한도에 걸리면 다음 날 0시 5분까지 쉬었다가 다시 시작합니다. 노트북이 꺼져 있었으면 마지막으로 수집한 날부터(최대 7일) 이어서 훑고, 밀린 중요 공시가 많으면 기자별로 묶어 알림 한 통으로 보냅니다.
- Claude Sonnet·Opus 호출에는 안전 분류기가 요청을 거절하면 서버가 다른 모델로 다시 처리하는 옵션(`fallbacks: "default"`)을 켜 두었습니다.

## 디자인과 문구
- 화면 설계와 레퍼런스, AI 티 나는 요소를 걷어낸 기록: `docs/design-system.md`
- 문구 원칙과 용어집: `docs/ux-writing.md`
- 화면 캡처(예시 데이터): `docs/screenshots/`

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
- `review/` 기획서, 독립 검토 보고서(기획·동작 점검), Codex 교차검증 요청문
- `docs/screenshots/` 화면 캡처 (예시 데이터)
