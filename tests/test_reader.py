# tests/test_reader.py
import gzip
from engine.reader import decompress_prproj, extract_media_refs, read_prproj
from tests.conftest import make_prproj_xml


def test_extract_dedupes_and_counts():
    xml = make_prproj_xml("/Users/me/a.mp4", "/Volumes/Disk/b.mov")
    refs = extract_media_refs(xml)
    paths = {r.raw_path: r for r in refs}
    # a.mp4는 ActualMediaFilePath + FilePath 2회 등장
    assert paths["/Users/me/a.mp4"].count == 2
    assert paths["/Volumes/Disk/b.mov"].count == 2
    # 캐시(PeakFilePath)는 추출 대상이 아님
    assert not any(".pek" in r.raw_path for r in refs)


def test_normalizes_boot_volume_prefix():
    xml = make_prproj_xml("/Volumes/Macintosh HD/Users/me/a.mp4", "/x/b.mov")
    refs = {r.raw_path: r for r in extract_media_refs(xml)}
    ref = refs["/Volumes/Macintosh HD/Users/me/a.mp4"]
    # 부트볼륨 접두는 정규화 경로에서 제거 후보를 제공
    assert ref.normalized_path == "/Users/me/a.mp4"


def test_read_prproj_roundtrip(tmp_path):
    xml = make_prproj_xml("/Users/me/a.mp4", "/Users/me/b.mov")
    f = tmp_path / "p.prproj"
    f.write_bytes(gzip.compress(xml.encode("utf-8")))
    out_xml, refs = read_prproj(str(f))
    assert "<ActualMediaFilePath>" in out_xml
    assert len(refs) == 2
