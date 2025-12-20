import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make project root importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Imports from src
from src.data.loaders import load_abn_example  # example data
from src.data.load_abn import load_abn        # novo loader ABN
from src.data.transformers import standardize_transactions
from src.utils.categorization import apply_categories

st.title("Personal Finance App - MVP")

# ---------------------------------------------------------------------
# ABN example data
# ---------------------------------------------------------------------
st.header("ABN example data")

raw_df = load_abn_example()
std_df = standardize_transactions(raw_df)
cat_df = apply_categories(std_df)

st.subheader("Raw data")
st.dataframe(raw_df)

st.subheader("Standardized data")
st.dataframe(std_df)

st.subheader("Categorized data")
st.dataframe(cat_df)

# ---------------------------------------------------------------------
# ABN real data (raw test)
# ---------------------------------------------------------------------
st.header("ABN real data (raw test)")

abn_filename = "abn_real.xls"  # ajuste para o nome exato do arquivo

# 1) Load raw (ABN-specific)
abn_raw = load_abn(abn_filename)

# 2) Standardize (ainda usando standardize_transactions)
abn_std = standardize_transactions(abn_raw)

# 3) Categorize
abn_cat = apply_categories(abn_std)