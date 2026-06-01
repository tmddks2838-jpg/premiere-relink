from __future__ import annotations
import gzip
from engine.pipeline import analyze
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
