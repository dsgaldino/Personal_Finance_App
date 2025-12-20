import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/example")  # já existia; vamos manter

REAL_DATA_DIR = Path("data/real/abn")


def load_abn_example() -> pd.DataFrame:
    """Load sample ABN CSV and return a basic standardized DataFrame."""
    file_path = DATA_DIR / "abn_example.csv"
    df = pd.read_csv(file_path)

    df = df.rename(
        columns={
            "date": "date",
            "description": "description",
            "amount": "original_amount",
            "currency": "original_currency",
            "account": "account_source",
        }
    )

    df["institution"] = "ABN"
    df["movement_type"] = None
    df["category"] = None
    df["subcategory"] = None

    return df


def load_abn_xlsx(filename: str) -> pd.DataFrame:
    """
    Load a real ABN statement from an Excel file and map it to the internal schema (partial).
    The file must be located under data/real/abn/.
    """
    file_path = REAL_DATA_DIR / filename

    # Ajuste header=0 se o arquivo tiver cabeçalho na primeira linha
    df = pd.read_excel(file_path, header=0, engine ="xlrd")

    # Rename columns from ABN layout to internal names
    df = df.rename(
        columns={
            "transactiondate": "date",
            "description": "description",
            "amount": "original_amount",
            "accountNumber": "account_source",
        }
    )

    # Currency: se tiver coluna separada, use; se não, fixa como EUR
    if "currency" in df.columns:
        df = df.rename(columns={"currency": "original_currency"})
    else:
        df["original_currency"] = "EUR"

    df["institution"] = "ABN"

    # Placeholders for now
    df["movement_type"] = None
    df["category"] = None
    df["subcategory"] = None

    return df
