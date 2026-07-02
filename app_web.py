#!/usr/bin/env python3
"""Premiere Relink — 브라우저 UI 서버"""
from __future__ import annotations
import sys
import os
import json
import subprocess
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template
from engine.pipeline import analyze as _analyze, apply as _apply
from engine.models import Candidate

PORT = 47831
app  = Flask(__name__, template_folder="templates")
_state: dict = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/pick-file", methods=["POST"])
def pick_file():
    """macOS 네이티브 파일 선택 다이얼로그를 열고 선택된 경로를 반환."""
    script = (
        'set f to choose file with prompt "프리미어 프로젝트 선택" '
        'of type {"prproj"}\n'
        'return POSIX path of f'
    )
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True, timeout=120)
    print(f"[pick-file] returncode={r.returncode} stdout={repr(r.stdout)} stderr={repr(r.stderr)}")
    if r.returncode == 0 and r.stdout.strip():
        return jsonify({"path": r.stdout.strip()})
    return jsonify({"error": "취소됨"}), 400


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    raw  = data.get("path", "")
    path = raw.strip()
    print(f"[DEBUG] received path repr: {repr(path)}")
    print(f"[DEBUG] isfile: {os.path.isfile(path)}")

    # NFD/NFC 정규화 시도
    import unicodedata
    for norm in ("NFC", "NFD", "NFKC"):
        p2 = unicodedata.normalize(norm, path)
        if os.path.isfile(p2):
            path = p2
            print(f"[DEBUG] resolved via {norm}: {repr(path)}")
            break
    else:
        if not os.path.isfile(path):
            return jsonify({"error": f"파일을 찾을 수 없습니다: {path}"}), 400

    try:
        plan = _analyze(path)
        _state["plan"]         = plan
        _state["project_path"] = path

        return jsonify({
            "project_path": path,
            "online":  plan.online_count,
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
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/apply", methods=["POST"])
def apply_route():
    data = request.get_json()
    plan = _state.get("plan")
    if plan is None:
        return jsonify({"error": "먼저 분석을 실행하세요"}), 400

    choices_raw: dict = data.get("choices", {})
    ask_choices: dict[str, Candidate] = {}
    for raw_path, found_path in choices_raw.items():
        size = os.path.getsize(found_path) if os.path.isfile(found_path) else 0
        ask_choices[raw_path] = Candidate(path=found_path, size=size, media_type="")

    try:
        result = _apply(plan, ask_choices=ask_choices)
        manifest_path = result.output_path.replace(".prproj", ".manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({
                "original":     _state.get("project_path", ""),
                "relinked":     result.output_path,
                "backup":       result.backup_path,
                "replacements": result.replacements,
            }, f, ensure_ascii=False, indent=2)

        return jsonify({
            "output":   result.output_path,
            "backup":   result.backup_path,
            "relinked": result.relinked_count,
            "missing":  result.missing_count,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/open-folder", methods=["POST"])
def open_folder():
    path = request.get_json().get("path", "")
    if os.path.isfile(path):
        # 리스트 인자로 셸을 거치지 않는다 (파일명 내 따옴표/세미콜론 주입 방지)
        subprocess.run(["open", "-R", path], check=False)
    return jsonify({"ok": True})


def _open_browser():
    import time; time.sleep(1.0)
    url = f"http://localhost:{PORT}"
    # macOS에서 가장 확실한 방법
    subprocess.run(["open", url])


if __name__ == "__main__":
    print(f"🎬  Premiere Relink → http://localhost:{PORT}  (종료: Ctrl+C)")
    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=PORT, debug=False)
