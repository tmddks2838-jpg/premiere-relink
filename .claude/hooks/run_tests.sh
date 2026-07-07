#!/bin/bash
# premiere-relink Stop 훅: pytest 실행 후 실패할 때만 알림(비차단).
# 성공하면 조용히 통과. 자동 커밋 훅과 부딪히지 않도록 항상 exit 0.
DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$DIR" || exit 0

OUT="$(python3 -m pytest -q 2>&1)"
CODE=$?

if [ $CODE -ne 0 ]; then
  SUMMARY="$(echo "$OUT" | tail -3 | tr '\n' ' ' | cut -c1-180)"
  osascript -e "display notification \"❌ pytest 실패 — $SUMMARY\" with title \"premiere-relink 테스트\" sound name \"Basso\"" 2>/dev/null || true
  echo "❌ pytest 실패 (아래 마지막 20줄):" >&2
  echo "$OUT" | tail -20 >&2
fi

exit 0
