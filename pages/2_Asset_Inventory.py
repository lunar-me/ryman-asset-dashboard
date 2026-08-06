"""
Page 2: Asset Inventory.

Searchable, filterable master list — "what do we own and where is it?"
"""
import pandas as pd
import streamlit as st

from utils.data_loader import load_data
from utils.metrics import add_derived_columns
from utils.filters import render_sidebar_filters
from utils.constants import DISCLAIMER
from utils.formatting import format_dataframe_for_display

st.set_page_config(page_title="Asset Inventory", page_icon="🗂️", layout="wide")

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
st.title("🗂️ Asset Inventory")
st.warning(DISCLAIMER)
st.caption(
    "The digital equivalent of 'what do we own and where is it?' — "
    "searchable, filterable, exportable."
)

with st.expander("ℹ️ What this page is for"):
    st.caption(
        "Supports the Asset Management Analyst responsibility of maintaining "
        "accurate asset records and preparing for remote or on-site audits."
    )

if len(filtered_df) == 0:
    st.warning("No data matches the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary counts
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    type_summary = filtered_df.groupby("asset_type").size().reset_index(name="count")
    st.markdown("**Assets by Type**")
    st.dataframe(format_dataframe_for_display(type_summary), hide_index=True, width='stretch')

with col2:
    install_summary = (
        filtered_df.groupby("install_status").size().reset_index(name="count")
    )
    st.markdown("**Assets by Install Status**")
    st.dataframe(format_dataframe_for_display(install_summary), hide_index=True, width='stretch')

with col3:
    loc_summary = filtered_df.groupby("location").size().reset_index(name="count")
    st.markdown("**Assets by Location**")
    st.dataframe(format_dataframe_for_display(loc_summary), hide_index=True, width='stretch')

st.divider()

# ---------------------------------------------------------------------------
# Search box
# ---------------------------------------------------------------------------
search_query = st.text_input(
    "🔍 Search assets",
    placeholder="Search by asset_tag, serial_number, assigned_to, or ci_name…",
    key="inventory_search",
)

# Default columns to surface (per spec)
default_cols = [
    "asset_tag",
    "asset_type",
    "model",
    "manufacturer",
    "install_status",
    "lifecycle_stage",
    "assigned_to",
    "location",
    "purchase_date",
    "purchase_cost_nzd",
    "utilisation_score",
    "is_non_compliant",
]

# Column selector
all_cols = list(filtered_df.columns)
selected_cols = st.multiselect(
    "Select columns to show",
    options=all_cols,
    default=[c for c in default_cols if c in all_cols],
    key="inventory_cols",
)

# Apply search
view = filtered_df
if search_query:
    mask = (
        view["asset_tag"].astype(str).str.contains(search_query, case=False, na=False)
        | view["serial_number"].astype(str).str.contains(search_query, case=False, na=False)
        | view["assigned_to"].astype(str).str.contains(search_query, case=False, na=False)
        | view["ci_name"].astype(str).str.contains(search_query, case=False, na=False)
    )
    view = view[mask]

# Select columns
if selected_cols:
    view = view[selected_cols]

# ---------------------------------------------------------------------------
# Display table
# ---------------------------------------------------------------------------
st.subheader(f"Inventory ({len(view):,} assets)")
st.dataframe(format_dataframe_for_display(view), width='stretch', hide_index=True)

# Download current view
if len(view) > 0:
    st.download_button(
        "⬇️ Download current view (CSV)",
        data=view.to_csv(index=False).encode("utf-8"),
        file_name="asset_inventory_view.csv",
        mime="text/csv",
    )

# Group by option
st.divider()
group_col = st.selectbox(
    "Group by (summary view)",
    options=["asset_type", "location", "model", "manufacturer", "department", "install_status"],
    key="inventory_group_col",
)

if group_col:
    group_summary = (
        filtered_df.groupby(group_col)
        .agg(
            count=("sys_id", "count"),
            total_cost=("purchase_cost_nzd", "sum"),
            avg_utilisation=("utilisation_score", "mean"),
        )
        .reset_index()
        .sort_values("count", ascending=False)
    )
    group_summary["total_cost"] = group_summary["total_cost"].round(0)
    group_summary["avg_utilisation"] = group_summary["avg_utilisation"].round(1)
    st.markdown(f"**Summary by {group_col.replace('_', ' ').title()}**")
    st.dataframe(format_dataframe_for_display(group_summary), hide_index=True, width='stretch')