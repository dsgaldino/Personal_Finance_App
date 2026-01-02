from __future__ import annotations

import sqlite3
import pandas as pd


def list_investment_transactions(conn: sqlite3.Connection) -> pd.DataFrame:
    # Investment transactions = category_final == 'Investment'
    # (manual override first, else auto)
    return pd.read_sql_query(
        """
        SELECT
          transaction_id,
          date,
          account_id,
          amount,
          currency,
          details,
          description_cleaned,
          category_auto,
          subcategory_auto,
          category_user,
          subcategory_user
        FROM transactions
        WHERE COALESCE(category_user, category_auto) = 'Investment'
        ORDER BY date DESC
        """,
        conn,
    )
