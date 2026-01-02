# app/pages/import_data.py
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.utils.categorization import apply_categories


def _validate_required_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize input columns to match the app's expected schema.

    This keeps the page independent from bank-specific loaders for now.
    If your ABN transformer/loader already outputs the standardized schema,
    you can remove this and just call apply_categories() directly.
    """
    df = df.copy()

    rename_map = {}
    if "transactiondate" in df.columns:
        rename_map["transactiondate"] = "date"
    if "date" not in df.columns and "Date" in df.columns:
        rename_map["Date"] = "date"

    if "description" not in df.columns and "Description" in df.columns:
        rename_map["Description"] = "description"
    if "description" not in df.columns and "details" in df.columns:
        rename_map["details"] = "description"

    if "original_amount" not in df.columns and "amount" in df.columns:
        rename_map["amount"] = "original_amount"
    if "original_amount" not in df.columns and "Amount" in df.columns:
        rename_map["Amount"] = "original_amount"

    if "original_currency" not in df.columns and "currency" in df.columns:
        rename_map["currency"] = "original_currency"
    if "original_currency" not in df.columns and "Currency" in df.columns:
        rename_map["Currency"] = "original_currency"

    df = df.rename(columns=rename_map)

    # Best-effort parsing
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    if "original_amount" in df.columns:
        df["original_amount"] = pd.to_numeric(df["original_amount"], errors="coerce")

    # Optional standard columns (safe defaults)
    if "account_source" not in df.columns:
        df["account_source"] = None
    if "institution" not in df.columns:
        df["institution"] = "ABN"

    return df


@st.cache_data(show_spinner=False)
def _read_excel_files(files: list, max_rows: int | None = None) -> pd.DataFrame:
    dfs: list[pd.DataFrame] = []

    for f in files:
        df = pd.read_excel(f)  # Streamlit UploadedFile is file-like [web:635]
        df["__source_file__"] = getattr(f, "name", None)
        dfs.append(df)

    df_all = pd.concat(dfs, ignore_index=True)

    if max_rows is not None and len(df_all) > max_rows:
        df_all = df_all.head(max_rows)

    return df_all


def render() -> None:
    st.title("Import")
    st.caption("Upload file (.xls / .xlsx)")

    files = st.file_uploader(
        "Upload file (.xls / .xlsx)",
        type=["xls", "xlsx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )  # st.file_uploader supports extensions filtering [web:640]

    if not files:
        st.info("Upload one or more files to preview them.")
        return

    try:
        with st.spinner("Reading files..."):
            df_raw = _read_excel_files(files)

        df_std = _standardize_columns(df_raw)

        _validate_required_columns(
            df_std,
            required=["date", "description", "original_amount", "original_currency"],
        )

        with st.spinner("Applying categories..."):
            df_cat = apply_categories(df_std)

        # Keep the display focused
        preferred_cols = [
            "date",
            "description",
            "original_amount",
            "original_currency",
            "transaction_type",
            "category",
            "subcategory",
            "__source_file__",
        ]
        show_cols = [c for c in preferred_cols if c in df_cat.columns]

        st.dataframe(
            df_cat[show_cols].sort_values("date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    except Exception as e:
        st.error("Import failed.")
        st.exception(e)


render()
