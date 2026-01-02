from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from src.db.connection import get_conn
from src.db.queries import load_transactions, expenses_by_category, income_vs_expense_by_month


st.title("Analytics · Accounts")

conn = get_conn()

accounts = pd.read_sql_query(
    "SELECT account_id, account_name, institution, currency FROM accounts ORDER BY institution, account_name",
    conn,
)

account_options = [("ALL", "All accounts")] + [
    (str(r.account_id), f"{r.account_name} ({r.institution}, {r.currency})")
    for r in accounts.itertuples(index=False)
]

(acc_id, _) = st.selectbox(
    "Account",
    options=account_options,
    format_func=lambda x: x[1],
    index=0,
)

period = st.date_input("Period", value=(date.today().replace(day=1), date.today()))

if isinstance(period, tuple) and len(period) == 2:
    start_date, end_date = period
else:
    start_date, end_date = date.today().replace(day=1), date.today()

df = load_transactions(
    conn,
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d"),
    account_id=acc_id,
)

st.caption(f"{len(df)} transactions")

# Monthly income vs expense
monthly = income_vs_expense_by_month(df)
st.subheader("Income vs Expense (monthly)")
if monthly.empty:
    st.info("No data for the selected period.")
else:
    st.bar_chart(monthly.set_index("month")[["income", "expense"]])

# Expenses by category
st.subheader("Expenses by category (final)")
cat = expenses_by_category(df)
if cat.empty:
    st.info("No expenses for the selected period.")
else:
    st.bar_chart(cat.head(15).set_index("category_final")[["expense_abs"]], horizontal=True)

with st.expander("Show table (top categories)", expanded=False):
    st.dataframe(cat.head(50), use_container_width=True, hide_index=True)
