"""
Page 4: Missing / Unassigned / Under-utilised.

Core investigative page — maps directly to the role's responsibility of
"investigating missing, unassigned, and under-utilised assets."
"""
import pandas as pd
import streamlit as st

from utils.data_loader import load_data
from utils.metrics import add_derived_columns
from utils.filters import render_sidebar_filters
from utils.constants import DISCLAIMER
from utils.formatting import format_dataframe_for_display
from utils import charts

st.set_page_config(page_title="Missing / Unassigned / Under-utilised", page_icon="🔎", layout="wide")

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
st.title("🔎 Missing / Unassigned / Under-utilised")
st.warning(DISCLAIMER)
st.caption(
    "Where is value leaking? Investigate missing, unassigned, and "
    "under-utilised assets — the core investigative work of the role."
)

with st.expander("ℹ️ What this page is for"):
    st.caption(
        "Supports the Asset Management Analyst responsibilities of investigating "
        "missing, unassigned, and under-utilised assets; accountability for "
        "assets; and maximising value from the estate."
    )

if len(filtered_df) == 0:
    st.warning("No data matches the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Tabs for the three investigation areas
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(
    ["🟥 Missing", "🟧 Unassigned", "🟨 Under-utilised / Stale"]
)

export_cols = [
    "asset_tag",
    "serial_number",
    "model",
    "asset_type",
    "location",
    "assigned_to",
    "install_status",
    "state",
    "last_discovered",
    "days_since_last_seen",
    "purchase_cost_nzd",
    "opportunity_value_nzd",
    "investigation_priority",
    "notes",
]

# ===========================================================================
# Tab A: Missing
# ===========================================================================
with tab1:
    missing_df = filtered_df[filtered_df["is_missing"]]

    if len(missing_df) == 0:
        st.success("No missing assets in the current filter view. ✅")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Missing Assets", f"{len(missing_df):,}")
        c2.metric(
            "Cost at Risk",
            f"${missing_df['purchase_cost_nzd'].sum():,.0f}",
        )
        c3.metric(
            "Estimated Recovery Value",
            f"${missing_df['opportunity_value_nzd'].sum():,.0f}",
        )

        left, right = st.columns(2)

        with left:
            missing_by_loc = (
                missing_df.groupby("location").size().reset_index(name="count")
                .sort_values("count", ascending=False).head(10)
            )
            st.plotly_chart(
                charts.horizontal_bar(
                    missing_by_loc, "count", "location", "Missing by Location",
                    color=charts.COLOR_CRITICAL,
                ),
                width='stretch',
            )

        with right:
            st.plotly_chart(
                charts.histogram(
                    missing_df,
                    "days_since_last_seen",
                    "Days Since Last Seen (Missing)",
                    color=charts.COLOR_CRITICAL,
                ),
                width='stretch',
            )

        st.markdown(f"**Missing Asset List ({len(missing_df):,})**")
        cols = [c for c in export_cols if c in missing_df.columns]
        view = missing_df[cols].sort_values("investigation_priority", ascending=False)
        st.dataframe(format_dataframe_for_display(view), hide_index=True, width='stretch')
        st.download_button(
            "⬇️ Download missing assets (CSV)",
            data=view.to_csv(index=False).encode("utf-8"),
            file_name="missing_assets.csv",
            mime="text/csv",
        )

# ===========================================================================
# Tab B: Unassigned
# ===========================================================================
with tab2:
    unassigned_df = filtered_df[filtered_df["is_unassigned"]]

    if len(unassigned_df) == 0:
        st.success("No unassigned assets in the current filter view. ✅")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Unassigned Assets", f"{len(unassigned_df):,}")
        c2.metric(
            "Total Cost",
            f"${unassigned_df['purchase_cost_nzd'].sum():,.0f}",
        )
        c3.metric(
            "Estimated Opportunity",
            f"${unassigned_df['opportunity_value_nzd'].sum():,.0f}",
        )

        left, right = st.columns(2)

        with left:
            unassigned_by_type = (
                unassigned_df.groupby("asset_type").size().reset_index(name="count")
                .sort_values("count", ascending=False)
            )
            st.plotly_chart(
                charts.horizontal_bar(
                    unassigned_by_type, "count", "asset_type", "Unassigned by Type",
                    color=charts.COLOR_WARNING,
                ),
                width='stretch',
            )

        with right:
            # High-value unassigned
            high_value = unassigned_df.nlargest(10, "purchase_cost_nzd")
            high_value = high_value[["asset_tag", "asset_type", "model", "purchase_cost_nzd", "location"]]
            st.markdown("**Top 10 High-Value Unassigned**")
            st.dataframe(format_dataframe_for_display(high_value), hide_index=True, width='stretch')

        st.markdown(f"**Unassigned Asset List ({len(unassigned_df):,})**")
        cols = [c for c in export_cols if c in unassigned_df.columns]
        view = unassigned_df[cols].sort_values("investigation_priority", ascending=False)
        st.dataframe(format_dataframe_for_display(view), hide_index=True, width='stretch')
        st.download_button(
            "⬇️ Download unassigned assets (CSV)",
            data=view.to_csv(index=False).encode("utf-8"),
            file_name="unassigned_assets.csv",
            mime="text/csv",
        )

# ===========================================================================
# Tab C: Under-utilised / Stale
# ===========================================================================
with tab3:
    st.caption(
        f"Under-utilised threshold: **{util_threshold}** (utilisation score). "
        f"Stale threshold: **{stale_threshold}** days since last seen. "
        "Adjust these in the sidebar."
    )

    underutilised_df = filtered_df[filtered_df["is_underutilised"]]
    stale_df = filtered_df[filtered_df["is_stale"]]
    reclaim_df = filtered_df[filtered_df["is_reclaim_candidate"]]

    c1, c2, c3 = st.columns(3)
    c1.metric("Under-Utilised", f"{len(underutilised_df):,}")
    c2.metric("Stale (> threshold days)", f"{len(stale_df):,}")
    c3.metric("Reclaim Candidates", f"{len(reclaim_df):,}")

    left, right = st.columns(2)

    with left:
        reclaim_by_loc = (
            reclaim_df.groupby("location").size().reset_index(name="count")
            .sort_values("count", ascending=False).head(10)
        )
        if len(reclaim_by_loc) > 0:
            st.plotly_chart(
                charts.horizontal_bar(
                    reclaim_by_loc, "count", "location", "Reclaim Candidates by Location",
                    color=charts.COLOR_WARNING,
                ),
                width='stretch',
            )

    with right:
        if len(reclaim_df) > 0:
            st.plotly_chart(
                charts.histogram(
                    reclaim_df,
                    "utilisation_score",
                    "Utilisation Score (Reclaim Candidates)",
                    color=charts.COLOR_WARNING,
                ),
                width='stretch',
            )

    # Ranked list of reclaim candidates
    if len(reclaim_df) > 0:
        st.markdown(f"**Reclaim Candidate List ({len(reclaim_df):,})** — ranked by investigation priority")
        cols = [c for c in export_cols if c in reclaim_df.columns]
        view = reclaim_df[cols].sort_values("investigation_priority", ascending=False)
        st.dataframe(format_dataframe_for_display(view), hide_index=True, width='stretch')
        st.download_button(
            "⬇️ Download reclaim candidates (CSV)",
            data=view.to_csv(index=False).encode("utf-8"),
            file_name="reclaim_candidates.csv",
            mime="text/csv",
        )
    else:
        st.success("No reclaim candidates in the current filter view. ✅")

st.divider()

# ---------------------------------------------------------------------------
# Guidance text
# ---------------------------------------------------------------------------
st.info(
    "**Typical next steps for an Asset Management Analyst:**\n\n"
    "1. **Contact the location** — confirm whether the asset is physically present.\n"
    "2. **Raise a ServiceNow task** — to investigate, relocate, or dispose of the asset.\n"
    "3. **Schedule a remote or on-site audit** — for villages with high anomaly counts.\n"
    "4. **Reassign unassigned devices** — match against staff onboarding records.\n"
    "5. **Reclaim under-utilised devices** — redeploy, pool, or dispose to recover value."
)

st.caption(
    "Opportunity value heuristic: residual value where available; otherwise "
    "40% of cost for missing, 25% for unassigned, 15% for under-utilised."
)