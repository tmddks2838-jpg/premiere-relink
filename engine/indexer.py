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
