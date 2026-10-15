"""월간 고객 등급 리포트 — 운영 DB를 읽는다."""
import sqlite3
from collections import Counter
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "db" / "prod.db"
tiers = Counter(t for (t,) in sqlite3.connect(DB).execute("SELECT tier FROM customers"))
for t in ("A", "B", "C"):
    print(f"{t} 등급: {tiers.get(t, 0)}곳")
unknown = {k: v for k, v in tiers.items() if k not in ("A", "B", "C")}
if unknown:
    raise SystemExit(f"오류: 알 수 없는 등급 값 {unknown}")
