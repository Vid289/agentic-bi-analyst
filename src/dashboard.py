"""
dashboard.py — Generates interactive dark-themed dashboards with 3D charts.

Three dashboard types: overview, revenue, churn.
Each dashboard:
  1. Runs SQL queries against DuckDB
  2. Builds Plotly charts (including at least one 3D visualisation)
  3. Assembles everything into a single dark HTML page
  4. Saves to output/ and returns the file path

The HTML page includes Plotly via CDN so all charts are interactive
(zoom, pan, hover, 3D rotation) without bundling Plotly's 3 MB JS file.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.offline as pyo

from src.config import CONFIG

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# --- dark theme constants ---

_BG    = "rgba(0,0,0,0)"           # transparent — panels provide the background
_FONT  = "#c9d1d9"
_GRID  = "#21262d"
_AXES  = "#30363d"
_SCENE = "rgba(22,27,34,0.95)"     # 3D chart panel background

# Colour palette (GitHub-inspired)
PAL = ["#58a6ff", "#3fb950", "#ffa657", "#f78166", "#d2a8ff", "#79c0ff", "#ff7b72"]


# --- DB helpers ---

def _con():
    return duckdb.connect(str(CONFIG.db_path), read_only=True)


def _q(sql: str) -> pd.DataFrame:
    con = _con()
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()


# --- Plotly layout helpers ---

def _layout(**extra) -> dict:
    """Base layout for 2D charts."""
    d = dict(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=dict(color=_FONT, family="Inter, -apple-system, sans-serif", size=11),
        margin=dict(l=45, r=15, t=30, b=40),
        xaxis=dict(gridcolor=_GRID, linecolor=_AXES, zeroline=False),
        yaxis=dict(gridcolor=_GRID, linecolor=_AXES, zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        hoverlabel=dict(bgcolor="#161b22", bordercolor="#30363d", font_color="#e6edf3"),
        hovermode="x unified",
    )
    d.update(extra)
    return d


def _scene(x_title: str, y_title: str, z_title: str,
           x_ticks: dict | None = None,
           y_ticks: dict | None = None) -> dict:
    """Scene layout for 3D charts."""
    def _ax(title: str, extra: dict | None = None) -> dict:
        ax = dict(
            backgroundcolor=_SCENE,
            gridcolor="#30363d",
            showbackground=True,
            tickcolor=_FONT,
            linecolor="#30363d",
            titlefont=dict(color=_FONT, size=11),
            tickfont=dict(color=_FONT, size=9),
            title=title,
        )
        if extra:
            ax.update(extra)
        return ax

    return dict(scene=dict(
        xaxis=_ax(x_title, x_ticks),
        yaxis=_ax(y_title, y_ticks),
        zaxis=_ax(z_title),
    ))


def _div(fig: go.Figure, div_id: str) -> str:
    """Render a Plotly figure as an HTML div (Plotly loaded from CDN)."""
    return pyo.plot(
        fig,
        output_type="div",
        include_plotlyjs=False,
        div_id=div_id,
        config={"displayModeBar": True, "scrollZoom": True, "responsive": True},
    )


def _panel(title: str, chart_div: str, full_width: bool = False) -> str:
    cls = "panel full" if full_width else "panel"
    return (
        f'<div class="{cls}">'
        f'<div class="panel-title">{title}</div>'
        f'<div class="panel-body">{chart_div}</div>'
        f'</div>'
    )


def _assemble(title: str, kpis: list[dict], panels: list[str]) -> str:
    """Build the final self-contained HTML page."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    kpi_html = ""
    for k in kpis:
        sub = f'<div class="kpi-sub">{k["sub"]}</div>' if k.get("sub") else ""
        kpi_html += (
            f'<div class="kpi-card">'
            f'<div class="kpi-val">{k["value"]}</div>'
            f'<div class="kpi-lbl">{k["label"]}</div>{sub}'
            f'</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: #0d1117;
    color: #c9d1d9;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    padding: 1.1rem 1.4rem 1.4rem;
}}
.db-header {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 0.75rem;
    margin-bottom: 0.9rem;
    border-bottom: 1px solid #21262d;
}}
.db-title  {{ font-size: 0.92rem; font-weight: 600; color: #e6edf3; }}
.db-source {{ margin-left: auto; font-size: 0.72rem; color: #484f58;
              font-family: 'JetBrains Mono', monospace; }}
.kpis {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.6rem;
    margin-bottom: 0.75rem;
}}
.kpi-card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
}}
.kpi-val {{ font-size: 1.55rem; font-weight: 700; color: #58a6ff;
            letter-spacing: -0.03em; line-height: 1; }}
.kpi-lbl {{ font-size: 0.66rem; color: #8b949e; text-transform: uppercase;
            letter-spacing: 0.08em; margin-top: 0.35rem; }}
.kpi-sub {{ font-size: 0.74rem; color: #3fb950; font-weight: 500;
            margin-top: 0.2rem; }}
.grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.65rem;
}}
.panel {{ background: #161b22; border: 1px solid #30363d;
          border-radius: 10px; overflow: hidden; }}
.full  {{ grid-column: 1 / -1; }}
.panel-title {{ padding: 0.55rem 1rem; font-size: 0.69rem; font-weight: 600;
                color: #8b949e; text-transform: uppercase; letter-spacing: 0.08em;
                border-bottom: 1px solid #21262d; }}
.panel-body  {{ padding: 0.1rem 0; }}
</style>
</head>
<body>
<div class="db-header">
  <span class="db-title">📊 {title}</span>
  <span class="db-source">nimbus analytics · saas.duckdb</span>
</div>
<div class="kpis">{kpi_html}</div>
<div class="grid">
{"".join(panels)}
</div>
</body>
</html>"""


# --- individual chart builders ---

def _chart_mrr_trend() -> go.Figure:
    df = _q("""
        SELECT YEAR(invoice_date) AS yr, MONTH(invoice_date) AS mo, SUM(amount) AS rev
        FROM invoices WHERE status = 'paid'
        GROUP BY yr, mo ORDER BY yr, mo
    """)
    labels = [f"{int(r.yr)}-{int(r.mo):02d}" for r in df.itertuples()]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=df["rev"].tolist(),
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(88,166,255,0.08)",
        line=dict(color="#58a6ff", width=2),
        hovertemplate="%{x}<br><b>Revenue: $%{y:,.0f}</b><extra></extra>",
    ))
    fig.update_layout(**_layout(
        yaxis=dict(tickprefix="$", gridcolor=_GRID, linecolor=_AXES, zeroline=False),
    ))
    return fig


def _chart_plan_donut() -> go.Figure:
    df = _q("""
        SELECT p.plan_name, SUM(s.mrr) AS mrr
        FROM subscriptions s JOIN plans p ON s.plan_id = p.plan_id
        WHERE s.status = 'active'
        GROUP BY p.plan_name ORDER BY mrr DESC
    """)
    fig = go.Figure(go.Pie(
        labels=df["plan_name"].tolist(),
        values=df["mrr"].tolist(),
        hole=0.55,
        marker=dict(colors=PAL, line=dict(color="#0d1117", width=2)),
        textfont=dict(color=_FONT),
        hovertemplate="<b>%{label}</b><br>MRR: $%{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    base = _layout()
    fig.update_layout(
        paper_bgcolor=base["paper_bgcolor"],
        font=base["font"],
        margin=dict(l=10, r=10, t=10, b=10),
        legend=base["legend"],
        hoverlabel=base["hoverlabel"],
    )
    return fig


def _chart_churn_by_reason() -> go.Figure:
    df = _q("""
        SELECT reason_category AS reason, COUNT(*) AS n, SUM(mrr_lost) AS lost
        FROM churn_events GROUP BY reason ORDER BY n DESC
    """)
    fig = go.Figure(go.Bar(
        x=df["n"].tolist(), y=df["reason"].tolist(),
        orientation="h",
        marker=dict(color=PAL[2], opacity=0.85),
        hovertemplate="<b>%{y}</b><br>Customers: %{x}<extra></extra>",
    ))
    fig.update_layout(**_layout(
        hovermode="y unified",
        xaxis=dict(gridcolor=_GRID, linecolor=_AXES, zeroline=False, title="Customers"),
        yaxis=dict(gridcolor=_GRID, linecolor=_AXES, zeroline=False, autorange="reversed"),
    ))
    return fig


def _chart_churn_by_region() -> go.Figure:
    df = _q("""
        SELECT c.region, COUNT(*) AS churned, SUM(ce.mrr_lost) AS lost
        FROM churn_events ce JOIN customers c ON ce.customer_id = c.customer_id
        GROUP BY c.region ORDER BY churned DESC
    """)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Customers churned",
        x=df["region"].tolist(), y=df["churned"].tolist(),
        marker_color=PAL[3], opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Churned: %{y}<extra></extra>",
    ))
    fig.update_layout(**_layout())
    return fig


def _chart_mrr_by_region() -> go.Figure:
    df = _q("""
        SELECT c.region, SUM(s.mrr) AS mrr
        FROM subscriptions s JOIN customers c ON s.customer_id = c.customer_id
        WHERE s.status = 'active'
        GROUP BY c.region ORDER BY mrr DESC
    """)
    fig = go.Figure(go.Bar(
        x=df["region"].tolist(), y=df["mrr"].tolist(),
        marker=dict(color=PAL[:len(df)], opacity=0.9),
        hovertemplate="<b>%{x}</b><br>MRR: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(**_layout(
        yaxis=dict(tickprefix="$", gridcolor=_GRID, linecolor=_AXES, zeroline=False),
    ))
    return fig


def _chart_csat_by_priority() -> go.Figure:
    df = _q("""
        SELECT priority, ROUND(AVG(CAST(csat_score AS DOUBLE)), 2) AS avg_csat
        FROM support_tickets WHERE csat_score IS NOT NULL
        GROUP BY priority ORDER BY avg_csat DESC
    """)
    fig = go.Figure(go.Bar(
        x=df["priority"].tolist(), y=df["avg_csat"].tolist(),
        marker=dict(color=PAL[1], opacity=0.85),
        hovertemplate="<b>%{x}</b><br>Avg CSAT: %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(**_layout(
        yaxis=dict(gridcolor=_GRID, linecolor=_AXES, zeroline=False, range=[0, 5]),
    ))
    return fig


def _chart_monthly_churn() -> go.Figure:
    df = _q("""
        SELECT YEAR(churn_date) AS yr, MONTH(churn_date) AS mo,
               COUNT(*) AS n, SUM(mrr_lost) AS lost
        FROM churn_events
        GROUP BY yr, mo ORDER BY yr, mo
    """)
    labels = [f"{int(r.yr)}-{int(r.mo):02d}" for r in df.itertuples()]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Churned customers",
        x=labels, y=df["n"].tolist(),
        marker_color=PAL[3], opacity=0.8,
        hovertemplate="%{x}<br>Churned: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        name="MRR lost",
        x=labels, y=df["lost"].tolist(),
        mode="lines+markers",
        yaxis="y2",
        line=dict(color=PAL[2], width=2),
        marker=dict(size=5),
        hovertemplate="%{x}<br>MRR lost: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(**_layout(
        hovermode="x unified",
        yaxis2=dict(
            overlaying="y", side="right",
            tickprefix="$", gridcolor="rgba(0,0,0,0)",
            linecolor=_AXES, zeroline=False,
            tickfont=dict(color=PAL[2]),
        ),
        barmode="group",
    ))
    return fig


# --- 3D chart builders ---

def _chart_3d_region_plan_mrr() -> go.Figure:
    """
    3D scatter: Region (x) × Plan (y) × Total MRR (z).
    Bubble size = active customer count.
    """
    df = _q("""
        SELECT c.region, p.plan_name,
               COUNT(DISTINCT s.customer_id) AS customers,
               SUM(s.mrr) AS total_mrr
        FROM subscriptions s
        JOIN customers c ON s.customer_id = c.customer_id
        JOIN plans p ON s.plan_id = p.plan_id
        WHERE s.status = 'active'
        GROUP BY c.region, p.plan_name
        ORDER BY c.region, p.plan_name
    """)
    if df.empty:
        return go.Figure()

    regions = sorted(df["region"].unique().tolist())
    plans   = sorted(df["plan_name"].unique().tolist())

    x_vals  = [regions.index(r) for r in df["region"]]
    y_vals  = [plans.index(p)   for p in df["plan_name"]]
    z_vals  = df["total_mrr"].tolist()
    sizes   = [max(5, int(c / 2)) for c in df["customers"]]
    labels  = [
        f"<b>{r}</b> · {p}<br>MRR: ${m:,.0f}<br>Customers: {c}"
        for r, p, m, c in zip(df["region"], df["plan_name"], df["total_mrr"], df["customers"])
    ]

    fig = go.Figure(go.Scatter3d(
        x=x_vals, y=y_vals, z=z_vals,
        mode="markers",
        marker=dict(
            size=sizes,
            color=z_vals,
            colorscale="Blues",
            showscale=True,
            colorbar=dict(
                title="MRR ($)",
                titlefont=dict(color=_FONT, size=10),
                tickfont=dict(color=_FONT, size=9),
                bgcolor="rgba(22,27,34,0.85)",
                bordercolor="#30363d",
                tickprefix="$",
            ),
            opacity=0.88,
            line=dict(color="#21262d", width=0.5),
        ),
        text=labels,
        hoverinfo="text",
    ))
    fig.update_layout(
        paper_bgcolor=_BG,
        font=dict(color=_FONT, family="Inter, sans-serif", size=10),
        margin=dict(l=0, r=0, t=5, b=0),
        hoverlabel=dict(bgcolor="#161b22", bordercolor="#30363d", font_color="#e6edf3"),
        **_scene(
            "Region", "Plan", "Total MRR ($)",
            x_ticks={"tickvals": list(range(len(regions))), "ticktext": regions},
            y_ticks={"tickvals": list(range(len(plans))),   "ticktext": plans},
        ),
    )
    return fig


def _chart_3d_surface_revenue() -> go.Figure:
    """
    3D surface: Monthly Revenue (z) over Time (x) × Plan tier (y).
    The 'wave' chart that shows how each plan's revenue evolved.
    """
    df = _q("""
        SELECT YEAR(i.invoice_date) AS yr, MONTH(i.invoice_date) AS mo,
               p.plan_name, SUM(i.amount) AS revenue
        FROM invoices i
        JOIN subscriptions s ON i.subscription_id = s.subscription_id
        JOIN plans p ON s.plan_id = p.plan_id
        WHERE i.status = 'paid'
        GROUP BY yr, mo, p.plan_name
        ORDER BY yr, mo
    """)
    if df.empty:
        return go.Figure()

    df["month_label"] = df.apply(lambda r: f"{int(r.yr)}-{int(r.mo):02d}", axis=1)
    pivot = (
        df.pivot_table(index="month_label", columns="plan_name",
                       values="revenue", fill_value=0)
        .sort_index()
    )

    months = pivot.index.tolist()
    plans  = pivot.columns.tolist()
    z      = pivot.values.T.tolist()   # shape: (n_plans, n_months)

    # Show every 3rd month to avoid overcrowding the x-axis
    tick_vals  = list(range(0, len(months), 3))
    tick_texts = [months[i] for i in tick_vals]

    fig = go.Figure(go.Surface(
        x=list(range(len(months))),
        y=list(range(len(plans))),
        z=z,
        colorscale="Blues",
        showscale=True,
        colorbar=dict(
            title="Revenue ($)",
            titlefont=dict(color=_FONT, size=10),
            tickfont=dict(color=_FONT, size=9),
            bgcolor="rgba(22,27,34,0.85)",
            bordercolor="#30363d",
            tickprefix="$",
        ),
        hovertemplate="Month: %{x}<br>Plan: %{y}<br>Revenue: $%{z:,.0f}<extra></extra>",
        lighting=dict(ambient=0.6, diffuse=0.8, specular=0.2, roughness=0.5),
        contours=dict(
            x=dict(show=True, color="#30363d", width=1),
            y=dict(show=True, color="#30363d", width=1),
        ),
    ))
    fig.update_layout(
        paper_bgcolor=_BG,
        font=dict(color=_FONT, family="Inter, sans-serif", size=10),
        margin=dict(l=0, r=0, t=5, b=0),
        hoverlabel=dict(bgcolor="#161b22", bordercolor="#30363d", font_color="#e6edf3"),
        **_scene(
            "Month", "Plan", "Revenue ($)",
            x_ticks={"tickvals": tick_vals, "ticktext": tick_texts},
            y_ticks={"tickvals": list(range(len(plans))), "ticktext": plans},
        ),
    )
    return fig


# --- KPI helpers ---

def _kpis_overview() -> list[dict]:
    con = _con()
    try:
        mrr        = con.execute("SELECT SUM(mrr)  FROM subscriptions WHERE status='active'").fetchone()[0] or 0
        customers  = con.execute("SELECT COUNT(DISTINCT customer_id) FROM subscriptions WHERE status='active'").fetchone()[0] or 0
        churned    = con.execute("SELECT COUNT(*) FROM churn_events").fetchone()[0] or 0
        total_cust = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0] or 1
        avg_csat   = con.execute("SELECT AVG(CAST(csat_score AS DOUBLE)) FROM support_tickets WHERE csat_score IS NOT NULL").fetchone()[0] or 0
    finally:
        con.close()

    return [
        {"label": "Total Active MRR",    "value": f"${mrr:,.0f}"},
        {"label": "Active Customers",     "value": f"{customers:,}"},
        {"label": "Lifetime Churn Rate",  "value": f"{churned/total_cust*100:.1f}%"},
        {"label": "Avg CSAT Score",       "value": f"{avg_csat:.2f} / 5"},
    ]


def _kpis_revenue() -> list[dict]:
    con = _con()
    try:
        total_mrr  = con.execute("SELECT SUM(mrr) FROM subscriptions WHERE status='active'").fetchone()[0] or 0
        customers  = con.execute("SELECT COUNT(DISTINCT customer_id) FROM subscriptions WHERE status='active'").fetchone()[0] or 1
        total_inv  = con.execute("SELECT SUM(amount) FROM invoices WHERE status='paid'").fetchone()[0] or 0
        # Month-over-month: last 2 complete months
        df_m = _q("""
            SELECT YEAR(invoice_date)*100+MONTH(invoice_date) AS ym, SUM(amount) AS rev
            FROM invoices WHERE status='paid'
            GROUP BY ym ORDER BY ym DESC LIMIT 2
        """)
    finally:
        con.close()

    mom = ""
    if len(df_m) == 2:
        pct = (df_m["rev"].iloc[0] - df_m["rev"].iloc[1]) / df_m["rev"].iloc[1] * 100
        sign = "+" if pct >= 0 else ""
        mom = f"{sign}{pct:.1f}% MoM"

    return [
        {"label": "Total Active MRR",   "value": f"${total_mrr:,.0f}"},
        {"label": "ARPU (active)",       "value": f"${total_mrr/customers:,.0f}"},
        {"label": "Total Invoiced",      "value": f"${total_inv:,.0f}"},
        {"label": "Revenue Trend",       "value": mom or "—"},
    ]


def _kpis_churn() -> list[dict]:
    con = _con()
    try:
        churned    = con.execute("SELECT COUNT(*), SUM(mrr_lost) FROM churn_events").fetchone()
        total_cust = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0] or 1
        avg_tenure = _q("""
            SELECT AVG(DATEDIFF('day', c.signup_date, ce.churn_date)) AS days
            FROM churn_events ce JOIN customers c ON ce.customer_id = c.customer_id
        """)["days"].iloc[0] or 0
    finally:
        con.close()

    n, lost = churned
    return [
        {"label": "Total Churned",     "value": f"{n:,}"},
        {"label": "MRR Lost",          "value": f"${lost:,.0f}"},
        {"label": "Lifetime Churn %",  "value": f"{n/total_cust*100:.1f}%"},
        {"label": "Avg Tenure (days)", "value": f"{int(avg_tenure):,}"},
    ]


# --- dashboard assemblers ---

def _build_overview() -> str:
    kpis   = _kpis_overview()
    panels = [
        _panel("Monthly Revenue Trend", _div(_chart_mrr_trend(), "mrr_trend"), full_width=True),
        _panel("Active MRR by Plan",    _div(_chart_plan_donut(),  "plan_donut")),
        _panel("Churn by Reason",       _div(_chart_churn_by_reason(), "churn_reason")),
        _panel("Churn by Region",       _div(_chart_churn_by_region(), "churn_region")),
        _panel("CSAT by Ticket Priority", _div(_chart_csat_by_priority(), "csat")),
        _panel("3D — Active MRR: Region × Plan × Revenue",
               _div(_chart_3d_region_plan_mrr(), "scatter3d"), full_width=True),
    ]
    return _assemble("Business Overview Dashboard", kpis, panels)


def _build_revenue() -> str:
    kpis   = _kpis_revenue()
    panels = [
        _panel("Monthly Revenue Trend",  _div(_chart_mrr_trend(),    "mrr_trend"),  full_width=True),
        _panel("Active MRR by Plan",     _div(_chart_plan_donut(),   "plan_donut")),
        _panel("Active MRR by Region",   _div(_chart_mrr_by_region(),"mrr_region")),
        _panel("3D — Revenue Wave: Time × Plan Tier × Monthly Revenue",
               _div(_chart_3d_surface_revenue(), "surface3d"), full_width=True),
    ]
    return _assemble("Revenue Dashboard", kpis, panels)


def _build_churn() -> str:
    kpis   = _kpis_churn()
    panels = [
        _panel("Monthly Churn & MRR Lost",  _div(_chart_monthly_churn(),     "churn_trend"),  full_width=True),
        _panel("Churn by Reason",           _div(_chart_churn_by_reason(),   "churn_reason")),
        _panel("Churn by Region",           _div(_chart_churn_by_region(),   "churn_region")),
        _panel("3D — Churn: Region × Plan × Revenue Lost",
               _div(_chart_3d_region_plan_mrr(), "scatter3d_churn"), full_width=True),
    ]
    return _assemble("Churn Analysis Dashboard", kpis, panels)


# --- public entry point ---

def generate_dashboard(dashboard_type: str) -> str:
    """
    Generate a dashboard, save it to output/, and return the file path.

    Args:
        dashboard_type: 'overview', 'revenue', or 'churn'
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    builders = {
        "overview": _build_overview,
        "revenue":  _build_revenue,
        "churn":    _build_churn,
    }

    key = dashboard_type.strip().lower()
    if key not in builders:
        # Default to overview for unrecognised types
        key = "overview"

    html = builders[key]()
    path = OUTPUT_DIR / f"dashboard_{key}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)
