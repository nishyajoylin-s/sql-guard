"""
sql-guard server — two ingestion modes:

  POST /track
    Push API. Send {question, sql, result, backend_name} from your existing code.
    Returns immediately; checks run in the background.

  POST /proxy/{backend_name}
    Transparent proxy. Point your app at this URL instead of your text-to-SQL tool.
    sql-guard forwards the request, captures question/sql/result, returns the
    original response unchanged. Checks run in the background.

  GET/POST/DELETE /api/backends
    Manage backend configs (CRUD). Also writable via .sql-guard.yml.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sql_guard.config import BackendConfig, Config, load_config, save_config
from sql_guard.server.processor import run_checks_and_store
from sql_guard.store.duckdb_store import DuckDBStore

# ── State shared across requests ──────────────────────────────────────────────

_config: Config = Config()
_config_path: Path | None = None


def get_config() -> Config:
    return _config


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config
    _config = load_config(_config_path)
    # Ensure DB + table exist on startup
    DuckDBStore(_config.event_store).close()
    yield


app = FastAPI(
    title="sql-guard",
    description="Trust and observability layer for text-to-SQL agents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Push API (/track) ─────────────────────────────────────────────────────────

class TrackRequest(BaseModel):
    question: str
    sql: str
    result: Any = None
    backend_name: str = "unknown"
    latency_ms: int | None = None
    token_count: int | None = None


class TrackResponse(BaseModel):
    status: str = "accepted"
    message: str = "Checks running in background. View results in the dashboard."


@app.post("/track", response_model=TrackResponse, tags=["ingestion"])
async def track(req: TrackRequest, background_tasks: BackgroundTasks):
    """
    Push API — call this after your text-to-SQL tool answers a question.
    sql-guard runs trust checks in the background and stores the result.

    ```python
    import httpx
    httpx.post("http://localhost:8080/track", json={
        "question": "How many orders last month?",
        "sql": "SELECT COUNT(*) FROM orders WHERE ...",
        "result": [{"count": 42}],
        "backend_name": "my-tool",
    })
    ```
    """
    cfg = get_config()
    backend_cfg = next((b for b in cfg.backends if b.name == req.backend_name), None)

    background_tasks.add_task(
        run_checks_and_store,
        question=req.question,
        sql=req.sql,
        result=req.result,
        backend_name=req.backend_name,
        latency_ms=req.latency_ms or 0,
        token_count=req.token_count,
        config=cfg,
        backend_config=backend_cfg,
    )
    return TrackResponse()


# ── Proxy (/proxy/{backend_name}) ─────────────────────────────────────────────

@app.post("/proxy/{backend_name}", tags=["ingestion"])
async def proxy(backend_name: str, body: dict, background_tasks: BackgroundTasks):
    """
    Transparent proxy — point your app at this URL instead of your text-to-SQL tool.
    sql-guard forwards the request, returns the unchanged response, and tracks in background.

    Change your app from:
      POST https://my-vanna-server/ask

    To:
      POST http://sql-guard-host:8080/proxy/my-vanna

    Configure the backend URL in .sql-guard.yml or via POST /api/backends.
    """
    cfg = get_config()
    backend_cfg = next((b for b in cfg.backends if b.name == backend_name), None)
    if not backend_cfg:
        raise HTTPException(
            status_code=404,
            detail=f"Backend '{backend_name}' not found. "
                   f"Add it via POST /api/backends or in .sql-guard.yml.",
        )

    # Extract question from request body using configured field name
    question = body.get(backend_cfg.question_field, "")

    # Forward to the configured backend URL
    headers = {"Content-Type": "application/json"}
    if backend_cfg.auth_header:
        headers["Authorization"] = backend_cfg.auth_header

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            if backend_cfg.method.upper() == "GET":
                resp = await client.get(backend_cfg.url, params=body, headers=headers)
            else:
                resp = await client.post(backend_cfg.url, json=body, headers=headers)
    except httpx.ConnectError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach backend '{backend_name}': {e}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Backend '{backend_name}' timed out.")

    latency_ms = int((time.monotonic() - start) * 1000)

    # Extract sql + result from the response using configured field names
    try:
        resp_body = resp.json()
    except Exception:
        resp_body = {"raw": resp.text}

    sql = resp_body.get(backend_cfg.sql_field, "")
    result = resp_body.get(backend_cfg.result_field)

    background_tasks.add_task(
        run_checks_and_store,
        question=question,
        sql=sql,
        result=result,
        backend_name=backend_name,
        latency_ms=latency_ms,
        token_count=None,
        config=cfg,
        backend_config=backend_cfg,
    )

    # Return the original backend response unchanged
    return resp_body


# ── Backends CRUD (/api/backends) ─────────────────────────────────────────────

@app.get("/api/backends", tags=["config"])
async def list_backends():
    """List all configured backends."""
    return get_config().backends


@app.post("/api/backends", tags=["config"])
async def add_backend(backend: BackendConfig):
    """Add or update a backend. Persists to .sql-guard.yml."""
    cfg = get_config()
    existing = [b for b in cfg.backends if b.name != backend.name]
    cfg.backends = existing + [backend]
    save_config(cfg, _config_path)
    return {"status": "saved", "backend": backend}


@app.delete("/api/backends/{name}", tags=["config"])
async def delete_backend(name: str):
    """Remove a backend by name."""
    cfg = get_config()
    before = len(cfg.backends)
    cfg.backends = [b for b in cfg.backends if b.name != name]
    if len(cfg.backends) == before:
        raise HTTPException(status_code=404, detail=f"Backend '{name}' not found.")
    save_config(cfg, _config_path)
    return {"status": "deleted", "name": name}


@app.post("/api/backends/{name}/test", tags=["config"])
async def test_backend(name: str, body: dict | None = None):
    """
    Send a test request to the backend and return the raw response.
    Use this to verify your field mapping is correct before going live.
    """
    cfg = get_config()
    backend_cfg = next((b for b in cfg.backends if b.name == name), None)
    if not backend_cfg:
        raise HTTPException(status_code=404, detail=f"Backend '{name}' not found.")

    test_body = body or {backend_cfg.question_field: "What is the total revenue?"}
    headers = {"Content-Type": "application/json"}
    if backend_cfg.auth_header:
        headers["Authorization"] = backend_cfg.auth_header

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(backend_cfg.url, json=test_body, headers=headers)
        latency_ms = int((time.monotonic() - start) * 1000)
        try:
            resp_body = resp.json()
        except Exception:
            resp_body = {"raw": resp.text}
        return {
            "status": "ok",
            "latency_ms": latency_ms,
            "http_status": resp.status_code,
            "response": resp_body,
            "detected": {
                "sql": resp_body.get(backend_cfg.sql_field, "(not found — check sql_field)"),
                "result": resp_body.get(backend_cfg.result_field, "(not found — check result_field)"),
            },
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health():
    cfg = get_config()
    return {
        "status": "ok",
        "backends": len(cfg.backends),
        "event_store": cfg.event_store,
    }
