"""
app.py — Streamlit chatbot UI for the Agentic BI Analyst.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import html as html_lib
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
    margin: 0.6rem 0 !important;
}

/* Sidebar scrollbar */
[data-testid="stSidebar"]::-webkit-scrollbar { width: 4px; }
[data-testid="stSidebar"]::-webkit-scrollbar-track { background: #0d1117; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
    background: #30363d;
    border-radius: 2px;
}

/* Sidebar buttons — monospace, dark */
[data-testid="stSidebar"] button {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #8b949e !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 0.73rem !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 6px !important;
    padding: 0.4rem 0.75rem !important;
    line-height: 1.45 !important;
    transition: background 0.15s, border-color 0.15s, color 0.15s !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(56, 139, 253, 0.1) !important;
    border-color: #388bfd !important;
    color: #58a6ff !important;
}
[data-testid="stSidebar"] button:hover p {
    color: #58a6ff !important;
}
[data-testid="stSidebar"] button p {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 0.73rem !important;
    color: #8b949e !important;
}

/* ── Sidebar custom HTML ──────────────────────────── */

.sb-brand {
    padding: 0.4rem 0 0.6rem 0;
}
.sb-brand-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    font-weight: 600;
    color: #e6edf3;
    letter-spacing: 0.01em;
}
.sb-brand-ver {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #484f58;
    margin-top: 0.2rem;
}

/* Status row */
.sb-status {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 7px;
    padding: 0.5rem 0.75rem;
    margin: 0.35rem 0;
}
.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}
.dot-green { background: #3fb950; box-shadow: 0 0 5px #3fb95066; }
.dot-blue  { background: #58a6ff; box-shadow: 0 0 5px #58a6ff55; }
.sb-status-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.71rem;
    color: #8b949e;
    flex: 1;
}
.sb-status-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.71rem;
    color: #3fb950;
    font-weight: 500;
}
.sb-status-val-blue {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.71rem;
    color: #58a6ff;
    font-weight: 500;
}

/* Section headers */
.sb-head {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #484f58;
    margin: 0.1rem 0 0.45rem 0;
    padding-left: 0.1rem;
}

/* Schema tree */
.schema-tree {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    line-height: 1;
    padding: 0.1rem 0;
}
.schema-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.32rem 0.6rem;
    border-radius: 5px;
    transition: background 0.1s;
    cursor: default;
}
.schema-row:hover { background: #161b22; }
.schema-tree-line { color: #30363d; margin-right: 0.4rem; }
.schema-tbl  { color: #79c0ff; }
.schema-cnt  { color: #484f58; font-size: 0.68rem; }

/* Capabilities list */
.cap-list {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    line-height: 1;
    padding: 0.1rem 0;
}
.cap-row {
    display: flex;
    align-items: flex-start;
    gap: 0.55rem;
    padding: 0.3rem 0.5rem;
    border-radius: 5px;
    color: #8b949e;
    transition: background 0.1s;
}
.cap-row:hover { background: #161b22; color: #c9d1d9; }
.cap-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #388bfd;
    flex-shrink: 0;
    margin-top: 0.35rem;
}
.cap-text { line-height: 1.4; }

/* ── Terminal hero window ─────────────────────────── */

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
    padding: 0.55rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.55rem;
    border-bottom: 1px solid #30363d;
}
.tr { width: 12px; height: 12px; border-radius: 50%; }
.tr-red    { background: #ff5f57; }
.tr-yellow { background: #febc2e; }
.tr-green  { background: #28c840; }
.terminal-tab {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    color: #8b949e;
    margin-left: 0.35rem;
}
.terminal-body {
    padding: 1.25rem 1.6rem 1.4rem 1.6rem;
    font-family: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
    font-size: 0.82rem;
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
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 0.75rem;
}

</style>
""", unsafe_allow_html=True)


# --- cached schema info ---
# Queries the real database once per app session.

@st.cache_data
def _get_schema_info() -> dict[str, int]:
    """Return {table_name: row_count} for all tables in the database."""
    con = duckdb.connect(str(CONFIG.db_path), read_only=True)
    try:
        tables = con.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
        """).fetchall()
        return {
            name: con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for (name,) in tables
        }
    finally:
        con.close()


schema_info  = _get_schema_info()
total_rows   = sum(schema_info.values())
table_count  = len(schema_info)

# Preferred display order for the schema tree
_TABLE_ORDER = [
    "customers", "subscriptions", "invoices",
    "usage_events", "support_tickets", "churn_events", "plans",
]
# Build ordered list, fall back to whatever the DB has
_ordered_tables = [t for t in _TABLE_ORDER if t in schema_info]
_ordered_tables += [t for t in schema_info if t not in _TABLE_ORDER]


# --- session state ---

if "messages" not in st.session_state:
    st.session_state.messages = []

if "trigger_question" not in st.session_state:
    st.session_state.trigger_question = None


# --- resolve input early ---
# st.chat_input always renders at the bottom; calling it here reads the value.

_typed   = st.chat_input("Ask a business question about Nimbus Analytics...")
_clicked = st.session_state.trigger_question
st.session_state.trigger_question = None
question: str | None = _clicked or _typed or None


# --- sidebar ---

EXAMPLES = [
    "Why did MRR drop in Q3 2025?",
    "Which customer segments have the highest churn rate?",
    "What is the relationship between support tickets and churn?",
    "Which acquisition channels produce the highest LTV customers?",
    "Compare enterprise vs pro plan churn rates",
    "What happened to EMEA customers in Q3 2025?",
]

CAPABILITIES = [
    "natural language → SQL",
    "z-score anomaly detection",
    "two-proportion z-test (cohorts)",
    "dimension decomposition",
    "plotly chart generation",
    "multi-turn conversation",
    "anthropic · google gemini",
]

TOOLS = [
    ("run_sql",              "execute SELECT queries"),
    ("detect_anomalies",     "flag statistical outliers"),
    ("compare_cohort_rates", "z-test two groups"),
    ("investigate_drop",     "decompose metric changes"),
    ("generate_chart",       "line / bar charts"),
    ("list_tables",          "explore the schema"),
    ("describe_table",       "inspect columns + samples"),
]

provider_label = "Anthropic Claude" if CONFIG.provider == "anthropic" else "Google Gemini"

# --- build schema tree HTML ---
tree_rows = ""
for i, name in enumerate(_ordered_tables):
    count     = schema_info.get(name, 0)
    prefix    = "└─" if i == len(_ordered_tables) - 1 else "├─"
    fmt_count = f"{count:,}"
    tree_rows += f"""
    <div class="schema-row">
        <span>
            <span class="schema-tree-line">{prefix}</span>
            <span class="schema-tbl">{name}</span>
        </span>
        <span class="schema-cnt">{fmt_count}</span>
    </div>"""

# --- build capabilities HTML ---
cap_rows = "".join(
    f'<div class="cap-row"><div class="cap-dot"></div><div class="cap-text">{c}</div></div>'
    for c in CAPABILITIES
)

# --- build tools HTML ---
tool_rows = "".join(
    f'<div class="cap-row"><div class="cap-dot"></div>'
    f'<div class="cap-text"><span style="color:#c9d1d9">{name}</span>'
    f'<span style="color:#484f58"> — {desc}</span></div></div>'
    for name, desc in TOOLS
)

with st.sidebar:

    # Brand
    st.markdown(f"""
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

    # Schema tree
    st.markdown(f'<div class="sb-head">schema — {table_count} tables · {total_rows:,} rows</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="schema-tree">{tree_rows}</div>', unsafe_allow_html=True)

    st.divider()

    # Capabilities
    st.markdown('<div class="sb-head">capabilities</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cap-list">{cap_rows}</div>', unsafe_allow_html=True)

    st.divider()

    # Tools
    st.markdown('<div class="sb-head">tools available</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cap-list">{tool_rows}</div>', unsafe_allow_html=True)

    st.divider()

    # Suggested queries
    st.markdown('<div class="sb-head">suggested queries</div>', unsafe_allow_html=True)
    for i, ex in enumerate(EXAMPLES):
        if st.button(f"> {ex}", key=f"sb_{i}", use_container_width=True):
            st.session_state.trigger_question = ex
            st.rerun()

    st.divider()

    if st.button("× clear conversation", key="clear_btn", use_container_width=True):
        st.session_state.messages = []
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
<span class="t-ps1">❯</span> <span class="t-cmd">python -m nimbus_agent</span>
  <span class="t-flag">--db</span> <span class="t-val">data/saas.duckdb</span>
  <span class="t-flag">--model</span> <span class="t-val">{CONFIG.active_model}</span>
  <span class="t-flag">--provider</span> <span class="t-val">{CONFIG.provider}</span>

<span class="t-ok">✓</span> <span class="t-gray">database connected  </span><span style="color:#c9d1d9">{total_rows:,} rows across {table_count} tables</span>
<span class="t-ok">✓</span> <span class="t-gray">schema loaded       </span><span style="color:#c9d1d9">{", ".join(_ordered_tables)}</span>
<span class="t-ok">✓</span> <span class="t-gray">tools registered    </span><span style="color:#c9d1d9">run_sql · detect_anomalies · compare_cohort_rates · investigate_drop · generate_chart</span>
<span class="t-ok">✓</span> <span class="t-gray">agent ready         </span><span style="color:#c9d1d9">ask a question to begin ↓</span>
    </div>
</div>
""", unsafe_allow_html=True)


# --- helpers ---

def _format_tool_log(lines: list[str]) -> str:
    """
    Colour-code tool log lines for the terminal display.
      blue  → tool call  ([1] run_sql: ...)
      green → result preview (   -> ...)
      gray  → everything else
    """
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


def _render_assistant(msg: dict, dl_key: str) -> None:
    """Render an assistant message: answer text, tool log, charts, download."""
    st.markdown(msg["content"])

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
            key=dl_key,
        )


# --- render existing chat history ---

for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            _render_assistant(msg, dl_key=f"dl_{idx}")


# --- empty state ---
# Show prompt cards only when there's no conversation and no question coming in.

if not st.session_state.messages and not question:
    st.markdown(
        '<p class="empty-hint"># select a prompt or type your own question below</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, ex in enumerate(EXAMPLES):
        if cols[i % 2].button(ex, key=f"es_{i}", use_container_width=True):
            st.session_state.trigger_question = ex
            st.rerun()


# --- process new question ---

if question:
    # User turn
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
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

        # Tool log
        tool_log_text = "\n".join(l for l in tool_log_lines if l.strip())
        if tool_log_text:
            with st.expander("🔍 Investigation steps"):
                formatted = _format_tool_log(tool_log_lines)
                st.markdown(
                    f'<div class="tool-log">{formatted}</div>',
                    unsafe_allow_html=True,
                )

        # Charts — read HTML content now while files are fresh
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

        # Persist to session state
        st.session_state.messages.append({
            "role":         "assistant",
            "content":      answer,
            "tool_log":     tool_log_text,
            "chart_htmls":  chart_htmls,
            "report_bytes": report_bytes,
        })
