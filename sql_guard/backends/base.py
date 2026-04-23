from __future__ import annotations

from abc import ABC, abstractmethod

from sql_guard.models import BackendResult


class BaseBackend(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, question: str) -> BackendResult:
        """Execute question through the text-to-SQL agent."""

    def schema(self) -> dict[str, list[str]] | None:
        """Return warehouse schema as {table: [col1, col2, ...]} or None."""
        return None
