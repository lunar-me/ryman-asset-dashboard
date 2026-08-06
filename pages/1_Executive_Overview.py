"""
Page 1: Executive Overview.

30-second health check for Technology / Finance stakeholders or a hiring manager.
"""
import pandas as pd
import streamlit as st

from utils.data_loader import load_data
from utils.metrics import add_derived_columns, compute_kpis
from utils.filters import render_sidebar_filters
from utils import charts

st.set_page_config(page_title="Executive Overview", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Load data + filters (shared across pages)
# ---------------------------------------------------------------------------
force_refresh = st.session_state.pop("force_refresh", False)
df, source, loaded_at = load_data(force_refresh=force_refresh)
st.session_state.data_source = source
st.session_state.last_loaded = loaded_at

df = add_derived_columns(df)
filtered_df, util_threshold, stale_threshold = render_sidebar_filters(df)
filtered_df = add_derived_columns(filtered_df, util_threshold, stale_threshold)

# ---------------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------------
st.title("📊 Executive Overview")
st.caption(
    "A 30-second health check on the technology estate — for Technology, "
    "Finance, and village stakeholders."
)

with st.expander("ℹ️ What this page is for"):
    st.caption(
        "Supports the Asset Management Analyst role by providing reporting "
        "and decision-support for stakeholders. KPIs and charts here should "
        "match the detail pages for the same filters."
    )

if len(filtered_df) == 0:
    st.warning("No data matches the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
kpis = compute_kpis(filtered_df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Assets", f"{kpis['total_assets']:,}")
c2.metric("Total Purchase Cost", f"${kpis['total_cost']:,.0f}")
c3.metric("Missing or Unassigned", f"{kpis['pct_missing_or_unassigned']}%")
c4.metric("Non-Compliant", f"{kpis['pct_non_compliant']}%")

c5, c6, c7 = st.columns(3)
c5.metric("Under-Utilised", f"{kpis['pct_underutilised']}%")
c6.metric("Refresh Due (12 mo)", f"{kpis['refresh_next_12m']:,}")
c7.metric("Reclaim Opportunity", f"${kpis['reclaim_opportunity']:,.0f}")

st.divider()

# ---------------------------------------------------------------------------
# Charts row 1: Asset count & cost by type, lifecycle distribution
# ---------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    type_counts = (
        filtered_df.groupby("asset_type")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    st.plotly_chart(
        charts.horizontal_bar(type_counts, "count", "asset_type", "Asset Count by Type"),
        use_container_width=True,
    )

with right:
    type_cost = (
        filtered_df.groupby("asset_type")["purchase_cost_nzd"]
        .sum()
        .reset_index()
        .sort_values("purchase_cost_nzd", ascending=False)
    )
    st.plotly_chart(
        charts.horizontal_bar(
            type_cost,
            "purchase_cost_nzd",
            "asset_type",
            "Total Cost by Type (NZD)",
            color=charts.COLOR_PRIMARY,
        ),
        use_container_width=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Charts row 2: Lifecycle funnel + top problem locations
# ---------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    lifecycle_counts = (
        filtered_df.groupby("lifecycle_stage")
        .size()
        .reset_index(name="count")
    )
    st.plotly_chart(
        charts.funnel_stages(lifecycle_counts, "lifecycle_stage", "count", "Lifecycle Stage Distribution"),
        use_container_width=True,
    )

with right:
    # Top 10 locations by problem rate (missing + unassigned + non-compliant)
    loc_problem = (
        filtered_df.groupby("location")
        .agg(
            total=("sys_id", "count"),
            problems=(
                "is_missing",
                "sum",
            ),
        )
        .reset_index()
    )
    if "is_unassigned" in filtered_df.columns:
        loc_unassigned = (
            filtered_df.groupby("location")["is_unassigned"].sum().reset_index()
        )
        loc_problem = loc_problem.merge(loc_unassigned, on="location")
    else:
        loc_problem["is_unassigned"] = 0
    if "is_non_compliant" in filtered_df.columns:
        loc_noncomp = (
            filtered_df.groupby("location")["is_non_compliant"].sum().reset_index()
        )
        loc_problem = loc_problem.merge(loc_noncomp, on="location")
    else:
        loc_problem["is_non_compliant"] = 0

    loc_problem["problem_count"] = (
        loc_problem["problems"] + loc_problem["is_unassigned"] + loc_problem["is_non_compliant"]
    )
    loc_problem["problem_rate"] = (
        loc_problem["problem_count"] / loc_problem["total"] * 100
    ).round(1)
    loc_problem = loc_problem.sort_values("problem_count", ascending=False).head(10)

    st.plotly_chart(
        charts.horizontal_bar(
            loc_problem,
            "problem_count",
            "location",
            "Top 10 Locations by Problem Count",
            color=charts.COLOR_WARNING,
        ),
        use_container_width=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Purchase trend
# ---------------------------------------------------------------------------
purchase_trend = (
    filtered_df.assign(year=pd.to_datetime(filtered_df["purchase_date"], errors="coerce").dt.year)
    .groupby("year")
    .size()
    .reset_index(name="count")
    .dropna()
)
if len(purchase_trend) > 0:
    st.plotly_chart(
        charts.line_trend(purchase_trend, "year", "count", "Assets Purchased by Year"),
        use_container_width=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Narrative / insight box
# ---------------------------------------------------------------------------
st.subheader("💡 Key Insights")

insights = []

if kpis["pct_missing_or_unassigned"] > 0:
    insights.append(
        f"**{kpis['pct_missing_or_unassigned']}%** of assets are missing or unassigned "
        f"({int(kpis['pct_missing_or_unassigned'] / 100 * kpis['total_assets'])} devices). "
        f"Estimated reclaim opportunity ≈ **${kpis['reclaim_opportunity']:,.0f}**."
    )

if kpis["pct_non_compliant"] > 0:
    insights.append(
        f"**{kpis['pct_non_compliant']}%** of assets are non-compliant — "
        "see the Compliance & Risk page for details by location and asset type."
    )

if kpis["refresh_next_12m"] > 0:
    insights.append(
        f"**{kpis['refresh_next_12m']:,}** assets are due for refresh in the next 12 months. "
        "See Lifecycle & Refresh Planning for the forecast."
    )

if kpis["avg_age_years"] > 0:
    insights.append(
        f"The average asset age is **{kpis['avg_age_years']} years** across the "
        f"{kpis['total_assets']:,} devices in this view."
    )

if not insights:
    insights.append("No major issues detected in the current filter view. 🎉")

for ins in insights:
    st.markdown(f"- {ins}")

st.caption(
    "Insights are rule-based estimates for demonstration purposes. "
    "Opportunity values use a transparent heuristic — see page descriptions for details."
)