import pandas as pd
from src.data.abn.load_abn import load_abn


def transform_abn(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw ABN dataframe to the common schema:
    date, description, original_amount, original_currency, account_source, institution.

    Expected raw columns (from load_abn):
      - transactiondate (int YYYYMMDD)
      - description (str)
      - amount (float)
    """
    df = df.copy()

    # 1) Rename raw columns to standard names
    df.rename(
        columns={
            "transactiondate": "date",
            "description": "description",
            "amount": "original_amount",
        },
        inplace=True,
    )

    # 2) Convert date from int YYYYMMDD to datetime
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d", errors="coerce")

    # 3) Fill standard metadata
    df["original_currency"] = "EUR"       # ABN is EUR by default
    df["account_source"] = "ABN"
    df["institution"] = "ABN AMRO"

    # 4) Select and order columns
    cols = [
        "date",
        "description",
        "original_amount",
        "original_currency",
        "account_source",
        "institution",
    ]
    df = df[cols]

    return df


if __name__ == "__main__":
    # simple local test
    raw = load_abn("abn_real.xls")  # ajuste o nome se for diferente
    std = transform_abn(raw)
    print(std.head())
    print(std.dtypes)
