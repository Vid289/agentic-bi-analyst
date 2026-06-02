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
from src.tools import get_generated_charts
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

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ── Dark sidebar ─────────────────────────────────── */

[data-testid="stSidebar"] {
    background-color: #0d1117 !important;
    border-right: 1px solid #21262d !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #c9d1d9 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #21262d !important;
    margin: 0.5rem 0 !important;
}
[data-testid="stSidebar"]::-webkit-scrollbar { width: 4px; }
[data-testid="stSidebar"]::-webkit-scrollbar-track { background: #0d1117; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
    background: #30363d;
    border-radius: 2px;
}

/* Sidebar query buttons */
[data-testid="stSidebar"] button {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #8b949e !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 0.72rem !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 6px !important;
    padding: 0.38rem 0.7rem !important;
    line-height: 1.45 !important;
    transition: background 0.15s, border-color 0.15s, color 0.15s !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(56, 139, 253, 0.1) !important;
    border-color: #388bfd !important;
    color: #58a6ff !important;
}
[data-testid="stSidebar"] button:hover p,
[data-testid="stSidebar"] button p {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 0.72rem !important;
}
[data-testid="stSidebar"] button:hover p { color: #58a6ff !important; }
[data-testid="stSidebar"] button p      { color: #8b949e !important; }

/* ── Sidebar: brand ──────────────────────────────── */

.sb-brand {
    padding: 0.3rem 0 0.5rem 0;
}
.sb-brand-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.88rem;
    font-weight: 600;
    color: #e6edf3;
    letter-spacing: 0.01em;
}
.sb-brand-ver {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    color: #484f58;
    margin-top: 0.18rem;
}

/* ── Sidebar: status rows ─────────────────────────── */

.sb-status {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 0.42rem 0.7rem;
    margin: 0.28rem 0;
}
.dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}
.dot-green { background: #3fb950; box-shadow: 0 0 5px #3fb95066; }
.dot-blue  { background: #58a6ff; box-shadow: 0 0 5px #58a6ff55; }
.sb-status-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.69rem;
    color: #8b949e;
    flex: 1;
}
.sb-status-val       { font-family: 'JetBrains Mono', monospace; font-size: 0.69rem; color: #3fb950; font-weight: 500; }
.sb-status-val-blue  { font-family: 'JetBrains Mono', monospace; font-size: 0.69rem; color: #58a6ff; font-weight: 500; }

/* ── Sidebar: section header ──────────────────────── */

.sb-head {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #484f58;
    margin: 0.1rem 0 0.4rem 0;
    padding-left: 0.1rem;
}

/* ── Sidebar: session stats grid ─────────────────── */

.sb-stats {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.35rem;
    margin-bottom: 0.1rem;
}
.sb-stat {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 0.45rem 0.35rem;
    text-align: center;
}
.sb-stat-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 600;
    color: #e6edf3;
    line-height: 1;
}
.sb-stat-lbl {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: #484f58;
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Sidebar: schema tree ─────────────────────────── */

.schema-tree { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; padding: 0.1rem 0; }
.schema-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.3rem 0.5rem;
    border-radius: 5px;
    transition: background 0.12s;
    cursor: default;
}
.schema-row:hover { background: #161b22; }
.schema-row-left  { display: flex; align-items: center; gap: 0.45rem; }
.schema-prefix    { color: #30363d; font-size: 0.65rem; }
.schema-tbl       { color: #79c0ff; }
.schema-cnt       { color: #484f58; font-size: 0.66rem; }
.schema-type      { font-size: 0.6rem; padding: 0.05rem 0.35rem; border-radius: 3px; margin-left: 0.3rem; }
.type-master      { background: #0f3d21; color: #3fb950; border: 1px solid #1a5c30; }
.type-txn         { background: #0c2c4a; color: #58a6ff; border: 1px solid #1a4775; }
.type-event       { background: #3d2800; color: #ffa657; border: 1px solid #5e3d00; }

/* ── Sidebar: pattern items ───────────────────────── */

.pattern-list { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; padding: 0.1rem 0; }
.pattern-row {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.28rem 0.5rem;
    border-radius: 5px;
    color: #8b949e;
    transition: background 0.12s;
    cursor: default;
    line-height: 1.4;
}
.pattern-row:hover { background: #161b22; color: #c9d1d9; }
.pattern-icon { color: #ffa657; flex-shrink: 0; margin-top: 0.05rem; }

/* ── Sidebar: capabilities list ──────────────────── */

.cap-list { font-family: 'JetBrains Mono', monospace; font-size: 0.71rem; padding: 0.1rem 0; }
.cap-row {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.27rem 0.5rem;
    border-radius: 5px;
    color: #8b949e;
    transition: background 0.12s;
    line-height: 1.4;
}
.cap-row:hover { background: #161b22; color: #c9d1d9; }
.cap-dot { width: 5px; height: 5px; border-radius: 50%; background: #388bfd; flex-shrink: 0; margin-top: 0.38rem; }
.cap-name { color: #c9d1d9; }
.cap-desc { color: #484f58; margin-left: 0.2rem; }

/* ── Terminal hero ────────────────────────────────── */

.terminal-window {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
}
.terminal-bar {
    background: #21262d;
    padding: 0.52rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    border-bottom: 1px solid #30363d;
}
.tr { width: 11px; height: 11px; border-radius: 50%; }
.tr-red    { background: #ff5f57; }
.tr-yellow { background: #febc2e; }
.tr-green  { background: #28c840; }
.terminal-tab {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.73rem;
    color: #8b949e;
    margin-left: 0.3rem;
}
.terminal-body {
    padding: 1.2rem 1.6rem 1.35rem 1.6rem;
    font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
    font-size: 0.81rem;
    line-height: 1.85;
    color: #c9d1d9;
}
.t-ps1  { color: #3fb950; }
.t-cmd  { color: #e6edf3; font-weight: 500; }
.t-flag { color: #79c0ff; }
.t-val  { color: #ffa657; }
.t-ok   { color: #3fb950; }
.t-dim  { color: #484f58; }
.t-gray { color: #8b949e; }

/* ── Tool log ─────────────────────────────────────── */

.tool-log {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
    font-size: 0.775rem;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 280px;
    overflow-y: auto;
}

/* ── Empty state ──────────────────────────────────── */

.empty-hint {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #484f58;
    margin-bottom: 0.6rem;
}
.empty-category {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #388bfd;
    margin: 1rem 0 0.4rem 0;
}

/* ── Chat: question number ────────────────────────── */

.q-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #484f58;
    margin-bottom: 0.2rem;
}

/* ── Copy button (rendered via components.html) ──── */

</style>
""", unsafe_allow_html=True)


# --- constants ---

# Table type determines the colour dot in the schema tree
_TABLE_TYPES = {
    "customers":       "master",
    "plans":           "master",
    "subscriptions":   "txn",
    "invoices":        "txn",
    "usage_events":    "txn",
    "support_tickets": "event",
    "churn_events":    "event",
}
_TYPE_LABEL = {"master": "ref", "txn": "txn", "event": "event"}

# Preferred display order for the schema tree
_TABLE_ORDER = [
    "customers", "plans", "subscriptions",
    "invoices", "usage_events", "support_tickets", "churn_events",
]

# Known patterns baked into the synthetic dataset
PATTERNS = [
    ("Pro price increase → churn spike", "Jun 2025"),
    ("EMEA pricing experiment → enterprise churn", "Q3 2025"),
    ("Low day-30 usage → 2× higher churn rate", "all time"),
    ("Enterprise: more tickets, yet higher CSAT", "all time"),
]

TOOLS = [
    ("run_sql",              "execute SELECT queries"),
    ("detect_anomalies",     "flag statistical outliers"),
    ("compare_cohort_rates", "z-test two groups"),
    ("investigate_drop",     "decompose a metric change"),
    ("generate_chart",       "line / bar charts"),
    ("list_tables",          "explore the schema"),
    ("describe_table",       "inspect columns + samples"),
]

EXAMPLES = [
    # (category, question)
    ("revenue",  "Why did MRR drop in Q3 2025?"),
    ("revenue",  "Which acquisition channels produce the highest LTV customers?"),
    ("churn",    "Which customer segments have the highest churn rate?"),
    ("churn",    "Compare enterprise vs pro plan churn rates"),
    ("ops",      "What is the relationship between support tickets and churn?"),
    ("ops",      "What happened to EMEA customers in Q3 2025?"),
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

if "messages"      not in st.session_state: st.session_state.messages      = []
if "trigger_question" not in st.session_state: st.session_state.trigger_question = None
if "session_stats" not in st.session_state:
    st.session_state.session_stats = {"questions": 0, "tool_calls": 0, "charts": 0}


# --- resolve input early ---
# st.chat_input renders at the bottom regardless of where it's called in the script.
# Reading the value here lets us suppress the empty-state cards if a question is incoming.

_typed   = st.chat_input("Ask a business question about Nimbus Analytics...")
_clicked = st.session_state.trigger_question
st.session_state.trigger_question = None
question: str | None = _clicked or _typed or None

stats = st.session_state.session_stats


# --- build sidebar HTML blocks ---

# Schema tree rows
schema_rows_html = ""
for i, name in enumerate(_ordered_tables):
    count    = schema_info.get(name, 0)
    prefix   = "└─" if i == len(_ordered_tables) - 1 else "├─"
    ttype    = _TABLE_TYPES.get(name, "txn")
    tlabel   = _TYPE_LABEL[ttype]
    dot_col  = {"master": "#3fb950", "txn": "#58a6ff", "event": "#ffa657"}[ttype]
    schema_rows_html += f"""
    <div class="schema-row">
        <div class="schema-row-left">
            <span class="schema-prefix">{prefix}</span>
            <span style="width:7px;height:7px;border-radius:50%;
                         background:{dot_col};display:inline-block;flex-shrink:0;"></span>
            <span class="schema-tbl">{name}</span>
            <span class="schema-type type-{ttype}">{tlabel}</span>
        </div>
        <span class="schema-cnt">{count:,}</span>
    </div>"""

# Pattern rows
pattern_rows_html = "".join(
    f'<div class="pattern-row">'
    f'<span class="pattern-icon">◈</span>'
    f'<span>{desc} <span style="color:#30363d">· {period}</span></span>'
    f'</div>'
    for desc, period in PATTERNS
)

# Tools rows
tools_rows_html = "".join(
    f'<div class="cap-row">'
    f'<div class="cap-dot"></div>'
    f'<div><span class="cap-name">{name}</span>'
    f'<span class="cap-desc"> — {desc}</span></div>'
    f'</div>'
    for name, desc in TOOLS
)

provider_label = "Anthropic Claude" if CONFIG.provider == "anthropic" else "Google Gemini"


# --- sidebar ---

with st.sidebar:

    # Brand
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-brand-name">▸ nimbus-bi-agent</div>
        <div class="sb-brand-ver">v1.0 · agentic sql analyst</div>
    </div>
    """, unsafe_allow_html=True)

    # Connection + model status
    st.markdown(f"""
    <div class="sb-status">
        <div class="dot dot-green"></div>
        <span class="sb-status-label">database</span>
        <span class="sb-status-val">connected</span>
    </div>
    <div class="sb-status">
        <div class="dot dot-blue"></div>
        <span class="sb-status-label">model</span>
        <span class="sb-status-val-blue">{CONFIG.active_model}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Session stats — updates after every question
    st.markdown('<div class="sb-head">this session</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="sb-stats">
        <div class="sb-stat">
            <div class="sb-stat-val">{stats["questions"]}</div>
            <div class="sb-stat-lbl">queries</div>
        </div>
        <div class="sb-stat">
            <div class="sb-stat-val">{stats["tool_calls"]}</div>
            <div class="sb-stat-lbl">tool calls</div>
        </div>
        <div class="sb-stat">
            <div class="sb-stat-val">{stats["charts"]}</div>
            <div class="sb-stat-lbl">charts</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Schema explorer
    st.markdown(
        f'<div class="sb-head">saas.duckdb &nbsp;·&nbsp; Jan 2024 – Dec 2025</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="schema-tree">{schema_rows_html}</div>', unsafe_allow_html=True)

    st.divider()

    # Built-in patterns — teasers for the analyst to find
    st.markdown('<div class="sb-head">patterns in the data</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pattern-list">{pattern_rows_html}</div>', unsafe_allow_html=True)

    st.divider()

    # Tools
    st.markdown('<div class="sb-head">tools available</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cap-list">{tools_rows_html}</div>', unsafe_allow_html=True)

    st.divider()

    # Suggested queries
    st.markdown('<div class="sb-head">suggested queries</div>', unsafe_allow_html=True)
    for i, (_, ex) in enumerate(EXAMPLES):
        if st.button(f"> {ex}", key=f"sb_{i}", use_container_width=True):
            st.session_state.trigger_question = ex
            st.rerun()

    st.divider()

    if st.button("× clear conversation", key="clear_btn", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_stats = {"questions": 0, "tool_calls": 0, "charts": 0}
        st.rerun()


# --- terminal hero ---

st.markdown(f"""
<div class="terminal-window">
    <div class="terminal-bar">
        <div class="tr tr-red"></div>
        <div class="tr tr-yellow"></div>
        <div class="tr tr-green"></div>
        <span class="terminal-tab">nimbus-bi-agent — zsh</span>
    </div>
    <div class="terminal-body">
<span class="t-ps1">❯</span> <span class="t-cmd">python -m nimbus_agent</span> <span class="t-flag">--db</span> <span class="t-val">data/saas.duckdb</span> <span class="t-flag">--model</span> <span class="t-val">{CONFIG.active_model}</span> <span class="t-flag">--provider</span> <span class="t-val">{CONFIG.provider}</span>

<span class="t-ok">✓</span> <span class="t-gray">database connected  </span><span style="color:#c9d1d9">{total_rows:,} rows across {table_count} tables  (Jan 2024 – Dec 2025)</span>
<span class="t-ok">✓</span> <span class="t-gray">schema loaded       </span><span style="color:#c9d1d9">{", ".join(_ordered_tables)}</span>
<span class="t-ok">✓</span> <span class="t-gray">tools registered    </span><span style="color:#c9d1d9">run_sql · detect_anomalies · compare_cohort_rates · investigate_drop · generate_chart</span>
<span class="t-ok">✓</span> <span class="t-gray">session             </span><span style="color:#c9d1d9">{stats["questions"]} quer{"y" if stats["questions"] == 1 else "ies"} · {stats["tool_calls"]} tool calls · {stats["charts"]} charts generated</span>
<span class="t-ok">✓</span> <span class="t-gray">agent ready         </span><span style="color:#3fb950">ask a question to begin ↓</span>
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
            parts.append(f'<span style="color:#79c0ff">{esc}</span>')
        elif line.startswith("   ->"):
            parts.append(f'<span style="color:#86efac">{esc}</span>')
        else:
            parts.append(f'<span style="color:#8b949e">{esc}</span>')
    return "\n".join(parts)


def _copy_button(text: str, key: str) -> None:
    """Render a copy-to-clipboard button using the browser clipboard API."""
    # json.dumps safely escapes the text as a JS string literal
    js_str = json.dumps(text)
    components.html(
        f"""
        <button
            onclick="navigator.clipboard.writeText({js_str}).then(()=>{{
                this.textContent='✓ copied';
                this.style.color='#3fb950';
                this.style.borderColor='#3fb950';
                setTimeout(()=>{{ this.textContent='📋 copy answer'; this.style.color=''; this.style.borderColor=''; }}, 1800);
            }})"
            style="background:#161b22;border:1px solid #30363d;color:#8b949e;
                   border-radius:5px;padding:3px 11px;
                   font-family:'JetBrains Mono','Fira Code',monospace;
                   font-size:11px;cursor:pointer;transition:all 0.2s;">
            📋 copy answer
        </button>
        """,
        height=34,
    )


def _render_assistant(msg: dict, idx: int) -> None:
    """Render an assistant message: answer, copy button, tool log, charts, download."""
    st.markdown(msg["content"])

    # Action row: copy + investigation steps + download
    col_copy, col_gap = st.columns([1, 4])
    with col_copy:
        _copy_button(msg["content"], key=f"cp_{idx}")

    if msg.get("tool_log"):
        with st.expander("🔍 Investigation steps"):
            formatted = _format_tool_log(msg["tool_log"].split("\n"))
            st.markdown(
                f'<div class="tool-log">{formatted}</div>',
                unsafe_allow_html=True,
            )

    for chart_html in msg.get("chart_htmls", []):
        components.html(chart_html, height=420, scrolling=False)

    if msg.get("report_bytes"):
        st.download_button(
            label="⬇ Download full report",
            data=msg["report_bytes"],
            file_name="report.html",
            mime="text/html",
            key=f"dl_{idx}",
        )


# --- render existing chat history ---

for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            # Show question number above the message
            q_num = sum(1 for m in st.session_state.messages[:idx+1] if m["role"] == "user")
            st.markdown(
                f'<div class="q-num">Q{q_num}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(msg["content"])
        else:
            _render_assistant(msg, idx)


# --- empty state ---
# Show category-organised prompt cards when no conversation has started yet.

if not st.session_state.messages and not question:
    st.markdown(
        '<p class="empty-hint"># select a prompt to begin, or type your own question below</p>',
        unsafe_allow_html=True,
    )

    categories = [
        ("revenue",  "📈 Revenue"),
        ("churn",    "📉 Churn"),
        ("ops",      "🔧 Operations"),
    ]

    # Group examples by category
    by_cat: dict[str, list[str]] = {}
    for cat, q in EXAMPLES:
        by_cat.setdefault(cat, []).append(q)

    for cat_key, cat_label in categories:
        st.markdown(f'<div class="empty-category">{cat_label}</div>', unsafe_allow_html=True)
        qs = by_cat.get(cat_key, [])
        cols = st.columns(len(qs)) if qs else []
        for i, (col, q) in enumerate(zip(cols, qs)):
            with col:
                if st.button(q, key=f"es_{cat_key}_{i}", use_container_width=True):
                    st.session_state.trigger_question = q
                    st.rerun()


# --- process new question ---

if question:
    q_num = stats["questions"] + 1

    # User turn
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(f'<div class="q-num">Q{q_num}</div>', unsafe_allow_html=True)
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
                label=f"Investigation complete · {n_tools} tool calls",
                state="complete",
                expanded=False,
            )

        st.markdown(answer)

        # Copy button
        col_copy, _ = st.columns([1, 4])
        with col_copy:
            _copy_button(answer, key="cp_current")

        # Tool log
        tool_log_text = "\n".join(l for l in tool_log_lines if l.strip())
        if tool_log_text:
            with st.expander("🔍 Investigation steps"):
                formatted = _format_tool_log(tool_log_lines)
                st.markdown(
                    f'<div class="tool-log">{formatted}</div>',
                    unsafe_allow_html=True,
                )

        # Charts — read HTML now before a future run can overwrite the files
        chart_htmls: list[str] = []
        for path in chart_paths:
            if Path(path).exists():
                html_content = Path(path).read_text(encoding="utf-8")
                chart_htmls.append(html_content)
                components.html(html_content, height=420, scrolling=False)

        # Report download
        report_bytes: bytes | None = None
        report_path = Path("output/report.html")
        if report_path.exists():
            report_bytes = report_path.read_bytes()
            st.download_button(
                label="⬇ Download full report",
                data=report_bytes,
                file_name="report.html",
                mime="text/html",
                key="dl_current",
            )

        # Update session stats
        st.session_state.session_stats["questions"]  += 1
        st.session_state.session_stats["tool_calls"] += n_tools
        st.session_state.session_stats["charts"]     += len(chart_htmls)

        # Persist to session state
        st.session_state.messages.append({
            "role":         "assistant",
            "content":      answer,
            "tool_log":     tool_log_text,
            "chart_htmls":  chart_htmls,
            "report_bytes": report_bytes,
        })
