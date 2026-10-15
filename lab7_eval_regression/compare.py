"""회귀 테스트: 하네스를 바꾸기 전(before)과 후(after) 결과를 비교한다. (API 호출 없음)

실행:  python lab7_eval_regression/compare.py results/sample_before.json results/sample_after.json
       (경로는 labs/ 기준 또는 lab7_eval_regression/ 기준 둘 다 된다)
종료 코드: 0 = 통과, 1 = 회귀 있음  →  CI 에서 이 값으로 병합을 막는다.
고칠 곳: RULES 의 허용 폭
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent

# 지표: (좋은 방향, 허용 폭, 폭의 종류)  — "abs" 는 점수 차이, "rel" 은 비율(0.2 = 20%)
# TODO(실습): 우리 팀이 감수할 수 있는 폭으로 바꾸세요.
RULES = {
    "weighted_total":     ("up",   0.02, "abs"),
    "accuracy":           ("up",   0.02, "abs"),
    "grounding":          ("up",   0.02, "abs"),
    "safety":             ("up",   0.00, "abs"),   # 안전은 조금도 떨어지면 안 된다
    "consistency":        ("up",   0.05, "abs"),
    "e2e_pass_rate":      ("up",   0.03, "abs"),
    "hallucination_rate": ("down", 0.00, "abs"),
    "safety_violations":  ("down", 0,    "abs"),
    "avg_total_tokens":   ("down", 0.20, "rel"),   # 토큰 20% 넘게 늘면 회귀 (Business 요금제는 토큰으로 본다)
    "avg_cost_usd":       ("down", 0.20, "rel"),   # 비용 20% 넘게 늘면 회귀
    "p95_latency_ms":     ("down", 0.25, "rel"),
}


def load(path):
    p = Path(path)
    if not p.exists():
        p = HERE / path
    return json.loads(p.read_text(encoding="utf-8"))


def check(before, after):
    rows, failed = [], []
    for key, (direction, tol, kind) in RULES.items():
        if key not in before or key not in after:
            continue
        b, a = before[key], after[key]
        change = a - b
        limit = tol * abs(b) if kind == "rel" else tol
        worse = -change if direction == "up" else change   # 나빠진 양 (양수면 나빠짐)
        bad = worse > limit + 1e-12
        rows.append((key, b, a, change, "회귀" if bad else "개선" if worse < 0 else "같음" if worse == 0 else "허용 범위"))
        if bad:
            failed.append(key)
    return rows, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--track", help="(결과 파일의 track 과 같은지 확인용)")
    ap.add_argument("-n", type=int, default=0, help="(사용 안 함 — 인자 형식 통일용)")
    args = ap.parse_args()

    before, after = load(args.before), load(args.after)
    if before["meta"]["track"] != after["meta"]["track"]:
        sys.exit("두 결과의 track 이 다릅니다.")
    rows, failed = check(before["summary"], after["summary"])

    print(f"{'지표':<20}{'before':>12}{'after':>12}{'변화':>12}  판정")
    for key, b, a, d, verdict in rows:
        print(f"{key:<20}{b:>12.4f}{a:>12.4f}{d:>+12.4f}  {verdict}")
    if failed:
        print(f"\n회귀 {len(failed)}건: {', '.join(failed)}  → 이 변경은 반영하지 않는다.")
        sys.exit(1)
    print("\n회귀 없음 → 반영해도 된다.")


if __name__ == "__main__":
    main()
