import pytest

from sql_guard.backends.custom import CustomBackend
from sql_guard.config import Config
from sql_guard.store.duckdb_store import DuckDBStore


@pytest.fixture
def in_memory_store():
    return DuckDBStore("duckdb:///:memory:")


@pytest.fixture
def simple_backend():
    def my_fn(question: str):
        return ("SELECT SUM(revenue) AS revenue FROM orders", [{"revenue": 1000}])

    return CustomBackend(
        fn=my_fn,
        name="test",
        schema_map={"orders": ["id", "revenue", "created_at", "status"]},
    )


@pytest.fixture
def default_config():
    return Config()
