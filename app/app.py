import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Personal Finance App", layout="wide")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.db.schema import init_db
init_db()

pages = {
    "Main": [
        st.Page("pages/overview.py", title="Overview"),
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
