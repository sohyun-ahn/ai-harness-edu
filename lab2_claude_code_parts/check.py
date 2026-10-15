"""Lab 2 — 프로젝트 부품(스킬·서브에이전트·명령·훅)이 헤드리스에서도 실제로 작동하는지 확인한다.

실행:  python lab2_claude_code_parts/check.py                 (4건 모두 · 호출 4번)
       python lab2_claude_code_parts/check.py --only hook     (하나만)
       python lab2_claude_code_parts/check.py --hook-only     (훅 스크립트만 직접 — 호출 없음)
       python lab2_claude_code_parts/check.py --dry-run       (저장된 출력으로)
고칠 곳: project/.claude/ 아래 파일들 (SKILL.md, agents/reviewer.md, commands/*.md, hooks/guard_rules.py)

project/ 를 임시 작업 폴더로 복사해서 돌린다 → .env 가 혹시 만들어져도 저장소에는 안 남는다.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import config, headless, workspace

HERE = Path(__file__).resolve().parent
PROJECT = HERE / "project"

TOOLS = "Read,Grep,Glob,Write,Edit,Bash,Skill,Agent"


def has_skill(r, ws):
    calls = headless.tool_uses(r["events"])
    used = any(c["name"] == "Skill" and "incident-report" in json.dumps(c["input"]) for c in calls)
    return used or "[장애 보고]" in r["text"], "Skill 도구로 incident-report 호출" if used else "양식 제목으로 추정"


def has_agent(r, ws):
    calls = headless.tool_uses(r["events"])
    hit = [c for c in calls if c["name"] in ("Agent", "Task") and c["input"].get("subagent_type") == "reviewer"]
    inner = [c["name"] for c in calls if hit and c["parent"] == hit[0]["id"]]
    return bool(hit), f"reviewer 안에서 쓴 도구: {sorted(set(inner)) or '없음'}"


def blocked_env(r, ws):
    calls = headless.tool_uses(r["events"])
    results = headless.tool_results(r["events"])
    tries = [c for c in calls if c["name"] in ("Write", "Edit") and ".env" in str(c["input"].get("file_path", ""))]
    denied = [c for c in tries if "가드레일" in results.get(c["id"], (False, ""))[1]]
    exists = (ws / ".env").exists()
    return bool(denied) and not exists, f".env 쓰기 시도 {len(tries)}번 · 훅 차단 {len(denied)}번 · 파일 생김={exists}"


def ran_command(r, ws):
    ok = "분류" in r["text"] and "담당" in r["text"]
    return ok, "명령 본문의 네 줄 형식으로 답함" if ok else "형식이 다름 (-p 에서 사용자 명령이 펼쳐지는지 확인 필요)"


CHECKS = {
    # TODO(실습): 프롬프트를 바꿔 보고 스킬·에이전트가 언제 호출되고 언제 안 되는지 본다.
    "skill": ("스킬", "어제 14시에 MES 가 20분 멈췄어. 장애 보고서 양식으로 정리해줘", has_skill),
    "agent": ("서브에이전트", "src/order_api.py 를 리뷰해줘. 고치지는 마.", has_agent),
    "hook": ("훅", "Write 도구로 .env 파일을 만들고 API_KEY=test 한 줄을 써줘.", blocked_env),
    "command": ("슬래시 명령", "/triage 노트북이 갑자기 안 켜져요. 내일 고객 발표가 있어요.", ran_command),
}


def hook_only():
    """Claude 를 부르지 않고 guard.py 에 가짜 입력을 넣어 본다."""
    samples = [
        {"tool_name": "Bash", "tool_input": {"command": "rm -rf build"}},
        {"tool_name": "Bash", "tool_input": {"command": "ls -al"}},
        {"tool_name": "Write", "tool_input": {"file_path": "/x/.env", "content": "A=1"}},
        {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}},
    ]
    for s in samples:
        p = subprocess.run([sys.executable, str(PROJECT / ".claude" / "hooks" / "guard.py")],
                           input=json.dumps(s), capture_output=True, text=True)
        verdict = json.loads(p.stdout)["hookSpecificOutput"]["permissionDecisionReason"] if p.stdout.strip() else "허용"
        print(f"  {s['tool_name']:<5} {json.dumps(s['tool_input'], ensure_ascii=False)[:50]:<52} → {verdict}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(CHECKS), help="하나만 확인")
    ap.add_argument("--hook-only", action="store_true", help="훅 스크립트만 직접 실행 (호출 없음)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show-cmd", action="store_true")
    ap.add_argument("--track", default=config.TRACK, help="(이 실습은 트랙과 무관)")
    args = ap.parse_args()
    headless.banner(args.dry_run)

    if args.hook_only:
        hook_only()
        return
    rows = []
    for key, (name, prompt, judge) in CHECKS.items():
        if args.only and key != args.only:
            continue
        ws = workspace.build("lab2-project", copy={p.name: p for p in PROJECT.iterdir()})
        r = headless.run(prompt, cwd=ws, model=config.HEADLESS_MODEL, setting_sources="project",
                         allowed_tools=TOOLS, stream=True, dry_run=args.dry_run, fixture=f"lab2_{key}")
        if args.show_cmd:
            print("  $", r["cmd_str"])
        ok, note = judge(r, ws)
        print(f"[{'통과' if ok else '확인'}] {name}: {note}\n       답: {r['text'][:100].strip()!r}")
        rows.append({"check": name, "ok": ok, "turns": r["turns"], "total": r["total_tokens"], "all": r["all_tokens"]})
    headless.print_table(rows, [("check", "부품"), ("ok", "작동"), ("turns", "턴"), ("total", "메인 토큰"),
                                ("all", "전체 토큰")])


if __name__ == "__main__":
    main()
