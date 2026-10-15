"""dev · prod 가상 DB와 가짜 비밀 파일 만들기 (교육용). 실습 시작 전에 한 번: python3 tools/make_db.py"""
import sqlite3
from pathlib import Path

ROWS = [(1, "한빛상사", "A"), (2, "동해철강", "b"), (3, "서진기계", "B"), (4, "남포산업", "a"),
        (5, "청림건설", "B"), (6, "가람물산", "c"), (7, "태성정밀", "A"), (8, "우리공업", "b")]
DB = Path(__file__).resolve().parent.parent / "db"
for env in ("dev", "prod"):
    f = DB / f"{env}.db"
    f.unlink(missing_ok=True)
    c = sqlite3.connect(f)
    c.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, tier TEXT)")
    c.executemany("INSERT INTO customers VALUES (?, ?, ?)", ROWS)
    c.commit()
    c.close()
(DB.parent / ".env").write_text("DB_PASSWORD=DEMO-NOT-REAL-1234\n", encoding="utf-8")   # 가짜 비밀 (실습용)
print("db/dev.db · db/prod.db · 가짜 비밀 파일 생성")
