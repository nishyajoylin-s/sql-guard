# sql-guard

> The open-source trust and observability layer for text-to-SQL and conversational BI agents.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)

---

## What it does

AI agents that write SQL are confidently wrong a lot of the time. The SQL runs, the number looks plausible, and nobody notices the agent used the wrong column, made up a join, or silently redefined a KPI.

sql-guard wraps any text-to-SQL agent and **verifies every answer in real time** before it reaches a stakeholder. Every query gets:

- A **trust score** from 0 to 1
- A list of **flagged issues** with plain-language explanations
- An entry in an **event store** that powers a live observability dashboard

Works with Vanna AI, Dataherald, Wren AI, dbt-mcp, Snowflake Cortex Analyst, Microsoft Fabric Data Agent, and any custom Python callable.

---

## Who benefits

| Role | How sql-guard helps |
|---|---|
| **Data engineers** | Catch schema hallucinations and broken joins before they reach reports |
| **BI / analytics leads** | Track agent reliability over time, identify flaky metrics, audit every answer |
| **AI engineers building text-to-SQL** | Continuous trust scoring, CI gate, and regression alerts during development |
| **Data platform teams** | Centralized observability across multiple text-to-SQL tools from one dashboard |

---

## Features

- **Five built-in trust checks** — schema grounding, self-consistency, reverse translation, semantic-layer cross-check, result plausibility
- **Trust score per answer** — a single 0–1 score with per-check breakdown
- **Observability dashboard** — trust trends, top offenders, latency P50/P95, token usage, drill-through to every flagged call
- **Vendor neutral** — one integration surface, any backend
- **Event store included** — DuckDB locally, Postgres for hosted deployments
- **Semantic layer aware** — first-class support for dbt MetricFlow and Cube
- **Pluggable checks** — write your own in one file
- **CI friendly** — exits non-zero when average trust score drops below threshold
- **Alert webhooks** — Slack and Teams for low-trust regressions

---

## How it works

Every call to `guard.ask(...)` runs through five independent checks. Each returns a score and findings. The final trust score is a weighted aggregate.

| Check | What it catches |
|---|---|
| **Schema grounding** | Tables, columns, or functions that don't exist in the warehouse |
| **Self-consistency** | The agent disagreeing with itself across repeated runs |
| **Reverse translation** | SQL that answers a different question than the user actually asked |
| **Semantic-layer cross-check** | Agent answers that contradict the sanctioned MetricFlow or Cube metric |
| **Result plausibility** | Numbers outside a believable range for that metric |

```
  ┌─────────────────────────┐
  │   Your text-to-SQL      │
  │        agent            │
  └────────────┬────────────┘
               │  question + SQL + result
               ▼
  ┌─────────────────────────┐
  │        sql-guard        │
  │                         │
  │  schema grounding       │
  │  self-consistency       │
  │  reverse translation    │
  │  semantic cross-check   │
  │  result plausibility    │
  │                         │
  │  → trust score (0–1)    │
  │  → flags + explanation  │
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │       event store       │  DuckDB (local) · Postgres (hosted)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │       dashboard         │  localhost:8501
  └─────────────────────────┘
```

---

## Run locally

### Prerequisites

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- Ollama running locally with a model pulled (for LLM-based checks)

### 1. Clone and install

```bash
git clone https://github.com/your-org/sql-guard
cd sql-guard

# With uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### 2. (Optional) Pull an LLM model for checks

```bash
ollama pull qwen2.5-coder:7b
```

### 3. Configure

Create `.sql-guard.yml` in your project root (or skip for defaults):

```yaml
llm:
  provider: ollama
  model: qwen2.5-coder:7b

event_store: duckdb:///sql_guard.db

checks:
  schema_grounding:
    enabled: true
    weight: 1.0
  self_consistency:
    enabled: true
    samples: 3
  reverse_translation:
    enabled: true
  result_plausibility:
    enabled: true

alerts:
  slack_webhook: ${SLACK_WEBHOOK_URL}   # optional
  trigger_below: 0.6
```

### 4. Start the API server

```bash
uv run sql-guard serve
# → API running on http://localhost:8080
```

### 5. Open the dashboard

```bash
uv run sql-guard dashboard
# → Opens http://localhost:8501
```

### 6. Send your first event

```python
import httpx

httpx.post("http://localhost:8080/track", json={
    "question": "How many orders did we get last month?",
    "sql": "SELECT COUNT(*) FROM orders WHERE created_at >= '2024-03-01'",
    "result": [{"count": 1482}],
    "backend_name": "my-agent",
})
```

Then refresh the dashboard — your event appears with a trust score and any flagged issues.

---

## Python API

```python
from sql_guard import Guard
from sql_guard.backends import VannaBackend

guard = Guard(
    backend=VannaBackend(model="llama3.1"),
    semantic_layer="metricflow",
    event_store="duckdb:///sql_guard.db",
)

report = guard.ask("How much revenue did we make last month?")

print(report.trust_score)   # 0.92
print(report.answer)        # 3,812,447.00
print(report.flags)         # []
print(report.sql)           # SELECT SUM(net_revenue) FROM fct_orders WHERE ...
```

---

## CLI reference

| Command | What it does |
|---|---|
| `sql-guard ask "question"` | Ask a question through the configured backend and print the trust report |
| `sql-guard verify --sql "..." --question "..."` | Run trust checks on an existing SQL + question pair |
| `sql-guard dashboard` | Open the Streamlit observability dashboard on `localhost:8501` |
| `sql-guard serve` | Start the FastAPI server on `localhost:8080` |
| `sql-guard report --since 7d --format html` | Generate an HTML trust report for a time window |
| `sql-guard ci --minimum 0.75` | Exit non-zero if average trust score is below threshold (for CI pipelines) |

---

## Integration options

### Option A — Proxy (zero code changes)

Point your app at the sql-guard proxy instead of your text-to-SQL tool:

```
Before: POST https://my-vanna-server/ask
After:  POST http://localhost:8080/proxy/my-vanna
```

sql-guard forwards the request, returns the unchanged response, and tracks the event in the background.

### Option B — Push API

Call `/track` from your existing code after you get an answer:

```python
import httpx

httpx.post("http://localhost:8080/track", json={
    "question": question,
    "sql": sql,
    "result": result,
    "backend_name": "my-tool",
    "latency_ms": 430,
})
```

### Option C — Python library

Wrap calls directly with `guard.ask(...)` as shown above.

---

## Dashboard

Start the dashboard:

```bash
uv run streamlit run sql_guard/dashboard/app.py
# → http://localhost:8501
```

### Overview tab

**Health banner** — the first thing you see. HEALTHY / DEGRADED / CRITICAL derived from pass rate and average trust score. Tells you agent status without reading any numbers.

**KPI strip (10 metrics across two rows):**

| Metric | What it means |
|---|---|
| Total Queries | Questions answered in the selected window |
| Pass Rate | % of answers with trust score ≥ threshold |
| Avg Trust | Mean trust score across all checks (0 = untrustworthy, 1 = fully trusted) |
| Latency P50 | Median response time |
| Latency P95 | 95th-percentile response time — worst-case |
| Total Tokens | Token count reported by backends (for cost estimation) |
| Failed Queries | Queries where trust score < threshold |
| Uptime | % of time buckets that had at least one query |
| Active Periods | Time buckets with at least one query |
| Busy Periods | Buckets with above-average query volume |

**Charts (6 panels):**

| Chart | How to read it |
|---|---|
| Query Volume | Green = passed (≥ threshold), red = failed. Rising red = agent degrading. |
| Trust Score Trend | Should stay flat and high. Dip = recent answers less reliable. Y-axis is always 0–1. |
| Latency | Teal = P50, purple = P95. Widening gap = occasional slow outliers. |
| Flag Frequency | Which checks fail most. `sql_inconsistent` = agent disagrees with itself. `unknown_table` = hallucinated table. |
| Trust Distribution | Histogram across five 0.2-wide bands, red→green. Ideal: most answers in 0.8–1.0. |
| Token Usage | Total tokens per period. Spikes = unusually complex questions. |

**Low Trust Questions** — sortable table of worst-scoring events. Click any row to open drill-through.

**Event Detail** — full question, SQL, result, per-check bar chart (green ≥ 0.7, red < 0.7), and flag pills.

**Sidebar controls:** time window (1h / 24h / 7d / 30d), backend filter, pass threshold (0.50–0.95), offenders limit, auto-refresh (30s).

### Backends tab

Add, inspect, and test backends. Each backend has a proxy URL (`/proxy/{name}`) and a test endpoint to verify field mapping.

### About tab

Reference card for the trust scoring system, check descriptions, flag definitions, and integration options.

---

## API endpoints

The FastAPI server (`sql-guard serve`) exposes:

| Method | Path | Description |
|---|---|---|
| `POST` | `/track` | Push a question/SQL/result event for background trust checking |
| `POST` | `/proxy/{backend_name}` | Transparent proxy — forwards to configured backend, tracks in background |
| `GET` | `/api/backends` | List all configured backends |
| `POST` | `/api/backends` | Add or update a backend |
| `DELETE` | `/api/backends/{name}` | Remove a backend |
| `POST` | `/api/backends/{name}/test` | Send a test request to verify field mapping |
| `GET` | `/health` | Health check |

Interactive docs at `http://localhost:8080/docs`.

---

## Supported backends

| Backend | Status |
|---|---|
| Vanna AI | Supported |
| Dataherald | Supported |
| dbt-mcp | Supported |
| Custom (any Python callable) | Supported |
| Wren AI | Planned |
| Microsoft Fabric Data Agent | Planned |
| Snowflake Cortex Analyst | Planned |

Writing a new backend takes one class with two methods.

---

## Supported semantic layers

| Layer | Status |
|---|---|
| dbt Semantic Layer (MetricFlow) | Supported |
| Cube | Supported |
| LookML | Planned |

---

## Configuration reference

```yaml
# .sql-guard.yml

llm:
  provider: ollama          # ollama | openai | anthropic
  model: qwen2.5-coder:7b   # any model available in the provider

event_store: duckdb:///sql_guard.db   # or postgres://user:pass@host/db

checks:
  schema_grounding:
    enabled: true
    weight: 1.0
  self_consistency:
    enabled: true
    samples: 5             # how many times to re-ask the backend
    temperature: 0.3
  reverse_translation:
    enabled: true
    judge_model: llama3.1  # model used to judge question↔SQL alignment
  semantic_cross_check:
    enabled: true
    layer: metricflow       # metricflow | cube
    project_path: ./dbt_project
  result_plausibility:
    enabled: true
    baseline: rolling_30d  # rolling_30d | static
    sigma_threshold: 3     # flag if result deviates > N sigma from baseline

alerts:
  slack_webhook: ${SLACK_WEBHOOK_URL}
  teams_webhook: ${TEAMS_WEBHOOK_URL}
  trigger_below: 0.6       # fire alert when trust score < this

thresholds:
  ci_minimum_avg_trust: 0.75   # sql-guard ci fails below this

backends:
  - name: my-vanna
    url: https://my-vanna-server.com/ask
    method: POST
    question_field: question
    sql_field: sql
    result_field: result
```

---

## Contributing

Contributions welcome. New checks, backends, and semantic-layer adapters have the biggest impact.

```bash
git clone https://github.com/your-org/sql-guard
cd sql-guard
uv sync
uv run pytest
```

Good first issues are tagged on GitHub.

---

## License

MIT
