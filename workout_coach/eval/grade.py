"""결과 파일을 읽어 사례별 항목 O / X 와 점수를 출력한다. (표준 라이브러리만)
사용: python eval/grade.py [결과 폴더]   기본값: eval/results/<사례 id>.md"""
import json
import sys as _s
_s.stdout.reconfigure(encoding="utf-8")
import sys
from pathlib import Path

here = Path(__file__).parent
res_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "results"
cases = [json.loads(l) for l in (here / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

total = got = 0
for c in cases:
    f = res_dir / f"{c['id']}.md"
    text = f.read_text(encoding="utf-8") if f.exists() else None
    checks = [("파일 생성", text is not None)]
    if text is not None:
        checks += [(f"포함: {w}", w in text) for w in c["must_include"]]
        checks += [(f"없음: {w}", w not in text) for w in c["must_not"]]
    else:
        checks += [(f"포함: {w}", False) for w in c["must_include"]]
        checks += [(f"없음: {w}", False) for w in c["must_not"]]
    ok = sum(r for _, r in checks)
    total += len(checks)
    got += ok
    print(f"\n[{c['id']}] ({c['kind']}) {ok}/{len(checks)}")
    for name, r in checks:
        print(f"  {'O' if r else 'X'}  {name}")
print(f"\n점수: {got}/{total} ({100 * got // total}%)")
