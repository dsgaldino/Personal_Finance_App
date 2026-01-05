from __future__ import annotations

from pathlib import Path
import pandas as pd


RULES_PATH = Path("config/categories_rules.csv")


def load_category_rules() -> pd.DataFrame:
    rules = pd.read_csv(RULES_PATH)

    expected_cols = {"match", "category", "subcategory"}
    missing = expected_cols - set(rules.columns)
    if missing:
        raise ValueError(f"Missing columns in rules file: {sorted(missing)}")

    rules = rules.copy()
    rules["match"] = rules["match"].astype(str).str.upper().str.strip()
    rules["category"] = rules["category"].astype(str).str.strip()
    rules["subcategory"] = rules["subcategory"].astype(str).str.strip()

    # ignora linhas vazias
    rules = rules[rules["match"].astype(bool)]
    return rules


def apply_categories_to_cleaned(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expects columns:
      - transaction_id
      - description_cleaned
      - amount (optional; only used if you want type-based logic later)
    Returns df with:
      - category_auto
      - subcategory_auto
    """
    rules = load_category_rules()

    if "transaction_id" not in df.columns:
        raise KeyError("Column 'transaction_id' not found")
    if "description_cleaned" not in df.columns:
        raise KeyError("Column 'description_cleaned' not found")

    out = df.copy()

    out["desc_upper"] = out["description_cleaned"].astype(str).str.upper().fillna("")
    out["category_auto"] = None
    out["subcategory_auto"] = None

    # primeira regra que casar “ganha”
    for _, rule in rules.iterrows():
        pattern = rule["match"]
        mask = out["desc_upper"].str.contains(pattern, na=False, regex=False)
        out.loc[mask & out["category_auto"].isna(), "category_auto"] = rule["category"]
        out.loc[mask & out["subcategory_auto"].isna(), "subcategory_auto"] = rule["subcategory"]

    return out.drop(columns=["desc_upper"])

def get_category_options(rules: pd.DataFrame) -> list[str]:
    cats = sorted(set(rules["category"].dropna().astype(str).str.strip()))
    return [""] + cats  # "" = None (sem override)


def get_subcategory_options(rules: pd.DataFrame) -> list[str]:
    subs = sorted(set(rules["subcategory"].dropna().astype(str).str.strip()))
    return [""] + subs  # "" = None (sem override)

def apply_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply category rules to a standardized transactions DataFrame (UI usage).

    Expected columns:
      - description
      - original_amount

    Adds:
      - transaction_type
      - category
      - subcategory
    """
    rules = load_category_rules()

    if "description" not in df.columns:
        raise KeyError("Column 'description' not found")
    if "original_amount" not in df.columns:
        raise KeyError("Column 'original_amount' not found")

    out = df.copy()

    out["transaction_type"] = out["original_amount"].apply(
        lambda x: "Income" if pd.notna(x) and float(x) > 0 else "Expense"
    )

    desc_upper = out["description"].astype(str).str.upper().fillna("")
    out["category"] = None
    out["subcategory"] = None

    for _, rule in rules.iterrows():
        pattern = rule["match"]
        mask = desc_upper.str.contains(pattern, na=False, regex=False)
        out.loc[mask & out["category"].isna(), "category"] = rule["category"]
        out.loc[mask & out["subcategory"].isna(), "subcategory"] = rule["subcategory"]

    return out
