#!/usr/bin/env python3
"""업무 과제를 하네스 미적용 · 업무 하네스로 반복 실행하고 채점한다 (Claude Sonnet 5.5 · 계정 사용량 소모).

  python3 run_tasks.py --cond bare single --tasks T1 T2 T3 T4 T5 T6 --k 1
  python3 run_tasks.py --cond bare single multi --tasks T7 --k 2      # 단일 vs 멀티에이전트 하네스
  python3 run_tasks.py --watch ...      # ../agent_watch 로 실시간 보기 (서버 먼저)

과제마다 새 작업 폴더(runs/…)를 만들어 workspace/를 복사하고, harness 조건이면 harness/를 덮어쓴다.
"""
import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from grade import grade

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
MODEL = "claude-sonnet-5-5"
ALIASES = {"ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5-5", "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-5-5",
           "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-5-5"}
TOOLS = "Read,Grep,Glob,Edit,Write,MultiEdit,TodoWrite,Task,Agent,Skill,Bash(python3:*),Bash(ls:*),Bash(cat:*),Bash(mkdir:*),Bash(head:*),Bash(wc:*)"


def one(cond, task, i, stamp, watch, timeout):
    wd = RUNS / f"{stamp}_{task}_{cond}_{i}"
    shutil.copytree(HERE / "workspace", wd)
    if cond in ("harness", "single", "multi"):
        shutil.copytree(HERE / "harness", wd, dirs_exist_ok=True)
    if cond == "multi":                               # 단일 하네스 + Sub Agent · 오케스트레이션 규칙
        shutil.copytree(HERE / "harness_multi" / ".claude", wd / ".claude", dirs_exist_ok=True)
        with open(wd / "CLAUDE.md", "a", encoding="utf-8") as f:
            f.write("\n" + (HERE / "harness_multi" / "CLAUDE.md").read_text(encoding="utf-8"))
    if watch:
        subprocess.run([sys.executable, str(HERE.parent / "agent_watch" / "install.py"), str(wd)], capture_output=True)
    prompt = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))[task]
    src = (["project"] if cond != "bare" else []) + (["local"] if watch else [])
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json", "--permission-mode", "acceptEdits",
           "--allowedTools", TOOLS, "--setting-sources", ",".join(src)]
    env = dict(os.environ, **ALIASES, CLAUDE_PROJECT_DIR=str(wd))
    env.pop("ANTHROPIC_API_KEY", None)
    t0 = time.time()
    try:
        out = json.loads(subprocess.run(cmd, cwd=wd, env=env, capture_output=True, text=True, timeout=timeout,
                                        stdin=subprocess.DEVNULL).stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        out = {}
    (wd / "_final.txt").write_text(out.get("result") or "", encoding="utf-8")   # 대화창 답도 채점에 넣는다
    mu = out.get("modelUsage") or {}
    tok = sum(sum((v.get(k) or 0) for k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")) for v in mu.values())
    r = grade(wd, task)
    r.update(cond=cond, run=i, sec=round(time.time() - t0), tokens=tok, models=sorted(mu.keys()), final=(out.get("result") or "")[-400:])
    (wd / "_result.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cond", nargs="+", default=["bare", "harness"], choices=["bare", "single", "multi", "harness"])
    ap.add_argument("--tasks", nargs="+", default=["T1", "T2", "T3", "T4", "T5", "T6", "T7"])
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--watch", action="store_true")
    a = ap.parse_args()
    stamp = time.strftime("%m%d-%H%M%S")
    jobs = [(c, t, i) for i in range(1, a.k + 1) for t in a.tasks for c in a.cond]
    res = []
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        for f in cf.as_completed([ex.submit(one, c, t, i, stamp, a.watch, a.timeout) for c, t, i in jobs]):
            r = f.result()
            res.append(r)
            miss = [n for n, ok in r["checks"] if not ok]
            print(f"{r['task']} {r['cond']:<7} #{r['run']}  {r['score']}/{r['total']}  원본 {'O' if r['inputs_intact'] else 'X'}"
                  f"  out/{r['task']} {'O' if r['in_out_folder'] else '-'}  {r['sec']}s  {r['tokens']:,}토큰  놓침: {'; '.join(miss)[:120]}", flush=True)
    print()
    for c in a.cond:
        g = [r for r in res if r["cond"] == c]
        print(f"{c:<7} 점수 {sum(r['score'] for r in g)}/{sum(r['total'] for r in g)} · 원본 보존 {sum(r['inputs_intact'] for r in g)}/{len(g)}"
              f" · 평균 {sum(r['sec'] for r in g) / len(g):.0f}초 · 평균 {sum(r['tokens'] for r in g) / len(g):,.0f}토큰")


if __name__ == "__main__":
    main()
