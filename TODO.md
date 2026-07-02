# TODO — premiere-relink

> 하루 시작 시 할 일을 적고, Claude에게 "TODO.md 읽고 첫 항목부터" 지시. 세션 끝에 "TODO.md 업데이트해줘".

## 진행 중 / 다음
- [ ] 배포: 구글 드라이브 결정됨 → 노션 게시 (최종본: `docs/notion-배포페이지.md`, Import로 올리기)
- [ ] (선택) 설치안내 스크린샷 STEP3 "그래도 열기" 버튼 실물 1장 — 차단 상태인 직원 맥에서만 캡처 가능. 대체용 설정 화면 2장은 확보 (`dist-assets/screenshots/step3-*.png`, 전 세션 transcript에서 복구)
- [ ] 커뮤니티 무료 배포 → 반응 보고 유료화($99 공증) 판단
- [ ] (반응 오면) Windows 포팅 — 전제조건: 윈도우 PC + 윈도우産 .prproj 샘플. 엔진 경로처리(POSIX `/` 가정) 손봐야 함
- [ ] 배포: CLI 버전 정리 (명령줄로 analyze/apply 실행)
- [ ] (선택) 성능: matcher._match_by_duration 가 색인 전체를 ffprobe 전수조사 → 영상 많으면 느림

## 완료
- [x] v1 파이프라인 (analyze → 검토 → apply → verify)
- [x] Flask 웹 UI
- [x] context/ 작업 구조 도입
- [x] .app 빌드 수정 (spec이 죽은 tkinter app.py → app_web.py 로)
- [x] 보안 취약점 수정 (open-folder os.system 명령주입, index.html XSS)
- [x] **유니버설 빌드 — Intel + Apple Silicon 모든 맥 지원** (ffprobe 유니버설화 + target_arch=universal2, 양쪽 슬라이스 실행 검증)
- [x] 무료 배포 zip + 설치 설명서 (미서명 → "그래도 열기" 안내)
