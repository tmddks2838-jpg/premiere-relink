from __future__ import annotations
import gzip
import os
import pytest
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
    assert "/old/무제 폴더/moved/b.mov" not in out_xml
    assert result.missing_count == 0
    assert result.relinked_count == 2


def test_apply_rewrites_boot_volume_raw_path(tmp_path):
    # 실제 프로젝트처럼 raw 경로에 /Volumes/Macintosh HD 접두가 붙어 있고,
    # 옛 위치(oldhome)엔 파일이 없으며 실제 파일은 newhome에 있는 상황.
    # 그 '날것의' 부트볼륨 문자열이 그대로 새 경로로 치환되어야 한다.
    newhome = tmp_path / "newhome"; newhome.mkdir()
    (newhome / "a.mp4").write_bytes(b"x" * 10)
    (newhome / "b.mov").write_bytes(b"y" * 20)
    old = "/Volumes/Macintosh HD" + str(tmp_path / "oldhome")
    proj = _make_project(tmp_path, old + "/a.mp4", old + "/b.mov")

    plan = analyze(str(proj), [str(tmp_path)])
    result = apply(plan)

    out_xml = gzip.decompress(open(result.output_path, "rb").read()).decode("utf-8")
    assert str(newhome / "a.mp4") in out_xml
    assert str(newhome / "b.mov") in out_xml
    # 부트볼륨 접두가 붙은 옛 문자열은 모두 사라져야 함
    assert "/Volumes/Macintosh HD" not in out_xml
    assert result.relinked_count == 2


def test_apply_refuses_to_overwrite_original(tmp_path):
    newdir = tmp_path / "media"; newdir.mkdir()
    (newdir / "a.mp4").write_bytes(b"x" * 10)
    (newdir / "b.mov").write_bytes(b"y" * 20)
    proj = _make_project(tmp_path,
                         str(newdir) + "/a.mp4",
                         str(newdir) + "/b.mov")
    plan = analyze(str(proj), [str(tmp_path)])
    with pytest.raises(ValueError):
        apply(plan, output_path=str(proj))
