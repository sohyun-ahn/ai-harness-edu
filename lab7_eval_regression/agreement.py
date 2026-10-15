"""judge 점수와 사람 점수가 얼마나 맞는지: 일치율과 Cohen's kappa (API 호출 없음).

실행:  python lab7_eval_regression/agreement.py
       python lab7_eval_regression/agreement.py --judge lab7_eval_regression/judge_scores.csv   (judge.py 실행 후)
읽는 법: kappa 0.6 이상이면 '상당한 일치', 0.4 미만이면 judge_prompt.md 를 고친다.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
PASS = 4  # TODO(실습): 합격 기준 점수. 몇 점 이상을 '쓸 만한 답' 으로 볼까?


def read_scores(path, column):
    with open(path, encoding="utf-8") as f:
        return {r["id"]: int(r[column]) for r in csv.DictReader(f) if r[column].strip()}


def cohen_kappa(a, b):
    """두 채점자의 일치도에서 '우연히 맞을 확률' 을 뺀 값. 1 = 완전 일치, 0 = 우연 수준."""
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default="pangyo", help="(사람 채점 예시는 판교만 있음)")
    ap.add_argument("-n", type=int, default=0, help="앞에서 n건만 (0 = 전부)")
    ap.add_argument("--human", default=str(HERE / "human_labels.csv"))
    ap.add_argument("--judge", default=str(HERE / "judge_scores_sample.csv"))
    args = ap.parse_args()

    human = read_scores(args.human, "human_score")
    judge = read_scores(args.judge, "judge_score")
    ids = [i for i in human if i in judge][: args.n or None]
    h, j = [human[i] for i in ids], [judge[i] for i in ids]
    n = len(ids)
    if n == 0:
        raise SystemExit("겹치는 id 가 없습니다. 두 CSV 의 id 를 확인하세요.")

    hp, jp = [x >= PASS for x in h], [x >= PASS for x in j]
    print(f"비교 건수: {n}")
    print(f"정확히 같은 점수   : {sum(x == y for x, y in zip(h, j)) / n:.0%}")
    print(f"±1점 안            : {sum(abs(x - y) <= 1 for x, y in zip(h, j)) / n:.0%}")
    print(f"Cohen's kappa(1–5) : {cohen_kappa(h, j):.2f}")
    print(f"합격/불합격 일치   : {sum(x == y for x, y in zip(hp, jp)) / n:.0%}  (기준 {PASS}점 이상)")
    print(f"kappa(합격/불합격) : {cohen_kappa(hp, jp):.2f}")
    print(f"judge 치우침       : 평균 {sum(j) / n - sum(h) / n:+.2f}점 (양수면 judge 가 후함)")

    print("\n점수가 다른 건 (사람 → judge):")
    for i, x, y in zip(ids, h, j):
        if x != y:
            print(f"  {i}: {x} → {y}{'   ← 합격 판정이 갈림' if (x >= PASS) != (y >= PASS) else ''}")


if __name__ == "__main__":
    main()
