from __future__ import annotations

import re
from datetime import datetime, timezone

import duckdb

from sql_guard.models import TrustEvent

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id           VARCHAR PRIMARY KEY,
    timestamp    TIMESTAMP NOT NULL,
    question     TEXT NOT NULL,
    sql          TEXT,
    result       JSON,
    trust_score  DOUBLE,
    flags        JSON,
    latency_ms   INTEGER,
    token_count  INTEGER,
    backend_name VARCHAR,
    check_scores JSON
)
"""


class DuckDBStore:
    def __init__(self, uri: str, read_only: bool = False) -> None:
        path = self._parse_uri(uri)
        self._conn = duckdb.connect(path, read_only=read_only)
        if not read_only:
            self._conn.execute(_CREATE_EVENTS)

    def _parse_uri(self, uri: str) -> str:
        if uri.startswith("duckdb:///"):
            return uri[len("duckdb:///"):]
        if uri.startswith("duckdb://"):
            return uri[len("duckdb://"):]
        return uri

    def _where(self, since: str, backend: str | None = None) -> tuple[str, list]:
        """Build a WHERE clause with optional backend filter. Returns (clause, params)."""
        interval = self._parse_since(since)
        clauses = [f"timestamp >= NOW() - INTERVAL {interval}"]
        params: list = []
        if backend and backend != "All":
            clauses.append("backend_name = ?")
            params.append(backend)
        return "WHERE " + " AND ".join(clauses), params

    def write_event(self, event: TrustEvent) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                event.id, event.timestamp, event.question, event.sql, event.result,
                event.trust_score, event.flags, event.latency_ms, event.token_count,
                event.backend_name, event.check_scores,
            ],
        )

    def query_events(
        self,
        since: str | None = None,
        limit: int = 100,
        backend_name: str | None = None,
    ) -> list[dict]:
        where, params = self._where(since, backend_name) if since else ("", [])
        rows = self._conn.execute(
            f"SELECT * FROM events {where} ORDER BY timestamp DESC LIMIT {limit}",
            params,
        ).fetchall()
        cols = [d[0] for d in self._conn.description]
        return [dict(zip(cols, row)) for row in rows]

    def get_backends(self) -> list[str]:
        """Distinct backend names across all events."""
        rows = self._conn.execute(
            "SELECT DISTINCT backend_name FROM events WHERE backend_name IS NOT NULL ORDER BY 1"
        ).fetchall()
        return [r[0] for r in rows]

    def get_summary_stats(
        self, since: str = "24h", threshold: float = 0.7, backend: str | None = None
    ) -> dict:
        where, params = self._where(since, backend)
        row = self._conn.execute(
            f"""
            SELECT
                COUNT(*)                                                          AS total,
                AVG(trust_score)                                                  AS avg_trust,
                SUM(CASE WHEN trust_score >= {threshold} THEN 1 ELSE 0 END)      AS passed,
                SUM(CASE WHEN trust_score <  {threshold} THEN 1 ELSE 0 END)      AS failed,
                AVG(latency_ms)                                                   AS avg_latency,
                SUM(COALESCE(token_count, 0))                                     AS total_tokens,
                MIN(timestamp)                                                    AS first_seen,
                MAX(timestamp)                                                    AS last_seen
            FROM events {where}
            """,
            params,
        ).fetchone()
        total = row[0] or 0
        return {
            "total": total,
            "avg_trust": row[1],
            "passed": int(row[2] or 0),
            "failed": int(row[3] or 0),
            "pass_rate": (row[2] or 0) / total if total else None,
            "fail_rate": (row[3] or 0) / total if total else None,
            "avg_latency": row[4],
            "total_tokens": int(row[5] or 0),
            "first_seen": row[6],
            "last_seen": row[7],
        }

    def get_trust_trend(
        self, since: str = "30d", backend: str | None = None
    ) -> list[dict]:
        where, params = self._where(since, backend)
        bucket = self._bucket_interval(since)
        rows = self._conn.execute(
            f"""
            SELECT
                time_bucket(INTERVAL '{bucket}', timestamp) AS bucket,
                AVG(trust_score) AS avg_trust,
                COUNT(*) AS n
            FROM events {where}
            GROUP BY bucket ORDER BY bucket
            """,
            params,
        ).fetchall()
        return [{"bucket": r[0], "avg_trust": r[1], "n": r[2]} for r in rows]

    def get_volume_trend(
        self, since: str = "24h", threshold: float = 0.7, backend: str | None = None
    ) -> list[dict]:
        where, params = self._where(since, backend)
        bucket = self._bucket_interval(since)
        rows = self._conn.execute(
            f"""
            SELECT
                time_bucket(INTERVAL '{bucket}', timestamp) AS bucket,
                COUNT(*) AS questions,
                SUM(CASE WHEN trust_score >= {threshold} THEN 1 ELSE 0 END) AS passed,
                SUM(CASE WHEN trust_score <  {threshold} THEN 1 ELSE 0 END) AS failed
            FROM events {where}
            GROUP BY bucket ORDER BY bucket
            """,
            params,
        ).fetchall()
        return [{"bucket": r[0], "questions": r[1], "passed": r[2], "failed": r[3]} for r in rows]

    def get_latency_trend(
        self, since: str = "24h", backend: str | None = None
    ) -> list[dict]:
        where, params = self._where(since, backend)
        bucket = self._bucket_interval(since)
        rows = self._conn.execute(
            f"""
            SELECT
                time_bucket(INTERVAL '{bucket}', timestamp) AS bucket,
                PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY latency_ms) AS p50,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
            FROM events {where}
            GROUP BY bucket ORDER BY bucket
            """,
            params,
        ).fetchall()
        return [{"bucket": r[0], "p50": r[1], "p95": r[2]} for r in rows]

    def get_token_trend(
        self, since: str = "24h", backend: str | None = None
    ) -> list[dict]:
        where, params = self._where(since, backend)
        bucket = self._bucket_interval(since)
        rows = self._conn.execute(
            f"""
            SELECT
                time_bucket(INTERVAL '{bucket}', timestamp) AS bucket,
                SUM(COALESCE(token_count, 0)) AS tokens
            FROM events {where}
            GROUP BY bucket ORDER BY bucket
            """,
            params,
        ).fetchall()
        return [{"bucket": r[0], "tokens": r[1]} for r in rows]

    def get_flag_counts(
        self, since: str = "24h", backend: str | None = None
    ) -> list[dict]:
        where, params = self._where(since, backend)
        rows = self._conn.execute(
            f"""
            SELECT flag, COUNT(*) AS n
            FROM (
                SELECT UNNEST(json_extract_string(flags, '$[*]')) AS flag
                FROM events {where}
                  AND flags IS NOT NULL AND flags != '[]'
            )
            GROUP BY flag ORDER BY n DESC
            """,
            params,
        ).fetchall()
        return [{"flag": r[0], "count": r[1]} for r in rows]

    def get_trust_histogram(
        self, since: str = "24h", backend: str | None = None
    ) -> list[dict]:
        where, params = self._where(since, backend)
        rows = self._conn.execute(
            f"""
            SELECT
                CASE
                    WHEN trust_score < 0.2 THEN '0.0–0.2'
                    WHEN trust_score < 0.4 THEN '0.2–0.4'
                    WHEN trust_score < 0.6 THEN '0.4–0.6'
                    WHEN trust_score < 0.8 THEN '0.6–0.8'
                    ELSE                        '0.8–1.0'
                END AS bucket,
                COUNT(*) AS n
            FROM events {where}
            GROUP BY bucket ORDER BY bucket
            """,
            params,
        ).fetchall()
        return [{"bucket": r[0], "n": r[1]} for r in rows]

    def get_latency_percentiles(
        self, since: str = "7d", backend: str | None = None
    ) -> dict:
        where, params = self._where(since, backend)
        row = self._conn.execute(
            f"""
            SELECT
                PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY latency_ms) AS p50,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95,
                COUNT(*) AS n,
                AVG(token_count) AS avg_tokens
            FROM events {where}
            """,
            params,
        ).fetchone()
        return {"p50": row[0], "p95": row[1], "n": row[2], "avg_tokens": row[3]}

    def get_top_offenders(
        self, n: int = 10, since: str = "7d",
        threshold: float = 0.7, backend: str | None = None
    ) -> list[dict]:
        where, params = self._where(since, backend)
        rows = self._conn.execute(
            f"""
            SELECT id, timestamp, question, trust_score, flags, backend_name
            FROM events {where}
            ORDER BY trust_score ASC
            LIMIT {n}
            """,
            params,
        ).fetchall()
        return [
            {"id": r[0], "timestamp": r[1], "question": r[2],
             "trust_score": r[3], "flags": r[4], "backend_name": r[5]}
            for r in rows
        ]

    def get_activity_stats(
        self, since: str = "24h", backend: str | None = None
    ) -> dict:
        where, params = self._where(since, backend)
        bucket = self._bucket_interval(since)
        active = self._conn.execute(
            f"""
            SELECT COUNT(*) FROM (
                SELECT time_bucket(INTERVAL '{bucket}', timestamp) AS b
                FROM events {where}
                GROUP BY b
            )
            """,
            params,
        ).fetchone()[0] or 0

        per_unit = {"1h": 12, "24h": 24, "7d": 28, "30d": 30}
        total_buckets = per_unit.get(since, 24)
        uptime_pct = min(1.0, active / total_buckets) if total_buckets else 0

        avg_q = self._conn.execute(
            f"""
            SELECT AVG(cnt) FROM (
                SELECT COUNT(*) AS cnt FROM events {where}
                GROUP BY time_bucket(INTERVAL '{bucket}', timestamp)
            )
            """,
            params,
        ).fetchone()[0] or 0

        busy = self._conn.execute(
            f"""
            SELECT COUNT(*) FROM (
                SELECT COUNT(*) AS cnt FROM events {where}
                GROUP BY time_bucket(INTERVAL '{bucket}', timestamp)
                HAVING cnt > {max(1, avg_q)}
            )
            """,
            params,
        ).fetchone()[0] or 0

        return {
            "uptime_pct": uptime_pct,
            "active_buckets": active,
            "total_buckets": total_buckets,
            "busy_buckets": int(busy),
            "idle_buckets": max(0, total_buckets - active),
        }

    def get_event(self, event_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM events WHERE id = ?", [event_id]
        ).fetchone()
        if not row:
            return None
        cols = [d[0] for d in self._conn.description]
        return dict(zip(cols, row))

    def _bucket_interval(self, since: str) -> str:
        return {"1h": "5 minutes", "24h": "1 hour", "7d": "6 hours", "30d": "1 day"}.get(since, "1 hour")

    def _parse_since(self, since: str) -> str:
        m = re.fullmatch(r"(\d+)([dhm])", since)
        if not m:
            raise ValueError(f"Invalid since format: {since!r}. Use e.g. '7d', '24h', '30m'.")
        n, unit = m.group(1), m.group(2)
        unit_map = {"d": "DAY", "h": "HOUR", "m": "MINUTE"}
        return f"'{n} {unit_map[unit]}'"

    def close(self) -> None:
        self._conn.close()
