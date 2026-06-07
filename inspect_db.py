import sqlite3
from pathlib import Path

paths = [
    Path("data/nasmi.db"),
    Path("data/database/nasmi.db"),
]

for path in paths:
    print("=" * 80)
    print(path)
    print("exists:", path.exists())
    if not path.exists():
        continue

    con = sqlite3.connect(path)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    print("tables:", tables)

    for table in tables:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(table, count)
        except Exception as e:
            print(table, "ERROR", e)

    for table in ["documents", "facts", "candidate_facts", "extraction_artifacts", "jobs"]:
        if table in tables:
            print("-" * 40)
            print("sample:", table)
            rows = con.execute(f"SELECT * FROM {table} LIMIT 5").fetchall()
            for row in rows:
                print(row)

    con.close()
