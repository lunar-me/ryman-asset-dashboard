"""
Page 7: Compliance & Risk.

Surface non-compliant and higher-risk assets for governance, audit readiness,
and risk conversations.
"""
import pandas as pd
import streamlit as st

from utils.data_loader import load_data
from utils.metrics import add_derived_columns
from utils.filters import render_sidebar_filters
from utils import charts

st.set_page_config(page_title="Compliance & Risk", page_icon="🛡️", layout="wide")

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
st.title("🛡️ Compliance & Risk")
st.caption(
    "Surface non-compliant and higher-risk assets — for governance, audit "
    "readiness, and risk conversations."
)

with st.expander("ℹ️ What this page is for"):
    st.caption(
        "Supports the Asset Management Analyst responsibilities of governance, "
        "compliance monitoring, and risk reduction."
    )

if len(filtered_df) == 0:
    st.warning("No data matches the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
total = len(filtered_df)
non_compliant = filtered_df[filtered_df["is_non_compliant"]]
compliance_rate = (1 - len(non_compliant) / total) * 100

encryption_disabled = 0
os_unsupported = 0
in_use_past_warranty = 0

if "encryption_status" in filtered_df.columns:
    encryption_disabled = int(
        (filtered_df["encryption_status"].astype(str) == "Disabled").sum()
    )
if "os_supported" in filtered_df.columns:
    os_unsupported = int(
        (filtered_df["os_supported"].astype(str) == "Unsupported").sum()
    )
if {"install_status", "warranty_status"}.issubset(filtered_df.columns):
    in_use_states = ["Installed", "In Use"]
    in_use_past_warranty = int(
        (
            filtered_df["install_status"].astype(str).isin(in_use_states)
            & (filtered_df["warranty_status"].astype(str) == "Expired")
        ).sum()
    )

# High-value non-compliant
high_value_threshold = filtered_df["purchase_cost_nzd"].quantile(0.9)
high_value_noncomp = non_compliant[non_compliant["purchase_cost_nzd"] > high_value_threshold]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Compliance Rate", f"{compliance_rate:.1f}%")
c2.metric("Encryption Disabled", f"{encryption_disabled}")
c3.metric("OS Unsupported", f"{os_unsupported}")
c4.metric("In Use Past Warranty", f"{in_use_past_warranty}")
c5.metric("High-Value Non-Compliant", f"{len(high_value_noncomp)}")

st.divider()

# ---------------------------------------------------------------------------
# Non-compliant breakdown
# ---------------------------------------------------------------------------
st.subheader("Non-Compliant Assets")

if len(non_compliant) == 0:
    st.success("No non-compliant assets in the current filter view. ✅")
else:
    left, right = st.columns(2)

    with left:
        noncomp_by_type = (
            non_compliant.groupby("asset_type")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        st.plotly_chart(
            charts.horizontal_bar(
                noncomp_by_type, "count", "asset_type", "Non-Compliant by Type",
                color=charts.COLOR_CRITICAL,
            ),
            width='stretch',
        )

    with right:
        noncomp_by_loc = (
            non_compliant.groupby("location")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(10)
        )
        st.plotly_chart(
            charts.horizontal_bar(
                noncomp_by_loc, "count", "location", "Non-Compliant by Location",
                color=charts.COLOR_CRITICAL,
            ),
            width='stretch',
        )

    st.divider()

    # Reason proxy breakdown
    st.subheader("Reasons for Non-Compliance")

    reason_counts = {}
    if "encryption_status" in filtered_df.columns:
        reason_counts["Encryption Disabled"] = int(
            (filtered_df["encryption_status"].astype(str) == "Disabled").sum()
        )
    if "os_supported" in filtered_df.columns:
        reason_counts["OS Unsupported"] = int(
            (filtered_df["os_supported"].astype(str) == "Unsupported").sum()
        )
    if "is_unassigned" in filtered_df.columns:
        reason_counts["Unassigned but In Use"] = int(
            (filtered_df["is_unassigned"] & filtered_df["install_status"].astype(str).isin(["Installed", "In Use"])).sum()
        )

    reason_df = pd.DataFrame(
        {"Reason": list(reason_counts.keys()), "Count": list(reason_counts.values())}
    ).sort_values("Count", ascending=False)

    st.dataframe(reason_df, hide_index=True, width='stretch')

    st.divider()

    # Non-compliant asset list
    st.subheader(f"Non-Compliant Asset List ({len(non_compliant):,})")
    cols = [c for c in ["asset_tag", "asset_type", "model", "location", "assigned_to", "install_status", "encryption_status", "os_supported", "warranty_status", "purchase_cost_nzd", "notes"] if c in non_compliant.columns]
    st.dataframe(non_compliant[cols], hide_index=True, width='stretch')
    st.download_button(
        "⬇️ Download non-compliant assets (CSV)",
        data=non_compliant.to_csv(index=False).encode("utf-8"),
        file_name="non_compliant_assets.csv",
        mime="text/csv",
    )

st.divider()

# ---------------------------------------------------------------------------
# Warranty risk
# ---------------------------------------------------------------------------
st.subheader("Warranty Risk")

if "warranty_status" in filtered_df.columns:
    warranty_summary = (
        filtered_df.groupby("warranty_status")
        .agg(count=("sys_id", "count"), total_cost=("purchase_cost_nzd", "sum"))
        .reset_index()
    )
    st.dataframe(warranty_summary.round(0), hide_index=True, width='stretch')

    # In-use past warranty list
    if in_use_past_warranty > 0:
        st.markdown(f"**In-Use Assets Past Warranty ({in_use_past_warranty:,})**")
        in_use_expired = filtered_df[
            filtered_df["install_status"].astype(str).isin(["Installed", "In Use"])
            & (filtered_df["warranty_status"].astype(str) == "Expired")
        ]
        cols = [c for c in ["asset_tag", "asset_type", "model", "location", "assigned_to", "purchase_date", "warranty_expiration", "purchase_cost_nzd"] if c in in_use_expired.columns]
        st.dataframe(in_use_expired[cols], hide_index=True, width='stretch')

st.divider()

# ---------------------------------------------------------------------------
# Notes indicating compliance issues
# ---------------------------------------------------------------------------
if "notes" in filtered_df.columns:
    notes_df = filtered_df[filtered_df["notes"].notna() & filtered_df["notes"].astype(str).str.len() > 0]
    if len(notes_df) > 0:
        st.subheader("Assets with Investigation Notes")
        cols = [c for c in ["asset_tag", "asset_type", "location", "assigned_to", "notes", "purchase_cost_nzd"] if c in notes_df.columns]
        st.dataframe(notes_df[cols], hide_index=True, width='stretch')

st.divider()
st.info(
    "**Risk perspective:** Non-compliant assets (encryption disabled, "
    "unsupported OS, unassigned but in use) expose the organisation to "
    "security, regulatory, and support risk. Assets past warranty and still "
    "in use carry replacement and availability risk."
)