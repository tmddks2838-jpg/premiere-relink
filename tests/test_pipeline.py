from __future__ import annotations
import gzip
import os
from engine.pipeline import analyze, apply
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


def test_apply_writes_relinked_and_backup(tmp_path):
    newdir = tmp_path / "moved"; newdir.mkdir()
    (newdir / "a.mp4").write_bytes(b"x" * 10)
    (newdir / "b.mov").write_bytes(b"y" * 20)
    proj = _make_project(tmp_path,
                         "/old/무제 폴더/moved/a.mp4",
                         "/old/무제 폴더/moved/b.mov")

    plan = analyze(str(proj), [str(tmp_path)])
    result = apply(plan, ask_choices={})

    # 새 파일 생성 + 원본 보존 + 백업 생성
    assert os.path.isfile(result.output_path)
    assert result.output_path.endswith("_relinked.prproj")
    assert os.path.isfile(result.backup_path)
    assert os.path.isfile(str(proj))

    # 결과 prproj가 새 경로를 담고 있는지
    out_xml = gzip.decompress(open(result.output_path, "rb").read()).decode("utf-8")
    assert str(newdir / "a.mp4") in out_xml
    assert "/old/무제 폴더/moved/a.mp4" not in out_xml
    assert result.relinked_count == 2
