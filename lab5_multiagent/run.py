"""Lab 5 — Supervisor(메인) + 서브에이전트를 헤드리스로 돌리고 이벤트를 저장·검증·시각화한다.

실행:  python lab5_multiagent/run.py --track pangyo --ids Q10
       python lab5_multiagent/run.py --track pohang --ids S06
       python lab5_multiagent/run.py --track pangyo --dry-run          (sample_events.jsonl 로)
결과:  runs/<시각>_<track>_<id>.jsonl (stream-json 원본 + _ts) 와 같은 이름 .html (타임라인)
고칠 곳: project/.claude/agents/*.md, project/.claude/skills/orchestrate-*/SKILL.md, 아래 EXPECTED

옵션:  --output-format stream-json --verbose  (서브에이전트 안의 이벤트까지 parent_tool_use_id 로 온다)
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from common import config, headless, workspace
from common.checks import verify
from common.data import load_cases
from common.parse import extract_json
from visualize import analyze, delegations, lane_rows, render

# TODO(실습): 지켜야 할 위임 순서. 스킬에서 단계를 바꾸면 여기도 맞춘다.
EXPECTED = {"pangyo": ["classifier", "responder-*", "verifier-inquiry"],
            "pohang": ["extractor", "estimator", "verifier-quote"]}
ASK = {"pangyo": "orchestrate-inquiry 스킬 순서대로 다음 사내 문의를 처리해 줘.\n\n문의: {x}",
       "pohang": "orchestrate-quote 스킬 순서대로 다음 사양서를 처리해 줘.\n\n{x}"}
TOOLS = "Read,Grep,Glob,Skill,Agent"
FIXTURE = {"pangyo": HERE / "sample_events.jsonl", "pohang": "lab5_pohang"}


def order_ok(track, subs):
    """기대 순서가 (재시도를 빼고) 차례대로 나왔는가."""
    want, i = EXPECTED[track], 0
    for s in subs:
        if i < len(want) and (s == want[i] or (want[i].endswith("*") and s.startswith(want[i][:-1]))):
            i += 1
    return i == len(want)


def live(ev):
    """도착하는 이벤트를 한 줄씩 보여준다."""
    if ev.get("type") != "assistant":
        return
    who = "sub" if ev.get("parent_tool_use_id") else "main"
    for b in (ev.get("message") or {}).get("content") or []:
        if b.get("type") == "tool_use":
            inp = b.get("input") or {}
            what = inp.get("subagent_type") or inp.get("skill") or inp.get("pattern") or inp.get("file_path") or ""
            print(f"  {ev.get('_ts', 0)/1000:6.1f}s [{who}] {b.get('name')} {what}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, choices=["pangyo", "pohang"])
    ap.add_argument("--ids", nargs="*", help="처리할 ID (기본: 판교 Q10, 포항 S06)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show-cmd", action="store_true")
    args = ap.parse_args()
    headless.banner(args.dry_run)
    ids = args.ids or (["Q10"] if args.track == "pangyo" else ["S06"])

    runs = HERE / "runs"
    runs.mkdir(exist_ok=True)
    for case in [c for c in load_cases(args.track) if c["id"] in ids]:
        ws = workspace.build(f"lab5-{args.track}", copy={"CLAUDE.md": HERE / "project" / "CLAUDE.md",
                                                        ".claude": HERE / "project" / ".claude"}, track=args.track)
        print(f"\n=== {case['id']} · 작업 폴더 {ws} ===")
        r = headless.run(ASK[args.track].format(x=case["input"]), cwd=ws, model=config.HEADLESS_MODEL,
                         setting_sources="project", allowed_tools=TOOLS, stream=True, on_event=live,
                         dry_run=args.dry_run, fixture=FIXTURE[args.track])
        if args.show_cmd:
            print("  $", r["cmd_str"])
        path = runs / f"{datetime.now():%Y%m%d_%H%M%S}_{args.track}_{case['id']}.jsonl"
        path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in r["events"]) + "\n", encoding="utf-8")

        a = analyze(r["events"])
        subs = [c.get("sub") for c in delegations(a)]
        out = extract_json(r["text"])
        problems = verify(args.track, out, case["input"])
        headless.print_table(lane_rows(a), [("lane", "줄"), ("model", "모델"), ("in", "in"), ("cache", "캐시"),
                                             ("out", "out"), ("total", "합계"), ("tools", "도구"), ("span", "구간(s)")])
        print(f"\n위임 순서: {' → '.join(subs) or '(없음)'}  | 기대 순서 지킴: {'O' if order_ok(args.track, subs) else 'X'}")
        print(f"코드 검증(common/checks): {problems or '통과'}")
        print(f"메인 토큰 {r['total_tokens']:,} · 서브 포함 {r['all_tokens']:,} · 턴 {r['turns']} · {r['duration_ms']/1000:.1f}s")
        html_path = path.with_suffix(".html")
        html_path.write_text(render(a, f"{args.track} {case['id']} 타임라인"), encoding="utf-8")
        print(f"이벤트: {path}\n타임라인: {html_path}")


if __name__ == "__main__":
    main()
