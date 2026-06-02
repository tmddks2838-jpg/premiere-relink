---
name: premiere-relink
description: 프리미어 프로 .prproj의 오프라인(누락) 미디어를 자동/반자동으로 재연결한다. 사용자가 "미디어 재연결", "media offline 고쳐줘", ".prproj 링크 다시" 등을 요청할 때 사용.
---

# 프리미어 미디어 재연결

## 동작

1. 대상 `.prproj` 경로를 확인한다 (사용자가 안 주면 묻는다).

2. **분석** — 오프라인 미디어 현황을 파악한다:
   ```bash
   python3 ~/premiere-relink/scripts/relink_skill.py analyze "<PROJECT_PATH>"
   ```
   추가 검색 폴더가 있으면 `--search-roots /Volumes/외장하드 ~/Downloads` 형태로 붙인다.

3. **미리보기**를 사용자에게 보여준다:
   - 🟢 자동 재연결 N개 (`auto` 배열 길이)
   - 🟡 확인 필요 N개 (`ask` 배열 — 후보 경로·크기·타입 함께 제시)
   - 🔴 못 찾음 N개 (`missing` 배열)
   - ☁️ 클라우드 전용 N개 (`cloud` 수)

4. 🟡 항목이 있으면 후보 목록을 보여주고 사용자에게 선택을 받는다.
   선택 결과를 JSON으로 정리한다: `{"오프라인경로": "선택한경로", ...}`

5. **적용** — 사용자가 확인하면 재연결을 실행한다:
   ```bash
   python3 ~/premiere-relink/scripts/relink_skill.py apply "<PROJECT_PATH>" \
     --choices '{"오프라인경로": "선택한경로"}'
   ```
   🟡 선택 항목이 없으면 `--choices` 생략 가능.

6. **결과 리포트**: 재연결 N개 / 여전히 오프라인 M개.
   `output` 경로의 `_relinked.prproj` 파일을 프리미어에서 열라고 안내한다.

## 안전 규칙

- 원본 `.prproj`는 절대 덮어쓰지 않는다 (`_relinked` 새 파일로 저장).
- 🔴(못 찾음)·클라우드 전용은 강제 연결하지 않는다.
- apply 전 반드시 미리보기로 사용자 확인을 받는다.

## 한계 (사용자에게 필요 시 안내)

- 이름이 바뀐 파일은 못 찾을 수 있음 (v2 내용 기반 매칭 예정).
- 프록시 첨부 관계가 깨지는 케이스는 v1.1에서 보강 예정.
