"""Lab 4 — 같은 과제(task.md)를 하네스별로 헤드리스 실행하고 토큰·시간·테스트·건너뛴 단계를 잰다.

실행:  python lab4_public_harness/run_task.py bare
       python lab4_public_harness/run_task.py mine                        (lab8 의 my-harness 를 --plugin-dir 로)
       python lab4_public_harness/run_task.py superpowers                 (/plugin 으로 설치한 것 = user 설정)
       python lab4_public_harness/run_task.py superpowers --plugin-dir <클론한 폴더>
       python lab4_public_harness/run_task.py gstack --dry-run
결과:  results/<하네스>_<시각>.json, events.jsonl  +  compare.md 에 붙일 표 한 줄
고칠 곳: PREFIX (하네스별로 과제 앞에 붙일 말), MINE

주의: 공개 하네스는 대화형 사용을 전제로 만든 것이 많다. 헤드리스는 「질문 없이 끝까지」 돌리므로
      브레인스토밍·계획 승인 단계가 줄어든다. 대화형으로도 한 번 해 보고 compare.md 에 같이 적는다.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import config, headless, workspace

HERE = Path(__file__).resolve().parent
MINE = HERE.parent / "lab8_final_plugin" / "my-harness"   # TODO(실습): 내 하네스 폴더

# TODO(실습): 하네스의 진입 명령을 과제 앞에 붙여 볼 수 있다 (예: "/superpowers:write-plan 먼저 쓰고 진행해.\n")
PREFIX = {"bare": "", "mine": "", "superpowers": "", "gstack": ""}

TOOLS = ("Read,Edit,Write,Glob,Grep,Skill,Agent,TodoWrite,"
         "Bash(python -m unittest*),Bash(python3 -m unittest*),Bash(git *),Bash(ls*),Bash(cat*)")


def harness_opts(name, plugin_dir):
    """하네스별 설정. user = 내 PC 에 설치된 플러그인·스킬(~/.claude)을 읽는다 → 다른 것도 섞일 수 있다."""
    if plugin_dir:
        return {"setting_sources": "", "plugin_dirs": [plugin_dir]}
    return {
        "bare": {"setting_sources": ""},
        "mine": {"setting_sources": "", "plugin_dirs": [MINE]},
        "superpowers": {"setting_sources": "user"},
        "gstack": {"setting_sources": "user"},
    }[name]


def unittest_result(ws):
    p = subprocess.run([sys.executable, "-m", "unittest"], cwd=ws, capture_output=True, text=True, timeout=120)
    out = p.stderr + p.stdout
    ran = int((re.search(r"Ran (\d+) test", out) or [0, 0])[1])
    bad = sum(int(x) for x in re.findall(r"(?:failures|errors)=(\d+)", out))
    return ran - bad, ran


def steps(events):
    """건너뛴 단계 판정 — 도구 호출 순서로."""
    calls = headless.tool_uses(events)
    seq = [(c["name"], json.dumps(c["input"], ensure_ascii=False)) for c in calls]
    is_test = lambda n, s: n == "Bash" and "unittest" in s  # noqa: E731
    is_edit = lambda n, s: n in ("Edit", "Write", "MultiEdit")  # noqa: E731
    first_edit = next((i for i, (n, s) in enumerate(seq) if is_edit(n, s)), None)
    last_edit = max((i for i, (n, s) in enumerate(seq) if is_edit(n, s)), default=None)
    tests = [i for i, (n, s) in enumerate(seq) if is_test(n, s)]
    return {
        "수정 전 테스트": bool(tests) and (first_edit is None or tests[0] < first_edit),
        "테스트 추가": any(is_edit(n, s) and "tests/" in s for n, s in seq),
        "끝에 테스트": bool(tests) and (last_edit is None or tests[-1] > last_edit),
        "스킬": sorted({c["input"].get("skill", "?") for c in calls if c["name"] == "Skill"}),
        "서브에이전트": sorted({c["input"].get("subagent_type", "?") for c in calls if c["name"] in ("Agent", "Task")}),
        "도구 호출": len(calls),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("harness", choices=["bare", "mine", "superpowers", "gstack"])
    ap.add_argument("--plugin-dir", help="플러그인 폴더를 직접 지정 (user 설정 대신)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show-cmd", action="store_true")
    args = ap.parse_args()
    headless.banner(args.dry_run)

    ws = workspace.build(f"lab4-{args.harness}", copy={p.name: p for p in (HERE / "sample_app").iterdir()
                                                       if p.name != "__pycache__"})
    if shutil.which("git"):  # 하네스 중 git 을 쓰는 것이 많다
        for c in (["init", "-q"], ["add", "-A"], ["-c", "user.name=lab", "-c", "user.email=lab@example.invalid",
                                                   "commit", "-qm", "start"]):
            subprocess.run(["git", *c], cwd=ws, capture_output=True)
    before = unittest_result(ws)
    task = re.sub(r"<!--.*?-->\s*", "", (HERE / "task.md").read_text(encoding="utf-8"), flags=re.S)
    print(f"[{args.harness}] 작업 폴더 {ws} · 시작 전 테스트 {before[0]}/{before[1]} 통과")

    r = headless.run(PREFIX[args.harness] + task, cwd=ws, model=config.HEADLESS_MODEL, allowed_tools=TOOLS,
                     permission_mode="acceptEdits", stream=True, dry_run=args.dry_run, fixture="lab4_task",
                     **harness_opts(args.harness, args.plugin_dir))
    if args.show_cmd:
        print("  $", r["cmd_str"])

    shutil.copy(HERE / "acceptance" / "test_history.py", ws / "tests" / "test_acceptance_history.py")
    after = unittest_result(ws)
    st = steps(r["events"])
    res = {"harness": args.harness, "tokens": {k: r[k] for k in ("input_tokens", "cache_read", "cache_write",
                                                                  "output_tokens", "total_tokens", "all_tokens")},
           "duration_ms": r["duration_ms"], "turns": r["turns"], "tests_before": before, "tests_after": after,
           "steps": st, "summary": r["text"][-600:], "dry_run": r["dry_run"]}
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    (out_dir / f"{args.harness}_{stamp}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{args.harness}_{stamp}.events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in r["events"]), encoding="utf-8")

    print(f"\n토큰: {headless.tok_line(r)} (서브에이전트 포함 {r['all_tokens']:,})")
    print(f"시간 {r['duration_ms']/1000:.0f}초 · 턴 {r['turns']} · 테스트 {after[0]}/{after[1]} 통과 (인수 테스트 포함)")
    print("단계:", ", ".join(f"{k}={'O' if v is True else 'X' if v is False else v}" for k, v in st.items()))
    if r["dry_run"]:
        print("(dry-run: 코드는 바뀌지 않았으므로 테스트 결과는 원본 그대로다)")
    skipped = [k for k in ("수정 전 테스트", "테스트 추가", "끝에 테스트") if not st[k]]
    print("\ncompare.md 에 붙일 줄:")
    print(f"| {args.harness} | {r['total_tokens']:,} | {r['all_tokens']:,} | {r['duration_ms']//1000} | {r['turns']} | "
          f"{after[0]}/{after[1]} | {', '.join(skipped) or '-'} | {', '.join(st['스킬'] + st['서브에이전트']) or '-'} |  |")


if __name__ == "__main__":
    main()
