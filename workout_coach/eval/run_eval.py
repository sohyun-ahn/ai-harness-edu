"""사례마다 임시 폴더에 하네스를 복사하고 claude -p 로 돌려 결과를 eval/results/<id>.md 에 저장한다. (표준 라이브러리만)
사용: python eval/run_eval.py [--bare] [id ...]   --bare: 하네스 없이(CLAUDE.md · .claude 복사 안 함)"""
import glob
import json
import sys as _s
_s.stdout.reconfigure(encoding="utf-8")
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

here = Path(__file__).parent
root = here.parent
args = sys.argv[1:]
bare = "--bare" in args
only = [a for a in args if not a.startswith("--")]
out_dir = here / ("results_bare" if bare else "results")
out_dir.mkdir(exist_ok=True)

PREV = """# 2026-10-15 (목)

## 어제(2026-10-14) 수행
- 판정: 추천대로 수행
- 실제 수행: 전체
- 사용자 답: 했어

## 오늘 루틴
| 순서 | 운동 | 부위 | 분량 |
|---|---|---|---|
| 1 | 스쿼트 | 하체 | 3×12 |
| 2 | 푸시업 | 가슴 | 3×10 |
| 3 | 덤벨 로우 | 등 | 3×12 |
| 4 | 플랭크 | 코어 | 3×30초 |

- 예상 소요: 30분
"""


def day_file(day, verdict):
    return f"""# 2026-10-{day:02d}

## 어제 수행
- 판정: {verdict}
- 실제 수행: {'스쿼트 3×12 · 푸시업 3×10 (일부는 다르게: 푸시업 대신 풀업 3×8)' if verdict == '일부 다르게 수행' else ('전체' if verdict != '미수행' else '없음')}
- 사용자 답: {'했어' if verdict != '미수행' else '응답 없음'}

## 오늘 루틴
| 순서 | 운동 | 부위 | 분량 |
|---|---|---|---|
| 1 | 스쿼트 | 하체 | 3×12 |
| 2 | 푸시업 | 가슴 | 3×10 |
"""


def fixtures(kind):
    if kind == "prev_day":
        return {"out/2026-10-15.md": PREV}
    if kind == "month":  # 파일 날짜의 전날이 수행한 날: 10/01~10/07 중 수행 5일 (파일 10-02~10-08)
        v = ["추천대로 수행", "추천대로 수행", "미수행", "일부 다르게 수행", "추천대로 수행", "미수행", "추천대로 수행", "일부 다르게 수행"]
        return {f"out/2026-10-{d + 1:02d}.md": day_file(d + 1, v[d]) for d in range(8)}
    return {}


def find_claude():
    p = shutil.which("claude")
    if p:
        return p
    for pat in (os.path.expanduser("~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude*"),):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    sys.exit("claude 실행 파일을 찾지 못했다")


claude = find_claude()
cases = [json.loads(l) for l in (here / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
for c in cases:
    if only and c["id"] not in only:
        continue
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if not bare:
            shutil.copy(root / "CLAUDE.md", tmp / "CLAUDE.md")
            shutil.copytree(root / ".claude", tmp / ".claude")
        for rel, body in fixtures(c["fixture"]).items():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_text(body, encoding="utf-8")
        (tmp / "out").mkdir(exist_ok=True)
        cmd = [claude, "-p", "--setting-sources", "" if bare else "project", "--permission-mode", "acceptEdits", c["prompt"]]
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, encoding="utf-8")
        produced = tmp / c["result"]
        dest = out_dir / f"{c['id']}.md"
        if produced.exists():
            shutil.copy(produced, dest)
        elif dest.exists():
            dest.unlink()
        (out_dir / f"{c['id']}.stdout.txt").write_text(r.stdout, encoding="utf-8")
        print(f"{c['id']}: {'저장' if produced.exists() else '결과 파일 없음'}")
