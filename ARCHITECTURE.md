# sql-guard Architecture

## Overview

sql-guard is a trust and observability layer that sits between a user (or application) and any text-to-SQL agent. Every question → SQL → result triple is scored for trustworthiness in real time before it reaches a stakeholder.

```
User / App
    │
    │  question
    ▼
┌──────────────┐     question      ┌──────────────────────┐
│  sql-guard   │ ──────────────▶  │  Text-to-SQL backend  │
│  proxy or    │ ◀──────────────  │  (Vanna, Dataherald,  │
│  push API    │   sql + result   │   dbt-mcp, custom…)   │
└──────┬───────┘                  └──────────────────────┘
       │
       │  question + sql + result + latency_ms
       ▼
┌──────────────────────────────────────────────────────┐
│                   Trust Engine                        │
│                                                      │
│  schema_grounding     self_consistency               │
│  reverse_translation  semantic_cross_check           │
│  result_plausibility                                 │
│                                                      │
│  → weighted aggregate → trust_score (0.0 – 1.0)     │
│  → flags list                                        │
│  → per-check score breakdown                         │
└──────┬───────────────────────────────────────────────┘
       │
       │  TrustEvent (id, timestamp, question, sql, result,
       │              trust_score, flags, check_scores,
       │              latency_ms, token_count, backend_name)
       ▼
┌──────────────┐
│  Event Store │  DuckDB (local)  ·  Postgres (hosted)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Dashboard   │  Streamlit · localhost:8501
└──────────────┘
```

---

## Components

### 1. Integration surface (`sql_guard/server.py`, `sql_guard/guard.py`)

Two ways to get events into the store:

| Mode | How |
|---|---|
| **Proxy** | `POST /proxy/{backend_name}` — sql-guard forwards to the backend, runs checks in background, returns the original response untouched |
| **Push API** | `POST /track` — caller sends question + sql + result directly; sql-guard runs checks asynchronously |
| **Python library** | `guard.ask(question)` — synchronous; returns a `TrustReport` with score, flags, SQL, and result |

### 2. Trust engine (`sql_guard/checks/`)

Five independent checks, each returning a score (0–1) and optional flags:

| Check | Implementation | What it catches |
|---|---|---|
| `schema_grounding` | Regex + schema map | Tables, columns, functions absent from the warehouse |
| `self_consistency` | Re-runs backend N times, compares SQL | Agent giving different SQL for the same question |
| `reverse_translation` | LLM judge: does this SQL answer the question? | SQL that solves a different problem than asked |
| `semantic_cross_check` | Compares against dbt MetricFlow / Cube metric definitions | Agent answers that contradict the sanctioned metric |
| `result_plausibility` | Statistical baseline (rolling 30d or static) | Numbers outside believable range for the metric |

Final trust score = weighted sum of enabled check scores. Disabled check weights redistribute to remaining checks so the maximum is always 1.0 (Decision 7).

LLM failures in any check → score = 0.5 + `llm_unavailable` flag. Pipeline never crashes (Decision 3).

### 3. Event store (`sql_guard/store/`)

**Interface:** `DuckDBStore` (default) with an abstract base for Postgres.

**Schema — `events` table:**

```sql
CREATE TABLE events (
    id           VARCHAR PRIMARY KEY,
    timestamp    TIMESTAMP NOT NULL,
    question     TEXT NOT NULL,
    sql          TEXT,
    result       JSON,
    trust_score  DOUBLE,
    flags        JSON,          -- ["sql_inconsistent", "unknown_table:revenue"]
    latency_ms   INTEGER,
    token_count  INTEGER,
    backend_name VARCHAR,
    check_scores JSON           -- {"schema_grounding": 0.9, "self_consistency": 0.6, ...}
)
```

`flags` and `check_scores` are stored as JSON VARCHAR — no schema migration needed when adding new checks (Decision 4).

Dashboard opens a second DuckDB connection in read-only mode so it never blocks Guard writes (Decision 6).

### 4. Dashboard (`sql_guard/dashboard/app.py`)

Single-file Streamlit application. All CSS is inlined (no external static files — Decision 9, 10).

**Data flow:**

```
DuckDBStore (read-only)
    │
    ├── get_summary_stats()      → KPI row (10 metrics)
    ├── get_summary_stats()      → health banner (pass_rate + avg_trust)
    ├── get_volume_trend()       → Query Volume chart
    ├── get_trust_trend()        → Trust Score Trend chart
    ├── get_latency_trend()      → Latency chart
    ├── get_flag_counts()        → Flag Frequency chart
    ├── get_trust_histogram()    → Trust Distribution chart
    ├── get_token_trend()        → Token Usage chart
    ├── get_top_offenders()      → Low Trust Questions table
    └── get_event(id)            → Event Detail drill-through
```

**Tabs:** Overview · Backends · About

**Design:** GitHub dark palette (`#0D1117` base, `#161B22` surface). Altair for charts with a shared dark theme applied via `_chart()`. Streamlit's native sidebar — no `position:fixed` override (the root cause of layout breakage in prior iterations, Decision 10).

### 5. Config (`sql_guard/config.py`, `.sql-guard.yml`)

Loaded from `.sql-guard.yml` or `sql_guard.yml` at startup. Environment variables expand with `${VAR}` syntax.

```yaml
llm:
  provider: ollama        # ollama | openai | anthropic
  model: qwen2.5-coder:7b

event_store: duckdb:///sql_guard.db

checks:
  schema_grounding: { enabled: true, weight: 1.0 }
  self_consistency:  { enabled: true, samples: 3 }
  reverse_translation: { enabled: true }
  result_plausibility: { enabled: true }

backends:
  - name: my-vanna
    url: https://my-vanna-server.com/ask
    method: POST
    question_field: question
    sql_field: sql
    result_field: result
```

### 6. CLI (`sql_guard/cli.py`)

Built with Typer. Entry point is `sql-guard` (defined in `pyproject.toml`).

| Command | Description |
|---|---|
| `sql-guard serve` | Start FastAPI server on port 8080 |
| `sql-guard dashboard` | Launch Streamlit dashboard on port 8501 |
| `sql-guard ask "..."` | One-shot question through configured backend |
| `sql-guard verify` | Run checks on existing SQL + question |
| `sql-guard report` | Generate HTML trust report for a time window |
| `sql-guard ci` | Exit non-zero if avg trust < threshold (for CI pipelines) |

---

## Key data types (`sql_guard/models.py`)

```python
@dataclass
class TrustEvent:
    id: str
    timestamp: datetime
    question: str
    sql: str | None
    result: str | None          # JSON-serialised
    trust_score: float | None
    flags: str | None           # JSON array
    latency_ms: int | None
    token_count: int | None
    backend_name: str | None
    check_scores: str | None    # JSON object

@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float                # 0.0 – 1.0
    flags: list[str]
    detail: str | None

@dataclass
class TrustReport:
    trust_score: float
    passed: bool
    checks: list[CheckResult]
    sql: str | None
    answer: Any
    flags: list[str]
    latency_ms: int
```

---

## Dependency map

```
sql_guard/
├── cli.py              → typer
├── guard.py            → checks/, store/, models.py
├── server.py           → fastapi, guard.py, store/
├── config.py           → pydantic, pyaml
├── models.py
├── llm.py              → ollama / openai / anthropic
├── templates.py        → BackendConfig presets
├── checks/
│   ├── schema.py
│   ├── consistency.py
│   ├── reverse.py
│   ├── semantic.py
│   └── plausibility.py
├── store/
│   ├── base.py
│   └── duckdb_store.py → duckdb
└── dashboard/
    └── app.py          → streamlit, altair, pandas
```

---

## Runtime environment

| Component | Default port | Command |
|---|---|---|
| FastAPI server | 8080 | `uv run sql-guard serve` |
| Streamlit dashboard | 8501 | `uv run streamlit run sql_guard/dashboard/app.py` |
| Ollama LLM | 11434 | `ollama serve` |

All three can run simultaneously on a single machine. The dashboard reads the same DuckDB file the server writes to.

---

## Extension points

- **New check** — add a file to `sql_guard/checks/`, register in `ChecksConfig` and the engine loop
- **New backend** — subclass `BackendConfig` or use the generic config with field mappings
- **New store** — implement the abstract store interface (`sql_guard/store/base.py`)
- **New semantic layer** — add an adapter in the semantic cross-check module
