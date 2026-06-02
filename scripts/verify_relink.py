#!/usr/bin/env python3
"""재연결 결과 검수 — original.prproj vs relinked.prproj 를 비교해 JSON 리포트를 출력한다.

사용법:
    python3 verify_relink.py <original.prproj> <relinked.prproj>
    python3 verify_relink.py <original.prproj> <relinked.prproj> --md   # Markdown 출력
"""
from __future__ import annotations
import sys
import os
import json
import argparse
import subprocess

_FFPROBE_CANDIDATES = [
    os.path.join(getattr(sys, "_MEIPASS", ""), "ffprobe"),
    os.path.expanduser("~/.local/bin/ffprobe"),
    "ffprobe",
]


def _ffprobe_bin() -> str:
    for p in _FFPROBE_CANDIDATES:
        if p and (p == "ffprobe" or os.path.isfile(p)):
            return p
    return "ffprobe"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.reader import read_prproj
from engine.models import media_type

DURATION_TOLERANCE = 0.5  # 초


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _ffprobe_duration(path: str) -> float | None:
    try:
        r = subprocess.run(
            [_ffprobe_bin(), "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=10,
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return None


def _name(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _ext(path: str) -> str:
    return path.rsplit(".", 1)[-1].lower() if "." in path else ""


# ── 검수 핵심 ──────────────────────────────────────────────────────────────────

def _check_item(before: str, after: str, orig_dur: float | None) -> dict:
    flags: list[str] = []
    checks: dict = {}

    # 파일 존재 여부
    checks["file_exists"] = os.path.isfile(after)
    if not checks["file_exists"]:
        flags.append("파일 없음")

    # 타입 일치
    bt, at = media_type(before), media_type(after)
    checks["type_match"] = (bt == at)
    if not checks["type_match"]:
        flags.append(f"타입 불일치 ({bt} → {at})")

    # 이름 일치 (폴더 이동이면 같음, 이름 변경이면 다름)
    checks["name_match"] = (_name(before).lower() == _name(after).lower())
    if not checks["name_match"]:
        flags.append(f"이름 변경 감지 — duration 매칭으로 연결됨")

    # 확장자 (타입은 같아도 확장자가 다를 수 있음)
    if checks["type_match"] and _ext(before) != _ext(after):
        checks["ext_changed"] = True
        flags.append(f"확장자 변경 ({_ext(before)} → {_ext(after)})")
    else:
        checks["ext_changed"] = False

    # duration 비교 (원본 duration 을 알고 있을 때)
    checks["orig_duration_secs"] = orig_dur
    if orig_dur is not None and checks["file_exists"]:
        new_dur = _ffprobe_duration(after)
        checks["new_duration_secs"] = new_dur
        if new_dur is not None:
            diff = abs(new_dur - orig_dur)
            checks["duration_diff_secs"] = round(diff, 3)
            if diff > DURATION_TOLERANCE:
                flags.append(f"duration 불일치 ({orig_dur:.2f}s → {new_dur:.2f}s)")
        else:
            checks["new_duration_secs"] = None
            checks["duration_diff_secs"] = None
    else:
        checks["new_duration_secs"] = None
        checks["duration_diff_secs"] = None

    # 파일 크기
    if checks["file_exists"]:
        checks["new_size_bytes"] = os.path.getsize(after)
    else:
        checks["new_size_bytes"] = None

    status = "ok" if not flags else (
        "suspicious" if any(k in f for f in flags for k in ["타입 불일치", "파일 없음", "duration 불일치"])
        else "warning"
    )

    return {
        "before": before,
        "after": after,
        "status": status,
        "checks": checks,
        "flags": flags,
    }


def _load_replacements(relinked_path: str, original_path: str) -> dict[str, str] | None:
    """매니페스트 JSON에서 정확한 before→after 매핑을 읽는다. 없으면 None."""
    manifest_path = relinked_path.replace(".prproj", ".manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("replacements")
    return None


def verify(original_path: str, relinked_path: str) -> dict:
    _, orig_refs = read_prproj(original_path)
    orig_map = {r.raw_path: r for r in orig_refs}

    # 매니페스트가 있으면 정확한 매핑 사용, 없으면 경고
    replacements = _load_replacements(relinked_path, original_path)
    if replacements is None:
        return {
            "original": original_path,
            "relinked": relinked_path,
            "error": "매니페스트 파일 없음 — relink_skill.py apply로 생성된 파일만 검수 가능",
        }

    items = []
    for before, after in replacements.items():
        orig_dur = orig_map.get(before, None)
        items.append(_check_item(before, after, orig_dur.duration_secs if orig_dur else None))

    suspicious = [i for i in items if i["status"] == "suspicious"]
    warnings   = [i for i in items if i["status"] == "warning"]
    verdict    = "approved" if not suspicious and not warnings else "needs_review"

    return {
        "original":       original_path,
        "relinked":       relinked_path,
        "relinked_count": len(items),
        "suspicious":     len(suspicious),
        "warnings":       len(warnings),
        "verdict":        verdict,
        "items":          items,
    }


# ── Markdown 출력 ──────────────────────────────────────────────────────────────

def _to_markdown(report: dict) -> str:
    lines = [
        f"# 재연결 검수 리포트",
        f"",
        f"- 원본: `{report['original']}`",
        f"- 결과: `{report['relinked']}`",
        f"- 재연결: **{report['relinked_count']}개** | "
        f"의심: {report['suspicious']}개 | 경고: {report['warnings']}개",
        f"- **판정: {'✅ 승인' if report['verdict'] == 'approved' else '⚠️ 재확인 필요'}**",
        f"",
        f"## 항목별 결과",
        f"",
    ]

    icon = {"ok": "✅", "warning": "⚠️", "suspicious": "🚨"}
    for item in report["items"]:
        ic = icon.get(item["status"], "❓")
        lines.append(f"### {ic} `{item['before'].rsplit('/', 1)[-1]}`")
        lines.append(f"- 이전: `{item['before']}`")
        lines.append(f"- 이후: `{item['after']}`")
        c = item.get("checks", {})
        if c.get("orig_duration_secs") is not None:
            lines.append(f"- 길이: {c['orig_duration_secs']:.2f}s → {c.get('new_duration_secs', '?')}s")
        if item["flags"]:
            for f in item["flags"]:
                lines.append(f"- 🔸 {f}")
        lines.append("")

    return "\n".join(lines)


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="재연결 결과 검수")
    parser.add_argument("original", help="원본 .prproj 경로")
    parser.add_argument("relinked", help="재연결된 .prproj 경로")
    parser.add_argument("--md", action="store_true", help="Markdown 형식으로 출력")
    args = parser.parse_args()

    report = verify(args.original, args.relinked)

    if args.md:
        print(_to_markdown(report))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
