from __future__ import annotations

import json
import os
import time
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="sql-guard", layout="wide", page_icon="🛡️")

# ── Design System CSS ──────────────────────────────────────────────────────────

def _load_css() -> str:
    static = Path(__file__).parent / "static"
    return (static / "tokens.css").read_text() + "\n" + (static / "components.css").read_text()

st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
/* ── Streamlit overrides (uses data-minds tokens) ── */

html, body { font-family: var(--font-sans) !important; }
.stApp { background: var(--bg-base) !important; }
.stApp > header {
  background: rgba(6,10,18,0.85) !important;
  backdrop-filter: var(--blur-md) !important;
  border-bottom: 1px solid var(--border) !important;
}
section.main .block-container { background: transparent !important; padding-top: 1.5rem !important; }
.stApp, .stApp * { font-family: var(--font-sans) !important; }
code, pre, code *, pre * { font-family: var(--font-mono) !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: rgba(10,16,32,0.97) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stSelectbox label {
  font-size: var(--text-xs) !important; color: var(--text-secondary) !important; font-weight: var(--font-medium) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
  background: var(--surface-1) !important;
  backdrop-filter: var(--blur-md) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  padding: var(--space-5) !important;
}
[data-testid="stMetricLabel"] > div {
  font-size: var(--text-xs) !important;
  font-weight: var(--font-bold) !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--text-tertiary) !important;
}
[data-testid="stMetricValue"] > div {
  font-size: 30px !important;
  font-weight: var(--font-black) !important;
  letter-spacing: -0.03em !important;
  color: var(--text-primary) !important;
  line-height: var(--leading-tight) !important;
}
[data-testid="stMetricDelta"] > div { font-size: var(--text-xs) !important; font-weight: var(--font-semibold) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--surface-1) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-full) !important;
  padding: 3px !important;
  gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: var(--radius-full) !important;
  font-size: var(--text-base) !important;
  font-weight: var(--font-medium) !important;
  color: var(--text-tertiary) !important;
  background: transparent !important;
  border: none !important;
  padding: 6px 18px !important;
}
.stTabs [aria-selected="true"][data-baseweb="tab"] {
  background: var(--surface-3) !important;
  color: var(--text-primary) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── Buttons ── */
.stButton > button {
  border-radius: var(--radius-md) !important;
  font-weight: var(--font-semibold) !important;
  font-size: var(--text-base) !important;
  transition: all var(--ease-base) !important;
}
.stButton > button[kind="primary"] {
  background: var(--grad-accent) !important;
  color: var(--text-inverse) !important;
  border: none !important;
  box-shadow: 0 0 20px var(--accent-dim) !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: var(--shadow-accent) !important;
  transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
  background: var(--surface-2) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover { background: var(--surface-3) !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background: var(--surface-1) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-primary) !important;
}
[data-testid="stSelectbox"] ul {
  background: var(--surface-solid) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
}
[data-testid="stSelectbox"] li { color: var(--text-secondary) !important; }
[data-testid="stSelectbox"] li:hover { background: var(--surface-2) !important; color: var(--text-primary) !important; }

/* ── Text Input ── */
[data-testid="stTextInput"] input {
  background: var(--surface-1) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-primary) !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-dim) !important;
}
[data-testid="stTextInput"] input::placeholder { color: var(--text-tertiary) !important; }
[data-testid="stTextInput"] label { font-size: var(--text-sm) !important; color: var(--text-secondary) !important; font-weight: var(--font-medium) !important; }

/* ── Slider ── */
[data-testid="stSlider"] > div > div > div > div {
  background: var(--grad-accent) !important;
}
[data-testid="stSlider"] div[role="slider"] {
  background: var(--accent) !important;
  border: 2px solid var(--bg-base) !important;
  box-shadow: 0 0 8px var(--accent-glow) !important;
}

/* ── Progress (drill-through) ── */
[data-testid="stProgress"] > div { background: rgba(255,255,255,0.06) !important; border-radius: var(--radius-full) !important; }
[data-testid="stProgress"] > div > div { background: var(--grad-accent) !important; border-radius: var(--radius-full) !important; }

/* ── Native HTML details/summary (guide) ── */
details > summary { list-style: none; }
details > summary::-webkit-details-marker { display: none; }

/* ── Streamlit expander (backends tab) ── */
[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
}

/* ── Alerts ── */
[data-testid="stInfo"]    { background: var(--info-dim) !important;    border: 1px solid rgba(59,130,246,0.2) !important;  border-radius: var(--radius-md) !important; color: var(--info) !important; }
[data-testid="stSuccess"] { background: var(--success-dim) !important; border: 1px solid rgba(34,197,94,0.2) !important;   border-radius: var(--radius-md) !important; color: var(--success) !important; }
[data-testid="stWarning"] { background: var(--warning-dim) !important; border: 1px solid rgba(245,158,11,0.2) !important;  border-radius: var(--radius-md) !important; color: var(--warning) !important; }
[data-testid="stError"]   { background: var(--danger-dim) !important;  border: 1px solid rgba(239,68,68,0.2) !important;   border-radius: var(--radius-md) !important; color: var(--danger) !important; }

/* ── Form ── */
[data-testid="stForm"] {
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
}

/* ── Toggle ── */
[data-baseweb="toggle"] { background: var(--surface-3) !important; }
[data-baseweb="toggle"][aria-checked="true"] { background: var(--accent-dim) !important; }
[data-baseweb="toggle"][aria-checked="true"] > div { background: var(--accent) !important; }

/* ── Dividers ── */
hr, [data-testid="stDivider"] { border-color: var(--border) !important; }

/* ── Markdown ── */
.stMarkdown strong { color: var(--text-primary) !important; }
.stMarkdown p { color: var(--text-secondary) !important; }
.stMarkdown h1, .stMarkdown h2 { font-weight: var(--font-black) !important; letter-spacing: -0.025em !important; color: var(--text-primary) !important; }
.stMarkdown h3, .stMarkdown h4 { font-weight: var(--font-bold) !important; color: var(--text-primary) !important; }
.stMarkdown table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.stMarkdown th { text-align: left; padding: 8px 12px; font-size: var(--text-xs); font-weight: var(--font-bold); letter-spacing: 0.07em; text-transform: uppercase; color: var(--text-tertiary); border-bottom: 1px solid var(--border); }
.stMarkdown td { padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); color: var(--text-secondary); vertical-align: middle; }
.stMarkdown tr:last-child td { border: none; }
.stMarkdown tbody tr:hover { background: var(--surface-1); }

/* ── Code ── */
code { background: var(--surface-2) !important; color: var(--accent) !important; border-radius: 4px !important; padding: 1px 5px !important; }
pre  { background: var(--surface-1) !important; border: 1px solid var(--border) !important; border-radius: var(--radius-md) !important; }
[data-testid="stCode"] { border-radius: var(--radius-md) !important; overflow: hidden !important; }

/* ── Altair chart glass container ── */
[data-testid="stArrowVegaLiteChart"],
[data-testid="stVegaLiteChart"] {
  background: var(--surface-1) !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: var(--radius-md) !important;
  padding: 8px 4px 4px !important;
}

/* ── DataFrame ── */
[data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: var(--radius-md) !important; overflow: hidden !important; }

/* ── Caption ── */
.stCaption { color: var(--text-tertiary) !important; font-size: var(--text-xs) !important; }
</style>
""", unsafe_allow_html=True)


# ── Store ─────────────────────────────────────────────────────────────────────

def _load_store():
    from sql_guard.config import load_config
    from sql_guard.store.duckdb_store import DuckDBStore

    config_path = os.environ.get("SQL_GUARD_CONFIG")
    cfg = load_config(Path(config_path) if config_path else None)
    store_uri = os.environ.get("SQL_GUARD_STORE", cfg.event_store)
    return DuckDBStore(store_uri, read_only=False)


# ── Altair dark theme ─────────────────────────────────────────────────────────

_AX = dict(
    labelColor="#4A6070",
    titleColor="#4A6070",
    gridColor="rgba(255,255,255,0.07)",
    tickColor="rgba(0,0,0,0)",
    domainColor="rgba(0,0,0,0)",
    labelFontSize=10,
    labelFont="Inter",
)

def _dark(chart, height: int = 280):
    """Apply transparent dark theme to an Altair chart."""
    return (
        chart.properties(height=height, background="transparent")
        .configure_view(strokeOpacity=0, fill="transparent")
        .configure_axis(**_AX)
        .configure_legend(
            labelColor="#8B9CB0", titleColor="#4A6070",
            labelFontSize=11, labelFont="Inter",
            padding=8,
        )
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_ms(ms) -> str:
    return "—" if ms is None else f"{int(ms)} ms"

def _fmt_pct(v) -> str:
    return "—" if v is None else f"{v:.1%}"

def _trust_color(score) -> str:
    if score is None:
        return "gray"
    return "green" if score >= 0.8 else "orange" if score >= 0.6 else "red"

def _section_label(text: str) -> None:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;padding-bottom:8px;">'
        f'<div style="width:2px;height:12px;background:var(--grad-accent);border-radius:var(--radius-full);flex-shrink:0;"></div>'
        f'<span class="dm-section-label">{text}</span></div>',
        unsafe_allow_html=True,
    )

def _section_header(text: str) -> None:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;padding:20px 0 12px;">'
        f'<div style="width:3px;height:14px;background:var(--grad-accent);border-radius:var(--radius-full);flex-shrink:0;"></div>'
        f'<span class="dm-section-label">{text}</span></div>',
        unsafe_allow_html=True,
    )

def _backends_section(text: str, caption: str = "") -> None:
    st.markdown(
        f'<div style="margin-bottom:{"2" if caption else "12"}px;">'
        f'<span style="font-size:var(--text-xl);font-weight:var(--font-extrabold);letter-spacing:-0.02em;color:var(--text-primary);">{text}</span>'
        f'</div>'
        + (f'<div style="font-size:var(--text-sm);color:var(--text-tertiary);margin-bottom:16px;">{caption}</div>' if caption else ""),
        unsafe_allow_html=True,
    )



# ── How to read this dashboard ────────────────────────────────────────────────

def render_guide(threshold: float) -> None:
    th = f"{threshold:.0%}"
    st.markdown(f"""
<div class="dm-card dm-card-sm" style="margin-bottom:16px;overflow:hidden;">
  <details>
    <summary style="padding:4px 0;cursor:pointer;font-size:var(--text-base);font-weight:var(--font-medium);
                    color:var(--text-secondary);list-style:none;display:flex;align-items:center;gap:8px;
                    user-select:none;-webkit-user-select:none;">
      📖 &nbsp;How to read this dashboard
    </summary>
    <div style="padding-top:16px;border-top:1px solid var(--border);margin-top:12px;">

      <p style="color:var(--text-primary);font-size:var(--text-base);font-weight:var(--font-semibold);margin:0 0 16px;">
        sql-guard monitors every question your text-to-SQL agent answers and scores it for trustworthiness.
      </p>

      <div class="dm-section-label" style="margin-bottom:8px;">Overview row</div>
      <table class="dm-table" style="margin-bottom:20px;">
        <thead><tr>
          <th>Metric</th><th>What it means</th><th>When to act</th>
        </tr></thead>
        <tbody>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Total Questions</td><td>How many questions were asked in the time window</td><td style="color:var(--text-tertiary);">—</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Pass Rate</td><td>% of answers with trust score ≥ {th}</td><td style="color:var(--text-tertiary);">Below 80% is a concern</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Avg Trust Score</td><td>Mean trust score across all answers</td><td style="color:var(--text-tertiary);">Below 0.75 warrants investigation</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Latency P50</td><td>Typical response time</td><td style="color:var(--text-tertiary);">Depends on your SLA</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Latency P95</td><td>Worst-case response time (95% faster)</td><td style="color:var(--text-tertiary);">High P95 = occasional freezes</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Total Tokens</td><td>LLM token consumption in the period</td><td style="color:var(--text-tertiary);">Use for cost estimation</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Uptime</td><td>% of time buckets with at least one query</td><td style="color:var(--text-tertiary);">Low = agent idle or down</td></tr>
        </tbody>
      </table>

      <div class="dm-section-label" style="margin-bottom:8px;">Charts</div>
      <table class="dm-table" style="margin-bottom:20px;">
        <thead><tr><th>Chart</th><th>How to read it</th></tr></thead>
        <tbody>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Query Volume</td><td>Green = passed (trust ≥ {th}), red = failed. Rising red bars = agent degrading.</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Trust Score Trend</td><td>Should stay flat and high. A dip means recent answers are less reliable.</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Latency P50/P95</td><td>P50 = typical; P95 = worst case. Widening gap = occasional slow outliers.</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Token Usage</td><td>Spikes = unusually complex questions. Blank = backend doesn't report tokens.</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Flag Frequency</td><td><code>sql_inconsistent</code> = agent disagrees with itself · <code>unknown_table</code> = hallucinated table name</td></tr>
          <tr><td style="color:var(--text-primary);font-weight:var(--font-semibold);">Trust Distribution</td><td>Ideal: most answers in the 0.8–1.0 band. Spread into lower bands = agent needs tuning.</td></tr>
        </tbody>
      </table>

      <div class="dm-section-label" style="margin-bottom:8px;">Activity row</div>
      <ul style="color:var(--text-secondary);font-size:var(--text-sm);padding-left:16px;margin:0 0 16px;line-height:1.8;">
        <li><span style="color:var(--text-primary);font-weight:var(--font-semibold);">Active Periods</span> — time buckets where at least one question was asked</li>
        <li><span style="color:var(--text-primary);font-weight:var(--font-semibold);">Idle Periods</span> — time buckets with no activity</li>
        <li><span style="color:var(--text-primary);font-weight:var(--font-semibold);">Busy Periods</span> — time buckets with above-average query volume</li>
      </ul>

      <div class="dm-section-label" style="margin-bottom:6px;">Low Trust Questions table</div>
      <p style="color:var(--text-secondary);font-size:var(--text-sm);margin:0;">Click any row to see the full SQL, result, per-check scores, and flags for that specific question.</p>
    </div>
  </details>
</div>
""", unsafe_allow_html=True)


# ── KPI row ───────────────────────────────────────────────────────────────────

def render_kpi_row(store, since: str, threshold: float, backend: str | None) -> None:
    stats = store.get_summary_stats(since, threshold=threshold, backend=backend)
    activity = store.get_activity_stats(since, backend=backend)
    perf = store.get_latency_percentiles(since, backend=backend)

    cols = st.columns(7)
    cols[0].metric("Total Questions", f"{stats['total']:,}", help="Questions asked in the selected time window")
    cols[1].metric("Pass Rate", _fmt_pct(stats["pass_rate"]), help=f"Answers with trust score ≥ {threshold:.0%}. Adjust threshold in the sidebar.")
    cols[2].metric("Avg Trust Score", _fmt_pct(stats["avg_trust"]), help="Mean trust score across all checks")
    cols[3].metric("Latency P50", _fmt_ms(perf["p50"]), help="Half of answers arrived faster than this")
    cols[4].metric("Latency P95", _fmt_ms(perf["p95"]), help="95% of answers arrived faster than this")
    cols[5].metric("Total Tokens", f"{stats['total_tokens']:,}" if stats["total_tokens"] else "—", help="Token count reported by the backend")
    cols[6].metric("Uptime", _fmt_pct(activity["uptime_pct"]), help=f"{activity['active_buckets']} of {activity['total_buckets']} time buckets had queries")


# ── Volume + Trust trend ──────────────────────────────────────────────────────

def render_volume_and_trust(store, since: str, threshold: float, backend: str | None) -> None:
    import altair as alt
    import pandas as pd

    col1, col2 = st.columns(2)

    with col1:
        _section_label("Query Volume")
        rows = store.get_volume_trend(since, threshold=threshold, backend=backend)
        if not rows:
            st.info("No data in this window.")
        else:
            df = pd.DataFrame(rows)
            df["bucket"] = pd.to_datetime(df["bucket"])
            df_long = df.melt("bucket", var_name="status", value_name="count")
            chart = alt.Chart(df_long).mark_bar(opacity=0.85).encode(
                x=alt.X("bucket:T", title=None),
                y=alt.Y("count:Q", title=None, stack=True),
                color=alt.Color("status:N",
                    scale=alt.Scale(domain=["passed", "failed"], range=["#22C55E", "#EF4444"]),
                    legend=None,
                ),
                order=alt.Order("status:N", sort="descending"),
            )
            st.altair_chart(_dark(chart), use_container_width=True)
            st.caption(f"Green = trust ≥ {threshold:.0%}  ·  Red = trust < {threshold:.0%}")

    with col2:
        _section_label("Trust Score Trend")
        rows = store.get_trust_trend(since, backend=backend)
        if not rows:
            st.info("No data in this window.")
        else:
            df = pd.DataFrame(rows)
            df["bucket"] = pd.to_datetime(df["bucket"])
            chart = alt.Chart(df).mark_line(
                color="#00C9B1", strokeWidth=2, interpolate="monotone",
            ).encode(
                x=alt.X("bucket:T", title=None),
                y=alt.Y("avg_trust:Q", title=None, scale=alt.Scale(domain=[0, 1])),
            )
            st.altair_chart(_dark(chart), use_container_width=True)
            st.caption("Average trust score per time bucket. Flat and high is good.")


# ── Latency + Tokens ──────────────────────────────────────────────────────────

def render_latency_and_tokens(store, since: str, backend: str | None) -> None:
    import altair as alt
    import pandas as pd

    col1, col2 = st.columns(2)

    with col1:
        _section_label("Latency over Time (ms)")
        rows = store.get_latency_trend(since, backend=backend)
        if not rows:
            st.info("No data in this window.")
        else:
            df = pd.DataFrame(rows)
            df["bucket"] = pd.to_datetime(df["bucket"])
            df_long = df.melt("bucket", var_name="percentile", value_name="latency_ms")
            chart = alt.Chart(df_long).mark_line(strokeWidth=2, interpolate="monotone").encode(
                x=alt.X("bucket:T", title=None),
                y=alt.Y("latency_ms:Q", title=None),
                color=alt.Color("percentile:N",
                    scale=alt.Scale(domain=["p50", "p95"], range=["#00C9B1", "#7850DC"]),
                    legend=alt.Legend(orient="top-right"),
                ),
            )
            st.altair_chart(_dark(chart), use_container_width=True)
            st.caption("P50 = typical speed · P95 = worst 5%. A widening gap means occasional slow outliers.")

    with col2:
        _section_label("Token Usage over Time")
        rows = store.get_token_trend(since, backend=backend)
        if not rows or all(r["tokens"] == 0 for r in rows):
            st.info("No token data — your backend doesn't report token counts.")
        else:
            df = pd.DataFrame(rows)
            df["bucket"] = pd.to_datetime(df["bucket"])
            chart = alt.Chart(df).mark_bar(color="#00C9B1", opacity=0.75).encode(
                x=alt.X("bucket:T", title=None),
                y=alt.Y("tokens:Q", title=None),
            )
            st.altair_chart(_dark(chart), use_container_width=True)
            st.caption("Total tokens consumed per period. Spikes = unusually complex questions.")


# ── Flags + Distribution ──────────────────────────────────────────────────────

def render_flags_and_distribution(store, since: str, backend: str | None) -> None:
    import altair as alt
    import pandas as pd

    col1, col2 = st.columns(2)

    with col1:
        _section_label("Flag Frequency")
        flags = store.get_flag_counts(since, backend=backend)
        if not flags:
            st.success("No flags raised in this period — agent output looks clean.")
        else:
            df = pd.DataFrame(flags)
            chart = alt.Chart(df).mark_bar(color="#00C9B1", opacity=0.75).encode(
                y=alt.Y("flag:N", title=None, sort="-x"),
                x=alt.X("count:Q", title=None),
            )
            st.altair_chart(_dark(chart), use_container_width=True)
            st.caption("Flags are raised when a check detects a problem. Longer bar = more frequent issue.")

    with col2:
        _section_label("Trust Score Distribution")
        hist = store.get_trust_histogram(since, backend=backend)
        if not hist:
            st.info("No data in this window.")
        else:
            df = pd.DataFrame(hist)
            chart = alt.Chart(df).mark_bar(color="#00C9B1", opacity=0.75).encode(
                x=alt.X("bucket:N", title=None),
                y=alt.Y("count:Q", title=None),
            )
            st.altair_chart(_dark(chart), use_container_width=True)
            st.caption("Ideal: most answers in the 0.8–1.0 band. Spread into lower bands = agent needs tuning.")


# ── Activity row ──────────────────────────────────────────────────────────────

def render_activity_row(store, since: str, threshold: float, backend: str | None) -> None:
    activity = store.get_activity_stats(since, backend=backend)
    stats = store.get_summary_stats(since, threshold=threshold, backend=backend)

    cols = st.columns(4)
    cols[0].metric("Active Periods", f"{activity['active_buckets']}", help="Time buckets with at least one query")
    cols[1].metric("Idle Periods", f"{activity['idle_buckets']}", help="Time buckets with no queries")
    cols[2].metric("Busy Periods", f"{activity['busy_buckets']}", help="Time buckets with above-average query volume")
    cols[3].metric("Failed Queries", f"{stats['failed']:,}", help=f"Queries where trust score < {threshold:.0%}")


# ── Low trust table ───────────────────────────────────────────────────────────

def render_low_trust_table(
    store, since: str, threshold: float, backend: str | None, n: int
) -> None:
    import pandas as pd

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;padding-bottom:8px;">'
        f'<div style="width:2px;height:12px;background:linear-gradient(180deg,var(--danger),var(--warning));border-radius:var(--radius-full);flex-shrink:0;"></div>'
        f'<span class="dm-section-label">Low Trust Questions</span>'
        f'<span style="font-size:var(--text-xs);font-weight:var(--font-semibold);color:var(--text-tertiary);text-transform:none;letter-spacing:0;">'
        f'&nbsp;·&nbsp;trust &lt; {threshold:.0%}</span></div>',
        unsafe_allow_html=True,
    )
    rows = store.get_top_offenders(n=n, since=since, threshold=threshold, backend=backend)
    if not rows:
        st.success(f"No questions below {threshold:.0%} trust in this window.")
        return

    df = pd.DataFrame(rows)
    df["question"] = df["question"].str[:100]
    df["trust_score"] = df["trust_score"].round(3)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")

    event = st.dataframe(
        df[["timestamp", "question", "trust_score", "flags", "backend_name"]],
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "trust_score": st.column_config.ProgressColumn("Trust Score", min_value=0, max_value=1, format="%.3f"),
            "question": st.column_config.TextColumn("Question", width="large"),
            "flags": st.column_config.TextColumn("Flags"),
        },
    )
    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        st.session_state["selected_event_id"] = rows[idx]["id"]
    st.caption("Click a row to inspect the full SQL, result, and per-check scores below.")


# ── Drill-through ─────────────────────────────────────────────────────────────

def render_drill_through(store, event_id: str) -> None:
    import altair as alt
    import pandas as pd

    event = store.get_event(event_id)
    if not event:
        return

    st.divider()
    st.markdown(
        '<div style="font-size:var(--text-lg);font-weight:var(--font-extrabold);letter-spacing:-0.02em;color:var(--text-primary);margin-bottom:16px;">Event Detail</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Question:** {event['question']}")
        st.code(event.get("sql") or "—", language="sql")
        result = event.get("result")
        if result:
            try:
                st.json(json.loads(result))
            except Exception:
                st.text(result)

    with col2:
        score = event.get("trust_score") or 0
        color = _trust_color(score)
        st.markdown(f"**Trust score:** :{color}[{score:.2%}]")
        st.progress(float(score))
        st.caption("1.0 = fully trusted · 0.0 = untrustworthy")

        flags = event.get("flags")
        if flags:
            try:
                flag_list = json.loads(flags)
                if flag_list:
                    st.warning("Flags: " + ", ".join(flag_list))
                else:
                    st.success("No flags raised")
            except Exception:
                pass

        check_scores_raw = event.get("check_scores")
        if check_scores_raw:
            try:
                scores = json.loads(check_scores_raw)
                df = pd.DataFrame(list(scores.items()), columns=["check", "score"])
                _section_label("Per-check scores")
                chart = alt.Chart(df).mark_bar(color="#00C9B1", opacity=0.8).encode(
                    x=alt.X("check:N", title=None),
                    y=alt.Y("score:Q", title=None, scale=alt.Scale(domain=[0, 1])),
                )
                st.altair_chart(_dark(chart, height=160), use_container_width=True)
                st.caption("Each check contributes to the overall trust score with different weights.")
            except Exception:
                pass

    if st.button("✕ Close detail"):
        del st.session_state["selected_event_id"]
        st.rerun()


# ── Backends tab ──────────────────────────────────────────────────────────────

def render_backends_tab(config_path) -> None:
    from sql_guard.config import BackendConfig, load_config, save_config

    cfg = load_config(config_path)
    server_url = os.environ.get("SQL_GUARD_SERVER", "http://localhost:8080")

    _backends_section(
        "Connected Backends",
        "A backend is any text-to-SQL tool sql-guard tracks. "
        "Add one here, then either point your app at the proxy URL or POST to /track.",
    )

    if not cfg.backends:
        st.info("No backends configured yet. Add one below.")
    else:
        for b in cfg.backends:
            with st.expander(f"**{b.name}** — `{b.url}`", expanded=False):
                col1, col2 = st.columns([3, 1])
                with col1:
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
                with col2:
                    st.markdown("**Integration options:**")
                    st.code(f'POST {server_url}/proxy/{b.name}', language="bash")
                    st.caption("or push API:")
                    st.code(
                        f'httpx.post("{server_url}/track",\n'
                        f'  json={{"question": ..., "sql": ...,\n'
                        f'         "result": ...,\n'
                        f'         "backend_name": "{b.name}"}})',
                        language="python",
                    )
                    if st.button(f"Delete {b.name}", key=f"del_{b.name}", type="secondary"):
                        cfg.backends = [x for x in cfg.backends if x.name != b.name]
                        save_config(cfg, config_path)
                        st.rerun()

    st.divider()
    _backends_section("Add Backend")

    with st.form("add_backend"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", placeholder="my-vanna", help="Unique identifier for this backend")
            url = st.text_input("Endpoint URL", placeholder="https://your-tool.com/ask", help="Where sql-guard forwards proxy requests")
            method = st.selectbox("HTTP Method", ["POST", "GET"])
            auth = st.text_input("Auth header value", placeholder="Bearer sk-...", type="password", help="Sent as Authorization header. Leave blank if not needed.")
        with col2:
            question_field = st.text_input("Question field name", value="question", help="Key in the request body that holds the user's question")
            sql_field = st.text_input("SQL response field", value="sql", help="Key in the response body that holds the generated SQL")
            result_field = st.text_input("Result response field", value="result", help="Key in the response body that holds the query result")
            st.caption("Not sure about field names? Add the backend then use the Test button.")

        submitted = st.form_submit_button("Add backend", type="primary")
        if submitted:
            if not name or not url:
                st.error("Name and URL are required.")
            else:
                new_backend = BackendConfig(
                    name=name, url=url, method=method,
                    auth_header=auth or None,
                    question_field=question_field,
                    sql_field=sql_field,
                    result_field=result_field,
                )
                cfg.backends = [b for b in cfg.backends if b.name != name] + [new_backend]
                save_config(cfg, config_path)
                st.success(f"Backend '{name}' saved. Point your app at: `{server_url}/proxy/{name}`")
                st.rerun()

    st.divider()
    _backends_section(
        "Test a Backend",
        "Sends a test request to the backend's URL and shows the raw response. Use this to verify your field mapping.",
    )

    backend_names = [b.name for b in cfg.backends]
    if not backend_names:
        st.info("Add a backend above to test it.")
    else:
        test_name = st.selectbox("Backend to test", backend_names, key="test_select")
        test_question = st.text_input("Test question", value="What is the total revenue?", key="test_q")
        if st.button("Run test request"):
            try:
                import httpx as _httpx
                resp = _httpx.post(
                    f"{server_url}/api/backends/{test_name}/test",
                    json={cfg.backends[backend_names.index(test_name)].question_field: test_question},
                    timeout=15,
                )
                result = resp.json()
                if result.get("status") == "ok":
                    st.success(f"Connected in {result['latency_ms']} ms")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Raw response:**")
                        st.json(result["response"])
                    with col2:
                        st.markdown("**Detected fields:**")
                        st.json(result["detected"])
                else:
                    st.error(f"Error: {result.get('detail', result)}")
            except Exception as e:
                st.error(f"Could not reach sql-guard server at {server_url}. Is it running? (`sql-guard serve`)\n\n{e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.markdown("""
    <div class="dm-aurora">
      <div class="dm-aurora-blob dm-aurora-blob-1"></div>
      <div class="dm-aurora-blob dm-aurora-blob-2"></div>
      <div class="dm-aurora-blob dm-aurora-blob-3"></div>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;padding:4px 0 20px;margin-bottom:4px;
             border-bottom:1px solid var(--border);">
          <div class="dm-sidebar-logo" style="width:34px;height:34px;margin-bottom:0;flex-shrink:0;">SG</div>
          <div style="font-size:var(--text-lg);font-weight:var(--font-black);letter-spacing:-0.02em;
               background:var(--grad-text);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
            sql-guard
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<p class="dm-section-label" style="margin:12px 0 6px;">Filters</p>',
            unsafe_allow_html=True,
        )
        since = st.selectbox(
            "Time window", ["1h", "24h", "7d", "30d"], index=1,
            help="All panels update to this time range", label_visibility="collapsed",
        )

        try:
            store_for_backends = _load_store()
            backends = ["All"] + store_for_backends.get_backends()
        except Exception:
            backends = ["All"]
        backend_choice = st.selectbox("Backend", backends, help="Filter all panels to one backend")
        backend = None if backend_choice == "All" else backend_choice

        st.markdown(
            '<p class="dm-section-label" style="margin:20px 0 6px;">Thresholds</p>',
            unsafe_allow_html=True,
        )
        threshold = st.slider(
            "Pass threshold", min_value=0.50, max_value=0.95, value=0.70, step=0.05,
            help="Score at or above this = PASS. Adjusts KPIs, volume chart, and the offenders table.",
            format="%.2f",
        )
        n_offenders = st.slider(
            "Offenders to show", min_value=5, max_value=50, value=20, step=5,
            help="How many low-trust questions to show in the table",
        )

        st.divider()
        auto_refresh = st.toggle("Auto-refresh (30s)", value=False)

    config_path_env = os.environ.get("SQL_GUARD_CONFIG")
    config_path = Path(config_path_env) if config_path_env else None

    tab_overview, tab_backends = st.tabs(["📊 Overview", "🔌 Backends"])

    with tab_backends:
        render_backends_tab(config_path)

    with tab_overview:
        st.markdown(f"""
        <div style="display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:24px;">
          <div>
            <div class="dm-page-title">
              Trust
              <span style="background:var(--grad-text);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
                Monitor
              </span>
            </div>
            <div class="dm-page-subtitle">
              sql-guard · real-time text-to-SQL reliability · window: {since}
            </div>
          </div>
          <span class="dm-badge dm-badge-pulse">
            <span class="dm-badge-pulse-dot"></span>
            MONITORING
          </span>
        </div>
        """, unsafe_allow_html=True)

        try:
            store = _load_store()
        except Exception as e:
            st.error(f"Could not connect to event store: {e}")
            return

        render_guide(threshold)
        render_kpi_row(store, since, threshold, backend)

        st.divider()
        render_volume_and_trust(store, since, threshold, backend)

        st.divider()
        render_latency_and_tokens(store, since, backend)

        st.divider()
        render_flags_and_distribution(store, since, backend)

        st.divider()
        _section_header("Activity")
        render_activity_row(store, since, threshold, backend)

        st.divider()
        render_low_trust_table(store, since, threshold, backend, n_offenders)

        if "selected_event_id" in st.session_state:
            render_drill_through(store, st.session_state["selected_event_id"])

    if auto_refresh:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
