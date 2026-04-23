from __future__ import annotations

import re

from sql_guard.checks.base import BaseCheck
from sql_guard.models import BackendResult, CheckResult


class SchemaGroundingCheck(BaseCheck):
    name = "schema_grounding"

    def run(self, question, backend_result, backend, config) -> CheckResult:
        schema = backend.schema()
        if schema is None:
            return CheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                detail="Schema not provided; grounding skipped.",
                flags=["schema_unavailable"],
            )

        known_tables = {t.lower() for t in schema}
        known_cols: set[str] = set()
        for cols in schema.values():
            known_cols.update(c.lower() for c in cols)

        sql = backend_result.sql
        extracted_tables = self._extract_tables(sql)
        extracted_cols = self._extract_columns(sql)

        unknown_tables = extracted_tables - known_tables
        unknown_cols = extracted_cols - known_cols - {"*"}

        total = len(extracted_tables) + len(extracted_cols)
        if total == 0:
            return CheckResult(
                check_name=self.name, passed=True, score=1.0,
                detail="No tables or columns extracted from SQL.",
            )

        unknown = len(unknown_tables) + len(unknown_cols)
        score = max(0.0, 1.0 - (unknown / total))
        flags = [f"unknown_table:{t}" for t in sorted(unknown_tables)]
        flags += [f"unknown_column:{c}" for c in sorted(unknown_cols)]

        return CheckResult(
            check_name=self.name,
            passed=score >= 0.8,
            score=round(score, 4),
            detail=f"{unknown} unknown reference(s) out of {total}.",
            flags=flags,
        )

    def _extract_tables(self, sql: str) -> set[str]:
        # Match FROM/JOIN followed by identifier (skip subqueries starting with '(')
        pattern = r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_.]*)"
        return {self._normalize(m) for m in re.findall(pattern, sql, re.IGNORECASE)}

    def _extract_columns(self, sql: str) -> set[str]:
        # Extract identifiers from SELECT clause (before FROM)
        select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.IGNORECASE | re.DOTALL)
        cols: set[str] = set()
        if select_match:
            select_part = select_match.group(1)
            # Split by comma, strip aliases (AS ...), functions, literals
            for token in select_part.split(","):
                token = token.strip()
                # Remove alias
                token = re.sub(r"\s+AS\s+\w+$", "", token, flags=re.IGNORECASE).strip()
                # Skip aggregates/functions — extract bare column references
                # e.g. SUM(revenue) -> revenue
                inner = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)", token)
                if inner:
                    for _, args in inner:
                        for arg in args.split(","):
                            arg = arg.strip()
                            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", arg):
                                # strip table prefix
                                cols.add(self._normalize(arg.split(".")[-1]))
                else:
                    # bare column or table.column
                    bare = re.match(r"^([a-zA-Z_][a-zA-Z0-9_.]*)$", token)
                    if bare:
                        cols.add(self._normalize(bare.group(1).split(".")[-1]))
        return cols

    def _normalize(self, name: str) -> str:
        return name.strip('"\'`').lower()
