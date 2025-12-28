import sqlite3
from pathlib import Path

db_path = Path("data/processed/personal_finance.sqlite")

print("DB absolute path:", db_path.resolve())
print("DB exists:", db_path.exists(), "size:", db_path.stat().st_size if db_path.exists() else None)

with sqlite3.connect(db_path) as conn:
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()

print("Tables:", tables)
