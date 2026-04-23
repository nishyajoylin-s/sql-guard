from __future__ import annotations

import time
from typing import Any, Callable

from sql_guard.backends.base import BaseBackend
from sql_guard.models import BackendResult

BackendFn = Callable[[str], tuple[str, Any]]


class CustomBackend(BaseBackend):
    """Wraps any callable that accepts a question and returns (sql, result)."""

    def __init__(
        self,
        fn: BackendFn,
        name: str = "custom",
        schema_map: dict[str, list[str]] | None = None,
    ) -> None:
        self._fn = fn
        self.name = name
        self._schema = schema_map

    def run(self, question: str) -> BackendResult:
        start = time.monotonic()
        sql, result = self._fn(question)
        latency_ms = int((time.monotonic() - start) * 1000)
        return BackendResult(sql=sql, result=result, latency_ms=latency_ms)

    def schema(self) -> dict[str, list[str]] | None:
        return self._schema
