#!/usr/bin/env bash
# session-wrap / daily-wrap — Windows(Git Bash) 설치 스크립트
#
# 가이드(README.md) 2~7단계를 그대로 자동화한다.
#   - 기존 스킬 폴더와 settings.json 백업
#   - 스킬 파일 5개 설치 (LF 줄바꿈 강제, SKILL.md의 "사용자명" 치환)
#   - settings.json에 env 1개 + 훅 3개만 병합 (기존 설정 보존, 재실행해도 중복되지 않음)
#   - 문법 검사 후 결과를 표로 출력
#
# 사용법:
#   bash install.sh              설치
#   bash install.sh --dry-run    무엇이 바뀌는지만 출력하고 아무것도 쓰지 않음
set -euo pipefail

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/files"
CLAUDE_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS="$CLAUDE_ROOT/settings.json"
BACKUP_TAG="$(date +%Y%m%d-%H%M%S)"

die() { echo "[중단] $*" >&2; exit 1; }
run() { if [ "$DRY_RUN" = 1 ]; then echo "  (dry-run) $*"; else "$@"; fi; }

# --- 0단계: 사전 확인 -------------------------------------------------------
command -v jq >/dev/null 2>&1 || die "jq가 없습니다. 'winget install jqlang.jq' 후 터미널을 새로 여세요."
[ -d "$SRC_DIR" ] || die "원본 폴더가 없습니다: $SRC_DIR"

BASH_EXE=""
for cand in "/c/Program Files/Git/bin/bash.exe" "/c/Program Files (x86)/Git/bin/bash.exe" "$(command -v bash || true)"; do
  [ -n "$cand" ] && [ -x "$cand" ] && { BASH_EXE="$cand"; break; }
done
[ -n "$BASH_EXE" ] || die "bash 실행 파일을 찾지 못했습니다."

if command -v cygpath >/dev/null 2>&1; then
  BASH_EXE_WIN="$(cygpath -w "$BASH_EXE")"   # 백슬래시 경로
  CLAUDE_ROOT_M="$(cygpath -m "$CLAUDE_ROOT")" # 슬래시 경로
else
  BASH_EXE_WIN="$BASH_EXE"
  CLAUDE_ROOT_M="$CLAUDE_ROOT"
fi
USER_NAME="$(basename "$HOME")"

echo "HOME              : $HOME"
echo "CLAUDE_ROOT       : $CLAUDE_ROOT"
echo "bash.exe          : $BASH_EXE_WIN"
echo "훅 스크립트 경로  : $CLAUDE_ROOT_M/skills/..."
echo "사용자명 치환값   : $USER_NAME"
echo

# --- 1단계: 로그 폴더 -------------------------------------------------------
run mkdir -p "$HOME/ClaudeLogs/SessionWraps" "$HOME/ClaudeLogs/DailyWraps"

# --- 2단계: 백업 ------------------------------------------------------------
run mkdir -p "$CLAUDE_ROOT/skills"
for s in session-wrap daily-wrap; do
  if [ -d "$CLAUDE_ROOT/skills/$s" ]; then
    run cp -R "$CLAUDE_ROOT/skills/$s" "$CLAUDE_ROOT/skills/$s.backup-$BACKUP_TAG"
  fi
done
[ -f "$SETTINGS" ] && run cp "$SETTINGS" "$SETTINGS.backup-$BACKUP_TAG"
echo "백업 태그: $BACKUP_TAG"

# --- 3~4단계: 파일 5개 설치 -------------------------------------------------
run mkdir -p "$CLAUDE_ROOT/skills/session-wrap" "$CLAUDE_ROOT/skills/daily-wrap"

install_file() {   # $1 = files/ 기준 상대 경로
  local rel="$1" src="$SRC_DIR/$1" dest="$CLAUDE_ROOT/$1"
  [ -f "$src" ] || die "원본 파일 없음: $src"
  if [ "$DRY_RUN" = 1 ]; then
    echo "  (dry-run) install $rel -> $dest"
    return
  fi
  # CR 제거 + 사용자명 치환을 한 번에. 항상 LF, UTF-8로 저장된다.
  sed -e 's/\r$//' -e "s|사용자명|$USER_NAME|g" "$src" > "$dest"
  case "$rel" in *.sh) chmod +x "$dest" 2>/dev/null || true ;; esac
}

install_file "skills/session-wrap/SKILL.md"
install_file "skills/session-wrap/queue-session.sh"
install_file "skills/session-wrap/check-pending.sh"
install_file "skills/daily-wrap/SKILL.md"
install_file "skills/daily-wrap/check-due.sh"

# --- 5단계: settings.json 병합 ---------------------------------------------
[ -f "$SETTINGS" ] || { run mkdir -p "$CLAUDE_ROOT"; [ "$DRY_RUN" = 1 ] || echo '{}' > "$SETTINGS"; }
jq empty "$SETTINGS" 2>/dev/null || die "기존 settings.json이 올바른 JSON이 아닙니다. 백업($SETTINGS.backup-$BACKUP_TAG)을 확인하세요."

MERGE_PROGRAM='
def ours: "session-wrap/(queue-session|check-pending)\\.sh|daily-wrap/check-due\\.sh";
def strip_ours:
  (. // [])
  | map(.hooks = ((.hooks // []) | map(select(((.command // "") | test(ours)) | not))))
  | map(select((.hooks | length) > 0));
.env = ((.env // {}) + {"CLAUDE_CODE_GIT_BASH_PATH": $bashexe})
| .hooks = (.hooks // {})
| .hooks.SessionEnd = ((.hooks.SessionEnd | strip_ours) + [{
    hooks: [{type: "command", command: ("\"" + $bashexe + "\" \"" + $root + "/skills/session-wrap/queue-session.sh\""), timeout: 10}]
  }])
| .hooks.SessionStart = ((.hooks.SessionStart | strip_ours) + [{
    hooks: [
      {type: "command", command: ("\"" + $bashexe + "\" \"" + $root + "/skills/session-wrap/check-pending.sh\""), timeout: 5},
      {type: "command", command: ("\"" + $bashexe + "\" \"" + $root + "/skills/daily-wrap/check-due.sh\""), timeout: 5}
    ]
  }])
'

if [ "$DRY_RUN" = 1 ]; then
  echo "  (dry-run) settings.json 병합 결과 미리보기:"
  jq --arg bashexe "$BASH_EXE_WIN" --arg root "$CLAUDE_ROOT_M" "$MERGE_PROGRAM" "$SETTINGS"
else
  TMP_SETTINGS="$(mktemp "$CLAUDE_ROOT/.settings.XXXXXX")"
  jq --arg bashexe "$BASH_EXE_WIN" --arg root "$CLAUDE_ROOT_M" "$MERGE_PROGRAM" "$SETTINGS" > "$TMP_SETTINGS"
  jq empty "$TMP_SETTINGS" || { rm -f "$TMP_SETTINGS"; die "병합 결과가 올바른 JSON이 아닙니다. 원본은 그대로 두었습니다."; }
  mv -- "$TMP_SETTINGS" "$SETTINGS"
fi

# --- 6~7단계: 검증 ----------------------------------------------------------
echo
if [ "$DRY_RUN" = 1 ]; then
  echo "dry-run 이므로 검증을 건너뜁니다."
  exit 0
fi

printf '%-42s %s\n' "항목" "결과"
printf '%-42s %s\n' "------------------------------------------" "------"

check() {  # $1 = 라벨, 나머지 = 명령
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf '%-42s %s\n' "$label" "OK"
  else
    printf '%-42s %s\n' "$label" "FAIL"
    FAILED=1
  fi
}
FAILED=0

check "queue-session.sh 문법"  bash -n "$CLAUDE_ROOT/skills/session-wrap/queue-session.sh"
check "check-pending.sh 문법"  bash -n "$CLAUDE_ROOT/skills/session-wrap/check-pending.sh"
check "check-due.sh 문법"      bash -n "$CLAUDE_ROOT/skills/daily-wrap/check-due.sh"
check "settings.json JSON 검사" jq empty "$SETTINGS"

if grep -lU $'\r' "$CLAUDE_ROOT"/skills/session-wrap/*.sh "$CLAUDE_ROOT"/skills/daily-wrap/*.sh >/dev/null 2>&1; then
  printf '%-42s %s\n' "CR(줄바꿈) 검사" "FAIL — CR 남아 있음"
  FAILED=1
else
  printf '%-42s %s\n' "CR(줄바꿈) 검사" "OK"
fi

# 훅 단독 실행 테스트 (transcript가 없으므로 조용히 0으로 끝나야 정상)
if echo '{"session_id":"testsession12345","transcript_path":"C:/nonexistent.jsonl","cwd":"C:/tmp","reason":"test"}' \
   | bash "$CLAUDE_ROOT/skills/session-wrap/queue-session.sh" >/dev/null 2>&1; then
  printf '%-42s %s\n' "queue-session.sh 단독 실행" "OK"
else
  printf '%-42s %s\n' "queue-session.sh 단독 실행" "FAIL"
  FAILED=1
fi

echo
if [ "$FAILED" = 0 ]; then
  echo "설치 완료. Claude Code를 완전히 종료했다가 다시 열어 주세요."
  echo "백업 태그: $BACKUP_TAG"
else
  echo "일부 검사가 실패했습니다. 위 표를 확인하고, 필요하면 백업($BACKUP_TAG)으로 되돌리세요." >&2
  exit 1
fi
