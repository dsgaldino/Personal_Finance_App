import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make project root importable (…/personal_finance_app)
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.data.abn.load_abn import load_all_abn
from src.data.abn.transform_abn import abn_full_pipeline
from src.utils.categorization import load_category_rules, append_rule


st.title("🛠️ Edit Categories")

# =========================
# Load data for this page
# =========================
with st.spinner("Loading ABN data..."):
    abn_raw = load_all_abn()
    abn_final = abn_full_pipeline(
        abn_raw,
        apply_categorization=True,
        save_final=False,
    )

# Find uncategorized transactions
uncategorized = abn_final[
    (abn_final["CATEGORY"].isna())
    | (abn_final["CATEGORY"] == "")
    | (abn_final["CATEGORY"].astype(str).str.strip() == "")
].copy().reset_index(drop=True)

st.metric("📊 Uncategorized transactions", len(uncategorized))

if uncategorized.empty:
    st.success("✅ All transactions are categorized!")
    st.stop()

# =========================
# Filters
# =========================
col1, col2 = st.columns(2)
with col1:
    date_from = st.date_input("From", uncategorized["DATE"].min())
with col2:
    date_to = st.date_input("To", uncategorized["DATE"].max())

filtered_uncat = uncategorized[
    (uncategorized["DATE"] >= pd.Timestamp(date_from))
    & (uncategorized["DATE"] <= pd.Timestamp(date_to) + pd.Timedelta(days=1))
].reset_index(drop=True)

st.subheader("Select transaction to categorize")

table = filtered_uncat[["DATE", "DESCRIPTION", "AMOUNT"]].copy()
table["AMOUNT"] = table["AMOUNT"].map(lambda x: f"€ {x:,.2f}")

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
)

row_idx = st.number_input(
    "Row index to edit (0-based, see table order above)",
    min_value=0,
    max_value=max(0, len(filtered_uncat) - 1),
    step=1,
    value=0,
)

selected_tx = filtered_uncat.iloc[int(row_idx)]

# =========================
# Transaction details card
# =========================
st.subheader("✏️ Categorize selected transaction")

with st.container(border=True):
    st.markdown("**Transaction details**")

    d1, d2 = st.columns(2)
    with d1:
        st.write("**Date**")
        st.write(
            selected_tx["DATE"].strftime("%Y-%m-%d")
            if isinstance(selected_tx["DATE"], pd.Timestamp)
            else str(selected_tx["DATE"])
        )
    with d2:
        st.write("**Amount**")
        st.write(f"€ {selected_tx['AMOUNT']:,.2f}")

    st.write("**Description**")
    st.write(str(selected_tx["DESCRIPTION"]))

    if "DETAILS" in selected_tx.index:
        st.write("**Details**")
        st.code(str(selected_tx["DETAILS"]), language="text")

# =========================
# Categorization form
# =========================
st.markdown("---")

c1, c2 = st.columns([1, 1])

with c1:
    match_text = st.text_input(
        "Match text",
        value=selected_tx.get(
            "SHORT_DESCRIPTION",
            str(selected_tx["DESCRIPTION"])[:40],
        ),
        help="Text pattern that will be used to match similar transactions",
    )

with c2:
    rules = load_category_rules()
    categories = sorted(set(rules["category"].dropna().astype(str)))

    category = st.selectbox(
        "Category",
        options=categories,
        help="Main category for this transaction",
    )

    existing_subcats = sorted(
        set(
            rules.loc[
                rules["category"] == category, "subcategory"
            ].dropna().astype(str)
        )
    )

    mode = st.radio(
        "Subcategory mode",
        options=["Choose existing", "Create new"],
        horizontal=True,
    )

    if mode == "Choose existing" and existing_subcats:
        subcategory = st.selectbox(
            "Subcategory",
            options=existing_subcats,
            help="Choose one of the existing subcategories",
        )
    else:
        subcategory = st.text_input(
            "New subcategory",
            value="",
            placeholder="e.g. Restaurants, Supermarket, Bills",
            help="Type a new subcategory name",
        )

# =========================
# Save actions
# =========================
st.markdown("### 💾 Save")

if st.button("Create rule", type="primary", use_container_width=True):
    if match_text and category and subcategory:
        try:
            append_rule(match_text, category, subcategory)
            st.success("✅ Rule saved. Re-run the main page to apply it.")
        except Exception as e:
            st.error(f"Error saving rule: {e}")
    else:
        st.error("Fill match, category and subcategory.")

if st.button("🔄 Refresh data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
