---
name: premiere-relink
description: 프리미어 프로 .prproj의 오프라인(누락) 미디어를 자동/반자동으로 재연결한다. 사용자가 "미디어 재연결", "media offline 고쳐줘", ".prproj 링크 다시" 등을 요청할 때 사용.
---

# 프리미어 미디어 재연결

## 동작

1. 대상 `.prproj` 경로를 확인한다 (사용자가 안 주면 묻는다).
2. 엔진으로 분석:
   ```bash
   cd ~/premiere-relink && python3 -c "
   from engine.pipeline import analyze
   import json
   plan = analyze('<PROJECT_PATH>')
   print('online', plan.online_count, 'offline', len(plan.results),
         'auto', len(plan.auto), 'ask', len(plan.ask), 'missing', len(plan.missing))
   for r in plan.ask:
       print('ASK', r.ref.raw_path)
       for c in r.candidates:
           print('   ', c.path, c.size, c.media_type)
   for r in plan.missing:
       print('MISSING', r.ref.raw_path)
   "
   ```
3. **미리보기**를 사용자에게 보여준다: 🟢 자동 K개 / 🟡 확인 L개 / 🔴 못 찾음 P개 / ☁️ 클라우드 Q개.
4. 🟡 항목은 후보(전체 경로+크기+타입)를 제시하고 사용자에게 고르게 한다.
5. 확정되면 `apply`를 호출해 `<프로젝트명>_relinked.prproj`를 만든다 (원본 보존 + 백업 생성).
6. 결과 리포트: 재연결 N개 / 여전히 오프라인 M개. "`_relinked` 파일을 프리미어에서 여세요" 안내.

## 안전 규칙

- 원본 `.prproj`는 절대 덮어쓰지 않는다 (기본은 `_relinked` 새 파일).
- 🔴(못 찾음)·타입 불일치·클라우드 전용은 강제 연결하지 않는다.
- apply 전 반드시 미리보기로 사용자 확인을 받는다.

## 한계 (사용자에게 필요 시 안내)

- 이름이 바뀐 파일은 못 찾을 수 있음 (v2 내용 기반 매칭 예정).
- 프록시 첨부 관계가 깨지는 케이스는 v1.1에서 보강 예정.
