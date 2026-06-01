from __future__ import annotations
import os
from dataclasses import dataclass, field
from engine.models import MediaRef


@dataclass
class Classification:
    online: list[MediaRef] = field(default_factory=list)   # 정상
    offline: list[MediaRef] = field(default_factory=list)  # 누락 → 재연결 대상
    cloud: list[MediaRef] = field(default_factory=list)    # 0바이트 플레이스홀더


def _resolve(ref: MediaRef) -> "str | None":
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
