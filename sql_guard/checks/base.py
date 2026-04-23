from __future__ import annotations

from abc import ABC, abstractmethod

from sql_guard.models import BackendResult, CheckResult


class BaseCheck(ABC):
    name: str

    @abstractmethod
    def run(
        self,
        question: str,
        backend_result: BackendResult,
        backend: "BaseBackend",  # noqa: F821
        config: "ChecksConfig",  # noqa: F821
    ) -> CheckResult:
        """Run the check and return a CheckResult."""
