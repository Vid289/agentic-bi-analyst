"""
Initialize the DuckDB database: create schema, generate synthetic data, and load it.

Run:  python database/init_db.py
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

from generate_data import generate_all

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / os.getenv("DB_PATH", "data/saas.duckdb")
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def init():
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing DB for a clean rebuild
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"🗑️  Removed existing database at {DB_PATH}")

    print(f"📁 Creating database at {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))

    # Apply schema
    print("📜 Applying schema...")
    with open(SCHEMA_PATH) as f:
        con.execute(f.read())

    # Generate data
    tables = generate_all()

    # Load each table — register DataFrame then INSERT INTO
    print("\n💾 Loading data into DuckDB...")
    for name, df in tables.items():
        # Register DataFrame as a temp view, then insert
        con.register("temp_df", df)
        con.execute(f"INSERT INTO {name} SELECT * FROM temp_df")
        con.unregister("temp_df")
        count = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"   ✓ {name:20s} {count:>8,} rows")

    # Sanity-check queries
    print("\n🔍 Sanity checks:")
    checks = [
        ("Total active subscriptions",
         "SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"),
        ("Total MRR (active subs)",
         "SELECT ROUND(SUM(mrr), 0) FROM subscriptions WHERE status = 'active'"),
        ("Customers by region",
         "SELECT region, COUNT(*) FROM customers GROUP BY region ORDER BY COUNT(*) DESC"),
        ("Churn events in Q3 2025 (EMEA enterprise)",
         """SELECT COUNT(*)
            FROM churn_events ce
            JOIN customers c ON ce.customer_id = c.customer_id
            JOIN subscriptions s ON s.customer_id = c.customer_id AND s.status = 'churned'
            JOIN plans p ON s.plan_id = p.plan_id
            WHERE c.region = 'EMEA'
              AND p.tier = 'enterprise'
              AND ce.churn_date BETWEEN '2025-07-01' AND '2025-09-30'"""),
        ("Pro tier churn count Jun-Aug 2025",
         """SELECT COUNT(*)
            FROM churn_events ce
            JOIN subscriptions s ON s.customer_id = ce.customer_id AND s.status = 'churned'
            JOIN plans p ON s.plan_id = p.plan_id
            WHERE p.tier = 'pro'
              AND ce.churn_date BETWEEN '2025-06-01' AND '2025-08-31'"""),
    ]
    for label, sql in checks:
        result = con.execute(sql).fetchall()
        print(f"   {label}:")
        for row in result:
            print(f"      {row}")

    con.close()
    print(f"\n✅ Done. Database ready at {DB_PATH}")
    print("   Next step: move on to Phase 2 (agent loop).")


if __name__ == "__main__":
    init()
