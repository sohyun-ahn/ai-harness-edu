"""Lab 3-1 — 단일 Agent: 시스템 프롬프트 + 사용자 정의 도구(search_kb / get_price).

실행:  python sdk_optional/lab3_sdk_agent/agent_single.py --track pangyo -n 3
고칠 곳: prompts.py 의 SINGLE
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from claude_agent_sdk import ClaudeAgentOptions

from common import config
from common.checks import verify
from common.data import load_cases
from common.parse import extract_json
from sdk_optional.sdk_run import run_once
from sdk_optional.sdk_tools import SERVER, TOOL_NAMES
from sdk_optional.lab3_sdk_agent.prompts import ASK, SINGLE


def single_options(track, model=None):
    return ClaudeAgentOptions(
        model=model or config.MODEL,
        system_prompt=SINGLE[track],
        mcp_servers={"tools": SERVER},
        allowed_tools=TOOL_NAMES[track],   # 이 도구만 자동 허용
        permission_mode="dontAsk",         # 나머지 도구(Bash, Write …)는 거절
        setting_sources=[],                # 내 PC 의 CLAUDE.md·설정에 영향받지 않게
        max_turns=8,
        max_budget_usd=config.MAX_BUDGET_USD,
    )


async def run_single(x, track, model=None, verbose=False):
    """입력 하나 처리 → run_once 결과 + output(JSON)."""
    r = await run_once(ASK[track].format(x=x), single_options(track, model), verbose=verbose)
    r["output"] = extract_json(r["text"])
    return r


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, choices=["pangyo", "pohang"])
    ap.add_argument("-n", type=int, default=3, help="처리할 건수 (앞에서부터)")
    args = ap.parse_args()

    for case in load_cases(args.track)[: args.n]:
        print(f"\n=== {case['id']} ===\n{case['input'][:200]}")
        r = await run_single(case["input"], args.track, verbose=True)
        print(json.dumps(r["output"], ensure_ascii=False, indent=2) if r["output"] else r["text"])
        print(f"검증: {verify(args.track, r['output'], case['input']) or '통과'}"
              f" | ${r['cost']:.4f} | 턴 {r['turns']} | {r['duration_ms']}ms")


if __name__ == "__main__":
    asyncio.run(main())
