"""
charts.py — Plotly chart generation.

Each function takes plain Python lists, builds a Plotly figure,
saves it to the output/ directory as a self-contained HTML file,
and returns the file path so it can be embedded in the report.
"""

from __future__ import annotations

from pathlib import Path
import plotly.graph_objects as go

# Charts are saved here alongside the final report
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)


# --- line chart ---

def line_chart(
    x: list,
    y: list[float],
    title: str,
    x_label: str = "",
    y_label: str = "",
    filename: str = "chart.html",
) -> str:
    """
    Generate a line chart and save it as a self-contained HTML file.
    Returns the file path.

    Good for: time series (MRR over time, churn count by month).
    """
    _ensure_output_dir()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="lines+markers",
        line=dict(width=2, color="#4A90D9"),
        marker=dict(size=6),
    ))
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
        hovermode="x unified",
    )

    path = OUTPUT_DIR / filename
    fig.write_html(str(path))
    return str(path)


# --- bar chart ---

def bar_chart(
    x: list,
    y: list[float],
    title: str,
    x_label: str = "",
    y_label: str = "",
    filename: str = "chart.html",
) -> str:
    """
    Generate a bar chart and save it as a self-contained HTML file.
    Returns the file path.

    Good for: comparisons across categories (churn by region, MRR by plan tier).
    """
    _ensure_output_dir()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x,
        y=y,
        marker_color="#4A90D9",
    ))
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white",
    )

    path = OUTPUT_DIR / filename
    fig.write_html(str(path))
    return str(path)
