"""Lab 3-2 — Supervisor + 하위 Agent, 검증 관문, 재시도·대체 경로.

실행:  python sdk_optional/lab3_sdk_agent/agent_multi.py --track pangyo -n 2
고칠 곳: prompts.py 의 SUPERVISOR / SUBAGENTS, 아래 MAX_RETRIES

흐름:  Supervisor ─ Agent 도구 → classifier/전문 Agent (또는 extractor/estimator)
       → Supervisor 자체 검증 → 코드 검증(common/checks.verify)
       → 실패하면 피드백을 붙여 재시도 (최대 MAX_RETRIES)
       → 그래도 실패하면 싼 단일 Agent 로 대체 → 그래도 실패하면 '사람 확인' 결과
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions

from common import config
from common.checks import verify
from common.data import load_cases
from common.parse import extract_json
from sdk_optional.sdk_run import run_once
from sdk_optional.sdk_tools import SERVER, TOOL_NAMES
from sdk_optional.lab3_sdk_agent.agent_single import run_single
from sdk_optional.lab3_sdk_agent.prompts import ASK, SUBAGENTS, SUPERVISOR

MAX_RETRIES = 2  # TODO(실습): 0 으로 바꾸면 비용·품질이 어떻게 달라지나?


def multi_options(track):
    model_of = {"main": config.MODEL, "cheap": config.JUDGE_MODEL}
    agents = {
        name: AgentDefinition(description=desc, prompt=prompt, tools=tools, model=model_of[kind])
        for name, (desc, prompt, tools, kind) in SUBAGENTS[track].items()
    }
    return ClaudeAgentOptions(
        model=config.MODEL,
        system_prompt=SUPERVISOR[track],
        agents=agents,
        mcp_servers={"tools": SERVER},
        allowed_tools=["Agent"] + TOOL_NAMES[track],  # "Agent" = 하위 Agent 호출 도구
        permission_mode="dontAsk",
        setting_sources=[],
        max_turns=15,
        max_budget_usd=config.MAX_BUDGET_USD,
    )


async def run_multi(x, track, feedback=""):
    prompt = ASK[track].format(x=x)
    if feedback:
        prompt += f"\n\n[이전 시도 검증 실패 — 고쳐서 다시 낼 것]\n{feedback}"
    r = await run_once(prompt, multi_options(track), verbose=True)
    r["output"] = extract_json(r["text"])
    return r


def needs_human_result(track, problems):
    out = {"needs_human": True, "verdict": "fail", "reason": "자동 처리 실패: " + "; ".join(problems)}
    out.update({"intent": "기타", "reply": "담당자가 확인 후 답변드리겠습니다.", "citations": []}
               if track == "pangyo" else {"items": [], "quote": None})
    return {"output": out, "cost": 0.0, "path": "needs_human"}


async def run_with_retry(x, track):
    problems, spent = [], 0.0
    for attempt in range(1, MAX_RETRIES + 2):          # 첫 시도 + 재시도
        try:
            r = await run_multi(x, track, feedback="\n".join(problems))
            spent += r["cost"]
            problems = verify(track, r["output"], x)
            if not problems:
                return {**r, "path": f"multi#{attempt}", "cost": spent}
            print(f"  ! 검증 실패 ({attempt}회차): {problems}")
        except Exception as e:                          # 네트워크·예산 초과 등
            problems = [f"실행 오류: {e}"]
            print(f"  ! 실행 오류 ({attempt}회차): {e}")

    print("  → 대체 경로: 싼 모델 단일 Agent")
    try:
        r = await run_single(x, track, model=config.JUDGE_MODEL)
        spent += r["cost"]
        if not verify(track, r["output"], x):
            return {**r, "path": "fallback_single", "cost": spent}
    except Exception as e:
        problems.append(f"대체 경로 오류: {e}")
    return {**needs_human_result(track, problems), "cost": spent}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, choices=["pangyo", "pohang"])
    ap.add_argument("-n", type=int, default=2, help="처리할 건수 (앞에서부터)")
    ap.add_argument("--ids", nargs="*", help="특정 ID 만 (예: Q26 S06)")
    args = ap.parse_args()

    cases = load_cases(args.track)
    cases = [c for c in cases if c["id"] in args.ids] if args.ids else cases[: args.n]
    for case in cases:
        print(f"\n=== {case['id']} ===\n{case['input'][:200]}")
        r = await run_with_retry(case["input"], args.track)
        print(json.dumps(r["output"], ensure_ascii=False, indent=2))
        print(f"경로: {r['path']} | 누적 비용 ${r['cost']:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
