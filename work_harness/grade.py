#!/usr/bin/env python3
"""업무 과제 채점 — 작업 폴더에서 새로 생긴 결과물을 모아 정답(gold/)과 대조한다.

  python3 grade.py workspace            # 수강생: VS Code로 작업한 폴더를 채점
  python3 grade.py workspace --task T3  # 과제 하나만

결과 파일 위치는 상관없다 (out/ 이 아니어도 새로 생긴 .md · .csv · .json · .txt 를 모두 읽는다).
파일을 만들지 않고 대화창에만 답했으면 그 답(_final.txt)으로 채점한다.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE / "gold"
ORIG = HERE / "workspace"
SKIP = {".claude", "inputs", "__pycache__", ".git"}


def outputs(wd, task=None):
    """inputs/ · .claude/ · CLAUDE.md 를 뺀 새 결과물 텍스트. task 를 주면 경로나 내용에 그 과제가 보이는 파일 우선."""
    files = [p for p in wd.rglob("*") if p.is_file() and not (set(p.relative_to(wd).parts) & SKIP)
             and p.name != "CLAUDE.md" and p.suffix in (".md", ".csv", ".json", ".txt")]
    if task:
        hit = [p for p in files if task in str(p.relative_to(wd))]
        files = hit or files
    final = wd / "_final.txt"
    if final.exists() and final not in files:
        files.append(final)
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files), [str(p.relative_to(wd)) for p in files]


def inputs_intact(wd):
    h = lambda root: {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (root / "inputs").rglob("*") if p.is_file()}
    return h(wd) == h(ORIG)


def any_of(text, alts):
    return any(a in text for a in alts)


def dates(d):
    y, m, dd = d.split("-")
    m, dd = int(m), int(dd)
    return [d, f"{m}/{dd}", f"{m}월 {dd}일", f"{m:02d}/{dd:02d}", f"{m}.{dd}", f"{m:02d}-{dd:02d}"]


def g_T1(t, g):
    ck = []
    for qid, q in g.items():
        ck += [(f"{qid} 필수 「{k}」", k in t) for k in q["must_include"]]
        ck += [(f"{qid} 금지 「{k}」 없음", k not in t) for k in q["must_not"]]
    seg = t[t.find("Q10"):][:600] if "Q10" in t else ""
    ck.append(("Q10 사람에게 넘김", any_of(seg, ["담당자", "확인 필요", "구매팀", "사람"])))
    return ck


def g_T2(t, g):
    num = t.replace(",", "")
    s06 = t[t.find("S06"):][:800] if "S06" in t else ""
    return [("S02 합계 360,000", "360000" in num),
            ("S02 볼트 240,000", "240000" in num),
            ("S02 너트 · 와셔 60,000", "60000" in num),
            ("S06 확인 필요 표시", any_of(s06, ["확인", "불일치", "다름", "상이"])),
            ("S06을 합계에 넣지 않음 (보류)", "10560000" not in num and "12600000" not in num)]


def g_T3(t, g):
    lines = t.splitlines()
    ck = [(f"{who} · {what} · {d}", any(who in l and any_of(l, dates(d)) for l in lines)) for who, what, d in g["items"]]
    bad = [l for l in lines if g["cancelled"] in l and any(re.search(r"\d{1,2}[/월.-]\s?\d{1,2}", l) for _ in [0])
           and not any_of(l, ["취소", "제외", "보류"])]
    ck.append(("취소된 견학을 할 일로 넣지 않음", not bad))
    return ck


def g_T4(t, g):
    lines = t.splitlines()
    ck = [(f"경고 {e}", e in t) for e in g["warn"]]
    ck += [(f"정비 요청 {e}", any(e in l and "정비" in l for l in lines) or
            any("정비" in l for l in lines[max(0, i - 3):i + 1] for i, x in enumerate(lines) if e in x)) for e in g["repair"]]
    ck += [(f"확인 필요 {e}", any(e in l and any_of(l, ["확인", "결측", "누락", "비어"]) for l in lines)) for e in g["check"]]
    ck += [(f"{e}는 경고 아님 (7.1은 초과 아님)", not any(e in l and "경고" in l and not any_of(l, ["아님", "정상", "미해당", "해당 없음", "경계"]) for l in lines))
           for e in g["not_warn"]]
    return ck


def g_T5(t, g):
    ck = [(f"변경점 「{alts[0]}」", any_of(t, alts)) for alts in g["must"]]
    ck.append(("초안 수치(300톤 5%)를 최종으로 쓰지 않음", not any(tr in t.replace(" ", "") for tr in [x.replace(" ", "") for x in g["trap"]])))
    return ck


def g_T6(t, g):
    ck = [(f"필수 「{alts[0]}」", any_of(t, alts)) for alts in g["must"]]
    ck += [(f"금지 「{k}」 없음", k not in t) for k in g["must_not"]]
    return ck


def g_T7(t, g):
    lines = t.replace(",", "").splitlines()
    ids = {sid: [sid, f"HB-SPEC-{700 + int(sid[3:])}"] for sid in g["specs"]}
    owner = []                                   # 줄마다 어느 사양서 얘기인지
    cur = None
    def mentions(l, sid, al):
        n = 700 + int(sid[3:])
        return any(a in l for a in al) or re.search(rf"(^\s*\|?\s*|^\s*[-*]\s*){n}(\s*\||[).:\s])", l) is not None
    for l in lines:
        hit = [sid for sid, al in ids.items() if mentions(l, sid, al)]
        cur = hit[0] if len(hit) == 1 else (None if hit else cur)
        owner.append(cur)
    ck = []
    for sid, v in g["specs"].items():
        seg = "\n".join(l for l, o in zip(lines, owner) if o == sid)
        if v["needs_human"]:
            held = any_of(seg, ["확인", "보류", "불일치", "누락", "기재"])
            own = [l for l in lines if mentions(l, sid, ids[sid])]   # 그 사양서가 직접 나오는 줄 (요약 표 행)
            no_amount = not any(re.search(r"\d{6,}", l.replace(sid, "")) for l in own)   # 보류한 사양서에 금액을 내지 않음
            ck.append((f"{sid} 견적 보류 · 확인 필요 ({v['trap']})", held and no_amount))
        elif v["no_price"]:
            ck.append((f"{sid} 단가 없음 표시", any_of(seg, ["단가 없음", "단가표에 없", "단가 미등록", "없음", "미등록", "확인"])))
        else:
            ck.append((f"{sid} 금액 {v['amount']:,} ({v['trap']})", str(v["amount"]) in seg))
    ck.append((f"전체 합계 {g['total']:,}", str(g["total"]) in t.replace(",", "")))
    return ck


def grade(wd, task):
    g = json.loads((GOLD / f"{task}.json").read_text(encoding="utf-8"))
    text, files = outputs(wd, task)
    ck = globals()[f"g_{task}"](text, g)
    return {"task": task, "score": sum(ok for _, ok in ck), "total": len(ck), "checks": ck, "files": files,
            "inputs_intact": inputs_intact(wd), "in_out_folder": any(f.startswith(f"out/{task}") for f in files),
            "file_made": any(not f.startswith("_") for f in files)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir", nargs="?", default=str(HERE / "workspace"))
    ap.add_argument("--task", nargs="*")
    a = ap.parse_args()
    wd = Path(a.workdir).resolve()
    for t in a.task or sorted(json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))):
        r = grade(wd, t)
        print(f"\n{t}  {r['score']}/{r['total']}  원본 보존 {'O' if r['inputs_intact'] else 'X'}  결과 위치 {', '.join(r['files'][:3]) or '없음'}")
        for name, ok in r["checks"]:
            print(f"  {'O' if ok else 'X'}  {name}")


if __name__ == "__main__":
    main()
