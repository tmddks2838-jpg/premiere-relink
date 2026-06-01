from engine.detector import classify
from engine.models import MediaRef


def _ref(p):
    return MediaRef(raw_path=p, normalized_path=p, count=1)


def test_classify_online_offline_cloud(tmp_path):
    online = tmp_path / "online.mp4"
    online.write_bytes(b"x" * 100)
    placeholder = tmp_path / "cloud.mp4"
    placeholder.write_bytes(b"")  # 0바이트 = 클라우드 전용 추정

    refs = [_ref(str(online)), _ref(str(placeholder)), _ref(str(tmp_path / "gone.mp4"))]
    result = classify(refs)

    assert [r.raw_path for r in result.online] == [str(online)]
    assert [r.raw_path for r in result.cloud] == [str(placeholder)]
    assert [r.raw_path for r in result.offline] == [str(tmp_path / "gone.mp4")]


def test_classify_uses_normalized_path(tmp_path):
    real = tmp_path / "a.mp4"
    real.write_bytes(b"x" * 10)
    # raw는 가짜 볼륨 경로, normalized는 실제 경로
    ref = MediaRef(raw_path="/Volumes/Ghost" + str(real),
                   normalized_path=str(real), count=1)
    result = classify([ref])
    assert result.online and result.online[0] is ref
