"""LLM-as-judge: Agent 출력을 judge_prompt.md 기준으로 1–5점 채점한다.

실행:  python lab7_eval_regression/judge.py --track pangyo -n 10
       python lab7_eval_regression/judge.py --dry-run
       python lab7_eval_regression/judge.py --engine sdk          (API 키 필요)
입력:  sample_outputs_<track>.jsonl (또는 --input 으로 다른 jsonl: {id, input, output})
출력:  judge_scores.csv  →  agreement.py --judge lab7_eval_regression/judge_scores.csv 로 사람 채점과 비교
고칠 곳: judge_prompt.md

헤드리스 judge 는 --system-prompt 로 Claude Code 기본 시스템 프롬프트를 통째로 바꾸고 도구를 끈다 → 싸고 깨끗하다.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import config, headless, workspace
from common.data import DATA, load_kb, read_jsonl
from common.parse import extract_json

HERE = Path(__file__).parent
SYSTEM = "너는 엄격한 채점자다. JSON 하나만 출력한다."


def evidence_for(track):
    """judge 에게 줄 근거 자료 — 판교는 지식베이스 전체, 포항은 단가표."""
    if track == "pangyo":
        return "\n".join(f"[{cid}] {body}" for cid, body in load_kb().items())
    return (DATA / "pohang" / "price_table.csv").read_text(encoding="utf-8")


def build_prompt(track, input_text, output):
    rubric = re.sub(r"<!--.*?-->", "", (HERE / "judge_prompt.md").read_text(encoding="utf-8"), flags=re.S)
    out_text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    return rubric.replace("{INPUT}", input_text).replace("{EVIDENCE}", evidence_for(track)).replace("{OUTPUT}", out_text)


def judge_one(track, input_text, output, engine="headless", dry_run=False, case_id=None):
    """출력 하나 채점 → {score, reason, cost, tokens}. 점수를 못 읽으면 score=None."""
    prompt = build_prompt(track, input_text, output)
    if engine == "sdk":
        import asyncio
        from claude_agent_sdk import ClaudeAgentOptions
        from sdk_optional.sdk_run import run_once
        opts = ClaudeAgentOptions(model=config.JUDGE_MODEL, system_prompt=SYSTEM, allowed_tools=[],
                                  permission_mode="dontAsk", setting_sources=[], max_turns=1)
        r = asyncio.run(run_once(prompt, opts))
        r["total_tokens"] = r["input_tokens"] + r["output_tokens"] + r["cache_read"]
    else:
        r = headless.run(prompt, cwd=workspace.build("lab7-judge"), model=config.HEADLESS_CHEAP_MODEL,
                         system_prompt=SYSTEM, tools="", setting_sources="", dry_run=dry_run,
                         fixture=f"lab7_judge.json#{case_id}")
    data = extract_json(r["text"]) or {}
    score = data.get("score")
    return {"score": int(score) if str(score).isdigit() else None, "reason": data.get("reason", r["text"][:100]),
            "cost": r["cost"], "tokens": r["total_tokens"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, choices=["pangyo", "pohang"])
    ap.add_argument("-n", type=int, default=10, help="채점할 건수")
    ap.add_argument("--input", help="채점할 jsonl (기본: sample_outputs_<track>.jsonl)")
    ap.add_argument("--out", default=str(HERE / "judge_scores.csv"))
    ap.add_argument("--engine", default="headless", choices=["headless", "sdk"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    headless.banner(args.dry_run)

    rows = read_jsonl(args.input or HERE / f"sample_outputs_{args.track}.jsonl")[: args.n]
    results, tokens = [], 0
    for row in rows:
        j = judge_one(args.track, row["input"], row["output"], args.engine, args.dry_run, row["id"])
        tokens += j["tokens"]
        results.append({"id": row["id"], "judge_score": j["score"], "reason": j["reason"]})
        print(f"{row['id']}: {j['score']}점 — {j['reason']}")

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "judge_score", "reason"])
        w.writeheader(); w.writerows(results)
    print(f"\n저장: {args.out} | judge 토큰 합계 {tokens:,}")


if __name__ == "__main__":
    main()
