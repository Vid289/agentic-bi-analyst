"""
app.py — Streamlit chatbot UI for the Agentic BI Analyst.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import html as html_lib
import json
from pathlib import Path

import duckdb
import streamlit as st
import streamlit.components.v1 as components

from src.agent import run_agent
from src.tools import get_generated_charts, get_generated_dashboards
from src.config import CONFIG


# --- page config ---

st.set_page_config(
    page_title="Nimbus Analytics · BI Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- CSS ---

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ── Sidebar ──────────────────────────────────────── */

[data-testid="stSidebar"] {
    background-color: #1e293b !important;
    border-right: 1px solid #334155 !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #cbd5e1 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #334155 !important;
    margin: 0.5rem 0 !important;
}
[data-testid="stSidebar"]::-webkit-scrollbar { width: 4px; }
[data-testid="stSidebar"]::-webkit-scrollbar-track { background: #1e293b; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
    background: #475569;
    border-radius: 4px;
}

/* Sidebar buttons */
[data-testid="stSidebar"] button {
    background: transparent !important;
    border: 1px solid #334155 !important;
    color: #94a3b8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 8px !important;
    padding: 0.45rem 0.85rem !important;
    line-height: 1.45 !important;
    transition: all 0.15s !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(99, 102, 241, 0.1) !important;
    border-color: #6366f1 !important;
    color: #a5b4fc !important;
}
[data-testid="stSidebar"] button p {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    color: #94a3b8 !important;
}
[data-testid="stSidebar"] button:hover p {
    color: #a5b4fc !important;
}

/* ── Sidebar: brand block ─────────────────────────── */

.sb-brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0.25rem 0 0.5rem 0;
}
.sb-brand-icon {
    font-size: 1.6rem;
    line-height: 1;
}
.sb-brand-name {
    font-size: 1rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1.25;
    letter-spacing: -0.01em;
}
.sb-brand-sub {
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.08rem;
}

/* ── Sidebar: status pills ────────────────────────── */

.sb-pills {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin: 0.1rem 0;
}
.sb-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border-radius: 20px;
    padding: 0.22rem 0.65rem;
    font-size: 0.73rem;
    font-weight: 500;
}
.pill-green { background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.3); color: #4ade80; }
.pill-blue  { background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.3); color: #818cf8; }
.pill-dot   { width: 6px; height: 6px; border-radius: 50%; }
.dot-on     { background: #4ade80; }
.dot-model  { background: #818cf8; }

/* ── Sidebar: section header ──────────────────────── */

.sb-section {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #475569;
    margin: 0.1rem 0 0.45rem 0;
}

/* ── Sidebar: session stats ───────────────────────── */

.sb-stats {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.4rem;
}
.sb-stat {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 0.55rem 0.4rem;
    text-align: center;
}
.sb-stat-val {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1;
}
.sb-stat-lbl {
    font-size: 0.65rem;
    color: #64748b;
    margin-top: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Sidebar: schema list ─────────────────────────── */

.schema-list { margin: 0; padding: 0; }
.schema-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.3rem 0.5rem;
    border-radius: 6px;
    transition: background 0.12s;
    cursor: default;
}
.schema-item:hover { background: rgba(255,255,255,0.04); }
.schema-item-left  { display: flex; align-items: center; gap: 0.5rem; }
.schema-dot        { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.schema-name       { font-size: 0.8rem; color: #cbd5e1; }
.schema-badge {
    font-size: 0.6rem;
    padding: 0.05rem 0.4rem;
    border-radius: 4px;
    font-weight: 500;
}
.badge-ref   { background: rgba(34,197,94,0.12); color: #4ade80; border: 1px solid rgba(34,197,94,0.2); }
.badge-txn   { background: rgba(99,102,241,0.12); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); }
.badge-event { background: rgba(251,146,60,0.12); color: #fb923c; border: 1px solid rgba(251,146,60,0.2); }
.schema-count { font-size: 0.72rem; color: #475569; }

/* ── Sidebar: pattern items ───────────────────────── */

.pattern-item {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.32rem 0.5rem;
    border-radius: 6px;
    transition: background 0.12s;
}
.pattern-item:hover { background: rgba(255,255,255,0.04); }
.pattern-marker { color: #f59e0b; font-size: 0.75rem; flex-shrink: 0; margin-top: 0.05rem; }
.pattern-text   { font-size: 0.78rem; color: #94a3b8; line-height: 1.4; }
.pattern-period { font-size: 0.7rem; color: #475569; }

/* ── Hero ─────────────────────────────────────────── */

.hero {
    background: linear-gradient(135deg, #1e3a5f 0%, #1e293b 60%, #162032 100%);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.75rem;
    color: white;
}
.hero-title {
    font-size: 1.7rem;
    font-weight: 700;
    letter-spacing: -0.025em;
    line-height: 1.2;
    margin: 0 0 0.5rem 0;
    color: #f1f5f9;
}
.hero-sub {
    color: #94a3b8;
    font-size: 0.92rem;
    line-height: 1.6;
    max-width: 580px;
    margin: 0;
}
.hero-tags {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 1.25rem;
}
.hero-tag {
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
    padding: 0.2rem 0.75rem;
    font-size: 0.75rem;
    color: #94a3b8;
}

/* ── Tool log ─────────────────────────────────────── */

.tool-log {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Menlo', monospace;
    font-size: 0.775rem;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 280px;
    overflow-y: auto;
}

/* ── Empty state ──────────────────────────────────── */

.empty-hint {
    font-size: 0.88rem;
    color: #64748b;
    margin-bottom: 0.25rem;
}
.empty-category {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6366f1;
    margin: 1.1rem 0 0.4rem 0;
}

/* ── Chat: question label ─────────────────────────── */

.q-num {
    font-size: 0.68rem;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.25rem;
}

</style>
""", unsafe_allow_html=True)


# --- constants ---

_TABLE_TYPES = {
    "customers":       ("ref",   "#4ade80", "badge-ref"),
    "plans":           ("ref",   "#4ade80", "badge-ref"),
    "subscriptions":   ("txn",   "#818cf8", "badge-txn"),
    "invoices":        ("txn",   "#818cf8", "badge-txn"),
    "usage_events":    ("txn",   "#818cf8", "badge-txn"),
    "support_tickets": ("event", "#fb923c", "badge-event"),
    "churn_events":    ("event", "#fb923c", "badge-event"),
}

_TABLE_ORDER = [
    "customers", "plans", "subscriptions",
    "invoices", "usage_events", "support_tickets", "churn_events",
]

PATTERNS = [
    ("Pro plan price increase triggered a churn spike",  "Jun 2025"),
    ("EMEA pricing experiment led to enterprise churn",  "Q3 2025"),
    ("Low day-30 usage doubles the long-term churn rate", "all time"),
    ("Enterprise files more tickets but scores higher CSAT", "all time"),
]

TOOLS = [
    ("run_sql",              "Execute SELECT queries against DuckDB"),
    ("detect_anomalies",     "Flag statistical outliers in a time series"),
    ("compare_cohort_rates", "Z-test two groups for significance"),
    ("investigate_drop",     "Decompose a before/after metric change"),
    ("generate_chart",       "Render Plotly line or bar charts"),
    ("list_tables",          "List available tables"),
    ("describe_table",       "Inspect columns and sample rows"),
]

EXAMPLES = [
    ("revenue", "Why did MRR drop in Q3 2025?"),
    ("revenue", "Which acquisition channels produce the highest LTV customers?"),
    ("churn",   "Which customer segments have the highest churn rate?"),
    ("churn",   "Compare enterprise vs pro plan churn rates"),
    ("ops",     "What is the relationship between support tickets and churn?"),
    ("ops",     "What happened to EMEA customers in Q3 2025?"),
]


# --- cached DB queries ---

@st.cache_data
def _get_schema_info() -> dict[str, int]:
    """Return {table_name: row_count} for every table. Runs once per session."""
    con = duckdb.connect(str(CONFIG.db_path), read_only=True)
    try:
        tables = con.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'main' ORDER BY table_name
        """).fetchall()
        return {
            name: con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for (name,) in tables
        }
    finally:
        con.close()


schema_info = _get_schema_info()
total_rows  = sum(schema_info.values())
table_count = len(schema_info)

_ordered_tables = [t for t in _TABLE_ORDER if t in schema_info]
_ordered_tables += [t for t in schema_info if t not in _TABLE_ORDER]


# --- session state ---

if "messages"         not in st.session_state: st.session_state.messages         = []
if "trigger_question" not in st.session_state: st.session_state.trigger_question = None
if "session_stats"    not in st.session_state:
    st.session_state.session_stats = {"questions": 0, "tool_calls": 0, "charts": 0}


# --- resolve input early ---
# st.chat_input renders at the bottom regardless of call position.

_typed   = st.chat_input("Ask a business question about Nimbus Analytics...")
_clicked = st.session_state.trigger_question
st.session_state.trigger_question = None
question: str | None = _clicked or _typed or None

stats = st.session_state.session_stats


# --- build sidebar HTML ---

schema_html = ""
for name in _ordered_tables:
    ttype, dot_col, badge_cls = _TABLE_TYPES.get(name, ("txn", "#818cf8", "badge-txn"))
    tlabel = ttype
    count  = schema_info.get(name, 0)
    schema_html += f"""
    <div class="schema-item">
        <div class="schema-item-left">
            <span class="schema-dot" style="background:{dot_col}"></span>
            <span class="schema-name">{name}</span>
            <span class="schema-badge {badge_cls}">{tlabel}</span>
        </div>
        <span class="schema-count">{count:,}</span>
    </div>"""

pattern_html = "".join(
    f'<div class="pattern-item">'
    f'<span class="pattern-marker">◆</span>'
    f'<span class="pattern-text">{text}'
    f'  <span class="pattern-period">{period}</span></span>'
    f'</div>'
    for text, period in PATTERNS
)

provider_label = "Anthropic Claude" if CONFIG.provider == "anthropic" else "Google Gemini"


# --- sidebar ---

with st.sidebar:

    # Brand
    st.markdown(f"""
    <div class="sb-brand">
        <span class="sb-brand-icon">📊</span>
        <div>
            <div class="sb-brand-name">Nimbus Analytics</div>
            <div class="sb-brand-sub">Agentic BI Analyst</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Status pills
    st.markdown(f"""
    <div class="sb-pills">
        <span class="sb-pill pill-green">
            <span class="pill-dot dot-on"></span> Connected
        </span>
        <span class="sb-pill pill-blue">
            <span class="pill-dot dot-model"></span> {CONFIG.active_model}
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Session stats
    st.markdown('<div class="sb-section">This session</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="sb-stats">
        <div class="sb-stat">
            <div class="sb-stat-val">{stats["questions"]}</div>
            <div class="sb-stat-lbl">Queries</div>
        </div>
        <div class="sb-stat">
            <div class="sb-stat-val">{stats["tool_calls"]}</div>
            <div class="sb-stat-lbl">Tool calls</div>
        </div>
        <div class="sb-stat">
            <div class="sb-stat-val">{stats["charts"]}</div>
            <div class="sb-stat-lbl">Charts</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Schema
    st.markdown(
        f'<div class="sb-section">Database &nbsp;·&nbsp; Jan 2024 – Dec 2025</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="schema-list">{schema_html}</div>', unsafe_allow_html=True)

    st.divider()

    # Patterns
    st.markdown('<div class="sb-section">Patterns in the data</div>', unsafe_allow_html=True)
    st.markdown(pattern_html, unsafe_allow_html=True)

    st.divider()

    # Suggested questions
    st.markdown('<div class="sb-section">Suggested questions</div>', unsafe_allow_html=True)
    for i, (_, ex) in enumerate(EXAMPLES):
        if st.button(ex, key=f"sb_{i}", use_container_width=True):
            st.session_state.trigger_question = ex
            st.rerun()

    st.divider()

    if st.button("Clear conversation", key="clear_btn", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_stats = {"questions": 0, "tool_calls": 0, "charts": 0}
        st.rerun()


# --- hero ---

st.markdown(f"""
<div class="hero">
    <div class="hero-title">📊 Agentic BI Analyst</div>
    <div class="hero-sub">
        Ask any business question about Nimbus Analytics. The agent queries the database,
        runs statistical tests, and explains exactly what it found — step by step.
    </div>
    <div class="hero-tags">
        <span class="hero-tag">DuckDB · {total_rows:,} rows</span>
        <span class="hero-tag">{table_count} tables · 2024–2025</span>
        <span class="hero-tag">SQL + Statistics + Charts</span>
        <span class="hero-tag">{provider_label}</span>
        <span class="hero-tag">{stats["questions"]} quer{"y" if stats["questions"] == 1 else "ies"} this session</span>
    </div>
</div>
""", unsafe_allow_html=True)


# --- helpers ---

def _format_tool_log(lines: list[str]) -> str:
    """Colour-code tool log lines for the terminal display."""
    parts = []
    for line in lines:
        if not line.strip():
            continue
        esc = html_lib.escape(line)
        if line.strip().startswith("["):
            parts.append(f'<span style="color:#818cf8">{esc}</span>')
        elif line.startswith("   ->"):
            parts.append(f'<span style="color:#86efac">{esc}</span>')
        else:
            parts.append(f'<span style="color:#64748b">{esc}</span>')
    return "\n".join(parts)


def _copy_button(text: str, key: str) -> None:
    """Render a copy-to-clipboard button using the browser clipboard API."""
    js_str = json.dumps(text)
    components.html(
        f"""
        <button
            onclick="navigator.clipboard.writeText({js_str}).then(()=>{{
                this.textContent='Copied';
                this.style.color='#4ade80';
                this.style.borderColor='#4ade80';
                setTimeout(()=>{{
                    this.textContent='Copy answer';
                    this.style.color='';
                    this.style.borderColor='';
                }}, 1800);
            }})"
            style="background:transparent;border:1px solid #334155;color:#64748b;
                   border-radius:6px;padding:4px 12px;font-family:'Inter',sans-serif;
                   font-size:12px;cursor:pointer;transition:all 0.2s;">
            Copy answer
        </button>
        """,
        height=34,
    )


def _render_assistant(msg: dict, idx: int) -> None:
    """Render an assistant message: answer, actions, tool log, charts, download."""
    st.markdown(msg["content"])

    # Action row
    col_copy, col_gap = st.columns([1, 5])
    with col_copy:
        _copy_button(msg["content"], key=f"cp_{idx}")

    if msg.get("tool_log"):
        with st.expander("View investigation steps"):
            formatted = _format_tool_log(msg["tool_log"].split("\n"))
            st.markdown(
                f'<div class="tool-log">{formatted}</div>',
                unsafe_allow_html=True,
            )

    for chart_html in msg.get("chart_htmls", []):
        components.html(chart_html, height=420, scrolling=False)

    if msg.get("report_bytes"):
        st.download_button(
            label="Download full report",
            data=msg["report_bytes"],
            file_name="report.html",
            mime="text/html",
            key=f"dl_{idx}",
        )


# --- render existing chat history ---

for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            q_num = sum(1 for m in st.session_state.messages[:idx + 1] if m["role"] == "user")
            st.markdown(f'<div class="q-num">Question {q_num}</div>', unsafe_allow_html=True)
            st.markdown(msg["content"])
        else:
            _render_assistant(msg, idx)


# --- empty state ---

if not st.session_state.messages and not question:
    st.markdown(
        '<p class="empty-hint">Not sure where to start? Pick a question below.</p>',
        unsafe_allow_html=True,
    )

    categories = [
        ("revenue", "Revenue"),
        ("churn",   "Churn"),
        ("ops",     "Operations"),
    ]
    by_cat: dict[str, list[str]] = {}
    for cat, q in EXAMPLES:
        by_cat.setdefault(cat, []).append(q)

    for cat_key, cat_label in categories:
        st.markdown(
            f'<div class="empty-category">{cat_label}</div>',
            unsafe_allow_html=True,
        )
        qs = by_cat.get(cat_key, [])
        cols = st.columns(len(qs)) if qs else []
        for col, q in zip(cols, qs):
            with col:
                if st.button(q, key=f"es_{q[:25]}", use_container_width=True):
                    st.session_state.trigger_question = q
                    st.rerun()


# --- process new question ---

if question:
    q_num = stats["questions"] + 1

    # User turn
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(f'<div class="q-num">Question {q_num}</div>', unsafe_allow_html=True)
        st.markdown(question)

    # Assistant turn
    with st.chat_message("assistant"):
        tool_log_lines: list[str] = []

        with st.status("Investigating...", expanded=True) as status:
            def write_fn(msg: str) -> None:
                tool_log_lines.append(msg)
                status.write(msg)

            answer      = run_agent(question, verbose=False, write_fn=write_fn)
            chart_paths = get_generated_charts()

            n_tools = sum(1 for l in tool_log_lines if l.strip().startswith("["))
            status.update(
                label=f"Done · {n_tools} tool calls",
                state="complete",
                expanded=False,
            )

        st.markdown(answer)

        col_copy, _ = st.columns([1, 5])
        with col_copy:
            _copy_button(answer, key="cp_current")

        tool_log_text = "\n".join(l for l in tool_log_lines if l.strip())
        if tool_log_text:
            with st.expander("View investigation steps"):
                formatted = _format_tool_log(tool_log_lines)
                st.markdown(
                    f'<div class="tool-log">{formatted}</div>',
                    unsafe_allow_html=True,
                )

        # Read chart HTML now before a future run can overwrite the files
        chart_htmls: list[str] = []
        for path in chart_paths:
            if Path(path).exists():
                html_content = Path(path).read_text(encoding="utf-8")
                chart_htmls.append(html_content)
                components.html(html_content, height=420, scrolling=False)

        report_bytes: bytes | None = None
        report_path = Path("output/report.html")
        if report_path.exists():
            report_bytes = report_path.read_bytes()
            st.download_button(
                label="Download full report",
                data=report_bytes,
                file_name="report.html",
                mime="text/html",
                key="dl_current",
            )

        # Update session stats
        st.session_state.session_stats["questions"]  += 1
        st.session_state.session_stats["tool_calls"] += n_tools
        st.session_state.session_stats["charts"]     += len(chart_htmls)

        st.session_state.messages.append({
            "role":         "assistant",
            "content":      answer,
            "tool_log":     tool_log_text,
            "chart_htmls":  chart_htmls,
            "report_bytes": report_bytes,
        })
