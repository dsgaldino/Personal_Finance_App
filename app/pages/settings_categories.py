from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

from src.utils.categorization import RULES_PATH


st.title("Settings · Categories / Rules")

rules_path = Path(RULES_PATH)

if not rules_path.exists():
    st.warning(f"Rules file not found: {rules_path}. Creating a new one.")
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=["match", "category", "subcategory"]).to_csv(rules_path, index=False)

rules = pd.read_csv(rules_path).fillna("")

st.caption("Edit the rules. Order matters: put more specific matches above generic ones.")
edited = st.data_editor(
    rules,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
)

c1, c2, c3 = st.columns(3)

with c1:
    if st.button("Save rules", type="primary"):
        out = edited.copy()
        for col in ["match", "category", "subcategory"]:
            if col not in out.columns:
                st.error(f"Missing column: {col}")
                st.stop()
            out[col] = out[col].astype(str).str.strip()

        # remove empty match rows
        out = out[out["match"] != ""]
        out.to_csv(rules_path, index=False)
        st.success(f"Saved: {rules_path}")

with c2:
    st.download_button(
        "Download rules CSV",
        data=edited.to_csv(index=False).encode("utf-8"),
        file_name="categories_rules.csv",
        mime="text/csv",
    )

with c3:
    if st.button("Reload"):
        st.rerun()
