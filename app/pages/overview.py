from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from src.db.connection import get_conn
from src.db.queries import load_transactions, expenses_by_category, income_vs_expense_by_month


def _month_range(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    if start.month == 12:
        end = date(start.year + 1, 1, 1) - pd.Timedelta(days=1)
    else:
        end = date(start.year, start.month + 1, 1) - pd.Timedelta(days=1)
    return start, end


st.title("Overview")

conn = get_conn()

accounts = pd.read_sql_query(
    "SELECT account_id, account_name, institution, currency FROM accounts ORDER BY institution, account_name",
    conn,
)
account_options = [("ALL", "All accounts")] + [
    (str(r.account_id), f"{r.account_name} ({r.institution}, {r.currency})")
    for r in accounts.itertuples(index=False)
]

today = date.today()
default_start, default_end = _month_range(today)

c1, c2, c3 = st.columns([1.2, 1.2, 1.6])

with c1:
    (acc_id, _) = st.selectbox(
        "Account",
        options=account_options,
        format_func=lambda x: x[1],
        index=0,
    )

with c2:
    period = st.date_input(
        "Period",
        value=(default_start, default_end),
    )

with c3:
    st.caption("Overview shows a fast summary for the selected period.")

if isinstance(period, tuple) and len(period) == 2:
    start_date, end_date = period
else:
    start_date, end_date = default_start, default_end

df = load_transactions(
    conn,
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d"),
    account_id=acc_id,
)

income = float(df.loc[df["amount"] > 0, "amount"].sum()) if not df.empty else 0.0
expense = float(df.loc[df["amount"] < 0, "amount"].sum()) if not df.empty else 0.0
net = income + expense
savings_rate = (net / income) if income else 0.0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Income", f"{income:,.2f}")
k2.metric("Expense", f"{abs(expense):,.2f}")
k3.metric("Net", f"{net:,.2f}")
k4.metric("Savings rate", f"{savings_rate:.0%}")

st.divider()

top = expenses_by_category(df).head(10)
st.subheader("Top expenses by category")
if top.empty:
    st.info("No expenses in the selected period.")
else:
    st.bar_chart(top.set_index("category_final")[["expense_abs"]], horizontal=True)

st.divider()

st.subheader("Income vs Expense (last 12 months)")
rolling_end = end_date
rolling_start = date(rolling_end.year - 1, rolling_end.month, 1)

df_12m = load_transactions(
    conn,
    start_date=rolling_start.strftime("%Y-%m-%d"),
    end_date=rolling_end.strftime("%Y-%m-%d"),
    account_id=acc_id,
)

monthly = income_vs_expense_by_month(df_12m)
if monthly.empty:
    st.info("Not enough data for the monthly chart.")
else:
    st.bar_chart(monthly.set_index("month")[["income", "expense"]])

st.divider()

st.subheader("Recent transactions")
st.dataframe(
    df[["date", "amount", "currency", "category_final", "description_cleaned"]]
      .rename(columns={"description_cleaned": "description"})
      .head(20),
    use_container_width=True,
    hide_index=True,
)

