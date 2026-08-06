"""
Global sidebar filters + session-state persistence.

Provides a shared `render_sidebar_filters()` that returns the filtered
DataFrame plus the threshold settings, so every page uses identical
filter behaviour and cross-page consistency.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st


def _safe_options(df: pd.DataFrame, col: str) -> list:
    """Return sorted unique non-null values for a column as options."""
    if col not in df.columns:
        return []
    vals = df[col].dropna().unique().tolist()
    return sorted(str(v) for v in vals)


def render_sidebar_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """
    Render all global sidebar filters and return (filtered_df, utilisation_threshold, stale_threshold).

    Uses st.session_state for persistence across pages.
    """
    # ---------- Data source info ----------
    if "data_source" in st.session_state:
        st.sidebar.caption(f"**Source:** {st.session_state.data_source}")
    if "last_loaded" in st.session_state:
        # Convert to Pacific/Auckland (NZST) timezone for display
        ts = st.session_state.last_loaded
        try:
            from zoneinfo import ZoneInfo
            nz_ts = ts.astimezone(ZoneInfo("Pacific/Auckland"))
            loaded_str = nz_ts.strftime("%d %b %Y %H:%M:%S %Z")
        except Exception:
            loaded_str = ts.strftime("%d %b %Y %H:%M:%S")
        st.sidebar.caption(f"**Loaded:** {loaded_str}")

    # Refresh button
    if st.sidebar.button("🔄 Refresh data", width='stretch'):
        st.session_state.force_refresh = True
        st.rerun()

    st.sidebar.divider()

    # ---------- Thresholds (persisted) ----------
    utilisation_threshold = st.sidebar.slider(
        "Utilisation threshold",
        min_value=0,
        max_value=100,
        value=st.session_state.get("utilisation_threshold", 30),
        help="Assets with utilisation_score below this are under-utilised.",
    )
    st.session_state.utilisation_threshold = utilisation_threshold

    stale_threshold = st.sidebar.slider(
        "Stale threshold (days)",
        min_value=0,
        max_value=365,
        value=st.session_state.get("stale_threshold", 90),
        help="Assets not seen for more than this many days are considered stale.",
    )
    st.session_state.stale_threshold = stale_threshold

    st.sidebar.divider()

    # ---------- Asset type filter ----------
    asset_types = _safe_options(df, "asset_type")
    selected_types = st.sidebar.multiselect(
        "Asset type",
        options=asset_types,
        default=st.session_state.get("filters_asset_types", asset_types),
    )
    st.session_state.filters_asset_types = selected_types

    # ---------- Location filter ----------
    locations = _safe_options(df, "location")
    selected_locations = st.sidebar.multiselect(
        "Location / Site",
        options=locations,
        default=st.session_state.get("filters_locations", locations),
    )
    st.session_state.filters_locations = selected_locations

    # ---------- Lifecycle stage filter ----------
    lifecycle_stages = _safe_options(df, "lifecycle_stage")
    selected_stages = st.sidebar.multiselect(
        "Lifecycle stage",
        options=lifecycle_stages,
        default=st.session_state.get("filters_lifecycle_stages", lifecycle_stages),
    )
    st.session_state.filters_lifecycle_stages = selected_stages

    # ---------- Install status filter ----------
    install_statuses = _safe_options(df, "install_status")
    selected_install = st.sidebar.multiselect(
        "Install status",
        options=install_statuses,
        default=st.session_state.get("filters_install_statuses", install_statuses),
    )
    st.session_state.filters_install_statuses = selected_install

    # ---------- Purchase date range ----------
    date_range = None
    if "purchase_date" in df.columns:
        valid_dates = pd.to_datetime(df["purchase_date"], errors="coerce").dropna()
        if len(valid_dates) > 0:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            date_range = st.sidebar.date_input(
                "Purchase date range",
                value=(
                    st.session_state.get("filters_date_start", min_date),
                    st.session_state.get("filters_date_end", max_date),
                ),
                min_value=min_date,
                max_value=max_date,
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                st.session_state.filters_date_start = date_range[0]
                st.session_state.filters_date_end = date_range[1]

    st.sidebar.divider()

    # ---------- Reset filters ----------
    if st.sidebar.button("Reset filters", width='stretch'):
        for key in [
            "filters_asset_types",
            "filters_locations",
            "filters_lifecycle_stages",
            "filters_install_statuses",
            "filters_date_start",
            "filters_date_end",
            "utilisation_threshold",
            "stale_threshold",
        ]:
            st.session_state.pop(key, None)
        st.rerun()

    # ---------- Apply filters ----------
    filtered = df.copy()

    if selected_types:
        filtered = filtered[filtered["asset_type"].astype(str).isin(selected_types)]
    if selected_locations:
        filtered = filtered[filtered["location"].astype(str).isin(selected_locations)]
    if selected_stages:
        filtered = filtered[filtered["lifecycle_stage"].astype(str).isin(selected_stages)]
    if selected_install:
        filtered = filtered[filtered["install_status"].astype(str).isin(selected_install)]

    # Date range filter
    if "purchase_date" in df.columns and isinstance(date_range, tuple) and len(date_range) == 2:
        start_ts = pd.Timestamp(date_range[0])
        end_ts = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
        filtered = filtered[
            pd.to_datetime(filtered["purchase_date"], errors="coerce").between(start_ts, end_ts)
        ]

    # ---------- Download current view ----------
    if len(filtered) > 0:
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.sidebar.download_button(
            "⬇️ Download filtered data (CSV)",
            data=csv,
            file_name="ryman_assets_filtered.csv",
            mime="text/csv",
            width='stretch',
        )

    # ---------- About expander ----------
    with st.sidebar.expander("ℹ️ About this demo"):
        st.caption(
            "Synthetic ServiceNow-style asset data generated for demonstration "
            "purposes. No real Ryman Healthcare data is used. The dashboard "
            "demonstrates the analytical work of an Asset Management Analyst: "
            "lifecycle management, data quality, investigations, forecasting, "
            "and compliance reporting."
        )

    return filtered, utilisation_threshold, stale_threshold