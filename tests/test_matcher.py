from __future__ import annotations
from engine.matcher import common_suffix_len, derive_prefix_rules
from engine.models import MediaRef, Candidate


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
