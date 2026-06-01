from engine.models import media_type, MediaRef, Candidate, MatchResult, Confidence


def test_media_type_by_extension():
    assert media_type("/a/b/clip.MP4") == "video"
    assert media_type("/a/b/clip.mp4") == "video"
    assert media_type("/a/b/song.WAV") == "audio"
    assert media_type("/a/b/pic.jpeg") == "image"
    assert media_type("/a/b/notes.txt") == "other"


def test_media_type_is_extension_case_insensitive():
    assert media_type("X.MOV") == media_type("x.mov") == "video"


def test_dataclasses_construct():
    ref = MediaRef(raw_path="/v/x.mp4", normalized_path="/x.mp4", count=3)
    cand = Candidate(path="/new/x.mp4", size=123, media_type="video")
    res = MatchResult(ref=ref, confidence=Confidence.AUTO, chosen=cand,
                      candidates=[cand], rule="/old->/new")
    assert res.confidence is Confidence.AUTO
    assert res.chosen.size == 123
