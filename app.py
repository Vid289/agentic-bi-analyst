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

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ── Animations ────────────────────────────────────── */

@keyframes statusPulse {
    0%   { box-shadow: 0 0 0 0   rgba(74, 222, 128, 0.55); }
    60%  { box-shadow: 0 0 0 7px rgba(74, 222, 128, 0);    }
    100% { box-shadow: 0 0 0 0   rgba(74, 222, 128, 0);    }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0);    }
}
@keyframes subtleFloat {
    0%, 100% { transform: translateY(0px);  }
    50%       { transform: translateY(-6px); }
}

/* Apply fadeInUp to every chat message bubble */
[data-testid="stChatMessage"] {
    animation: fadeInUp 0.35s ease both;
}

/* ── Layout ────────────────────────────────────────── */

/* Constrain the main content column to a readable width */
.block-container {
    max-width: 820px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 5rem !important;
}

/* ── Sidebar ──────────────────────────────────────── */

[data-testid="stSidebar"] {
    background-color: #0f172a !important;
    border-right: 1px solid #1e293b !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #cbd5e1 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #1e293b !important;
    margin: 0.5rem 0 !important;
}
[data-testid="stSidebar"]::-webkit-scrollbar { width: 3px; }
[data-testid="stSidebar"]::-webkit-scrollbar-track { background: #0f172a; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
    background: #334155;
    border-radius: 4px;
}

/* Sidebar suggested-question buttons */
[data-testid="stSidebar"] .stButton button {
    background: transparent !important;
    border: 1px solid #1e293b !important;
    color: #94a3b8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.81rem !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 8px !important;
    padding: 0.42rem 0.8rem !important;
    line-height: 1.45 !important;
    transition: all 0.18s ease !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(99, 102, 241, 0.09) !important;
    border-color: rgba(99, 102, 241, 0.35) !important;
    color: #a5b4fc !important;
    transform: translateX(2px) !important;
}
[data-testid="stSidebar"] .stButton button p {
    font-size: 0.81rem !important;
    color: inherit !important;
}

/* ── Sidebar: brand ─────────────────────────────────── */

.sb-brand {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.1rem 0 0.6rem 0;
}
.sb-brand-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; line-height: 1; flex-shrink: 0;
}
.sb-brand-name {
    font-size: 0.97rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1.2;
    letter-spacing: -0.01em;
}
.sb-brand-sub {
    font-size: 0.72rem;
    color: #475569;
    margin-top: 0.1rem;
}

/* ── Sidebar: live dot (animated) ──────────────────── */

.sb-pills {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin: 0.1rem 0 0.2rem 0;
}
.sb-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.32rem;
    border-radius: 20px;
    padding: 0.2rem 0.65rem;
    font-size: 0.72rem;
    font-weight: 500;
}
.pill-green {
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.25);
    color: #4ade80;
}
.pill-blue {
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.25);
    color: #818cf8;
}
.pill-dot {
    width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
.dot-on {
    background: #4ade80;
    animation: statusPulse 2s ease-in-out infinite;
}
.dot-model { background: #818cf8; }

/* ── Sidebar: section label ─────────────────────────── */

.sb-section {
    font-size: 0.66rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #334155;
    margin: 0.1rem 0 0.5rem 0;
}

/* ── Sidebar: capability cards ──────────────────────── */

.cap-card {
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    padding: 0.55rem 0.6rem;
    border-radius: 10px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
    cursor: default;
    margin-bottom: 0.2rem;
}
.cap-card:hover {
    background: rgba(99, 102, 241, 0.07);
    border-color: rgba(99, 102, 241, 0.22);
    transform: translateX(3px);
}
.cap-icon-box {
    width: 30px; height: 30px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.95rem; line-height: 1; flex-shrink: 0;
}
.cap-text { flex: 1; min-width: 0; }
.cap-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #e2e8f0;
    line-height: 1.2;
}
.cap-desc {
    font-size: 0.72rem;
    color: #64748b;
    line-height: 1.4;
    margin-top: 0.15rem;
}

/* ── Sidebar: session stats ─────────────────────────── */

.sb-stats {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.35rem;
}
.sb-stat {
    background: #0a1628;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 0.5rem 0.35rem;
    text-align: center;
}
.sb-stat-val {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1;
}
.sb-stat-lbl {
    font-size: 0.63rem;
    color: #475569;
    margin-top: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Sidebar: schema list ───────────────────────────── */

.schema-list { margin: 0; padding: 0; }
.schema-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.28rem 0.5rem;
    border-radius: 6px;
    transition: background 0.12s;
    cursor: default;
}
.schema-item:hover { background: rgba(255,255,255,0.03); }
.schema-item-left  { display: flex; align-items: center; gap: 0.45rem; }
.schema-dot        { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.schema-name       { font-size: 0.78rem; color: #94a3b8; }
.schema-badge {
    font-size: 0.58rem;
    padding: 0.04rem 0.38rem;
    border-radius: 4px;
    font-weight: 500;
}
.badge-ref   { background: rgba(34,197,94,0.1);  color: #4ade80; border: 1px solid rgba(34,197,94,0.2); }
.badge-txn   { background: rgba(99,102,241,0.1); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); }
.badge-event { background: rgba(251,146,60,0.1); color: #fb923c; border: 1px solid rgba(251,146,60,0.2); }
.schema-count { font-size: 0.7rem; color: #334155; }

/* ── Welcome screen ─────────────────────────────────── */

.welcome {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 3.5rem 1rem 2rem 1rem;
    animation: fadeInUp 0.5s ease both;
}
.welcome-icon {
    font-size: 3rem;
    line-height: 1;
    margin-bottom: 1.25rem;
    animation: subtleFloat 3.5s ease-in-out infinite;
    display: block;
}
.welcome-title {
    font-size: 1.65rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.025em;
    line-height: 1.2;
    margin-bottom: 0.55rem;
}
.welcome-sub {
    font-size: 0.95rem;
    color: #64748b;
    line-height: 1.6;
    max-width: 480px;
    margin-bottom: 2rem;
}
.welcome-divider {
    width: 40px; height: 2px;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    border-radius: 2px;
    margin-bottom: 1.75rem;
}
.eg-category {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6366f1;
    margin: 1.25rem 0 0.55rem 0;
    width: 100%;
    text-align: left;
}

/* ── Main chat: chip buttons (empty state) ──────────── */

section[data-testid="stMain"] .stButton button {
    background: rgba(30, 41, 59, 0.7) !important;
    border: 1px solid #334155 !important;
    color: #94a3b8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.83rem !important;
    border-radius: 10px !important;
    padding: 0.5rem 0.9rem !important;
    line-height: 1.4 !important;
    transition: all 0.2s ease !important;
    text-align: left !important;
    justify-content: flex-start !important;
}
section[data-testid="stMain"] .stButton button:hover {
    background: rgba(99, 102, 241, 0.1) !important;
    border-color: rgba(99, 102, 241, 0.4) !important;
    color: #c7d2fe !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(99, 102, 241, 0.14) !important;
}
section[data-testid="stMain"] .stButton button p {
    font-size: 0.83rem !important;
    color: inherit !important;
}

/* ── Chat: question label ───────────────────────────── */

.q-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.3rem;
}

/* ── Tool log ───────────────────────────────────────── */

.tool-log {
    background: #080f1e;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    font-family: 'SF Mono', 'Fira Code', 'Menlo', monospace;
    font-size: 0.75rem;
    line-height: 1.75;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 260px;
    overflow-y: auto;
}
.tool-log::-webkit-scrollbar { width: 4px; }
.tool-log::-webkit-scrollbar-thumb {
    background: #334155;
    border-radius: 4px;
}

/* ── Download button ────────────────────────────────── */

section[data-testid="stMain"] .stDownloadButton button {
    background: rgba(30, 41, 59, 0.6) !important;
    border: 1px solid #334155 !important;
    color: #94a3b8 !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    transition: all 0.18s !important;
}
section[data-testid="stMain"] .stDownloadButton button:hover {
    background: rgba(99, 102, 241, 0.1) !important;
    border-color: rgba(99, 102, 241, 0.4) !important;
    color: #a5b4fc !important;
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

# Business-language capability cards shown in the sidebar
CAPABILITIES = [
    ("📊", "#6366f1", "rgba(99,102,241,.15)",  "Revenue & MRR Tracking",
     "Monitor revenue trends, pricing impact, and growth over time"),
    ("👥", "#10b981", "rgba(16,185,129,.15)",  "Customer Churn Analysis",
     "Find out who's leaving, when, and what's driving it"),
    ("🔍", "#3b82f6", "rgba(59,130,246,.15)",  "Root Cause Investigation",
     "Break down any metric change by region, plan, or channel"),
    ("⚡", "#8b5cf6", "rgba(139,92,246,.15)",  "Anomaly Detection",
     "Automatically flag unusual spikes or drops in your data"),
    ("🧪", "#f59e0b", "rgba(245,158,11,.15)",  "Segment Comparison",
     "Test whether differences between groups are statistically significant"),
    ("📈", "#06b6d4", "rgba(6,182,212,.15)",   "Visual Dashboards",
     "Generate interactive charts and 3D analytics views"),
    ("📋", "#64748b", "rgba(100,116,139,.15)", "Downloadable Reports",
     "Export your findings as a formatted HTML report"),
]

EXAMPLES = [
    ("revenue",   "Why did MRR drop in Q3 2025?"),
    ("revenue",   "Which acquisition channels produce the highest LTV customers?"),
    ("churn",     "Which customer segments have the highest churn rate?"),
    ("churn",     "Compare enterprise vs pro plan churn rates"),
    ("ops",       "What is the relationship between support tickets and churn?"),
    ("ops",       "What happened to EMEA customers in Q3 2025?"),
    ("dashboard", "Show me the revenue dashboard"),
    ("dashboard", "Give me the full business overview dashboard"),
    ("dashboard", "Show me the churn analysis dashboard"),
]

_EXAMPLE_CATEGORIES = [
    ("revenue",   "📈 Revenue"),
    ("churn",     "📉 Churn"),
    ("ops",       "🔧 Operations"),
    ("dashboard", "📊 Dashboards"),
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


schema_info    = _get_schema_info()
total_rows     = sum(schema_info.values())
table_count    = len(schema_info)
provider_label = "Anthropic Claude" if CONFIG.provider == "anthropic" else "Google Gemini"

_ordered_tables = [t for t in _TABLE_ORDER if t in schema_info]
_ordered_tables += [t for t in schema_info if t not in _TABLE_ORDER]


# --- session state ---

if "messages"         not in st.session_state: st.session_state.messages         = []
if "trigger_question" not in st.session_state: st.session_state.trigger_question = None
if "session_stats"    not in st.session_state:
    st.session_state.session_stats = {"questions": 0, "tool_calls": 0, "charts": 0}


# --- resolve input early ---
# st.chat_input renders at the very bottom regardless of where it is called.

_typed   = st.chat_input("Ask me anything about your business data…")
_clicked = st.session_state.trigger_question
st.session_state.trigger_question = None
question: str | None = _clicked or _typed or None

stats = st.session_state.session_stats


# --- build sidebar HTML ---

# Capability cards
_cap_cards_html = ""
for emoji, color, bg, title, desc in CAPABILITIES:
    _cap_cards_html += f"""
    <div class="cap-card">
        <div class="cap-icon-box" style="background:{bg};">
            <span style="color:{color};">{emoji}</span>
        </div>
        <div class="cap-text">
            <div class="cap-title">{title}</div>
            <div class="cap-desc">{desc}</div>
        </div>
    </div>"""

# Schema rows
_schema_html = ""
for name in _ordered_tables:
    ttype, dot_col, badge_cls = _TABLE_TYPES.get(name, ("txn", "#818cf8", "badge-txn"))
    count = schema_info.get(name, 0)
    _schema_html += f"""
    <div class="schema-item">
        <div class="schema-item-left">
            <span class="schema-dot" style="background:{dot_col}"></span>
            <span class="schema-name">{name}</span>
            <span class="schema-badge {badge_cls}">{ttype}</span>
        </div>
        <span class="schema-count">{count:,}</span>
    </div>"""


# --- sidebar ---

with st.sidebar:

    # Brand block
    st.markdown(f"""
    <div class="sb-brand">
        <div class="sb-brand-icon">📊</div>
        <div>
            <div class="sb-brand-name">Nimbus Analytics</div>
            <div class="sb-brand-sub">Agentic BI Analyst</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Live status + model pill
    st.markdown(f"""
    <div class="sb-pills">
        <span class="sb-pill pill-green">
            <span class="pill-dot dot-on"></span> Live
        </span>
        <span class="sb-pill pill-blue">
            <span class="pill-dot dot-model"></span> {CONFIG.active_model}
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # What I can do
    st.markdown('<div class="sb-section">What I can do</div>', unsafe_allow_html=True)
    st.markdown(_cap_cards_html, unsafe_allow_html=True)

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
            <div class="sb-stat-lbl">Steps</div>
        </div>
        <div class="sb-stat">
            <div class="sb-stat-val">{stats["charts"]}</div>
            <div class="sb-stat-lbl">Charts</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Database schema
    st.markdown(
        f'<div class="sb-section">Database · Jan 2024 – Dec 2025</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="schema-list">{_schema_html}</div>', unsafe_allow_html=True)

    st.divider()

    # Suggested questions
    st.markdown('<div class="sb-section">Try asking…</div>', unsafe_allow_html=True)
    for i, (_, ex) in enumerate(EXAMPLES):
        if st.button(ex, key=f"sb_{i}", use_container_width=True):
            st.session_state.trigger_question = ex
            st.rerun()

    st.divider()

    if st.button("✕  Clear conversation", key="clear_btn", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_stats = {"questions": 0, "tool_calls": 0, "charts": 0}
        st.rerun()


# --- helpers ---

def _format_tool_log(lines: list[str]) -> str:
    """Colour-code tool log lines for the investigation panel."""
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
            parts.append(f'<span style="color:#475569">{esc}</span>')
    return "\n".join(parts)


def _copy_button(text: str, key: str) -> None:
    """Render a copy-to-clipboard button using the browser clipboard API."""
    js_str = json.dumps(text)
    components.html(
        f"""
        <button
            onclick="navigator.clipboard.writeText({js_str}).then(()=>{{
                this.textContent='Copied ✓';
                this.style.color='#4ade80';
                this.style.borderColor='rgba(74,222,128,0.4)';
                setTimeout(()=>{{
                    this.textContent='Copy answer';
                    this.style.color='';
                    this.style.borderColor='';
                }}, 1800);
            }})"
            style="background:transparent;border:1px solid #1e293b;color:#475569;
                   border-radius:7px;padding:4px 13px;font-family:'Inter',sans-serif;
                   font-size:12px;cursor:pointer;transition:all 0.2s;">
            Copy answer
        </button>
        """,
        height=34,
    )


def _render_assistant(msg: dict, idx: int) -> None:
    """Render a stored assistant message: answer, tool log, charts, download."""
    st.markdown(msg["content"])

    col_copy, _ = st.columns([1, 5])
    with col_copy:
        _copy_button(msg["content"], key=f"cp_{idx}")

    if msg.get("tool_log"):
        with st.expander("See how I found this"):
            fmt = _format_tool_log(msg["tool_log"].split("\n"))
            st.markdown(f'<div class="tool-log">{fmt}</div>', unsafe_allow_html=True)

    for chart_html in msg.get("chart_htmls", []):
        components.html(chart_html, height=420, scrolling=False)

    for dash_html in msg.get("dashboard_htmls", []):
        components.html(dash_html, height=960, scrolling=True)

    if msg.get("report_bytes"):
        st.download_button(
            label="⬇  Download full report",
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
            st.markdown(f'<div class="q-label">Question {q_num}</div>', unsafe_allow_html=True)
            st.markdown(msg["content"])
        else:
            _render_assistant(msg, idx)


# --- welcome / empty state ---

if not st.session_state.messages and not question:

    # Build per-category example buttons
    by_cat: dict[str, list[str]] = {}
    for cat, q in EXAMPLES:
        by_cat.setdefault(cat, []).append(q)

    st.markdown("""
    <div class="welcome">
        <span class="welcome-icon">📊</span>
        <div class="welcome-title">Hello! I'm your BI Analyst.</div>
        <div class="welcome-sub">
            Ask me anything about your Nimbus Analytics data — revenue trends,
            churn drivers, segment comparisons, or a full interactive dashboard.
        </div>
        <div class="welcome-divider"></div>
    </div>
    """, unsafe_allow_html=True)

    for cat_key, cat_label in _EXAMPLE_CATEGORIES:
        st.markdown(
            f'<div class="eg-category">{cat_label}</div>',
            unsafe_allow_html=True,
        )
        qs = by_cat.get(cat_key, [])
        if qs:
            cols = st.columns(len(qs))
            for col, q in zip(cols, qs):
                with col:
                    if st.button(q, key=f"es_{q[:30]}", use_container_width=True):
                        st.session_state.trigger_question = q
                        st.rerun()


# --- process new question ---

if question:
    q_num = stats["questions"] + 1

    # User bubble
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(f'<div class="q-label">Question {q_num}</div>', unsafe_allow_html=True)
        st.markdown(question)

    # Assistant bubble
    with st.chat_message("assistant"):
        tool_log_lines: list[str] = []

        with st.status("Analysing your data…", expanded=True) as status:
            def write_fn(msg_text: str) -> None:
                tool_log_lines.append(msg_text)
                status.write(msg_text)

            answer          = run_agent(question, verbose=False, write_fn=write_fn)
            chart_paths     = get_generated_charts()
            dashboard_paths = get_generated_dashboards()

            n_steps = sum(1 for l in tool_log_lines if l.strip().startswith("["))
            status.update(
                label=f"Analysis complete · {n_steps} step{'s' if n_steps != 1 else ''}",
                state="complete",
                expanded=False,
            )

        st.markdown(answer)

        col_copy, _ = st.columns([1, 5])
        with col_copy:
            _copy_button(answer, key="cp_current")

        tool_log_text = "\n".join(l for l in tool_log_lines if l.strip())
        if tool_log_text:
            with st.expander("See how I found this"):
                fmt = _format_tool_log(tool_log_lines)
                st.markdown(f'<div class="tool-log">{fmt}</div>', unsafe_allow_html=True)

        # Capture chart HTML now — file will be overwritten on the next run
        chart_htmls: list[str] = []
        for path in chart_paths:
            if Path(path).exists():
                content = Path(path).read_text(encoding="utf-8")
                chart_htmls.append(content)
                components.html(content, height=420, scrolling=False)

        # Dashboards — taller to give 3-D plots room to breathe
        dashboard_htmls: list[str] = []
        for path in dashboard_paths:
            if Path(path).exists():
                content = Path(path).read_text(encoding="utf-8")
                dashboard_htmls.append(content)
                components.html(content, height=960, scrolling=True)

        report_bytes: bytes | None = None
        report_path = Path("output/report.html")
        if report_path.exists():
            report_bytes = report_path.read_bytes()
            st.download_button(
                label="⬇  Download full report",
                data=report_bytes,
                file_name="report.html",
                mime="text/html",
                key="dl_current",
            )

        # Update session stats
        st.session_state.session_stats["questions"]  += 1
        st.session_state.session_stats["tool_calls"] += n_steps
        st.session_state.session_stats["charts"]     += len(chart_htmls) + len(dashboard_htmls)

        st.session_state.messages.append({
            "role":            "assistant",
            "content":         answer,
            "tool_log":        tool_log_text,
            "chart_htmls":     chart_htmls,
            "dashboard_htmls": dashboard_htmls,
            "report_bytes":    report_bytes,
        })
