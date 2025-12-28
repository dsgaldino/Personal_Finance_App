from __future__ import annotations

import sqlite3
import pandas as pd


def load_transactions(
    conn: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
    account_id: str | None = None,
) -> pd.DataFrame:
    where = []
    params: list[object] = []

    if start_date:
        where.append("date >= ?")
        params.append(start_date)
    if end_date:
        where.append("date <= ?")
        params.append(end_date)
    if account_id and account_id != "ALL":
        where.append("account_id = ?")
        params.append(account_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    df = pd.read_sql_query(
        f"""
        SELECT
          transaction_id,
          date,
          account_id,
          amount,
          currency,
          transaction_type,
          details,
          description_cleaned,
          COALESCE(category_user, category_auto) AS category_final,
          COALESCE(subcategory_user, subcategory_auto) AS subcategory_final
        FROM transactions
        {where_sql}
        ORDER BY date DESC
        """,
        conn,
        params=params,
    )
    return df


def expenses_by_category(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category_final", "expense_abs"])

    tmp = df.copy()
    tmp["category_final"] = tmp["category_final"].fillna("Uncategorized")
    exp = tmp[tmp["amount"] < 0].copy()
    exp["expense_abs"] = -exp["amount"]

    out = (
        exp.groupby("category_final", as_index=False)["expense_abs"]
        .sum()
        .sort_values("expense_abs", ascending=False)
    )
    return out


def income_vs_expense_by_month(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "income", "expense"])

    tmp = df.copy()
    tmp["month"] = tmp["date"].astype(str).str.slice(0, 7)  # YYYY-MM

    inc = tmp[tmp["amount"] > 0].groupby("month")["amount"].sum()
    exp = tmp[tmp["amount"] < 0].groupby("month")["amount"].sum().abs()

    out = pd.DataFrame(
        {
            "month": sorted(set(tmp["month"])),
        }
    )
    out["income"] = out["month"].map(inc).fillna(0.0)
    out["expense"] = out["month"].map(exp).fillna(0.0)
    return out.sort_values("month")
