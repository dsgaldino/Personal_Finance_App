# app/pages/import_data.py
import pandas as pd
import streamlit as st

from src.db.connection import get_conn
from src.data.transformers.transform_abn import transform_abn_to_transactions
from src.db.transactions_repo import insert_transactions


st.title("Transactions · Import")

conn = get_conn()

accounts = pd.read_sql_query(
    """
    SELECT account_id, account_name, institution, currency
    FROM accounts
    ORDER BY institution, account_name
    """,
    conn,
)

if accounts.empty:
    st.warning("Create at least one account in Settings → Accounts before importing.")
    st.stop()

files = st.file_uploader(
    "Upload ABN statements (.xls / .xlsx)",
    type=["xls", "xlsx"],
    accept_multiple_files=True,
)

if not files:
    st.info("Upload one or more files to preview them.")
    st.stop()

# Read all uploaded files
dfs = []
read_errors = []
for f in files:
    try:
        df = pd.read_excel(f)
        df["__source_file__"] = f.name
        dfs.append(df)
    except Exception as e:
        read_errors.append((f.name, str(e)))

if read_errors:
    for name, err in read_errors:
        st.error(f"Could not read {name}: {err}")

if not dfs:
    st.stop()

df_all = pd.concat(dfs, ignore_index=True)

# ABN validation: must contain accountNumber
if "accountNumber" not in df_all.columns:
    st.error("Expected ABN column 'accountNumber'.")
    st.stop()

df_all["accountNumber"] = pd.Series(df_all["accountNumber"]).dropna().astype(str).str.strip()
detected_accounts = sorted(df_all["accountNumber"].dropna().unique().tolist())

st.subheader("Detected accounts in uploaded files")

accounts_id_set = set(accounts["account_id"].astype(str).tolist())

mapping_rows = []
missing = []
for acc in detected_accounts:
    ok = str(acc) in accounts_id_set
    mapping_rows.append({"accountNumber": acc, "Status": "Found" if ok else "Missing"})
    if not ok:
        missing.append(acc)

st.dataframe(pd.DataFrame(mapping_rows), use_container_width=True, hide_index=True)

if missing:
    st.warning(
        "Some accountNumber values are not registered in Settings → Accounts. "
        "Create them before importing."
    )
    st.stop()

st.divider()
st.subheader("Transform preview")

try:
    tx = transform_abn_to_transactions(df_all)
except Exception as e:
    st.error(f"Transform error: {e}")
    st.stop()

st.caption(f"{len(tx)} rows ready to import")

# --- Quick standardized preview (small) ---
st.dataframe(
    tx[["date", "account_id", "amount", "currency", "description_cleaned"]].head(20),
    use_container_width=True,
    hide_index=True,
)

# --- Raw vs Cleaned preview (expanded) ---
with st.expander("Show cleaning preview (raw vs cleaned)", expanded=False):
    preview_n = st.slider("Rows to preview", min_value=10, max_value=200, value=50, step=10)

    left, right = st.columns(2)

    with left:
        st.caption("Raw (details)")
        st.dataframe(
            tx[["date", "account_id", "amount", "currency", "details"]].head(preview_n),
            use_container_width=True,
            hide_index=True,
        )

    with right:
        st.caption("Cleaned (description_cleaned)")
        st.dataframe(
            tx[["date", "account_id", "amount", "currency", "description_cleaned"]].head(preview_n),
            use_container_width=True,
            hide_index=True,
        )

    st.caption("Combined")
    st.dataframe(
        tx[["date", "amount", "details", "description_cleaned"]].head(preview_n),
        use_container_width=True,
        hide_index=True,
    )

# --- Import action ---
confirm = st.checkbox("I confirm I want to import these transactions.", value=False)

if st.button("Import & Save", type="primary", disabled=not confirm):
    inserted = insert_transactions(conn, tx)
    st.success(f"Import finished. Inserted: {inserted}")
