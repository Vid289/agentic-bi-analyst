"""
app.py — Streamlit chatbot UI for the Agentic BI Analyst.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import html as html_lib
from pathlib import Path

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

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #0f2044 0%, #0e2d3d 55%, #0a2818 100%);
    border-radius: 16px;
    padding: 2.25rem 2.75rem;
    margin-bottom: 1.75rem;
    color: white;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
}
.hero-title {
    font-size: 1.85rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.2;
    margin: 0 0 0.5rem 0;
}
.hero-sub {
    color: rgba(255, 255, 255, 0.6);
    font-size: 0.92rem;
    line-height: 1.6;
    max-width: 620px;
    margin: 0;
}
.hero-pills {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 1.25rem;
}
.pill {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 999px;
    padding: 0.22rem 0.85rem;
    font-size: 0.74rem;
    color: rgba(255, 255, 255, 0.78);
    letter-spacing: 0.01em;
}

/* ── Sidebar brand ── */
.brand-block {
    padding: 0.25rem 0 0.75rem 0;
}
.brand-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.01em;
    line-height: 1.3;
}
.brand-sub {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 0.15rem;
}
.model-badge {
    display: inline-flex;
    align-items: center;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 999px;
    padding: 0.28rem 0.85rem;
    font-size: 0.76rem;
    color: #1e40af;
    font-weight: 500;
    margin-top: 0.6rem;
}

/* ── Dataset stats ── */
.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.45rem;
    margin: 0.5rem 0 0.25rem 0;
}
.stat-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.65rem 0.5rem;
    text-align: center;
}
.stat-val {
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1;
}
.stat-lbl {
    font-size: 0.67rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 0.25rem;
}

/* ── Section label ── */
.section-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin-bottom: 0.5rem;
}

/* ── Terminal tool log ── */
.tool-log {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Menlo', 'Consolas', monospace;
    font-size: 0.775rem;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 280px;
    overflow-y: auto;
}

/* ── Empty-state prompt cards ── */
.empty-state-hint {
    color: #64748b;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}

</style>
""", unsafe_allow_html=True)


# --- session state ---

if "messages" not in st.session_state:
    # Each message: {role, content, tool_log, chart_htmls, report_bytes}
    st.session_state.messages = []

if "trigger_question" not in st.session_state:
    st.session_state.trigger_question = None


# --- resolve input early ---
# st.chat_input always pins to the bottom regardless of where it's called.
# Reading it here lets us know whether a question is incoming before we render
# the empty-state cards, so those cards don't flash on the screen mid-run.

_typed   = st.chat_input("Ask a business question about Nimbus Analytics...")
_clicked = st.session_state.trigger_question
st.session_state.trigger_question = None           # clear so it doesn't re-fire
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

provider_label = "Anthropic Claude" if CONFIG.provider == "anthropic" else "Google Gemini"

with st.sidebar:
    st.markdown(f"""
    <div class="brand-block">
        <div class="brand-name">📊 Nimbus Analytics</div>
        <div class="brand-sub">Agentic BI Analyst</div>
        <div class="model-badge">⚡ {provider_label} &nbsp;·&nbsp; {CONFIG.active_model}</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="section-label">Dataset</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-val">7</div>
            <div class="stat-lbl">Tables</div>
        </div>
        <div class="stat-card">
            <div class="stat-val">~1.3M</div>
            <div class="stat-lbl">Rows</div>
        </div>
        <div class="stat-card">
            <div class="stat-val">24 mo</div>
            <div class="stat-lbl">History</div>
        </div>
        <div class="stat-card">
            <div class="stat-val">~2K</div>
            <div class="stat-lbl">Customers</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="section-label">Suggested questions</div>', unsafe_allow_html=True)
    for i, ex in enumerate(EXAMPLES):
        if st.button(ex, key=f"sb_{i}", use_container_width=True):
            st.session_state.trigger_question = ex
            st.rerun()

    st.divider()

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# --- hero header ---

st.markdown(f"""
<div class="hero">
    <div class="hero-title">📊 Agentic BI Analyst</div>
    <div class="hero-sub">
        Ask any business question about Nimbus Analytics. The agent queries the
        database, runs statistical tests, and explains exactly what it found —
        step by step.
    </div>
    <div class="hero-pills">
        <span class="pill">DuckDB · 1.3M rows</span>
        <span class="pill">SQL + Statistics + Charts</span>
        <span class="pill">7 tables · 2024–2025</span>
        <span class="pill">{provider_label}</span>
    </div>
</div>
""", unsafe_allow_html=True)


# --- helpers ---

def _format_tool_log(lines: list[str]) -> str:
    """
    Colour-code tool log lines for the terminal display.
      blue  → tool call  (e.g. [1] run_sql: ...)
      green → result preview  (lines starting with   ->)
      gray  → everything else (provider info, done line)
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
    """Render an assistant message: answer + tool log + charts + download."""
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
# Show clickable example cards only when there's no conversation yet and
# no question is already on its way in.

if not st.session_state.messages and not question:
    st.markdown(
        '<p class="empty-state-hint">Not sure where to start? Pick a question below.</p>',
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

            answer     = run_agent(question, verbose=False, write_fn=write_fn)
            chart_paths = get_generated_charts()

            # Count tool calls (lines like "[1] run_sql: ...")
            n_tools = sum(
                1 for line in tool_log_lines
                if line.strip().startswith("[")
            )
            status.update(
                label=f"Investigation complete · {n_tools} tool calls",
                state="complete",
                expanded=False,
            )

        # Answer
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

        # Charts — read the HTML files now while they're fresh.
        # Storing the content (not the path) means charts survive future runs
        # that might overwrite the files.
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

        # Persist this turn to session state so it re-renders on the next run
        st.session_state.messages.append({
            "role":        "assistant",
            "content":     answer,
            "tool_log":    tool_log_text,
            "chart_htmls": chart_htmls,
            "report_bytes": report_bytes,
        })
