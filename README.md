# Agentic BI Analyst
An AI agent that answers business questions about a SaaS company by querying a database, investigating the results, and writing back a plain-English answer.

It's different from a normal "natural language to SQL" tool because it doesn't just translate one question into one query. It plans, runs follow-up queries when something looks off, and explains its findings.

## Example
Ask:
> Why did MRR drop in Q3 2025?

The agent will write SQL to confirm the drop, break it down by region and plan tier, look at churn reasons in that window, and come back with something like:

> Q3 2025 MRR dropped by ~$X due to enterprise churn in EMEA. 23 enterprise customers in that region cancelled between July and September, citing price as the reason. This lines up with a regional pricing experiment that ran in Q3.

## How it works
The core is a simple loop:

1. Send the user's question to an LLM along with the database schema and a set of tools the LLM can call (`list_tables`, `describe_table`, `run_sql`).
2. The LLM either answers in plain text, or asks to call a tool.
3. If it asks for a tool, run it and send the result back. Repeat.
4. When the LLM is satisfied, return the final answer.

There's a hard cap on iterations so the loop can't run forever.

## Tech stack
- Python 3.10+
- DuckDB (local analytical SQL database)
- Anthropic Claude or Google Gemini (configurable)
- pandas, numpy, Faker for synthetic data generation

## Switching LLM providers
The agent works with either Claude or Gemini. Change one line in `.env`:

```
LLM_PROVIDER=anthropic   # paid API, no rate limits
LLM_PROVIDER=google      # free tier, rate-limited (5 req/min on Flash)
```

No code changes needed — the provider layer in `src/llm_provider.py` handles the differences.

## Project structure
```
agentic-bi-analyst/
├── README.md
├── requirements.txt
├── .env.example
├── database/
│   ├── schema.sql            # Table definitions
│   ├── generate_data.py      # Synthetic data generator
│   └── init_db.py            # Creates the database and loads data
├── src/
│   ├── config.py             # Loads settings from .env
│   ├── schema_introspection.py
│   ├── tools.py              # list_tables, describe_table, run_sql
│   ├── llm_provider.py       # Anthropic + Gemini abstraction
│   ├── agent.py              # The agent loop
│   └── cli.py                # Terminal interface
└── data/                     # DuckDB file lives here (gitignored)
```

## Setup
```bash
git clone https://github.com/Vid289/agentic-bi-analyst.git
cd agentic-bi-analyst
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add either an Anthropic or Google API key
```

Then build the database:
```bash
python database/init_db.py
```

And run the agent:
```bash
python -m src.cli
```

## The dataset
Two years (Jan 2024 – Dec 2025) of synthetic data for a fictional SaaS company called Nimbus Analytics:

| Table | Rows | What's in it |
|---|---|---|
| customers | ~2,000 | Company accounts with industry, size, region |
| plans | 4 | Free, Starter, Pro, Enterprise tiers |
| subscriptions | ~3,000 | Plan history per customer (upgrades, downgrades, churn) |
| usage_events | ~1M | Daily product engagement per customer |
| support_tickets | ~5,000 | Tickets with priority, category, CSAT |
| churn_events | ~500 | Cancellations with reason |
| invoices | ~13,000 | Monthly billing records |

The data has a few patterns built in so the agent has interesting things to find:
- A Pro plan price increase in June 2025 caused a churn spike on that tier
- An EMEA pricing experiment in Q3 2025 led to enterprise customer cancellations
- Customers with low usage in their first 30 days churn at roughly twice the normal rate
- Enterprise customers file more tickets but report higher satisfaction

## Status
- [x] Phase 1 — Project scaffold and synthetic database
- [x] Phase 2 — Agent loop with tool use and multi-provider LLM support
- [ ] Phase 3 — Statistical anomaly detection and root-cause investigation
- [ ] Phase 4 — Auto-generated visualizations and written summaries
- [ ] Phase 5 — Streamlit UI and deployment

## Notes
This is a portfolio project. The data is synthetic and the company is fictional. The architecture is intentionally simple — a custom agent loop instead of a framework like LangChain — so the mechanics are visible and easy to follow.
