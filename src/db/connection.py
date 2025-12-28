from pathlib import Path
import sqlite3
import streamlit as st

from src.db.schema import DB_PATH, init_db


@st.cache_resource
def get_conn() -> sqlite3.Connection:
    init_db(DB_PATH)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
