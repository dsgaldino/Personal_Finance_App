from typing import Dict

import pandas as pd

STANDARD_COLUMNS: Dict[str, str] = {
    "transaction_id": "string",
    "date": "datetime64[ns]",
    "description": "string",
    "institution": "string",
    "account_source": "string",
    "movement_type": "string",
    "category": "string",
    "subcategory": "string",
    "original_amount": "float",
    "original_currency": "string",
    "base_amount": "float",
    "base_currency": "string",
    "asset": "string",
    "asset_class": "string",
}


def standardize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure the DataFrame has all standard columns and basic dtypes.
    Missing columns are created with null values.
    """
    df = df.copy()

    # Create missing columns
    for col, dtype in STANDARD_COLUMNS.items():
        if col not in df.columns:
            df[col] = pd.NA

    # Basic conversions
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["original_amount"] = pd.to_numeric(df["original_amount"], errors="coerce")

    # For now, base_* = original_*
    df["base_amount"] = df["original_amount"]
    df["base_currency"] = df["original_currency"]

    # Simple transaction_id for now
    if df["transaction_id"].isna().all():
        df["transaction_id"] = df.index.astype(str)

    # Return columns in a fixed order
    return df[list(STANDARD_COLUMNS.keys())]
