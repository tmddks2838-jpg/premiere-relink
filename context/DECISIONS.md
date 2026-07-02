# DECISIONS — premiere-relink

> 중요한 결정을 내릴 때마다 맨 아래에 한 줄씩 append. 형식: `날짜 — 결정 (이유)`

- 원본 `.prproj`는 **절대 덮어쓰지 않는다.** 출력은 항상 `_relinked.prproj`이고, 먼저 타임스탬프 백업(`.backup-YYYYMMDD-HHMMSS-μs.prproj`)을 만든다. (데이터 유실 방지)
- tkinter(`app.py`) 폐기, Flask 웹 UI로 전환. (macOS Sequoia + 시스템 Python tkinter 8.5에서 Label 텍스트가 렌더링 안 됨)
- 파일 선택은 osascript `choose file`만 사용하고 `tell application "System Events"` 래퍼는 **금지.** (Automation 권한 오류 발생)
- ffprobe 탐색 순서: PyInstaller 번들 내부 → `~/.local/bin/ffprobe` → PATH. (`matcher.py:_ffprobe_bin()`)
