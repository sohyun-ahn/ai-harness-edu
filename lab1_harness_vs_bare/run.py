"""Lab 1 — 같은 입력을 N번: 하네스 미적용 Claude Code vs 하네스(CLAUDE.md + 출력 형식 + 근거 자료)를 붙인 Claude Code.

실행:  python lab1_harness_vs_bare/run.py --track pangyo -n 5
       python lab1_harness_vs_bare/run.py --track pohang -n 3 --dry-run    (호출 없이 흐름만)
고칠 곳: harness/CLAUDE.md, 아래 SAMPLE_ID
보는 것: 서로 다른 답 수, JSON 형식 지킨 비율, 평균 토큰·턴
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # labs/

from common import config, headless, workspace
from common.data import load_cases
from common.parse import extract_json

HERE = Path(__file__).resolve().parent

# TODO(실습): 다른 문의·사양서 ID 로 바꿔 보세요 (data/README.md 참고)
SAMPLE_ID = {"pangyo": "Q25", "pohang": "S06"}

ASK = {
    "pangyo": "[pangyo] 다음 사내 문의를 IT/구매/인사/보안/기타 중 하나로 분류하고 답변해 주세요.\n\n문의: {x}",
    "pohang": "[pohang] 다음 사양서에서 품목·규격·재질·수량·단위·비고를 뽑고 견적을 내 주세요.\n\n{x}",
}


def variants(track):
    """(a) 하네스 미적용: 빈 폴더 · 설정 안 읽음 · 도구 없음   (b) 하네스: CLAUDE.md + data/ · 읽기 도구만."""
    bare = workspace.build("lab1-bare")
    harness = workspace.build("lab1-harness", copy={"CLAUDE.md": HERE / "harness" / "CLAUDE.md"}, track=track)
    return [
        ("(a) 하네스 미적용", "bare", dict(cwd=bare, setting_sources="", tools="")),
        ("(b) 하네스", "harness", dict(cwd=harness, setting_sources="project", tools="Read,Grep,Glob",
                                      allowed_tools="Read,Grep,Glob")),
    ]


def label_of(track, text):
    """일관성 비교용 라벨 — 판교는 분류, 포항은 (품목:수량) 목록."""
    data = extract_json(text)
    if track == "pangyo":
        if data and data.get("intent"):
            return data["intent"]
        m = re.search(r"(IT|구매|인사|보안|기타)", text)
        return f"{m.group(1)}(본문에서 추정)" if m else "분류 없음"
    if data and data.get("items"):
        return ", ".join(f"{i.get('품목')}:{i.get('수량')}" for i in data["items"])
    return "형식 없음(JSON 아님)"


def trial(name, key, track, prompt, opts, n, args):
    print(f"\n=== {name} ({n}회) · 작업 폴더 {opts['cwd']} ===")
    labels, texts, tokens, turns = [], [], [], []
    for i in range(n):
        r = headless.run(prompt, model=config.HEADLESS_MODEL, dry_run=args.dry_run,
                         fixture=f"lab1_{key}_{track}", **opts)
        if args.show_cmd and i == 0:
            print("  $", r["cmd_str"])
        label = label_of(track, r["text"])
        labels.append(label); texts.append(r["text"].strip()); tokens.append(r["total_tokens"]); turns.append(r["turns"])
        err = " | 오류: " + r["text"][:80] if r["is_error"] else ""
        print(f" {i+1}. 라벨={label} | {headless.tok_line(r)} | 턴 {r['turns']} | {r['duration_ms']}ms{err}")
    top, top_n = Counter(labels).most_common(1)[0]
    json_ok = sum(extract_json(t) is not None for t in texts)
    print(f" → 서로 다른 라벨 {len(set(labels))}개 (최빈 '{top}' {top_n}/{n}) | 서로 다른 답 {len(set(texts))}개"
          f" | JSON 형식 {json_ok}/{n} | 평균 토큰 {sum(tokens)//n:,} | 평균 턴 {sum(turns)/n:.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, choices=["pangyo", "pohang"])
    ap.add_argument("-n", type=int, default=config.DEFAULT_N, help="반복 횟수")
    ap.add_argument("--dry-run", action="store_true", help="호출 없이 저장된 출력(common/fixtures)으로")
    ap.add_argument("--show-cmd", action="store_true", help="실제 claude 명령을 보여준다")
    args = ap.parse_args()
    headless.banner(args.dry_run)

    case = next(c for c in load_cases(args.track) if c["id"] == SAMPLE_ID[args.track])
    prompt = ASK[args.track].format(x=case["input"])
    print(f"[{args.track}] 입력 {case['id']}:\n{case['input'][:300]}")
    for name, key, opts in variants(args.track):
        trial(name, key, args.track, prompt, opts, args.n, args)


if __name__ == "__main__":
    main()
