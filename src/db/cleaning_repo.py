from __future__ import annotations

import sqlite3
import pandas as pd

from src.utils.cleaning import clean_description_for_rules


def recompute_description_cleaned(conn: sqlite3.Connection, only_missing: bool = False) -> int:
    """
    Recalcula description_cleaned a partir de details (raw) usando o cleaning atual.

    - only_missing=False: atualiza tudo (recomendado quando você mudou o cleaning).
    - only_missing=True: atualiza só onde description_cleaned está vazio/NULL.
    """
    where = ""
    if only_missing:
        where = "WHERE description_cleaned IS NULL OR TRIM(description_cleaned) = ''"

    df = pd.read_sql_query(
        f"""
        SELECT transaction_id, details
        FROM transactions
        {where}
        """,
        conn,
    )

    if df.empty:
        return 0

    df["description_cleaned_new"] = df["details"].apply(clean_description_for_rules)

    rows = df[["description_cleaned_new", "transaction_id"]].to_records(index=False)

    cur = conn.cursor()
    cur.executemany(
        """
        UPDATE transactions
        SET description_cleaned = ?
        WHERE transaction_id = ?
        """,
        [(r[0], r[1]) for r in rows],
    )
    conn.commit()

    return int(cur.rowcount)
