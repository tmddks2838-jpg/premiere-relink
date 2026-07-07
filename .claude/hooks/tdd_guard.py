#!/usr/bin/env python3
"""TDD 가드 (PreToolUse).

engine/ 아래의 소스 .py를 만들거나 고칠 때, 대응하는 tests/test_<module>.py가
없으면 저장을 차단한다. (테스트 먼저 → 실패 확인 → 구현)

- 대상: $CLAUDE_PROJECT_DIR/engine/**/*.py 중 test_*.py / __init__.py / conftest.py 제외
- app.py 같은 UI 진입점(engine/ 밖)은 대상 아님 → 통과
- 입력 파싱 실패 등 애매하면 '통과'(exit 0)로 안전하게 처리
"""
import json
import os
import sys


def project_dir():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return env
    # 폴백: 이 스크립트는 <PROJECT>/.claude/hooks/tdd_guard.py 위치
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    file_path = (data.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    proj = project_dir()
    abs_fp = os.path.abspath(file_path)
    engine_dir = os.path.join(proj, "engine")

    # engine/ 아래의 .py 소스만 대상
    if not abs_fp.startswith(engine_dir + os.sep) or not abs_fp.endswith(".py"):
        sys.exit(0)

    base = os.path.basename(abs_fp)
    if base.startswith("test_") or base in ("__init__.py", "conftest.py"):
        sys.exit(0)

    module = base[:-3]  # .py 제거
    test_path = os.path.join(proj, "tests", f"test_{module}.py")
    if os.path.exists(test_path):
        sys.exit(0)

    rel = os.path.relpath(abs_fp, proj)
    print(
        f"⛔ TDD 가드: {rel} 에 대응하는 테스트가 없습니다.\n"
        f"   먼저 tests/test_{module}.py 에 실패하는 테스트를 작성한 뒤 구현하세요.\n"
        f"   (테스트 먼저 → 실패 확인 → 구현)",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
