# sql-guard: Architectural Decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | Regex for schema grounding (not sqlglot) | MVP: avoids dep; sqlglot is upgrade path for CTEs/subqueries |
| 2 | Synchronous execution | Simpler testing; ThreadPoolExecutor later for parallel checks |
| 3 | LLM failure → score=0.5 + flag | Never crashes pipeline; flag surfaces in dashboard |
| 4 | JSON VARCHAR for flags/check_scores in DuckDB | Portable; no schema migration when adding checks |
| 5 | CustomBackend callable returns tuple `(sql, result)` | No sql-guard imports required from user code |
| 6 | Dashboard uses read_only DuckDB connection | DuckDB allows 1 rw + N ro; prevents blocking Guard writes |
| 7 | Disabled check weights redistribute to remaining checks | Max trust score always 1.0 regardless of config |
| 8 | uv for package management | Fastest resolver, lockfile, venv in one tool |
| 9 | Dashboard CSS inlined in app.py, no external static files | Removed tokens.css + components.css; the design system abstraction added complexity without benefit in a single-file Streamlit app. All styling lives in one place and is easier to maintain. |
| 10 | Dashboard rebuilt from scratch (removed aurora/glass design) | Three iterations with the aurora/glass design produced broken layouts due to `position:fixed` sidebar overlapping main content. New design uses Streamlit's native sidebar, GitHub dark palette (#0D1117), and minimal overrides — reliable across Streamlit versions. |
| 11 | Health banner as first element of Overview tab | Users need agent status at a glance without reading numbers. A contextual banner (HEALTHY / DEGRADED / CRITICAL) derived from pass_rate + avg_trust gives instant situational awareness before any KPI is read. |
| 12 | `get_top_offenders` filters by threshold in SQL WHERE clause | The threshold parameter was accepted but unused — the "Low Trust" table showed events above threshold, contradicting its label. Moved the filter into the SQL WHERE clause so the data contract matches the UI claim. |
| 13 | Trust trend Y-axis pinned to [0, 1] domain | Auto-ranging (`zero=False, nice=True`) made small dips from 0.93 → 0.87 look catastrophic. Pinning to the semantically correct 0–1 range keeps dips proportional to their actual severity. |
| 14 | Per-check scores chart rendered at full page width in drill-through | Was inside a 1/4-width column — chart bars were unreadable. Moved to full width below the question/SQL columns. |
