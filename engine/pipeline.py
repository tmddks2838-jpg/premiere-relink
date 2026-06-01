from __future__ import annotations
import os
from dataclasses import dataclass, field
from engine.models import MediaRef, MatchResult, Confidence, Candidate
from engine import reader, detector, indexer, matcher, writer

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


@dataclass
class RelinkResult:
    output_path: str
    backup_path: str
    relinked_count: int
    missing_count: int


def apply(plan: RelinkPlan,
          ask_choices: dict[str, Candidate] | None = None,
          output_path: str | None = None) -> RelinkResult:
    """계획 + 사용자 선택(ask_choices: raw_path → 선택 Candidate)을 적용해 저장한다.

    - AUTO: 자동 적용
    - ASK: ask_choices에 선택이 있는 항목만 적용
    - MISSING / 선택 안 한 ASK: 건드리지 않음
    """
    ask_choices = ask_choices or {}
    replacements: dict[str, str] = {}

    for r in plan.results:
        if r.confidence is Confidence.AUTO and r.chosen:
            replacements[r.ref.raw_path] = r.chosen.path
        elif r.confidence is Confidence.ASK:
            chosen = ask_choices.get(r.ref.raw_path)
            if chosen is not None:
                replacements[r.ref.raw_path] = chosen.path

    backup_path = writer.backup(plan.project_path)
    new_xml = writer.apply_replacements(plan.xml, replacements)

    if output_path is None:
        root, ext = os.path.splitext(plan.project_path)
        output_path = f"{root}_relinked{ext}"
    writer.write_prproj(new_xml, output_path)

    missing = sum(1 for r in plan.results if r.confidence is Confidence.MISSING)
    return RelinkResult(output_path=output_path, backup_path=backup_path,
                        relinked_count=len(replacements), missing_count=missing)
