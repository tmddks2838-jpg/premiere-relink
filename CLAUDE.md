# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 테스트 전체 실행
pytest

# 단일 테스트 파일
pytest tests/test_pipeline.py

# 단일 테스트 함수
pytest tests/test_matcher.py::test_derive_prefix_rules

# 앱 실행 (브라우저가 자동으로 열림)
python3 app_web.py

# 재연결 결과 검수
python3 scripts/verify_relink.py "<원본.prproj>" "<relinked.prproj>"
python3 scripts/verify_relink.py "<원본.prproj>" "<relinked.prproj>" --md

# 실제 .prproj로 스모크 테스트
python3 scripts/smoke_real.py "<실제.prproj>"

# PyInstaller .app 빌드 (dist/ 에 생성됨)
bash build_app.sh
```

## Architecture

### Engine layer (`engine/`)
순수 Python 로직이며 Flask/UI에 독립적이다. 데이터 흐름:

```
reader.py          → prproj(gzip) 압축 해제 → XML 파싱 → MediaRef 목록 추출
detector.py        → 각 MediaRef를 online/offline/cloud 로 분류
indexer.py         → 검색 루트들을 walk해 소문자 파일명 → Candidate 색인 생성
matcher.py         → prefix 규칙 도출 → 파일명 매칭 → duration 매칭 (ffprobe)
                     → MatchResult(AUTO|ASK|MISSING) 생성
writer.py          → XML 경로 치환 → gzip 재압축 → _relinked.prproj 저장
pipeline.py        → 위 모듈을 orchestrate하는 analyze() / apply() 공개 API
```

**핵심 데이터 모델** (`engine/models.py`):
- `MediaRef` — XML에서 추출된 미디어 참조 (raw_path, normalized_path, count, duration_secs)
- `Candidate` — 디스크에서 찾은 후보 파일 (path, size, media_type)
- `MatchResult` — 매칭 결과 (ref, confidence=AUTO|ASK|MISSING, chosen, candidates)

**매칭 우선순위** (matcher.py):
1. Prefix 규칙 (폴더 이동/볼륨 변경 감지) → AUTO
2. 파일명 완전일치 단일 후보 → AUTO
3. 파일명 완전일치 복수 후보 → ASK (규칙 일치 → 부모 폴더 → 경로 길이 순으로 랭킹)
4. ffprobe duration 매칭 (이름 바뀐 파일) → ASK 또는 MISSING

**경로 정규화**: macOS에서 부트볼륨이 `/Volumes/<이름>/Users/...`로 보일 때 `/Users/...`로 변환. 한국어 파일명은 HFS+ NFD를 사용하므로 analyze 엔드포인트에서 NFC/NFD/NFKC 정규화를 모두 시도한다.

**원본 보호**: `apply()`는 원본 .prproj를 절대 덮어쓰지 않는다. 출력은 항상 `_relinked.prproj`이며, 타임스탬프 백업(`.backup-YYYYMMDD-HHMMSS-μs.prproj`)을 먼저 생성한다.

### Web app layer
- `app_web.py` — Flask 서버 (localhost:47831), 인메모리 `_state`로 plan을 세션 간 보관
- `templates/index.html` — 단일 페이지 UI (파일 선택 → 분석 → 검토 → 완료)
- `Premiere Relink.command` — 더블클릭 실행기 (터미널이 열리고 서버 시작, 브라우저 자동 열림)

**파일 선택**: osascript `choose file of type {"prproj"}` 사용. `tell application "System Events"` 래퍼를 쓰면 Automation 권한 오류 발생 — 절대 추가하지 말 것.

**ffprobe 경로**: PyInstaller 번들 내 → `~/.local/bin/ffprobe` → PATH 순으로 탐색 (`matcher.py:_ffprobe_bin()`).

### tkinter (`app.py`)
macOS Sequoia + Apple 시스템 Python(tkinter 8.5)에서 Label 텍스트가 렌더링되지 않아 사용 불가. 참조용으로 유지하되 실제로 사용하지 않는다.
