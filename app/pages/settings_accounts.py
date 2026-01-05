# app/pages/transactions.py
from __future__ import annotations

import sqlite3
import pandas as pd
import streamlit as st

from src.db.connection import get_conn
from src.utils.categorization import load_category_rules


def _load_transactions(conn: sqlite3.Connection, limit: int = 5000) -> pd.DataFrame:
    query = f"""
    SELECT
        t.transaction_id,
        t.date,
        t.account_id,
        a.account_name,
        t.description_cleaned,
        COALESCE(NULLIF(TRIM(t.category_user), ''), t.category_auto) AS category_final,
        COALESCE(NULLIF(TRIM(t.subcategory_user), ''), t.subcategory_auto) AS subcategory_final
    FROM transactions t
    JOIN accounts a ON a.account_id = t.account_id
    ORDER BY t.date DESC
    LIMIT {int(limit)}
    """
    return pd.read_sql_query(query, conn)


def _load_transaction_detail(conn: sqlite3.Connection, transaction_id: str) -> pd.Series:
    df = pd.read_sql_query(
        """
        SELECT
            transaction_id,
            date,
            institution,
            account_id,
            amount,
            currency,
            details,
            description_cleaned,
            transaction_type,
            category_auto,
            subcategory_auto,
            category_user,
            subcategory_user,
            description_user
        FROM transactions
        WHERE transaction_id = ?
        """,
        conn,
        params=(transaction_id,),
    )
    if df.empty:
        raise ValueError("Transaction not found")
    return df.iloc[0]


def _update_transaction_user_fields(
    conn: sqlite3.Connection,
    transaction_id: str,
    *,
    category_user: str | None,
    subcategory_user: str | None,
    description_user: str | None,
) -> None:
    conn.execute(
        """
        UPDATE transactions
        SET
            category_user = ?,
            subcategory_user = ?,
            description_user = ?
        WHERE transaction_id = ?
        """,
        (category_user, subcategory_user, description_user, transaction_id),
    )
    conn.commit()


def render() -> None:
    st.title("Transactions")

    conn = get_conn()

    # Removed: "Run auto-categorization" button (it happens on import now).

    with st.expander("Filters", expanded=False):
        limit = st.number_input("Max rows", min_value=100, max_value=50000, value=5000, step=100)

    tx = _load_transactions(conn, limit=int(limit))

    if tx.empty:
        st.info("No transactions found.")
        return

    # Display table
    display = tx.rename(
        columns={
            "date": "Date",
            "account_name": "Account Name",
            "category_final": "Category",
            "subcategory_final": "Subcategory",
            "description_cleaned": "Description",
        }
    )

    display_cols = ["Date", "Account Name", "Category", "Subcategory", "Description"]

    st.caption("Select a row to edit.")
    event = st.dataframe(
        display[display_cols],
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
    )

    selected_idx = None
    try:
        selected_idx = event.selection.rows[0] if event.selection.rows else None
    except Exception:
        selected_idx = None

    if selected_idx is None:
        return

    selected_transaction_id = tx.iloc[selected_idx]["transaction_id"]

    st.divider()
    st.subheader("Edit transaction")

    row = _load_transaction_detail(conn, str(selected_transaction_id))

    rules = load_category_rules()
    category_options = sorted(set(rules["category"].dropna().astype(str).str.strip()))
    subcategory_options = sorted(set(rules["subcategory"].dropna().astype(str).str.strip()))

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.text_input("Transaction ID", value=str(row["transaction_id"]), disabled=True)
            st.text_input("Date", value=str(row["date"]), disabled=True)
            st.text_input("Account", value=str(row["account_id"]), disabled=True)
            st.text_input("Currency", value=str(row["currency"]), disabled=True)

        with col2:
            st.text_input("Type", value=str(row["transaction_type"]), disabled=True)
            st.number_input("Amount", value=float(row["amount"]), disabled=True)

        with col3:
            st.text_input("Institution", value=str(row["institution"]), disabled=True)

        st.text_area("Details", value=str(row["details"]), disabled=True, height=80)
        st.text_area("Description (cleaned)", value=str(row["description_cleaned"]), disabled=True, height=60)

        st.divider()

        st.caption("Leave blank to remove manual override (fallback to auto).")

        # Category: allow select existing or type new
        category_existing = st.selectbox(
            "Category (existing)",
            options=[""] + category_options,
            index=0,
        )
        category_new = st.text_input("Category (new)", value="")

        subcategory_existing = st.selectbox(
            "Subcategory (existing)",
            options=[""] + subcategory_options,
            index=0,
        )
        subcategory_new = st.text_input("Subcategory (new)", value="")

        description_user = st.text_input(
            "Description override (optional)",
            value="" if row["description_user"] is None else str(row["description_user"]),
        )

        # Resolve final user inputs (new overrides existing; blank => NULL)
        resolved_category = (category_new.strip() or category_existing.strip() or None)
        resolved_subcategory = (subcategory_new.strip() or subcategory_existing.strip() or None)
        resolved_description = (description_user.strip() or None)

        col_save, col_reset = st.columns([1, 1])

        with col_save:
            if st.button("Save", type="primary"):
                _update_transaction_user_fields(
                    conn,
                    str(row["transaction_id"]),
                    category_user=resolved_category,
                    subcategory_user=resolved_subcategory,
                    description_user=resolved_description,
                )
                st.success("Saved.")
                st.rerun()

        with col_reset:
            if st.button("Clear manual override"):
                _update_transaction_user_fields(
                    conn,
                    str(row["transaction_id"]),
                    category_user=None,
                    subcategory_user=None,
                    description_user=None,
                )
                st.success("Cleared.")
                st.rerun()


render()
