from __future__ import annotations

import pandas as pd
import streamlit as st

from src.db.connection import get_conn
from src.db.parameters_repo import get_parameters, upsert_parameters


st.title("Settings · Parameters")

conn = get_conn()

df = get_parameters(conn)
if df.empty:
    df = pd.DataFrame(
        [
            {"key": "emergency_fund_months", "value": "6"},
            {"key": "invest_percent_income", "value": "15"},
            {"key": "target_savings_rate", "value": "20"},
        ]
    )

st.caption("Simple key/value settings (stored in SQLite).")
edited = st.data_editor(
    df[["key", "value"]],
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
)

if st.button("Save parameters", type="primary"):
    edited = edited.copy()
    edited["key"] = edited["key"].astype(str).str.strip()
    edited["value"] = edited["value"].astype(str).str.strip()
    edited = edited[edited["key"] != ""]
    n = upsert_parameters(conn, edited)
    st.success(f"Saved/updated: {n} rows")
