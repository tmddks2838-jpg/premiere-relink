# Codex 검수 태스크 — Premiere 미디어 재연결

## 역할

재연결 결과물(`_relinked.prproj`)이 올바른지 검수한다.
자동 연결된 항목 중 이상한 것이 없는지, 사람이 놓칠 수 있는 의심 항목을 플래그한다.

## 검수 실행 방법

```bash
cd ~/premiere-relink

# JSON 리포트
python3 scripts/verify_relink.py \
  "<원본.prproj 경로>" \
  "<relinked.prproj 경로>"

# Markdown 리포트 (읽기 편한 버전)
python3 scripts/verify_relink.py \
  "<원본.prproj 경로>" \
  "<relinked.prproj 경로>" \
  --md
```

## 판정 기준

| 상태 | 기호 | 조건 |
|---|---|---|
| 정상 | ✅ ok | 이름 일치, 타입 일치, duration 일치, 파일 존재 |
| 경고 | ⚠️ warning | 이름이 다름 (duration 매칭으로 연결된 경우) |
| 의심 | 🚨 suspicious | 타입 불일치 / duration 차이 큼 / 파일 없음 |

- `suspicious` 항목이 하나라도 있으면 → **재확인 필요**
- `warning`만 있으면 → 사람이 직접 확인 후 판단
- 전부 `ok`면 → **승인**

## Codex가 해야 할 일

1. 위 명령어를 실행해 리포트를 얻는다.
2. `suspicious` 항목이 있으면 왜 의심스러운지 이유를 설명한다.
3. `warning` 항목(이름 변경 감지)은 before/after 파일명을 나란히 보여주고 맞는지 물어본다.
4. 최종 판정을 내린다: **"승인"** 또는 **"재확인 필요 — [이유]"**

## 플래그 해석 가이드

- **이름 변경 감지**: duration이 일치해서 연결했지만 이름이 다름. 실제로 같은 파일인지 사람이 확인 필요.
- **타입 불일치**: video ↔ audio 같은 근본적인 차이. 거의 항상 오매칭.
- **duration 불일치**: 같은 이름이지만 길이가 다름. 같은 이름의 다른 파일일 수 있음.
- **파일 없음**: apply 이후에도 해당 경로에 파일이 없음. 심각한 문제.
