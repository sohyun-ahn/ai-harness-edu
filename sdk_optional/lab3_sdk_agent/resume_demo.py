"""Lab 3-3 — 세션 이어가기: 같은 대화 안의 여러 턴(ClaudeSDKClient) + 나중에 resume.

실행:  python sdk_optional/lab3_sdk_agent/resume_demo.py --track pangyo
보는 것: 턴이 쌓일수록 cache_read(캐시로 읽은 토큰)가 늘고, resume 하면 앞 대화를 기억한다.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from claude_agent_sdk import ClaudeSDKClient, ResultMessage

from common import config
from common.data import load_cases
from sdk_optional.sdk_run import run_once
from sdk_optional.lab3_sdk_agent.agent_single import single_options
from sdk_optional.lab3_sdk_agent.prompts import ASK

# TODO(실습): 이어서 물어볼 말을 바꿔 보세요.
FOLLOW_UPS = {
    "pangyo": ["방금 답변을 2문장으로 줄여줘. 형식은 그대로.", "인용한 조항 ID 만 다시 알려줘."],
    "pohang": ["수량이 가장 많은 품목만 다시 알려줘.", "견적 합계만 숫자로 다시 알려줘."],
}


def show(tag, m):
    u = m.usage or {}
    print(f"[{tag}] 턴 {m.num_turns} | in {u.get('input_tokens', 0)} + 캐시 {u.get('cache_read_input_tokens', 0)}"
          f" / out {u.get('output_tokens', 0)} | ${m.total_cost_usd or 0:.4f}\n  → {(m.result or '')[:150]}")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, choices=["pangyo", "pohang"])
    ap.add_argument("-n", type=int, default=1, help="(사용 안 함 — 인자 형식 통일용)")
    args = ap.parse_args()
    case = load_cases(args.track)[0]

    # 1) 한 대화 안에서 여러 턴 — 앞 내용을 그대로 이어 간다
    session_id = None
    async with ClaudeSDKClient(options=single_options(args.track)) as client:
        for i, msg in enumerate([ASK[args.track].format(x=case["input"])] + FOLLOW_UPS[args.track]):
            await client.query(msg)
            async for m in client.receive_response():
                if isinstance(m, ResultMessage):
                    show(f"턴{i+1}", m)
                    session_id = m.session_id

    # 2) 프로그램을 다시 켰다고 치고 — session_id 로 이어서 묻기
    print(f"\nresume: {session_id}")
    opts = single_options(args.track)
    opts.resume = session_id
    r = await run_once("처음에 받은 입력이 무엇이었는지 한 줄로 말해줘.", opts)
    print(f"[resume] ${r['cost']:.4f} | 캐시 {r['cache_read']}\n  → {r['text'][:200]}")


if __name__ == "__main__":
    asyncio.run(main())
