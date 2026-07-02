# TODO — premiere-relink

> 하루 시작 시 할 일을 적고, Claude에게 "TODO.md 읽고 첫 항목부터" 지시. 세션 끝에 "TODO.md 업데이트해줘".

## 진행 중 / 다음
- [ ] 배포 반응 모니터링 (다운로드/설치 막힘/버그 제보) → 1~2주 보고 유료화($99 공증) 판단
- [ ] zip 안 설치 txt(`dist-assets/★ 먼저 읽어주세요.txt`)를 노션과 동일하게 터미널 방식 위주로 갱신 + 재패키징 (지금은 GUI 방식 기준이라 노션 안내와 다름)
- [ ] (선택) 설치안내 스크린샷 STEP3 "그래도 열기" 버튼 실물 1장 — 차단 상태인 직원 맥에서만 캡처 가능. 대체용 설정 화면 2장은 확보 (`dist-assets/screenshots/step3-*.png`)
- [ ] (반응 오면) Windows 포팅 — 전제조건: 윈도우 PC + 윈도우産 .prproj 샘플. 엔진 경로처리(POSIX `/` 가정) 손봐야 함
- [ ] 배포: CLI 버전 정리 (명령줄로 analyze/apply 실행)
- [ ] (선택) 성능: matcher._match_by_duration 가 색인 전체를 ffprobe 전수조사 → 영상 많으면 느림

## 완료
- [x] **v0.1 첫 배포** (2026-07-02, 구글 드라이브 + 노션 안내 페이지 → 오픈카톡 공유)
- [x] v1 파이프라인 (analyze → 검토 → apply → verify)
- [x] Flask 웹 UI
- [x] context/ 작업 구조 도입
- [x] .app 빌드 수정 (spec이 죽은 tkinter app.py → app_web.py 로)
- [x] 보안 취약점 수정 (open-folder os.system 명령주입, index.html XSS)
- [x] **유니버설 빌드 — Intel + Apple Silicon 모든 맥 지원** (ffprobe 유니버설화 + target_arch=universal2, 양쪽 슬라이스 실행 검증)
- [x] 무료 배포 zip + 설치 설명서 (미서명 → "그래도 열기" 안내)
