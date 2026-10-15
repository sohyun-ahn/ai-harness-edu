"""Lab 5 — stream-json 이벤트(events.jsonl)를 한 장짜리 HTML 타임라인으로. 표준 라이브러리만 쓴다.

실행:  python lab5_multiagent/visualize.py lab5_multiagent/sample_events.jsonl
       python lab5_multiagent/visualize.py runs/<파일>.jsonl -o timeline.html
그림:  줄(lane) = 메인 + 서브에이전트마다 하나 · 막대 = 도구 호출(시작~결과) · 주황 화살표 = 위임과 반환
       줄 이름 아래 숫자 = 그 줄이 쓴 토큰 (in+캐시 / out)
시각:  이벤트의 _ts(ms, run.py 가 받은 시각을 붙임)를 쓴다. 없으면 이벤트 순서로 그린다.
"""
import argparse
import html
import json
from pathlib import Path

NAVY, GRAY, ORANGE = "#1F3A5F", "#D9DDE3", "#F28C28"
DELEGATE = ("Agent", "Task")


def load(path):
    events = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def analyze(events):
    """이벤트 → {lanes, calls, marks, result, timed}. 서브에이전트 이벤트는 parent_tool_use_id 로 줄을 찾는다."""
    timed = any("_ts" in e for e in events)
    lanes = {"main": {"name": "main", "kind": "main", "in": 0, "cache": 0, "out": 0, "model": None,
                      "first": None, "last": None}}
    lane_of_call, calls, marks, seen, result, init = {}, {}, [], set(), None, None

    def touch(lane, ts):
        ln = lanes[lane]
        ln["first"] = ts if ln["first"] is None else min(ln["first"], ts)
        ln["last"] = ts if ln["last"] is None else max(ln["last"], ts)

    for i, e in enumerate(events):
        ts = e.get("_ts", i * 1000) if timed else i * 1000
        parent = e.get("parent_tool_use_id")
        lane = lane_of_call.get(parent, "main") if parent else "main"
        if parent and parent not in lane_of_call:          # 부모 호출을 못 본 경우에도 줄은 만든다
            lane = lane_of_call[parent] = f"sub-{parent[-4:]}"
            lanes.setdefault(lane, {"name": lane, "kind": "sub", "in": 0, "cache": 0, "out": 0, "model": None,
                                    "first": None, "last": None})
        t = e.get("type")
        if t == "system" and e.get("subtype") == "init":
            init = e
        elif t == "assistant":
            msg = e.get("message") or {}
            mid = msg.get("id") or f"_{i}"
            if mid not in seen:                              # 같은 메시지가 블록마다 나뉘어 와도 토큰은 한 번만
                seen.add(mid)
                u = msg.get("usage") or {}
                ln = lanes[lane]
                ln["in"] += u.get("input_tokens", 0) or 0
                ln["cache"] += (u.get("cache_read_input_tokens", 0) or 0) + (u.get("cache_creation_input_tokens", 0) or 0)
                ln["out"] += u.get("output_tokens", 0) or 0
                ln["model"] = ln["model"] or msg.get("model")
            touch(lane, ts)
            for b in msg.get("content") or []:
                if b.get("type") == "tool_use":
                    inp = b.get("input") or {}
                    c = {"id": b.get("id"), "name": b.get("name"), "lane": lane, "t0": ts, "t1": None,
                         "input": inp, "error": False, "result": ""}
                    if b.get("name") in DELEGATE:
                        sub = inp.get("subagent_type") or "general-purpose"
                        lane_of_call[b.get("id")] = sub
                        lanes.setdefault(sub, {"name": sub, "kind": "sub", "in": 0, "cache": 0, "out": 0,
                                               "model": None, "first": None, "last": None})
                        c["sub"] = sub
                    calls[b.get("id")] = c
                elif b.get("type") == "text" and b.get("text", "").strip():
                    marks.append({"lane": lane, "t": ts, "text": b["text"].strip()})
        elif t == "user":
            content = (e.get("message") or {}).get("content")
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                    c = calls[b["tool_use_id"]]
                    c["t1"] = ts
                    c["error"] = bool(b.get("is_error"))
                    rc = b.get("content")
                    c["result"] = rc if isinstance(rc, str) else " ".join(
                        x.get("text", "") for x in rc or [] if isinstance(x, dict))
            touch(lane, ts)
        elif t == "result":
            result = e
            touch("main", ts)
    end = max([ln["last"] or 0 for ln in lanes.values()] + [c["t1"] or c["t0"] for c in calls.values()] + [1])
    for c in calls.values():
        if c["t1"] is None:
            c["t1"] = end
    return {"lanes": lanes, "calls": list(calls.values()), "marks": marks, "result": result, "init": init,
            "timed": timed, "end": end}


def lane_rows(a):
    """표·콘솔용 줄별 요약."""
    rows = []
    for key, ln in a["lanes"].items():
        n_tools = sum(1 for c in a["calls"] if c["lane"] == key)
        rows.append({"lane": key, "model": (ln["model"] or "-").replace("claude-", ""), "in": ln["in"],
                     "cache": ln["cache"], "out": ln["out"], "total": ln["in"] + ln["cache"] + ln["out"],
                     "tools": n_tools,
                     "span": f'{((ln["last"] or 0) - (ln["first"] or 0)) / 1000:.1f}' if a["timed"] else "-"})
    return rows


def delegations(a):
    return [c for c in a["calls"] if c["name"] in DELEGATE]


def _short(s, n=60):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def render(a, title="멀티에이전트 타임라인"):
    lanes = list(a["lanes"].items())
    left, width, lane_h, top = 190, 1180, 64, 36
    chart_w = width - left - 24
    end = a["end"] or 1
    x = lambda t: left + (t / end) * chart_w  # noqa: E731
    y = {key: top + i * lane_h for i, (key, _) in enumerate(lanes)}
    height = top + len(lanes) * lane_h + 40
    svg = [f'<svg viewBox="0 0 {width} {height}" width="100%" style="min-width:900px" role="img" aria-label="{html.escape(title)}">',
           '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{ORANGE}"/></marker></defs>']
    # 줄 배경과 이름
    for i, (key, ln) in enumerate(lanes):
        yy = y[key]
        svg.append(f'<rect x="0" y="{yy}" width="{width}" height="{lane_h - 6}" rx="6" fill="{GRAY}" '
                   f'fill-opacity="{0.55 if i % 2 == 0 else 0.3}"/>')
        color = NAVY if key == "main" else ORANGE
        svg.append(f'<text x="12" y="{yy + 24}" class="lane" fill="{color}">{html.escape(key)}</text>')
        svg.append(f'<text x="12" y="{yy + 44}" class="tok">{ln["in"] + ln["cache"]:,} / {ln["out"]:,} tok</text>')
        if ln["kind"] == "sub" and ln["first"] is not None:
            svg.append(f'<rect x="{x(ln["first"]):.1f}" y="{yy + 6}" width="{max(2, x(ln["last"]) - x(ln["first"])):.1f}" '
                       f'height="{lane_h - 18}" rx="5" fill="none" stroke="{ORANGE}" stroke-dasharray="4 3"/>')
    # 시간 눈금
    step = _nice_step(end / 1000) if a["timed"] else max(1, round(end / 1000 / 10))
    t = 0.0
    while t * 1000 <= end + 1:
        xx = x(t * 1000)
        svg.append(f'<line x1="{xx:.1f}" y1="{top - 6}" x2="{xx:.1f}" y2="{height - 34}" stroke="{NAVY}" stroke-opacity="0.08"/>')
        label = f"{t:g}s" if a["timed"] else f"#{int(t)}"
        svg.append(f'<text x="{xx:.1f}" y="{height - 16}" class="axis" text-anchor="middle">{label}</text>')
        t += step
    # 도구 호출 막대
    for c in a["calls"]:
        yy = y[c["lane"]]
        x0, x1 = x(c["t0"]), max(x(c["t1"]), x(c["t0"]) + 5)
        fill = ORANGE if c["name"] in DELEGATE else NAVY
        name = f'{c["name"]} → {c.get("sub")}' if c.get("sub") else c["name"]
        tip = f'{name}\n입력: {_short(json.dumps(c["input"], ensure_ascii=False), 160)}\n결과: {_short(c["result"], 160)}'
        stroke = f' stroke="{ORANGE}" stroke-width="3"' if c["error"] else ""
        if c["error"]:
            tip += "\n(오류·차단)"
        svg.append(f'<g><title>{html.escape(tip)}</title><rect x="{x0:.1f}" y="{yy + 20}" width="{x1 - x0:.1f}" '
                   f'height="18" rx="3" fill="{fill}" fill-opacity="{0.55 if c["name"] in DELEGATE else 0.9}"{stroke}/>')
        if x1 - x0 > 44:
            svg.append(f'<text x="{x0 + 5:.1f}" y="{yy + 33}" class="bar">{html.escape(_short(name, int((x1 - x0) / 7)))}</text>')
        svg.append("</g>")
    # 위임·반환 화살표
    for c in delegations(a):
        sub = c.get("sub")
        if sub not in y:
            continue
        y0, y1 = y[c["lane"]] + 38, y[sub] + 20
        svg.append(f'<line x1="{x(c["t0"]):.1f}" y1="{y0}" x2="{x(c["t0"]) + 8:.1f}" y2="{y1}" stroke="{ORANGE}" '
                   f'stroke-width="2" marker-end="url(#arr)"/>')
        svg.append(f'<line x1="{x(c["t1"]):.1f}" y1="{y1 + 18}" x2="{x(c["t1"]) - 8:.1f}" y2="{y0 - 18}" stroke="{ORANGE}" '
                   f'stroke-width="2" stroke-dasharray="5 3" marker-end="url(#arr)"/>')
    # 글 출력 표시
    for m in a["marks"]:
        yy = y[m["lane"]]
        svg.append(f'<g><title>{html.escape(_short(m["text"], 300))}</title><circle cx="{x(m["t"]):.1f}" cy="{yy + 50}" '
                   f'r="4" fill="{NAVY}"/></g>')
    svg.append("</svg>")
    return _page(title, a, "\n".join(svg))


def _nice_step(sec):
    for s in (0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300):
        if sec / s <= 14:
            return s
    return 600


def _page(title, a, svg):
    r = a["result"] or {}
    u = r.get("usage") or {}
    main_tok = sum((u.get(k, 0) or 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                                 "cache_creation_input_tokens"))
    all_tok = sum(ln["in"] + ln["cache"] + ln["out"] for ln in a["lanes"].values())
    model = (a["init"] or {}).get("model", "-")
    meta = [("세션", (r.get("session_id") or (a["init"] or {}).get("session_id") or "-")[:13]), ("모델(메인)", model),
            ("턴", r.get("num_turns", "-")), ("시간", f'{(r.get("duration_ms") or 0) / 1000:.1f}s'),
            ("메인 토큰(result)", f"{main_tok:,}"), ("줄별 합계", f"{all_tok:,}"),
            ("위임", len(delegations(a))), ("도구 호출", len(a["calls"]))]
    rows = "".join(
        f'<tr><td><b style="color:{NAVY if x["lane"] == "main" else ORANGE}">{html.escape(x["lane"])}</b></td>'
        f'<td>{html.escape(x["model"])}</td><td>{x["in"]:,}</td><td>{x["cache"]:,}</td><td>{x["out"]:,}</td>'
        f'<td><b>{x["total"]:,}</b></td><td>{x["tools"]}</td><td>{x["span"]}</td></tr>' for x in lane_rows(a))
    dl = "".join(
        f'<li><b>{html.escape(c.get("sub") or "?")}</b> ({(c["t1"] - c["t0"]) / 1000:.1f}s) — '
        f'{html.escape(_short(c["input"].get("description") or c["input"].get("prompt", ""), 80))}'
        f'<br><span class="ret">↩ {html.escape(_short(c["result"], 160))}</span></li>' for c in delegations(a))
    final = html.escape(r.get("result") or "")
    order = " → ".join(c.get("sub") or "?" for c in delegations(a)) or "(위임 없음)"
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--navy:{NAVY};--gray:{GRAY};--orange:{ORANGE}}}
body{{margin:0;padding:24px 16px;background:#fff;color:#1b2430;font:14px/1.5 -apple-system,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif}}
main{{max-width:1200px;margin:0 auto}}
h1{{font-size:20px;color:var(--navy);margin:0 0 4px}}
.sub{{color:#5b6573;margin:0 0 16px}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px;padding:0;list-style:none}}
.meta li{{background:var(--gray);border-radius:6px;padding:6px 10px}}
.meta b{{color:var(--navy)}}
.card{{border:1px solid var(--gray);border-radius:10px;padding:12px;margin:0 0 16px;overflow-x:auto}}
svg text.lane{{font-size:14px;font-weight:700}} svg text.tok{{font-size:11px;fill:#5b6573}}
svg text.axis{{font-size:11px;fill:#5b6573}} svg text.bar{{font-size:11px;fill:#fff}}
table{{border-collapse:collapse;width:100%}} th,td{{border-bottom:1px solid var(--gray);padding:6px 8px;text-align:right}}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}} th{{color:var(--navy)}}
.legend span{{display:inline-block;margin-right:16px}} .sw{{display:inline-block;width:18px;height:10px;border-radius:2px;vertical-align:middle;margin-right:4px}}
ol li{{margin-bottom:6px}} .ret{{color:#5b6573}}
pre{{white-space:pre-wrap;background:#f6f7f9;border-radius:8px;padding:10px;margin:0}}
</style></head><body><main>
<h1>{html.escape(title)}</h1>
<p class="sub">위임 순서: <b>{html.escape(order)}</b></p>
<ul class="meta">{"".join(f"<li>{k} <b>{html.escape(str(v))}</b></li>" for k, v in meta)}</ul>
<div class="card legend"><span><i class="sw" style="background:{NAVY}"></i>도구 호출</span>
<span><i class="sw" style="background:{ORANGE};opacity:.6"></i>서브에이전트 위임</span>
<span><i class="sw" style="border:1px dashed {ORANGE}"></i>서브에이전트가 일한 구간</span>
<span>● 글 출력 · 막대에 마우스를 올리면 입력·결과</span></div>
<div class="card">{svg}</div>
<div class="card"><table><thead><tr><th>줄</th><th>모델</th><th>in</th><th>캐시</th><th>out</th><th>합계</th><th>도구</th><th>구간(s)</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<div class="card"><b>위임과 반환</b><ol>{dl or "<li>없음</li>"}</ol></div>
<div class="card"><b>최종 답</b><pre>{final}</pre></div>
</main></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events", help="events.jsonl (stream-json 한 줄에 하나)")
    ap.add_argument("-o", "--out", help="HTML 경로 (기본: 같은 이름 .html)")
    ap.add_argument("--title", default="멀티에이전트 타임라인")
    args = ap.parse_args()
    a = analyze(load(args.events))
    out = Path(args.out) if args.out else Path(args.events).with_suffix(".html")
    out.write_text(render(a, args.title), encoding="utf-8")
    for row in lane_rows(a):
        print(f"  {row['lane']:<18} in {row['in']:>6,} 캐시 {row['cache']:>8,} out {row['out']:>6,} 도구 {row['tools']}")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
