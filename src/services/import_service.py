from __future__ import annotations

from dataclasses import dataclass
import sqlite3

import pandas as pd

from src.db.connection import get_conn
from src.db.transactions_repo import insert_transactions
from src.db.categorization_repo import categorize_transactions


@dataclass(frozen=True)
class ImportResult:
    rows_transformed: int
    inserted: int


def import_transactions_dataframe(
    tx: pd.DataFrame,
    *,
    conn: sqlite3.Connection | None = None,
    run_categorization: bool = True,
    only_missing: bool = True,
) -> ImportResult:
    """
    Inserts standardized transactions into SQLite and optionally runs auto-categorization.

    This function assumes `tx` is already in the standardized schema (output of a transformer),
    including a stable `transaction_id` used for deduplication.
    """
    if conn is None:
        conn = get_conn()

    inserted = int(insert_transactions(conn, tx))

    if run_categorization:
        categorize_transactions(conn, only_missing=only_missing)

    return ImportResult(rows_transformed=len(tx), inserted=inserted)
