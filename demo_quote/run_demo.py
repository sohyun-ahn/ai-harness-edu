#!/usr/bin/env python3
"""하네스 없는 Agent vs 있는 Agent — 같은 과제를 조건별로 k번 돌리고 숨은 테스트로 채점한다.

조건
  bare         project/ 만 (CLAUDE.md · .claude 없음, 내 PC 설정도 끊음)
  harness      project/ + harness/ (CLAUDE.md · Skill · verifier Sub Agent · Hook)
  superpowers  project/ + Superpowers 플러그인 (--plugin-dir)

사용
  python3 run_demo.py --cond bare harness --k 3            # 실제 실행 (계정 사용량 소모)
  python3 run_demo.py --variant ext --cond bare harness     # 확정 정책이 저장소 밖(하네스 안)에만 있을 때
  python3 run_demo.py --watch ...                           # Agent Watch(../agent_watch)로 실시간 보기
  python3 run_demo.py --show-cmd --cond harness            # 명령만 보기
  python3 dashboard.py                                     # runs/ 결과를 대시보드 HTML로
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
SUPERPOWERS = Path.home() / ".claude/plugins/cache/superpowers-marketplace/superpowers/5.1.0"
TOOLS = "Read,Grep,Glob,Edit,Write,MultiEdit,TodoWrite,Task,Agent,Skill,Bash(python3:*),Bash(ls:*),Bash(cat:*)"
TEST_CMD = [sys.executable, "-m", "unittest"]
MODEL = "claude-sonnet-5-5"
# 별칭(sonnet · haiku · opus)도 5.5 세대로 고정 — Sub Agent(Explore=haiku 등)까지
ALIASES = {"ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5-5",
           "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-5-5",
           "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-5-5"}
MINUTES = "docs/wiki/회의록_2026-09-02_단가정책확정.md"
WATCH = HERE.parent / "agent_watch"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare(cond, name, variant, watch):
    wd = RUNS / name / "work"
    shutil.copytree(HERE / "project", wd)
    if variant == "ext":                      # 확정 내용이 저장소에 없다 (하네스에만)
        (wd / MINUTES).unlink()
    if cond == "harness":
        shutil.copytree(HERE / "harness", wd, dirs_exist_ok=True)
    if watch:
        subprocess.run([sys.executable, str(WATCH / "install.py"), str(wd)], check=True, capture_output=True)
    return wd


def command(cond, model, watch=False):
    cmd = ["claude", "-p", (HERE / "task.md").read_text(encoding="utf-8"),
           "--model", model, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--allowedTools", TOOLS]
    src = ["project"] if cond == "harness" else []
    if watch:
        src.append("local")                   # Agent Watch Hook (settings.local.json)
    cmd += ["--setting-sources", ",".join(src)]
    if cond == "superpowers":
        cmd += ["--plugin-dir", str(SUPERPOWERS)]
    return cmd


def run_agent(cond, name, model, timeout, variant, watch):
    wd = prepare(cond, name, variant, watch)
    env = dict(os.environ, **ALIASES)
    env.pop("ANTHROPIC_API_KEY", None)          # 구독(Business · Max) 계정으로
    env["CLAUDE_PROJECT_DIR"] = str(wd)
    t0 = time.time()
    events = []
    with open(RUNS / name / "events.jsonl", "w", encoding="utf-8") as log:
        p = subprocess.Popen(command(cond, model, watch), cwd=wd, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True)
        try:
            for line in p.stdout:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                e["_ts"] = round(time.time() - t0, 2)
                events.append(e)
                log.write(json.dumps(e, ensure_ascii=False) + "\n")
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
    return wd, events, round(time.time() - t0, 1)


def analyse(events):
    m = {"tools": {}, "sub_agents": [], "skills": [], "read": [], "blocked": 0, "stop_blocked": 0}
    for e in events:
        if e.get("type") == "assistant":
            for b in e.get("message", {}).get("content", []):
                if b.get("type") != "tool_use":
                    continue
                n, i = b.get("name"), b.get("input", {})
                key = n if not e.get("parent_tool_use_id") else f"(sub) {n}"
                m["tools"][key] = m["tools"].get(key, 0) + 1
                if n in ("Task", "Agent"):
                    m["sub_agents"].append(i.get("subagent_type", "?"))
                if n == "Skill":
                    m["skills"].append(i.get("skill") or i.get("command") or "?")
                if n == "Read":
                    m["read"].append(Path(i.get("file_path", "")).name)
        text = json.dumps(e, ensure_ascii=False)
        m["blocked"] += text.count("차단:")
        m["stop_blocked"] += text.count("테스트 실패 상태로는")
        if e.get("type") == "result":
            u = e.get("usage", {})
            m.update(result_ok=e.get("subtype") == "success", turns=e.get("num_turns"),
                     cost_usd=e.get("total_cost_usd"), duration_s=round((e.get("duration_ms") or 0) / 1000, 1),
                     input=u.get("input_tokens", 0), cache_read=u.get("cache_read_input_tokens", 0),
                     cache_write=u.get("cache_creation_input_tokens", 0), output=u.get("output_tokens", 0),
                     model_usage={k: {kk: v.get(kk) for kk in ("inputTokens", "outputTokens", "cacheReadInputTokens",
                                                               "cacheCreationInputTokens")}
                                  for k, v in (e.get("modelUsage") or {}).items()},
                     final=(e.get("result") or "")[-600:])
    m["read_2025"] = "영업_단가정책_2025.md" in m["read"]
    m["read_draft"] = "영업_단가정책_2026Q3_초안.md" in m["read"]
    m["read_minutes"] = "회의록_2026-09-02_단가정책확정.md" in m["read"]
    m["read_reference"] = "reference.md" in m["read"]
    return m


def unittest_count(cwd, target):
    r = subprocess.run(TEST_CMD + target, cwd=cwd, capture_output=True, text=True, timeout=300)
    out = r.stderr
    ran = int((re.search(r"Ran (\d+) test", out) or [0, 0])[1])
    bad = sum(int(x) for x in re.findall(r"(?:failures|errors)=(\d+)", out))
    return ran, ran - bad, out


def grade(wd, name):
    g = RUNS / name / "grade"
    shutil.copytree(wd, g, ignore=shutil.ignore_patterns(".claude", "__pycache__"))
    m = {"regression_file_unchanged": sha(wd / "tests/test_pricing.py") == sha(HERE / "project/tests/test_pricing.py")}
    shutil.copy(HERE / "project/tests/test_pricing.py", g / "tests/test_pricing.py")
    shutil.copy(HERE / "hidden/test_acceptance.py", g / "tests/test_zz_hidden.py")
    ran, ok, out = unittest_count(g, ["tests.test_zz_hidden", "-v"])
    m.update(hidden_total=15, hidden_pass=ok if ran else 0, hidden_log=out[-3000:])
    ran, ok, _ = unittest_count(g, ["tests.test_pricing"])
    m.update(regression_pass=ok, regression_total=5)
    ran, ok, _ = unittest_count(wd, ["discover", "-s", "tests", "-t", "."])
    m.update(own_tests=ran, own_tests_pass=ok)
    src = "".join(p.read_text(encoding="utf-8") for p in (wd / "quote").glob("*.py"))
    m["rule_violations"] = len(re.findall(r"\bfloat\(|\bround\(", src))
    def base(rel):
        for root in (HERE / "harness", HERE / "project"):
            if (root / rel).exists():
                return root / rel
    m["files_changed"] = sorted(str(p.relative_to(wd)) for p in wd.rglob("*")
                                if p.is_file() and "__pycache__" not in p.parts and p.name != "settings.local.json"
                                and (base(p.relative_to(wd)) is None or sha(p) != sha(base(p.relative_to(wd)))))
    return m


def one(cond, i, model, timeout, stamp, variant, watch):
    name = f"{stamp}_{variant}_{cond}_{i}"
    (RUNS / name).mkdir(parents=True)
    wd, events, wall = run_agent(cond, name, model, timeout, variant, watch)
    res = {"name": name, "cond": cond, "variant": variant, "model": model, "wall_s": wall, **analyse(events), **grade(wd, name)}
    res["models_used"] = sorted((res.get("model_usage") or {}).keys())
    (RUNS / name / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cond", nargs="+", default=["bare", "harness"], choices=["bare", "harness", "superpowers"])
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--variant", default="repo", choices=["repo", "ext"], help="repo: 정보가 저장소에 다 있음 · ext: 확정 회의록이 저장소에 없음")
    ap.add_argument("--watch", action="store_true", help="Agent Watch Hook 켜기 (서버를 먼저 켠다)")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--show-cmd", action="store_true")
    a = ap.parse_args()
    if a.show_cmd:
        for c in a.cond:
            print(c, ":", " ".join(repr(x) if " " in x or not x else x for x in command(c, a.model, a.watch)))
        return
    stamp = time.strftime("%m%d-%H%M%S")
    jobs = [(c, i) for i in range(1, a.k + 1) for c in a.cond]
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(one, c, i, a.model, a.timeout, stamp, a.variant, a.watch): (c, i) for c, i in jobs}
        for f in cf.as_completed(futs):
            r = f.result()
            print(f"{r['name']:<34} {','.join(r['models_used'])}  숨은 테스트 {r['hidden_pass']:>2}/15  회귀 {r['regression_pass']}/5  "
                  f"Sub Agent {len(r['sub_agents'])}  Skill {len(r['skills'])}  차단 {r['blocked']}  "
                  f"턴 {r.get('turns')}  {r['wall_s']}s  출력 {r.get('output')}  "
                  f"읽음: 2025 {'O' if r['read_2025'] else '-'} 초안 {'O' if r['read_draft'] else '-'} 회의록 {'O' if r['read_minutes'] else '-'} 확정본 {'O' if r['read_reference'] else '-'}", flush=True)


if __name__ == "__main__":
    main()
