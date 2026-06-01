from __future__ import annotations
from engine.matcher import common_suffix_len, derive_prefix_rules, match_refs
from engine.models import MediaRef, Candidate, Confidence


def test_common_suffix_len():
    a = "/Users/me/Desktop/무제 폴더/proj/a.mp4"
    b = "/Users/me/Desktop/proj/a.mp4"
    # 공통 후행 컴포넌트: proj, a.mp4 → 2
    assert common_suffix_len(a, b) == 2


def test_derive_rule_for_folder_move():
    refs = [
        MediaRef("/Users/me/Desktop/무제 폴더/proj/a.mp4",
                 "/Users/me/Desktop/무제 폴더/proj/a.mp4", 1),
        MediaRef("/Users/me/Desktop/무제 폴더/proj/b.mov",
                 "/Users/me/Desktop/무제 폴더/proj/b.mov", 1),
    ]
    index = {
        "a.mp4": [Candidate("/Users/me/Desktop/proj/a.mp4", 10, "video")],
        "b.mov": [Candidate("/Users/me/Desktop/proj/b.mov", 20, "video")],
    }
    rules = derive_prefix_rules(refs, index)
    # 옛 접두 → 새 접두 규칙이 도출되어야 함
    assert ("/Users/me/Desktop/무제 폴더", "/Users/me/Desktop") in rules


def test_auto_via_rule(tmp_path):
    real = tmp_path / "a.mp4"
    real.write_bytes(b"x" * 10)
    ref = MediaRef(f"/old/{real.name}", f"/old/{real.name}", 1)
    index = {"a.mp4": [Candidate(str(real), 10, "video")]}
    rules = [("/old", str(tmp_path))]
    results = match_refs([ref], index, rules)
    assert results[0].confidence is Confidence.AUTO
    assert results[0].chosen.path == str(real)


def test_auto_unique_filename():
    ref = MediaRef("/old/a.mp4", "/old/a.mp4", 1)
    index = {"a.mp4": [Candidate("/new/a.mp4", 10, "video")]}
    results = match_refs([ref], index, rules=[])
    assert results[0].confidence is Confidence.AUTO


def test_missing_when_no_candidate():
    ref = MediaRef("/old/gone.mp4", "/old/gone.mp4", 1)
    results = match_refs([ref], index={}, rules=[])
    assert results[0].confidence is Confidence.MISSING


def test_ask_when_multiple_candidates():
    ref = MediaRef("/old/dup.mov", "/old/dup.mov", 1)
    index = {"dup.mov": [
        Candidate("/a/dup.mov", 10, "video"),
        Candidate("/b/dup.mov", 20, "video"),
    ]}
    results = match_refs([ref], index, rules=[])
    assert results[0].confidence is Confidence.ASK
    assert len(results[0].candidates) == 2


def test_type_mismatch_is_rejected():
    # 영상 참조인데 후보가 오디오면 연결 금지 → MISSING
    ref = MediaRef("/old/take.mp4", "/old/take.mp4", 1)
    index = {"take.mp4": [Candidate("/new/take.mp4", 10, "audio")]}
    results = match_refs([ref], index, rules=[])
    assert results[0].confidence is Confidence.MISSING
