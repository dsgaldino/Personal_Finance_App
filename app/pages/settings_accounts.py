import pandas as pd
import streamlit as st

from src.db.connection import get_conn

st.title("Accounts")

conn = get_conn()

# ---- Load existing accounts ----
df = pd.read_sql_query(
    """
    SELECT account_id, institution, account_name, currency, opening_balance, opening_date
    FROM accounts
    ORDER BY institution, account_name
    """,
    conn,
)

# Friendly headers without renaming backend columns
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "account_id": st.column_config.Column("Account Nr."),
        "institution": st.column_config.Column("Bank / Institution"),
        "account_name": st.column_config.Column("Account Name"),
        "currency": st.column_config.Column("Currency"),
        "opening_balance": st.column_config.NumberColumn("Initial Balance", format="%.2f"),
        "opening_date": st.column_config.Column("Initial Date"),
    },
)
# column_config is the intended way to customize column labels/format in Streamlit tables. [web:487]

st.divider()

st.subheader("Add / Update")

with st.form("account_form", clear_on_submit=False):
    c1, c2 = st.columns(2)
    with c1:
        account_id = st.text_input("Account Nr.", placeholder="999999999")
        institution = st.text_input("Bank / Institution", placeholder="Bank")
        currency = st.selectbox("Currency", options=["EUR", "USD", "BRL", "GBP"], index=0)
    with c2:
        account_name = st.text_input("Account Name", placeholder="Main Account")

        # No +/- steppers: use text_input and validate
        opening_balance_txt = st.text_input("Initial Balance", value="0.00", help="Numbers only. Example: 1234.56")
        opening_date = st.date_input("Initial Date (Optional)", value=None)

    submitted = st.form_submit_button("Save")

if submitted:
    account_id_clean = account_id.strip()
    institution_clean = institution.strip()
    account_name_clean = account_name.strip()

    if not account_id_clean:
        st.error("Account Number is required.")
        st.stop()
    if not account_name_clean:
        st.error("Account Name is required.")
        st.stop()

    try:
        opening_balance = float(opening_balance_txt.replace(",", ".").strip())
    except ValueError:
        st.error("Initial balance must be a number (example: 1234.56).")
        st.stop()

    conn.execute(
        """
        INSERT INTO accounts (account_id, institution, account_name, currency, opening_balance, opening_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(account_id) DO UPDATE SET
          institution=excluded.institution,
          account_name=excluded.account_name,
          currency=excluded.currency,
          opening_balance=excluded.opening_balance,
          opening_date=excluded.opening_date
        """,
        (
            account_id_clean,
            institution_clean,
            account_name_clean,
            currency,
            float(opening_balance),
            opening_date.isoformat() if opening_date else None,
        ),
    )
    conn.commit()
    st.success("Saved.")
    st.rerun()

st.divider()
st.subheader("Delete account")

if df.empty:
    st.info("No accounts to delete yet.")
else:
    account_to_delete = st.selectbox(
        "Select account",
        options=df["account_id"].tolist(),
    )

    confirm = st.checkbox("I understand this will delete the account.", value=False)

    if st.button("Delete", type="primary", disabled=not confirm):
        try:
            conn.execute("DELETE FROM accounts WHERE account_id = ?", (account_to_delete,))
            conn.commit()
            st.success("Account deleted.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not delete account: {e}")
