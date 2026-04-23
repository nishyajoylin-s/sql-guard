import json
from datetime import datetime, timezone


from sql_guard.models import TrustEvent, TrustReport, CheckResult
from sql_guard.store.duckdb_store import DuckDBStore


def _make_event(**kwargs):
    defaults = dict(
        timestamp=datetime.now(timezone.utc),
        question="How many orders?",
        sql="SELECT COUNT(*) FROM orders",
        result=json.dumps([{"count": 42}]),
        trust_score=0.9,
        flags=json.dumps([]),
        latency_ms=123,
        token_count=None,
        backend_name="test",
        check_scores=json.dumps({"schema_grounding": 1.0}),
    )
    defaults.update(kwargs)
    return TrustEvent(**defaults)


def test_write_and_read(in_memory_store):
    event = _make_event()
    in_memory_store.write_event(event)
    events = in_memory_store.query_events()
    assert len(events) == 1
    assert events[0]["question"] == "How many orders?"
    assert abs(events[0]["trust_score"] - 0.9) < 1e-6


def test_idempotent_write(in_memory_store):
    event = _make_event()
    in_memory_store.write_event(event)
    in_memory_store.write_event(event)  # same id, should replace
    assert len(in_memory_store.query_events()) == 1


def test_parse_since_valid(in_memory_store):
    assert in_memory_store._parse_since("7d") == "'7 DAY'"
    assert in_memory_store._parse_since("24h") == "'24 HOUR'"
    assert in_memory_store._parse_since("30m") == "'30 MINUTE'"


def test_parse_since_invalid(in_memory_store):
    import pytest
    with pytest.raises(ValueError):
        in_memory_store._parse_since("bad")


def test_get_top_offenders(in_memory_store):
    for i, score in enumerate([0.3, 0.9, 0.5]):
        in_memory_store.write_event(_make_event(trust_score=score))
    offenders = in_memory_store.get_top_offenders(n=2, since="1h")
    assert offenders[0]["trust_score"] <= offenders[1]["trust_score"]
