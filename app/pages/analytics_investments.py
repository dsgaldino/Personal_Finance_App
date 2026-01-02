from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from src.db.connection import get_conn
from src.db.queries import load_transactions, income_vs_expense_by_month


st.title("Analytics · Investments")

conn = get_conn()

period = st.date_input("Period", value=(date.today().replace(day=1), date.today()))
if isinstance(period, tuple) and len(period) == 2:
    start_date, end_date = period
else:
    start_date, end_date = date.today().replace(day=1), date.today()

df = load_transactions(
    conn,
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d"),
    account_id="ALL",
)

# Investment = category_final == Investment
df["category_final"] = df["category_final"].fillna("Uncategorized")
inv = df[df["category_final"] == "Investment"].copy()

st.caption(f"{len(inv)} investment transactions in period")

net = float(inv["amount"].sum()) if not inv.empty else 0.0
st.metric("Net investment cashflow", f"{net:,.2f}")

st.subheader("Investment transactions")
st.dataframe(
    inv[["date", "account_id", "amount", "currency", "subcategory_final", "description_cleaned"]]
      .rename(columns={"description_cleaned": "description"}),
    use_container_width=True,
    hide_index=True,
)

with st.expander("Monthly view (cashflow)", expanded=False):
    monthly = income_vs_expense_by_month(inv)
    if monthly.empty:
        st.info("No monthly data.")
    else:
        st.bar_chart(monthly.set_index("month")[["income", "expense"]])
