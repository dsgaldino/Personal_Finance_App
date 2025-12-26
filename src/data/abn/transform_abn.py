import pandas as pd

from src.utils.cleaning import clean_basic_description, clean_tikkie_v2
from src.utils.categorization import apply_categories


def abn_full_pipeline(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Full ABN pipeline:
      1) start from raw ABN df (load_abn)
      2) ensure standard columns (DATE, AMOUNT, DESCRIPTION)
      3) apply description cleaning (clean_basic_description + clean_tikkie_v2)
      4) apply categorization rules
      5) return final schema for the app
    """
    df = df_raw.copy()

    # --- 2. Standard columns (ajuste conforme os nomes reais do ABN) ---
    # Exemplo típico ABN: 'Datum', 'Omschrijving', 'Bedrag'
    if "DATE" not in df.columns and "Datum" in df.columns:
        df["DATE"] = pd.to_datetime(df["Datum"])

    if "DESCRIPTION" not in df.columns and "Omschrijving" in df.columns:
        df["DESCRIPTION"] = df["Omschrijving"].astype(str)

    if "AMOUNT" not in df.columns and "Bedrag" in df.columns:
        df["AMOUNT"] = df["Bedrag"].astype(float)
        df["original_amount"] = df["AMOUNT"]

    # Garante coluna 'description' que a categorization espera renomear depois
    df["description"] = df["DESCRIPTION"].astype(str)

    # --- 3. Cleaning (description_cleaned) ---
    df["description_cleaned"] = df["description"].apply(clean_basic_description)

    mask_tikkie = df["description_cleaned"].str.contains("TIKKIE", na=False)
    if mask_tikkie.any():
        df_tikkie = df[mask_tikkie].copy()
        df_tikkie["description_cleaned"] = df_tikkie["description_cleaned"].apply(clean_tikkie_v2)
        df.loc[df_tikkie.index, "description_cleaned"] = df_tikkie["description_cleaned"]

    # --- 4. Categorization (usando description_cleaned) ---
    df_cat = df.copy()
    df_cat = df_cat.rename(columns={
        "description": "description_original",
        "description_cleaned": "description",
    })
    df_cat = apply_categories(df_cat)
    df_cat = df_cat.rename(columns={
        "description": "description_cleaned",
        "description_original": "description",
    })

    return df_cat
