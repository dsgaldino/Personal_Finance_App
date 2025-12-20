# Project Document – Personal Finance App

## 1. Overview

The **Personal Finance App** is a web application (Python + Streamlit) designed to track personal finances and investments in an integrated way, accessible via browser on desktop and mobile.

### 1.1. Main objectives

- Consolidate income, expenses, account balances and invested wealth into a single view, with filters by month, year, and full history.  
- Automatically calculate how much to invest each month, based on income and user‑defined percentages/amounts for different goals (long term, medium term, trips, short term, pets, crypto, etc.).  
- Monitor the target asset allocation by asset class (e.g. 60% stocks, 30% ETFs, 10% crypto) and suggest rebalancing actions when relevant deviations occur.  

### 1.2. Users and context

- Main users: the project owner and spouse, sharing a joint view of their finances.  
- Future: possibility to invite friends, each with their own account and isolated data.  
- Usage: online access with zero or very low cost, preferably via Streamlit Community Cloud connected to GitHub.  

## 2. MVP scope

The MVP focuses on a few essential features:

### 2.1. Data collection (monthly, via folder)

- Monthly ingestion of bank and brokerage statements from files placed in a configured folder.  
- Institutions covered in the MVP: ABN (accounts), Revolut (account), AMEX (credit card), Coinbase (crypto) and XP Investimentos (equities / fixed income).  

### 2.2. Unified data model

- Standardize all sources into a single transaction model with fields: date, description, account/source, transaction type, category, subcategory, amount, currency, asset, asset class.  

### 2.3. Budgeting and monthly investing rules

- Configure, via UI, the percentage of monthly income allocated to investments (e.g. 50%) and the internal split across goals (“buckets”) such as long‑term, medium‑term, fixed amount for trips, etc.  
- Automatically compute the recommended contribution per goal for the selected period.  

### 2.4. Portfolio monitoring and target allocation

- Define, via UI, a target allocation per asset class (e.g. 60% stocks, 30% ETFs, 10% crypto).  
- Compute the current allocation and compare target vs. actual, with deviation alerts and suggested rebalancing trades.  

### 2.5. Basic visualizations

- Cash‑flow chart (income vs. expenses) per month.  
- Net‑worth evolution chart in the base currency.  
- Target vs. actual allocation chart per asset class.  

### 2.6. Basic security

- User authentication (username/password) before displaying any financial data.  
- Public code on GitHub, but real data, sensitive configs and secrets kept outside the repository using ignore rules and secure secrets storage.  

## 3. Functional requirements

### F1 – Data upload and ingestion

- The system must read files placed in a configured folder (e.g. `data/real/abn`, `data/real/xp`) on a monthly basis.  
- The system must support, in the MVP, files from ABN, Revolut, AMEX, Coinbase and XP Investimentos.  
- For each institution, the system must implement a specific loader that converts the original layout into the internal transaction model.  

### F2 – Unified transaction model

Each transaction must contain at least:

- `transaction_id`  
- `date`  
- `description`  
- `movement_type` (Income, Expense, Transfer, Contribution, Withdrawal, Adjustment)
  - **Income**: money coming from outside (salary, tax refunds, dividends, etc.).
  - **Expense**: money going out to the outside world (bills, groceries, leisure, etc.).
  - **Transfer**: movements between internal accounts (e.g. ABN → Revolut, checking → savings).
  - **Contribution**: money leaving checking and going into investment accounts (brokerage, long-term savings).
  - **Withdrawal**: money leaving investment accounts and going back to checking (redemptions, cash-outs).
  - **Adjustment**: manual/exception adjustments.
- `category` (e.g. HOUSING, TRANSPORT, LEISURE)  
- `subcategory` (e.g. Mortgage, Groceries, Restaurant)  
- `original_amount`  
- `original_currency` (EUR, BRL, USD, crypto)  
- `base_amount`  
- `base_currency`  
- `asset` (when applicable)  
- `asset_class` (Stock, ETF, REIT/FII, Fixed Income, Pension, Crypto, etc.)  

The system must keep auxiliary tables for:

- **Categories:** type (Income/Expense), category, subcategory, macro group (e.g. Fixed / Variable).  
- **Assets:** ticker, name, asset class, other relevant fields.  

### F3 – Currencies and base currency

- The system must allow the user to choose a **base currency** (e.g. EUR) for consolidated reporting.  
- The system must convert `original_amount` to `base_amount` using configurable FX rates (FX table or API in future versions).  
- The system must support at least EUR, BRL, USD and main cryptocurrencies (converted to base currency using a reference rate).  

### F4 – Automatic categorization with rules

- The system must keep a **categorization rules dictionary**, based on:  
  - keywords in the description,  
  - institution,  
  - transaction type,  
  - simple combinations of these.  
- When importing new transactions, the system must apply the dictionary to automatically assign `category` and `subcategory`.  
- If a transaction does not match any rule, it must be flagged as “Uncategorized”.  
- The UI must allow the user to:  
  - Review uncategorized transactions.  
  - Choose type, category and subcategory.  
  - Optionally create a new rule so similar future transactions are categorized automatically.  

### F5 – Budgeting and investing rules

- The system must allow the user to configure, via UI:  
  - Percentage of monthly income to invest.  
  - Split of investments across goals/buckets (percentages and fixed amounts).  
- For the selected period, the system must:  
  - Compute consolidated income.  
  - Compute the total amount to invest.  
  - Compute the recommended contribution for each goal.  

### F6 – Allocation monitoring and rebalancing

- The system must allow the user to define target allocation per asset class (in percentage).  
- The system must compute current allocation based on base‑currency value of each asset class.  
- For each class, the system must show:  
  - Target (%), Actual (%), and the difference in percentage points.  
- The system must highlight classes where the absolute difference is greater than or equal to 5 percentage points.  
- The system must suggest, for deviating classes, how much to buy or sell to return to the target allocation, given the current portfolio value.  

### F7 – Special handling for Tikkie

- The system must identify Tikkie‑related transactions in ABN statements, preferably via description patterns.  
- It must support two main scenarios:  
  - **Shared‑expense reimbursement:** a large initial expense (e.g. restaurant) followed by incoming Tikkie payments; the net expense equals the restaurant bill minus reimbursements and must be booked in the original category (e.g. LEISURE / Restaurant).  
  - **Gift/other collections:** Tikkie payments used to collect money for gifts; the net outgoing amount must be categorized appropriately (e.g. OTHER / Gifts).  
- In the MVP, matching logic may rely on simple rules (date and approximate amounts) and allow manual correction later.  

### F8 – Authentication and basic multi‑user

- The system must require login (username/password) before showing any data.  
- The system must use a secure authentication module for Streamlit, storing passwords as hashes and keeping user configuration outside the public repository.  
- The system must support at least two users in the “family instance” (owner and spouse) and be designed so that, in the future, multiple independent user accounts can be supported.  

## 4. Non‑functional requirements

- **Cost:** rely on free or low‑cost services (Python, Streamlit, Streamlit Community Cloud, GitHub).  
- **Performance:** monthly processing of statements should complete within seconds/minutes, given typical file sizes.  
- **Security / privacy:**  
  - Real data must never be committed to the public repository.  
  - Sensitive files and configs must be listed in `.gitignore` (e.g. `data/real/`, `config/config.yaml`, `.streamlit/secrets.toml`, `.env`).  
- **Maintainability:**  
  - Code organized into modules (`src/data`, `src/domain`, `src/utils`, `app/`).  
  - Use of `requirements.txt` for environment reproducibility.  

## 5. Project folder structure

personal_finance_app/
├── app/
│ └── app.py # Streamlit entry point
├── src/
│ ├── data/
│ │ ├── loaders.py # Institution-specific loaders
│ │ └── transformers.py # Standardization and unification
│ ├── domain/
│ │ ├── budgeting.py # Budget and investing rules
│ │ └── allocation.py # Allocation and rebalancing logic
│ └── utils/
│ └── categorization.py # Categorization engine (rules)
├── config/
│ ├── config_example.yaml # Example config (no secrets)
├── data/
│ ├── example/ # Sample data for the repo
│ └── real/ # Real data (gitignored)
├── docs/
│ └── projeto_financas_en.md
├── tests/
├── requirements.txt
├── .gitignore
└── README.md