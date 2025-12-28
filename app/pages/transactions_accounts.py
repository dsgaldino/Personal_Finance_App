import pandas as pd
import streamlit as st

from src.db.connection import get_conn
from src.db.categorization_repo import categorize_transactions, save_category_overrides
from src.utils.categorization import load_category_rules, get_category_options, get_subcategory_options


st.title("Transactions")

conn = get_conn()

left, right = st.columns(2)
with left:
    if st.button("Run auto-categorization", type="primary"):
        n = categorize_transactions(conn, only_missing=True)
        st.success(f"Auto-categorized: {n} transactions")

with right:
    show_all = st.checkbox("Show all transactions", value=False)

where = "" if show_all else "WHERE (category_user IS NULL AND category_auto IS NULL)"

df = pd.read_sql_query(
    f"""
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
    {where}
    ORDER BY date DESC
    LIMIT 500
    """,
    conn,
)

if df.empty:
    st.info("No transactions to show with current filters.")
    st.stop()

rules = load_category_rules()
category_options = get_category_options(rules)
subcategory_options = get_subcategory_options(rules)

st.caption("Edit category_user/subcategory_user. Blank means no override (keeps auto/None).")

edited = st.data_editor(
    df,
    use_container_width=True,
    hide_index=True,
    disabled=[
        "transaction_id",
        "date",
        "account_id",
        "amount",
        "currency",
        "details",
        "description_cleaned",
        "category_auto",
        "subcategory_auto",
    ],
    column_config={
        "category_user": st.column_config.SelectboxColumn(
            "Category (manual)",
            options=category_options,
        ),
        "subcategory_user": st.column_config.SelectboxColumn(
            "Subcategory (manual)",
            options=subcategory_options,
        ),
    },
    key="tx_editor",
)

def _blank_to_none(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    s = s.replace({"": None, "None": None, "nan": None})
    s = s.where(s.notna(), None)
    return s

if st.button("Save manual categories"):
    payload = edited[["transaction_id", "category_user", "subcategory_user"]].copy()
    payload["category_user"] = payload["category_user"].fillna("").astype(str).str.strip()
    payload["subcategory_user"] = payload["subcategory_user"].fillna("").astype(str).str.strip()
    payload.loc[payload["category_user"] == "", "category_user"] = None
    payload.loc[payload["subcategory_user"] == "", "subcategory_user"] = None

    n = save_category_overrides(conn, payload)
    st.success(f"Saved manual categories for: {n} rows")
