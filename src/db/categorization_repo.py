from __future__ import annotations

import sqlite3
import pandas as pd

from src.utils.categorization import apply_categories_to_cleaned


def categorize_transactions(conn: sqlite3.Connection, only_missing: bool = True) -> int:
    where = "WHERE category_auto IS NULL AND subcategory_auto IS NULL" if only_missing else ""

    tx = pd.read_sql_query(
        f"""
        SELECT transaction_id, description_cleaned
        FROM transactions
        {where}
        """,
        conn,
    )
    if tx.empty:
        return 0

    categorized = apply_categories_to_cleaned(tx)

    rows = categorized[["category_auto", "subcategory_auto", "transaction_id"]].to_records(index=False)

    cur = conn.cursor()
    cur.executemany(
        """
        UPDATE transactions
        SET category_auto = ?,
            subcategory_auto = ?
        WHERE transaction_id = ?
        """,
        [(r[0], r[1], r[2]) for r in rows],
    )
    conn.commit()
    return int(cur.rowcount)


def save_category_overrides(conn: sqlite3.Connection, edited: pd.DataFrame) -> int:
    """
    Expects columns: transaction_id, category_user, subcategory_user
    Only updates rows present in 'edited' (so use it with a filtered table).
    """
    needed = {"transaction_id", "category_user", "subcategory_user"}
    missing = needed - set(edited.columns)
    if missing:
        raise KeyError(f"Missing columns: {sorted(missing)}")

    rows = edited[["category_user", "subcategory_user", "transaction_id"]].to_records(index=False)

    cur = conn.cursor()
    cur.executemany(
        """
        UPDATE transactions
        SET category_user = ?,
            subcategory_user = ?
        WHERE transaction_id = ?
        """,
        [(r[0], r[1], r[2]) for r in rows],
    )
    conn.commit()
    return int(cur.rowcount)
