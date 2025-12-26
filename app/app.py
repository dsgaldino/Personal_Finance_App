import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make project root importable (../ from app/)
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.data.abn.load_abn import load_all_abn
from src.data.abn.transform_abn import abn_full_pipeline


# =========================
# Main title
# =========================
st.title("Personal Finance App - ABN")

st.header("ABN real data")

# 1) Load raw ABN data from all .xls files
abn_raw = load_all_abn()
st.subheader("Raw ABN data (all files)")
st.dataframe(abn_raw.head(50))

# 2) Run full ABN pipeline (CORRIGIDO: SEM parâmetros extras)
abn_final = abn_full_pipeline(abn_raw)  # ← SÓ ISSO!

# ---- Presentation formatting for Streamlit table ----
abn_display = abn_final.copy()

# 1) Format DATE as YYYY-MM-DD
if pd.api.types.is_datetime64_any_dtype(abn_display["DATE"]):
    abn_display["DATE"] = abn_display["DATE"].dt.strftime("%Y-%m-%d")

# 2) Format AMOUNT with two decimals (European style 1.234,56)
abn_display["AMOUNT"] = (
    abn_display["AMOUNT"]
    .map(lambda x: f"{x:,.2f}")
    .str.replace(",", "X")
    .str.replace(".", ",")
    .str.replace("X", ".")
)

st.subheader("Processed ABN data (final schema)")
st.dataframe(abn_display.head(200), use_container_width=True)
