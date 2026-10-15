"""데이터 읽기 도우미 — 문의(판교), 사양서(포항), 지식베이스, 단가표."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_cases(track):
    """트랙과 상관없이 [{id, input, gold}] 로 맞춰서 돌려준다."""
    if track == "pangyo":
        return [{"id": r["id"], "input": r["text"], "gold": r}
                for r in read_jsonl(DATA / "pangyo" / "inquiries.jsonl")]
    gold = {r["id"]: r for r in read_jsonl(DATA / "pohang" / "gold.jsonl")}
    cases = []
    for p in sorted((DATA / "pohang" / "specs").glob("*.txt")):
        sid = p.stem.split("_")[0]  # S01_강판.txt → S01
        cases.append({"id": sid, "input": p.read_text(encoding="utf-8"), "gold": gold.get(sid)})
    return cases


def load_kb():
    """kb/*.md 의 '- **IT-3** 제목: 내용' 줄을 {조항ID: 내용} 으로."""
    clauses = {}
    for p in sorted((DATA / "pangyo" / "kb").glob("*.md")):
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"-\s*\*\*([A-Z]+-\d+)\*\*\s*(.+)", line)
            if m:
                clauses[m.group(1)] = m.group(2).strip()
    return clauses


def norm(s):
    """규격 비교용: 공백 제거, 소문자, ×/X → x."""
    return re.sub(r"\s+", "", str(s or "")).lower().replace("×", "x").replace("*", "x")


def load_prices():
    """단가표 → [{품목, 규격, 재질, 단위, 단가}]"""
    with open(DATA / "pohang" / "price_table.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["단가"] = int(r["단가"])
    return rows


def find_price(item, spec):
    """품목·규격으로 단가 행을 찾는다. 규격이 정확히 같아야 한다."""
    for r in load_prices():
        if norm(r["규격"]) == norm(spec) and (norm(r["품목"]) in norm(item) or norm(item) in norm(r["품목"])):
            return r
    return None
