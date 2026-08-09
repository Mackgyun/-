#!/usr/bin/env bash
# SessionStart hook: report overdue daily wraps as factual context.
# Windows(Git Bash) adapted.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "[daily-wrap] jq가 없어 데일리 기록 상태를 확인하지 못했습니다." >&2
  exit 2
fi

SESSION_WRAP_DIR="$HOME/ClaudeLogs/SessionWraps"
DAILY_WRAP_DIR="$HOME/ClaudeLogs/DailyWraps"

TODAY=$(date '+%Y-%m-%d')
# Git Bash는 GNU date이므로 -d를 먼저 시도한다.
YESTERDAY=$(date -d 'yesterday' '+%Y-%m-%d' 2>/dev/null || date -v-1d '+%Y-%m-%d')
HOUR=$(date '+%H')
HOUR=$((10#$HOUR))

TODAY_FILE="$DAILY_WRAP_DIR/$TODAY-daily-wrap.md"
YESTERDAY_FILE="$DAILY_WRAP_DIR/$YESTERDAY-daily-wrap.md"

count_wraps_for_date() {
  local target_date="$1"
  local count=0
  if [ -d "$SESSION_WRAP_DIR" ]; then
    count=$(find "$SESSION_WRAP_DIR" -maxdepth 1 -name "${target_date}-*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
  fi
  echo "${count:-0}"
}

NEEDED=""

if [ ! -f "$YESTERDAY_FILE" ]; then
  YESTERDAY_WRAPS=$(count_wraps_for_date "$YESTERDAY")
  if [ "$YESTERDAY_WRAPS" -gt 0 ]; then
    NEEDED="$YESTERDAY (어제, ${YESTERDAY_WRAPS}개 세션)"
  fi
fi

if [ "$HOUR" -ge 23 ] && [ ! -f "$TODAY_FILE" ]; then
  TODAY_WRAPS=$(count_wraps_for_date "$TODAY")
  if [ "$TODAY_WRAPS" -gt 0 ]; then
    if [ -n "$NEEDED" ]; then
      NEEDED="$NEEDED + $TODAY (오늘, ${TODAY_WRAPS}개 세션)"
    else
      NEEDED="$TODAY (오늘, ${TODAY_WRAPS}개 세션)"
    fi
  fi
fi

[ -n "$NEEDED" ] || exit 0

MSG="[Daily-Wrap 상태] 아직 데일리 기록이 없는 날짜: ${NEEDED}. 사용 가능한 명령: 어제는 /daily-wrap 어제, 오늘은 /daily-wrap."

jq -nc \
  --arg ev "SessionStart" \
  --arg ctx "$MSG" \
  '{hookSpecificOutput: {hookEventName: $ev, additionalContext: $ctx}}'

exit 0
