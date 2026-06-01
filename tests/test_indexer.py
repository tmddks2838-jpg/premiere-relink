from engine.indexer import build_index


def test_index_keys_by_lowercase_filename(tmp_path):
    (tmp_path / "sub").mkdir()
    f1 = tmp_path / "Clip.MP4"
    f1.write_bytes(b"x" * 5)
    f2 = tmp_path / "sub" / "song.wav"
    f2.write_bytes(b"y" * 7)

    index = build_index([str(tmp_path)])
    # 확장자 대소문자 무시: 키는 소문자 전체 파일명
    assert "clip.mp4" in index
    assert index["clip.mp4"][0].path == str(f1)
    assert index["clip.mp4"][0].media_type == "video"
    assert index["clip.mp4"][0].size == 5
    assert "song.wav" in index


def test_index_excludes_noise_dirs(tmp_path):
    junk = tmp_path / ".Trash"
    junk.mkdir()
    (junk / "ghost.mp4").write_bytes(b"z")
    index = build_index([str(tmp_path)])
    assert "ghost.mp4" not in index


def test_index_collects_same_name_in_multiple_dirs(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "dup.mov").write_bytes(b"x")
    (tmp_path / "b" / "dup.mov").write_bytes(b"xx")
    index = build_index([str(tmp_path)])
    assert len(index["dup.mov"]) == 2
