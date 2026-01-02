import sys
from pathlib import Path

import streamlit as st

# --- Ensure project root is importable before importing local packages ---
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.app_config import BRAND
from src.db.schema import init_db
from src.ui.branding import apply_global_css, inject_sidebar_nav_header

# --- Page config (must be first Streamlit command) ---
st.set_page_config(
    page_title=BRAND.name,
    page_icon=BRAND.icon_emoji,
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- DB init ---
init_db()

# --- UI (CSS + header above nav) ---
apply_global_css()
inject_sidebar_nav_header()

pages = {
    "Home": [
        st.Page("pages/overview.py", title="Overview"),
        st.Page("pages/dashboard.py", title="Dashboard"),
    ],
    "Transactions": [
        st.Page("pages/import_data.py", title="Import"),
        st.Page("pages/transactions_accounts.py", title="Accounts"),
        st.Page("pages/transactions_investments.py", title="Investments"),
    ],
    "Analytics": [
        st.Page("pages/analytics_accounts.py", title="Accounts"),
        st.Page("pages/analytics_investments.py", title="Investments"),
    ],
    "Settings": [
        st.Page("pages/settings_accounts.py", title="Accounts"),
        st.Page("pages/settings_categories.py", title="Categories / Rules"),
        st.Page("pages/settings_parameters.py", title="Parameters"),
    ],
}

pg = st.navigation(pages)
pg.run()
