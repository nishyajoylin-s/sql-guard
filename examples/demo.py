"""
End-to-end demo using a mock backend (no real warehouse or Ollama needed).
Run: uv run python examples/demo.py
"""
from unittest.mock import patch

from sql_guard import Guard, CustomBackend
from sql_guard.checks.reverse_translation import ReverseTranslationCheck
from sql_guard.checks.schema_grounding import SchemaGroundingCheck
from sql_guard.checks.self_consistency import SelfConsistencyCheck
from sql_guard.config import Config, OllamaConfig


MOCK_SCHEMA = {
    "orders": ["id", "customer_id", "revenue", "created_at", "status"],
    "customers": ["id", "name", "email", "country"],
}


def my_sql_agent(question: str) -> tuple[str, list]:
    """Pretend text-to-SQL agent."""
    return (
        "SELECT SUM(revenue) AS total_revenue FROM orders WHERE status = 'completed'",
        [{"total_revenue": 3_812_447.00}],
    )


def main():
    backend = CustomBackend(
        fn=my_sql_agent,
        name="demo-agent",
        schema_map=MOCK_SCHEMA,
    )

    config = Config()
    checks = [
        SchemaGroundingCheck(),
        SelfConsistencyCheck(),
        ReverseTranslationCheck(OllamaConfig()),
    ]

    guard = Guard(
        backend=backend,
        event_store="duckdb:///demo.db",
        config=config,
        checks=checks,
    )

    mock_llm = {
        "message": {
            "content": '{"score": 0.92, "reasoning": "SQL correctly sums completed revenue.", "flags": []}'
        }
    }

    with patch("ollama.chat", return_value=mock_llm):
        report = guard.ask("How much revenue did we make last month?")

    print(f"\nQuestion : {report.question}")
    print(f"SQL      : {report.sql}")
    print(f"Answer   : {report.answer}")
    print(f"Trust    : {report.trust_score:.2%}")
    print(f"Flags    : {report.flags or 'none'}")
    print()
    for cr in report.check_results:
        status = "✓" if cr.passed else "✗"
        print(f"  {status} {cr.check_name:<25} score={cr.score:.2f}  {cr.detail}")

    print("\nEvent stored to demo.db — run `sql-guard dashboard` to view it.")


if __name__ == "__main__":
    main()
