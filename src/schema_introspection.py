"""
schema_introspection.py — Builds a schema summary string for the system prompt.

Kept compact so we're not sending unnecessary tokens to the model on every
request. Column types and short table descriptions are enough context for
the model to write correct SQL.
"""

from __future__ import annotations
import duckdb
from src.config import CONFIG


# Short description for each table, included in the system prompt alongside
# the column list. Helps the model pick the right table without querying metadata.
TABLE_DESCRIPTIONS = {
    "customers":      "Company accounts. One row per customer (B2B). "
                      "Includes industry, employee_count, country, region, "
                      "signup_date, acquisition_channel.",
    "plans":          "The 4 subscription tiers: Free, Starter, Pro, Enterprise. "
                      "Note: Pro plan price increased from $199 to $249 on 2025-06-01 "
                      "(this is reflected in the subscriptions.mrr column, not in plans).",
    "subscriptions":  "Subscription history. Each customer can have multiple rows "
                      "(upgrades, downgrades, churn). Status: active | churned | "
                      "upgraded | downgraded. mrr = monthly recurring revenue for "
                      "that subscription period. end_date is NULL for currently-active subs.",
    "usage_events":   "Daily product engagement events per customer. event_type is one of "
                      "login | dashboard_view | report_export | api_call | integration_used. "
                      "Large table (~1M rows) — always filter by customer_id and/or "
                      "event_date to avoid full scans.",
    "support_tickets":"Customer support tickets. csat_score (1-5) only present for "
                      "resolved tickets. resolved_date is NULL for open tickets.",
    "churn_events":   "Cancellation events (paid plans only — free tier 'churns' silently). "
                      "reason_category in: price | missing_features | competitor | low_usage "
                      "| bad_support | business_closure | other.",
    "invoices":       "Monthly billing records. status in: paid | pending | failed | refunded.",
}


def get_schema_summary() -> str:
    """
    Query the database for table and column metadata and return it as a
    formatted string. This string goes directly into the system prompt.
    """
    con = duckdb.connect(str(CONFIG.db_path), read_only=True)
    try:
        lines = ["# Database schema\n"]
        lines.append(
            "All dates are stored as DATE. The current date in the dataset "
            "is 2025-12-31 (treat this as 'today' for relative-date questions).\n"
        )

        tables = con.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
        """).fetchall()

        for (table_name,) in tables:
            desc = TABLE_DESCRIPTIONS.get(table_name, "")
            lines.append(f"\n## {table_name}")
            if desc:
                lines.append(f"_{desc}_\n")

            columns = con.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'main' AND table_name = '{table_name}'
                ORDER BY ordinal_position
            """).fetchall()

            for col_name, col_type in columns:
                lines.append(f"- `{col_name}` ({col_type})")

        return "\n".join(lines)
    finally:
        con.close()


if __name__ == "__main__":
    # Run directly to preview what gets sent to the model
    print(get_schema_summary())
