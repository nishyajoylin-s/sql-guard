from __future__ import annotations

from datetime import datetime, timezone

from sql_guard.backends.base import BaseBackend
from sql_guard.checks.base import BaseCheck
from sql_guard.checks.reverse_translation import ReverseTranslationCheck
from sql_guard.checks.schema_grounding import SchemaGroundingCheck
from sql_guard.checks.self_consistency import SelfConsistencyCheck
from sql_guard.config import Config, load_config
from sql_guard.models import BackendResult, TrustEvent, TrustReport
from sql_guard.store.duckdb_store import DuckDBStore


class Guard:
    def __init__(
        self,
        backend: BaseBackend,
        event_store: str = "duckdb:///sql_guard.db",
        config: Config | None = None,
        checks: list[BaseCheck] | None = None,
    ) -> None:
        self._backend = backend
        self._config = config or load_config()
        self._store = DuckDBStore(event_store)
        self._checks = checks if checks is not None else self._build_default_checks()

    def ask(self, question: str) -> TrustReport:
        result = self._backend.run(question)
        check_results = [
            c.run(question, result, self._backend, self._config.checks)
            for c in self._checks
        ]
        trust_score = self._compute_trust_score(check_results)
        flags = sorted({f for cr in check_results for f in cr.flags})

        report = TrustReport(
            question=question,
            sql=result.sql,
            answer=result.result,
            trust_score=trust_score,
            flags=flags,
            check_results=check_results,
            latency_ms=result.latency_ms,
            token_count=result.token_count,
            backend_name=self._backend.name,
            timestamp=datetime.now(timezone.utc),
        )
        self._store.write_event(TrustEvent.from_report(report))
        return report

    def verify(self, question: str, sql: str) -> TrustReport:
        """Run checks against a provided SQL without calling the backend."""
        synthetic = BackendResult(sql=sql, result=None, latency_ms=0)
        check_results = [
            c.run(question, synthetic, self._backend, self._config.checks)
            for c in self._checks
        ]
        trust_score = self._compute_trust_score(check_results)
        flags = sorted({f for cr in check_results for f in cr.flags})

        report = TrustReport(
            question=question,
            sql=sql,
            answer=None,
            trust_score=trust_score,
            flags=flags,
            check_results=check_results,
            latency_ms=0,
            token_count=None,
            backend_name=self._backend.name,
            timestamp=datetime.now(timezone.utc),
        )
        self._store.write_event(TrustEvent.from_report(report))
        return report

    def _compute_trust_score(self, check_results: list) -> float:
        weights = self._config.checks.weights
        # Only include checks that actually ran; normalize remaining weights
        active = {cr.check_name: cr.score for cr in check_results}
        active_weights = {k: v for k, v in weights.items() if k in active}
        total_weight = sum(active_weights.values())
        if total_weight == 0:
            return sum(active.values()) / len(active) if active else 0.0
        score = sum(active[k] * w for k, w in active_weights.items()) / total_weight
        return round(score, 4)

    def _build_default_checks(self) -> list[BaseCheck]:
        cfg = self._config.checks
        checks: list[BaseCheck] = []
        if cfg.schema_grounding:
            checks.append(SchemaGroundingCheck())
        if cfg.self_consistency:
            checks.append(SelfConsistencyCheck())
        if cfg.reverse_translation:
            checks.append(ReverseTranslationCheck(self._config.ollama))
        return checks
