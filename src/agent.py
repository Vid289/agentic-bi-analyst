"""
agent.py — The core agent loop.

The schema is embedded in the system prompt upfront so the model doesn't
need to call list_tables or describe_table on every question.

The loop is provider-agnostic — it calls start() once, then feeds tool
results back with continue_with_tool_results() until the model stops
requesting tools or the iteration cap is hit.
"""

from __future__ import annotations

from src.config import CONFIG
from src.schema_introspection import get_schema_summary
from src.tools import execute_tool, get_generated_charts, clear_generated_charts
from src.llm_provider import get_provider
from src.report import generate_report


# --- system prompt ---
# The schema is injected at runtime so it always reflects the live database.

SYSTEM_PROMPT_TEMPLATE = """You are an expert business intelligence analyst with deep \
SQL and statistics skills, working for a SaaS company called Nimbus Analytics.

You answer business questions by querying a DuckDB database and applying statistical \
analysis. You have these tools:

- list_tables, describe_table, run_sql: explore and query the data.
- detect_anomalies: given a time-series, flag statistically unusual points.
- compare_cohort_rates: two-proportion z-test to confirm if a difference between
  two cohorts is real or just noise.
- investigate_drop: given a metric before/after, decompose the change by some
  dimension (region, plan, channel) and rank where the change concentrated.
- generate_chart: run a SQL query and save the result as a Plotly chart (line or
  bar). Use 'line' for time series, 'bar' for category comparisons. Call this
  after you've confirmed the data with run_sql so you know the column names.

# How to work

1. Think about what's really being asked. Questions like "why did X drop?" usually
   require: confirm the drop -> decompose by dimensions -> identify cohorts -> test
   significance -> check qualitative factors (e.g., churn reasons).
2. Prefer the statistical tools over eyeballing SQL output. If a number looks
   anomalous, RUN detect_anomalies. If a cohort difference looks meaningful,
   RUN compare_cohort_rates. Don't just say "this looks significant" -- prove it.
3. When you have the full picture, write a clear answer. Lead with the headline.
   Include the key numbers and (where relevant) the p-value or % contribution.

# SQL guidelines

- Current "today" in the dataset is 2025-12-31.
- For MRR over time: sum subscriptions.mrr where active on the target date
  (start_date <= date AND (end_date IS NULL OR end_date >= date)).
- For churn analysis, join churn_events with subscriptions to get plan tier.
- usage_events is large (~1M rows) -- always filter by date or customer_id.

{schema}
"""


def _build_system_prompt() -> str:
    schema = get_schema_summary()
    return SYSTEM_PROMPT_TEMPLATE.format(schema=schema)


# --- agent loop ---

def run_agent(question: str, verbose: bool = True, write_fn=None) -> str:
    """
    Run the agent loop for a business question.

    Args:
        question: The business question to investigate.
        verbose:  If True, prints each tool call to stdout (used by the CLI).
        write_fn: Optional callback for status messages. When provided (e.g.
                  from the Streamlit app), messages go there instead of stdout.

    Returns:
        The final answer as a plain string.
    """

    def _log(msg: str) -> None:
        # Route output to the Streamlit callback or stdout depending on context
        if write_fn:
            write_fn(msg)
        elif verbose:
            print(msg)

    # Clear any charts left over from a previous run
    clear_generated_charts()

    system_prompt = _build_system_prompt()
    provider = get_provider(system_prompt)

    _log(f"Provider: {CONFIG.provider} / {CONFIG.active_model}\n")

    response = provider.start(question)
    iteration = 0

    while response.stop_reason == "tool_use":
        iteration += 1

        if iteration > CONFIG.max_agent_iterations:
            return (
                f"Stopped after {CONFIG.max_agent_iterations} tool calls "
                "without a final answer."
            )

        results: list[str] = []

        for tc in response.tool_calls:
            # Build a readable label for this tool call
            if tc.name == "run_sql":
                sql_preview = tc.args.get("query", "").replace("\n", " ").strip()
                label = f"[{iteration}] run_sql: {sql_preview[:120]}{'...' if len(sql_preview) > 120 else ''}"
            elif tc.name == "describe_table":
                label = f"[{iteration}] describe_table({tc.args.get('table_name', '')})"
            elif tc.name == "generate_chart":
                label = f"[{iteration}] generate_chart: {tc.args.get('title', '')}"
            else:
                label = f"[{iteration}] {tc.name}"

            _log(label)

            result = execute_tool(tc.name, tc.args)
            results.append(result)

            # Show the first line of the result as a quick preview
            preview = result.split("\n")[0][:100]
            _log(f"   -> {preview}\n")

        response = provider.continue_with_tool_results(response.tool_calls, results)

    answer = response.text or "(No text response from agent.)"

    # Write the HTML report with any charts generated during the run
    chart_paths = get_generated_charts()
    report_path = generate_report(question, answer, chart_paths)

    _log(f"\nDone. {iteration} tool call(s). Report: {report_path}")

    return answer
