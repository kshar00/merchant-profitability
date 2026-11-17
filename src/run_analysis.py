"""Run every question query in sql/ and save the results to outputs/.

Run:  python src/run_analysis.py
"""

from pathlib import Path

import pandas as pd

from db import ROOT, SQL, connect, query

OUT = ROOT / "outputs"


def main():
    OUT.mkdir(exist_ok=True)
    con = connect()
    # Materialise the views once so the question queries run quickly
    con.executescript("""
        CREATE TABLE fe AS SELECT * FROM fact_economics;
        CREATE TABLE mm AS SELECT * FROM merchant_month;
        DROP VIEW merchant_month; DROP VIEW fact_economics;
        ALTER TABLE fe RENAME TO fact_economics;
        ALTER TABLE mm RENAME TO merchant_month;
    """)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    for path in sorted(SQL.glob("[0-9][0-9]_*.sql")):
        if path.name.startswith("00_"):
            continue
        df = query(con, path.read_text())
        df.to_csv(OUT / f"{path.stem}.csv", index=False)
        print(f"\n== {path.stem} ({len(df)} rows)")
        print(df.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
