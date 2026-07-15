# DECISIONS — premiere-relink

> 중요한 결정을 내릴 때마다 맨 아래에 한 줄씩 append. 형식: `날짜 — 결정 (이유)`

- 원본 `.prproj`는 **절대 덮어쓰지 않는다.** 출력은 항상 `_relinked.prproj`이고, 먼저 타임스탬프 백업(`.backup-YYYYMMDD-HHMMSS-μs.prproj`)을 만든다. (데이터 유실 방지)
- tkinter(`app.py`) 폐기, Flask 웹 UI로 전환. (macOS Sequoia + 시스템 Python tkinter 8.5에서 Label 텍스트가 렌더링 안 됨)
- 파일 선택은 osascript `choose file`만 사용하고 `tell application "System Events"` 래퍼는 **금지.** (Automation 권한 오류 발생)
- ffprobe 탐색 순서: PyInstaller 번들 내부 → `~/.local/bin/ffprobe` → PATH. (`matcher.py:_ffprobe_bin()`)
- 맥 배포는 유니버설 빌드(Intel+Apple Silicon)로 통일한다. (한국 편집자 인텔 맥 잔존 + AS 네이티브 둘 다 커버, Rosetta 의존 회피)
- 서명/공증($99)은 무료 배포로 수요 검증 후 결정한다. 당장은 미서명 zip + "그래도 열기" 안내로 배포.
- 2026-07-02 — 배포 채널: 구글 드라이브(zip) + 노션 안내 페이지로 결정. 카톡방엔 노션 링크만 공유. (링크 하나로 버전 교체 관리)
- 2026-07-02 — 설치 안내는 터미널 방식(`xattr -cr`)을 메인으로, GUI "그래도 열기"는 FAQ로. 스크린샷 없이 글로만 안내. (`docs/notion-배포페이지.md`)
- 2026-07-02 — **v0.1 첫 배포 완료** (AI 스터디방·커뮤니티 오픈카톡). 이제 피드백 수집 단계.
- 2026-07-15: .venv 생성(ruff·pytest·pytest-cov) — 전역 프리커밋 훅 게이트 실효화, CI 워크플로 추가(ruff+pytest+coverage). 스타일 위반 8건 정리(세미콜론 분리, scripts E402는 per-file-ignores).
