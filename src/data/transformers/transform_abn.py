from __future__ import annotations

import hashlib
import pandas as pd

from src.utils.cleaning import clean_description_for_rules


ABN_REQUIRED_COLS = {
    "accountNumber",
    "mutationcode",
    "transactiondate",
    "amount",
    "description",
}


def _parse_abn_date_yyyymmdd(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s.astype(str), format="%Y%m%d", errors="coerce")


def _normalize_account_id(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    return s


def make_transaction_id(account_id: str, date_iso: str, amount: float, currency: str, details: str) -> str:
    base = f"{account_id}|{date_iso}|{amount:.2f}|{currency}|{details}".strip()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def transform_abn_to_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    missing = ABN_REQUIRED_COLS - set(df_raw.columns)
    if missing:
        raise KeyError(f"Missing columns in ABN file: {sorted(missing)}")

    df = df_raw.copy()

    df["account_id"] = _normalize_account_id(df["accountNumber"])
    df["currency"] = df["mutationcode"].astype(str).str.strip()
    df["date"] = _parse_abn_date_yyyymmdd(df["transactiondate"]).dt.date.astype(str)

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    df["details"] = df["description"].astype(str).fillna("").str.strip()

    # >>> aqui é a mudança importante após ajustar cleaning.py
    df["description_cleaned"] = df["details"].apply(clean_description_for_rules)

    df["transaction_type"] = df["amount"].apply(lambda x: "Income" if x > 0 else "Expense")

    df["transaction_id"] = df.apply(
        lambda r: make_transaction_id(
            account_id=r["account_id"],
            date_iso=r["date"],
            amount=float(r["amount"]) if pd.notna(r["amount"]) else 0.0,
            currency=r["currency"],
            details=r["details"],
        ),
        axis=1,
    )

    out = df[
        [
            "transaction_id",
            "date",
            "institution",  # opcional: se não existir, removemos já já
        ]
    ] if "institution" in df.columns else None

    out = df[
        [
            "transaction_id",
            "date",
            "account_id",
            "amount",
            "currency",
            "details",
            "description_cleaned",
            "transaction_type",
        ]
    ].copy()

    out = out.dropna(subset=["date", "amount"])
    return out
