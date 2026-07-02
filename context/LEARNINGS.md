# LEARNINGS — premiere-relink

> 삽질·발견을 그때그때 맨 아래에 한 줄씩 append. 형식: `날짜 — 배운 점`

- 한국어 파일명은 HFS+ NFD를 쓰므로, analyze 단계에서 NFC/NFD/NFKC 정규화를 **모두** 시도해야 매칭이 된다.
- macOS에서 부트볼륨이 `/Volumes/<이름>/Users/...`로 보일 때가 있다 → `/Users/...`로 정규화해야 경로가 맞는다.
- 이름이 바뀐 파일은 파일명으로 못 잡으므로 ffprobe duration 매칭으로 ASK/MISSING 처리한다.
- 유니버설(Intel+AS) 빌드: CLT 파이썬·표준확장·markupsafe는 이미 유니버설. 걸림돌은 ffprobe(arm64 전용) 하나였음 → static_ffmpeg 출처(zackees/ffmpeg_bins)의 x86_64+arm64 바이너리를 `lipo -create`로 합쳐 유니버설 ffprobe 생성 후 `~/.local/bin/ffprobe`에 배치, spec의 target_arch="universal2"로 빌드. 검증은 `arch -x86_64`/`arch -arm64`로 각 슬라이스 실행 확인.
- 미서명 앱의 "그래도 열기"(시스템 설정) 버튼은 사람이 경고창 [완료]를 눌러야 커밋됨 → 접근성 권한 없는 자동화로는 재현/캡처 불가.
