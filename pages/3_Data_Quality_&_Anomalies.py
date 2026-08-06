"""
Page 3: Data Quality & Anomalies.

Explicitly demonstrates data-management and anomaly-detection skills.
"""
import pandas as pd
import streamlit as st

from utils.data_loader import load_data
from utils.metrics import add_derived_columns, compute_data_quality
from utils.filters import render_sidebar_filters
from utils.constants import DISCLAIMER
from utils.formatting import format_dataframe_for_display
from utils import charts

st.set_page_config(page_title="Data Quality & Anomalies", page_icon="🔍", layout="wide")

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
st.title("🔍 Data Quality & Anomalies")
st.warning(DISCLAIMER)
st.caption(
    "Are our asset records trustworthy? This page surfaces blanks, duplicates, "
    "and anomalies an analyst investigates before relying on the data."
)

with st.expander("ℹ️ What this page is for"):
    st.caption(
        "Supports the Asset Management Analyst responsibilities of data "
        "management, data-quality improvement, and process improvement. "
        "These are the exact issues an analyst investigates before trusting "
        "reports or starting a refresh programme."
    )

if len(filtered_df) == 0:
    st.warning("No data matches the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------
dq = compute_data_quality(filtered_df)

st.subheader("📋 Data Quality Scorecard")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Duplicate Serials", f"{dq['duplicate_serials']}")
c2.metric("Future Purchase Dates", f"{dq['future_purchase_dates']}")
c3.metric("Warranty Before Purchase", f"{dq['warranty_before_purchase']}")
c4.metric("Cost Outliers", f"{dq['cost_outliers']}")
c5.metric("Blank Assigned To", f"{dq['blank_counts'].get('assigned_to', 0)}")
c6.metric("Blank Location", f"{dq['blank_counts'].get('location', 0)}")

st.divider()

# Completeness visual
left, right = st.columns([3, 2])

with left:
    st.plotly_chart(
        charts.completeness_heatmap(dq["completeness"]),
        width='stretch',
    )

with right:
    st.markdown("**Completeness by Field**")
    comp_df = pd.DataFrame(
        {
            "Field": dq["completeness"].keys(),
            "Complete %": dq["completeness"].values(),
            "Blank": [dq["blank_counts"].get(f, 0) for f in dq["completeness"].keys()],
        }
    )
    st.dataframe(format_dataframe_for_display(comp_df), hide_index=True, width='stretch')

st.divider()

# ---------------------------------------------------------------------------
# Anomaly lists
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["Duplicate Serials", "Missing Critical Fields", "Cost Outliers", "Date Inconsistencies"]
)

with tab1:
    st.markdown("**Duplicate serial numbers** — same serial appearing on multiple records.")
    if len(dq["duplicate_rows"]) > 0:
        dup_cols = [c for c in ["asset_tag", "serial_number", "ci_name", "location", "assigned_to", "install_status", "purchase_date"] if c in dq["duplicate_rows"].columns]
        st.dataframe(format_dataframe_for_display(dq["duplicate_rows"][dup_cols]), hide_index=True, width='stretch')
        st.download_button(
            "⬇️ Download duplicate serials",
            data=dq["duplicate_rows"].to_csv(index=False).encode("utf-8"),
            file_name="duplicate_serials.csv",
            mime="text/csv",
        )
    else:
        st.success("No duplicate serials found in the current view.")

with tab2:
    st.markdown("**Missing critical fields** — blanks in key columns.")
    blank_cols = ["assigned_to", "location", "serial_number", "purchase_date", "model"]
    missing_mask = pd.Series(False, index=filtered_df.index)
    for col in blank_cols:
        if col in filtered_df.columns:
            missing_mask |= filtered_df[col].isna()
    if missing_mask.sum() > 0:
        missing_df = filtered_df[missing_mask]
        cols = [c for c in ["asset_tag", "asset_type", "model", "location", "assigned_to", "serial_number", "purchase_date"] if c in missing_df.columns]
        st.dataframe(format_dataframe_for_display(missing_df[cols]), hide_index=True, width='stretch')
        st.caption(f"**{len(missing_df):,}** records with at least one missing critical field.")
    else:
        st.success("No missing critical fields found in the current view.")

with tab3:
    st.markdown(
        "**Cost outliers** — purchase cost > 3× the median for that asset type."
    )
    if len(dq["cost_outlier_rows"]) > 0:
        outlier_cols = [c for c in ["asset_tag", "asset_type", "model", "purchase_cost_nzd", "location", "purchase_date"] if c in dq["cost_outlier_rows"].columns]
        st.dataframe(format_dataframe_for_display(dq["cost_outlier_rows"][outlier_cols]), hide_index=True, width='stretch')
        st.caption(
            f"**{len(dq['cost_outlier_rows']):,}** records flagged as cost outliers."
        )
    else:
        st.success("No cost outliers found in the current view.")

with tab4:
    st.markdown("**Date inconsistencies** — future purchase dates, warranty before purchase.")
    date_issues = []

    if "purchase_date" in filtered_df.columns:
        future = filtered_df[pd.to_datetime(filtered_df["purchase_date"], errors="coerce") > pd.Timestamp.now()]
        if len(future) > 0:
            date_issues.append(("Future purchase date", future))

    if {"purchase_date", "warranty_expiration"}.issubset(filtered_df.columns):
        p = pd.to_datetime(filtered_df["purchase_date"], errors="coerce")
        w = pd.to_datetime(filtered_df["warranty_expiration"], errors="coerce")
        bad_warranty = filtered_df[(w.notna()) & (p.notna()) & (w < p)]
        if len(bad_warranty) > 0:
            date_issues.append(("Warranty before purchase", bad_warranty))

    if not date_issues:
        st.success("No date inconsistencies found in the current view.")
    else:
        for label, data in date_issues:
            st.markdown(f"**{label}** — {len(data):,} records")
            cols = [c for c in ["asset_tag", "asset_type", "purchase_date", "warranty_expiration", "location"] if c in data.columns]
            st.dataframe(format_dataframe_for_display(data[cols]), hide_index=True, width='stretch')

st.divider()

# ---------------------------------------------------------------------------
# Anomaly by location / asset type visual
# ---------------------------------------------------------------------------
st.subheader("Anomaly Volume by Dimension")

dim = st.selectbox("Dimension", ["location", "asset_type"], key="dq_dimension")

anomaly_flags = (
    filtered_df["serial_number"].isna()
    | filtered_df["assigned_to"].isna()
    | filtered_df["location"].isna()
)

anomaly_by_dim = (
    filtered_df.assign(has_anomaly=anomaly_flags)
    .groupby(dim)
    .agg(total=("sys_id", "count"), anomalies=("has_anomaly", "sum"))
    .reset_index()
    .sort_values("anomalies", ascending=False)
    .head(15)
)
anomaly_by_dim["anomaly_rate"] = (anomaly_by_dim["anomalies"] / anomaly_by_dim["total"] * 100).round(1)

if len(anomaly_by_dim) > 0:
    st.plotly_chart(
        charts.horizontal_bar(
            anomaly_by_dim,
            "anomalies",
            dim,
            f"Anomalies by {dim.replace('_', ' ').title()}",
            color=charts.COLOR_WARNING,
        ),
        width='stretch',
    )

st.divider()
st.info(
    "**Insight:** These are the exact data-quality issues an analyst investigates "
    "before trusting reports or starting a refresh programme. In practice, these "
    "would be raised as ServiceNow tasks and followed up with village managers."
)