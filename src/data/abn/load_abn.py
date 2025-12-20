from pathlib import Path
import pandas as pd


# Base directory for real ABN files
REAL_DATA_DIR = Path("data/real/abn")


def load_abn(filename: str) -> pd.DataFrame:
    """
    Load raw ABN statement from XLS file and return a DataFrame
    exactly as read from Excel (no standardization).
    """
    file_path = REAL_DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"ABN file not found: {file_path}")

    df = pd.read_excel(file_path, header=0, engine="xlrd")
    return df

