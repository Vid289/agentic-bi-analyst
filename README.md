# 🤖 Agentic BI Analyst

An autonomous AI analyst that investigates business questions in natural language, queries a SaaS database, detects anomalies, generates visualizations, and writes executive summaries explaining *what* happened and *why*.

Unlike simple "natural language to SQL" tools, this is a true **agentic system**: it plans, executes multi-step investigations, self-corrects, and decides on its own what to investigate next based on what it finds.

## 🎯 What it does

Ask a question like:
> *"Why did MRR drop in Q3 2025?"*

The agent will autonomously:
1. **Plan** an investigation strategy
2. **Query** the database (writing its own SQL)
3. **Inspect** the results and decide follow-up queries (e.g., break down by region → by plan tier → by customer cohort)
4. **Detect anomalies** using statistical methods
5. **Visualize** the findings
6. **Write** an executive summary with root causes and recommended actions

## 🛠️ Tech stack

- **LLM:** Anthropic Claude (Sonnet 4.6)
- **Database:** DuckDB (in-process analytical SQL)
- **Agent orchestration:** Custom Python (no heavy framework — shows the mechanics)
- **Backend:** FastAPI
- **Frontend:** Streamlit
- **Visualization:** Plotly
- **Vector store:** ChromaDB (for semantic schema retrieval)
- **ML / Statistics:** scikit-learn, scipy

## 📂 Project structure

```
agentic-bi-analyst/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   └── saas.duckdb           # Generated synthetic database
├── database/
│   ├── schema.sql            # Table definitions
│   ├── generate_data.py      # Synthetic data generator with embedded patterns
│   └── init_db.py            # Creates DB and loads data
└── src/
    └── (agent code — coming in Phase 2)
```

## 🚀 Setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd agentic-bi-analyst
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

### 2. Get an Anthropic API key

Sign up at https://console.anthropic.com, create an API key, then:

```bash
cp .env.example .env
# Edit .env and paste your API key
```

### 3. Generate the synthetic SaaS database

```bash
python database/init_db.py
```

This creates `data/saas.duckdb` with 2 years of realistic synthetic SaaS data: customers, subscriptions, usage events, support tickets, churn events, and invoices — with intentional patterns embedded for the agent to discover.

### 4. (Coming next) Run the agent

```bash
# Phase 2 onward — not yet built
python src/agent.py
```

## 📊 The synthetic dataset

The dataset simulates a B2B SaaS company "Nimbus Analytics" over Jan 2024 – Dec 2025:

| Table | Rows | Description |
|---|---|---|
| `customers` | ~2,000 | Company accounts with industry, size, region |
| `plans` | 4 | Free, Starter, Pro, Enterprise tiers |
| `subscriptions` | ~3,000 | Plan changes over time (upgrades, downgrades) |
| `usage_events` | ~50,000 | Daily product engagement per customer |
| `support_tickets` | ~5,000 | Tickets with priority, category, CSAT |
| `churn_events` | ~150 | Cancellations with reason category |
| `invoices` | ~25,000 | Monthly billing records |

**Hidden patterns** intentionally embedded for the agent to surface:
- Q3 2025 EMEA revenue dropped due to a specific cause
- Customers with low first-30-day usage churn dramatically more
- Enterprise tier has highest CSAT but most tickets per account
- A specific plan migration in mid-2025 caused a churn spike

## 🗺️ Build phases

- [x] **Phase 1:** Project scaffold + synthetic database
- [ ] **Phase 2:** Core agent loop with SQL tool use
- [ ] **Phase 3:** Multi-step investigation + anomaly detection
- [ ] **Phase 4:** Auto-visualization + narrative writing
- [ ] **Phase 5:** Streamlit UI + deployment

## 📝 License

MIT
