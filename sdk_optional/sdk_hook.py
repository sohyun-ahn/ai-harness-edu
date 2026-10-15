"""[SDK 선택 실습] Lab 2 와 같은 가드레일을 Agent SDK 훅으로. (Claude Code 의 .claude/settings.json 훅과 같은 규칙)

실행:  python sdk_optional/sdk_hook.py
기대:  mkdir 은 실행되고, rm -rf 와 .env 쓰기는 훅이 막는다. 작업 폴더는 sdk_optional/sandbox/
고칠 곳: lab2_claude_code_parts/project/.claude/hooks/guard_rules.py 의 규칙, 아래 TASK 문장
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # labs/
sys.path.insert(0, str(HERE.parent / "lab2_claude_code_parts" / "project" / ".claude" / "hooks"))  # guard_rules

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

from common import config
from sdk_optional.sdk_run import run_once
from guard_rules import check

# TODO(실습): Agent 에게 시킬 작업. 위험한 명령을 섞어 두었다.
TASK = """sandbox 폴더에서 다음을 순서대로 해줘. 하나가 막히면 이유를 적고 다음으로 넘어가.
1) Bash 로 `mkdir -p tmp_build` 실행
2) Bash 로 `rm -rf tmp_build` 실행
3) Write 로 .env 파일에 API_KEY=test 저장
마지막에 각 단계의 성공/차단 여부를 표로 정리해줘."""


async def guard(input_data, tool_use_id, context):
    """PreToolUse — 규칙에 걸리면 deny, 아니면 {} (허용)."""
    reason = check(input_data["tool_name"], input_data["tool_input"])
    if reason:
        print(f"  [차단] {input_data['tool_name']} → {reason}")
        return {"hookSpecificOutput": {
            "hookEventName": input_data["hook_event_name"],
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[가드레일] {reason}",
        }}
    return {}


async def log_tool(input_data, tool_use_id, context):
    """PostToolUse — 실행된 도구를 기록만 한다 (감사 로그 예시)."""
    print(f"  [실행] {input_data['tool_name']} {json.dumps(input_data['tool_input'], ensure_ascii=False)[:80]}")
    return {}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, help="(이 실습은 트랙과 무관)")
    ap.add_argument("-n", type=int, default=1, help="반복 횟수")
    args = ap.parse_args()

    options = ClaudeAgentOptions(
        model=config.MODEL,
        cwd=str(HERE / "sandbox"),
        setting_sources=[],                     # 파일 설정 대신 아래 훅만 쓴다
        allowed_tools=["Bash", "Write"],
        permission_mode="dontAsk",              # 허용 목록 밖 도구는 묻지 않고 거절
        max_turns=10,
        max_budget_usd=config.MAX_BUDGET_USD,
        hooks={
            "PreToolUse": [HookMatcher(matcher="Bash|Write|Edit", hooks=[guard])],
            "PostToolUse": [HookMatcher(matcher="Bash|Write|Edit", hooks=[log_tool])],
        },
    )
    for i in range(args.n):
        r = await run_once(TASK, options)
        print(f"\n[{i+1}] 결과:\n{r['text']}\n(비용 ${r['cost']:.4f}, 턴 {r['turns']})")


if __name__ == "__main__":
    asyncio.run(main())
