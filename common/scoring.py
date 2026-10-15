"""채점 함수 (lab7 run_suite 가 씀) — 한 번의 실행 결과를 정답과 비교해 지표별 점수를 낸다. (API 호출 없음)

지표 이름과 가중치는 lab7_eval_regression/metrics.md 와 맞춘다.
"""
from collections import Counter

from common.checks import expected_total, numbers_not_in_source, quote_errors, unknown_clauses
from common.data import norm

# TODO(실습): metrics.md 에서 정한 가중치로 바꾸세요 (합계 100).
WEIGHTS = {"accuracy": 30, "grounding": 25, "safety": 20, "consistency": 10, "latency": 5, "cost": 10}
TARGETS = {"latency_ms": 60_000, "cost_usd": 0.05}

FIELDS = ["품목", "규격", "재질", "수량", "단위"]  # 비고는 자유 문장이라 뺀다


def score_pangyo(output, gold):
    out = output or {}
    reply = str(out.get("reply", ""))
    evidence = reply + " " + " ".join(map(str, out.get("citations") or []))
    intent_ok = out.get("intent") == gold["gold_intent"]
    facts = gold["must_include"]
    coverage = sum(f in evidence for f in facts) / len(facts) if facts else 1.0
    violations = [p for p in gold["must_not"] if p in reply]
    human_ok = bool(out.get("needs_human")) == gold["needs_human"]
    fake = unknown_clauses(out) if output else []
    return {
        "label": out.get("intent"),
        "accuracy": float(intent_ok),
        "grounding": 0.0 if fake else coverage,
        "safety": float(not violations and human_ok),
        "hallucination": bool(fake),
        "notes": violations + [f"없는 조항 {c}" for c in fake] + ([] if human_ok else ["needs_human 불일치"]),
        "stage": {"분류": float(intent_ok), "답변_사실포함": coverage},
        "e2e": intent_ok and not violations and not fake and human_ok,
    }


def _same(field, p, g):
    if field == "품목":
        return bool(p) and (norm(g) in norm(p) or norm(p) in norm(g))
    if field == "수량":
        return p == g
    return norm(p) == norm(g)


def field_f1(pred_items, gold_items):
    """규격이 같은 항목끼리 짝지은 뒤 필드 단위로 맞은 개수를 센다."""
    tp, used = 0, set()
    for g in gold_items:
        for i, p in enumerate(pred_items):
            if i not in used and norm(p.get("규격")) == norm(g["규격"]) and _same("품목", p.get("품목"), g["품목"]):
                used.add(i)
                tp += sum(_same(f, p.get(f), g.get(f)) for f in FIELDS)
                break
    pred_n, gold_n = len(pred_items) * len(FIELDS), len(gold_items) * len(FIELDS)
    if pred_n == 0 or gold_n == 0:
        return 1.0 if pred_n == gold_n else 0.0
    prec, rec = tp / pred_n, tp / gold_n
    return 0.0 if tp == 0 else 2 * prec * rec / (prec + rec)


def score_pohang(output, gold, source):
    out = output or {}
    items = out.get("items") or []
    f1 = field_f1(items, gold["items"])
    fake = numbers_not_in_source(items, source)
    q_err = quote_errors(out.get("quote"))
    total_ok = ((out.get("quote") or {}).get("total") or 0) == expected_total(gold["items"])
    human_ok = bool(out.get("needs_human")) == gold["needs_human"]
    return {
        "label": "; ".join(sorted(f"{i.get('품목')}:{i.get('수량')}" for i in items)) or None,
        "accuracy": f1,
        "grounding": float(not fake),
        "safety": float(human_ok),
        "hallucination": bool(fake),
        "notes": [f"원문에 없는 숫자 {fake}"] * bool(fake) + q_err + ([] if human_ok else ["needs_human 불일치"]),
        "stage": {"추출_F1": f1, "견적_정확": float(total_ok and not q_err)},
        "e2e": f1 >= 0.9 and not fake and not q_err and total_ok and human_ok,
    }


def consistency(labels):
    """K번 실행한 라벨 중 가장 많이 나온 라벨의 비율."""
    return Counter(labels).most_common(1)[0][1] / len(labels) if labels else 0.0


def weighted_total(s):
    parts = {
        "accuracy": s["accuracy"], "grounding": s["grounding"], "safety": s["safety"],
        "consistency": s["consistency"],
        "latency": min(1.0, TARGETS["latency_ms"] / max(s["p95_latency_ms"], 1)),
        "cost": min(1.0, TARGETS["cost_usd"] / max(s["avg_cost_usd"], 1e-9)),
    }
    return sum(parts[k] * w for k, w in WEIGHTS.items()) / sum(WEIGHTS.values())
