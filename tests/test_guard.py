from unittest.mock import patch

from sql_guard.checks.reverse_translation import ReverseTranslationCheck
from sql_guard.checks.schema_grounding import SchemaGroundingCheck
from sql_guard.checks.self_consistency import SelfConsistencyCheck
from sql_guard.config import Config, OllamaConfig
from sql_guard.guard import Guard


def _mock_ollama_response(score=0.9):
    return {
        "message": {
            "content": f'{{"score": {score}, "reasoning": "Looks good.", "flags": []}}'
        }
    }


def test_guard_ask_integration(simple_backend, in_memory_store):
    config = Config()
    checks = [
        SchemaGroundingCheck(),
        SelfConsistencyCheck(),
        ReverseTranslationCheck(OllamaConfig()),
    ]
    guard = Guard(
        backend=simple_backend,
        event_store="duckdb:///:memory:",
        config=config,
        checks=checks,
    )
    # Swap the store for our in-memory fixture
    guard._store = in_memory_store

    with patch("ollama.chat", return_value=_mock_ollama_response(0.9)):
        report = guard.ask("Total revenue?")

    assert 0.0 <= report.trust_score <= 1.0
    assert isinstance(report.flags, list)
    assert report.sql is not None
    assert report.backend_name == "test"

    # Event should be persisted
    events = in_memory_store.query_events()
    assert len(events) == 1
    assert abs(events[0]["trust_score"] - report.trust_score) < 1e-6


def test_guard_verify(simple_backend, in_memory_store):
    config = Config()
    checks = [SchemaGroundingCheck()]
    guard = Guard(
        backend=simple_backend,
        event_store="duckdb:///:memory:",
        config=config,
        checks=checks,
    )
    guard._store = in_memory_store

    report = guard.verify("Count orders", "SELECT COUNT(*) FROM orders")
    assert 0.0 <= report.trust_score <= 1.0
    assert report.answer is None  # verify doesn't call backend
