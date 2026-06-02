from __future__ import annotations
import json
import os
import sys
import subprocess
from collections import Counter
from engine.models import MediaRef, Candidate, MatchResult, Confidence, media_type

DURATION_TOLERANCE_SECS = 0.5  # 길이 허용 오차

_FFPROBE_CANDIDATES = [
    # PyInstaller 번들 내부
    os.path.join(getattr(sys, "_MEIPASS", ""), "ffprobe"),
    # 개발 환경 known path
    os.path.expanduser("~/.local/bin/ffprobe"),
    # PATH
    "ffprobe",
]


def _ffprobe_bin() -> str:
    for p in _FFPROBE_CANDIDATES:
        if p and (p == "ffprobe" or os.path.isfile(p)):
            return p
    return "ffprobe"


def _ffprobe_duration(path: str) -> float | None:
    """ffprobe로 파일의 재생 길이(초)를 반환. 실패 시 None."""
    try:
        r = subprocess.run(
            [_ffprobe_bin(), "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=10
        )
        info = json.loads(r.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return None


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
    votes: Counter = Counter()
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


def _apply_rule(path: str, rule: tuple[str, str]) -> str | None:
    old_prefix, new_prefix = rule
    if old_prefix == "" or path.startswith(old_prefix + "/"):
        return new_prefix + path[len(old_prefix):]
    return None


def _type_ok(ref_path: str, cand: Candidate) -> bool:
    return media_type(ref_path) == cand.media_type


def _parent_name(path: str) -> str:
    parts = path.rstrip("/").split("/")
    return parts[-2] if len(parts) >= 2 else ""


def _rank(ref: MediaRef, cands: list[Candidate],
          rules: list[tuple[str, str]]) -> list[Candidate]:
    """동명 후보 순위화: 규칙 일치 → 부모폴더명 유사 → 경로 길이 순."""
    ref_parent = _parent_name(ref.normalized_path)

    def key(c: Candidate):
        rule_hit = any(_apply_rule(ref.normalized_path, r) == c.path for r in rules)
        parent = _parent_name(c.path)
        return (not rule_hit, parent != ref_parent, len(c.path))

    return sorted(cands, key=key)


def match_refs(refs: list[MediaRef],
               index: dict[str, list[Candidate]],
               rules: list[tuple[str, str]]) -> list[MatchResult]:
    """오프라인 ref들을 매칭하고 신뢰도를 판정한다."""
    results: list = []
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
            # 3) duration 매칭 — 이름이 바뀐 파일을 ffprobe로 찾는다
            dur_result = _match_by_duration(ref, index)
            results.append(dur_result)
        elif len(cands) == 1:
            results.append(MatchResult(ref, Confidence.AUTO, chosen=cands[0]))
        else:
            ranked = _rank(ref, cands, rules)
            results.append(MatchResult(ref, Confidence.ASK, candidates=ranked))
    return results


def _match_by_duration(ref: MediaRef,
                       index: dict[str, list[Candidate]]) -> MatchResult:
    """prproj duration을 알고 있는 MISSING ref에 대해 ffprobe로 후보를 찾는다.
    duration을 모르거나 image 타입이면 바로 MISSING 반환."""
    if ref.duration_secs is None or media_type(ref.normalized_path) == "image":
        return MatchResult(ref, Confidence.MISSING)

    ref_type = media_type(ref.normalized_path)
    matched: list[Candidate] = []
    for cands in index.values():
        for cand in cands:
            if cand.media_type != ref_type:
                continue
            cand_dur = _ffprobe_duration(cand.path)
            if cand_dur is None:
                continue
            if abs(cand_dur - ref.duration_secs) <= DURATION_TOLERANCE_SECS:
                matched.append(cand)

    if not matched:
        return MatchResult(ref, Confidence.MISSING)
    if len(matched) == 1:
        return MatchResult(ref, Confidence.ASK, candidates=matched)
    return MatchResult(ref, Confidence.ASK, candidates=matched)
