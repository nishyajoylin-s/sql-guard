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
