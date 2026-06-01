"""실제 프로젝트 복사본으로 analyze 결과를 출력(쓰기 없음)."""
import shutil, sys, glob, os, tempfile
# 어디서 실행하든 engine 패키지를 찾도록 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.pipeline import analyze

src = sorted(glob.glob(os.path.expanduser(
    "~/Documents/자동저장/Adobe Premiere Pro Auto-Save/*.prproj")))[-1]
tmp = tempfile.mkdtemp()
copy = os.path.join(tmp, "probe.prproj")
shutil.copy2(src, copy)
print("검사본:", copy)

plan = analyze(copy)  # 기본 검색 루트(Desktop/Documents/Movies)
print(f"온라인 {plan.online_count} / 오프라인 {len(plan.results)} "
      f"(AUTO {len(plan.auto)}, ASK {len(plan.ask)}, MISSING {len(plan.missing)}) "
      f"/ 클라우드 {len(plan.cloud)}")
for r in plan.auto[:5]:
    print("  AUTO", r.ref.raw_path, "->", r.chosen.path,
          f"[규칙 {r.rule}]" if r.rule else "")
