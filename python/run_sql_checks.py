"""
Run the SQL layer end to end in a throw-away SQLite database and print every query result.

    python python/run_sql_checks.py

Why SQLite? It needs no server, so anyone can verify the queries in seconds. The schema and queries
use only ANSI features (CTEs, window functions, CASE, POWER) that MySQL 8 also supports; the
MySQL-only lines (CREATE DATABASE / USE / DROP VIEW syntax) are stripped before running.
For the real MySQL run use sql/01_schema.sql, 02_load_data.sql and 03_business_queries.sql.

Results are also written to outputs/sql_query_results.md.
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
RAW = ROOT / "data" / "raw"

LOADS = [
    ("coal_production", "coal_production_ei_2014_2024.csv"),
    ("coal_consumption", "coal_consumption_ei_2014_2024.csv"),
    ("coal_trade", "coal_trade_selected_2023_2024.csv"),
    ("coal_prices_annual", "coal_price_worldbank_2021_2025.csv"),
    ("coal_prices_detail", "coal_price_detail_worldbank.csv"),
]


def strip_mysql_only(script: str) -> str:
    out = []
    for line in script.splitlines():
        if re.match(r"\s*(CREATE DATABASE|USE)\b", line, re.I):
            continue
        out.append(line)
    return "\n".join(out)


def split_queries(script: str):
    """Yield (title, sql) for each statement that has a '-- Q<n>:' title."""
    for chunk in script.split(";"):
        m = re.search(r"--\s*(Q\d+:[^\n]*)", chunk)
        if m:
            sql = "\n".join(l for l in chunk.splitlines() if not l.strip().startswith("--")).strip()
            if sql.upper().startswith(("SELECT", "WITH")):
                yield m.group(1).strip(), sql


def main():
    con = sqlite3.connect(":memory:")
    con.executescript(strip_mysql_only((SQL / "01_schema.sql").read_text()))
    for table, fname in LOADS:
        df = pd.read_csv(RAW / fname)
        df.columns = [c for c in pd.read_sql(f"PRAGMA table_info({table})", con)["name"]]
        df.to_sql(table, con, if_exists="append", index=False)
        print(f"loaded {len(df):>3} rows into {table}")

    md = ["# SQL query results (verified in SQLite)\n"]
    failed = 0
    for title, sql in split_queries((SQL / "03_business_queries.sql").read_text()):
        try:
            res = pd.read_sql(sql, con)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"\n[FAIL] {title}\n  {exc}")
            continue
        print(f"\n{title}\n{res.to_string(index=False)}")
        md.append(f"## {title}\n\n```\n{res.to_string(index=False)}\n```\n")
    (ROOT / "outputs" / "sql_query_results.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n{'ALL QUERIES RAN' if not failed else str(failed) + ' QUERY(IES) FAILED'}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
