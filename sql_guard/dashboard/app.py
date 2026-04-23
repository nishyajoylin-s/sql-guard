from __future__ import annotations

import json
import os
import time
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="sql-guard · Trust Monitor",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background: #0D1117 !important; }
.stApp > header {
  background: rgba(13,17,23,0.95) !important;
  border-bottom: 1px solid rgba(255,255,255,0.07) !important;
  backdrop-filter: blur(12px) !important;
}
section.main .block-container { padding-top: 1.5rem !important; padding-bottom: 3rem !important; }
code, pre { font-family: 'JetBrains Mono', monospace !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: #161B22 !important;
  border-right: 1px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
  background: #161B22 !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 12px !important;
  padding: 18px 20px 16px !important;
  transition: border-color 0.15s !important;
}
[data-testid="stMetric"]:hover { border-color: rgba(255,255,255,0.14) !important; }
[data-testid="stMetricLabel"] > div {
  font-size: 10px !important;
  font-weight: 700 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  color: #484F58 !important;
}
[data-testid="stMetricValue"] > div {
  font-size: 24px !important;
  font-weight: 800 !important;
  letter-spacing: -0.03em !important;
  color: #E6EDF3 !important;
  line-height: 1.2 !important;
}
[data-testid="stMetricDelta"] > div { font-size: 11px !important; font-weight: 600 !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: #161B22 !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 10px !important;
  padding: 3px !important;
  gap: 2px !important;
  width: fit-content !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 8px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: #484F58 !important;
  background: transparent !important;
  border: none !important;
  padding: 6px 20px !important;
}
.stTabs [aria-selected="true"][data-baseweb="tab"] {
  background: #21262D !important;
  color: #E6EDF3 !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── Buttons ── */
.stButton > button {
  background: #21262D !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 8px !important;
  color: #E6EDF3 !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  font-family: 'Inter', sans-serif !important;
  transition: all 0.15s !important;
}
.stButton > button:hover { background: #2D333B !important; border-color: rgba(255,255,255,0.18) !important; }
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #00C9B1, #00AAFF) !important;
  border: none !important;
  color: #0D1117 !important;
  font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 0 20px rgba(0,201,177,0.3) !important;
  transform: translateY(-1px) !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: #21262D !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 8px !important;
  color: #E6EDF3 !important;
}
[data-testid="stSelectbox"] ul {
  background: #21262D !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 8px !important;
}
[data-testid="stSelectbox"] li { color: #8B949E !important; }
[data-testid="stSelectbox"] li:hover { background: rgba(255,255,255,0.05) !important; color: #E6EDF3 !important; }

/* ── Text Input ── */
[data-testid="stTextInput"] input {
  background: #21262D !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 8px !important;
  color: #E6EDF3 !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: #00C9B1 !important;
  box-shadow: 0 0 0 2px rgba(0,201,177,0.15) !important;
}
[data-testid="stTextInput"] input::placeholder { color: #484F58 !important; }
[data-testid="stTextInput"] label { font-size: 12px !important; color: #8B949E !important; font-weight: 500 !important; }

/* ── Slider ── */
[data-testid="stSlider"] > div > div > div > div { background: #00C9B1 !important; }
[data-testid="stSlider"] div[role="slider"] {
  background: #00C9B1 !important;
  border: 2px solid #0D1117 !important;
  box-shadow: 0 0 8px rgba(0,201,177,0.5) !important;
}

/* ── Progress ── */
[data-testid="stProgress"] > div { background: rgba(255,255,255,0.06) !important; border-radius: 9999px !important; }
[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, #00C9B1, #00AAFF) !important;
  border-radius: 9999px !important;
}

/* ── Toggle ── */
[data-baseweb="toggle"] { background: #21262D !important; border: 1px solid rgba(255,255,255,0.1) !important; }
[data-baseweb="toggle"][aria-checked="true"] { background: rgba(0,201,177,0.15) !important; border-color: rgba(0,201,177,0.3) !important; }
[data-baseweb="toggle"][aria-checked="true"] > div { background: #00C9B1 !important; }

/* ── Alerts ── */
[data-testid="stInfo"]    { background: rgba(88,166,255,0.08) !important; border: 1px solid rgba(88,166,255,0.2) !important; border-radius: 8px !important; color: #58A6FF !important; }
[data-testid="stSuccess"] { background: rgba(63,185,80,0.08) !important; border: 1px solid rgba(63,185,80,0.2) !important; border-radius: 8px !important; color: #3FB950 !important; }
[data-testid="stWarning"] { background: rgba(210,153,34,0.08) !important; border: 1px solid rgba(210,153,34,0.2) !important; border-radius: 8px !important; color: #D29922 !important; }
[data-testid="stError"]   { background: rgba(248,81,73,0.08) !important; border: 1px solid rgba(248,81,73,0.2) !important; border-radius: 8px !important; color: #F85149 !important; }

/* ── Form ── */
[data-testid="stForm"] {
  background: rgba(255,255,255,0.02) !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 10px !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
  background: #161B22 !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 10px !important;
}

/* ── DataFrame ── */
[data-testid="stDataFrame"] {
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 10px !important;
  overflow: hidden !important;
}

/* ── Code ── */
code { background: #21262D !important; color: #00C9B1 !important; border-radius: 4px !important; padding: 1px 5px !important; }
pre  { background: #161B22 !important; border: 1px solid rgba(255,255,255,0.07) !important; border-radius: 10px !important; }
[data-testid="stCode"] { border-radius: 10px !important; overflow: hidden !important; }

/* ── Markdown ── */
.stMarkdown p { color: #8B949E !important; }
.stMarkdown strong { color: #E6EDF3 !important; }
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 { color: #E6EDF3 !important; font-weight: 700 !important; }
.stMarkdown table { width: 100%; border-collapse: collapse; font-size: 13px; }
.stMarkdown th {
  text-align: left; padding: 8px 12px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
  color: #484F58; border-bottom: 1px solid rgba(255,255,255,0.07);
}
.stMarkdown td { padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); color: #8B949E; vertical-align: middle; }
.stMarkdown tr:last-child td { border: none; }
.stMarkdown tbody tr:hover { background: rgba(255,255,255,0.02); }
hr, [data-testid="stDivider"] { border-color: rgba(255,255,255,0.07) !important; margin: 20px 0 !important; }
.stCaption { color: #484F58 !important; font-size: 11px !important; }

/* ── Chart container ── */
[data-testid="stArrowVegaLiteChart"],
[data-testid="stVegaLiteChart"] {
  background: #161B22 !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 12px !important;
  padding: 16px 12px 12px !important;
  overflow: hidden !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 9999px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }

/* ── Live pulse animation ── */
@keyframes live-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0,201,177,0.5); }
  50%       { box-shadow: 0 0 0 5px rgba(0,201,177,0); }
}
</style>
""", unsafe_allow_html=True)


# ── Store ─────────────────────────────────────────────────────────────────────

@st.cache_resource
def _load_store():
    from sql_guard.config import load_config
    from sql_guard.store.duckdb_store import DuckDBStore
    config_path = os.environ.get("SQL_GUARD_CONFIG")
    cfg = load_config(Path(config_path) if config_path else None)
    store_uri = os.environ.get("SQL_GUARD_STORE", cfg.event_store)
    store = DuckDBStore(store_uri, read_only=False)

    # Auto-seed demo data when the store is empty (e.g. fresh Streamlit Cloud deploy)
    stats = store.get_summary_stats("30d")
    if stats["total"] == 0:
        from sql_guard.demo import seed_demo_data
        seed_demo_data(store)

    return store


# ── Altair theme ──────────────────────────────────────────────────────────────

_AX = dict(
    labelColor="#8B949E",
    titleColor="#8B949E",
    gridColor="rgba(255,255,255,0.06)",
    tickColor="rgba(0,0,0,0)",
    domainColor="rgba(0,0,0,0)",
    labelFontSize=11,
    titleFontSize=11,
    labelFont="Inter",
    titleFont="Inter",
    titleFontWeight=600,
    titlePadding=8,
)


def _chart(c, height: int = 260):
    return (
        c.properties(height=height, background="#161B22",
                     padding={"top": 4, "right": 8, "bottom": 4, "left": 8})
        .configure_view(strokeOpacity=0, fill="#161B22")
        .configure_axis(**_AX)
        .configure_legend(
            labelColor="#8B949E",
            titleColor="#484F58",
            labelFontSize=11,
            labelFont="Inter",
            padding=10,
            cornerRadius=6,
            fillColor="#1C2128",
            strokeColor="rgba(255,255,255,0.1)",
        )
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_ms(v) -> str:
    return "—" if v is None else f"{int(v)} ms"

def _fmt_pct(v) -> str:
    return "—" if v is None else f"{v:.1%}"

def _trust_color(score) -> str:
    if score is None:
        return "#484F58"
    return "#3FB950" if score >= 0.8 else "#D29922" if score >= 0.6 else "#F85149"

def _section(text: str, sub: str = "") -> None:
    sub_html = f'<div style="font-size:11px;color:#484F58;margin-top:3px;">{sub}</div>' if sub else ""
    st.markdown(
        f'<div style="margin-bottom:10px;">'
        f'<span style="font-size:10px;font-weight:700;letter-spacing:0.12em;'
        f'text-transform:uppercase;color:#8B949E;">{text}</span>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


# ── Health banner ─────────────────────────────────────────────────────────────

def _health_banner(stats: dict, threshold: float) -> None:
    pr = stats.get("pass_rate")
    at = stats.get("avg_trust") or 0
    total = stats.get("total", 0)

    if total == 0:
        bg = "rgba(255,255,255,0.03)"; bc = "rgba(255,255,255,0.08)"
        dot = "#484F58"; label = "NO DATA"; msg = "No events recorded in this time window."
    elif pr >= 0.9 and at >= 0.85:
        bg = "rgba(63,185,80,0.07)"; bc = "rgba(63,185,80,0.2)"
        dot = "#3FB950"; label = "HEALTHY"
        msg = f"Pass rate {pr:.0%} · Avg trust {at:.0%} · Agent performing well"
    elif pr >= threshold and at >= 0.7:
        bg = "rgba(210,153,34,0.07)"; bc = "rgba(210,153,34,0.2)"
        dot = "#D29922"; label = "DEGRADED"
        msg = f"Pass rate {pr:.0%} · Avg trust {at:.0%} · Some answers need review"
    else:
        bg = "rgba(248,81,73,0.07)"; bc = "rgba(248,81,73,0.2)"
        dot = "#F85149"; label = "CRITICAL"
        msg = f"Pass rate {pr:.0%} · Avg trust {at:.0%} · Agent needs immediate attention"

    st.markdown(f"""
<div style="background:{bg};border:1px solid {bc};border-radius:10px;
            padding:12px 20px;margin-bottom:20px;
            display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
  <div style="width:8px;height:8px;border-radius:50%;background:{dot};flex-shrink:0;
              animation:live-pulse 2s infinite;"></div>
  <span style="font-size:10px;font-weight:800;color:{dot};text-transform:uppercase;
               letter-spacing:0.15em;flex-shrink:0;">{label}</span>
  <div style="width:1px;height:14px;background:rgba(255,255,255,0.1);flex-shrink:0;"></div>
  <span style="font-size:13px;color:#8B949E;">{msg}</span>
  <span style="margin-left:auto;font-size:11px;color:#484F58;flex-shrink:0;">
    threshold {threshold:.0%}
  </span>
</div>
""", unsafe_allow_html=True)


# ── KPI row ───────────────────────────────────────────────────────────────────

def render_kpis(store, since: str, threshold: float, backend) -> None:
    stats = store.get_summary_stats(since, threshold=threshold, backend=backend)
    perf = store.get_latency_percentiles(since, backend=backend)
    act = store.get_activity_stats(since, backend=backend)

    cols = st.columns(6)
    cols[0].metric("Total Queries", f"{stats['total']:,}",
                   help="Questions answered in the selected window")
    cols[1].metric("Pass Rate", _fmt_pct(stats["pass_rate"]),
                   help=f"Answers with trust score ≥ {threshold:.0%}")
    cols[2].metric("Avg Trust", _fmt_pct(stats["avg_trust"]),
                   help="Mean trust score across all checks (0 = untrustworthy, 1 = fully trusted)")
    cols[3].metric("Latency P50", _fmt_ms(perf["p50"]),
                   help="Median response time — half of answers arrive faster than this")
    cols[4].metric("Latency P95", _fmt_ms(perf["p95"]),
                   help="95th-percentile response time — worst-case speed")
    cols[5].metric("Total Tokens",
                   f"{stats['total_tokens']:,}" if stats["total_tokens"] else "—",
                   help="Token count reported by backends (for cost estimation)")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    cols2 = st.columns(4)
    cols2[0].metric("Failed Queries", f"{stats['failed']:,}",
                    help=f"Queries where trust score < {threshold:.0%}")
    cols2[1].metric("Uptime", _fmt_pct(act["uptime_pct"]),
                    help="% of time buckets that had at least one query")
    cols2[2].metric("Active Periods", f"{act['active_buckets']}",
                    help="Time buckets with at least one query")
    cols2[3].metric("Busy Periods", f"{act['busy_buckets']}",
                    help="Time buckets with above-average query volume")


# ── Volume chart ──────────────────────────────────────────────────────────────

def render_volume(store, since: str, threshold: float, backend) -> None:
    _section("Query Volume", "Passed vs failed per time bucket")
    rows = store.get_volume_trend(since, threshold=threshold, backend=backend)
    if not rows:
        st.info("No data in this window.")
        return
    df = pd.DataFrame(rows)
    df["bucket"] = pd.to_datetime(df["bucket"])
    df_long = df.melt("bucket", var_name="status", value_name="count")
    df_long["label"] = df_long["status"].str.title()
    c = alt.Chart(df_long).mark_bar(opacity=0.9).encode(
        x=alt.X("bucket:T", title=None, axis=alt.Axis(format="%b %d", labelAngle=-30)),
        y=alt.Y("count:Q", title=None, stack="zero"),
        color=alt.Color("status:N",
            scale=alt.Scale(domain=["passed", "failed"], range=["#3FB950", "#F85149"]),
            legend=alt.Legend(orient="top-right", title=None),
        ),
        order=alt.Order("status:N", sort="descending"),
        tooltip=[
            alt.Tooltip("bucket:T", title="Time", format="%b %d %H:%M"),
            alt.Tooltip("label:N", title="Status"),
            alt.Tooltip("count:Q", title="Count"),
        ],
    )
    st.altair_chart(_chart(c), use_container_width=True)
    st.caption(f"Green ≥ {threshold:.0%} threshold · Red < {threshold:.0%}")


# ── Trust trend ───────────────────────────────────────────────────────────────

def render_trust_trend(store, since: str, threshold: float, backend) -> None:
    _section("Trust Score Trend", "Average trust per time bucket")
    rows = store.get_trust_trend(since, backend=backend)
    if not rows:
        st.info("No data.")
        return
    df = pd.DataFrame(rows)
    df["bucket"] = pd.to_datetime(df["bucket"])
    area = alt.Chart(df).mark_area(
        color="#00C9B1", opacity=0.15, interpolate="monotone",
        line={"color": "#00C9B1", "strokeWidth": 2},
    ).encode(
        x=alt.X("bucket:T", title=None, axis=alt.Axis(format="%b %d", labelAngle=-30)),
        y=alt.Y("avg_trust:Q", title=None, scale=alt.Scale(domainMin=0, domainMax=1)),
        tooltip=[
            alt.Tooltip("bucket:T", title="Time", format="%b %d %H:%M"),
            alt.Tooltip("avg_trust:Q", title="Avg Trust", format=".3f"),
            alt.Tooltip("n:Q", title="Queries"),
        ],
    )
    rule = alt.Chart(pd.DataFrame({"t": [threshold]})).mark_rule(
        color="#F85149", strokeDash=[4, 4], strokeWidth=1.5, opacity=0.6,
    ).encode(y="t:Q")
    st.altair_chart(_chart(area + rule), use_container_width=True)
    st.caption(f"Teal = avg trust · Red dashed = {threshold:.0%} threshold")


# ── Latency chart ─────────────────────────────────────────────────────────────

def render_latency(store, since: str, backend) -> None:
    _section("Latency", "P50 = typical · P95 = worst-case response time")
    rows = store.get_latency_trend(since, backend=backend)
    if not rows:
        st.info("No data.")
        return
    df = pd.DataFrame(rows)
    df["bucket"] = pd.to_datetime(df["bucket"])
    df_long = df.melt("bucket", var_name="pct", value_name="ms")
    c = alt.Chart(df_long).mark_line(strokeWidth=2, interpolate="monotone").encode(
        x=alt.X("bucket:T", title=None, axis=alt.Axis(format="%b %d", labelAngle=-30)),
        y=alt.Y("ms:Q", title="ms"),
        color=alt.Color("pct:N",
            scale=alt.Scale(domain=["p50", "p95"], range=["#00C9B1", "#7C5CDB"]),
            legend=alt.Legend(orient="top-right", title=None),
        ),
        tooltip=[
            alt.Tooltip("bucket:T", title="Time", format="%b %d %H:%M"),
            alt.Tooltip("pct:N", title="Percentile"),
            alt.Tooltip("ms:Q", title="Latency (ms)", format=".0f"),
        ],
    )
    st.altair_chart(_chart(c), use_container_width=True)
    st.caption("Widening gap between P50 and P95 = occasional slow outliers")


# ── Flag frequency ────────────────────────────────────────────────────────────

def render_flags(store, since: str, backend) -> None:
    _section("Flag Frequency", "Which checks fail most often")
    flags = store.get_flag_counts(since, backend=backend)
    if not flags:
        st.success("No flags raised in this period — agent output looks clean.")
        return
    df = pd.DataFrame(flags)
    base = alt.Chart(df)
    bars = base.mark_bar(
        color="#F85149", opacity=0.8,
        cornerRadiusTopRight=3, cornerRadiusBottomRight=3,
    ).encode(
        y=alt.Y("flag:N", title=None, sort="-x", axis=alt.Axis(labelLimit=280)),
        x=alt.X("count:Q", title=None),
        tooltip=[
            alt.Tooltip("flag:N", title="Flag"),
            alt.Tooltip("count:Q", title="Count"),
        ],
    )
    labels = base.mark_text(align="left", dx=5, color="#8B949E", fontSize=11).encode(
        y=alt.Y("flag:N", sort="-x"),
        x=alt.X("count:Q"),
        text=alt.Text("count:Q", format="d"),
    )
    st.altair_chart(_chart(bars + labels), use_container_width=True)
    st.caption("sql_inconsistent = agent disagrees with itself · unknown_table = hallucinated table")


# ── Trust distribution ────────────────────────────────────────────────────────

def render_trust_dist(store, since: str, backend) -> None:
    _section("Trust Distribution", "Ideal: most answers in the 0.8–1.0 band")
    hist = store.get_trust_histogram(since, backend=backend)
    if not hist:
        st.info("No data.")
        return
    df = pd.DataFrame(hist)
    order = ["0.0–0.2", "0.2–0.4", "0.4–0.6", "0.6–0.8", "0.8–1.0"]
    c = alt.Chart(df).mark_bar(
        opacity=0.9, cornerRadiusTopLeft=3, cornerRadiusTopRight=3,
    ).encode(
        x=alt.X("bucket:N", title=None, sort=order),
        y=alt.Y("count:Q", title=None),
        color=alt.Color("bucket:N",
            scale=alt.Scale(
                domain=order,
                range=["#F85149", "#F97316", "#D29922", "#84CC16", "#3FB950"],
            ),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("bucket:N", title="Trust Range"),
            alt.Tooltip("count:Q", title="Count"),
        ],
    )
    st.altair_chart(_chart(c), use_container_width=True)
    st.caption("Spread into lower bands = agent needs tuning")


# ── Token usage ───────────────────────────────────────────────────────────────

def render_tokens(store, since: str, backend) -> None:
    _section("Token Usage", "Total LLM tokens consumed per period")
    rows = store.get_token_trend(since, backend=backend)
    if not rows or all(r["tokens"] == 0 for r in rows):
        st.info("No token data — backend doesn't report token counts.")
        return
    df = pd.DataFrame(rows)
    df["bucket"] = pd.to_datetime(df["bucket"])
    c = alt.Chart(df).mark_bar(
        color="#7C5CDB", opacity=0.8,
        cornerRadiusTopLeft=2, cornerRadiusTopRight=2,
    ).encode(
        x=alt.X("bucket:T", title=None, axis=alt.Axis(format="%b %d", labelAngle=-30)),
        y=alt.Y("tokens:Q", title=None),
        tooltip=[
            alt.Tooltip("bucket:T", title="Time", format="%b %d %H:%M"),
            alt.Tooltip("tokens:Q", title="Tokens", format=","),
        ],
    )
    st.altair_chart(_chart(c), use_container_width=True)
    st.caption("Spikes = unusually complex questions · use for cost estimation")


# ── Low trust table ───────────────────────────────────────────────────────────

def render_low_trust_table(store, since: str, threshold: float, backend, n: int) -> None:
    _section("Low Trust Questions", f"Worst-scoring events · trust < {threshold:.0%}")
    rows = store.get_top_offenders(n=n, since=since, threshold=threshold, backend=backend)
    if not rows:
        st.success(f"No questions below {threshold:.0%} trust in this window.")
        return
    df = pd.DataFrame(rows)
    df["question"] = df["question"].str[:120]
    df["trust_score"] = df["trust_score"].round(3)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
    sel = st.dataframe(
        df[["timestamp", "question", "trust_score", "flags", "backend_name"]],
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "trust_score": st.column_config.ProgressColumn(
                "Trust", min_value=0, max_value=1, format="%.3f"
            ),
            "question":     st.column_config.TextColumn("Question", width="large"),
            "timestamp":    st.column_config.TextColumn("Time", width="small"),
            "flags":        st.column_config.TextColumn("Flags"),
            "backend_name": st.column_config.TextColumn("Backend"),
        },
    )
    if sel and sel.selection and sel.selection.rows:
        st.session_state["_sel_event"] = rows[sel.selection.rows[0]]["id"]
    st.caption("Click any row to drill into the full SQL, result, and per-check scores.")


# ── Event drill-through ───────────────────────────────────────────────────────

def render_drill_through(store, event_id: str) -> None:
    event = store.get_event(event_id)
    if not event:
        return

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:13px;font-weight:700;letter-spacing:0.02em;'
        'color:#E6EDF3;margin-bottom:14px;padding-top:4px;">EVENT DETAIL</div>',
        unsafe_allow_html=True,
    )

    score = event.get("trust_score") or 0
    score_color = _trust_color(score)
    flags_raw = event.get("flags")
    flag_list: list[str] = []
    if flags_raw:
        try:
            flag_list = json.loads(flags_raw) or []
        except Exception:
            pass

    flag_pills = "".join(
        f'<span style="background:rgba(248,81,73,0.1);border:1px solid rgba(248,81,73,0.2);'
        f'border-radius:6px;padding:2px 9px;font-size:11px;color:#F85149;font-weight:600;">{f}</span>'
        for f in flag_list
    ) or '<span style="font-size:12px;color:#484F58;">none</span>'

    # Summary strip
    st.markdown(f"""
<div style="background:#161B22;border:1px solid rgba(255,255,255,0.07);border-radius:12px;
            padding:16px 20px;margin-bottom:16px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
  <div>
    <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
                color:#484F58;margin-bottom:5px;">Trust Score</div>
    <div style="font-size:26px;font-weight:800;color:{score_color};letter-spacing:-0.02em;">
      {score:.2%}
    </div>
    <div style="width:80px;height:4px;background:rgba(255,255,255,0.06);border-radius:9999px;
                margin-top:6px;overflow:hidden;">
      <div style="width:{score*100:.0f}%;height:100%;background:{score_color};border-radius:9999px;"></div>
    </div>
  </div>
  <div style="width:1px;height:48px;background:rgba(255,255,255,0.07);flex-shrink:0;"></div>
  <div>
    <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
                color:#484F58;margin-bottom:5px;">Backend</div>
    <div style="font-size:14px;font-weight:600;color:#E6EDF3;">{event.get('backend_name') or '—'}</div>
  </div>
  <div style="width:1px;height:48px;background:rgba(255,255,255,0.07);flex-shrink:0;"></div>
  <div>
    <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
                color:#484F58;margin-bottom:7px;">Flags</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;">{flag_pills}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    col_q, col_r = st.columns([1, 1])
    with col_q:
        st.markdown(
            '<div style="font-size:10px;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#484F58;margin-bottom:8px;">Question</div>',
            unsafe_allow_html=True,
        )
        q = event.get("question", "")
        st.markdown(
            f'<div style="background:#161B22;border:1px solid rgba(255,255,255,0.07);'
            f'border-radius:10px;padding:14px 16px;font-size:14px;color:#E6EDF3;'
            f'line-height:1.55;">{q}</div>',
            unsafe_allow_html=True,
        )

    with col_r:
        st.markdown(
            '<div style="font-size:10px;font-weight:700;letter-spacing:0.1em;'
            'text-transform:uppercase;color:#484F58;margin-bottom:8px;">Result</div>',
            unsafe_allow_html=True,
        )
        result = event.get("result")
        if result:
            try:
                st.json(json.loads(result))
            except Exception:
                st.text(str(result)[:600])
        else:
            st.markdown(
                '<div style="color:#484F58;font-size:13px;padding:14px 0;">No result recorded.</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div style="font-size:10px;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#484F58;margin:16px 0 8px;">SQL</div>',
        unsafe_allow_html=True,
    )
    st.code(event.get("sql") or "—", language="sql")

    check_scores_raw = event.get("check_scores")
    if check_scores_raw:
        try:
            scores = json.loads(check_scores_raw)
            df = pd.DataFrame(list(scores.items()), columns=["check", "score"])
            df["color"] = df["score"].apply(lambda s: "#3FB950" if s >= 0.7 else "#F85149")
            st.markdown(
                '<div style="font-size:10px;font-weight:700;letter-spacing:0.1em;'
                'text-transform:uppercase;color:#484F58;margin:16px 0 10px;">Per-check Scores</div>',
                unsafe_allow_html=True,
            )
            c = alt.Chart(df).mark_bar(
                opacity=0.85,
                cornerRadiusTopLeft=3, cornerRadiusTopRight=3,
            ).encode(
                x=alt.X("check:N", title=None),
                y=alt.Y("score:Q", title=None, scale=alt.Scale(domain=[0, 1])),
                color=alt.Color("color:N", scale=None, legend=None),
                tooltip=[
                    alt.Tooltip("check:N", title="Check"),
                    alt.Tooltip("score:Q", title="Score", format=".3f"),
                ],
            )
            st.altair_chart(_chart(c, height=200), use_container_width=True)
            st.caption("Green ≥ 0.7 · Red < 0.7 · Each check contributes to the overall trust score")
        except Exception:
            pass

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("✕  Close detail", key="close_detail"):
        del st.session_state["_sel_event"]
        st.rerun()


# ── Backends tab ──────────────────────────────────────────────────────────────

def render_backends(config_path) -> None:
    from sql_guard.config import BackendConfig, load_config, save_config

    cfg = load_config(config_path)
    server_url = os.environ.get("SQL_GUARD_SERVER", "http://localhost:8080")

    st.markdown("### Connected Backends")
    st.markdown(
        "A backend is any text-to-SQL tool sql-guard monitors. "
        "Point your app at the proxy URL or POST events directly to `/track`."
    )
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if not cfg.backends:
        st.info("No backends configured yet. Add one below.")
    else:
        for b in cfg.backends:
            with st.expander(f"**{b.name}** — `{b.url}`"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"""
| Field | Value |
|---|---|
| **Proxy URL** | `{server_url}/proxy/{b.name}` |
| **Backend URL** | `{b.url}` |
| **Method** | `{b.method}` |
| **Question field** | `{b.question_field}` |
| **SQL field** | `{b.sql_field}` |
| **Result field** | `{b.result_field}` |
| **Auth** | `{"set" if b.auth_header else "none"}` |
""")
                with c2:
                    st.code(f"POST {server_url}/proxy/{b.name}", language="bash")
                    st.caption("or push API:")
                    st.code(
                        f'httpx.post("{server_url}/track",\n'
                        f'  json={{"question": ...,\n'
                        f'         "backend_name": "{b.name}"}})',
                        language="python",
                    )
                    if st.button(f"Delete {b.name}", key=f"del_{b.name}"):
                        cfg.backends = [x for x in cfg.backends if x.name != b.name]
                        save_config(cfg, config_path)
                        st.rerun()

    st.divider()
    st.markdown("### Add Backend")

    with st.form("add_backend"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name", placeholder="my-vanna",
                                 help="Unique identifier for this backend")
            url = st.text_input("Endpoint URL", placeholder="https://your-tool.com/ask",
                                help="Where sql-guard forwards proxy requests")
            method = st.selectbox("HTTP Method", ["POST", "GET"])
            auth = st.text_input("Auth header", placeholder="Bearer sk-...", type="password",
                                 help="Sent as Authorization header. Leave blank if not needed.")
        with c2:
            q_field = st.text_input("Question field", value="question",
                                    help="Key in request body holding the user's question")
            sql_field = st.text_input("SQL response field", value="sql",
                                      help="Key in response body holding the generated SQL")
            res_field = st.text_input("Result response field", value="result",
                                      help="Key in response body holding the query result")
            st.caption("Unsure about field names? Add the backend then use the Test section below.")

        if st.form_submit_button("Add backend", type="primary"):
            if not name or not url:
                st.error("Name and URL are required.")
            else:
                cfg.backends = [b for b in cfg.backends if b.name != name] + [
                    BackendConfig(
                        name=name, url=url, method=method,
                        auth_header=auth or None,
                        question_field=q_field, sql_field=sql_field, result_field=res_field,
                    )
                ]
                save_config(cfg, config_path)
                st.success(f"Backend '{name}' saved. Proxy URL: `{server_url}/proxy/{name}`")
                st.rerun()

    st.divider()
    st.markdown("### Test a Backend")
    st.markdown("Send a live request to verify your field mapping is correct.")

    names = [b.name for b in cfg.backends]
    if not names:
        st.info("Add a backend above to test it.")
    else:
        test_name = st.selectbox("Backend to test", names, key="test_select")
        test_q = st.text_input("Test question", value="What is the total revenue?", key="test_q")
        if st.button("Run test", type="primary"):
            try:
                import httpx as _httpx
                idx = names.index(test_name)
                resp = _httpx.post(
                    f"{server_url}/api/backends/{test_name}/test",
                    json={cfg.backends[idx].question_field: test_q},
                    timeout=15,
                )
                r = resp.json()
                if r.get("status") == "ok":
                    st.success(f"Connected in {r['latency_ms']} ms")
                    rc1, rc2 = st.columns(2)
                    rc1.markdown("**Raw response:**"); rc1.json(r["response"])
                    rc2.markdown("**Detected fields:**"); rc2.json(r["detected"])
                else:
                    st.error(f"Error: {r.get('detail', r)}")
            except Exception as e:
                st.error(
                    f"Could not reach sql-guard server at {server_url}. "
                    f"Is it running? (`sql-guard serve`)\n\n{e}"
                )


# ── About tab ────────────────────────────────────────────────────────────────

def render_about() -> None:
    def _h(text: str) -> None:
        st.markdown(
            f'<div style="font-size:13px;font-weight:700;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:#8B949E;margin:28px 0 12px;">{text}</div>',
            unsafe_allow_html=True,
        )

    def _card(content: str) -> None:
        st.markdown(
            f'<div style="background:#161B22;border:1px solid rgba(255,255,255,0.07);'
            f'border-radius:12px;padding:20px 24px;">{content}</div>',
            unsafe_allow_html=True,
        )

    # Header
    st.markdown("""
<div style="margin-bottom:28px;">
  <h1 style="font-size:26px;font-weight:800;letter-spacing:-0.025em;color:#E6EDF3;
             line-height:1.15;margin:0 0 6px;">About sql-guard</h1>
  <p style="font-size:14px;color:#8B949E;margin:0;max-width:640px;line-height:1.6;">
    The open-source trust and observability layer for text-to-SQL and conversational BI agents.
    Every question your agent answers gets a trust score before it reaches a stakeholder.
  </p>
</div>
""", unsafe_allow_html=True)

    # What it does
    _h("What it does")
    _card("""
<p style="color:#8B949E;font-size:13px;line-height:1.7;margin:0 0 16px;">
AI agents that write SQL are confidently wrong a lot of the time. The SQL runs, the number looks
plausible, and nobody notices the agent used the wrong column, made up a join, or silently
redefined a KPI.
</p>
<p style="color:#8B949E;font-size:13px;line-height:1.7;margin:0;">
sql-guard wraps any text-to-SQL agent and verifies every answer in real time before it reaches
a stakeholder. Every query gets a <strong style="color:#E6EDF3;">trust score</strong> (0–1),
a list of <strong style="color:#E6EDF3;">flagged issues</strong>, and an entry in an
<strong style="color:#E6EDF3;">event store</strong> that powers this dashboard.
</p>
""")

    # Trust score
    _h("How the trust score works")
    st.markdown("""
| Score range | Meaning |
|---|---|
| **0.85 – 1.00** | High trust — agent almost certainly answered correctly |
| **0.70 – 0.85** | Moderate trust — worth spot-checking before sharing |
| **0.50 – 0.70** | Low trust — likely contains an error or hallucination |
| **0.00 – 0.50** | Very low trust — agent output should not be used |

The final score is a weighted average of all enabled checks.
Disabled checks redistribute their weight so the maximum is always 1.0.
""")

    # Checks
    _h("Trust checks")
    col1, col2 = st.columns(2)
    checks = [
        ("Schema Grounding", "#00C9B1",
         "Verifies every table, column, and function in the generated SQL exists in the warehouse schema. "
         "Flags: <code style='color:#00C9B1;'>unknown_table:X</code>, <code style='color:#00C9B1;'>unknown_column:X</code>"),
        ("Self-consistency", "#00AAFF",
         "Re-runs the backend 2–5 times and compares SQL output. An agent that writes different SQL for "
         "the same question cannot be trusted. Flags: <code style='color:#00AAFF;'>sql_inconsistent</code>"),
        ("Reverse Translation", "#7C5CDB",
         "Asks an LLM judge whether the generated SQL actually answers the user's question. "
         "Catches SQL that runs but solves the wrong problem. Flags: <code style='color:#7C5CDB;'>question_mismatch</code>"),
        ("Semantic Cross-check", "#D29922",
         "Compares the agent's answer against the definition in your dbt MetricFlow or Cube semantic "
         "layer. Flags deviations from sanctioned metric definitions. Flags: <code style='color:#D29922;'>metric_deviation</code>"),
        ("Result Plausibility", "#3FB950",
         "Compares the numeric result against a statistical baseline (rolling 30-day or static range). "
         "Flags values that are statistically implausible for that metric. Flags: <code style='color:#3FB950;'>implausible_result</code>"),
    ]
    for i, (name, color, desc) in enumerate(checks):
        col = col1 if i % 2 == 0 else col2
        with col:
            st.markdown(f"""
<div style="background:#161B22;border:1px solid rgba(255,255,255,0.07);border-radius:12px;
            padding:16px 18px;margin-bottom:12px;border-left:3px solid {color};">
  <div style="font-size:12px;font-weight:700;color:{color};margin-bottom:6px;">{name}</div>
  <div style="font-size:12px;color:#8B949E;line-height:1.6;">{desc}</div>
</div>
""", unsafe_allow_html=True)

    # Flags
    _h("Flag reference")
    st.markdown("""
| Flag | Raised by | Meaning |
|---|---|---|
| `sql_inconsistent` | Self-consistency | Agent produced different SQL across repeated runs |
| `unknown_table:X` | Schema grounding | Table X does not exist in the warehouse schema |
| `unknown_column:X` | Schema grounding | Column X does not exist in the referenced table |
| `question_mismatch` | Reverse translation | Generated SQL answers a different question than asked |
| `metric_deviation` | Semantic cross-check | Answer contradicts the sanctioned metric definition |
| `implausible_result` | Result plausibility | Numeric result is outside statistically expected range |
| `llm_unavailable` | Any LLM check | LLM request failed — check scored at 0.5 (neutral) |
""")

    # Dashboard guide
    _h("Reading the dashboard")
    st.markdown("""
| Panel | How to read it |
|---|---|
| **Health banner** | HEALTHY / DEGRADED / CRITICAL — derived from pass rate and avg trust. Read this first. |
| **Pass Rate** | % of answers at or above your threshold. Below 80% is a concern. |
| **Avg Trust** | Mean trust score. Below 0.75 warrants investigation. |
| **Latency P95** | 95th-percentile response time. High P95 = occasional freezes. |
| **Query Volume** | Green = passed, red = failed. Rising red = agent degrading. |
| **Trust Score Trend** | Y-axis is always 0–1. A dip means recent answers are less reliable. |
| **Latency chart** | Widening gap between P50 and P95 = occasional slow outliers. |
| **Flag Frequency** | Tallest bar = most systematic weakness. Fix these checks first. |
| **Trust Distribution** | Ideal: most answers in the 0.8–1.0 band. Spread = tuning needed. |
| **Low Trust Questions** | Sorted worst-first. Click any row to inspect full SQL and per-check scores. |
""")

    # Integration
    _h("Integration options")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""
<div style="background:#161B22;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px 18px;height:100%;">
  <div style="font-size:12px;font-weight:700;color:#00C9B1;margin-bottom:8px;">A — Proxy</div>
  <div style="font-size:12px;color:#8B949E;line-height:1.6;margin-bottom:10px;">
    Point your app at the sql-guard proxy URL. Zero code changes needed.
  </div>
</div>
""", unsafe_allow_html=True)
        st.code("POST /proxy/{backend_name}", language="bash")

    with col_b:
        st.markdown("""
<div style="background:#161B22;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px 18px;height:100%;">
  <div style="font-size:12px;font-weight:700;color:#00AAFF;margin-bottom:8px;">B — Push API</div>
  <div style="font-size:12px;color:#8B949E;line-height:1.6;margin-bottom:10px;">
    Call <code>/track</code> from your existing code after getting an answer.
  </div>
</div>
""", unsafe_allow_html=True)
        st.code('httpx.post("/track", json={\n  "question": ...,\n  "sql": ...,\n  "result": ...\n})', language="python")

    with col_c:
        st.markdown("""
<div style="background:#161B22;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px 18px;height:100%;">
  <div style="font-size:12px;font-weight:700;color:#7C5CDB;margin-bottom:8px;">C — Python library</div>
  <div style="font-size:12px;color:#8B949E;line-height:1.6;margin-bottom:10px;">
    Wrap calls directly with <code>guard.ask()</code> for synchronous trust scoring.
  </div>
</div>
""", unsafe_allow_html=True)
        st.code('report = guard.ask("...")\nprint(report.trust_score)', language="python")

    # Footer
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("""
<div style="background:#161B22;border:1px solid rgba(255,255,255,0.07);border-radius:12px;
            padding:16px 24px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
  <div>
    <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#484F58;margin-bottom:3px;">Version</div>
    <div style="font-size:13px;font-weight:600;color:#E6EDF3;">0.1.0 · Alpha</div>
  </div>
  <div style="width:1px;height:28px;background:rgba(255,255,255,0.07);"></div>
  <div>
    <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#484F58;margin-bottom:3px;">License</div>
    <div style="font-size:13px;font-weight:600;color:#E6EDF3;">MIT</div>
  </div>
  <div style="width:1px;height:28px;background:rgba(255,255,255,0.07);"></div>
  <div>
    <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#484F58;margin-bottom:3px;">Event Store</div>
    <div style="font-size:13px;font-weight:600;color:#E6EDF3;">DuckDB · Postgres</div>
  </div>
  <div style="width:1px;height:28px;background:rgba(255,255,255,0.07);"></div>
  <div>
    <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#484F58;margin-bottom:3px;">Built with</div>
    <div style="font-size:13px;font-weight:600;color:#E6EDF3;">Streamlit · Altair · DuckDB · FastAPI</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Sidebar
    with st.sidebar:
        st.markdown("""
<div style="display:flex;align-items:center;gap:10px;padding:4px 0 20px;
     border-bottom:1px solid rgba(255,255,255,0.07);">
  <div style="width:32px;height:32px;border-radius:8px;flex-shrink:0;
       background:linear-gradient(135deg,#00C9B1,#00AAFF);
       display:flex;align-items:center;justify-content:center;
       font-size:11px;font-weight:900;color:#0D1117;letter-spacing:-0.02em;">SG</div>
  <span style="font-size:16px;font-weight:800;letter-spacing:-0.02em;
       background:linear-gradient(135deg,#00C9B1,#00AAFF);
       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
       background-clip:text;">sql-guard</span>
</div>
""", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        st.markdown(
            '<div style="font-size:10px;font-weight:700;letter-spacing:0.12em;'
            'text-transform:uppercase;color:#484F58;margin-bottom:6px;">Time Window</div>',
            unsafe_allow_html=True,
        )
        since = st.selectbox(
            "Time window", ["1h", "24h", "7d", "30d"], index=1,
            label_visibility="collapsed",
            help="All panels update to this time range",
        )

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:10px;font-weight:700;letter-spacing:0.12em;'
            'text-transform:uppercase;color:#484F58;margin-bottom:6px;">Backend</div>',
            unsafe_allow_html=True,
        )
        try:
            _store = _load_store()
            backend_opts = ["All"] + _store.get_backends()
        except Exception:
            backend_opts = ["All"]
        bc = st.selectbox("Backend", backend_opts, label_visibility="collapsed")
        backend = None if bc == "All" else bc

        st.divider()

        st.markdown(
            '<div style="font-size:10px;font-weight:700;letter-spacing:0.12em;'
            'text-transform:uppercase;color:#484F58;margin-bottom:6px;">Pass Threshold</div>',
            unsafe_allow_html=True,
        )
        threshold = st.slider(
            "Pass threshold", 0.50, 0.95, 0.70, 0.05, format="%.2f",
            label_visibility="collapsed",
            help="Trust ≥ this = PASS. Affects KPIs, charts, and the offenders table.",
        )
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:10px;font-weight:700;letter-spacing:0.12em;'
            'text-transform:uppercase;color:#484F58;margin-bottom:6px;">Offenders Limit</div>',
            unsafe_allow_html=True,
        )
        n_offenders = st.slider(
            "Offenders", 5, 50, 20, 5, label_visibility="collapsed",
            help="How many low-trust questions to show in the table",
        )

        st.divider()
        auto_refresh = st.toggle("Auto-refresh (30s)", value=False)

    config_path = (
        Path(os.environ["SQL_GUARD_CONFIG"])
        if os.environ.get("SQL_GUARD_CONFIG") else None
    )

    tab_overview, tab_backends, tab_about = st.tabs(["Overview", "Backends", "About"])

    with tab_backends:
        render_backends(config_path)

    with tab_about:
        render_about()

    with tab_overview:
        # Header
        st.markdown(f"""
<div style="display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:20px;">
  <div>
    <h1 style="font-size:26px;font-weight:800;letter-spacing:-0.025em;color:#E6EDF3;
               line-height:1.15;margin:0 0 4px;">Trust Monitor</h1>
    <p style="font-size:12px;color:#484F58;margin:0;font-weight:500;">
      sql-guard · text-to-SQL reliability · window: {since}
    </p>
  </div>
  <div style="display:flex;align-items:center;gap:7px;
              background:rgba(0,201,177,0.07);border:1px solid rgba(0,201,177,0.18);
              border-radius:9999px;padding:5px 12px 5px 9px;flex-shrink:0;">
    <div style="width:7px;height:7px;border-radius:50%;background:#00C9B1;
                animation:live-pulse 2s infinite;"></div>
    <span style="font-size:10px;font-weight:700;letter-spacing:0.1em;color:#00C9B1;">LIVE</span>
  </div>
</div>
""", unsafe_allow_html=True)

        try:
            store = _load_store()
        except Exception as e:
            st.error(f"Could not connect to event store: {e}")
            return

        stats = store.get_summary_stats(since, threshold=threshold, backend=backend)
        _health_banner(stats, threshold)

        render_kpis(store, since, threshold, backend)
        st.divider()

        col_v, col_t = st.columns([3, 2])
        with col_v:
            render_volume(store, since, threshold, backend)
        with col_t:
            render_trust_trend(store, since, threshold, backend)

        st.divider()

        col_l, col_f = st.columns(2)
        with col_l:
            render_latency(store, since, backend)
        with col_f:
            render_flags(store, since, backend)

        st.divider()

        col_d, col_tk = st.columns(2)
        with col_d:
            render_trust_dist(store, since, backend)
        with col_tk:
            render_tokens(store, since, backend)

        st.divider()

        render_low_trust_table(store, since, threshold, backend, n_offenders)

        if "_sel_event" in st.session_state:
            render_drill_through(store, st.session_state["_sel_event"])

    if auto_refresh:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
