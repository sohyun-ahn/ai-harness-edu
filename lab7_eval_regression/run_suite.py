"""평가 스위트: 데이터셋 전체를 K번씩 돌려 채점하고 결과 파일과 보고서를 남긴다.

실행:  python lab7_eval_regression/run_suite.py --track pangyo -n 10 --k 3
       python lab7_eval_regression/run_suite.py --track pohang --agent multi --k 2
       python lab7_eval_regression/run_suite.py --track pangyo -n 5 --k 2 --dry-run
       python lab7_eval_regression/run_suite.py --engine sdk ...         (API 키 필요, sdk_optional 의 Agent)
출력:  results/<시각>_<track>.json  +  같은 이름의 .md 보고서  →  compare.py 로 전후 비교
평가 대상: --agent single = lab1 하네스(CLAUDE.md), multi = lab5 멀티에이전트 → 그 파일들을 고치고 다시 돌린다.
할당량: 건수 × K 번 호출 (multi 는 한 번에 서브에이전트 여러 번). 처음에는 -n 5 --k 2 로.
"""
import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import config, headless
from common.data import load_cases
from common.scoring import WEIGHTS, consistency, score_pangyo, score_pohang, weighted_total
from lab7_eval_regression.agent import solve
from lab7_eval_regression.judge import judge_one

HERE = Path(__file__).parent


def run_case(case, track, args):
    t0 = time.time()
    try:
        r = solve(case, track, args.agent, args.engine, args.dry_run)
    except Exception as e:                      # 한 건이 실패해도 스위트는 계속
        r = {"output": None, "cost": 0.0, "error": str(e)}
    if not r.get("duration_ms"):
        r["duration_ms"] = int((time.time() - t0) * 1000)
    s = score_pangyo(r["output"], case["gold"]) if track == "pangyo" else \
        score_pohang(r["output"], case["gold"], case["input"])
    if args.judge and r["output"]:              # 답변 문장 품질은 LLM judge 로 (1–5)
        j = judge_one(track, case["input"], r["output"], args.engine, args.dry_run, case["id"])
        s.update(judge=j["score"], judge_cost=j["cost"])
    return {**s, "output": r["output"], "cost": r.get("cost", 0.0), "duration_ms": r["duration_ms"],
            "input_tokens": r.get("input_tokens", 0), "output_tokens": r.get("output_tokens", 0),
            "cache_read": r.get("cache_read", 0), "cache_write": r.get("cache_write", 0),
            "total_tokens": r.get("total_tokens", 0), "all_tokens": r.get("all_tokens", 0),
            "error": r.get("error") or (r.get("text", "")[:200] if r.get("is_error") else None)}


def summarize(items):
    runs = [run for it in items for run in it["runs"]]
    mean = lambda key: statistics.mean(r[key] for r in runs)  # noqa: E731
    lat = sorted(r["duration_ms"] for r in runs)
    stages = {k: statistics.mean(r["stage"][k] for r in runs) for k in runs[0]["stage"]}
    s = {
        "accuracy": mean("accuracy"), "grounding": mean("grounding"), "safety": mean("safety"),
        "consistency": statistics.mean(it["consistency"] for it in items),
        "hallucination_rate": statistics.mean(float(r["hallucination"]) for r in runs),
        "safety_violations": sum(r["safety"] < 1 for r in runs),
        "e2e_pass_rate": statistics.mean(float(r["e2e"]) for r in runs),
        "avg_latency_ms": mean("duration_ms"), "p95_latency_ms": lat[int(0.95 * (len(lat) - 1))],
        "avg_cost_usd": mean("cost"), "total_cost_usd": sum(r["cost"] for r in runs),
        "avg_input_tokens": mean("input_tokens"), "avg_output_tokens": mean("output_tokens"),
        "avg_cache_read": mean("cache_read"), "avg_cache_write": mean("cache_write"),
        "avg_total_tokens": mean("total_tokens"), "avg_all_tokens": mean("all_tokens"),
        "errors": sum(bool(r["error"]) for r in runs),
        "stage": stages,
    }
    judged = [r["judge"] for r in runs if r.get("judge")]
    if judged:
        s["judge_avg"] = statistics.mean(judged)
        s["judge_cost_usd"] = sum(r.get("judge_cost", 0) for r in runs)
    s["weighted_total"] = weighted_total(s)
    return s


def write_report(path, meta, s, items):
    lines = [f"# 평가 결과 — {meta['track']} / {meta['agent']}", "",
             f"- 실행: {meta['started']} · 건수 {meta['n_cases']} × K={meta['k']} · 엔진 {meta['engine']} · 모델 {meta['model']}", "",
             "| 지표 | 값 |", "|---|---|"]
    for key in ["weighted_total", "accuracy", "grounding", "safety", "consistency", "hallucination_rate",
                "safety_violations", "e2e_pass_rate", "avg_latency_ms", "p95_latency_ms",
                "avg_total_tokens", "avg_all_tokens", "avg_input_tokens", "avg_output_tokens", "avg_cache_read",
                "avg_cost_usd", "total_cost_usd", "errors",
                "judge_avg"]:
        if key not in s:
            continue
        v = s[key]
        lines.append(f"| {key} | {v:.3f} |" if isinstance(v, float) else f"| {key} | {v} |")
    lines += ["", "## 단계별", ""] + [f"- {k}: {v:.3f}" for k, v in s["stage"].items()]
    lines += ["", "## 실패한 건", ""]
    for it in items:
        bad = [r for r in it["runs"] if not r["e2e"]]
        if bad:
            notes = sorted({n for r in bad for n in r["notes"]}) or ["(정답과 다름)"]
            lines.append(f"- **{it['id']}** {len(bad)}/{len(it['runs'])}회 실패 · 일관성 {it['consistency']:.2f} · "
                         + ", ".join(notes))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=config.TRACK, choices=["pangyo", "pohang"])
    ap.add_argument("-n", type=int, default=0, help="앞에서 n건만 (0 = 전부)")
    ap.add_argument("--k", type=int, default=3, help="같은 입력 반복 횟수 (일관성 측정)")
    ap.add_argument("--agent", default="single", choices=["single", "multi"])
    ap.add_argument("--engine", default="headless", choices=["headless", "sdk"])
    ap.add_argument("--judge", action="store_true", help="LLM judge 채점도 한다 (호출 추가)")
    ap.add_argument("--dry-run", action="store_true", help="저장된 출력(common/fixtures/lab7_*)으로")
    ap.add_argument("--out", help="결과 파일 경로 (기본: results/<시각>_<track>.json)")
    args = ap.parse_args()
    headless.banner(args.dry_run)

    cases = load_cases(args.track)[: args.n or None]
    meta = {"track": args.track, "agent": args.agent, "engine": args.engine, "k": args.k, "n_cases": len(cases),
            "model": config.HEADLESS_MODEL if args.engine == "headless" else config.MODEL,
            "judge_model": config.HEADLESS_CHEAP_MODEL if args.engine == "headless" else config.JUDGE_MODEL,
            "weights": WEIGHTS, "dry_run": args.dry_run, "started": datetime.now().isoformat(timespec="seconds")}
    items = []
    for case in cases:
        runs = [run_case(case, args.track, args) for _ in range(args.k)]
        c = consistency([r["label"] for r in runs])
        items.append({"id": case["id"], "consistency": c, "runs": runs})
        print(f"{case['id']}: e2e {sum(r['e2e'] for r in runs)}/{args.k} · 일관성 {c:.2f} · "
              f"토큰 {sum(r['total_tokens'] for r in runs):,}")

    s = summarize(items)
    out = Path(args.out) if args.out else HERE / "results" / f"{datetime.now():%Y%m%d_%H%M%S}_{args.track}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "summary": s, "items": items}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    write_report(out.with_suffix(".md"), meta, s, items)
    print(f"\n종합 {s['weighted_total']:.3f} · 정확도 {s['accuracy']:.3f} · 환각 {s['hallucination_rate']:.2%}"
          f" · 안전 위반 {s['safety_violations']} · 평균 토큰 {s['avg_total_tokens']:,.0f}\n저장: {out}")


if __name__ == "__main__":
    main()
