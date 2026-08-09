# Session Wrap + Daily Wrap — Windows 네이티브 설치 가이드

> 원본(하하선 @hahaseonha.ai)의 macOS 기준 가이드를 Windows 네이티브 Claude Code 환경에 맞게 수정한 버전입니다.
> 개인 설치용으로만 사용하세요.

이 폴더에는 가이드 본문과, 그대로 복사해 쓸 수 있는 파일 5개가 함께 들어 있습니다.

```
docs/session-wrap-windows/
├── README.md                     ← 이 문서
├── install.sh                    ← 2~7단계 자동화 스크립트 (선택)
└── files/
    ├── settings.hooks.json       ← 5단계에서 병합할 훅 조각
    └── skills/
        ├── session-wrap/
        │   ├── SKILL.md
        │   ├── queue-session.sh
        │   └── check-pending.sh
        └── daily-wrap/
            ├── SKILL.md
            └── check-due.sh
```

`files/skills/` 아래 구조는 `C:\Users\사용자명\.claude\skills\` 아래와 1:1로 대응합니다.
`.gitattributes`에서 `*.sh`를 `eol=lf`로 고정해 두었으므로, Windows에서 이 저장소를 클론해도 스크립트가 CRLF로 바뀌지 않습니다.

---

## 원본과 달라지는 점 (요약)

| 항목 | 원본(macOS) | Windows 네이티브 수정본 | 이유 |
|---|---|---|---|
| 셸 | 시스템 bash | Git Bash (`bash.exe`) | 네이티브 Claude Code는 Git Bash로 셸 명령을 실행 |
| 훅 명령 | `bash "경로"` | `"C:\Program Files\Git\bin\bash.exe" "경로"` | Git\bin이 PATH에 없으면 `bash` 호출이 실패하는 알려진 이슈 회피 |
| 어제 날짜 | `date -v-1d` | `date -d 'yesterday'` 우선 | Git Bash는 GNU date |
| 저장 폴더 | `~/Documents/...` | `%USERPROFILE%\ClaudeLogs\...` | Windows의 Documents는 OneDrive로 리디렉션되는 경우가 많음 |
| 데일리 파일명 | `YYYY-MM-DD-데일리랩.md` | `YYYY-MM-DD-daily-wrap.md` | Git Bash에서 한글 glob 매칭이 로케일에 따라 불안정 |
| 권한 | `chmod 700/600` 유효 | 사실상 무효 | NTFS에서 Git Bash의 chmod는 형식적 |
| 줄바꿈 | LF | **반드시 LF 유지** | CRLF면 `bad interpreter` / `$'\r'` 오류 |

---

## 0단계 — 사전 준비

### Git for Windows 및 bash.exe 경로 확인

PowerShell에서:

```powershell
git --version
Test-Path "C:\Program Files\Git\bin\bash.exe"
```

`True`가 나오면 그대로 진행하시면 됩니다. `False`라면 실제 설치 경로를 찾으세요.

```powershell
Get-ChildItem -Path C:\, D:\ -Filter bash.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 5 FullName
```

찾은 경로를 아래 모든 단계에서 `C:\Program Files\Git\bin\bash.exe` 대신 사용하세요.

### jq 설치

PowerShell(관리자 아님)에서:

```powershell
winget install jqlang.jq
```

설치 후 **터미널을 완전히 닫았다가 새로 여세요.** 그다음 Git Bash에서 확인합니다.

```bash
jq --version
```

`command not found`가 나오면 jq가 Git Bash PATH에 없는 것입니다. 이 경우 jq.exe를 `C:\Program Files\Git\usr\bin\`에 복사하면 확실합니다.

### 줄바꿈 설정

훅 스크립트가 CRLF로 저장되면 실행되지 않습니다. Git Bash에서 미리 설정해 두세요.

```bash
git config --global core.autocrlf input
```

---

## 1단계 — 저장 폴더 정하기

`~/Documents`는 쓰지 않습니다. Windows에서 이 경로는 OneDrive로 리디렉션되어 있는 경우가 많고, 그러면 작업 대화 요약이 클라우드로 자동 업로드됩니다. 인터뷰 대본이나 미공개 학회 자료가 오간 세션이라면 곤란해질 수 있습니다.

동기화되지 않는 로컬 폴더를 씁니다.

| 용도 | 경로 (Windows) | 경로 (Git Bash) |
|---|---|---|
| 세션 기록 | `C:\Users\사용자명\ClaudeLogs\SessionWraps` | `$HOME/ClaudeLogs/SessionWraps` |
| 데일리 기록 | `C:\Users\사용자명\ClaudeLogs\DailyWraps` | `$HOME/ClaudeLogs/DailyWraps` |

Git Bash에서 미리 만들어 둡니다.

```bash
mkdir -p "$HOME/ClaudeLogs/SessionWraps" "$HOME/ClaudeLogs/DailyWraps"
```

**본인 사용자명 확인:**

```bash
echo "$HOME"
```

이후 나오는 `사용자명` 자리에 이 값의 마지막 부분을 넣으세요.

---

## 2단계 — 백업

Claude Code를 완전히 종료한 뒤, **Git Bash**에서 실행합니다.

```bash
CLAUDE_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
BACKUP_TAG="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$CLAUDE_ROOT/skills"

[ -d "$CLAUDE_ROOT/skills/session-wrap" ] && \
  cp -R "$CLAUDE_ROOT/skills/session-wrap" "$CLAUDE_ROOT/skills/session-wrap.backup-$BACKUP_TAG"

[ -d "$CLAUDE_ROOT/skills/daily-wrap" ] && \
  cp -R "$CLAUDE_ROOT/skills/daily-wrap" "$CLAUDE_ROOT/skills/daily-wrap.backup-$BACKUP_TAG"

[ -f "$CLAUDE_ROOT/settings.json" ] && \
  cp "$CLAUDE_ROOT/settings.json" "$CLAUDE_ROOT/settings.json.backup-$BACKUP_TAG"

mkdir -p "$CLAUDE_ROOT/skills/session-wrap" "$CLAUDE_ROOT/skills/daily-wrap"
echo "백업 완료: $BACKUP_TAG"
```

---

## 3단계 — session-wrap 파일 3개

전체 내용은 이 폴더의 실제 파일을 그대로 복사해서 쓰시면 됩니다.

- [`files/skills/session-wrap/SKILL.md`](files/skills/session-wrap/SKILL.md)
- [`files/skills/session-wrap/queue-session.sh`](files/skills/session-wrap/queue-session.sh) — 원본에서 **Windows 경로 정규화 3줄이 추가**되었고, 아래 `cleanup` 종료 코드 버그가 함께 수정되었습니다.
- [`files/skills/session-wrap/check-pending.sh`](files/skills/session-wrap/check-pending.sh) — 원본과 동일하되 `chmod` 실패를 무시하도록 처리했습니다.

`SKILL.md`의 `사용자명` 자리는 1단계에서 확인한 본인 값으로 바꿔야 합니다. `.sh` 두 개는 `$HOME`을 쓰므로 치환할 것이 없습니다.

> **원본 대비 추가 수정 — `cleanup` 종료 코드**
>
> 원본의 `cleanup`은 `[ -n "$TMP_FILE" ] && [ -f "$TMP_FILE" ] && rm -f -- "$TMP_FILE"` 한 줄짜리입니다.
> 큐 등록에 성공하면 직전에 `TMP_FILE=""`이 되므로 이 줄의 첫 조건이 거짓이 되고, 함수는 상태 1로 끝납니다.
> bash는 **EXIT 트랩의 마지막 명령 상태로 스크립트 종료 코드를 덮어쓰기** 때문에, `exit 0`을 써 두었는데도
> 세션이 정상적으로 큐에 들어간 경우에만 훅이 `exit 1`로 보고됩니다. (bash 5.2 기준, Git Bash도 동일)
>
> 가이드 7단계의 단독 실행 테스트는 존재하지 않는 transcript 경로를 쓰기 때문에 트랩이 설치되기 전에
> 함수가 반환되고, 그래서 이 문제가 드러나지 않습니다. 이 저장소의 파일은 `cleanup`을 `if` 블록으로 바꾸고
> 끝에 `return 0`을 넣어 수정해 두었습니다.

수동으로 복사하려면 Git Bash에서:

```bash
CLAUDE_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
GUIDE_DIR="이 저장소를 클론한 경로/docs/session-wrap-windows"

cp "$GUIDE_DIR/files/skills/session-wrap/"* "$CLAUDE_ROOT/skills/session-wrap/"
sed -i "s|사용자명|$(basename "$HOME")|g" "$CLAUDE_ROOT/skills/session-wrap/SKILL.md"
```

---

## 4단계 — daily-wrap 파일 2개

- [`files/skills/daily-wrap/SKILL.md`](files/skills/daily-wrap/SKILL.md)
- [`files/skills/daily-wrap/check-due.sh`](files/skills/daily-wrap/check-due.sh) — **폴더 경로, 파일명, 어제 날짜 계산이 모두 수정**되었습니다.

```bash
cp "$GUIDE_DIR/files/skills/daily-wrap/"* "$CLAUDE_ROOT/skills/daily-wrap/"
sed -i "s|사용자명|$(basename "$HOME")|g" "$CLAUDE_ROOT/skills/daily-wrap/SKILL.md"
```

---

## 5단계 — settings.json 훅 병합

`C:\Users\사용자명\.claude\settings.json`에 [`files/settings.hooks.json`](files/settings.hooks.json)의 내용을 병합합니다. **기존 설정을 통째로 덮어쓰지 마세요.**
`사용자명` 3곳과 bash.exe 경로를 본인 환경에 맞게 바꾸세요.

```json
{
  "env": {
    "CLAUDE_CODE_GIT_BASH_PATH": "C:\\Program Files\\Git\\bin\\bash.exe"
  },
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"C:\\Program Files\\Git\\bin\\bash.exe\" \"C:/Users/사용자명/.claude/skills/session-wrap/queue-session.sh\"",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"C:\\Program Files\\Git\\bin\\bash.exe\" \"C:/Users/사용자명/.claude/skills/session-wrap/check-pending.sh\"",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "\"C:\\Program Files\\Git\\bin\\bash.exe\" \"C:/Users/사용자명/.claude/skills/daily-wrap/check-due.sh\"",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

> **왜 `bash` 대신 전체 경로인가:** Git for Windows를 기본 옵션으로 설치하면 `Git\cmd`만 PATH에 등록되고 `bash.exe`가 있는 `Git\bin`은 등록되지 않습니다. 이 상태에서 훅 명령을 `bash ...`로 쓰면 `'bash' is not recognized` 오류로 조용히 실패합니다. 전체 경로를 쓰면 이 문제를 우회할 수 있습니다.
>
> 실행 파일 경로는 백슬래시(JSON에서 `\\`), 스크립트 경로는 슬래시로 쓰는 조합이 가장 안정적입니다.

문법 검증:

```bash
CLAUDE_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
jq empty "$CLAUDE_ROOT/settings.json" && echo "JSON OK"
```

---

## 6단계 — 줄바꿈 정리 (Windows 필수)

스크립트 3개가 CRLF로 저장되었으면 실행되지 않습니다. Git Bash에서 확실히 LF로 만들어 두세요.

```bash
CLAUDE_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

for f in \
  "$CLAUDE_ROOT/skills/session-wrap/queue-session.sh" \
  "$CLAUDE_ROOT/skills/session-wrap/check-pending.sh" \
  "$CLAUDE_ROOT/skills/daily-wrap/check-due.sh"
do
  sed -i 's/\r$//' "$f"
  chmod +x "$f" 2>/dev/null || true
done
echo "줄바꿈 정리 완료"
```

CR이 남아 있는지 확인:

```bash
grep -lU $'\r' "$CLAUDE_ROOT"/skills/*/*.sh || echo "CR 없음 — 정상"
```

---

## 7단계 — 검증

### 문법 검사

```bash
CLAUDE_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
bash -n "$CLAUDE_ROOT/skills/session-wrap/queue-session.sh" && echo "queue-session OK"
bash -n "$CLAUDE_ROOT/skills/session-wrap/check-pending.sh" && echo "check-pending OK"
bash -n "$CLAUDE_ROOT/skills/daily-wrap/check-due.sh" && echo "check-due OK"
jq empty "$CLAUDE_ROOT/settings.json" && echo "settings OK"
```

### 훅 단독 실행 테스트

실제 세션 없이 queue-session.sh가 도는지 확인합니다. (아래는 일부러 실패해야 정상입니다 — transcript가 없으므로 조용히 종료됩니다.)

```bash
echo '{"session_id":"testsession12345","transcript_path":"C:/nonexistent.jsonl","cwd":"C:/tmp","reason":"test"}' \
  | bash "$CLAUDE_ROOT/skills/session-wrap/queue-session.sh"
echo "exit code: $?"
```

`exit code: 0`이면 스크립트 자체는 정상입니다.

다만 이 테스트는 transcript가 없어서 **큐 등록 직전에 끝나는 경로**만 확인합니다. 실제로 큐가 만들어지는
성공 경로까지 보려면 5줄 이상짜리 가짜 transcript로 한 번 더 확인하세요.

```bash
printf 'l1\nl2\nl3\nl4\nl5\nl6\n' > /tmp/fake-transcript.jsonl
echo '{"session_id":"testsession12345","transcript_path":"/tmp/fake-transcript.jsonl","cwd":"C:/tmp","reason":"test"}' \
  | bash "$CLAUDE_ROOT/skills/session-wrap/queue-session.sh"
echo "exit code: $?"
cat "$CLAUDE_ROOT/.omc/pending-wraps/testsession12345.json"
```

여기서도 `exit code: 0`이어야 하고, JSON 파일이 만들어져 있어야 합니다. 확인이 끝나면 테스트용 큐를 지웁니다.

```bash
rm -f "$CLAUDE_ROOT/.omc/pending-wraps/testsession12345.json" /tmp/fake-transcript.jsonl
```

check-pending.sh와 check-due.sh는 직접 실행해 봅니다.

```bash
bash "$CLAUDE_ROOT/skills/session-wrap/check-pending.sh"; echo "exit: $?"
bash "$CLAUDE_ROOT/skills/daily-wrap/check-due.sh"; echo "exit: $?"
```

대기 세션이나 밀린 데일리 기록이 없으면 아무 출력 없이 `exit: 0`이 정상입니다.

### 실사용 테스트

1. Claude Code를 완전히 종료했다가 다시 엽니다.
2. 민감하지 않은 짧은 테스트 대화를 5개 메시지 이상 진행합니다.
3. `/clear`로 세션을 전환합니다.
4. 대기 목록이 생겼는지 확인합니다.

```bash
ls -l "$CLAUDE_ROOT/.omc/pending-wraps"
```

5. 파일이 있으면 `/session-wrap` 실행 → `C:\Users\사용자명\ClaudeLogs\SessionWraps` 확인
6. `/daily-wrap` 실행 → `C:\Users\사용자명\ClaudeLogs\DailyWraps` 확인

> 원본 가이드의 `drwx------`, `-rw-------` 권한 확인 단계는 Windows에서는 의미가 없습니다. NTFS에서 Git Bash의 chmod는 실제 ACL을 바꾸지 않습니다. 대신 이 폴더들이 본인 사용자 프로필 안에 있고, 동기화 대상이 아니라는 점으로 보호됩니다.

---

## 자동 설치 (2~7단계 한 번에)

수동 복사 대신 [`install.sh`](install.sh)를 쓸 수 있습니다. Git Bash에서:

```bash
bash docs/session-wrap-windows/install.sh --dry-run   # 무엇이 바뀌는지만 확인
bash docs/session-wrap-windows/install.sh             # 실제 설치
```

이 스크립트가 하는 일:

1. `bash.exe` 경로와 `$HOME`을 자동 감지하고 `사용자명`을 치환합니다.
2. 기존 `skills/session-wrap`, `skills/daily-wrap`, `settings.json`을 타임스탬프 태그로 백업합니다.
3. 파일 5개를 LF·UTF-8로 설치합니다.
4. `settings.json`에 `env` 1개와 훅 3개만 **병합**합니다. 기존 설정은 그대로 두고, 이 스크립트가 넣은 훅은 재실행 시 중복되지 않도록 먼저 제거한 뒤 다시 넣습니다.
5. 문법 검사와 CR 검사 결과를 표로 출력합니다. 하나라도 실패하면 0이 아닌 코드로 종료합니다.

---

## 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `'bash' is not recognized` | Git\bin이 PATH에 없음 | 훅 명령을 bash.exe 전체 경로로 변경 (5단계) |
| `$'\r': command not found` | CRLF 줄바꿈 | 6단계 sed 실행 |
| `jq: command not found` | Git Bash PATH에 jq 없음 | jq.exe를 `C:\Program Files\Git\usr\bin\`에 복사 |
| 대기 목록이 안 생김 | transcript 5줄 미만 또는 경로 인식 실패 | 더 긴 대화로 재시도, `queue-session.sh`의 경로 정규화 확인 |
| 큐는 잘 만들어지는데 SessionEnd 훅이 실패로 표시됨 | 원본 `cleanup`이 EXIT 트랩에서 상태 1을 반환 | `cleanup`을 `if` 블록 + `return 0`으로 교체 (3단계 주석 참고) |
| 알림이 너무 자주 뜸 | `matcher` 생략으로 resume·`/clear`·compaction에서도 실행 | 정상 동작. 거슬리면 SessionStart 훅만 제거 |
| 기록이 OneDrive에 올라감 | 저장 폴더가 리디렉션된 Documents | 1단계 경로로 변경 |

---

## Claude Code에 붙여넣을 설치 프롬프트

이 폴더를 Claude Code에 첨부하거나 이 문서를 붙여넣은 뒤, 아래처럼 요청하면 됩니다.

```
첨부한 Windows 네이티브 설치 가이드대로 session-wrap / daily-wrap을 설치해줘.

작업 순서:
1. echo $HOME으로 내 사용자명을 먼저 확인하고, 가이드의 "사용자명" 자리를 전부 실제 값으로 치환할 것
2. Test-Path로 bash.exe 실제 경로를 확인하고 마찬가지로 치환할 것
3. 2단계 백업을 먼저 실행하고 백업 태그를 보고할 것
4. 파일 5개를 생성하되 .sh는 반드시 LF 줄바꿈, UTF-8로 저장할 것
5. settings.json은 기존 설정을 보존하면서 env 1개와 훅 3개만 병합할 것
6. 6단계 CRLF 정리와 7단계 문법 검사를 전부 실행하고 결과를 표로 보여줄 것
7. 중간에 실패하면 진행을 멈추고 원인을 보고할 것

저장 폴더는 가이드의 ClaudeLogs 경로를 그대로 쓴다.
```

---

## 보안 체크 (설치 후 한 번)

- [ ] `ClaudeLogs` 폴더가 OneDrive 동기화 대상이 아닌지 확인 (OneDrive 설정 → 백업 → 폴더 백업 관리)
- [ ] 인터뷰 원고, 미공개 학회 자료, 계약 관련 대화가 오간 세션은 `/session-wrap`을 돌리지 않기
- [ ] 실수로 요약된 경우 해당 `.md` 파일을 삭제하고, 큐도 함께 확인
- [ ] 회사 정책상 작업 대화 로그를 로컬에 남겨도 되는지 확인
