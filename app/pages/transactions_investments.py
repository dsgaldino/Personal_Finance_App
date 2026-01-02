from __future__ import annotations

import streamlit as st

from src.db.connection import get_conn
from src.db.investments_repo import list_investment_transactions


st.title("Transactions · Investments")

conn = get_conn()
df = list_investment_transactions(conn)

if df.empty:
    st.info("No investment transactions found (category_final == 'Investment').")
    st.stop()

text_q = st.text_input("Search", value="").strip()
if text_q:
    mask = df["details"].astype(str).str.contains(text_q, case=False, na=False) | \
           df["description_cleaned"].astype(str).str.contains(text_q, case=False, na=False)
    df = df[mask]

st.caption(f"{len(df)} rows")

st.dataframe(
    df[["date", "account_id", "amount", "currency", "subcategory_auto", "subcategory_user", "description_cleaned", "details"]]
      .rename(columns={"description_cleaned": "description"}),
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="investment_transactions.csv",
    mime="text/csv",
)
