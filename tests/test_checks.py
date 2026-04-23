from unittest.mock import patch

import pytest

from sql_guard.backends.custom import CustomBackend
from sql_guard.checks.reverse_translation import ReverseTranslationCheck
from sql_guard.checks.schema_grounding import SchemaGroundingCheck
from sql_guard.checks.self_consistency import SelfConsistencyCheck
from sql_guard.config import ChecksConfig, Config, OllamaConfig
from sql_guard.models import BackendResult


# ── Schema grounding ──────────────────────────────────────────────────────────

def _grounding_check():
    return SchemaGroundingCheck()


def _backend_with_schema(schema):
    return CustomBackend(fn=lambda q: ("", None), schema_map=schema)


def test_schema_grounding_all_valid(default_config):
    schema = {"orders": ["id", "revenue", "created_at"]}
    backend = _backend_with_schema(schema)
    result = BackendResult(sql="SELECT SUM(revenue) FROM orders", result=None, latency_ms=0)
    cr = _grounding_check().run("q", result, backend, default_config.checks)
    assert cr.score == 1.0
    assert cr.passed


def test_schema_grounding_unknown_table(default_config):
    schema = {"orders": ["id", "revenue"]}
    backend = _backend_with_schema(schema)
    result = BackendResult(sql="SELECT * FROM nonexistent_table", result=None, latency_ms=0)
    cr = _grounding_check().run("q", result, backend, default_config.checks)
    assert cr.score < 1.0
    assert any("unknown_table:nonexistent_table" in f for f in cr.flags)


def test_schema_grounding_no_schema(default_config):
    backend = CustomBackend(fn=lambda q: ("SELECT 1", None))
    result = BackendResult(sql="SELECT 1", result=None, latency_ms=0)
    cr = _grounding_check().run("q", result, backend, default_config.checks)
    assert cr.score == 1.0
    assert "schema_unavailable" in cr.flags


# ── Self-consistency ───────────────────────────────────────────────────────────

def test_self_consistency_always_same(default_config):
    backend = CustomBackend(
        fn=lambda q: ("SELECT COUNT(*) FROM orders", [{"count": 10}])
    )
    result = BackendResult(
        sql="SELECT COUNT(*) FROM orders", result=[{"count": 10}], latency_ms=0
    )
    config = ChecksConfig(self_consistency_n=3)
    cr = SelfConsistencyCheck().run("q", result, backend, config)
    assert cr.score == 1.0


def test_self_consistency_always_different(default_config):
    call_count = [0]

    def varying_fn(q):
        call_count[0] += 1
        return (f"SELECT {call_count[0]} FROM orders", [{"v": call_count[0]}])

    backend = CustomBackend(fn=varying_fn)
    result = BackendResult(sql="SELECT 0 FROM orders", result=[{"v": 0}], latency_ms=0)
    config = ChecksConfig(self_consistency_n=3)
    cr = SelfConsistencyCheck().run("q", result, backend, config)
    assert cr.score < 1.0
    assert "sql_inconsistent" in cr.flags


# ── Reverse translation ────────────────────────────────────────────────────────

def test_reverse_translation_success(default_config):
    mock_response = {
        "message": {
            "content": '{"score": 0.95, "reasoning": "SQL matches question.", "flags": []}'
        }
    }
    check = ReverseTranslationCheck(OllamaConfig())
    result = BackendResult(sql="SELECT SUM(revenue) FROM orders", result=None, latency_ms=0)

    with patch("ollama.chat", return_value=mock_response):
        cr = check.run("Total revenue?", result, None, default_config.checks)

    assert abs(cr.score - 0.95) < 1e-6
    assert cr.passed
    assert cr.flags == []


def test_reverse_translation_llm_error(default_config):
    check = ReverseTranslationCheck(OllamaConfig())
    result = BackendResult(sql="SELECT 1", result=None, latency_ms=0)

    with patch("ollama.chat", side_effect=ConnectionError("Ollama offline")):
        cr = check.run("q", result, None, default_config.checks)

    assert cr.score == 0.5
    assert "llm_judge_error" in cr.flags


def test_reverse_translation_parse_error(default_config):
    check = ReverseTranslationCheck(OllamaConfig())
    result = BackendResult(sql="SELECT 1", result=None, latency_ms=0)
    mock_response = {"message": {"content": "not json at all"}}

    with patch("ollama.chat", return_value=mock_response):
        cr = check.run("q", result, None, default_config.checks)

    assert cr.score == 0.5
    assert "llm_judge_error" in cr.flags
