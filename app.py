"""
app.py — Streamlit UI for the Agentic BI Analyst.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

from src.agent import run_agent
from src.tools import get_generated_charts

# --- page config ---

st.set_page_config(
    page_title="Agentic BI Analyst",
    page_icon="📊",
    layout="centered",
)

# --- header ---

st.title("Agentic BI Analyst")
st.caption("Ask a business question. The agent queries the database, runs statistics, and writes back a plain-English answer.")

st.divider()

# --- example questions ---

EXAMPLES = [
    "Why did MRR drop in Q3 2025?",
    "Which customer segments have the highest churn rate?",
    "What is the relationship between support ticket volume and churn?",
    "Which acquisition channels produce the highest LTV customers?",
]

st.markdown("**Example questions**")
cols = st.columns(2)
for i, example in enumerate(EXAMPLES):
    if cols[i % 2].button(example, use_container_width=True):
        st.session_state["question"] = example

# --- input ---

question = st.text_input(
    "Your question",
    value=st.session_state.get("question", ""),
    placeholder="Why did MRR drop in Q3 2025?",
)

run = st.button("Investigate", type="primary", disabled=not question)

# --- agent run ---

if run and question:
    st.divider()

    # st.status shows a live feed of tool calls while the agent runs
    with st.status("Running investigation...", expanded=True) as status:
        # write_fn routes agent log lines into the status box
        def write_fn(msg: str) -> None:
            status.write(msg)

        answer = run_agent(question, verbose=False, write_fn=write_fn)
        status.update(label="Investigation complete", state="complete", expanded=False)

    # --- answer ---

    st.subheader("Findings")
    st.markdown(answer)

    # --- charts ---

    chart_paths = get_generated_charts()
    if chart_paths:
        st.subheader("Charts")
        for path in chart_paths:
            html_content = Path(path).read_text(encoding="utf-8")
            components.html(html_content, height=460, scrolling=False)

    # --- report download ---

    report_path = Path("output/report.html")
    if report_path.exists():
        st.divider()
        st.download_button(
            label="Download full report",
            data=report_path.read_bytes(),
            file_name="report.html",
            mime="text/html",
        )
