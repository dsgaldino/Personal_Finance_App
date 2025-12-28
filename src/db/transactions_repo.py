from __future__ import annotations

import sqlite3
import pandas as pd


TX_REQUIRED_COLS = {
    "transaction_id",
    "date",
    "account_id",
    "amount",
    "currency",
    "details",
    "description_cleaned",
    "transaction_type",
}


def insert_transactions(conn: sqlite3.Connection, tx: pd.DataFrame) -> int:
    if tx is None or tx.empty:
        return 0

    missing = TX_REQUIRED_COLS - set(tx.columns)
    if missing:
        raise KeyError(f"Missing columns in tx DataFrame: {sorted(missing)}")

    before = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

    rows = tx[
        [
            "transaction_id",
            "date",
            "account_id",
            "amount",
            "currency",
            "details",
            "description_cleaned",
            "transaction_type",
        ]
    ].to_records(index=False)

    conn.executemany(
        """
        INSERT INTO transactions (
          transaction_id,
          date,
          institution,
          account_id,
          amount,
          currency,
          details,
          description_cleaned,
          transaction_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(transaction_id) DO NOTHING
        """,
        [
            (
                r[0],
                r[1],
                "ABN AMRO",
                r[2],
                float(r[3]),
                r[4],
                r[5],
                r[6],
                r[7],
            )
            for r in rows
        ],
    )
    conn.commit()

    after = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    return int(after - before)
