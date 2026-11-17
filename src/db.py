"""Load the CSVs into SQLite and build the economics views."""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SQL = ROOT / "sql"
TABLES = ["merchants", "pricing", "payment_method_costs", "monthly_transactions"]


def connect() -> sqlite3.Connection:
    """In-memory SQLite database with the four tables and the two economics views."""
    con = sqlite3.connect(":memory:")
    for name in TABLES:
        pd.read_csv(DATA / f"{name}.csv").to_sql(name, con, index=False)
    con.execute("CREATE INDEX ix_tx ON monthly_transactions (merchant_id, payment_method, month)")
    con.execute("CREATE INDEX ix_pr ON pricing (merchant_id, payment_method)")
    con.executescript((SQL / "00_economics_model.sql").read_text())
    return con


def query(con: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, con)
