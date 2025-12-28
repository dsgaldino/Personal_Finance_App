# src/db/schema.py
from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "personal_finance.sqlite"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
  account_id TEXT PRIMARY KEY,
  institution TEXT NOT NULL,
  account_name TEXT NOT NULL,
  currency TEXT NOT NULL DEFAULT 'EUR',
  opening_balance REAL NOT NULL DEFAULT 0,
  opening_date TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
  transaction_id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  institution TEXT NOT NULL,
  account_id TEXT NOT NULL,
  amount REAL NOT NULL,
  currency TEXT NOT NULL,
  details TEXT NOT NULL,
  description_cleaned TEXT NOT NULL,
  transaction_type TEXT NOT NULL,
  category_auto TEXT,
  subcategory_auto TEXT,
  category_user TEXT,
  subcategory_user TEXT,
  description_user TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- ===== Indexes (performance) =====
-- Common date filters / ordering
CREATE INDEX IF NOT EXISTS idx_transactions_date
  ON transactions(date);

-- Common filters: per account + time series
CREATE INDEX IF NOT EXISTS idx_transactions_account_date
  ON transactions(account_id, date);

-- Common filters: income vs expense over time
CREATE INDEX IF NOT EXISTS idx_transactions_type_date
  ON transactions(transaction_type, date);

-- Useful for "latest imports" / audit / troubleshooting
CREATE INDEX IF NOT EXISTS idx_transactions_created_at
  ON transactions(created_at);

-- For reports by currency
CREATE INDEX IF NOT EXISTS idx_transactions_currency_date
  ON transactions(currency, date);

-- For reports by institution (if you ever add other sources)
CREATE INDEX IF NOT EXISTS idx_transactions_institution_date
  ON transactions(institution, date);

-- For "final category" reporting (manual overrides first, else auto)
CREATE INDEX IF NOT EXISTS idx_transactions_category_user
  ON transactions(category_user);

CREATE INDEX IF NOT EXISTS idx_transactions_category_auto
  ON transactions(category_auto);

-- Partial index to accelerate the default "uncategorized" screen
-- (indexes only rows where both are NULL, usually a small subset). [web:977]
CREATE INDEX IF NOT EXISTS idx_transactions_uncategorized
  ON transactions(date)
  WHERE category_user IS NULL AND category_auto IS NULL;
"""


def init_db(db_path: Path = DB_PATH) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(SCHEMA_SQL)

        # Migration: add currency column if DB was created before
        cols = {row[1] for row in conn.execute("PRAGMA table_info(accounts);").fetchall()}
        if "currency" not in cols:
            conn.execute("ALTER TABLE accounts ADD COLUMN currency TEXT NOT NULL DEFAULT 'EUR';")

        conn.commit()
