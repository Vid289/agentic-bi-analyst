"""
report.py — Assembles the agent's findings into an HTML report.

Takes the original question, the agent's final answer, and any chart
files generated during the investigation, and produces a single
self-contained HTML file in the output/ directory.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def generate_report(
    question: str,
    answer: str,
    chart_paths: list[str] | None = None,
) -> str:
    """
    Write output/report.html and return its path.

    Args:
        question:    The original business question.
        answer:      The agent's final plain-text answer.
        chart_paths: List of HTML chart files to embed in the report.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Wrap each non-empty line of the answer in a <p> tag
    answer_html = "\n".join(
        f"<p>{line}</p>"
        for line in answer.strip().split("\n")
        if line.strip()
    )

    # Embed charts using relative paths so the report is portable
    charts_html = ""
    if chart_paths:
        for path in chart_paths:
            # Use just the filename so links work from the output/ directory
            fname = Path(path).name
            charts_html += (
                f'<div class="chart">'
                f'<iframe src="{fname}" width="100%" height="460" frameborder="0"></iframe>'
                f'</div>\n'
            )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Report — {question[:70]}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f9f9f9;
      color: #222;
      padding: 40px 20px;
    }}
    .container {{
      max-width: 880px;
      margin: 0 auto;
      background: #fff;
      border-radius: 8px;
      padding: 40px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }}
    .label {{
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #888;
      margin-bottom: 8px;
    }}
    .question {{
      font-size: 1.3rem;
      font-weight: 600;
      color: #111;
      margin-bottom: 32px;
      padding-bottom: 20px;
      border-bottom: 1px solid #eee;
    }}
    .answer p {{
      line-height: 1.75;
      margin-bottom: 12px;
      color: #333;
    }}
    .charts {{
      margin-top: 36px;
    }}
    .chart {{
      margin-bottom: 24px;
      border: 1px solid #eee;
      border-radius: 6px;
      overflow: hidden;
    }}
    .footer {{
      margin-top: 40px;
      font-size: 0.8rem;
      color: #aaa;
      border-top: 1px solid #eee;
      padding-top: 16px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="label">Nimbus Analytics — Analyst Report</div>
    <div class="question">{question}</div>
    <div class="answer">{answer_html}</div>
    {f'<div class="charts">{charts_html}</div>' if charts_html else ''}
    <div class="footer">Generated {timestamp}</div>
  </div>
</body>
</html>"""

    report_path = OUTPUT_DIR / "report.html"
    report_path.write_text(html, encoding="utf-8")
    return str(report_path)
