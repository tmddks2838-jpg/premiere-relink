# 프리미어 미디어 자동 재연결 툴 v1 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프리미어 `.prproj`를 분석해 위치가 바뀐 미디어를 자동/반자동으로 재연결하는 순수 파이썬 엔진과, 그 위에 얹는 클로드 스킬 껍데기를 만든다.

**Architecture:** `engine/`는 클로드/UI에 비의존하는 순수 파이썬 모듈 6개(models, reader, detector, indexer, matcher, writer) + 공개 API `pipeline.py`로 구성된다. `skill/`은 pipeline을 호출해 미리보기·확인·리포트만 담당한다. 안전: 백업 우선 + 새 파일 저장 + 태그 앵커 기반 수술적 문자열 치환.

**Tech Stack:** Python 3.11+, 표준 라이브러리만(gzip, re, os, pathlib, hashlib, dataclasses), pytest.

설계 문서: `docs/superpowers/specs/2026-06-01-premiere-media-relink-design.md`

---

## 파일 구조

```
premiere-relink/
├── pyproject.toml                 # 패키지/pytest 설정
├── .gitignore
├── engine/
│   ├── __init__.py
│   ├── models.py                  # MediaRef, Candidate, MatchResult, Confidence, 미디어타입 분류
│   ├── reader.py                  # .prproj gzip 해제 + 경로 추출
│   ├── detector.py                # 오프라인/온라인/클라우드 분류
│   ├── indexer.py                 # 검색 폴더 색인
│   ├── matcher.py                 # 경로 규칙 도출 + 매칭 + 신뢰도
│   ├── writer.py                  # 백업 + 수술적 치환 + gzip 저장
│   └── pipeline.py                # 공개 API: analyze() / apply()
├── skill/
│   └── SKILL.md                   # 클로드 스킬 껍데기 정의
└── tests/
    ├── conftest.py                # 공용 픽스처(미니 prproj gz 생성기)
    ├── test_models.py
    ├── test_reader.py
    ├── test_detector.py
    ├── test_indexer.py
    ├── test_matcher.py
    ├── test_writer.py
    └── test_pipeline.py
```

**모듈 경계 원칙:** 각 모듈은 단일 책임. 데이터는 `models.py`의 dataclass로만 주고받는다. `pipeline.py`만이 모듈들을 조립하며, 외부(스킬/CLI/GUI)는 `pipeline.py`의 `analyze`/`apply`만 호출한다.

---

## Task 0: 프로젝트 스캐폴딩

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `engine/__init__.py` (빈 파일)
- Create: `tests/__init__.py` (빈 파일)

- [ ] **Step 1: pyproject.toml 작성**

```toml
[project]
name = "premiere-relink"
version = "0.1.0"
description = "프리미어 프로 미디어 자동 재연결 엔진"
requires-python = ">=3.9"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: .gitignore 작성**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.venv/
*.backup-*.prproj
```

- [ ] **Step 3: 빈 패키지 파일 생성**

`engine/__init__.py`, `tests/__init__.py` 두 빈 파일을 만든다.

- [ ] **Step 4: pytest 동작 확인**

Run: `cd ~/premiere-relink && python3 -m pytest -q`
Expected: `no tests ran` (수집 에러 없이 통과)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore engine/__init__.py tests/__init__.py
git commit -m "chore: 프로젝트 스캐폴딩 (pyproject, pytest, 패키지 구조)"
```

---

## Task 1: 데이터 모델 + 미디어 타입 분류 (models.py)

**Files:**
- Create: `engine/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_models.py
from engine.models import media_type, MediaRef, Candidate, MatchResult, Confidence


def test_media_type_by_extension():
    assert media_type("/a/b/clip.MP4") == "video"
    assert media_type("/a/b/clip.mp4") == "video"
    assert media_type("/a/b/song.WAV") == "audio"
    assert media_type("/a/b/pic.jpeg") == "image"
    assert media_type("/a/b/notes.txt") == "other"


def test_media_type_is_extension_case_insensitive():
    assert media_type("X.MOV") == media_type("x.mov") == "video"


def test_dataclasses_construct():
    ref = MediaRef(raw_path="/v/x.mp4", normalized_path="/x.mp4", count=3)
    cand = Candidate(path="/new/x.mp4", size=123, media_type="video")
    res = MatchResult(ref=ref, confidence=Confidence.AUTO, chosen=cand,
                      candidates=[cand], rule="/old->/new")
    assert res.confidence is Confidence.AUTO
    assert res.chosen.size == 123
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_models.py -q`
Expected: FAIL (`ModuleNotFoundError: engine.models`)

- [ ] **Step 3: 구현**

```python
# engine/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath

VIDEO_EXTS = {"mp4", "mov", "m4v", "mxf", "avi", "mkv", "mts", "m2ts",
              "mpg", "mpeg", "wmv", "r3d", "braw", "webm", "flv", "ts"}
AUDIO_EXTS = {"wav", "aif", "aiff", "mp3", "m4a", "aac", "flac", "ogg", "wma"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "tif", "tiff", "psd", "gif", "bmp",
              "exr", "dpx", "heic", "webp", "tga"}


def media_type(path: str) -> str:
    """확장자로 미디어 타입군을 판정한다 (대소문자 무시)."""
    ext = PurePosixPath(path).suffix.lower().lstrip(".")
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in IMAGE_EXTS:
        return "image"
    return "other"


class Confidence(Enum):
    AUTO = "auto"        # 🟢 자동 연결
    ASK = "ask"          # 🟡 사용자 확인
    MISSING = "missing"  # 🔴 못 찾음


@dataclass(frozen=True)
class MediaRef:
    """프로젝트가 참조하는 미디어 경로 하나 (고유 문자열 단위)."""
    raw_path: str          # XML에 적힌 원본 문자열 (볼륨 접두 포함 가능)
    normalized_path: str   # 부트볼륨 접두 제거 등 정규화한 실경로 후보
    count: int             # XML 내 등장 횟수


@dataclass(frozen=True)
class Candidate:
    """디스크에서 찾은 후보 파일."""
    path: str
    size: int
    media_type: str


@dataclass
class MatchResult:
    ref: MediaRef
    confidence: Confidence
    chosen: Candidate | None = None        # AUTO일 때 확정 후보
    candidates: list[Candidate] = field(default_factory=list)  # ASK일 때 후보들
    rule: str | None = None                # 적용된 경로 규칙 (있으면)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_models.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/models.py tests/test_models.py
git commit -m "feat(engine): 데이터 모델 + 미디어 타입 분류"
```

---

## Task 2: 공용 테스트 픽스처 (conftest.py)

미니 `.prproj`(gzip XML)를 만드는 헬퍼. 이후 reader/writer/pipeline 테스트가 공유한다.

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: 픽스처 작성**

```python
# tests/conftest.py
import gzip
import pytest

# 경로를 담는 태그들을 섞은 최소 prproj XML 골격.
# - ActualMediaFilePath/FilePath: 사용자 미디어 (재연결 대상)
# - PeakFilePath: 자동생성 캐시 (건드리면 안 됨)
PRPROJ_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<PremiereData Version="3">
 <Media ObjectID="1">
  <ActualMediaFilePath>{p1}</ActualMediaFilePath>
  <FilePath>{p1}</FilePath>
 </Media>
 <Media ObjectID="2">
  <ActualMediaFilePath>{p2}</ActualMediaFilePath>
  <FilePath>{p2}</FilePath>
 </Media>
 <MediaCache>
  <PeakFilePath>/Users/me/Library/Media Cache/{p1name}.pek</PeakFilePath>
 </MediaCache>
</PremiereData>
"""


def make_prproj_xml(p1: str, p2: str) -> str:
    p1name = p1.rsplit("/", 1)[-1]
    return PRPROJ_TEMPLATE.format(p1=p1, p2=p2, p1name=p1name)


@pytest.fixture
def write_prproj_gz(tmp_path):
    """주어진 두 경로를 참조하는 미니 .prproj(gzip)를 만들어 경로를 돌려준다."""
    def _make(p1: str, p2: str, name: str = "proj.prproj"):
        xml = make_prproj_xml(p1, p2)
        out = tmp_path / name
        out.write_bytes(gzip.compress(xml.encode("utf-8")))
        return out
    return _make
```

- [ ] **Step 2: 픽스처 수집 확인**

Run: `python3 -m pytest -q`
Expected: 에러 없이 통과 (여전히 `no tests ran` 또는 기존 통과)

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: 미니 prproj gzip 픽스처 추가"
```

---

## Task 3: reader — 경로 추출 (reader.py)

**Files:**
- Create: `engine/reader.py`
- Test: `tests/test_reader.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_reader.py
import gzip
from engine.reader import decompress_prproj, extract_media_refs, read_prproj
from tests.conftest import make_prproj_xml


def test_extract_dedupes_and_counts():
    xml = make_prproj_xml("/Users/me/a.mp4", "/Volumes/Disk/b.mov")
    refs = extract_media_refs(xml)
    paths = {r.raw_path: r for r in refs}
    # a.mp4는 ActualMediaFilePath + FilePath 2회 등장
    assert paths["/Users/me/a.mp4"].count == 2
    assert paths["/Volumes/Disk/b.mov"].count == 2
    # 캐시(PeakFilePath)는 추출 대상이 아님
    assert not any(".pek" in r.raw_path for r in refs)


def test_normalizes_boot_volume_prefix():
    xml = make_prproj_xml("/Volumes/Macintosh HD/Users/me/a.mp4", "/x/b.mov")
    refs = {r.raw_path: r for r in extract_media_refs(xml)}
    ref = refs["/Volumes/Macintosh HD/Users/me/a.mp4"]
    # 부트볼륨 접두는 정규화 경로에서 제거 후보를 제공
    assert ref.normalized_path == "/Users/me/a.mp4"


def test_read_prproj_roundtrip(tmp_path):
    xml = make_prproj_xml("/Users/me/a.mp4", "/Users/me/b.mov")
    f = tmp_path / "p.prproj"
    f.write_bytes(gzip.compress(xml.encode("utf-8")))
    out_xml, refs = read_prproj(str(f))
    assert "<ActualMediaFilePath>" in out_xml
    assert len(refs) == 2
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_reader.py -q`
Expected: FAIL (`ModuleNotFoundError: engine.reader`)

- [ ] **Step 3: 구현**

```python
# engine/reader.py
from __future__ import annotations
import gzip
import re
from collections import Counter
from engine.models import MediaRef

# 사용자 미디어 경로를 담는 태그만 대상. 캐시/리소스 태그는 제외.
PATH_TAGS = ("ActualMediaFilePath", "FilePath", "FullPath")

_TAG_RE = re.compile(
    r"<(?:" + "|".join(PATH_TAGS) + r")>([^<>]+)</(?:" + "|".join(PATH_TAGS) + r")>"
)


def decompress_prproj(path: str) -> str:
    """.prproj(gzip)를 풀어 UTF-8 XML 문자열로 반환."""
    with open(path, "rb") as fh:
        data = fh.read()
    return gzip.decompress(data).decode("utf-8")


def _normalize(raw: str) -> str:
    """부트볼륨 접두(/Volumes/<name>/)를 루트(/)로 환산한 경로 후보를 만든다.
    비부트 외장(/Volumes/Disk/...)은 그대로 둔다 (detector가 존재여부로 판단)."""
    m = re.match(r"^/Volumes/[^/]+(/Users/.*)$", raw)
    if m:
        return m.group(1)
    return raw


def extract_media_refs(xml: str) -> list[MediaRef]:
    """XML에서 미디어 경로를 추출, 고유 문자열 단위로 묶고 등장 횟수를 센다.
    절대경로(/로 시작)만 대상으로 한다."""
    counts = Counter(m for m in _TAG_RE.findall(xml) if m.startswith("/"))
    return [
        MediaRef(raw_path=p, normalized_path=_normalize(p), count=c)
        for p, c in counts.items()
    ]


def read_prproj(path: str) -> tuple[str, list[MediaRef]]:
    xml = decompress_prproj(path)
    return xml, extract_media_refs(xml)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_reader.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/reader.py tests/test_reader.py
git commit -m "feat(engine): reader — prproj 경로 추출/정규화"
```

---

## Task 4: detector — 오프라인/클라우드 분류 (detector.py)

**Files:**
- Create: `engine/detector.py`
- Test: `tests/test_detector.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_detector.py
from engine.detector import classify
from engine.models import MediaRef


def _ref(p):
    return MediaRef(raw_path=p, normalized_path=p, count=1)


def test_classify_online_offline_cloud(tmp_path):
    online = tmp_path / "online.mp4"
    online.write_bytes(b"x" * 100)
    placeholder = tmp_path / "cloud.mp4"
    placeholder.write_bytes(b"")  # 0바이트 = 클라우드 전용 추정

    refs = [_ref(str(online)), _ref(str(placeholder)), _ref(str(tmp_path / "gone.mp4"))]
    result = classify(refs)

    assert [r.raw_path for r in result.online] == [str(online)]
    assert [r.raw_path for r in result.cloud] == [str(placeholder)]
    assert [r.raw_path for r in result.offline] == [str(tmp_path / "gone.mp4")]


def test_classify_uses_normalized_path(tmp_path):
    real = tmp_path / "a.mp4"
    real.write_bytes(b"x" * 10)
    # raw는 가짜 볼륨 경로, normalized는 실제 경로
    ref = MediaRef(raw_path="/Volumes/Ghost" + str(real),
                   normalized_path=str(real), count=1)
    result = classify([ref])
    assert result.online and result.online[0] is ref
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_detector.py -q`
Expected: FAIL (`ModuleNotFoundError: engine.detector`)

- [ ] **Step 3: 구현**

```python
# engine/detector.py
from __future__ import annotations
import os
from dataclasses import dataclass, field
from engine.models import MediaRef


@dataclass
class Classification:
    online: list[MediaRef] = field(default_factory=list)   # 정상
    offline: list[MediaRef] = field(default_factory=list)  # 🔴 누락 → 재연결 대상
    cloud: list[MediaRef] = field(default_factory=list)    # ☁️ 0바이트 플레이스홀더


def _resolve(ref: MediaRef) -> str | None:
    """디스크에 실제 존재하는 경로를 찾는다. raw → normalized 순으로 시도."""
    for cand in (ref.raw_path, ref.normalized_path):
        if os.path.isfile(cand):
            return cand
    return None


def classify(refs: list[MediaRef]) -> Classification:
    out = Classification()
    for ref in refs:
        real = _resolve(ref)
        if real is None:
            out.offline.append(ref)
        elif os.path.getsize(real) == 0:
            out.cloud.append(ref)
        else:
            out.online.append(ref)
    return out
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_detector.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/detector.py tests/test_detector.py
git commit -m "feat(engine): detector — 오프라인/클라우드/온라인 분류"
```

---

## Task 5: indexer — 검색 폴더 색인 (indexer.py)

**Files:**
- Create: `engine/indexer.py`
- Test: `tests/test_indexer.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_indexer.py
from engine.indexer import build_index


def test_index_keys_by_lowercase_filename(tmp_path):
    (tmp_path / "sub").mkdir()
    f1 = tmp_path / "Clip.MP4"
    f1.write_bytes(b"x" * 5)
    f2 = tmp_path / "sub" / "song.wav"
    f2.write_bytes(b"y" * 7)

    index = build_index([str(tmp_path)])
    # 확장자 대소문자 무시: 키는 소문자 전체 파일명
    assert "clip.mp4" in index
    assert index["clip.mp4"][0].path == str(f1)
    assert index["clip.mp4"][0].media_type == "video"
    assert index["clip.mp4"][0].size == 5
    assert "song.wav" in index


def test_index_excludes_noise_dirs(tmp_path):
    junk = tmp_path / ".Trash"
    junk.mkdir()
    (junk / "ghost.mp4").write_bytes(b"z")
    index = build_index([str(tmp_path)])
    assert "ghost.mp4" not in index


def test_index_collects_same_name_in_multiple_dirs(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "dup.mov").write_bytes(b"x")
    (tmp_path / "b" / "dup.mov").write_bytes(b"xx")
    index = build_index([str(tmp_path)])
    assert len(index["dup.mov"]) == 2
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_indexer.py -q`
Expected: FAIL (`ModuleNotFoundError: engine.indexer`)

- [ ] **Step 3: 구현**

```python
# engine/indexer.py
from __future__ import annotations
import os
from engine.models import Candidate, media_type

# 색인에서 제외할 폴더 이름 (캐시/휴지통/시스템)
EXCLUDE_DIRS = {".Trash", ".git", "node_modules", "Library",
                "Media Cache", "Media Cache Files", ".cache"}


def build_index(roots: list[str]) -> dict[str, list[Candidate]]:
    """검색 루트들을 순회하여 '소문자 파일명 → 후보 목록' 색인을 만든다."""
    index: dict[str, list[Candidate]] = {}
    seen: set[str] = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for name in filenames:
                full = os.path.join(dirpath, name)
                if full in seen:
                    continue
                seen.add(full)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                cand = Candidate(path=full, size=size, media_type=media_type(name))
                index.setdefault(name.lower(), []).append(cand)
    return index
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_indexer.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/indexer.py tests/test_indexer.py
git commit -m "feat(engine): indexer — 검색 폴더 색인 (확장자 대소문자 무시)"
```

---

## Task 6: matcher — 경로 규칙 도출 (matcher.py 1/2)

**Files:**
- Create: `engine/matcher.py`
- Test: `tests/test_matcher.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_matcher.py
from engine.matcher import common_suffix_len, derive_prefix_rules
from engine.models import MediaRef, Candidate


def test_common_suffix_len():
    a = "/Users/me/Desktop/무제 폴더/proj/a.mp4"
    b = "/Users/me/Desktop/proj/a.mp4"
    # 공통 후행 컴포넌트: proj, a.mp4 → 2
    assert common_suffix_len(a, b) == 2


def test_derive_rule_for_folder_move():
    refs = [
        MediaRef("/Users/me/Desktop/무제 폴더/proj/a.mp4",
                 "/Users/me/Desktop/무제 폴더/proj/a.mp4", 1),
        MediaRef("/Users/me/Desktop/무제 폴더/proj/b.mov",
                 "/Users/me/Desktop/무제 폴더/proj/b.mov", 1),
    ]
    index = {
        "a.mp4": [Candidate("/Users/me/Desktop/proj/a.mp4", 10, "video")],
        "b.mov": [Candidate("/Users/me/Desktop/proj/b.mov", 20, "video")],
    }
    rules = derive_prefix_rules(refs, index)
    # 옛 접두 → 새 접두 규칙이 도출되어야 함
    assert ("/Users/me/Desktop/무제 폴더", "/Users/me/Desktop") in rules
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_matcher.py -q`
Expected: FAIL (`ModuleNotFoundError: engine.matcher`)

- [ ] **Step 3: 구현 (규칙 도출 부분)**

```python
# engine/matcher.py
from __future__ import annotations
import os
from collections import Counter
from engine.models import MediaRef, Candidate, MatchResult, Confidence, media_type


def common_suffix_len(a: str, b: str) -> int:
    """두 경로의 공통 후행 컴포넌트 개수."""
    pa = a.strip("/").split("/")
    pb = b.strip("/").split("/")
    n = 0
    for x, y in zip(reversed(pa), reversed(pb)):
        if x != y:
            break
        n += 1
    return n


def _split_prefix(path: str, suffix_components: int) -> tuple[str, str]:
    """경로를 (접두, 후행) 으로 나눈다. 후행은 suffix_components 개."""
    parts = path.strip("/").split("/")
    cut = len(parts) - suffix_components
    prefix = "/" + "/".join(parts[:cut]) if cut > 0 else ""
    return prefix, "/" + "/".join(parts[cut:])


def derive_prefix_rules(refs: list[MediaRef],
                        index: dict[str, list[Candidate]]) -> list[tuple[str, str]]:
    """오프라인 ref와 색인 후보를 비교해 (옛 접두 → 새 접두) 규칙을 도출한다.
    폴더 이동 / 볼륨명 변경 / 계정 변경이 모두 이 규칙으로 표현된다."""
    votes: Counter[tuple[str, str]] = Counter()
    for ref in refs:
        name = ref.normalized_path.rsplit("/", 1)[-1]
        for cand in index.get(name.lower(), []):
            scl = common_suffix_len(ref.normalized_path, cand.path)
            if scl == 0:
                continue
            old_prefix, _ = _split_prefix(ref.normalized_path, scl)
            new_prefix, _ = _split_prefix(cand.path, scl)
            if old_prefix != new_prefix:
                votes[(old_prefix, new_prefix)] += 1
    # 1표 이상 받은 규칙을 표 많은 순으로 반환
    return [rule for rule, _ in votes.most_common()]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_matcher.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/matcher.py tests/test_matcher.py
git commit -m "feat(engine): matcher — 경로 접두 치환 규칙 도출"
```

---

## Task 7: matcher — 매칭 + 신뢰도 (matcher.py 2/2)

**Files:**
- Modify: `engine/matcher.py` (함수 추가)
- Test: `tests/test_matcher.py` (테스트 추가)

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# tests/test_matcher.py 에 추가
from engine.matcher import match_refs


def test_auto_via_rule(tmp_path):
    real = tmp_path / "a.mp4"
    real.write_bytes(b"x" * 10)
    ref = MediaRef(f"/old/{real.name}", f"/old/{real.name}", 1)
    index = {"a.mp4": [Candidate(str(real), 10, "video")]}
    rules = [("/old", str(tmp_path))]
    results = match_refs([ref], index, rules)
    assert results[0].confidence is Confidence.AUTO
    assert results[0].chosen.path == str(real)


def test_auto_unique_filename():
    ref = MediaRef("/old/a.mp4", "/old/a.mp4", 1)
    index = {"a.mp4": [Candidate("/new/a.mp4", 10, "video")]}
    results = match_refs([ref], index, rules=[])
    assert results[0].confidence is Confidence.AUTO


def test_missing_when_no_candidate():
    ref = MediaRef("/old/gone.mp4", "/old/gone.mp4", 1)
    results = match_refs([ref], index={}, rules=[])
    assert results[0].confidence is Confidence.MISSING


def test_ask_when_multiple_candidates():
    ref = MediaRef("/old/dup.mov", "/old/dup.mov", 1)
    index = {"dup.mov": [
        Candidate("/a/dup.mov", 10, "video"),
        Candidate("/b/dup.mov", 20, "video"),
    ]}
    results = match_refs([ref], index, rules=[])
    assert results[0].confidence is Confidence.ASK
    assert len(results[0].candidates) == 2


def test_type_mismatch_is_rejected():
    # 영상 참조인데 후보가 오디오면 연결 금지 → MISSING
    ref = MediaRef("/old/take.mp4", "/old/take.mp4", 1)
    index = {"take.mp4": [Candidate("/new/take.mp4", 10, "audio")]}
    results = match_refs([ref], index, rules=[])
    assert results[0].confidence is Confidence.MISSING
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_matcher.py -q`
Expected: FAIL (`cannot import name 'match_refs'`)

- [ ] **Step 3: 구현 추가 (matcher.py 끝에 추가)**

```python
# engine/matcher.py 에 추가

def _apply_rule(path: str, rule: tuple[str, str]) -> str | None:
    old_prefix, new_prefix = rule
    # 경로 경계 보호: "/Volumes/Disk" 규칙이 "/Volumes/Disk2/..."에 잘못 적용되지 않도록
    if old_prefix == "" or path.startswith(old_prefix + "/"):
        return new_prefix + path[len(old_prefix):]
    return None


def _type_ok(ref_path: str, cand: Candidate) -> bool:
    return media_type(ref_path) == cand.media_type


def _rank(ref: MediaRef, cands: list[Candidate],
          rules: list[tuple[str, str]]) -> list[Candidate]:
    """동명 후보 순위화: 규칙 일치 → 부모폴더명 유사 → 경로 길이 순."""
    ref_parent = ref.normalized_path.rsplit("/", 2)[-2] if "/" in ref.normalized_path else ""

    def key(c: Candidate):
        rule_hit = any(_apply_rule(ref.normalized_path, r) == c.path for r in rules)
        parent = c.path.rsplit("/", 2)[-2] if "/" in c.path else ""
        return (not rule_hit, parent != ref_parent, len(c.path))

    return sorted(cands, key=key)


def match_refs(refs: list[MediaRef],
               index: dict[str, list[Candidate]],
               rules: list[tuple[str, str]]) -> list[MatchResult]:
    """오프라인 ref들을 매칭하고 신뢰도를 판정한다."""
    results: list[MatchResult] = []
    for ref in refs:
        # 1) 경로 규칙 우선 적용 (실파일 + 타입 일치 시 AUTO)
        rule_hit = None
        for rule in rules:
            new_path = _apply_rule(ref.normalized_path, rule)
            if new_path and os.path.isfile(new_path) and media_type(ref.normalized_path) == media_type(new_path):
                rule_hit = (new_path, rule)
                break
        if rule_hit:
            new_path, rule = rule_hit
            chosen = Candidate(new_path, os.path.getsize(new_path), media_type(new_path))
            results.append(MatchResult(ref, Confidence.AUTO, chosen=chosen,
                                       rule=f"{rule[0]} -> {rule[1]}"))
            continue

        # 2) 파일명 매칭 (타입 일치 후보만)
        name = ref.normalized_path.rsplit("/", 1)[-1].lower()
        cands = [c for c in index.get(name, []) if _type_ok(ref.normalized_path, c)]
        if not cands:
            results.append(MatchResult(ref, Confidence.MISSING))
        elif len(cands) == 1:
            results.append(MatchResult(ref, Confidence.AUTO, chosen=cands[0]))
        else:
            ranked = _rank(ref, cands, rules)
            results.append(MatchResult(ref, Confidence.ASK, candidates=ranked))
    return results
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_matcher.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/matcher.py tests/test_matcher.py
git commit -m "feat(engine): matcher — 매칭 + 신뢰도(AUTO/ASK/MISSING) + 타입 가드"
```

---

## Task 8: writer — 백업 (writer.py 1/3)

**Files:**
- Create: `engine/writer.py`
- Test: `tests/test_writer.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_writer.py
import gzip
import os
from engine.writer import backup, apply_replacements, write_prproj


def test_backup_creates_timestamped_copy(tmp_path):
    src = tmp_path / "proj.prproj"
    src.write_bytes(b"hello")
    b = backup(str(src))
    assert os.path.isfile(b)
    assert ".backup-" in b
    assert open(b, "rb").read() == b"hello"
    assert os.path.isfile(src)  # 원본 보존
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_writer.py -q`
Expected: FAIL (`ModuleNotFoundError: engine.writer`)

- [ ] **Step 3: 구현**

```python
# engine/writer.py
from __future__ import annotations
import gzip
import os
import shutil
from datetime import datetime


def backup(project_path: str) -> str:
    """원본을 타임스탬프 백업으로 복사하고 백업 경로를 반환한다."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root, ext = os.path.splitext(project_path)
    backup_path = f"{root}.backup-{stamp}{ext}"
    shutil.copy2(project_path, backup_path)
    return backup_path
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_writer.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/writer.py tests/test_writer.py
git commit -m "feat(engine): writer — 타임스탬프 백업"
```

---

## Task 9: writer — 수술적 치환 (writer.py 2/3)

**Files:**
- Modify: `engine/writer.py`
- Test: `tests/test_writer.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# tests/test_writer.py 에 추가
def test_apply_replacements_is_tag_anchored():
    xml = ("<A>/Users/me/a.mp4</A><B>/Users/me/a.mp4</B>"
           "<Peak>/Users/me/a.mp4.pek</Peak>")
    out = apply_replacements(xml, {"/Users/me/a.mp4": "/new/a.mp4"})
    # 태그로 감싼 정확한 경로만 치환
    assert "<A>/new/a.mp4</A>" in out
    assert "<B>/new/a.mp4</B>" in out
    # .pek 캐시 경로는 접두만 같을 뿐 다른 문자열 → 손대지 않음
    assert "/Users/me/a.mp4.pek" in out


def test_apply_replacements_counts():
    xml = "<A>/x.mov</A><A>/x.mov</A>"
    out = apply_replacements(xml, {"/x.mov": "/y.mov"})
    assert out.count("/y.mov") == 2
    assert "/x.mov" not in out
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_writer.py -q`
Expected: FAIL (`cannot import name 'apply_replacements'`)

- [ ] **Step 3: 구현 추가**

```python
# engine/writer.py 에 추가

def apply_replacements(xml: str, replacements: dict[str, str]) -> str:
    """옛 경로 → 새 경로를 태그 경계(>...<)에 앵커해 안전하게 치환한다.
    경로 문자열이 더 긴 경로(.pek 등)의 접두일 때 오치환을 막는다."""
    out = xml
    for old, new in replacements.items():
        out = out.replace(f">{old}<", f">{new}<")
    return out
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_writer.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/writer.py tests/test_writer.py
git commit -m "feat(engine): writer — 태그 앵커 기반 수술적 치환"
```

---

## Task 10: writer — gzip 저장 (writer.py 3/3)

**Files:**
- Modify: `engine/writer.py`
- Test: `tests/test_writer.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# tests/test_writer.py 에 추가
def test_write_prproj_roundtrip(tmp_path):
    out = tmp_path / "out.prproj"
    write_prproj("<X>hi</X>", str(out))
    assert gzip.decompress(out.read_bytes()).decode("utf-8") == "<X>hi</X>"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_writer.py -q`
Expected: FAIL (`cannot import name 'write_prproj'`)

- [ ] **Step 3: 구현 추가**

```python
# engine/writer.py 에 추가

def write_prproj(xml: str, out_path: str) -> str:
    """XML을 gzip으로 압축해 .prproj로 저장한다."""
    with open(out_path, "wb") as fh:
        fh.write(gzip.compress(xml.encode("utf-8")))
    return out_path
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_writer.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/writer.py tests/test_writer.py
git commit -m "feat(engine): writer — gzip prproj 저장"
```

---

## Task 11: pipeline — analyze() 공개 API

**Files:**
- Create: `engine/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_pipeline.py
import gzip
from engine.pipeline import analyze, apply
from engine.models import Confidence
from tests.conftest import make_prproj_xml


def _make_project(tmp_path, p1, p2):
    xml = make_prproj_xml(p1, p2)
    f = tmp_path / "proj.prproj"
    f.write_bytes(gzip.compress(xml.encode("utf-8")))
    return f


def test_analyze_detects_folder_move(tmp_path):
    # 새 위치에 실제 파일 배치
    newdir = tmp_path / "moved"
    newdir.mkdir()
    a = newdir / "a.mp4"; a.write_bytes(b"x" * 10)
    b = newdir / "b.mov"; b.write_bytes(b"y" * 20)
    # 프로젝트는 옛 경로(무제 폴더)를 참조
    proj = _make_project(tmp_path,
                         "/old/무제 폴더/moved/a.mp4",
                         "/old/무제 폴더/moved/b.mov")
    plan = analyze(str(proj), [str(tmp_path)])
    autos = [r for r in plan.results if r.confidence is Confidence.AUTO]
    assert len(autos) == 2
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_pipeline.py -q`
Expected: FAIL (`ModuleNotFoundError: engine.pipeline`)

- [ ] **Step 3: 구현**

```python
# engine/pipeline.py
from __future__ import annotations
import os
from dataclasses import dataclass, field
from engine.models import MediaRef, MatchResult, Confidence
from engine import reader, detector, indexer, matcher

DEFAULT_ROOTS = ["~/Desktop", "~/Documents", "~/Movies"]


@dataclass
class RelinkPlan:
    project_path: str
    xml: str
    results: list[MatchResult] = field(default_factory=list)
    cloud: list[MediaRef] = field(default_factory=list)
    online_count: int = 0

    @property
    def auto(self):
        return [r for r in self.results if r.confidence is Confidence.AUTO]

    @property
    def ask(self):
        return [r for r in self.results if r.confidence is Confidence.ASK]

    @property
    def missing(self):
        return [r for r in self.results if r.confidence is Confidence.MISSING]


def _expand(roots: list[str]) -> list[str]:
    return [os.path.expanduser(r) for r in roots]


def analyze(project_path: str, search_roots: list[str] | None = None) -> RelinkPlan:
    """프로젝트를 읽고 오프라인 미디어를 매칭한 '계획'을 반환한다 (쓰기 없음)."""
    xml, refs = reader.read_prproj(project_path)
    cls = detector.classify(refs)

    project_dir = os.path.dirname(os.path.abspath(project_path))
    roots = [project_dir] + _expand(search_roots or DEFAULT_ROOTS)
    index = indexer.build_index(roots)

    rules = matcher.derive_prefix_rules(cls.offline, index)
    results = matcher.match_refs(cls.offline, index, rules)

    return RelinkPlan(project_path=project_path, xml=xml, results=results,
                      cloud=cls.cloud, online_count=len(cls.online))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_pipeline.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/pipeline.py tests/test_pipeline.py
git commit -m "feat(engine): pipeline.analyze — 읽기/탐지/색인/매칭 조립"
```

---

## Task 12: pipeline — apply() 공개 API

**Files:**
- Modify: `engine/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# tests/test_pipeline.py 에 추가
import os


def test_apply_writes_relinked_and_backup(tmp_path):
    newdir = tmp_path / "moved"; newdir.mkdir()
    (newdir / "a.mp4").write_bytes(b"x" * 10)
    (newdir / "b.mov").write_bytes(b"y" * 20)
    proj = _make_project(tmp_path,
                         "/old/무제 폴더/moved/a.mp4",
                         "/old/무제 폴더/moved/b.mov")

    plan = analyze(str(proj), [str(tmp_path)])
    result = apply(plan, ask_choices={})

    # 새 파일 생성 + 원본 보존 + 백업 생성
    assert os.path.isfile(result.output_path)
    assert result.output_path.endswith("_relinked.prproj")
    assert os.path.isfile(result.backup_path)
    assert os.path.isfile(str(proj))

    # 결과 prproj가 새 경로를 담고 있는지
    out_xml = gzip.decompress(open(result.output_path, "rb").read()).decode("utf-8")
    assert str(newdir / "a.mp4") in out_xml
    assert "/old/무제 폴더/moved/a.mp4" not in out_xml
    assert result.relinked_count == 2
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest tests/test_pipeline.py -q`
Expected: FAIL (`cannot import name 'apply'`)

- [ ] **Step 3: 구현 추가**

```python
# engine/pipeline.py 에 추가
import os as _os
from engine import writer
from engine.models import Confidence, Candidate


@dataclass
class RelinkResult:
    output_path: str
    backup_path: str
    relinked_count: int
    missing_count: int


def apply(plan: RelinkPlan,
          ask_choices: dict[str, Candidate] | None = None,
          output_path: str | None = None) -> RelinkResult:
    """계획 + 사용자 선택(ask_choices: raw_path → 선택 Candidate)을 적용해 저장한다.

    - AUTO: 자동 적용
    - ASK: ask_choices에 선택이 있는 항목만 적용
    - MISSING / 선택 안 한 ASK: 건드리지 않음
    """
    ask_choices = ask_choices or {}
    replacements: dict[str, str] = {}

    for r in plan.results:
        if r.confidence is Confidence.AUTO and r.chosen:
            replacements[r.ref.raw_path] = r.chosen.path
        elif r.confidence is Confidence.ASK:
            chosen = ask_choices.get(r.ref.raw_path)
            if chosen is not None:
                replacements[r.ref.raw_path] = chosen.path

    backup_path = writer.backup(plan.project_path)
    new_xml = writer.apply_replacements(plan.xml, replacements)

    if output_path is None:
        root, ext = _os.path.splitext(plan.project_path)
        output_path = f"{root}_relinked{ext}"
    writer.write_prproj(new_xml, output_path)

    missing = sum(1 for r in plan.results if r.confidence is Confidence.MISSING)
    return RelinkResult(output_path=output_path, backup_path=backup_path,
                        relinked_count=len(replacements), missing_count=missing)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_pipeline.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: 전체 테스트 통과 확인**

Run: `python3 -m pytest -q`
Expected: PASS (전체 통과, 약 24개)

- [ ] **Step 6: Commit**

```bash
git add engine/pipeline.py tests/test_pipeline.py
git commit -m "feat(engine): pipeline.apply — 백업+치환+새파일 저장"
```

---

## Task 13: 실제 프로젝트로 통합 검증 (수동, 안전)

엔진이 본인의 실제 프로젝트에서 동작하는지 **복사본으로만** 확인한다. 원본은 절대 건드리지 않는다.

**Files:**
- Create: `scripts/smoke_real.py` (일회성 검증 스크립트)

- [ ] **Step 1: 검증 스크립트 작성**

```python
# scripts/smoke_real.py
"""실제 프로젝트 복사본으로 analyze 결과를 출력(쓰기 없음)."""
import shutil, sys, glob, os, tempfile
from engine.pipeline import analyze

src = sorted(glob.glob(os.path.expanduser(
    "~/Documents/자동저장/Adobe Premiere Pro Auto-Save/*.prproj")))[-1]
tmp = tempfile.mkdtemp()
copy = os.path.join(tmp, "probe.prproj")
shutil.copy2(src, copy)
print("검사본:", copy)

plan = analyze(copy)  # 기본 검색 루트(Desktop/Documents/Movies)
print(f"온라인 {plan.online_count} / 오프라인 {len(plan.results)} "
      f"(AUTO {len(plan.auto)}, ASK {len(plan.ask)}, MISSING {len(plan.missing)}) "
      f"/ 클라우드 {len(plan.cloud)}")
for r in plan.auto[:5]:
    print("  AUTO", r.ref.raw_path, "->", r.chosen.path,
          f"[규칙 {r.rule}]" if r.rule else "")
```

- [ ] **Step 2: 실행**

Run: `cd ~/premiere-relink && python3 scripts/smoke_real.py`
Expected: 오프라인/AUTO 건수가 출력되고, 폴더 이동(무제 폴더) 경로가 AUTO로 잡히는지 눈으로 확인. 에러 없이 종료.

- [ ] **Step 3: (선택) 실제 apply 후 프리미어 확인**

복사본에 `apply`를 돌려 `probe_relinked.prproj`를 만든 뒤, **그 복사본을 프리미어에서 열어** 미디어가 온라인으로 뜨는지 1회 수동 확인. 원본 프로젝트와 무관하므로 안전.

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_real.py
git commit -m "test: 실제 프로젝트 복사본 스모크 검증 스크립트"
```

---

## Task 14: 클로드 스킬 껍데기 (SKILL.md)

엔진을 호출해 미리보기·확인·리포트를 담당하는 스킬. 사용자가 "이 프로젝트 미디어 재연결해줘"라고 하면 발동.

**Files:**
- Create: `skill/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

````markdown
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
````

- [ ] **Step 2: 스킬 배치 안내 확인**

`skill/SKILL.md`를 `~/.claude/skills/premiere-relink/SKILL.md`로 복사하면 클로드에서 바로 쓸 수 있음. (배치는 사용자 승인 후)

- [ ] **Step 3: Commit**

```bash
git add skill/SKILL.md
git commit -m "feat(skill): 클로드 스킬 껍데기 — 미디어 재연결 오케스트레이션"
```

---

## Self-Review 결과

**1. 스펙 커버리지:**
- 엔진/껍데기 분리 → Task 0~12(엔진), 14(껍데기) ✅
- reader/detector/indexer/matcher/writer/pipeline → Task 3~12 ✅
- 경로 접두 치환 규칙(폴더/볼륨/계정) → Task 6 ✅
- 확장자 대소문자 무시 → Task 5(색인 키), Task 7 테스트 ✅
- 미디어 타입 보존 가드 → Task 1, Task 7 ✅
- 동명 다중 후보 → ASK + 순위화 → Task 7 ✅
- 클라우드 전용 → Task 4 ✅
- 백업 + 새파일 + 수술적 치환 → Task 8~10, 12 ✅
- 검증 가능한 성공기준 → Task 11~13 ✅
- v1 한계(프록시/이름변경) → Task 14 명시 ✅

**2. 플레이스홀더 스캔:** 모든 스텝에 실제 코드/명령 포함. "적절히 처리" 류 없음. ✅

**3. 타입 일관성:** `MediaRef`, `Candidate`, `MatchResult`, `Confidence`, `RelinkPlan`, `RelinkResult` 명칭이 Task 1·11·12에서 일치. `analyze`/`apply`/`match_refs`/`derive_prefix_rules`/`build_index`/`classify`/`apply_replacements`/`backup`/`write_prproj` 시그니처가 호출부와 일치. ✅
