# app/pages/import_data.py
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db.connection import get_conn
from src.data.transformers.transform_abn import transform_abn_to_transactions
from src.utils.categorization import apply_categories_to_cleaned
from src.services.import_service import import_transactions_dataframe


def _format_amount_accounting(x: object) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    try:
        return f"{float(x):.2f}"
    except Exception:
        return str(x)


def render() -> None:
    st.title("Import")
    st.caption("Upload file (.xls / .xlsx)")

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
        return

    files = st.file_uploader(
        "Upload file (.xls / .xlsx)",
        type=["xls", "xlsx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if not files:
        st.info("Upload one or more files to preview them.")
        return

    dfs: list[pd.DataFrame] = []
    read_errors: list[tuple[str, str]] = []

    for f in files:
        try:
            df = pd.read_excel(f)
            df["__source_file__"] = getattr(f, "name", None)
            dfs.append(df)
        except Exception as e:
            read_errors.append((getattr(f, "name", "uploaded_file"), str(e)))

    for name, err in read_errors:
        st.error(f"Could not read {name}: {err}")

    if not dfs:
        return

    df_all = pd.concat(dfs, ignore_index=True)

    if "accountNumber" not in df_all.columns:
        st.error("Expected ABN column 'accountNumber'.")
        return

    df_all["accountNumber"] = (
        pd.Series(df_all["accountNumber"]).dropna().astype(str).str.strip()
    )
    detected_accounts = sorted(df_all["accountNumber"].dropna().unique().tolist())

    accounts_lookup = (
        accounts.assign(account_id_str=accounts["account_id"].astype(str))
        .set_index("account_id_str")["account_name"]
        .to_dict()
    )

    st.subheader("Accounts in the file")

    mapping_rows: list[dict[str, str]] = []
    missing: list[str] = []
    for acc in detected_accounts:
        account_name = accounts_lookup.get(str(acc))
        if account_name is None:
            missing.append(acc)
            account_name = "Missing (create it in Settings → Accounts)"
        mapping_rows.append({"Account Number": acc, "Account Name": account_name})

    st.dataframe(pd.DataFrame(mapping_rows), use_container_width=True, hide_index=True)

    if missing:
        st.warning(
            "Some account numbers are not registered in Settings → Accounts. "
            "Create them before importing."
        )
        return

    st.divider()

    try:
        with st.spinner("Transforming and cleaning..."):
            tx = transform_abn_to_transactions(df_all)
    except Exception as e:
        st.error(f"Transform error: {e}")
        st.stop()

    try:
        with st.spinner("Applying categories..."):
            tx_cat = apply_categories_to_cleaned(tx)
    except Exception as e:
        st.error(f"Categorization error: {e}")
        st.stop()

    preview_cols = [
        "date",
        "amount",
        "currency",
        "account_id",
        "description_cleaned",
        "category_auto",
        "subcategory_auto",
    ]
    missing_preview_cols = [c for c in preview_cols if c not in tx_cat.columns]
    if missing_preview_cols:
        st.error(f"Preview columns missing from transformer output: {missing_preview_cols}")
        st.stop()

    preview = tx_cat[preview_cols].copy()
    preview["amount"] = preview["amount"].apply(_format_amount_accounting)

    preview = preview.rename(
        columns={
            "date": "Date",
            "amount": "Amount",
            "currency": "Currency",
            "account_id": "Account",
            "description_cleaned": "Description (cleaned)",
            "category_auto": "Category",
            "subcategory_auto": "Subcategory",
        }
    )

    st.subheader("Preview")
    st.caption(f"{len(preview)} rows ready to import")

    st.dataframe(
        preview.sort_values("Date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    confirm = st.checkbox("I confirm I want to import these transactions.", value=False)

    if st.button("Import & Save", type="primary", disabled=not confirm):
        result = import_transactions_dataframe(
            tx,
            conn=conn,
            run_categorization=True,
            only_missing=True,
        )
        st.success(f"Import finished. Inserted: {result.inserted}")


render()
