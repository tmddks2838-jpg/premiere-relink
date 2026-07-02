# LEARNINGS — premiere-relink

> 삽질·발견을 그때그때 맨 아래에 한 줄씩 append. 형식: `날짜 — 배운 점`

- 한국어 파일명은 HFS+ NFD를 쓰므로, analyze 단계에서 NFC/NFD/NFKC 정규화를 **모두** 시도해야 매칭이 된다.
- macOS에서 부트볼륨이 `/Volumes/<이름>/Users/...`로 보일 때가 있다 → `/Users/...`로 정규화해야 경로가 맞는다.
- 이름이 바뀐 파일은 파일명으로 못 잡으므로 ffprobe duration 매칭으로 ASK/MISSING 처리한다.
