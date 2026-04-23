import pytest

from sql_guard.backends.custom import CustomBackend


def test_run_returns_backend_result():
    def fn(q):
        return ("SELECT 1", [{"v": 1}])

    backend = CustomBackend(fn=fn)
    result = backend.run("test")
    assert result.sql == "SELECT 1"
    assert result.result == [{"v": 1}]
    assert result.latency_ms >= 0


def test_schema_passthrough():
    schema = {"orders": ["id", "revenue"]}
    backend = CustomBackend(fn=lambda q: ("SELECT 1", None), schema_map=schema)
    assert backend.schema() == schema


def test_schema_none_by_default():
    backend = CustomBackend(fn=lambda q: ("SELECT 1", None))
    assert backend.schema() is None


def test_exception_propagates():
    def bad_fn(q):
        raise ValueError("backend error")

    backend = CustomBackend(fn=bad_fn)
    with pytest.raises(ValueError, match="backend error"):
        backend.run("test")
