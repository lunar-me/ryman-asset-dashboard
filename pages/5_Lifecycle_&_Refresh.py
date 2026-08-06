"""
Page 5: Lifecycle & Refresh Planning.

End-to-end lifecycle visibility and technology refresh programme support.
"""
import pandas as pd
import streamlit as st

from utils.data_loader import load_data
from utils.metrics import add_derived_columns
from utils.filters import render_sidebar_filters
from utils.constants import DISCLAIMER
from utils.formatting import format_dataframe_for_display, format_age_years
from utils import charts

st.set_page_config(page_title="Lifecycle & Refresh", page_icon="🔄", layout="wide")

# ---------------------------------------------------------------------------
# Load data + filters
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
st.title("🔄 Lifecycle & Refresh Planning")
st.warning(DISCLAIMER)
st.caption(
    "End-to-end lifecycle visibility — age, stage, refresh timing, and "
    "disposal recovery — to support refresh programmes and budgeting."
)

with st.expander("ℹ️ What this page is for"):
    st.caption(
        "Supports the Asset Management Analyst responsibilities of lifecycle "
        "management, refresh programme planning, and budgeting conversations "
        "with Technology and Finance."
    )

if len(filtered_df) == 0:
    st.warning("No data matches the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
avg_age = filtered_df["asset_age_years"].mean()
pct_past_life = filtered_df["is_past_useful_life"].mean() * 100
refresh_volume = int(filtered_df["is_refresh_due_soon"].sum())

# Planned refresh cost (avg recent purchase cost × forecast volume)
recent = filtered_df[pd.to_datetime(filtered_df["purchase_date"], errors="coerce") >= pd.Timestamp.now() - pd.DateOffset(years=2)]
avg_recent_cost = recent["purchase_cost_nzd"].mean() if len(recent) > 0 else filtered_df["purchase_cost_nzd"].mean()
est_refresh_cost = refresh_volume * avg_recent_cost

# Residual on retired
retired = filtered_df[filtered_df["lifecycle_stage"].astype(str).isin(["Retired", "Disposed"])]
residual_value = retired["residual_value_nzd"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Average Age", format_age_years(avg_age))
c2.metric("% Past Useful Life", f"{pct_past_life:.1f}%")
c3.metric("Refresh Due (12 mo)", f"{refresh_volume:,}")
c4.metric("Est. Refresh Cost", f"${est_refresh_cost:,.0f}")

st.divider()

# ---------------------------------------------------------------------------
# Lifecycle distribution
# ---------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    lifecycle_counts = (
        filtered_df.groupby("lifecycle_stage")
        .agg(count=("sys_id", "count"), cost=("purchase_cost_nzd", "sum"))
        .reset_index()
    )
    st.plotly_chart(
        charts.funnel_stages(lifecycle_counts, "lifecycle_stage", "count", "Lifecycle Stage Distribution"),
        width='stretch',
    )

with right:
    lifecycle_cost = (
        filtered_df.groupby("lifecycle_stage")["purchase_cost_nzd"]
        .sum()
        .reset_index()
        .sort_values("purchase_cost_nzd", ascending=False)
    )
    st.plotly_chart(
        charts.horizontal_bar(
            lifecycle_cost,
            "purchase_cost_nzd",
            "lifecycle_stage",
            "Cost by Lifecycle Stage (NZD)",
            color=charts.COLOR_PRIMARY,
        ),
        width='stretch',
    )

st.divider()

# ---------------------------------------------------------------------------
# Age histogram by asset type
# ---------------------------------------------------------------------------
st.subheader("Asset Age Distribution by Type")
age_by_type = filtered_df[filtered_df["asset_age_years"].notna()]
if len(age_by_type) > 0:
    fig = charts.histogram(
        age_by_type,
        "asset_age_years",
        "Asset Age (Years)",
        nbins=25,
        height=350,
    )
    st.plotly_chart(fig, width='stretch')

st.divider()

# ---------------------------------------------------------------------------
# Refresh forecast
# ---------------------------------------------------------------------------
st.subheader("Refresh Forecast (Next 5 Years)")

current_year = pd.Timestamp.now().year
refresh_forecast = (
    filtered_df.groupby("refresh_year")
    .agg(count=("sys_id", "count"), est_cost=("purchase_cost_nzd", "sum"))
    .reset_index()
    .sort_values("refresh_year")
)
refresh_forecast = refresh_forecast[
    (refresh_forecast["refresh_year"] >= current_year)
    & (refresh_forecast["refresh_year"] <= current_year + 5)
]

if len(refresh_forecast) > 0:
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            charts.vertical_bar(
                refresh_forecast, "refresh_year", "count", "Assets Due for Refresh",
                color=charts.COLOR_WARNING,
            ),
            width='stretch',
        )

    with col2:
        st.plotly_chart(
            charts.vertical_bar(
                refresh_forecast, "refresh_year", "est_cost", "Estimated Refresh Cost (NZD)",
                color=charts.COLOR_PRIMARY,
            ),
            width='stretch',
        )

    # Detailed table
    st.markdown("**Refresh Forecast Detail**")
    detail = refresh_forecast.copy()
    detail["est_cost"] = detail["est_cost"].round(0)
    st.dataframe(format_dataframe_for_display(detail), hide_index=True, width='stretch')

st.divider()

# ---------------------------------------------------------------------------
# Warranty vs age
# ---------------------------------------------------------------------------
st.subheader("Warranty Status vs Asset Age")
warranty_summary = (
    filtered_df.groupby("warranty_status")
    .agg(count=("sys_id", "count"), avg_age=("asset_age_years", "mean"))
    .reset_index()
)
if len(warranty_summary) > 0:
    st.dataframe(format_dataframe_for_display(warranty_summary), hide_index=True, width='stretch')

st.divider()

# ---------------------------------------------------------------------------
# Disposal summary
# ---------------------------------------------------------------------------
st.subheader("Disposal Summary")

if len(retired) > 0:
    col1, col2 = st.columns(2)

    with col1:
        disposal_by_method = (
            retired.groupby("disposal_method")
            .agg(count=("sys_id", "count"), recovered=("residual_value_nzd", "sum"))
            .reset_index()
            .sort_values("count", ascending=False)
        )
        st.plotly_chart(
            charts.horizontal_bar(
                disposal_by_method,
                "count",
                "disposal_method",
                "Disposals by Method",
                color=charts.COLOR_NEUTRAL,
            ),
            width='stretch',
        )

    with col2:
        total_original = retired["purchase_cost_nzd"].sum()
        total_residual = retired["residual_value_nzd"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Original Cost (Retired)", f"${total_original:,.0f}")
        c2.metric("Residual Value", f"${total_residual:,.0f}")
        st.caption(f"Recovery rate: {total_residual / total_original * 100:.1f}%" if total_original > 0 else "")

    st.markdown(f"**Retired / Disposed Asset List ({len(retired):,})**")
    cols = [c for c in ["asset_tag", "asset_type", "model", "disposal_date", "disposal_method", "purchase_cost_nzd", "residual_value_nzd", "location"] if c in retired.columns]
    st.dataframe(format_dataframe_for_display(retired[cols]), hide_index=True, width='stretch')
else:
    st.info("No retired/disposed assets in the current filter view.")

st.divider()

# ---------------------------------------------------------------------------
# Devices already in Refresh Due stage
# ---------------------------------------------------------------------------
refresh_due_df = filtered_df[filtered_df["is_refresh_due_soon"]]
if len(refresh_due_df) > 0:
    st.subheader(f"Devices Due for Refresh ({len(refresh_due_df):,})")
    cols = [c for c in ["asset_tag", "asset_type", "model", "location", "assigned_to", "purchase_date", "asset_age_years", "planned_refresh_date", "remaining_life_years", "purchase_cost_nzd"] if c in refresh_due_df.columns]
    st.dataframe(format_dataframe_for_display(refresh_due_df[cols]), hide_index=True, width='stretch')