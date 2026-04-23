"""Auto-seeds realistic demo data when the event store is empty."""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

from sql_guard.models import TrustEvent
from sql_guard.store.duckdb_store import DuckDBStore

_BACKENDS = ["vanna-prod", "dataherald", "dbt-mcp"]
_BACKEND_WEIGHTS = [0.5, 0.3, 0.2]

_QUESTIONS = [
    ("What was total revenue last month?",
     "SELECT SUM(net_revenue) FROM fct_orders WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')",
     0.93, [],
     {"schema_grounding": 0.98, "self_consistency": 0.95, "reverse_translation": 0.92, "result_plausibility": 0.88}),
    ("How many active users do we have today?",
     "SELECT COUNT(DISTINCT user_id) FROM user_sessions WHERE session_date = CURRENT_DATE",
     0.91, [],
     {"schema_grounding": 0.97, "self_consistency": 0.94, "reverse_translation": 0.90, "result_plausibility": 0.85}),
    ("Show me revenue by region for Q3",
     "SELECT region, SUM(revenue) FROM sales WHERE quarter = 3 GROUP BY region ORDER BY 2 DESC",
     0.78, [],
     {"schema_grounding": 0.88, "self_consistency": 0.82, "reverse_translation": 0.75, "result_plausibility": 0.70}),
    ("What is the average order value this week?",
     "SELECT AVG(order_total) FROM orders WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)",
     0.95, [],
     {"schema_grounding": 0.99, "self_consistency": 0.97, "reverse_translation": 0.94, "result_plausibility": 0.92}),
    ("Which products had the highest sales in the last 30 days?",
     "SELECT product_name, SUM(quantity) FROM order_items JOIN products USING(product_id) WHERE created_at >= CURRENT_DATE - 30 GROUP BY 1 ORDER BY 2 DESC LIMIT 10",
     0.87, [],
     {"schema_grounding": 0.92, "self_consistency": 0.88, "reverse_translation": 0.85, "result_plausibility": 0.84}),
    ("What is our monthly recurring revenue?",
     "SELECT SUM(mrr) FROM customer_subscriptions WHERE status = 'active'",
     0.68, ["sql_inconsistent"],
     {"schema_grounding": 0.85, "self_consistency": 0.55, "reverse_translation": 0.72, "result_plausibility": 0.62}),
    ("How many new signups did we get this month?",
     "SELECT COUNT(*) FROM users WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)",
     0.90, [],
     {"schema_grounding": 0.96, "self_consistency": 0.93, "reverse_translation": 0.88, "result_plausibility": 0.86}),
    ("What is the churn rate for the last quarter?",
     "SELECT COUNT(*) FROM churned_customers / COUNT(*) FROM all_customers WHERE quarter = 2",
     0.32, ["sql_inconsistent", "unknown_table:churned_customers"],
     {"schema_grounding": 0.40, "self_consistency": 0.28, "reverse_translation": 0.35, "result_plausibility": 0.30}),
    ("Show me DAU for the past 7 days",
     "SELECT activity_date, COUNT(DISTINCT user_id) FROM dau_metrics GROUP BY 1 ORDER BY 1",
     0.88, [],
     {"schema_grounding": 0.94, "self_consistency": 0.90, "reverse_translation": 0.86, "result_plausibility": 0.83}),
    ("What are the top 5 customers by lifetime value?",
     "SELECT customer_name, SUM(order_total) AS ltv FROM customer_orders GROUP BY 1 ORDER BY 2 DESC LIMIT 5",
     0.85, [],
     {"schema_grounding": 0.90, "self_consistency": 0.87, "reverse_translation": 0.83, "result_plausibility": 0.80}),
    ("How many failed payments did we have last week?",
     "SELECT COUNT(*) FROM transactions WHERE status = 'failed' AND created_at >= CURRENT_DATE - 7",
     0.55, ["reverse_translation_mismatch"],
     {"schema_grounding": 0.75, "self_consistency": 0.60, "reverse_translation": 0.42, "result_plausibility": 0.58}),
    ("What is the conversion rate from trial to paid?",
     "SELECT COUNT(CASE WHEN plan = 'paid' THEN 1 END) * 1.0 / COUNT(*) FROM trial_conversions",
     0.72, [],
     {"schema_grounding": 0.80, "self_consistency": 0.75, "reverse_translation": 0.70, "result_plausibility": 0.68}),
    ("Show me the NPS score trend for the last 6 months",
     "SELECT month, AVG(nps_score) FROM customer_feedback GROUP BY month ORDER BY month",
     0.76, [],
     {"schema_grounding": 0.82, "self_consistency": 0.78, "reverse_translation": 0.74, "result_plausibility": 0.72}),
    ("What is the total support tickets opened this week?",
     "SELECT COUNT(*) FROM support_tickets_v2 WHERE opened_at >= DATE_TRUNC('week', CURRENT_DATE)",
     0.41, ["unknown_table:support_tickets_v2"],
     {"schema_grounding": 0.35, "self_consistency": 0.65, "reverse_translation": 0.55, "result_plausibility": 0.50}),
    ("What percentage of orders are fulfilled same-day?",
     "SELECT AVG(CASE WHEN fulfilled_at::date = created_at::date THEN 1.0 ELSE 0 END) FROM orders",
     0.83, [],
     {"schema_grounding": 0.88, "self_consistency": 0.85, "reverse_translation": 0.82, "result_plausibility": 0.78}),
    ("Show me month-over-month revenue growth",
     "SELECT month, revenue, LAG(revenue) OVER (ORDER BY month) AS prev, revenue / LAG(revenue) OVER (ORDER BY month) - 1 AS growth FROM monthly_revenue",
     0.89, [],
     {"schema_grounding": 0.93, "self_consistency": 0.91, "reverse_translation": 0.87, "result_plausibility": 0.85}),
    ("How many users completed onboarding this month?",
     "SELECT COUNT(*) FROM onboarding_completions WHERE completed_at >= DATE_TRUNC('month', CURRENT_DATE)",
     0.86, [],
     {"schema_grounding": 0.91, "self_consistency": 0.88, "reverse_translation": 0.84, "result_plausibility": 0.82}),
    ("What is the average session duration by device type?",
     "SELECT device_type, AVG(duration_seconds) FROM user_sessions GROUP BY device_type",
     0.80, [],
     {"schema_grounding": 0.85, "self_consistency": 0.82, "reverse_translation": 0.78, "result_plausibility": 0.76}),
    ("Show me revenue attribution by marketing channel",
     "SELECT utm_source, SUM(revenue) FROM orders JOIN attribution ON orders.session_id = attribution.session_id GROUP BY 1 ORDER BY 2 DESC",
     0.63, ["sql_inconsistent"],
     {"schema_grounding": 0.78, "self_consistency": 0.52, "reverse_translation": 0.65, "result_plausibility": 0.60}),
    ("What is our gross margin by product category?",
     "SELECT category, (SUM(revenue) - SUM(cogs)) / SUM(revenue) AS margin FROM products p JOIN order_items oi USING(product_id) GROUP BY 1",
     0.74, [],
     {"schema_grounding": 0.80, "self_consistency": 0.76, "reverse_translation": 0.72, "result_plausibility": 0.70}),
]

_WEIGHTS = [12, 12, 6, 11, 9, 2, 9, 1, 9, 7, 3, 6, 6, 1, 7, 8, 8, 7, 2, 6]

_RESULTS = [
    [{"total_revenue": 1482340.50}],
    [{"active_users": 8742}],
    [{"region": "North America", "revenue": 892000}, {"region": "Europe", "revenue": 541000}],
    [{"avg_order_value": 127.40}],
    [{"product_name": "Pro Plan", "quantity": 3841}],
    [{"mrr": 284500}],
    [{"signups": 1203}],
    [{"error": "syntax error near /"}],
    [{"date": "2024-03-01", "dau": 12400}],
    [{"customer": "Acme Corp", "ltv": 98200}],
    [{"failed_payments": 34}],
    [{"conversion_rate": 0.234}],
    [{"month": "2024-01", "avg_nps": 42.1}],
    [{"error": "table not found"}],
    [{"same_day_pct": 0.67}],
    [{"month": "2024-01", "revenue": 1200000, "growth": 0.12}],
    [{"completed": 892}],
    [{"device_type": "mobile", "avg_duration": 234.5}],
    [{"utm_source": "google", "revenue": 420000}],
    [{"category": "software", "margin": 0.72}],
]

_DEGRADATION_WINDOWS = [
    (18, 16, 0.88),
    (7,  10, 0.91),
]


def _jitter(base: float, spread: float = 0.06) -> float:
    return min(1.0, max(0.0, base + random.gauss(0, spread)))


def _latency(hour: int, phase: float = 1.0) -> int:
    if 9 <= hour <= 17:
        base = random.randint(380, 620)
    elif 7 <= hour <= 9 or 17 <= hour <= 20:
        base = random.randint(260, 440)
    else:
        base = random.randint(140, 280)
    return max(80, int(base / phase) + random.randint(-60, 120))


def _phase(ts: datetime, now: datetime) -> float:
    hours_ago = (now - ts).total_seconds() / 3600
    for days_ago, duration_h, factor in _DEGRADATION_WINDOWS:
        if (days_ago * 24 - duration_h) <= hours_ago <= (days_ago * 24):
            return factor
    return 1.0


def _make_event(ts: datetime, backend: str, phase: float, rng: random.Random) -> TrustEvent:
    idx = rng.choices(range(len(_QUESTIONS)), weights=_WEIGHTS)[0]
    question, sql, base_trust, flags, check_base = _QUESTIONS[idx]
    result = _RESULTS[idx % len(_RESULTS)]

    trust = _jitter(base_trust * phase)
    final_flags = list(flags)
    if phase < 0.92 and rng.random() > 0.6:
        final_flags.append("sql_inconsistent")
    if phase < 0.85 and rng.random() > 0.7:
        final_flags.append(rng.choice(["unknown_table:metrics_v3", "result_out_of_range"]))

    check_scores = {k: round(_jitter(v * phase, spread=0.04), 3) for k, v in check_base.items()}

    return TrustEvent(
        timestamp=ts,
        question=question,
        sql=sql,
        result=json.dumps(result),
        trust_score=round(trust, 4),
        flags=json.dumps(list(set(final_flags))),
        latency_ms=_latency(ts.hour, phase),
        token_count=rng.randint(280, 1800) if rng.random() > 0.15 else None,
        backend_name=backend,
        check_scores=json.dumps(check_scores),
    )


def _queries_per_hour(day_offset: int, hour: int, rng: random.Random) -> int:
    weekday = (datetime.now() - timedelta(days=day_offset)).weekday()
    if weekday >= 5:
        return 1 if 9 <= hour <= 17 else 0
    if 9 <= hour <= 17:
        return rng.randint(3, 8)
    if 7 <= hour <= 9 or 17 <= hour <= 20:
        return rng.randint(1, 3)
    return 0 if rng.random() > 0.3 else 1


def seed_demo_data(store: DuckDBStore, seed: int = 42) -> int:
    """Seed 30 days of realistic demo events. Returns number of events written."""
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    total = 0

    for day in range(30, 0, -1):
        for hour in range(24):
            ts_base = now - timedelta(days=day) + timedelta(hours=hour)
            for _ in range(_queries_per_hour(day, hour, rng)):
                ts = ts_base + timedelta(
                    minutes=rng.randint(0, 59),
                    seconds=rng.randint(0, 59),
                )
                backend = rng.choices(_BACKENDS, weights=_BACKEND_WEIGHTS)[0]
                store.write_event(_make_event(ts, backend, _phase(ts, now), rng))
                total += 1

    # Seed today so the 24h window always has data
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for hour in range(now.hour + 1):
        ts_base = today_start + timedelta(hours=hour)
        for _ in range(_queries_per_hour(0, hour, rng)):
            ts = ts_base + timedelta(
                minutes=rng.randint(0, 59),
                seconds=rng.randint(0, 59),
            )
            backend = rng.choices(_BACKENDS, weights=_BACKEND_WEIGHTS)[0]
            store.write_event(_make_event(ts, backend, _phase(ts, now), rng))
            total += 1

    return total
