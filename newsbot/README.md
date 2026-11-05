# 청년의사 브리핑

DART 공시를 24시간 수집해 보건의료 기업 공시만 골라 보여주고, 중요한 건은 PC 오른쪽 아래 팝업과 휴대폰 푸시로 알려주는 자체 웹앱입니다. 알리오, 보도자료 메일, 질문 답변, 기사 초안은 다음 단계에서 붙입니다.

## 지금 되는 것 (1단계)
- **DART 수집**: 5분마다 최근 300건을 다시 확인하고, 매시간 이틀치 전체를 대조합니다. DART는 공시 제출 후 약 15분 뒤에 공개되고 순서가 뒤섞일 수 있어서, 늦게 나타난 공시도 놓치지 않게 만들었습니다.
- **보건의료 기업만**: `config/rules.toml`의 감시 기업 목록이 기준이고, 목록 밖 회사는 업종코드(의약품·의료기기 제조, 보건업, 의약 연구개발)로 보충합니다.
- **중요도 분류**: 중요(빨강)·일반(노랑)·기록(회색). 정정공시는 '정정' 표시를 붙이고 팝업은 보내지 않습니다.
- **웹앱 화면**: 오늘의 브리핑 요약, 피드, 상세, [내가 쓸게요], 검색·필터, 키보드 단축키(J/K/Enter/C), 다크 모드, 글자 크기 조절, 휴대폰 화면
- **알림**: 웹 푸시로 PC는 Windows 알림(오른쪽 아래), 휴대폰은 홈 화면 앱 알림. 처음엔 `ALERT_MODE=log`(기록만)으로 2주간 알림량을 재고 나서 `notify`로 켭니다.
- **다중 사용자**: 관리자가 만든 1회용 초대 링크로 가입, 비밀번호 해시 저장, 로그인 5회 실패 시 10분 잠금
- **관리자 화면**: 수집 상태, DART 호출 수, 초대 링크, 사용자 비활성화, 최근 기록
- **외부 감시용 주소**: `/healthz` (수집이 20분 넘게 멈추면 503)

## 아직 안 되는 것
- 질문 창, 기사 초안: AI API 키를 받으면 붙입니다 (화면에 자리는 있음)
- 보도자료 메일: 법무·IT 검토 후
- 알리오: 공공데이터포털 결산 자료 비교부터
- 외부(휴대폰) 접속: 보안 터널 설정 후. 그 전까지는 이 노트북의 브라우저에서만 알림이 됩니다

## 노트북(Windows)에 설치하기

1. **Python 3.11 이상** 설치: https://www.python.org/downloads/ (설치 화면에서 'Add python.exe to PATH' 체크)
2. 이 저장소를 받습니다.
   ```bash
   git clone -b claude/eloquent-fermi-pj12x0 https://github.com/Mackgyun/-.git chungnyun-bot
   ```
3. `chungnyun-bot\newsbot` 폴더에서 PowerShell을 열고 설치 스크립트를 실행합니다.
   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\windows\setup.ps1
   ```
4. 생긴 `.env` 파일을 메모장으로 열어 `DART_API_KEY=`에 OpenDART 인증키를 넣습니다. 키가 없어도 화면은 뜹니다.
5. 관리자 계정을 만듭니다.
   ```bash
   .\.venv\Scripts\python.exe -m newsbot create-admin 내아이디 --name 내이름
   ```
6. 실행하고 브라우저에서 http://localhost:8000 을 엽니다.
   ```bash
   scripts\windows\start.bat
   ```
7. **24시간 실행**: 관리자 권한 PowerShell에서 두 스크립트를 실행합니다. 덮개를 닫아도 안 꺼지게 하고, 부팅하면 로그인 없이 자동 시작합니다.
   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\windows\power-settings.ps1
   ```
   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\windows\install-autostart.ps1
   ```

> Windows 스크립트는 클라우드 환경에서 작성해 실제 Windows에서는 아직 실행해 보지 않았습니다. 오류가 나면 메시지를 그대로 알려주세요.

## 자주 쓰는 명령
| 명령 | 하는 일 |
| --- | --- |
| `python -m newsbot` | 웹앱 + 수집 실행 |
| `python -m newsbot create-admin 아이디` | 관리자 계정 만들기 |
| `python -m newsbot invite` | 기자 초대 링크 만들기 (관리자 화면에서도 가능) |
| `python -m newsbot poll` | DART 한 번 수집해 보기 (알림 없음) |

## 알아둘 점
- **알림은 HTTPS 또는 localhost에서만 동작합니다.** 같은 사무실 PC가 `http://노트북IP:8000`으로 접속하면 화면은 보이지만 푸시 알림은 켜지지 않습니다. 다른 기기 알림은 보안 터널(HTTPS)을 연결한 뒤 가능합니다.
- **아이폰**은 Safari에서 '홈 화면에 추가'로 설치한 앱에서만 알림을 받을 수 있습니다 (iOS 16.4 이상).
- 감시 기업 목록(`config/rules.toml`)은 예시입니다. 회사명은 DART 표기와 같아야 하니 출입처에 맞게 고쳐 주세요.
- 데이터는 `data/` 폴더(SQLite)에 쌓입니다. 이 폴더를 주기적으로 NAS에 백업하세요.

## 개발
```bash
pip install -r requirements-dev.txt
```
```bash
python -m pytest
```

## 폴더
- `newsbot/` 서버 코드: `dart.py` 수집, `rules.py` 분류, `app.py` 웹 API, `auth.py` 로그인, `push.py` 웹 푸시, `static/` 화면
- `config/rules.toml` 감시 기업·중요도 키워드
- `scripts/windows/` 설치·자동 실행·전원 설정
- `review/` 기획서, 독립 검토 보고서, Codex 교차검증 요청문
