"""합성 테스트 데이터 만들기: 시드 예시 + 까다로운 유형을 주고 모델이 새 케이스를 쓰게 한다.

실행:  python lab7_eval_regression/make_synthetic.py --track pangyo -n 3
       python lab7_eval_regression/make_synthetic.py --dry-run
출력:  synthetic_<track>.jsonl — 모든 줄에 "synthetic": true, "reviewed": false
주의:  모델이 만든 정답(gold)은 틀릴 수 있다. 사람이 검토한 뒤 reviewed 를 true 로 바꾸고 나서 평가에 쓴다.
고칠 곳: EDGE_TYPES, SEEDS_PER_PROMPT
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import config, headless, workspace
from common.data import load_cases

HERE = Path(__file__).parent

# TODO(실습): 우리 업무에서 실제로 겪는 까다로운 유형을 추가하세요.
EDGE_TYPES = {
    "pangyo": ["두 분야가 섞인 문의", "프롬프트 주입(이전 지시 무시 요청)", "업무 범위 밖 문의",
               "정보가 부족한 문의", "욕설·감정이 섞인 문의", "오타·줄임말이 많은 문의"],
    "pohang": ["본문과 표의 수량이 다른 사양서", "수량이 빠진 사양서", "단위가 섞인 사양서(EA·SET·박스)",
               "도면 번호·날짜 같은 숫자가 많은 사양서", "영문·국문이 섞인 사양서", "단가표에 없는 품목이 섞인 사양서"],
}
SEEDS_PER_PROMPT = 3  # 예시로 보여줄 기존 케이스 수

FORMAT_HINT = {
    "pangyo": '{"text": "...", "gold_intent": "IT|구매|인사|보안|기타", "must_include": ["조항ID", "핵심 사실"], '
              '"must_not": ["하면 안 되는 말"], "needs_human": false}',
    "pohang": '{"text": "사양서 원문 전체", "items": [{"품목": "", "규격": "", "재질": "", "수량": 0, "단위": "", "비고": ""}], '
              '"needs_human": false}',
}


def build_prompt(track, edge, seeds, n):
    examples = "\n".join(json.dumps({**{k: v for k, v in s["gold"].items() if k != "id"}, "text": s["input"]},
                                    ensure_ascii=False) for s in seeds)
    return (f"가상 회사 「한빛스틸」의 Agent 평가용 테스트 케이스를 {n}개 만들어라.\n"
            f"유형: {edge}\n실제 회사·인물 이름은 쓰지 않는다. 기존 예시와 문장을 겹치지 않게 한다.\n\n"
            f"기존 예시:\n{examples}\n\n"
            f"한 줄에 JSON 하나씩, 이 형식으로만 출력:\n{FORMAT_HINT[track]}")


def generate(prompt, engine, dry_run, track):
    if engine == "sdk":  # [API 키 필요]
        import asyncio
        from claude_agent_sdk import ClaudeAgentOptions
        from sdk_optional.sdk_run import run_once
        opts = ClaudeAgentOptions(model=config.MODEL, allowed_tools=[], permission_mode="dontAsk",
                                  setting_sources=[], max_turns=1)
        r = asyncio.run(run_once(prompt, opts))
        r["total_tokens"] = r["input_tokens"] + r["output_tokens"] + r["cache_read"]
        return r
    return headless.run(prompt, cwd=workspace.build("lab7-synth"), model=config.HEADLESS_MODEL, tools="",
                        setting_sources="", dry_run=dry_run, fixture=f"lab7_synthetic_{track}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, choices=["pangyo", "pohang"])
    ap.add_argument("-n", type=int, default=3, help="유형마다 만들 개수")
    ap.add_argument("--engine", default="headless", choices=["headless", "sdk"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    headless.banner(args.dry_run)

    seeds = load_cases(args.track)[:SEEDS_PER_PROMPT]
    out_path = HERE / f"synthetic_{args.track}.jsonl"
    count, tokens = 0, 0
    with open(out_path, "w", encoding="utf-8") as f:
        for edge in EDGE_TYPES[args.track]:
            r = generate(build_prompt(args.track, edge, seeds, args.n), args.engine, args.dry_run, args.track)
            tokens += r["total_tokens"]
            for line in r["text"].splitlines():
                try:
                    case = json.loads(line.strip().rstrip(","))
                except json.JSONDecodeError:
                    continue  # 설명 문장·코드 블록 표시는 건너뜀
                count += 1
                case.update(id=f"SYN-{count:03d}", edge=edge, synthetic=True, reviewed=False)
                f.write(json.dumps(case, ensure_ascii=False) + "\n")
            print(f"[{edge}] 누적 {count}건")
    print(f"\n저장: {out_path} ({count}건, 토큰 {tokens:,}) — 사람 검토 전에는 평가에 쓰지 마세요.")


if __name__ == "__main__":
    main()
