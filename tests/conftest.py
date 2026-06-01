import gzip
import pytest

# 경로를 담는 태그들을 섞은 최소 prproj XML 골격.
# - ActualMediaFilePath/FilePath: 사용자 미디어 (재연결 대상)
# - PeakFilePath: 자동생성 캐시 (건드리면 안 됨)
PRPROJ_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<PremiereData Version="3">
 <Media ObjectID="1">
  <ActualMediaFilePath>{p1}</ActualMediaFilePath>
  <FilePath>{p1}</FilePath>
 </Media>
 <Media ObjectID="2">
  <ActualMediaFilePath>{p2}</ActualMediaFilePath>
  <FilePath>{p2}</FilePath>
 </Media>
 <MediaCache>
  <PeakFilePath>/Users/me/Library/Media Cache/{p1name}.pek</PeakFilePath>
 </MediaCache>
</PremiereData>
"""


def make_prproj_xml(p1: str, p2: str) -> str:
    p1name = p1.rsplit("/", 1)[-1]
    return PRPROJ_TEMPLATE.format(p1=p1, p2=p2, p1name=p1name)


@pytest.fixture
def write_prproj_gz(tmp_path):
    """주어진 두 경로를 참조하는 미니 .prproj(gzip)를 만들어 경로를 돌려준다."""
    def _make(p1: str, p2: str, name: str = "proj.prproj"):
        xml = make_prproj_xml(p1, p2)
        out = tmp_path / name
        out.write_bytes(gzip.compress(xml.encode("utf-8")))
        return out
    return _make
