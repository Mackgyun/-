#!/usr/bin/env bash
# SessionStart hook: report pending session-wrap count as factual context.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "[session-wrap] jq가 없어 대기 목록을 확인하지 못했습니다." >&2
  exit 2
fi

CLAUDE_ROOT="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
QUEUE_DIR="$CLAUDE_ROOT/.omc/pending-wraps"

[ -d "$QUEUE_DIR" ] || exit 0
chmod 700 "$QUEUE_DIR" 2>/dev/null || true

COUNT=$(find "$QUEUE_DIR" -maxdepth 1 -name '*.json' -type f 2>/dev/null | wc -l | tr -d ' ')
[ "${COUNT:-0}" -gt 0 ] || exit 0

MSG="[Session-Wrap 상태] 아직 정리하지 않은 세션이 ${COUNT}개 있습니다. 사용 가능한 명령: /session-wrap. 민감한 세션은 '빼' 또는 '제외'로 표시할 수 있습니다."

jq -nc \
  --arg ev "SessionStart" \
  --arg ctx "$MSG" \
  '{hookSpecificOutput: {hookEventName: $ev, additionalContext: $ctx}}'

exit 0
