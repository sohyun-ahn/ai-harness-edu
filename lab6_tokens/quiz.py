"""Lab 6 — quiz.md 의 정답을 가장 최근 results/tokens_*.json 으로 계산한다. (호출 없음)

실행:  python lab6_tokens/quiz.py
       python lab6_tokens/quiz.py --file lab6_tokens/results/tokens_<시각>.json
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def pick(rows, lever, task=None):
    return [r for r in rows if r["lever"] == lever and (task is None or r["task"].startswith(task))]


def pct(new, old):
    return f"{(new - old) / old:+.0%}" if old else "-"


def answers(rows):
    a = {}
    b1 = pick(rows, "baseline", "t1")
    if b1:
        r = b1[0]
        a[1] = f"{r['total']:,} 토큰"
        a[2] = f"{r['out']:,} 토큰"
        a[3] = f"{r['cr'] / r['total']:.0%}" if r["total"] else "-"
    base, brief = pick(rows, "baseline"), pick(rows, "brief")
    tasks = {r["task"] for r in brief} & {r["task"] for r in base}
    if tasks:
        bo = sum(r["out"] for r in base if r["task"] in tasks)
        so = sum(r["out"] for r in brief if r["task"] in tasks)
        a[4] = f"{bo:,} → {so:,} ({pct(so, bo)})"
    h, o = pick(rows, "haiku", "t1"), pick(rows, "opus", "t1")
    if h and o:
        hc, oc = h[0].get("cost", 0), o[0].get("cost", 0)
        a[5] = (f"토큰 haiku {h[0]['total']:,} · opus {o[0]['total']:,} — 비용 참고값 ${hc:.4f} vs ${oc:.4f}"
                + (f" ({oc / hc:.1f}배)" if hc else ""))
    c = [r for r in rows if r["lever"].startswith("cache#")]
    if c:
        a[6] = f"1회차 캐시쓰기 {c[0]['cw']:,} · 캐시읽기 {c[0]['cr']:,} → {len(c)}회차 캐시읽기 {c[-1]['cr']:,}"
    s = pick(rows, "subagent")
    if s:
        a[7] = f"메인 {s[0]['total']:,} · 전체 {s[0]['all']:,} (서브에이전트 {s[0]['all'] - s[0]['total']:,})"
    b5, k5 = pick(rows, "baseline", "t5"), pick(rows, "rtk", "t5")
    if b5 and k5:
        bi, ki = b5[0]["in"] + b5[0]["cr"] + b5[0]["cw"], k5[0]["in"] + k5[0]["cr"] + k5[0]["cw"]
        a[8] = f"{bi:,} → {ki:,} ({pct(ki, bi)})"
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="결과 파일 (기본: 가장 최근)")
    args = ap.parse_args()
    files = sorted((HERE / "results").glob("tokens_*.json"))
    path = Path(args.file) if args.file else (files[-1] if files else None)
    if not path:
        raise SystemExit("결과가 없습니다. 먼저 python lab6_tokens/bench.py 를 돌리세요.")
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"결과 파일: {path}{' (dry-run 저장 출력)' if data['meta'].get('dry_run') else ''}\n")
    a = answers(data["rows"])
    for i in range(1, 9):
        print(f"{i}. {a.get(i, '이번 실행에 없음 — quiz.md 의 「필요한 실행」 참고')}")


if __name__ == "__main__":
    main()
