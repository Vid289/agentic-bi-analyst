"""
tools.py — Tool definitions for the agent.

Each tool is defined twice:
  1. As a JSON schema sent to the model so it knows the name, description,
     and required arguments.
  2. As a Python function that actually runs when the model calls it.

execute_tool() is the single entry point used by the agent loop.
"""

from __future__ import annotations

import json
import duckdb
import pandas as pd
from src.config import CONFIG
from src.stats import detect_anomalies, compare_cohort_rates, investigate_drop
from src.charts import line_chart, bar_chart


# Tracks chart file paths generated during the current agent run.
# Cleared at the start of each run by clear_generated_charts().
_generated_charts: list[str] = []


def get_generated_charts() -> list[str]:
    """Return chart paths produced so far in this run."""
    return list(_generated_charts)


def clear_generated_charts() -> None:
    """Reset the chart list at the start of a new run."""
    _generated_charts.clear()


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


# --- statistical tool schemas ---

TOOLS_SCHEMA += [
    {
        "name": "detect_anomalies",
        "description": (
            "Run a SQL query that returns a date column and a numeric column, "
            "then flag any rows where the value is statistically unusual "
            "(z-score above the threshold). Use this to confirm whether a dip "
            "or spike in a metric is genuinely anomalous."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": (
                        "SELECT query returning exactly two columns: "
                        "a date/period column and a numeric value column."
                    ),
                },
                "date_column": {
                    "type": "string",
                    "description": "Name of the date or period column in the query result.",
                },
                "value_column": {
                    "type": "string",
                    "description": "Name of the numeric column to analyse.",
                },
                "threshold": {
                    "type": "string",
                    "description": "Z-score cutoff. Default is '2.0'. Raise to '2.5' for stricter detection.",
                },
            },
            "required": ["sql", "date_column", "value_column"],
        },
    },
    {
        "name": "compare_cohort_rates",
        "description": (
            "Two-proportion z-test: checks whether a rate difference between "
            "two groups (e.g. churn rate in EMEA vs NAM) is statistically "
            "significant or could be random variation. "
            "Use run_sql first to get the counts, then pass them here."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "successes_a": {"type": "string", "description": "Count for group A (e.g. churned customers)."},
                "trials_a":    {"type": "string", "description": "Total for group A (e.g. all customers in that group)."},
                "successes_b": {"type": "string", "description": "Count for group B."},
                "trials_b":    {"type": "string", "description": "Total for group B."},
                "label_a":     {"type": "string", "description": "Display name for group A."},
                "label_b":     {"type": "string", "description": "Display name for group B."},
            },
            "required": ["successes_a", "trials_a", "successes_b", "trials_b"],
        },
    },
    {
        "name": "investigate_drop",
        "description": (
            "Decompose a before/after change in a metric across a dimension "
            "(e.g. region, plan tier, acquisition channel) to see which segment "
            "drove the change. Runs two SQL queries — one for each period — and "
            "ranks segments from largest drop to largest gain."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "before_sql": {
                    "type": "string",
                    "description": (
                        "SELECT query for the earlier period. Must return exactly "
                        "two columns: a dimension column and a numeric value column."
                    ),
                },
                "after_sql": {
                    "type": "string",
                    "description": "SELECT query for the later period. Same two-column format.",
                },
                "dimension_column": {
                    "type": "string",
                    "description": "Name of the dimension column (e.g. 'region').",
                },
                "value_column": {
                    "type": "string",
                    "description": "Name of the numeric column (e.g. 'mrr').",
                },
                "metric_name": {
                    "type": "string",
                    "description": "Label for the metric used in the output (e.g. 'MRR').",
                },
            },
            "required": ["before_sql", "after_sql", "dimension_column", "value_column"],
        },
    },
]


# --- statistical tool implementations ---

def _run_query_to_df(sql: str) -> pd.DataFrame:
    """Run a SELECT query and return the result as a DataFrame."""
    con = _connect()
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()


def tool_detect_anomalies(
    sql: str,
    date_column: str,
    value_column: str,
    threshold: str = "2.0",
) -> str:
    """
    Run the provided SQL, extract the two columns, and call detect_anomalies.
    The agent passes threshold as a string because all tool args are strings.
    """
    try:
        df = _run_query_to_df(sql)
    except Exception as e:
        return f"SQL Error: {e}"

    if date_column not in df.columns:
        return f"Error: column '{date_column}' not found. Columns: {list(df.columns)}"
    if value_column not in df.columns:
        return f"Error: column '{value_column}' not found. Columns: {list(df.columns)}"

    dates = df[date_column].astype(str).tolist()
    values = pd.to_numeric(df[value_column], errors="coerce").tolist()

    return detect_anomalies(dates, values, threshold=float(threshold))


def tool_compare_cohort_rates(
    successes_a: str,
    trials_a: str,
    successes_b: str,
    trials_b: str,
    label_a: str = "Group A",
    label_b: str = "Group B",
) -> str:
    """
    Wrapper that converts string arguments (from the tool call) to ints,
    then calls compare_cohort_rates from stats.py.
    """
    return compare_cohort_rates(
        int(successes_a), int(trials_a),
        int(successes_b), int(trials_b),
        label_a, label_b,
    )


def tool_investigate_drop(
    before_sql: str,
    after_sql: str,
    dimension_column: str,
    value_column: str,
    metric_name: str = "metric",
) -> str:
    """
    Run the before and after queries, build dimension->value dicts,
    then call investigate_drop from stats.py.
    """
    try:
        df_before = _run_query_to_df(before_sql)
        df_after  = _run_query_to_df(after_sql)
    except Exception as e:
        return f"SQL Error: {e}"

    for label, df in [("before", df_before), ("after", df_after)]:
        if dimension_column not in df.columns:
            return f"Error: '{dimension_column}' not in {label} query. Columns: {list(df.columns)}"
        if value_column not in df.columns:
            return f"Error: '{value_column}' not in {label} query. Columns: {list(df.columns)}"

    before = dict(zip(
        df_before[dimension_column].astype(str),
        pd.to_numeric(df_before[value_column], errors="coerce"),
    ))
    after = dict(zip(
        df_after[dimension_column].astype(str),
        pd.to_numeric(df_after[value_column], errors="coerce"),
    ))

    return investigate_drop(before, after, metric_name=metric_name)


TOOLS_SCHEMA += [
    {
        "name": "generate_chart",
        "description": (
            "Run a SQL query and turn the result into a Plotly chart saved as HTML. "
            "Use 'line' for time series (e.g. MRR by month) and 'bar' for category "
            "comparisons (e.g. churn by region). Call this after confirming the data "
            "with run_sql so you know the column names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SELECT query returning exactly two columns: x and y.",
                },
                "chart_type": {
                    "type": "string",
                    "description": "'line' or 'bar'.",
                },
                "x_column": {
                    "type": "string",
                    "description": "Column name to use as the x-axis.",
                },
                "y_column": {
                    "type": "string",
                    "description": "Column name to use as the y-axis.",
                },
                "title": {
                    "type": "string",
                    "description": "Chart title shown above the chart.",
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename, e.g. 'mrr_over_time.html'. Must end in .html.",
                },
            },
            "required": ["sql", "chart_type", "x_column", "y_column", "title"],
        },
    },
]


def tool_generate_chart(
    sql: str,
    chart_type: str,
    x_column: str,
    y_column: str,
    title: str,
    filename: str = "chart.html",
) -> str:
    """
    Run the SQL, extract the two columns, and call the right chart function.
    Appends the saved path to _generated_charts so the report can embed it.
    """
    try:
        df = _run_query_to_df(sql)
    except Exception as e:
        return f"SQL Error: {e}"

    if x_column not in df.columns:
        return f"Error: '{x_column}' not found. Columns: {list(df.columns)}"
    if y_column not in df.columns:
        return f"Error: '{y_column}' not found. Columns: {list(df.columns)}"

    x = df[x_column].astype(str).tolist()
    y = pd.to_numeric(df[y_column], errors="coerce").tolist()

    if chart_type == "line":
        path = line_chart(x, y, title=title, filename=filename)
    elif chart_type == "bar":
        path = bar_chart(x, y, title=title, filename=filename)
    else:
        return f"Error: chart_type must be 'line' or 'bar', got '{chart_type}'."

    _generated_charts.append(path)
    return f"Chart saved: {path}"


# --- dashboard tool ---

# Tracks dashboard file paths generated during the current run.
_generated_dashboards: list[str] = []


def get_generated_dashboards() -> list[str]:
    """Return dashboard paths produced so far in this run."""
    return list(_generated_dashboards)


def clear_generated_dashboards() -> None:
    """Reset the dashboard list at the start of a new run."""
    _generated_dashboards.clear()


TOOLS_SCHEMA += [
    {
        "name": "generate_dashboard",
        "description": (
            "Generate a full interactive dark-themed dashboard with multiple charts "
            "including 3D visualisations. Use this when the user asks to 'see a dashboard', "
            "'show me the metrics', or wants a broad overview of a topic rather than a "
            "specific number. "
            "dashboard_type options: "
            "'overview' — KPIs + MRR trend + plan donut + churn breakdown + 3D scatter; "
            "'revenue'  — revenue KPIs + monthly trend + by region + 3D surface (plan × time); "
            "'churn'    — churn KPIs + monthly trend + by reason + by region + 3D breakdown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dashboard_type": {
                    "type": "string",
                    "description": "'overview', 'revenue', or 'churn'",
                },
            },
            "required": ["dashboard_type"],
        },
    },
]


def tool_generate_dashboard(dashboard_type: str) -> str:
    """
    Call the dashboard module, save the HTML file, and track the path.
    """
    from src.dashboard import generate_dashboard   # local import to avoid circular deps
    try:
        path = generate_dashboard(dashboard_type)
        _generated_dashboards.append(path)
        return f"Dashboard saved: {path}"
    except Exception as e:
        return f"Dashboard error: {type(e).__name__}: {e}"


# --- dispatcher ---
# Maps tool names to their Python functions.
# execute_tool() is the only function the agent loop needs to call.

TOOL_FUNCTIONS = {
    "list_tables":          list_tables,
    "describe_table":       describe_table,
    "run_sql":              run_sql,
    "detect_anomalies":     tool_detect_anomalies,
    "compare_cohort_rates": tool_compare_cohort_rates,
    "investigate_drop":     tool_investigate_drop,
    "generate_chart":       tool_generate_chart,
    "generate_dashboard":   tool_generate_dashboard,
}


def execute_tool(name: str, arguments: dict) -> str:
    """Dispatch a tool call by name and return the result as a string."""
    if name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool '{name}'."
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except TypeError as e:
        return f"Error: Bad arguments for {name}: {e}"
