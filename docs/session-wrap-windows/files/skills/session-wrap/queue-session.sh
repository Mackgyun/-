#!/usr/bin/env bash
# SessionEnd hook: save minimal session metadata to a private local queue.
# Windows(Git Bash) adapted.
set -euo pipefail
umask 077

if ! command -v jq >/dev/null 2>&1; then
  echo "[session-wrap] jq가 없어 세션을 큐에 넣지 못했습니다." >&2
  exit 2
fi

INPUT=$(cat)

if ! jq -e . >/dev/null 2>&1 <<<"$INPUT"; then
  echo "[session-wrap] SessionEnd 훅 입력이 올바른 JSON이 아닙니다." >&2
  exit 2
fi

SESSION_ID=$(jq -er '.session_id | select(type == "string" and length > 0)' <<<"$INPUT") || {
  echo "[session-wrap] session_id가 없어 큐 등록을 건너뜁니다." >&2
  exit 2
}

TRANSCRIPT_PATH=$(jq -er '.transcript_path | select(type == "string" and length > 0)' <<<"$INPUT") || {
  echo "[session-wrap] transcript_path가 없어 큐 등록을 건너뜁니다." >&2
  exit 2
}

CWD=$(jq -r 'if (.cwd | type) == "string" then .cwd else "" end' <<<"$INPUT")
REASON=$(jq -r 'if (.reason | type) == "string" then .reason else "unknown" end' <<<"$INPUT")

# --- Windows 경로 정규화: 백슬래시 -> 슬래시 ---
TRANSCRIPT_PATH="${TRANSCRIPT_PATH//\\//}"
CWD="${CWD//\\//}"
# ---------------------------------------------

if [[ ! "$SESSION_ID" =~ ^[A-Za-z0-9_-]{8,128}$ ]]; then
  echo "[session-wrap] 안전하지 않은 session_id 형식이라 큐 등록을 거부했습니다." >&2
  exit 2
fi

[ -f "$TRANSCRIPT_PATH" ] || exit 0

LINES=$(wc -l < "$TRANSCRIPT_PATH" | tr -d ' ')
[ "${LINES:-0}" -ge 5 ] || exit 0

CLAUDE_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
QUEUE_DIR="$CLAUDE_ROOT/.omc/pending-wraps"
mkdir -p "$QUEUE_DIR"
chmod 700 "$QUEUE_DIR" 2>/dev/null || true

DEST="$QUEUE_DIR/$SESSION_ID.json"
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  exit 0
fi

TMP_FILE=$(mktemp "$QUEUE_DIR/.queue.XXXXXX")
cleanup() {
  # 반드시 0으로 끝나야 한다. EXIT 트랩의 마지막 명령 상태가 스크립트 종료 코드를
  # 덮어쓰기 때문에, 여기서 실패하면 큐 등록에 성공해도 훅이 exit 1로 보고된다.
  if [ -n "${TMP_FILE:-}" ] && [ -f "$TMP_FILE" ]; then
    rm -f -- "$TMP_FILE"
  fi
  return 0
}
trap cleanup EXIT HUP INT TERM

ISO_NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

jq -n \
  --arg sid "$SESSION_ID" \
  --arg tp "$TRANSCRIPT_PATH" \
  --arg cwd "$CWD" \
  --arg reason "$REASON" \
  --arg ts "$ISO_NOW" \
  '{session_id: $sid, transcript_path: $tp, cwd: $cwd, reason: $reason, ended_at: $ts, queued_at: $ts}' \
  > "$TMP_FILE"

chmod 600 "$TMP_FILE" 2>/dev/null || true
mv -- "$TMP_FILE" "$DEST"
TMP_FILE=""

exit 0
