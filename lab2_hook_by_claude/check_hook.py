#!/usr/bin/env python3
"""project/.claude/settings.json 의 PreToolUse Hook을 시험 사례(cases.json)로 채점한다.

  python3 check_hook.py              # 기본: project/
  python3 check_hook.py 다른/폴더

Hook을 실제로 실행해 본다 (Claude 호출 없음). exit 2 또는 permissionDecision=deny → 차단으로 본다.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
proj = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "project"
cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))

hooks = []
for f in (proj / ".claude" / "settings.json", proj / ".claude" / "settings.local.json"):
    if f.exists():
        for g in json.loads(f.read_text(encoding="utf-8")).get("hooks", {}).get("PreToolUse", []):
            for h in g.get("hooks", []):
                if h.get("type") == "command":
                    hooks.append((g.get("matcher", "*"), h["command"]))
if not hooks:
    print(f"PreToolUse Hook 없음 (하네스 미적용): {proj}/.claude/settings.json\n")


def matches(matcher, tool):
    return matcher in ("", "*") or re.fullmatch(matcher, tool) is not None


def blocked(case):
    event = {"hook_event_name": "PreToolUse", "tool_name": case["tool"], "tool_input": case["input"],
             "cwd": str(proj), "session_id": "check", "transcript_path": ""}
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(proj))
    for matcher, cmd in hooks:
        if not matches(matcher, case["tool"]):
            continue
        r = subprocess.run(cmd, shell=True, cwd=proj, env=env, input=json.dumps(event),
                           capture_output=True, text=True, timeout=20)
        if r.returncode == 2:
            return True, (r.stderr or r.stdout).strip().splitlines()[:1]
        try:
            out = json.loads(r.stdout or "{}")
            if out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
                return True, [out["hookSpecificOutput"].get("permissionDecisionReason", "")]
        except json.JSONDecodeError:
            pass
    return False, []


ok = 0
print(f"{'사례':<20}{'기대':<8}{'결과':<8}판정   이유")
for c in cases:
    b, why = blocked(c)
    got = "block" if b else "allow"
    good = got == c["expect"]
    ok += good
    print(f"{c['id']:<20}{c['expect']:<8}{got:<8}{'O' if good else 'X'}      {(why or [''])[0][:60]}")
miss = [c["id"] for c in cases if c["expect"] == "block" and not blocked(c)[0]]
over = [c["id"] for c in cases if c["expect"] == "allow" and blocked(c)[0]]
print(f"\n점수 {ok}/{len(cases)} · 놓친 차단 {len(miss)} {miss} · 잘못 막음 {len(over)} {over}")
sys.exit(0 if ok == len(cases) else 1)
