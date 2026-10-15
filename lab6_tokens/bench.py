"""Lab 6 — 토큰 경제학: 고정 과제 5개(tasks.json)에 레버를 하나씩 걸고 헤드리스로 토큰을 잰다.

실행:  python lab6_tokens/bench.py --levers baseline,brief
       python lab6_tokens/bench.py --levers haiku,sonnet,opus          (모델 라우팅 — 분류·추출만)
       python lab6_tokens/bench.py --levers cache                      (같은 앞부분 3번 → 캐시 읽기)
       python lab6_tokens/bench.py --levers all --dry-run
결과:  표 출력 + results/tokens_<시각>.json  →  python lab6_tokens/quiz.py 로 퀴즈 정답
고칠 곳: LEVERS 안의 TODO(실습) — 지시 문장, 모델, 플러그인 진입 명령

Business 요금제에서는 cost 가 실제 청구와 다를 수 있다 → 토큰으로 비교한다.
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from common import config, headless, workspace

TASKS = {k: v for k, v in json.loads((HERE / "tasks.json").read_text(encoding="utf-8")).items() if k.startswith("t")}
STABLE_PREFIX = (HERE.parent / "lab3_context" / "manual.md").read_text(encoding="utf-8")  # 캐시 실험용 긴 고정 앞부분

# TODO(실습): 출력을 줄이는 지시 문장
BRIEF = "답만 쓴다. 인사·설명·요약·되묻기 없이 최대 3줄. 코드는 바뀐 줄만."

# 레버: 이름 → 설정. tasks 가 있으면 그 과제만. plugin 이 있으면 설치돼 있어야 돈다.
LEVERS = {
    "baseline": {"desc": "기준선 (sonnet · 설정·도구 없음)"},
    "brief": {"desc": "출력 짧게 지시", "system_append": BRIEF},
    # TODO(실습): 모델 라우팅 — 싼 일에 싼 모델
    "haiku": {"desc": "--model haiku", "model": "haiku", "tasks": ["t1", "t2"]},
    "sonnet": {"desc": "--model sonnet", "model": "sonnet", "tasks": ["t1", "t2"]},
    "opus": {"desc": "--model opus", "model": "opus", "tasks": ["t1", "t2"]},
    "cache": {"desc": "긴 고정 앞부분 ×3 (5분 안)", "system_append": STABLE_PREFIX, "tasks": ["t1"], "repeat": 3},
    "subagent": {"desc": "요약을 haiku 서브에이전트에", "tasks": ["t3"], "tools": "Agent,Read",
                 "system_append": "요약 작업은 반드시 summarizer 서브에이전트에게 원문 그대로 넘기고, 받은 결과만 출력한다.",
                 "agents_json": {"summarizer": {"description": "긴 글 요약 전담", "prompt": "받은 글을 5줄 이내로 요약한다.",
                                                "tools": ["Read"], "model": "haiku"}}},
    # 플러그인 레버 — 설치: README 참고. 진입 방식은 플러그인 README 확인 (확인 필요)
    "caveman": {"desc": "caveman 플러그인", "plugin": "caveman", "prefix": "/caveman "},   # TODO(실습): 진입 명령
    "ponytail": {"desc": "ponytail 플러그인", "plugin": "ponytail", "prefix": ""},       # TODO(실습): 진입 명령
    "rtk": {"desc": "rtk 로 명령 출력 압축", "tasks": ["t5"], "needs_bin": "rtk",
            "system_append": "셸 명령은 앞에 rtk 를 붙여 실행한다 (예: rtk python -m unittest)."},
}
DEFAULT = "baseline,brief"


def plugin_installed(name):
    try:
        out = subprocess.run([config.CLAUDE_BIN, "plugin", "list"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return f"{name}@" in out


def opts_for(lever, task):
    lv = LEVERS[lever]
    o = {"model": lv.get("model", config.HEADLESS_MODEL), "setting_sources": "", "tools": lv.get("tools", "")}
    for k in ("system_append", "agents_json"):
        if lv.get(k):
            o[k] = lv[k]
    if lv.get("tools"):
        o["allowed_tools"] = lv["tools"]
    if lv.get("plugin"):
        o["setting_sources"] = "user"          # /plugin 으로 설치한 것을 읽는다 (다른 user 설정도 섞인다)
    if TASKS[task].get("bash"):                 # 테스트 실행 과제: lab4 샘플 앱 복사본에서
        o["cwd"] = workspace.build("lab6-t5", copy={p.name: p for p in (HERE.parent / "lab4_public_harness" /
                                                                        "sample_app").iterdir()})
        o["tools"] = "Bash,Read"
        o["allowed_tools"] = "Bash(python -m unittest*),Bash(python3 -m unittest*),Bash(rtk *),Read"
    else:
        o["cwd"] = workspace.build("lab6-empty")
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levers", default=DEFAULT, help=f"쉼표로 ({', '.join(LEVERS)}) 또는 all")
    ap.add_argument("--tasks", help="과제를 좁힌다 (예: t1,t3)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show-cmd", action="store_true")
    args = ap.parse_args()
    headless.banner(args.dry_run)
    levers = list(LEVERS) if args.levers == "all" else args.levers.split(",")
    only = set(args.tasks.split(",")) if args.tasks else None

    rows = []
    for lever in levers:
        lv = LEVERS[lever]
        if not args.dry_run and lv.get("plugin") and not plugin_installed(lv["plugin"]):
            print(f"[건너뜀] {lever}: 플러그인이 설치돼 있지 않다 (README 의 설치 명령)")
            continue
        if not args.dry_run and lv.get("needs_bin") and not shutil.which(lv["needs_bin"]):
            print(f"[건너뜀] {lever}: `{lv['needs_bin']}` 명령이 없다 (설치 방법은 공식 README 확인)")
            continue
        for task in lv.get("tasks", list(TASKS)):
            if only and task not in only:
                continue
            for rep in range(lv.get("repeat", 1)):
                r = headless.run(lv.get("prefix", "") + TASKS[task]["prompt"], dry_run=args.dry_run,
                                 fixture=f"lab6_bench.json#{lever}/{task}", **opts_for(lever, task))
                if args.show_cmd and rep == 0:
                    print("  $", r["cmd_str"])
                tag = f"{lever}#{rep + 1}" if lv.get("repeat") else lever
                rows.append({"lever": tag, "task": f"{task} {TASKS[task]['name']}", "in": r["input_tokens"],
                             "cr": r["cache_read"], "cw": r["cache_write"], "out": r["output_tokens"],
                             "total": r["total_tokens"], "all": r["all_tokens"], "turns": r["turns"],
                             "ms": r["duration_ms"], "cost": r["cost"], "err": r["is_error"]})
                print(f"  {tag:<12} {task}  {headless.tok_line(r)}")

    headless.print_table(rows, [("lever", "레버"), ("task", "과제"), ("in", "in"), ("cr", "캐시읽기"), ("cw", "캐시쓰기"),
                                ("out", "out"), ("total", "메인 합계"), ("all", "서브 포함"), ("turns", "턴"), ("ms", "ms")],
                         title="=== 레버 × 과제 ===")
    base = {r["task"]: r for r in rows if r["lever"] == "baseline"}
    summary = []
    for lever in dict.fromkeys(r["lever"] for r in rows):
        mine = [r for r in rows if r["lever"] == lever]
        same = [r for r in mine if r["task"] in base]
        d_out = sum(r["out"] for r in same) - sum(base[r["task"]]["out"] for r in same)
        d_all = sum(r["all"] for r in same) - sum(base[r["task"]]["all"] for r in same)
        b_out = sum(base[r["task"]]["out"] for r in same) or 1
        b_all = sum(base[r["task"]]["all"] for r in same) or 1
        summary.append({"lever": lever, "n": len(mine), "out": sum(r["out"] for r in mine),
                        "all": sum(r["all"] for r in mine),
                        "d_out": f"{d_out / b_out:+.0%}" if same and lever != "baseline" else "-",
                        "d_all": f"{d_all / b_all:+.0%}" if same and lever != "baseline" else "-"})
    headless.print_table(summary, [("lever", "레버"), ("n", "실행"), ("out", "out 합"), ("all", "전체 합"),
                                   ("d_out", "out 대비"), ("d_all", "전체 대비")], title="=== 기준선 대비 (같은 과제끼리) ===")

    res = HERE / "results"
    res.mkdir(exist_ok=True)
    path = res / f"tokens_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps({"meta": {"levers": levers, "model": config.HEADLESS_MODEL, "dry_run": args.dry_run,
                                         "at": datetime.now().isoformat(timespec="seconds")},
                                "rows": rows, "summary": summary}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {path}  →  python lab6_tokens/quiz.py")


if __name__ == "__main__":
    main()
