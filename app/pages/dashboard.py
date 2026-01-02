from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st
import altair as alt

from src.db.connection import get_conn
from src.db.queries import load_transactions, expenses_by_category, income_vs_expense_by_month


st.title("Dashboard")

conn = get_conn()

accounts = pd.read_sql_query(
    "SELECT account_id, account_name, institution, currency FROM accounts ORDER BY institution, account_name",
    conn,
)
account_options = [("ALL", "All accounts")] + [
    (str(r.account_id), f"{r.account_name} ({r.institution}, {r.currency})")
    for r in accounts.itertuples(index=False)
]

st.sidebar.header("Filters")

(acc_id, _) = st.sidebar.selectbox(
    "Account",
    options=account_options,
    format_func=lambda x: x[1],
    index=0,
)

period = st.sidebar.date_input(
    "Period",
    value=(date.today().replace(day=1), date.today()),
)

tx_type = st.sidebar.selectbox("Type", options=["ALL", "Expense", "Income"], index=0)
text_q = st.sidebar.text_input("Search text (details/cleaned)", value="").strip()

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

# Type filter
if tx_type != "ALL":
    df = df[df["transaction_type"] == tx_type]

# Text search filter (simple contains)
if text_q:
    mask = df["details"].astype(str).str.contains(text_q, case=False, na=False) | \
           df["description_cleaned"].astype(str).str.contains(text_q, case=False, na=False)
    df = df[mask]

# -------- Category selection state --------
if "selected_category" not in st.session_state:
    st.session_state["selected_category"] = None

topbar1, topbar2 = st.columns([1, 1])
with topbar1:
    st.caption(f"{len(df)} transactions (filtered)")
with topbar2:
    if st.button("Clear category selection"):
        st.session_state["selected_category"] = None
        st.rerun()

income = float(df.loc[df["amount"] > 0, "amount"].sum()) if not df.empty else 0.0
expense = float(df.loc[df["amount"] < 0, "amount"].sum()) if not df.empty else 0.0
net = income + expense

k1, k2, k3 = st.columns(3)
k1.metric("Income", f"{income:,.2f}")
k2.metric("Expense", f"{abs(expense):,.2f}")
k3.metric("Net", f"{net:,.2f}")

st.divider()

c1, c2 = st.columns(2)

with c1:
    st.subheader("Expenses by category (click to filter)")

    cat = expenses_by_category(df).head(15)
    if cat.empty:
        st.info("No expenses in this selection.")
    else:
        # Altair selection (point/click)
        sel = alt.selection_point(fields=["category_final"], name="cat_sel", empty=True)

        chart = (
            alt.Chart(cat)
            .mark_bar()
            .encode(
                y=alt.Y("category_final:N", sort="-x", title="Category"),
                x=alt.X("expense_abs:Q", title="Expense"),
                tooltip=["category_final:N", alt.Tooltip("expense_abs:Q", format=",.2f")],
                opacity=alt.condition(sel, alt.value(1.0), alt.value(0.35)),
            )
            .add_params(sel)
            .properties(height=420)
        )

        event = st.altair_chart(chart, use_container_width=True, on_select="rerun")

        # If user clicked a bar, Streamlit returns selection data.
        try:
            points = event.selection.get("cat_sel", {}).get("points", [])
            if points:
                st.session_state["selected_category"] = points[0].get("category_final")
        except Exception:
            pass

        if st.session_state["selected_category"]:
            st.info(f"Filtering by category: {st.session_state['selected_category']}")

with c2:
    st.subheader("Income vs Expense (monthly)")
    monthly = income_vs_expense_by_month(df)
    if monthly.empty:
        st.info("No data for monthly chart.")
    else:
        st.bar_chart(monthly.set_index("month")[["income", "expense"]])

st.divider()

# Apply category filter to table after chart selection
df_table = df.copy()
if st.session_state["selected_category"]:
    df_table["category_final"] = df_table["category_final"].fillna("Uncategorized")
    df_table = df_table[df_table["category_final"] == st.session_state["selected_category"]]

st.subheader("Transactions (filtered)")
show_cols = st.multiselect(
    "Columns",
    options=list(df_table.columns),
    default=["date", "account_id", "amount", "currency", "category_final", "subcategory_final", "description_cleaned"],
)

st.dataframe(
    df_table[show_cols].sort_values("date", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download CSV",
    data=df_table.to_csv(index=False).encode("utf-8"),
    file_name="transactions_filtered.csv",
    mime="text/csv",
)
