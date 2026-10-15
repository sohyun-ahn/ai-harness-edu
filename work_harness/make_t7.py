#!/usr/bin/env python3
"""T7 — 사양서 40건 일괄 견적 (함정 포함) 생성. 가상 자료 · 고정 시드라 매번 같은 결과.

  python3 make_t7.py   → workspace/inputs/T7/ (사양서 40건 + 단가표) · gold/T7.json
"""
import csv
import json
import random
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "workspace" / "inputs" / "T7"
NOTE = "※ 가상 회사 「한빛스틸」 실습용 가상 문서"
rng = random.Random(20261015)

PRICE = [  # 품목, 규격, 재질, 단위, 단가
    ("강판", "6t x 1500 x 3000", "SS275", "EA", 210000), ("강판", "9t x 2000 x 6000", "SM355A", "EA", 1020000),
    ("볼트", "M20 x 80", "SCM435", "EA", 1200), ("볼트", "M16 x 60", "SS400", "EA", 650),
    ("너트", "M20", "SS400", "EA", 300), ("와셔", "M20", "SS400", "EA", 150),
    ("게이트밸브", "50A 10K", "SCS13", "EA", 185000), ("가스켓", "50A 10K", "비석면", "EA", 4800),
    ("베어링", "6312ZZ", "SUJ2", "EA", 38000), ("베어링", "22220EK", "SUJ2", "EA", 412000),
    ("원심펌프", "150 x 125 / 37kW", "SCS13", "SET", 18500000), ("기어커플링", "GC-112", "SCM440", "SET", 2350000),
]
OTHER_MAT = {"SS275": "SM355A", "SCM435": "SS400", "SCS13": "SCS14", "SUJ2": "SUJ3", "SS400": "SUS304", "비석면": "흑연",
             "SM355A": "SS275", "SCM440": "SCM435"}


def fmt_kv(no, items, extra):
    s = [f"[자재 사양서] 문서번호 {no}", NOTE, ""]
    for it in items:
        s += [f"품목: {it['품목']}", f"규격: {it['규격']}", f"재질: {it['재질']}", f"수량: {it['show']}", ""]
    return "\n".join(s + extra)


def fmt_table(no, items, extra):
    s = [f"[자재 사양서] 문서번호 {no}", NOTE, "", "| 품목 | 규격 | 재질 | 수량 |", "|---|---|---|---|"]
    s += [f"| {it['품목']} | {it['규격']} | {it['재질']} | {it['show']} |" for it in items]
    return "\n".join(s + [""] + extra)


def fmt_sentence(no, items, extra):
    s = [f"[자재 요청] {no}", NOTE, ""]
    s += [f"{k + 1}) {it['품목']} {it['재질']}, {it['규격']} — {it['show']}" for k, it in enumerate(items)]
    return "\n".join(s + [""] + extra)


def fmt_en(no, items, extra):
    s = [f"[Material Spec] Doc No. {no}", NOTE, ""]
    s += [f"Item: {it['품목']}   Size: {it['규격']}   Material: {it['재질']}   Q'ty: {it['show']}" for it in items]
    return "\n".join(s + [""] + extra)


FORMATS = [fmt_kv, fmt_table, fmt_sentence, fmt_en]


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    with open(OUT / "단가표.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["품목", "규격", "재질", "단위", "단가"])
        w.writerows(PRICE)
    traps = (["conflict"] * 4 + ["missing"] * 3 + ["nomat"] * 5 + ["box"] * 5 + ["none"] * 23)
    rng.shuffle(traps)
    gold, total = {}, 0
    for n in range(1, 41):
        sid = f"T7-{n:02d}"
        trap = traps[n - 1]
        picks = rng.sample(PRICE, rng.choice([1, 1, 2, 2, 3]))
        if trap == "box" and picks[0][3] != "EA":
            picks[0] = rng.choice([x for x in PRICE if x[3] == "EA" and x not in picks])
        items, extra, needs, amount, nomat = [], [], False, 0, False
        for k, (name, size, mat, unit, price) in enumerate(picks):
            q = rng.choice([2, 3, 4, 6, 8, 10, 12, 20, 24, 40, 50, 100, 200])
            it = {"품목": name, "규격": size, "재질": mat, "단위": unit, "수량": q, "show": f"{q} {unit}"}
            if k == 0 and trap == "box" and unit == "EA":
                box = rng.choice([5, 10])
                it["수량"] = q * box
                it["show"] = f"{box} 박스 (박스당 {q} {unit})"
            if k == 0 and trap == "nomat":
                it["재질"] = OTHER_MAT[mat]
                nomat = True
            items.append(it)
            if not (k == 0 and trap == "nomat"):
                amount += it["수량"] * price
        if trap == "conflict":
            other = items[0]["수량"] + rng.choice([2, 4, 10])
            extra.append(f"비고: 본문 기준 필요 수량은 {items[0]['품목']} {other} {items[0]['단위']} 입니다.")
            needs = True
        if trap == "missing":
            items[0]["show"] = "(현장 확인 후 기재)"
            needs = True
        text = rng.choice(FORMATS)(f"HB-SPEC-{700 + n}", items, extra)
        (OUT / f"{sid}.txt").write_text(text + "\n", encoding="utf-8")
        g = {"needs_human": needs, "no_price": nomat and not needs,
             "amount": None if (needs or nomat) else amount, "trap": trap}
        if g["amount"]:
            total += amount
        gold[sid] = g
    json.dump({"specs": gold, "total": total}, open(HERE / "gold" / "T7.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    t = json.load(open(HERE / "tasks.json", encoding="utf-8"))
    t["T7"] = "inputs/T7 사양서 40건 견적 내 줘. 사양서별 금액과 전체 합계까지."
    json.dump(t, open(HERE / "tasks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    c = {}
    for v in gold.values():
        c[v["trap"]] = c.get(v["trap"], 0) + 1
    print("T7 생성 · 함정", c, "· 견적 가능 합계", f"{total:,}")


if __name__ == "__main__":
    main()
