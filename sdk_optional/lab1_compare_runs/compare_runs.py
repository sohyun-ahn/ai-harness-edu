"""Lab 1 — 같은 질문을 N번 돌려서 '하네스 없음' 과 '하네스 있음' 을 비교한다.

실행:  python sdk_optional/lab1_compare_runs/compare_runs.py --track pangyo -n 5
고칠 곳: harness_prompt.md (코드 수정 없음), 아래 SAMPLE_ID
"""
import argparse
import asyncio
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # labs/ 를 import 경로에

from claude_agent_sdk import ClaudeAgentOptions

from common import config
from common.data import load_cases
from common.parse import extract_json
from sdk_optional.sdk_run import run_once
from sdk_optional.sdk_tools import SERVER, TOOL_NAMES

HERE = Path(__file__).parent

# TODO(실습): 다른 문의·사양서 ID 로 바꿔 보세요 (data/README.md 참고)
SAMPLE_ID = {"pangyo": "Q25", "pohang": "S06"}

ASK = {
    "pangyo": "다음 사내 문의를 IT/구매/인사/보안/기타 중 하나로 분류하고 답변해 주세요.\n\n문의: {x}",
    "pohang": "다음 사양서에서 품목·규격·재질·수량·단위·비고를 뽑고 견적을 내 주세요.\n\n{x}",
}


def load_harness_prompt(track):
    """harness_prompt.md 에서 '## 공통' + '## <track>' 부분만 이어 붙인다."""
    text = (HERE / "harness_prompt.md").read_text(encoding="utf-8")
    sections = dict(re.findall(r"^## (\S+)\n(.*?)(?=^## |\Z)", text, re.S | re.M))
    return sections["공통"].strip() + "\n\n" + sections[track].strip()


def label_of(track, text):
    """일관성 비교용 '라벨' — 판교는 분류 결과, 포항은 (품목, 수량) 목록."""
    data = extract_json(text)
    if track == "pangyo":
        if data and data.get("intent"):
            return data["intent"]
        m = re.search(r"(IT|구매|인사|보안|기타)", text)
        return f"{m.group(1)}(본문에서 추정)" if m else "분류 없음"
    if data and data.get("items"):
        return ", ".join(f"{i.get('품목')}:{i.get('수량')}" for i in data["items"])
    return "형식 없음(JSON 아님)"


def bare_options():
    # 하네스 없음: 시스템 프롬프트 없음, 설정 파일 안 읽음, 도구 없음
    return ClaudeAgentOptions(model=config.MODEL, setting_sources=[], allowed_tools=[],
                              permission_mode="dontAsk", max_turns=3)


def harness_options(track):
    # 하네스 있음: 규칙 + 출력 형식 + 지식베이스/단가 도구
    return ClaudeAgentOptions(model=config.MODEL, system_prompt=load_harness_prompt(track),
                              mcp_servers={"tools": SERVER}, allowed_tools=TOOL_NAMES[track],
                              setting_sources=[], permission_mode="dontAsk", max_turns=8,
                              max_budget_usd=config.MAX_BUDGET_USD)


async def trial(name, track, prompt, make_options, n):
    print(f"\n=== {name} ({n}회) ===")
    labels, texts, costs, tokens = [], [], [], []
    for i in range(n):
        r = await run_once(prompt, make_options())
        label = label_of(track, r["text"])
        labels.append(label); texts.append(r["text"].strip()); costs.append(r["cost"])
        tokens.append(r["input_tokens"] + r["cache_read"] + r["output_tokens"])
        print(f" {i+1}. 라벨={label} | 토큰 in {r['input_tokens']}+캐시 {r['cache_read']} / out {r['output_tokens']}"
              f" | ${r['cost']:.4f} | {r['duration_ms']}ms")
    top, top_n = Counter(labels).most_common(1)[0]
    json_ok = sum(extract_json(t) is not None for t in texts)
    print(f" → 서로 다른 라벨 {len(set(labels))}개 (최빈 '{top}' {top_n}/{n}) | 서로 다른 답변 {len(set(texts))}개"
          f" | JSON 형식 {json_ok}/{n} | 평균 비용 ${sum(costs)/n:.4f} | 평균 토큰 {sum(tokens)//n}")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, choices=["pangyo", "pohang"])
    ap.add_argument("-n", type=int, default=config.DEFAULT_N, help="반복 횟수")
    args = ap.parse_args()

    case = next(c for c in load_cases(args.track) if c["id"] == SAMPLE_ID[args.track])
    prompt = ASK[args.track].format(x=case["input"])
    print(f"[{args.track}] 입력 {case['id']}:\n{case['input'][:300]}")
    await trial("(a) 하네스 없음", args.track, prompt, bare_options, args.n)
    await trial("(b) 하네스 있음", args.track, prompt, lambda: harness_options(args.track), args.n)


if __name__ == "__main__":
    asyncio.run(main())
