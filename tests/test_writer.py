from __future__ import annotations
import gzip
import os
from engine.writer import backup


def test_backup_creates_timestamped_copy(tmp_path):
    src = tmp_path / "proj.prproj"
    src.write_bytes(b"hello")
    b = backup(str(src))
    assert os.path.isfile(b)
    assert ".backup-" in b
    assert open(b, "rb").read() == b"hello"
    assert os.path.isfile(src)  # 원본 보존
