"""
Background task: runs trust checks on a captured event and persists the result.
Called after the server has already returned a response to the caller.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sql_guard.backends.custom import CustomBackend
from sql_guard.checks.reverse_translation import ReverseTranslationCheck
from sql_guard.checks.schema_grounding import SchemaGroundingCheck
from sql_guard.checks.self_consistency import SelfConsistencyCheck
from sql_guard.config import BackendConfig, Config
from sql_guard.models import BackendResult, TrustEvent, TrustReport
from sql_guard.store.duckdb_store import DuckDBStore


def _build_checks(config: Config):
    cfg = config.checks
    checks = []
    if cfg.schema_grounding:
        checks.append(SchemaGroundingCheck())
    if cfg.self_consistency:
        checks.append(SelfConsistencyCheck())
    if cfg.reverse_translation:
        checks.append(ReverseTranslationCheck(config.ollama))
    return checks


def _compute_trust_score(check_results, weights: dict) -> float:
    active = {cr.check_name: cr.score for cr in check_results}
    active_weights = {k: v for k, v in weights.items() if k in active}
    total = sum(active_weights.values())
    if not total:
        return sum(active.values()) / len(active) if active else 0.0
    return round(sum(active[k] * w for k, w in active_weights.items()) / total, 4)


def run_checks_and_store(
    question: str,
    sql: str,
    result,
    backend_name: str,
    latency_ms: int,
    token_count: int | None,
    config: Config,
    backend_config: BackendConfig | None,
) -> None:
    """Synchronous — call this inside a FastAPI BackgroundTask thread."""
    store = DuckDBStore(config.event_store)

    # Build a stub backend so checks have something to call for self-consistency.
    # For proxy/push mode, self-consistency re-calls the real endpoint.
    # If no backend_config, self-consistency is effectively skipped (always returns same result).
    _captured_sql = sql
    _captured_result = result

    def _stub(q: str):
        return (_captured_sql, _captured_result)

    stub_backend = CustomBackend(
        fn=_stub,
        name=backend_name,
        schema_map=backend_config.schema_map if backend_config else None,
    )

    backend_result = BackendResult(sql=sql, result=result, latency_ms=latency_ms)
    checks = _build_checks(config)
    check_results = [
        c.run(question, backend_result, stub_backend, config.checks)
        for c in checks
    ]
    trust_score = _compute_trust_score(check_results, config.checks.weights)
    flags = sorted({f for cr in check_results for f in cr.flags})

    report = TrustReport(
        question=question,
        sql=sql,
        answer=result,
        trust_score=trust_score,
        flags=flags,
        check_results=check_results,
        latency_ms=latency_ms,
        token_count=token_count,
        backend_name=backend_name,
        timestamp=datetime.now(timezone.utc),
    )
    store.write_event(TrustEvent.from_report(report))
