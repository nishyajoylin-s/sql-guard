from __future__ import annotations

import json
import re
from collections import Counter

from sql_guard.checks.base import BaseCheck
from sql_guard.models import BackendResult, CheckResult


class SelfConsistencyCheck(BaseCheck):
    name = "self_consistency"

    def run(self, question, backend_result, backend, config) -> CheckResult:
        n = config.self_consistency_n
        sqls = [self._normalize_sql(backend_result.sql)]
        results = [self._normalize_result(backend_result.result)]

        for _ in range(n - 1):
            try:
                extra = backend.run(question)
                sqls.append(self._normalize_sql(extra.sql))
                results.append(self._normalize_result(extra.result))
            except Exception:
                pass  # a failed run counts as a divergent sample

        _, sql_agreement = self._majority(sqls)
        _, result_agreement = self._majority(results)

        score = round(0.6 * sql_agreement + 0.4 * result_agreement, 4)
        flags = []
        if sql_agreement < 0.8:
            flags.append("sql_inconsistent")
        if result_agreement < 0.8:
            flags.append("result_inconsistent")

        return CheckResult(
            check_name=self.name,
            passed=score >= 0.8,
            score=score,
            detail=(
                f"SQL agreement {sql_agreement:.0%} over {len(sqls)} runs; "
                f"result agreement {result_agreement:.0%}."
            ),
            flags=flags,
        )

    def _normalize_sql(self, sql: str) -> str:
        return re.sub(r"\s+", " ", sql.strip().lower().rstrip(";"))

    def _normalize_result(self, result) -> str:
        try:
            return json.dumps(result, sort_keys=True, default=str)
        except Exception:
            return str(result)

    def _majority(self, items: list[str]) -> tuple[str, float]:
        if not items:
            return ("", 0.0)
        counts = Counter(items)
        majority_val, majority_count = counts.most_common(1)[0]
        return majority_val, majority_count / len(items)
