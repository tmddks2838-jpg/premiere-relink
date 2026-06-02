#!/usr/bin/env python3
"""Claude 스킬 진입점 — analyze / apply 두 서브커맨드를 JSON으로 출력한다."""
from __future__ import annotations
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import analyze, apply, RelinkPlan
from engine.models import Candidate


def cmd_analyze(args: argparse.Namespace) -> None:
    roots = args.search_roots or []
    plan = analyze(args.project, search_roots=roots if roots else None)

    out: dict = {
        "project": args.project,
        "online": plan.online_count,
        "cloud": len(plan.cloud),
        "auto": [
            {"path": r.ref.raw_path, "found": r.chosen.path if r.chosen else None}
            for r in plan.auto
        ],
        "ask": [
            {
                "path": r.ref.raw_path,
                "candidates": [
                    {"path": c.path, "size": c.size, "type": c.media_type}
                    for c in r.candidates
                ],
            }
            for r in plan.ask
        ],
        "missing": [r.ref.raw_path for r in plan.missing],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_apply(args: argparse.Namespace) -> None:
    roots = args.search_roots or []
    plan = analyze(args.project, search_roots=roots if roots else None)

    # ask_choices: JSON 파일 또는 인라인 JSON 문자열
    ask_choices: dict[str, Candidate] = {}
    if args.choices:
        raw = json.loads(args.choices)
        for offline_path, found_path in raw.items():
            ask_choices[offline_path] = Candidate(
                path=found_path, size=0, media_type=""
            )

    result = apply(plan, ask_choices=ask_choices, output_path=args.output)

    # 매니페스트 저장 — verify_relink.py 검수 시 사용
    manifest_path = result.output_path.replace(".prproj", ".manifest.json")
    manifest = {
        "original": args.project,
        "relinked": result.output_path,
        "backup": result.backup_path,
        "replacements": result.replacements,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    out = {
        "output": result.output_path,
        "backup": result.backup_path,
        "manifest": manifest_path,
        "relinked": result.relinked_count,
        "missing": result.missing_count,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Premiere relink skill CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_analyze = sub.add_parser("analyze", help="오프라인 미디어 분석")
    p_analyze.add_argument("project", help=".prproj 경로")
    p_analyze.add_argument("--search-roots", nargs="*", metavar="DIR",
                           help="추가 검색 폴더")

    p_apply = sub.add_parser("apply", help="재연결 적용")
    p_apply.add_argument("project", help=".prproj 경로")
    p_apply.add_argument("--search-roots", nargs="*", metavar="DIR")
    p_apply.add_argument("--choices", metavar="JSON",
                         help='ASK 항목 선택: \'{"오프라인경로": "찾은경로"}\'')
    p_apply.add_argument("--output", metavar="PATH", help="출력 .prproj 경로")

    args = parser.parse_args()
    if args.cmd == "analyze":
        cmd_analyze(args)
    else:
        cmd_apply(args)


if __name__ == "__main__":
    main()
