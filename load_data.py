#!/usr/bin/env python3
"""Create the SQLite database and load cell-count.csv into it.
Usage:  python load_data.py           
Output: loblaw_bio.db in the repository root.
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DB_PATH = ROOT / "loblaw_bio.db"
SCHEMA_PATH = ROOT / "schema.sql"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

# The task text and the actual file use slightly different column names;
# accept both so the loader works with either.
ALIASES = {
    "sample_id": "sample",
    "indication": "condition",
    "gender": "sex",
    "subject_id": "subject",
    "project_id": "project",
}


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        reader.fieldnames = [ALIASES.get(c.strip(), c.strip()) for c in reader.fieldnames]
        needed = {"project", "subject", "condition", "age", "sex", "treatment", "response",
                  "sample", "sample_type", "time_from_treatment_start", *POPULATIONS}
        missing = needed - set(reader.fieldnames)
        if missing:
            sys.exit(f"cell-count.csv is missing columns: {sorted(missing)}")
        for row in reader:
            yield {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def main() -> None:
    if not CSV_PATH.exists():
        sys.exit(f"Input file not found: {CSV_PATH}\nPlace cell-count.csv in the repository root.")

    if DB_PATH.exists():
        DB_PATH.unlink()  

    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA_PATH.read_text())

    n_samples = 0
    seen_subjects = {} 
    with con:
        for r in read_rows(CSV_PATH):
            meta = (r["project"], r["condition"],
                    int(r["age"]) if r["age"] else None,
                    r["sex"] or None, r["treatment"], r["response"] or None)
            prev = seen_subjects.setdefault(r["subject"], meta)
            if prev != meta:
                sys.exit(f"Inconsistent metadata for subject {r['subject']} "
                         f"(sample {r['sample']}): {prev} vs {meta}")
            con.execute("INSERT OR IGNORE INTO projects VALUES (?)", (r["project"],))
            con.execute(
                "INSERT OR IGNORE INTO subjects VALUES (?,?,?,?,?,?,?)",
                (r["subject"], *meta),
            )
            con.execute(
                "INSERT INTO samples VALUES (?,?,?,?)",
                (r["sample"], r["subject"], r["sample_type"],
                 int(r["time_from_treatment_start"])),
            )
            con.executemany(
                "INSERT INTO cell_counts VALUES (?,?,?)",
                [(r["sample"], p, int(r[p])) for p in POPULATIONS],
            )
            n_samples += 1

    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("projects", "subjects", "samples", "cell_counts")}
    con.close()
    print(f"Loaded {n_samples} samples into {DB_PATH.name}: {counts}")


if __name__ == "__main__":
    main()
