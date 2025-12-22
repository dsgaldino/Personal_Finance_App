from pathlib import Path
import pandas as pd

# Project root: personal_finance_app (…/personal_finance_app/src/data/abn/load_abn.py -> sobe 3 níveis)
ROOT_DIR = Path(__file__).resolve().parents[3]

# Base directory for real ABN files (always under project root)
REAL_DATA_DIR = ROOT_DIR / "data" / "real" / "abn"


def load_abn(filename: str) -> pd.DataFrame:
    """
    Load a single raw ABN statement from an XLS file and return a DataFrame
    exactly as read from Excel (no standardization).
    """
    file_path = REAL_DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"ABN file not found: {file_path}")

    df = pd.read_excel(file_path, header=0, engine="xlrd")
    return df


def load_all_abn() -> pd.DataFrame:
    """
    Load and concatenate all ABN .xls files in data/real/abn.

    This allows you to drop many monthly statements into the folder and
    process them as a single DataFrame.
    """
    files = sorted(REAL_DATA_DIR.glob("*.xls"))

    if not files:
        raise FileNotFoundError(f"No ABN .xls files found in {REAL_DATA_DIR}")

    dfs = [pd.read_excel(f, header=0, engine="xlrd") for f in files]
    df_all = pd.concat(dfs, ignore_index=True)
    return df_all
