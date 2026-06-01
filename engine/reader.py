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
    """`/Volumes/<볼륨명>/Users/...` 형태를 `/Users/...`로 환산한 경로 후보를 만든다.
    (부트볼륨이 `/Volumes/<이름>`으로도 보이는 케이스 대응.) 그 외 형태는 그대로 둔다 —
    detector가 raw·normalized를 모두 시도해 실제 존재 여부로 판정한다."""
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
