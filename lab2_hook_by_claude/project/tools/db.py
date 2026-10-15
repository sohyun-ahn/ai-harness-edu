"""DB에 SQL 실행: python3 tools/db.py --env dev|prod "SQL" """
import argparse
import sqlite3
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--env", choices=["dev", "prod"], required=True)
ap.add_argument("sql")
a = ap.parse_args()
c = sqlite3.connect(Path(__file__).resolve().parent.parent / "db" / f"{a.env}.db")
cur = c.execute(a.sql)
for row in cur.fetchall():
    print(row)
c.commit()
print(f"[{a.env}] 완료")
