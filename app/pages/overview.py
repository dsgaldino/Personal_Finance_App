import pandas as pd
import streamlit as st

from src.db.connection import get_conn
from src.db.queries import load_transactions, expenses_by_category, income_vs_expense_by_month


st.title("Dashboard")

conn = get_conn()

accounts = pd.read_sql_query(
    "SELECT account_id, account_name, institution, currency FROM accounts ORDER BY institution, account_name",
    conn,
)

account_options = ["ALL"] + accounts["account_id"].astype(str).tolist()

filters = st.container()
with filters:
    col1, col2, col3 = st.columns(3)

    with col1:
        account_id = st.selectbox("Account", options=account_options, index=0)

    with col2:
        start_date = st.text_input("Start date (YYYY-MM-DD)", value="")

    with col3:
        end_date = st.text_input("End date (YYYY-MM-DD)", value="")

df = load_transactions(
    conn,
    start_date=start_date.strip() or None,
    end_date=end_date.strip() or None,
    account_id=account_id,
)

st.caption(f"{len(df)} transactions (filtered)")

# KPIs
income = float(df[df["amount"] > 0]["amount"].sum()) if not df.empty else 0.0
expense = float(df[df["amount"] < 0]["amount"].sum()) if not df.empty else 0.0
net = income + expense  # expense is negative

k1, k2, k3 = st.columns(3)
k1.metric("Income", f"{income:,.2f}")
k2.metric("Expense", f"{abs(expense):,.2f}")
k3.metric("Net", f"{net:,.2f}")

st.divider()

# Expenses by category
cat = expenses_by_category(df)
st.subheader("Expenses by category")
if cat.empty:
    st.info("No expenses in this filter.")
else:
    chart_df = cat.set_index("category_final")[["expense_abs"]]
    st.bar_chart(chart_df, horizontal=True)

st.divider()

# Income vs Expense by month
monthly = income_vs_expense_by_month(df)
st.subheader("Income vs Expense (monthly)")
if monthly.empty:
    st.info("No data for monthly chart.")
else:
    chart_df = monthly.set_index("month")[["income", "expense"]]
    st.bar_chart(chart_df)
