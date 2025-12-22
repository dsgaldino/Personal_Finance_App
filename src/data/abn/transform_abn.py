"""
ABN full transform: raw → account mapping → standardize → categorize → short_description → final schema → save CSV.

Output CSV:
C:\\Users\\dsgal\\Documents\\Finanças\\personal_finance_app\\data\\processed\\abn_transactions_final.csv
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd
import re

from src.data.abn.load_abn import load_abn
from src.utils.categorization import apply_categories


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_ROOT = Path(r"C:\Users\dsgal\Documents\Finanças\personal_finance_app")
ACCOUNT_MAPPING_PATH = PROJECT_ROOT / "config" / "account_mapping.csv"
PROCESSED_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "abn_transactions_final.csv"


# =============================================================================
# 1) ACCOUNT MAPPING
# =============================================================================

def load_account_mapping(path: Path = ACCOUNT_MAPPING_PATH) -> pd.DataFrame:
    """
    Load account_number -> account_name mapping from CSV.

    Expected columns: account_number, account_name
    Graceful fallback: returns empty mapping if file doesn't exist.
    """
    if not path.exists():
        print(f"⚠️  Account mapping not found: {path} (using raw account numbers)")
        return pd.DataFrame(columns=["account_number", "account_name"])

    df = pd.read_csv(path, dtype={"account_number": str, "account_name": str})
    required = {"account_number", "account_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Account mapping invalid. Missing columns: {missing}")

    df["account_number"] = df["account_number"].astype(str).str.strip()
    df["account_name"] = df["account_name"].astype(str).str.strip()
    return df


def apply_account_mapping(df: pd.DataFrame, account_map: pd.DataFrame) -> pd.DataFrame:
    """
    Replace account numbers with friendly names where available.

    Requires raw df column: accountNumber
    """
    df = df.copy()

    if "accountNumber" not in df.columns:
        raise KeyError("Expected column 'accountNumber' not found in ABN raw DataFrame")

    df["accountNumber"] = df["accountNumber"].astype(str).str.strip()

    if account_map.empty:
        return df

    df = df.merge(
        account_map,
        how="left",
        left_on="accountNumber",
        right_on="account_number",
    )

    df["accountNumber"] = df["account_name"].fillna(df["accountNumber"])
    return df.drop(columns=["account_number", "account_name"], errors="ignore")


# =============================================================================
# 2) STANDARDIZE RAW ABN COLUMNS
# =============================================================================

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename ABN columns to intermediate schema:
      Account, Currency, Date, Value, Description
    """
    df = df.copy()

    rename_map = {
        "accountNumber": "Account",
        "mutationcode": "Currency",
        "transactiondate": "Date",
        "amount": "Value",
        "description": "Description",
    }
    df = df.rename(columns=rename_map)

    # Drop ABN fields if present
    df = df.drop(columns=["valuedate", "startsaldo", "endsaldo"], errors="ignore")

    required = {"Account", "Currency", "Date", "Value", "Description"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing required standardized columns: {missing}")

    df["Account"] = df["Account"].astype(str).str.strip()
    df["Currency"] = df["Currency"].astype(str).str.strip().str.upper()

    # ABN dates are like 20250316 (YYYYMMDD)
    df["Date"] = pd.to_datetime(df["Date"].astype(str), format="%Y%m%d", errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["Description"] = df["Description"].astype(str)

    return df


# =============================================================================
# 3) PREPARE FOR CATEGORIZATION MODULE
# =============================================================================

def clean_description_for_matching(description_series: pd.Series) -> pd.Series:
    """Uppercase + remove newlines + collapse spaces (for consistent matching)."""
    s = description_series.astype(str)
    s = s.str.replace(r"\s*\n\s*", " ", regex=True)
    s = s.str.replace(r"\s+", " ", regex=True)
    s = s.str.strip().str.upper()
    return s


def prepare_for_categorization(df_clean: pd.DataFrame) -> pd.DataFrame:
    """
    Build the schema expected by apply_categories():
      date, description, original_amount, original_currency, account_source, institution
    """
    return pd.DataFrame(
        {
            "date": df_clean["Date"],
            "description": clean_description_for_matching(df_clean["Description"]),
            "original_amount": df_clean["Value"],
            "original_currency": df_clean["Currency"],
            "account_source": df_clean["Account"],
            "institution": "ABN AMRO",
        }
    )


# =============================================================================
# 5) FINAL SCHEMA (stays before short_description block, as you requested)
# =============================================================================

def finalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Rename to YOUR exact column names + exact order."""
    rename_map = {
        "date": "DATE",
        "institution": "INSTITUTION",
        "account_source": "ACCOUNT",
        "transaction_type": "TRANSACTION",
        "category": "CATEGORY",
        "subcategory": "SUBCATEGORY",
        "short_description": "DESCRIPTION",
        "original_amount": "AMOUNT",
        "original_currency": "CURRENCY",
        "description": "DETAILS",
    }
    df = df.rename(columns=rename_map)

    exact_order = [
        "DATE",
        "INSTITUTION",
        "ACCOUNT",
        "TRANSACTION",
        "CATEGORY",
        "SUBCATEGORY",
        "DESCRIPTION",
        "AMOUNT",
        "CURRENCY",
        "DETAILS",
    ]
    return df.reindex(columns=exact_order)


# =============================================================================
# 4) SHORT DESCRIPTION PROCESSORS (after finalize_schema, before pipeline)
# =============================================================================

def _normalize_simple(s: str) -> str:
    """Uppercase, remove dot/comma punctuation, collapse spaces."""
    if not isinstance(s, str):
        return ""
    t = s.upper()
    t = re.sub(r"[.,]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def process_abn_hypotheek(description: str) -> str:
    """
    If Description == ABN AMRO BANK NV (accept punctuation like N.V.),
    return ABN AMRO BANK NV - HYPOTHEEK.
    """
    norm = _normalize_simple(description)
    if norm == "ABN AMRO BANK NV":
        return "ABN AMRO BANK NV - HYPOTHEEK"
    return description


def process_credit_interest(description: str) -> str:
    """If contains CREDIT INTEREST, remove everything after it (keep only the phrase)."""
    if not isinstance(description, str):
        return description

    m = re.search(r"(CREDIT\s+INTEREST)", description.upper())
    if not m:
        return description

    end = m.end(1)
    return description[:end].strip()


def process_tikkie_id(description: str) -> str:
    """
    Original Tikkie treatment: Extract AUX (NAME) format.
    Example: "... TIKKIE ID ..., KART, VAN JOHN DOE, IBAN..." → "KART (JOHN DOE)"
    """
    if not isinstance(description, str) or "TIKKIE ID" not in description.upper():
        return description

    parts = description.split("TIKKIE ID", 1)
    if len(parts) < 2:
        return description
    after = parts[1].strip()

    if ", " not in after:
        return description
    after = after.split(", ", 1)[1].strip()

    upper_after = after.upper()
    if ", VAN" not in upper_after:
        return description
    idx_van = upper_after.find(", VAN")
    aux = after[:idx_van].strip()

    resto = after[idx_van + 6 :].strip()  # ", VAN" = 6 chars
    name = resto.split(", ", 1)[0].strip() if ", " in resto else resto.strip()

    return f"{aux} ({name})"


def process_tikkie_sepa_ideal(description: str) -> str:
    """
    SEPA iDEAL via Tikkie:
      - Name: between 'NAAM:' and 'VIA TIKKIE'
      - Label: between 'OMSCHRIJVING:' and 'KENMERK:' (or end)
        -> remove numbers
        -> remove IBAN-like chunks starting with NL
        -> pick FIRST remaining word (>=3 letters)
      - Output: LABEL (NAME)
    """
    if not isinstance(description, str):
        return description

    u = description.upper()
    if "NAAM:" not in u or "VIA TIKKIE" not in u or "OMSCHRIJVING:" not in u:
        return description

    # 1) NAME
    naam_start = u.find("NAAM:") + len("NAAM:")
    via_pos = u.find("VIA TIKKIE", naam_start)
    if via_pos == -1:
        return description
    name_clean = re.sub(r"\s+", " ", description[naam_start:via_pos]).strip()

    # 2) OMSCHRIJVING block
    oms_start = u.find("OMSCHRIJVING:", via_pos) + len("OMSCHRIJVING:")
    if oms_start < len("OMSCHRIJVING:"):
        return description

    kenmerk_pos = u.find("KENMERK:", oms_start)
    oms_raw = description[oms_start:kenmerk_pos].strip() if kenmerk_pos != -1 else description[oms_start:].strip()
    oms_u = oms_raw.upper()

    # Remove long numeric blocks
    oms_u = re.sub(r"\d+", " ", oms_u)

    # Remove IBAN-like chunks (NL + letters/numbers)
    # examples: NL39ABNA0102421188, NL13ABNA0506417344
    oms_u = re.sub(r"\bNL[0-9A-Z]{6,}\b", " ", oms_u)

    # Collapse spaces
    oms_u = re.sub(r"\s+", " ", oms_u).strip()

    # Extract candidate words
    words = re.findall(r"\b[A-Z]{3,}\b", oms_u)

    # Remove noise words
    stop = {"ABNA", "IBAN", "BIC", "SEPA", "IDEAL", "TIKKIE", "VIA", "KENMERK", "OMSCHRIJVING", "NL"}
    words = [w for w in words if w not in stop]

    if not words:
        return description

    label = words[0]  # FIRST meaningful word => FEIRA

    return f"{label} ({name_clean})"




def process_apple_pay(description: str) -> str:
    """Apple Pay: remove prefixes and truncate at ',PAS'."""
    if not isinstance(description, str):
        return description

    t = description
    prefixes = [
        "BEA, APPLE PAY ",
        "BEA, Apple Pay ",
        "ECOM, APPLE PAY ",
        "ECOM, Apple Pay ",
        "eCom, Apple Pay ",
    ]
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):]
            break

    if ",PAS" in t:
        t = t.split(",PAS", 1)[0]

    return re.sub(r"\s+", " ", t).strip()


def process_sepa_slash_name(description: str) -> str:
    """SEPA /NAME/ rule: extract between /NAME/ and next /."""
    if not isinstance(description, str) or "/NAME/" not in description:
        return description

    t = description.split("/NAME/", 1)[1]
    if "/" in t:
        t = t.split("/", 1)[0]
    return re.sub(r"\s+", " ", t.strip(" /")).strip()


def process_sepa_naam_machtiging(description: str) -> str:
    """SEPA NAAM rule: extract between 'NAAM:' and 'MACHTIGING:'."""
    if not isinstance(description, str):
        return description

    u = description.upper()
    if "NAAM:" not in u or "MACHTIGING:" not in u:
        return description

    naam_start = u.find("NAAM:") + len("NAAM:")
    end_pos = u.find("MACHTIGING:", naam_start)
    if naam_start < len("NAAM:") or end_pos == -1:
        return description

    name_raw = description[naam_start:end_pos].strip()
    return re.sub(r"\s+", " ", name_raw).strip()


def process_sepa_naam_omschrijving(description: str) -> str:
    """SEPA NAAM rule: extract between 'NAAM:' and 'OMSCHRIJVING:'."""
    if not isinstance(description, str):
        return description

    u = description.upper()
    if "NAAM:" not in u or "OMSCHRIJVING:" not in u:
        return description

    naam_start = u.find("NAAM:") + len("NAAM:")
    end_pos = u.find("OMSCHRIJVING:", naam_start)
    if naam_start < len("NAAM:") or end_pos == -1:
        return description

    name_raw = description[naam_start:end_pos].strip()
    return re.sub(r"\s+", " ", name_raw).strip()


def process_gea_betaalpas(description: str) -> str:
    """GEA, BETAALPAS: extract store/address before ',PAS'."""
    if not isinstance(description, str) or not description.upper().startswith("GEA, BETAALPAS"):
        return description

    if ",PAS" in description:
        return description.split(",PAS", 1)[0].replace("GEA, BETAALPAS ", "").strip()
    return description


def process_basic_package(description: str) -> str:
    """ABN BASIC PACKAGE: normalize to BASIC PACKAGE."""
    if not isinstance(description, str):
        return description
    if "BASIC PACKAGE" in description.upper():
        return "BASIC PACKAGE"
    return description


def process_revolut(description: str) -> str:
    """REVOLUT: normalize to REVOLUT."""
    if not isinstance(description, str):
        return description
    if description.upper().startswith("REVOLUT"):
        return "REVOLUT"
    return description


def generate_short_descriptions(df: pd.DataFrame) -> pd.Series:
    """
    Apply short description treatments in priority order.
    Expects df to have column: 'description' (categorization schema).
    """
    if "description" not in df.columns:
        raise KeyError("generate_short_descriptions expects column 'description' in DataFrame")

    descriptions = df["description"].astype(str).copy()

    processors = [
        (r"TIKKIE ID", process_tikkie_id, False),
        (r"SEPA\s+IDEAL.*VIA\s+TIKKIE", process_tikkie_sepa_ideal, True),
        (r"APPLE PAY", process_apple_pay, False),
        (r"/NAME/", process_sepa_slash_name, False),

        # Simple trigger; parsing happens inside functions
        (r"NAAM:", process_sepa_naam_machtiging, False),
        (r"NAAM:", process_sepa_naam_omschrijving, False),

        (r"ABN AMRO BANK", process_abn_hypotheek, False),
        (r"CREDIT INTEREST", process_credit_interest, False),
        (r"GEA, BETAALPAS", process_gea_betaalpas, False),
        (r"BASIC PACKAGE", process_basic_package, False),
        (r"REVOLUT", process_revolut, False),
    ]

    for pat, fn, is_regex in processors:
        mask = descriptions.str.contains(pat, case=False, na=False, regex=is_regex)
        if mask.any():
            descriptions.loc[mask] = descriptions.loc[mask].apply(fn)

    return descriptions


# =============================================================================
# 6) CSV SAVE/LOAD
# =============================================================================

def save_processed_csv(df: pd.DataFrame, csv_path: Path = PROCESSED_CSV_PATH) -> None:
    """Save processed DataFrame to CSV (creates directory if needed)."""
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)

    try:
        size_kb = csv_path.stat().st_size / 1024
        print(f"💾 Saved {len(df)} rows to: {csv_path} ({size_kb:.1f} KB)")
    except Exception:
        print(f"💾 Saved {len(df)} rows to: {csv_path}")


def load_processed_csv(csv_path: Path = PROCESSED_CSV_PATH) -> Optional[pd.DataFrame]:
    """Load cached processed CSV if exists."""
    csv_path = Path(csv_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return None


# =============================================================================
# 7) PIPELINE (PUBLIC) - ONLY ONE DEFINITION
# =============================================================================

def abn_full_pipeline(
    raw_df: Union[pd.DataFrame, Path, str],
    save_csv: bool = True,
    csv_path: Path = PROCESSED_CSV_PATH,
) -> pd.DataFrame:
    """
    Full ABN pipeline.

    Accepts:
      - DataFrame (from load_all_abn())
      - or Path/str to a single .xls file

    Returns final DataFrame with EXACT columns:
      DATE, INSTITUTION, ACCOUNT, TRANSACTION, CATEGORY, SUBCATEGORY,
      DESCRIPTION, AMOUNT, CURRENCY, DETAILS
    """
    print("🚀 Starting ABN Full Pipeline...")

    # Allow passing a file path (optional)
    if isinstance(raw_df, (str, Path)):
        abn_file_path = Path(raw_df)
        if not abn_file_path.exists():
            raise FileNotFoundError(f"ABN file not found: {abn_file_path}")
        df_raw = load_abn(abn_file_path)
        print(f"📥 Loaded from file: {abn_file_path} ({len(df_raw)} rows)")
    else:
        df_raw = raw_df
        print(f"📊 Using raw DataFrame: {len(df_raw)} rows")

    if not isinstance(df_raw, pd.DataFrame):
        raise TypeError("raw_df must be a pandas DataFrame, a Path, or a str path")

    account_map = load_account_mapping()
    df_clean = apply_account_mapping(df_raw, account_map)
    df_clean = standardize_columns(df_clean)

    df_cat = prepare_for_categorization(df_clean)
    df_cat = apply_categories(df_cat)

    df_cat["short_description"] = generate_short_descriptions(df_cat)

    df_final = finalize_schema(df_cat)

    if save_csv:
        save_processed_csv(df_final, csv_path=csv_path)

    print(f"✅ Pipeline complete: {len(df_final)} transactions")
    return df_final
