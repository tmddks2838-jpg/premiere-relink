from __future__ import annotations
import gzip
import os
from engine.writer import backup, apply_replacements, write_prproj


def test_backup_creates_timestamped_copy(tmp_path):
    src = tmp_path / "proj.prproj"
    src.write_bytes(b"hello")
    b = backup(str(src))
    assert os.path.isfile(b)
    assert ".backup-" in b
    assert open(b, "rb").read() == b"hello"
    assert os.path.isfile(src)  # 원본 보존


def test_apply_replacements_is_tag_anchored():
    xml = ("<A>/Users/me/a.mp4</A><B>/Users/me/a.mp4</B>"
           "<Peak>/Users/me/a.mp4.pek</Peak>")
    out = apply_replacements(xml, {"/Users/me/a.mp4": "/new/a.mp4"})
    # 태그로 감싼 정확한 경로만 치환
    assert "<A>/new/a.mp4</A>" in out
    assert "<B>/new/a.mp4</B>" in out
    # .pek 캐시 경로는 접두만 같을 뿐 다른 문자열 → 손대지 않음
    assert "/Users/me/a.mp4.pek" in out


def test_apply_replacements_counts():
    xml = "<A>/x.mov</A><A>/x.mov</A>"
    out = apply_replacements(xml, {"/x.mov": "/y.mov"})
    assert out.count("/y.mov") == 2
    assert "/x.mov" not in out
