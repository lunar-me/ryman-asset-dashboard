"""
Ryman IT Asset Management Dashboard — Entry Point.

Landing page / Home. Loads data, applies global sidebar filters,
and displays a brief overview plus navigation guidance.
"""
import streamlit as st

from utils.data_loader import load_data
from utils.metrics import add_derived_columns, compute_kpis
from utils.filters import render_sidebar_filters
from utils.constants import DISCLAIMER
from utils import charts

st.set_page_config(
    page_title="Ryman IT Asset Management",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
force_refresh = st.session_state.pop("force_refresh", False)
try:
    df, source, loaded_at = load_data(force_refresh=force_refresh)
    st.session_state.data_source = source
    st.session_state.last_loaded = loaded_at
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.stop()

# Enrich with derived columns using persisted thresholds
util_threshold = st.session_state.get("utilisation_threshold", 30)
stale_threshold = st.session_state.get("stale_threshold", 90)
df = add_derived_columns(df, util_threshold, stale_threshold)

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
filtered_df, util_threshold, stale_threshold = render_sidebar_filters(df)
# Re-apply derived columns with updated thresholds
filtered_df = add_derived_columns(filtered_df, util_threshold, stale_threshold)

# ---------------------------------------------------------------------------
# Page content
# ---------------------------------------------------------------------------
st.title("🖥️ Ryman IT Asset Management Dashboard")

st.warning(DISCLAIMER)

st.caption(
    "A demonstration of the analytical work of an **Asset Management Analyst** — "
    "managing the full lifecycle of technology assets across Ryman villages in "
    "New Zealand and Australia."
)

# KPI row
kpis = compute_kpis(filtered_df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Assets", f"{kpis['total_assets']:,}")
col2.metric("Total Purchase Cost", f"${kpis['total_cost']:,.0f}")
col3.metric("Missing or Unassigned", f"{kpis['pct_missing_or_unassigned']}%")
col4.metric("Non-Compliant", f"{kpis['pct_non_compliant']}%")

col5, col6, col7 = st.columns(3)
col5.metric("Under-Utilised", f"{kpis['pct_underutilised']}%")
col6.metric("Refresh Due (12 mo)", f"{kpis['refresh_next_12m']:,}")
col7.metric("Reclaim Opportunity", f"${kpis['reclaim_opportunity']:,.0f}")

st.divider()

st.subheader("What's in this dashboard?")
st.markdown(
    """
    This tool demonstrates how an **Asset Management Analyst** keeps technology
    assets accurate, productive, compliant, and cost-efficient:

    | Page | What it answers |
    |------|-----------------|
    | **Executive Overview** | The 30-second health check for Technology & Finance |
    | **Asset Inventory** | What do we own, and where is it? |
    | **Data Quality & Anomalies** | Are our records trustworthy? |
    | **Missing / Unassigned / Under-utilised** | Where is value leaking? |
    | **Lifecycle & Refresh Planning** | What's coming due for replacement? |
    | **Cost Savings & Forecasting** | What can we save, and what will refresh cost? |
    | **Compliance & Risk** | What are our governance risks? |
    """
)

st.info(
    "Use the **sidebar** to filter by asset type, location, lifecycle stage, "
    "and more. Thresholds for under-utilisation and stale detection are "
    "adjustable there too. Use the navigation on the left to explore each page."
)

# Quick chart: asset count by type
if len(filtered_df) > 0:
    st.subheader("Quick View")
    type_counts = (
        filtered_df.groupby("asset_type")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    st.plotly_chart(
        charts.vertical_bar(type_counts, "asset_type", "count", "Assets by Type"),
        width='stretch',
    )