"""
tools.py — Tool definitions for the agent.

Each tool is defined twice:
  1. As a JSON schema sent to the model so it knows the name, description,
     and required arguments.
  2. As a Python function that actually runs when the model calls it.

execute_tool() is the single entry point used by the agent loop.
"""

from __future__ import annotations

import duckdb
import pandas as pd
from src.config import CONFIG


# --- tool schemas ---
# These dicts are passed directly to the model in the API request.

TOOLS_SCHEMA = [
    {
        "name": "list_tables",
        "description": "List all tables in the database. Use this first if you're "
                       "unsure what data is available.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "describe_table",
        "description": "Get the column names and types for a specific table, "
                       "plus 3 sample rows. Use this when you need to confirm "
                       "exact column names before writing SQL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table to describe.",
                },
            },
            "required": ["table_name"],
        },
    },
    {
        "name": "run_sql",
        "description": "Execute a SQL SELECT query against the DuckDB database "
                       "and return the result. Only SELECT/WITH queries are allowed. "
                       "If the query fails, the error message is returned — read it "
                       "and write a corrected query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A valid DuckDB SQL SELECT or WITH query.",
                },
            },
            "required": ["query"],
        },
    },
]


# --- tool implementations ---

def _connect():
    """Open a read-only connection so the agent can't modify the database."""
    return duckdb.connect(str(CONFIG.db_path), read_only=True)


def list_tables() -> str:
    """Return a comma-separated list of table names."""
    con = _connect()
    try:
        tables = con.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'main' ORDER BY table_name
        """).fetchall()
        return "Tables: " + ", ".join(t[0] for t in tables)
    finally:
        con.close()


def describe_table(table_name: str) -> str:
    """Return column names, types, and 3 sample rows for a table."""
    con = _connect()
    try:
        cols = con.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'main' AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """).fetchall()
        if not cols:
            return f"Table '{table_name}' not found."

        col_lines = "\n".join(f"  - {n} ({t})" for n, t in cols)
        sample = con.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchdf()
        return (
            f"Table: {table_name}\nColumns:\n{col_lines}\n\n"
            f"Sample rows:\n{sample.to_string(index=False)}"
        )
    finally:
        con.close()


def run_sql(query: str) -> str:
    """
    Execute a SQL query and return the results as a plain-text table.
    Returns the error message if the query fails.
    Only SELECT and WITH queries are allowed.
    """
    q_lower = query.strip().lower()
    if not (q_lower.startswith("select") or q_lower.startswith("with")):
        return ("Error: Only SELECT or WITH queries are allowed. "
                "Do not use INSERT, UPDATE, DELETE, DROP, etc.")

    con = _connect()
    try:
        df = con.execute(query).fetchdf()
        if len(df) == 0:
            return "Query returned no rows."
        # Cap at 50 rows to keep the response size reasonable
        if len(df) > 50:
            head = df.head(50).to_string(index=False)
            return (f"Query returned {len(df)} rows (showing first 50):\n{head}\n"
                    f"... ({len(df) - 50} more rows omitted)")
        return f"Query returned {len(df)} rows:\n{df.to_string(index=False)}"
    except Exception as e:
        return f"SQL Error: {type(e).__name__}: {e}"
    finally:
        con.close()


# --- dispatcher ---
# Maps tool names to their Python functions.
# execute_tool() is the only function the agent loop needs to call.

TOOL_FUNCTIONS = {
    "list_tables": list_tables,
    "describe_table": describe_table,
    "run_sql": run_sql,
}


def execute_tool(name: str, arguments: dict) -> str:
    """Dispatch a tool call by name and return the result as a string."""
    if name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool '{name}'."
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except TypeError as e:
        return f"Error: Bad arguments for {name}: {e}"
