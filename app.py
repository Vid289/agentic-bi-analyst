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
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ── Animations ────────────────────────────────────── */

@keyframes livePulse {
    0%, 100% { opacity: 1;   transform: scale(1);   }
    50%       { opacity: 0.4; transform: scale(1.45); }
}
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0);    }
}

[data-testid="stChatMessage"] {
    animation: fadeSlideIn 0.26s ease both;
}

/* ── Layout ───────────────────────────────────────── */

.block-container {
    max-width: 760px !important;
    padding-top: 2rem !important;
    padding-bottom: 6rem !important;
}

/* ── Sidebar ──────────────────────────────────────── */

[data-testid="stSidebar"] {
    background-color: #111111 !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #c0c0c0 !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.06) !important;
    margin: 0.55rem 0 !important;
}
[data-testid="stSidebar"]::-webkit-scrollbar { width: 3px; }
[data-testid="stSidebar"]::-webkit-scrollbar-track { background: #111111; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.1);
    border-radius: 4px;
}

/* Sidebar suggested-question buttons */
[data-testid="stSidebar"] .stButton button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    color: #666 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.79rem !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 8px !important;
    padding: 0.38rem 0.72rem !important;
    line-height: 1.45 !important;
    transition: all 0.15s ease !important;
    letter-spacing: -0.005em !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(255,255,255,0.04) !important;
    border-color: rgba(255,255,255,0.13) !important;
    color: #ccc !important;
}
[data-testid="stSidebar"] .stButton button p {
    font-size: 0.79rem !important;
    color: inherit !important;
}

/* ── Sidebar: brand ──────────────────────────────── */

.sb-brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0.2rem 0 0.65rem 0;
}
.sb-logo {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, #4f6ef7 0%, #7c3aed 100%);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.sb-brand-name {
    font-size: 0.91rem;
    font-weight: 600;
    color: #e8e8e8;
    letter-spacing: -0.02em;
    line-height: 1.2;
}
.sb-brand-sub {
    font-size: 0.69rem;
    color: #404040;
    margin-top: 0.08rem;
    letter-spacing: 0.01em;
}

/* ── Sidebar: status row ─────────────────────────── */

.sb-status {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 0.05rem 0 0.1rem 0;
}
.sb-status-item {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.69rem;
    color: #404040;
}
.live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #22c55e;
    flex-shrink: 0;
    animation: livePulse 2.5s ease-in-out infinite;
}
.model-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #6366f1;
    flex-shrink: 0;
}

/* ── Sidebar: section label ──────────────────────── */

.sb-label {
    font-size: 0.62rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #2e2e2e;
    margin: 0.1rem 0 0.5rem 0;
}

/* ── Sidebar: capability list ────────────────────── */

.cap-row {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.3rem 0.4rem;
    border-radius: 6px;
    transition: background 0.12s;
    margin-bottom: 0.04rem;
}
.cap-row:hover { background: rgba(255,255,255,0.03); }
.cap-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.cap-text { font-size: 0.77rem; color: #5a5a5a; line-height: 1.3; }

/* ── Sidebar: session stats ──────────────────────── */

.sb-stats {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.4rem;
}
.sb-stat {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 0.5rem 0.3rem;
    text-align: center;
}
.sb-stat-val {
    font-size: 1rem;
    font-weight: 600;
    color: #e0e0e0;
    line-height: 1;
    letter-spacing: -0.02em;
}
.sb-stat-lbl {
    font-size: 0.59rem;
    color: #363636;
    margin-top: 0.22rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}

/* ── Sidebar: schema list ────────────────────────── */

.schema-list { margin: 0; padding: 0; }
.schema-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.26rem 0.4rem;
    border-radius: 6px;
    transition: background 0.1s;
}
.schema-item:hover { background: rgba(255,255,255,0.025); }
.schema-item-left  { display: flex; align-items: center; gap: 0.42rem; }
.schema-dot        { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.schema-name       { font-size: 0.76rem; color: #6e6e6e; }
.schema-badge {
    font-size: 0.55rem;
    padding: 0.03rem 0.33rem;
    border-radius: 3px;
    font-weight: 500;
}
.badge-ref   { background: rgba(34,197,94,0.1);  color: #4ade80; }
.badge-txn   { background: rgba(99,102,241,0.1); color: #818cf8; }
.badge-event { background: rgba(251,146,60,0.1); color: #fb923c; }
.schema-count {
    font-size: 0.67rem;
    color: #2e2e2e;
    font-variant-numeric: tabular-nums;
}

/* ── Welcome ──────────────────────────────────────── */

.welcome {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 4.5rem 1.5rem 2rem 1.5rem;
    animation: fadeSlideIn 0.4s ease both;
}
.welcome-title {
    font-size: 1.8rem;
    font-weight: 600;
    color: #e8e8e8;
    letter-spacing: -0.035em;
    line-height: 1.15;
    margin-bottom: 0.7rem;
}
.welcome-sub {
    font-size: 0.9rem;
    color: #555;
    line-height: 1.7;
    max-width: 400px;
    margin-bottom: 2.5rem;
    font-weight: 300;
}

/* ── Example chips ───────────────────────────────── */

.eg-category {
    font-size: 0.62rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #333;
    margin: 1.3rem 0 0.5rem 0;
    width: 100%;
    text-align: left;
}

/* Main-area chip buttons (example prompts) */
section[data-testid="stMain"] .stButton button {
    background: rgba(255,255,255,0.035) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: #7a7a7a !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.84rem !important;
    border-radius: 12px !important;
    padding: 0.65rem 1.05rem !important;
    line-height: 1.45 !important;
    transition: all 0.16s ease !important;
    text-align: left !important;
    justify-content: flex-start !important;
    letter-spacing: -0.01em !important;
    font-weight: 400 !important;
}
section[data-testid="stMain"] .stButton button:hover {
    background: rgba(255,255,255,0.07) !important;
    border-color: rgba(255,255,255,0.15) !important;
    color: #d0d0d0 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 24px rgba(0,0,0,0.4) !important;
}
section[data-testid="stMain"] .stButton button p {
    font-size: 0.84rem !important;
    color: inherit !important;
}

/* ── Chat: question label ────────────────────────── */

.q-label {
    font-size: 0.62rem;
    font-weight: 500;
    color: #2e2e2e;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 0.35rem;
}

/* ── Tool log ────────────────────────────────────── */

.tool-log {
    background: #0c0c0c;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 0.85rem 1.05rem;
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Menlo', monospace;
    font-size: 0.73rem;
    line-height: 1.8;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 260px;
    overflow-y: auto;
}
.tool-log::-webkit-scrollbar { width: 3px; }
.tool-log::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.07);
    border-radius: 4px;
}

/* ── Download button ─────────────────────────────── */

section[data-testid="stMain"] .stDownloadButton button {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: #505050 !important;
    border-radius: 8px !important;
    font-size: 0.79rem !important;
    letter-spacing: -0.005em !important;
    transition: all 0.15s !important;
}
section[data-testid="stMain"] .stDownloadButton button:hover {
    background: rgba(255,255,255,0.06) !important;
    border-color: rgba(255,255,255,0.14) !important;
    color: #aaa !important;
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

# Simple dot + label capabilities (no big cards)
CAPABILITIES = [
    ("#6b9dff", "Revenue & MRR tracking"),
    ("#3dd68c", "Customer churn analysis"),
    ("#5b8dee", "Root cause investigation"),
    ("#a78bfa", "Statistical anomaly detection"),
    ("#fbbf24", "Segment comparison testing"),
    ("#22d3ee", "Interactive 3D dashboards"),
    ("#555",    "Downloadable HTML reports"),
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
    ("revenue",   "Revenue"),
    ("churn",     "Churn"),
    ("ops",       "Operations"),
    ("dashboard", "Dashboards"),
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

# Capability rows (simple dot + text)
_cap_rows_html = ""
for color, label in CAPABILITIES:
    _cap_rows_html += f"""
    <div class="cap-row">
        <span class="cap-dot" style="background:{color}"></span>
        <span class="cap-text">{label}</span>
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

    # Brand + logo
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-logo">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"
                 xmlns="http://www.w3.org/2000/svg">
                <rect x="1"   y="9" width="3" height="6" rx="0.75" fill="white" opacity="0.9"/>
                <rect x="6.5" y="5" width="3" height="10" rx="0.75" fill="white" opacity="0.9"/>
                <rect x="12"  y="1" width="3" height="14" rx="0.75" fill="white" opacity="0.9"/>
            </svg>
        </div>
        <div>
            <div class="sb-brand-name">Nimbus Analytics</div>
            <div class="sb-brand-sub">Agentic BI Analyst</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Live status + model
    st.markdown(f"""
    <div class="sb-status">
        <span class="sb-status-item">
            <span class="live-dot"></span>Connected
        </span>
        <span class="sb-status-item">
            <span class="model-dot"></span>{CONFIG.active_model}
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Capabilities
    st.markdown('<div class="sb-label">Capabilities</div>', unsafe_allow_html=True)
    st.markdown(_cap_rows_html, unsafe_allow_html=True)

    st.divider()

    # Session stats
    st.markdown('<div class="sb-label">Session</div>', unsafe_allow_html=True)
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
        '<div class="sb-label">Database &middot; 2024 – 2025</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="schema-list">{_schema_html}</div>', unsafe_allow_html=True)

    st.divider()

    # Suggested questions
    st.markdown('<div class="sb-label">Try asking</div>', unsafe_allow_html=True)
    for i, (_, ex) in enumerate(EXAMPLES):
        if st.button(ex, key=f"sb_{i}", use_container_width=True):
            st.session_state.trigger_question = ex
            st.rerun()

    st.divider()

    if st.button("Clear conversation", key="clear_btn", use_container_width=True):
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
            parts.append(f'<span style="color:#6b9dff">{esc}</span>')
        elif line.startswith("   ->"):
            parts.append(f'<span style="color:#3dd68c">{esc}</span>')
        else:
            parts.append(f'<span style="color:#3a3a3a">{esc}</span>')
    return "\n".join(parts)


def _copy_button(text: str, key: str) -> None:
    """Render a copy-to-clipboard button using the browser clipboard API."""
    js_str = json.dumps(text)
    components.html(
        f"""
        <button
            onclick="navigator.clipboard.writeText({js_str}).then(()=>{{
                this.textContent='Copied';
                this.style.color='#3dd68c';
                this.style.borderColor='rgba(61,214,140,0.3)';
                setTimeout(()=>{{
                    this.textContent='Copy';
                    this.style.color='';
                    this.style.borderColor='';
                }}, 1800);
            }})"
            style="background:transparent;
                   border:1px solid rgba(255,255,255,0.08);
                   color:#4a4a4a;
                   border-radius:7px;
                   padding:4px 13px;
                   font-family:'Inter',sans-serif;
                   font-size:11.5px;
                   cursor:pointer;
                   transition:all 0.15s;
                   letter-spacing:-0.005em;">
            Copy
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
            label="Download report",
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

    by_cat: dict[str, list[str]] = {}
    for cat, q in EXAMPLES:
        by_cat.setdefault(cat, []).append(q)

    st.markdown("""
    <div class="welcome">
        <div class="welcome-title">What would you like to explore?</div>
        <div class="welcome-sub">
            Ask anything about your Nimbus Analytics data — revenue trends,
            churn drivers, segment analysis, or an interactive dashboard.
        </div>
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
                label=f"Done · {n_steps} step{'s' if n_steps != 1 else ''}",
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
                label="Download report",
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
