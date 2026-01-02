from __future__ import annotations

import sqlite3
import pandas as pd


def init_parameters_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS parameters (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def get_parameters(conn: sqlite3.Connection) -> pd.DataFrame:
    init_parameters_table(conn)
    return pd.read_sql_query(
        "SELECT key, value, updated_at FROM parameters ORDER BY key",
        conn,
    )


def upsert_parameters(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    init_parameters_table(conn)

    needed = {"key", "value"}
    missing = needed - set(df.columns)
    if missing:
        raise KeyError(f"Missing columns: {sorted(missing)}")

    rows = df[["key", "value"]].to_records(index=False)

    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO parameters(key, value, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          updated_at = datetime('now')
        """,
        [(str(r[0]).strip(), str(r[1]).strip()) for r in rows],
    )
    conn.commit()
    return int(cur.rowcount)