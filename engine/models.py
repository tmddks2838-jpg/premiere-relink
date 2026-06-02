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
    raw_path: str                    # XML에 적힌 원본 문자열 (볼륨 접두 포함 가능)
    normalized_path: str             # 부트볼륨 접두 제거 등 정규화한 실경로 후보
    count: int                       # XML 내 등장 횟수
    duration_secs: float | None = None  # prproj에서 추출한 재생 길이 (초)


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
