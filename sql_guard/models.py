from __future__ import annotations

import json
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any

from pydantic import BaseModel, Field


class BackendResult(BaseModel):
    sql: str
    result: list[dict] | dict | str | float | None
    latency_ms: int
    token_count: int | None = None
    raw: dict = Field(default_factory=dict)


class CheckResult(BaseModel):
    check_name: str
    passed: bool
    score: float
    detail: str = ""
    flags: list[str] = Field(default_factory=list)


class TrustReport(BaseModel):
    question: str
    sql: str | None
    answer: list[dict] | dict | str | float | None
    trust_score: float
    flags: list[str]
    check_results: list[CheckResult]
    latency_ms: int
    token_count: int | None = None
    backend_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrustEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime
    question: str
    sql: str | None
    result: str | None  # JSON serialized
    trust_score: float
    flags: str  # JSON serialized list
    latency_ms: int
    token_count: int | None
    backend_name: str
    check_scores: str  # JSON serialized dict

    @classmethod
    def from_report(cls, report: TrustReport) -> "TrustEvent":
        return cls(
            timestamp=report.timestamp,
            question=report.question,
            sql=report.sql,
            result=json.dumps(report.answer, default=str) if report.answer is not None else None,
            trust_score=report.trust_score,
            flags=json.dumps(report.flags),
            latency_ms=report.latency_ms,
            token_count=report.token_count,
            backend_name=report.backend_name,
            check_scores=json.dumps({r.check_name: r.score for r in report.check_results}),
        )
