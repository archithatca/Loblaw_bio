#!/usr/bin/env python3
"""Check that loblaw_bio.db holds everything in cell-count.csv.

1. Prints every table's columns (in order).
2. Rebuilds the original wide CSV layout from the database with a JOIN and
   compares it to cell-count.csv cell by cell (every column, every row).

Run after `python load_data.py`:   python verify_db.py
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DB, CSV = ROOT / "loblaw_bio.db", ROOT / "cell-count.csv"
POPS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

con = sqlite3.connect(DB)

print("== Tables and columns ==")
for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t:12s} ({n} rows): {', '.join(cols)}")

# Rebuild the CSV layout (same column names and order as the file) from the DB.
pivot = ",\n".join(
    f"MAX(CASE WHEN cc.population='{p}' THEN cc.count END) AS {p}" for p in POPS)
sql = f"""
SELECT sub.project_id AS project, sub.subject_id AS subject, sub.condition, sub.age,
       sub.sex, sub.treatment, COALESCE(sub.response, '') AS response,
       s.sample_id AS sample, s.sample_type, s.time_from_treatment_start,
       {pivot}
FROM samples s
JOIN subjects sub ON sub.subject_id = s.subject_id
JOIN cell_counts cc ON cc.sample_id = s.sample_id
GROUP BY s.sample_id
"""
db = pd.read_sql_query(sql, con)

csv = pd.read_csv(CSV, dtype=str, keep_default_na=False)
csv.columns = [c.strip() for c in csv.columns]
db = db.astype(str)[list(csv.columns)]

print("\n== Round-trip comparison ==")
print(f"CSV rows: {len(csv)}   DB rows: {len(db)}")
ok = True
csv_s = csv.sort_values("sample").reset_index(drop=True)
db_s = db.sort_values("sample").reset_index(drop=True)
for col in csv.columns:
    same = len(csv_s) == len(db_s) and (csv_s[col] == db_s[col]).all()
    ok &= bool(same)
    print(f"  {col:28s} {'OK' if same else 'MISMATCH'}")
print("\nRESULT:", "database reproduces the CSV exactly" if ok else "DIFFERENCES FOUND")
sys.exit(0 if ok else 1)
