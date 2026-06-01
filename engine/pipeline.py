from __future__ import annotations
import os
from dataclasses import dataclass, field
from engine.models import MediaRef, MatchResult, Confidence
from engine import reader, detector, indexer, matcher

DEFAULT_ROOTS = ["~/Desktop", "~/Documents", "~/Movies"]


@dataclass
class RelinkPlan:
    project_path: str
    xml: str
    results: list[MatchResult] = field(default_factory=list)
    cloud: list[MediaRef] = field(default_factory=list)
    online_count: int = 0

    @property
    def auto(self):
        return [r for r in self.results if r.confidence is Confidence.AUTO]

    @property
    def ask(self):
        return [r for r in self.results if r.confidence is Confidence.ASK]

    @property
    def missing(self):
        return [r for r in self.results if r.confidence is Confidence.MISSING]


def _expand(roots: list[str]) -> list[str]:
    return [os.path.expanduser(r) for r in roots]


def analyze(project_path: str, search_roots: list[str] | None = None) -> RelinkPlan:
    """프로젝트를 읽고 오프라인 미디어를 매칭한 '계획'을 반환한다 (쓰기 없음)."""
    xml, refs = reader.read_prproj(project_path)
    cls = detector.classify(refs)

    project_dir = os.path.dirname(os.path.abspath(project_path))
    roots = [project_dir] + _expand(search_roots or DEFAULT_ROOTS)
    index = indexer.build_index(roots)

    rules = matcher.derive_prefix_rules(cls.offline, index)
    results = matcher.match_refs(cls.offline, index, rules)

    return RelinkPlan(project_path=project_path, xml=xml, results=results,
                      cloud=cls.cloud, online_count=len(cls.online))
