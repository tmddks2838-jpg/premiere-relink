# PROJECT — premiere-relink

> 새 세션 시작 시 이 파일을 먼저 읽어 맥락을 잡는다. 상세 아키텍처는 중복 작성하지 말고 루트 `CLAUDE.md` 참조.

## 목적
프리미어 프로 `.prproj`의 오프라인(누락) 미디어를 자동/반자동으로 재연결해 주는 데스크톱 툴.

## 기술 스택
- Python 3 / Flask (로컬 웹 UI, localhost:47831)
- ffprobe (duration 매칭)
- PyInstaller (.app 빌드)

## 현재 상태
- **v1 완료.** 분석 → 검토 → 재연결 → 검수 파이프라인 동작.
- 다음 단계: 배포 (CLI·GUI 양쪽 로드맵) — 자세한 건 `TODO.md`.

## 핵심 진입점
- `app_web.py` — Flask 서버 / UI 진입점
- `engine/pipeline.py` — `analyze()` / `apply()` 공개 API (엔진 orchestration)
- 상세 아키텍처·데이터 모델·매칭 우선순위 → 루트 `CLAUDE.md`

## 관련 문서
- 아키텍처/명령어: `../CLAUDE.md`
- 내려진 결정: `DECISIONS.md`
- 배운 점: `LEARNINGS.md`
- 할 일: `../TODO.md`
