from pathlib import Path
import re  # needed for catching regex errors
import pandas as pd

# Project root: personal_finance_app
ROOT_DIR = Path(__file__).resolve().parents[2]

# Path to the external rules file (root/config/categories_rules.csv)
RULES_PATH = ROOT_DIR / "config" / "categories_rules.csv"



def load_category_rules() -> pd.DataFrame:
    """Load category rules from CSV and normalize match column."""
    rules = pd.read_csv(RULES_PATH)

    # Ensure required columns exist
    expected_cols = {"match", "category", "subcategory"}
    missing = expected_cols - set(rules.columns)
    if missing:
        raise ValueError(f"Missing columns in rules file: {missing}")

    rules["match"] = rules["match"].astype(str).str.upper()
    rules["category"] = rules["category"].astype(str)
    rules["subcategory"] = rules["subcategory"].astype(str)
    return rules


def apply_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add transaction_type, category and subcategory columns to the DataFrame
    based on description and external rules file.
    - transaction_type: 'Income' if original_amount > 0 else 'Expense'
    - category / subcategory: filled using substring matches from rules
    """
    rules = load_category_rules()

    desc_col = "description_cleaned"
    amount_col = "original_amount"

    if desc_col not in df.columns:
        raise KeyError(f"Column '{desc_col}' not found in DataFrame")
    if amount_col not in df.columns:
        raise KeyError(f"Column '{amount_col}' not found in DataFrame")

    df = df.copy()
    df["description_upper"] = df[desc_col].astype(str).str.upper().fillna("")

    df["transaction_type"] = df[amount_col].apply(
        lambda x: "Income" if x > 0 else "Expense"
    )
    df["category"] = None
    df["subcategory"] = None

    # DEBUG: print each pattern before applying
    for idx, rule in rules.iterrows():
        raw_pattern = rule["match"]

        if pd.isna(raw_pattern):
            continue

        pattern = str(raw_pattern).upper()
        print(f"Applying rule {idx}: pattern = {repr(pattern)}")

        try:
            mask = df["description_upper"].str.contains(pattern, na=False, regex=False)
        except Exception as e:
            # print problematic pattern and re-raise to ver no log
            print(f"ERROR on pattern {idx}: {repr(pattern)} -> {e}")
            raise

        category = rule["category"]
        subcategory = rule["subcategory"]

        category = None if pd.isna(category) or category == "" else str(category)
        subcategory = None if pd.isna(subcategory) or subcategory == "" else str(subcategory)

        df.loc[mask, "category"] = category
        df.loc[mask, "subcategory"] = subcategory

    df = df.drop(columns=["description_upper"])
    return df


def append_rule(match: str, category: str, subcategory: str) -> None:
    """
    Append a new categorization rule to the CSV file.

    The 'match' text is stored in upper case, consistent with load_category_rules().
    If the file does not exist yet, it will be created.
    """
    match = str(match).strip().upper()
    category = str(category).strip()
    subcategory = str(subcategory).strip()

    if not match:
        raise ValueError("Match text cannot be empty.")

    new_row = pd.DataFrame(
        [{"match": match, "category": category, "subcategory": subcategory}]
    )

    if RULES_PATH.exists():
        rules = pd.read_csv(RULES_PATH)
        rules = pd.concat([rules, new_row], ignore_index=True)
    else:
        rules = new_row

    rules.to_csv(RULES_PATH, index=False)