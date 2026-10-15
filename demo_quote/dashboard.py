#!/usr/bin/env python3
"""runs/*/result.json · events.jsonl → runs/dashboard.html

조건별 평균(정확도 · 토큰 · 시간 · 턴 · Sub Agent · 차단)과 실행마다 타임라인(메인 · Sub Agent 레인)을 한 장에.
사용: python3 dashboard.py [--only 0414-1530]   (이름에 포함된 실행만)
"""
import argparse
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
N, G, O, L = "#1F3A5F", "#9AA5B1", "#F28C28", "#EEF1F5"
LABEL = {"bare": "하네스 없음", "harness": "내 하네스", "superpowers": "Superpowers",
         "repo:bare": "저장소 · 하네스 미적용", "repo:harness": "저장소 · 내 하네스", "repo:superpowers": "저장소 · Superpowers",
         "ext:bare": "저장소 밖 · 하네스 미적용", "ext:harness": "저장소 밖 · 내 하네스", "ext:superpowers": "저장소 밖 · Superpowers"}
ORDER = [f"{v}:{c}" for v in ("repo", "ext") for c in ("bare", "harness", "superpowers")]
CLS = lambda k: k.split(":")[-1]


def total_tokens(r):
    mu = r.get("model_usage") or {}
    if mu:
        return sum((v.get("inputTokens") or 0) + (v.get("outputTokens") or 0) + (v.get("cacheReadInputTokens") or 0)
                   + (v.get("cacheCreationInputTokens") or 0) for v in mu.values())
    return r.get("input", 0) + r.get("output", 0) + r.get("cache_read", 0) + r.get("cache_write", 0)


def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0


def bars(title, unit, rows, fmt="{:,.0f}", better="high"):
    """rows: (조건, 평균[, 최소, 최대])"""
    rows = [(r[0], r[1], r[2] if len(r) > 2 else None, r[3] if len(r) > 3 else None) for r in rows]
    mx = max([(r[3] if r[3] is not None else r[1]) for r in rows] + [1e-9])
    out = f'<div class="card"><h3>{title} <small>{ {"high": "높을수록 좋음", "low": "낮을수록 좋음"}.get(better, "")}</small></h3>'
    for name, v, lo, hi in rows:
        w = 100 * v / mx
        rng = (f'<span class="rng" style="left:{100 * lo / mx:.1f}%;width:{max(.6, 100 * (hi - lo) / mx):.1f}%"></span>'
               if lo is not None and hi is not None and hi > lo else "")
        spread = f'<small> ({fmt.format(lo)}~{fmt.format(hi)})</small>' if rng else ""
        out += (f'<div class="bar"><span class="bl">{LABEL.get(name, name)}</span>'
                f'<span class="track"><span class="fill {CLS(name)}" style="width:{w:.1f}%"></span>{rng}</span>'
                f'<span class="bv">{fmt.format(v)}{unit}{spread}</span></div>')
    return out + "</div>"


def timeline(name):
    f = RUNS / name / "events.jsonl"
    if not f.exists():
        return ""
    ev = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    lanes, marks, t_end = {"메인": 0}, [], 1
    sub_of = {}
    for k, e in enumerate(ev):
        t = e.get("_ts", k)
        t_end = max(t_end, t)
        if e.get("type") == "assistant":
            lane = "메인" if not e.get("parent_tool_use_id") else sub_of.get(e["parent_tool_use_id"], "Sub Agent")
            for b in e.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    n = b.get("name")
                    if n in ("Task", "Agent"):
                        sub_of[b.get("id")] = "Sub · " + b.get("input", {}).get("subagent_type", "?")
                    lanes.setdefault(lane, len(lanes))
                    marks.append((t, lane, n, b.get("input", {})))
        txt = json.dumps(e, ensure_ascii=False)
        if "차단:" in txt or "테스트 실패 상태로는" in txt:
            marks.append((t, "메인", "HOOK", {}))
    for v in sub_of.values():
        lanes.setdefault(v, len(lanes))
    W, LH, X0 = 1000, 34, 150
    H = LH * len(lanes) + 30
    s = f'<svg viewBox="0 0 {W} {H}" class="tl">'
    for lane, i in lanes.items():
        y = 10 + i * LH
        s += f'<rect x="{X0}" y="{y}" width="{W - X0 - 10}" height="{LH - 6}" fill="{L if i % 2 == 0 else "#fff"}"/>'
        s += f'<text x="{X0 - 10}" y="{y + LH / 2}" text-anchor="end" class="ln">{html.escape(lane)}</text>'
    for t, lane, n, i in marks:
        x = X0 + (W - X0 - 20) * t / t_end
        y = 10 + lanes.get(lane, 0) * LH + (LH - 6) / 2
        col = O if n in ("Task", "Agent", "HOOK", "Skill") else (N if n in ("Edit", "Write", "MultiEdit") else G)
        r = 7 if col == O else 4.5
        tip = n + (" " + str(i.get("file_path") or i.get("command") or i.get("subagent_type") or i.get("skill") or "")[:80])
        s += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}"><title>{html.escape(tip)}</title></circle>'
    s += f'<text x="{X0}" y="{H - 4}" class="ax">0s</text><text x="{W - 10}" y="{H - 4}" text-anchor="end" class="ax">{t_end:.0f}s</text>'
    return s + "</svg>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    rs = []
    for p in sorted(RUNS.glob("*/result.json")):
        if a.only in p.parent.name:
            r = json.loads(p.read_text(encoding="utf-8"))
            r["name"] = p.parent.name
            rs.append(r)
    if not rs:
        raise SystemExit("runs/ 에 결과가 없다. 먼저 run_demo.py 를 돌린다.")
    key = lambda r: f'{r.get("variant", "repo")}:{r["cond"]}'
    conds = [c for c in ORDER if any(key(r) == c for r in rs)]
    by = {c: [r for r in rs if key(r) == c] for c in conds}

    def agg(f):
        out = []
        for c in conds:
            xs = [f(r) for r in by[c] if f(r) is not None]
            out.append((c, avg(xs), min(xs) if xs else 0, max(xs) if xs else 0))
        return out
    head = "".join(
        f'<div class="kpi {CLS(c)}"><b>{LABEL[c]}</b><span>{len(by[c])}회 · {", ".join(sorted({m.replace("claude-", "") for r in by[c] for m in r.get("models_used", [])}))}</span>'
        f'<em>{avg([r["hidden_pass"] for r in by[c]]):.1f}<small>/15</small></em><i>숨은 테스트 평균</i></div>' for c in conds)
    grid = (bars("숨은 테스트 통과", "/15", agg(lambda r: r["hidden_pass"]), "{:.1f}")
            + bars("회귀 테스트", "/5", agg(lambda r: r["regression_pass"]), "{:.1f}")
            + bars("전체 토큰 (캐시 포함)", "", agg(total_tokens), better="low")
            + bars("출력 토큰", "", agg(lambda r: r.get("output")), better="low")
            + bars("걸린 시간", "s", agg(lambda r: r["wall_s"]), better="low")
            + bars("턴 수", "", agg(lambda r: r.get("turns")), "{:.1f}", better="low")
            + bars("Sub Agent 호출", "회", agg(lambda r: len(r["sub_agents"])), "{:.1f}", better="")
            + bars("Hook 차단", "회", agg(lambda r: r["blocked"] + r["stop_blocked"]), "{:.1f}", better=""))
    rows = ""
    for r in rs:
        rows += ("<tr>" + "".join(f"<td>{x}</td>" for x in [
            r["name"], LABEL.get(key(r)), f'{r["hidden_pass"]}/15', f'{r["regression_pass"]}/5',
            "O" if r["regression_file_unchanged"] else "<b class=o>수정됨</b>",
            f"{total_tokens(r):,}", f'{r.get("output", 0):,}', r["wall_s"], r.get("turns"),
            ", ".join(r["sub_agents"]) or "-", ", ".join(r["skills"]) or "-", r["blocked"] + r["stop_blocked"],
            " · ".join(n for n, k in (("2025", "read_2025"), ("초안", "read_draft"), ("회의록", "read_minutes"), ("확정본", "read_reference")) if r.get(k)) or "-", r["rule_violations"]]) + "</tr>")
    tls = "".join(f'<div class="card"><h3>{r["name"]} · {LABEL.get(key(r))} · 숨은 테스트 {r["hidden_pass"]}/15</h3>{timeline(r["name"])}</div>'
                  for r in rs)
    page = f"""<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>하네스 비교 대시보드</title>
<style>
body{{font-family:Pretendard,-apple-system,"Apple SD Gothic Neo",sans-serif;background:#F7F8FA;color:{N};margin:0;padding:28px}}
h1{{margin:0 0 4px;font-size:26px}} .sub{{color:#6B7785;margin-bottom:20px}}
.kpis{{display:flex;gap:14px;margin-bottom:18px;flex-wrap:wrap}}
.kpi{{background:#fff;border-radius:12px;padding:16px 20px;min-width:200px;border-top:4px solid {G};display:grid;gap:2px}}
.kpi.harness{{border-color:{O}}} .kpi.superpowers{{border-color:{N}}}
.kpi span,.kpi i{{color:#6B7785;font-size:13px;font-style:normal}} .kpi em{{font-size:34px;font-style:normal;font-weight:800}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:14px;margin-bottom:18px}}
.card{{background:#fff;border-radius:12px;padding:16px 18px;margin-bottom:14px}} .card h3{{margin:0 0 12px;font-size:15px}}
.card h3 small{{color:#9AA5B1;font-weight:500;margin-left:6px}}
.bar{{display:grid;grid-template-columns:150px 1fr 170px;align-items:center;gap:10px;margin:7px 0;font-size:13px}}
.track{{background:{L};height:16px;border-radius:8px;overflow:hidden;position:relative}}
.rng{{position:absolute;top:6px;height:4px;background:{N};opacity:.55;border-radius:2px}}
.bv small{{color:#9AA5B1;font-weight:500}} .fill{{display:block;height:100%;background:{G}}}
.fill.harness{{background:{O}}} .fill.superpowers{{background:{N}}} .bv{{text-align:right;font-weight:700}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;background:#fff}} th,td{{padding:7px 8px;border-bottom:1px solid {L};text-align:left}}
th{{background:{N};color:#fff;font-weight:600}} .o{{color:{O}}}
.tl{{width:100%;height:auto}} .ln{{font-size:12px;fill:{N};font-weight:700}} .ax{{font-size:11px;fill:#9AA5B1}}
.legend span{{display:inline-flex;align-items:center;gap:6px;margin-right:16px;font-size:13px}} .legend i{{width:11px;height:11px;border-radius:50%;display:inline-block}}
</style>
<h1>하네스 비교 대시보드</h1><div class="sub">같은 과제 (QUOTE-231 할인 · 할증) · 메인 모델 {rs[0]["model"]} · 숨은 인수 테스트 15개로 채점 · 막대 = 평균, 짙은 선 = 최소~최대</div>
<div class="kpis">{head}</div><div class="grid">{grid}</div>
<div class="card"><h3>실행별 상세</h3><table><tr><th>실행</th><th>조건</th><th>숨은 테스트</th><th>회귀</th><th>회귀 파일</th><th>전체 토큰</th><th>출력</th><th>초</th><th>턴</th><th>Sub Agent</th><th>Skill</th><th>차단</th><th>읽은 정책</th><th>규칙 위반</th></tr>{rows}</table></div>
<div class="card legend"><h3>타임라인</h3><span><i style="background:{O}"></i>Sub Agent · Skill · Hook 차단</span><span><i style="background:{N}"></i>파일 수정</span><span><i style="background:{G}"></i>읽기 · 검색 · 실행</span></div>
{tls}
</html>"""
    out = RUNS / "dashboard.html"
    out.write_text(page, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
