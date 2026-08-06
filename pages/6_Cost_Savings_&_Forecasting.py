"""
Page 6: Cost Savings & Forecasting.

Turn asset data into financial insight for Finance and Technology leadership.
"""
import pandas as pd
import streamlit as st

from utils.data_loader import load_data
from utils.metrics import add_derived_columns
from utils.filters import render_sidebar_filters
from utils.constants import DISCLAIMER
from utils.formatting import format_dataframe_for_display
from utils import charts

st.set_page_config(page_title="Cost Savings & Forecasting", page_icon="💰", layout="wide")

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
st.title("💰 Cost Savings & Forecasting")
st.warning(DISCLAIMER)
st.caption(
    "Turn asset data into financial insight — spend analysis, reclaim "
    "scenarios, model standardisation, and refresh cost forecasting."
)

with st.expander("ℹ️ What this page is for"):
    st.caption(
        "Supports the Asset Management Analyst responsibilities of cost "
        "analysis, waste reduction, budgeting, and forecasting for Finance "
        "and Technology leadership."
    )

if len(filtered_df) == 0:
    st.warning("No data matches the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Spend over time
# ---------------------------------------------------------------------------
st.subheader("Historical Spend")

spend_by_year = (
    filtered_df.assign(year=pd.to_datetime(filtered_df["purchase_date"], errors="coerce").dt.year)
    .groupby("year")["purchase_cost_nzd"]
    .sum()
    .reset_index()
    .dropna()
)

if len(spend_by_year) > 0:
    st.plotly_chart(
        charts.line_trend(spend_by_year, "year", "purchase_cost_nzd", "Spend by Year (NZD)"),
        width='stretch',
    )

st.divider()

# ---------------------------------------------------------------------------
# Cost of problem assets
# ---------------------------------------------------------------------------
st.subheader("Cost of Problem Assets")

problem_df = filtered_df[
    filtered_df["is_missing"] | filtered_df["is_unassigned"] | filtered_df["is_underutilised"]
]
problem_summary = pd.DataFrame(
    {
        "Category": [
            "Missing",
            "Unassigned",
            "Under-utilised",
            "Reclaim candidates",
        ],
        "Count": [
            int(filtered_df["is_missing"].sum()),
            int(filtered_df["is_unassigned"].sum()),
            int(filtered_df["is_underutilised"].sum()),
            int(filtered_df["is_reclaim_candidate"].sum()),
        ],
        "Cost (NZD)": [
            filtered_df[filtered_df["is_missing"]]["purchase_cost_nzd"].sum(),
            filtered_df[filtered_df["is_unassigned"]]["purchase_cost_nzd"].sum(),
            filtered_df[filtered_df["is_underutilised"]]["purchase_cost_nzd"].sum(),
            filtered_df[filtered_df["is_reclaim_candidate"]]["purchase_cost_nzd"].sum(),
        ],
        "Opportunity (NZD)": [
            filtered_df[filtered_df["is_missing"]]["opportunity_value_nzd"].sum(),
            filtered_df[filtered_df["is_unassigned"]]["opportunity_value_nzd"].sum(),
            filtered_df[filtered_df["is_underutilised"]]["opportunity_value_nzd"].sum(),
            filtered_df[filtered_df["is_reclaim_candidate"]]["opportunity_value_nzd"].sum(),
        ],
    }
)

st.dataframe(format_dataframe_for_display(problem_summary.round(0)),
    hide_index=True,
    width='stretch',
)

st.divider()

# ---------------------------------------------------------------------------
# Savings scenarios
# ---------------------------------------------------------------------------
st.subheader("Reclaim / Savings Scenarios")

reclaim_cost = filtered_df[filtered_df["is_reclaim_candidate"]]["purchase_cost_nzd"].sum()
reclaim_opp = filtered_df[filtered_df["is_reclaim_candidate"]]["opportunity_value_nzd"].sum()

scenarios = pd.DataFrame(
    {
        "Scenario": [
            "Reclaim 50% of under-utilised devices",
            "Reclaim 25% of unassigned devices",
            "Recover 100% of missing device value",
            "Total reclaim opportunity (all candidates)",
        ],
        "Estimated Savings (NZD)": [
            filtered_df[filtered_df["is_underutilised"]]["purchase_cost_nzd"].sum() * 0.50,
            filtered_df[filtered_df["is_unassigned"]]["purchase_cost_nzd"].sum() * 0.25,
            filtered_df[filtered_df["is_missing"]]["purchase_cost_nzd"].sum() * 0.40,
            reclaim_opp,
        ],
    }
)
scenarios["Estimated Savings (NZD)"] = scenarios["Estimated Savings (NZD)"].round(0)

st.dataframe(format_dataframe_for_display(scenarios), hide_index=True, width='stretch')

st.caption(
    "Heuristic: 50% of under-utilised cost, 25% of unassigned cost, 40% of "
    "missing cost — conservative estimates for demonstration."
)

st.divider()

# ---------------------------------------------------------------------------
# Model proliferation / Pareto
# ---------------------------------------------------------------------------
st.subheader("Model Standardisation (Pareto)")

model_counts = (
    filtered_df.groupby("model")
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

total_models = len(model_counts)
top3_models = model_counts.head(3)["count"].sum()
top5_models = model_counts.head(5)["count"].sum()
total_assets = len(filtered_df)

c1, c2, c3 = st.columns(3)
c1.metric("Distinct Models", f"{total_models}")
c2.metric("Top 3 Models % of Estate", f"{top3_models / total_assets * 100:.0f}%")
c3.metric("Top 5 Models % of Estate", f"{top5_models / total_assets * 100:.0f}%")

# Pareto chart
model_counts["cum_pct"] = (model_counts["count"].cumsum() / total_assets * 100).round(1)
model_counts["model_pct"] = (model_counts["count"] / total_assets * 100).round(1)
top_models = model_counts.head(15)

st.plotly_chart(
    charts.vertical_bar(
        top_models,
        "model",
        "count",
        "Top 15 Models by Asset Count",
        color=charts.COLOR_PRIMARY,
    ),
    width='stretch',
)

st.divider()

# ---------------------------------------------------------------------------
# Refresh cost forecast
# ---------------------------------------------------------------------------
st.subheader("Refresh Cost Forecast")

current_year = pd.Timestamp.now().year
recent = filtered_df[pd.to_datetime(filtered_df["purchase_date"], errors="coerce") >= pd.Timestamp.now() - pd.DateOffset(years=2)]
avg_cost_by_type = recent.groupby("asset_type")["purchase_cost_nzd"].mean()

refresh_forecast = (
    filtered_df.groupby("refresh_year")
    .agg(count=("sys_id", "count"))
    .reset_index()
)
refresh_forecast = refresh_forecast[
    (refresh_forecast["refresh_year"] >= current_year)
    & (refresh_forecast["refresh_year"] <= current_year + 5)
]

# Estimate refresh cost by type × count × avg cost
forecast_by_type_year = (
    filtered_df[filtered_df["refresh_year"].isin(refresh_forecast["refresh_year"])]
    .groupby(["refresh_year", "asset_type"])
    .size()
    .reset_index(name="count")
)
if len(forecast_by_type_year) > 0:
    forecast_by_type_year["est_unit_cost"] = forecast_by_type_year["asset_type"].map(avg_cost_by_type)
    forecast_by_type_year["est_cost"] = (
        forecast_by_type_year["count"] * forecast_by_type_year["est_unit_cost"]
    )

    total_by_year = (
        forecast_by_type_year.groupby("refresh_year")["est_cost"]
        .sum()
        .reset_index()
        .sort_values("refresh_year")
    )

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            charts.vertical_bar(
                total_by_year, "refresh_year", "est_cost", "Forecast Refresh Cost by Year (NZD)",
                color=charts.COLOR_PRIMARY,
            ),
            width='stretch',
        )

    with col2:
        st.dataframe(format_dataframe_for_display(forecast_by_type_year.round(0)),
            hide_index=True,
            width='stretch',
        )

st.divider()

# ---------------------------------------------------------------------------
# Residual value opportunity
# ---------------------------------------------------------------------------
st.subheader("Residual Value Opportunity")

retired = filtered_df[filtered_df["lifecycle_stage"].astype(str).isin(["Retired", "Disposed"])]
total_residual = retired["residual_value_nzd"].sum()
total_original = retired["purchase_cost_nzd"].sum()

if len(retired) > 0:
    c1, c2 = st.columns(2)
    c1.metric("Residual Value on Retired", f"${total_residual:,.0f}")
    c2.metric("Recovery Rate", f"{total_residual / total_original * 100:.1f}%")

    st.markdown("**Top 10 by Residual Value**")
    top_residual = retired.nlargest(10, "residual_value_nzd")
    cols = [c for c in ["asset_tag", "asset_type", "model", "disposal_method", "residual_value_nzd", "purchase_cost_nzd"] if c in top_residual.columns]
    st.dataframe(format_dataframe_for_display(top_residual[cols]), hide_index=True, width='stretch')
else:
    st.info("No retired/disposed assets in the current filter view.")

st.divider()

# ---------------------------------------------------------------------------
# Narrative box
# ---------------------------------------------------------------------------
st.subheader("💡 Monthly Pack Recommendations")

total_spend = filtered_df["purchase_cost_nzd"].sum()
reclaim_candidates = int(filtered_df["is_reclaim_candidate"].sum())

recs = []
if reclaim_candidates > 0:
    recs.append(
        f"**{reclaim_candidates:,} reclaim candidates** represent an estimated "
        f"**${reclaim_opp:,.0f}** in recoverable value. Recommend a targeted "
        "reclaim programme starting with the highest-priority locations."
    )
if total_models > 20:
    recs.append(
        f"**{total_models} distinct models** in the estate. Standardising on the "
        "top 3 laptop models could simplify procurement, support, and refresh."
    )
if len(refresh_forecast) > 0:
    peak_year = total_by_year.sort_values("est_cost", ascending=False).iloc[0]
    recs.append(
        f"Refresh cost peaks in **{int(peak_year['refresh_year'])}** at "
        f"**${peak_year['est_cost']:,.0f}**. Recommend early budget allocation "
        "and staged refresh planning."
    )
if total_residual > 0:
    recs.append(
        f"**${total_residual:,.0f}** in residual value is tied up in retired assets. "
        "Ensure disposal methods maximise recovery (resale vs recycle)."
    )

for r in recs:
    st.markdown(f"- {r}")

st.caption(
    "Recommendations are rule-based templates an analyst might include in a "
    "monthly reporting pack for Finance and Technology leadership."
)