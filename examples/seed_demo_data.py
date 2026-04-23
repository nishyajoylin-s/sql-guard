"""
Seeds realistic demo data into sql_guard.db so the dashboard has something to show.
Run: uv run python examples/seed_demo_data.py
"""
import json
import random
from datetime import datetime, timedelta, timezone

from sql_guard.models import TrustEvent
from sql_guard.store.duckdb_store import DuckDBStore

QUESTIONS = [
    ("Total revenue last month?", "SELECT SUM(revenue) FROM orders WHERE ...", 0.95, []),
    ("How many active users?", "SELECT COUNT(*) FROM users WHERE active=1", 0.88, []),
    ("Revenue by region?", "SELECT region, SUM(rev) FROM sales GROUP BY region", 0.72, []),
    ("Top 10 products by sales?", "SELECT product_id, SUM(qty) FROM nonexistent_table", 0.41, ["unknown_table:nonexistent_table"]),
    ("MRR trend?", "SELECT month, SUM(mrr) FROM metrics GROUP BY month", 0.65, ["sql_inconsistent"]),
    ("Churn rate last quarter?", "SELECT COUNT(*) FROM churned / COUNT(*) FROM all_users", 0.30, ["sql_inconsistent", "result_inconsistent"]),
    ("DAU this week?", "SELECT date, COUNT(DISTINCT user_id) FROM events GROUP BY date", 0.91, []),
    ("Average order value?", "SELECT AVG(order_total) FROM orders", 0.97, []),
    ("New signups today?", "SELECT COUNT(*) FROM signups WHERE created_at >= TODAY()", 0.82, []),
    ("Failed payments last week?", "SELECT * FROM payments WHERE status = 'failed'", 0.55, ["reverse_translation_mismatch"]),
]

store = DuckDBStore("duckdb:///sql_guard.db")
now = datetime.now(timezone.utc)

for i in range(120):
    q, sql, base_score, flags = random.choice(QUESTIONS)
    score = min(1.0, max(0.0, base_score + random.uniform(-0.08, 0.08)))
    ts = now - timedelta(minutes=random.randint(0, 60 * 24))  # spread over last 24h

    event = TrustEvent(
        timestamp=ts,
        question=q,
        sql=sql,
        result=json.dumps([{"value": round(random.uniform(100, 100000), 2)}]),
        trust_score=round(score, 4),
        flags=json.dumps(flags),
        latency_ms=random.randint(200, 4500),
        token_count=random.randint(300, 1800) if random.random() > 0.2 else None,
        backend_name=random.choice(["vanna", "custom", "dbt-mcp"]),
        check_scores=json.dumps({
            "schema_grounding": round(random.uniform(0.6, 1.0), 3),
            "self_consistency": round(random.uniform(0.5, 1.0), 3),
            "reverse_translation": round(score + random.uniform(-0.1, 0.1), 3),
        }),
    )
    store.write_event(event)

print("Seeded 120 events into sql_guard.db")
