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
from src.tools import execute_tool
from src.llm_provider import get_provider


# --- system prompt ---

def _build_system_prompt() -> str:
    schema = get_schema_summary()
    return f"""You are a BI analyst investigating business questions for a B2B SaaS company called Nimbus Analytics.

{schema}

## Your job
Given a business question, investigate it by querying the database.
Follow the data — if something looks interesting, drill down further.

## Rules
- Use run_sql to query the data. The schema above tells you what tables and
  columns exist; use describe_table or list_tables only if you need to double-check.
- Run multiple queries to build a complete picture. Don't stop at one.
- Drill down by region, plan tier, time period, cohort — whatever the data suggests.
- Be specific: cite actual numbers from your queries in your final answer.
- End with a clear summary: what happened, why it happened, and recommended actions.
- If a query returns an error, read it carefully and write a corrected version.
- Hard limit: you will be stopped after {CONFIG.max_agent_iterations} tool calls.
"""


# --- agent loop ---

def run_agent(question: str, verbose: bool = True) -> str:
    """
    Run the agent loop for a business question.

    Args:
        question: The business question to investigate.
        verbose:  If True, prints each tool call as it runs.

    Returns:
        The final answer as a plain string.
    """
    system_prompt = _build_system_prompt()
    provider = get_provider(system_prompt)

    if verbose:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print(f"Provider: {CONFIG.provider} / {CONFIG.active_model}")
        print(f"{'='*60}\n")

    response = provider.start(question)
    iteration = 0

    while response.stop_reason == "tool_use":
        iteration += 1

        # Stop if we've hit the iteration cap
        if iteration > CONFIG.max_agent_iterations:
            return (
                f"Stopped after {CONFIG.max_agent_iterations} tool calls "
                "without a final answer."
            )

        results: list[str] = []

        for tc in response.tool_calls:
            if verbose:
                print(f"[{iteration}] tool: {tc.name}", end="")
                if tc.name == "run_sql":
                    # Show a trimmed preview of the SQL on the next line
                    sql_preview = tc.args.get("query", "").replace("\n", " ").strip()
                    print(f"\n   SQL: {sql_preview[:140]}{'...' if len(sql_preview) > 140 else ''}")
                elif tc.name == "describe_table":
                    print(f"({tc.args.get('table_name', '')})")
                else:
                    print()

            result = execute_tool(tc.name, tc.args)
            results.append(result)

            if verbose:
                # Print just the first line as a quick preview
                preview = result.split("\n")[0][:100]
                print(f"   -> {preview}\n")

        response = provider.continue_with_tool_results(response.tool_calls, results)

    if verbose:
        print(f"\nDone. {iteration} tool call(s).\n")

    return response.text or "(No text response from agent.)"
