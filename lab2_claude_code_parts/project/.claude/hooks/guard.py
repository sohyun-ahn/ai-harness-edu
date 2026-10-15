"""Claude Code PreToolUse 훅 — 도구 실행 직전에 호출되어 위험한 명령을 막는다.

Claude Code 가 stdin 으로 JSON({"tool_name", "tool_input", ...})을 넘겨준다.
막을 때는 stdout 으로 permissionDecision "deny" JSON 을 내보낸다.
규칙은 같은 폴더의 guard_rules.py 에 있다.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # guard_rules.py
from guard_rules import check  # noqa: E402

data = json.load(sys.stdin)
reason = check(data.get("tool_name", ""), data.get("tool_input", {}))
if reason:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": f"[가드레일] {reason}",
    }}, ensure_ascii=False))
sys.exit(0)
