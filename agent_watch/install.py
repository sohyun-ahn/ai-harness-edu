#!/usr/bin/env python3
"""프로젝트에 agent_watch Hook을 켜고 끈다. .claude/settings.local.json 만 고친다 (팀 공유 설정은 그대로).

  python3 install.py /path/to/project            # 켜기
  python3 install.py /path/to/project --remove   # 끄기
"""
import argparse
import json
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "hook.py"
EVENTS = ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure",
          "SubagentStart", "SubagentStop", "Stop", "PreCompact", "SessionEnd"]
TAG = "agent_watch"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    f = Path(a.project).resolve() / ".claude" / "settings.local.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    s = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    hooks = s.setdefault("hooks", {})
    for ev in EVENTS:                                   # 예전 agent_watch 항목은 지운다
        hooks[ev] = [g for g in hooks.get(ev, []) if TAG not in json.dumps(g)]
        if not a.remove:
            g = {"hooks": [{"type": "command", "command": f'"{sys.executable}" "{HOOK}"', "timeout": 5}]}
            if ev.startswith(("PreTool", "PostTool")):
                g["matcher"] = "*"
            hooks[ev].append(g)
        if not hooks[ev]:
            del hooks[ev]
    if not hooks:
        del s["hooks"]
    f.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    print(("끔: " if a.remove else "켬: ") + str(f))


if __name__ == "__main__":
    main()
