# app/pages/transactions_accounts.py
from __future__ import annotations

import sqlite3
import uuid
import datetime as dt

import pandas as pd
import streamlit as st

from src.db.connection import get_conn


NONE_LABEL = "None"
DEFAULT_LIMIT = 200000


def _final_expr(col_user: str, col_auto: str) -> str:
    return f"COALESCE(NULLIF(TRIM({col_user}), ''), {col_auto})"


def _to_none_if_blank(x: str | None) -> str | None:
    x = (x or "").strip()
    return x or None


@st.cache_data(show_spinner=False)
def _load_accounts(_conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT account_id, account_name, institution, currency
        FROM accounts
        ORDER BY institution, account_name
        """,
        _conn,
    )


@st.cache_data(show_spinner=False)
def _load_filter_options(_conn: sqlite3.Connection) -> dict[str, list[str]]:
    df = pd.read_sql_query(
        """
        SELECT DISTINCT
            institution,
            currency,
            transaction_type,
            account_id
        FROM transactions
        """,
        _conn,
    )

    def _sorted(col: str) -> list[str]:
        return sorted(v for v in df[col].dropna().astype(str).unique().tolist() if v.strip())

    return {
        "institution": _sorted("institution"),
        "currency": _sorted("currency"),
        "transaction_type": _sorted("transaction_type"),
        "account_id": _sorted("account_id"),
    }


@st.cache_data(show_spinner=False)
def _load_category_values(_conn: sqlite3.Connection) -> tuple[list[str], list[str]]:
    df = pd.read_sql_query(
        f"""
        SELECT
            {_final_expr('category_user', 'category_auto')} AS category_final,
            {_final_expr('subcategory_user', 'subcategory_auto')} AS subcategory_final
        FROM transactions
        """,
        _conn,
    )

    cats = sorted(v for v in df["category_final"].dropna().astype(str).unique().tolist() if v.strip())
    subs = sorted(v for v in df["subcategory_final"].dropna().astype(str).unique().tolist() if v.strip())
    return cats, subs


def _split_none(values: list[str]) -> tuple[list[str], bool]:
    include_nulls = NONE_LABEL in values
    clean = [v for v in values if v != NONE_LABEL]
    return clean, include_nulls


def _build_where_clause(filters: dict) -> tuple[str, dict]:
    clauses: list[str] = []
    params: dict[str, object] = {}

    cat_final = _final_expr("t.category_user", "t.category_auto")
    sub_final = _final_expr("t.subcategory_user", "t.subcategory_auto")
    desc_final = _final_expr("t.description_user", "t.description_cleaned")

    if filters["date_start"] is not None:
        clauses.append("t.date >= :date_start")
        params["date_start"] = str(filters["date_start"])
    if filters["date_end"] is not None:
        clauses.append("t.date <= :date_end")
        params["date_end"] = str(filters["date_end"])

    def _in_clause(values: list[str], prefix: str) -> str:
        return "(" + ",".join([f":{prefix}_{i}" for i in range(len(values))]) + ")"

    if filters["institution"]:
        clauses.append("t.institution IN " + _in_clause(filters["institution"], "inst"))
        for i, v in enumerate(filters["institution"]):
            params[f"inst_{i}"] = v

    if filters["currency"]:
        clauses.append("t.currency IN " + _in_clause(filters["currency"], "cur"))
        for i, v in enumerate(filters["currency"]):
            params[f"cur_{i}"] = v

    if filters["transaction_type"]:
        clauses.append("t.transaction_type IN " + _in_clause(filters["transaction_type"], "typ"))
        for i, v in enumerate(filters["transaction_type"]):
            params[f"typ_{i}"] = v

    if filters["account_id"]:
        clauses.append("t.account_id IN " + _in_clause(filters["account_id"], "acc"))
        for i, v in enumerate(filters["account_id"]):
            params[f"acc_{i}"] = v

    if filters["category"]:
        clean, include_nulls = _split_none(filters["category"])
        parts: list[str] = []
        if clean:
            parts.append(f"{cat_final} IN " + _in_clause(clean, "cat"))
            for i, v in enumerate(clean):
                params[f"cat_{i}"] = v
        if include_nulls:
            parts.append(f"{cat_final} IS NULL")
        if parts:
            clauses.append("(" + " OR ".join(parts) + ")")

    if filters["subcategory"]:
        clean, include_nulls = _split_none(filters["subcategory"])
        parts: list[str] = []
        if clean:
            parts.append(f"{sub_final} IN " + _in_clause(clean, "sub"))
            for i, v in enumerate(clean):
                params[f"sub_{i}"] = v
        if include_nulls:
            parts.append(f"{sub_final} IS NULL")
        if parts:
            clauses.append("(" + " OR ".join(parts) + ")")

    if filters["search"]:
        clauses.append(
            f"(UPPER({desc_final}) LIKE :q OR UPPER(t.description_cleaned) LIKE :q OR UPPER(t.details) LIKE :q)"
        )
        params["q"] = f"%{str(filters['search']).upper()}%"

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where_sql, params


@st.cache_data(show_spinner=False)
def _load_transactions(_conn: sqlite3.Connection, filters: dict, limit: int) -> pd.DataFrame:
    where_sql, params = _build_where_clause(filters)

    query = f"""
    SELECT
        t.transaction_id,
        t.date,
        a.account_name,
        t.amount,
        t.currency,
        {_final_expr('t.category_user', 't.category_auto')} AS category_final,
        {_final_expr('t.subcategory_user', 't.subcategory_auto')} AS subcategory_final,
        {_final_expr('t.description_user', 't.description_cleaned')} AS description_final
    FROM transactions t
    JOIN accounts a ON a.account_id = t.account_id
    {where_sql}
    ORDER BY t.date DESC
    LIMIT {int(limit)}
    """
    return pd.read_sql_query(query, _conn, params=params)


@st.cache_data(show_spinner=False)
def _load_transaction_detail(_conn: sqlite3.Connection, transaction_id: str) -> pd.Series:
    df = pd.read_sql_query(
        """
        SELECT
            transaction_id,
            date,
            institution,
            account_id,
            amount,
            currency,
            details,
            description_cleaned,
            description_user,
            transaction_type,
            category_auto,
            subcategory_auto,
            category_user,
            subcategory_user
        FROM transactions
        WHERE transaction_id = ?
        """,
        _conn,
        params=(transaction_id,),
    )
    if df.empty:
        raise ValueError("Transaction not found")
    return df.iloc[0]


def _update_transaction_user_fields(
    conn: sqlite3.Connection,
    transaction_id: str,
    *,
    description_user: str | None,
    category_user: str | None,
    subcategory_user: str | None,
) -> None:
    conn.execute(
        """
        UPDATE transactions
        SET
            description_user = ?,
            category_user = ?,
            subcategory_user = ?
        WHERE transaction_id = ?
        """,
        (description_user, category_user, subcategory_user, transaction_id),
    )
    conn.commit()


def _insert_transaction(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    date: str,
    institution: str,
    account_id: str,
    amount: float,
    currency: str,
    details: str,
    description_cleaned: str,
    transaction_type: str,
    category_user: str | None,
    subcategory_user: str | None,
    description_user: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO transactions (
            transaction_id,
            date,
            institution,
            account_id,
            amount,
            currency,
            details,
            description_cleaned,
            transaction_type,
            category_auto,
            subcategory_auto,
            category_user,
            subcategory_user,
            description_user
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
        """,
        (
            transaction_id,
            date,
            institution,
            account_id,
            amount,
            currency,
            details,
            description_cleaned,
            transaction_type,
            category_user,
            subcategory_user,
            description_user,
        ),
    )
    conn.commit()


def _delete_transaction(conn: sqlite3.Connection, transaction_id: str) -> None:
    conn.execute("DELETE FROM transactions WHERE transaction_id = ?", (transaction_id,))
    conn.commit()


def render() -> None:
    st.title("Transactions")

    conn = get_conn()

    # ---------- Top actions ----------
    col_add, col_del = st.columns([1, 1])

    with col_add:
        if st.button("Add new transaction", type="primary"):
            st.session_state["show_add_tx"] = True

    # Delete uses the currently selected tx (set later); keep UI here
    with col_del:
        st.session_state.setdefault("confirm_delete", False)
        st.session_state.setdefault("delete_clicked", False)

    # ---------- Add transaction panel ----------
    if st.session_state.get("show_add_tx", False):
        accounts = _load_accounts(conn)
        if accounts.empty:
            st.warning("Create an account first in Settings → Accounts.")
        else:
            cats, subs = _load_category_values(conn)

            with st.container(border=True):
                st.subheader("Add transaction")

                with st.form("add_tx_form", clear_on_submit=False):
                    # Defaults
                    today = dt.date.today().isoformat()

                    date = st.text_input("Date (YYYY-MM-DD)", value=today)
                    account_id = st.selectbox(
                        "Account",
                        options=accounts["account_id"].astype(str).tolist(),
                        format_func=lambda x: (
                            accounts.loc[accounts["account_id"].astype(str) == str(x), "account_name"].iloc[0]
                        ),
                    )

                    # institution/currency: prefill from selected account
                    acc_row = accounts.loc[accounts["account_id"].astype(str) == str(account_id)].iloc[0]
                    institution = st.text_input("Institution", value=str(acc_row["institution"]))
                    currency = st.text_input("Currency", value=str(acc_row["currency"]))

                    amount = st.number_input("Amount", value=0.00, format="%.2f")
                    transaction_type = st.selectbox("Type", options=["Expense", "Income"], index=0)

                    description = st.text_input("Description", value="")
                    details = st.text_area("Details", value="", height=80)

                    # category/subcategory: can type new (accept_new_options) and also fallback inputs
                    category_options = [NONE_LABEL] + cats
                    subcategory_options = [NONE_LABEL] + subs

                    category_value = st.selectbox(
                        "Category",
                        options=category_options,
                        index=0,
                        accept_new_options=True,
                        placeholder="Select or type a new category...",
                    )
                    category_new = st.text_input("New category (optional)", value="")

                    subcategory_value = st.selectbox(
                        "Subcategory",
                        options=subcategory_options,
                        index=0,
                        accept_new_options=True,
                        placeholder="Select or type a new subcategory...",
                    )
                    subcategory_new = st.text_input("New subcategory (optional)", value="")

                    submit = st.form_submit_button("Create", type="primary")

                if submit:
                    tx_id = uuid.uuid4().hex

                    chosen_cat = _to_none_if_blank(category_new) or (
                        None if category_value == NONE_LABEL else _to_none_if_blank(category_value)
                    )
                    chosen_sub = _to_none_if_blank(subcategory_new) or (
                        None if subcategory_value == NONE_LABEL else _to_none_if_blank(subcategory_value)
                    )

                    # Use description as cleaned for manual inserts (simple & predictable)
                    desc_cleaned = description.strip()

                    _insert_transaction(
                        conn,
                        transaction_id=tx_id,
                        date=str(date).strip(),
                        institution=str(institution).strip(),
                        account_id=str(account_id).strip(),
                        amount=float(amount),
                        currency=str(currency).strip(),
                        details=str(details),
                        description_cleaned=desc_cleaned,
                        transaction_type=str(transaction_type),
                        category_user=chosen_cat,
                        subcategory_user=chosen_sub,
                        description_user=_to_none_if_blank(description),
                    )

                    st.success("Transaction created.")
                    st.session_state["show_add_tx"] = False
                    st.cache_data.clear()
                    st.rerun()

    # ---------- Filters ----------
    opts = _load_filter_options(conn)
    cats, subs = _load_category_values(conn)

    cat_filter_options = [NONE_LABEL] + cats
    sub_filter_options = [NONE_LABEL] + subs

    with st.expander("Filters", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            date_range = st.date_input("Date range", value=())
        with c2:
            account_id = st.multiselect("Account", options=opts["account_id"], default=[])

        c3, c4, c5 = st.columns(3)
        with c3:
            institution = st.multiselect("Institution", options=opts["institution"], default=[])
        with c4:
            currency = st.multiselect("Currency", options=opts["currency"], default=[])
        with c5:
            transaction_type = st.multiselect("Type", options=opts["transaction_type"], default=[])

        c6, c7 = st.columns(2)
        with c6:
            category = st.multiselect("Category", options=cat_filter_options, default=[])
        with c7:
            subcategory = st.multiselect("Subcategory", options=sub_filter_options, default=[])

        search = st.text_input("Search", value="", placeholder="Search description/details...")

    date_start = None
    date_end = None
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        date_start, date_end = date_range[0], date_range[1]

    filters = {
        "date_start": date_start,
        "date_end": date_end,
        "institution": institution,
        "currency": currency,
        "transaction_type": transaction_type,
        "account_id": account_id,
        "category": category,
        "subcategory": subcategory,
        "search": (search or "").strip(),
    }

    tx = _load_transactions(conn, filters, limit=DEFAULT_LIMIT)
    if tx.empty:
        st.info("No transactions found for the selected filters.")
        return

    table = tx.rename(
        columns={
            "date": "Date",
            "account_name": "Account Name",
            "amount": "Amount",
            "currency": "Currency",
            "category_final": "Category",
            "subcategory_final": "Subcategory",
            "description_final": "Description",
        }
    )

    event = st.dataframe(
        table[["Date", "Account Name", "Amount", "Currency", "Category", "Subcategory", "Description"]],
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        column_config={
            "Date": {"alignment": "center"},
            "Account Name": {"alignment": "center"},
            "Amount": st.column_config.NumberColumn(format="%.2f"),
            "Currency": {"alignment": "center"},
            "Category": {"alignment": "center"},
            "Subcategory": {"alignment": "center"},
        },
    )

    selected_idx = None
    try:
        selected_idx = event.selection.rows[0] if event.selection.rows else None
    except Exception:
        selected_idx = None

    selected_transaction_id = None
    if selected_idx is not None:
        selected_transaction_id = str(tx.iloc[selected_idx]["transaction_id"])

    # ---------- Delete button (needs selection) ----------
    st.divider()
    del_col1, del_col2, del_col3 = st.columns([1, 1, 4])

    with del_col1:
        delete_clicked = st.button("Delete selected", disabled=(selected_transaction_id is None))
    with del_col2:
        confirm_delete = st.checkbox("Confirm", value=False, disabled=(selected_transaction_id is None), key="confirm_del_tx")
    with del_col3:
        if selected_transaction_id is None:
            st.caption("Select a transaction to enable delete.")
        else:
            st.caption(f"Selected: {selected_transaction_id}")

    if delete_clicked:
        if not confirm_delete:
            st.warning("Check Confirm to delete.")
        else:
            _delete_transaction(conn, selected_transaction_id)
            st.success("Deleted.")
            st.cache_data.clear()
            st.rerun()

    # ---------- Edit panel ----------
    if selected_transaction_id is None:
        return

    row = _load_transaction_detail(conn, selected_transaction_id)

    current_description = (
        (str(row["description_user"]).strip() if row["description_user"] else "")
        or str(row["description_cleaned"])
    )
    current_category = (
        (str(row["category_user"]).strip() if row["category_user"] else "")
        or (str(row["category_auto"]).strip() if row["category_auto"] else "")
    )
    current_subcategory = (
        (str(row["subcategory_user"]).strip() if row["subcategory_user"] else "")
        or (str(row["subcategory_auto"]).strip() if row["subcategory_auto"] else "")
    )

    category_options = [NONE_LABEL] + sorted(set(cats + ([current_category] if current_category else [])))
    subcategory_options = [NONE_LABEL] + sorted(set(subs + ([current_subcategory] if current_subcategory else [])))

    cat_index = category_options.index(current_category) if current_category in category_options else 0
    sub_index = subcategory_options.index(current_subcategory) if current_subcategory in subcategory_options else 0

    st.subheader("Edit")

    with st.form(f"edit_tx_{selected_transaction_id}", clear_on_submit=False):
        st.text_input("Transaction ID", value=str(row["transaction_id"]), disabled=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("Date", value=str(row["date"]), disabled=True)
            st.text_input("Account ID", value=str(row["account_id"]), disabled=True)
        with c2:
            st.text_input("Institution", value=str(row["institution"]), disabled=True)
            st.text_input("Type", value=str(row["transaction_type"]), disabled=True)
        with c3:
            st.text_input("Currency", value=str(row["currency"]), disabled=True)
            st.number_input("Amount", value=float(row["amount"]), disabled=True)

        st.text_area("Details", value=str(row["details"]), disabled=True, height=90)
        st.divider()

        description_value = st.text_input("Description", value=current_description)

        category_value = st.selectbox(
            "Category",
            options=category_options,
            index=cat_index,
            accept_new_options=True,
            placeholder="Select or type a new category...",
        )
        category_new = st.text_input("New category (optional)", value="")

        subcategory_value = st.selectbox(
            "Subcategory",
            options=subcategory_options,
            index=sub_index,
            accept_new_options=True,
            placeholder="Select or type a new subcategory...",
        )
        subcategory_new = st.text_input("New subcategory (optional)", value="")

        saved = st.form_submit_button("Save", type="primary")

    if saved:
        chosen_cat = _to_none_if_blank(category_new) or (
            None if category_value == NONE_LABEL else _to_none_if_blank(category_value)
        )
        chosen_sub = _to_none_if_blank(subcategory_new) or (
            None if subcategory_value == NONE_LABEL else _to_none_if_blank(subcategory_value)
        )

        _update_transaction_user_fields(
            conn,
            selected_transaction_id,
            description_user=_to_none_if_blank(description_value),
            category_user=chosen_cat,
            subcategory_user=chosen_sub,
        )
        st.success("Saved.")
        st.cache_data.clear()
        st.rerun()


render()
