"""
Reusable chart helpers for the dashboard.

Wraps Plotly express/Figure construction so all pages share consistent
styling, colour semantics, and layout conventions.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Colour semantics (per spec §6 "Visual language")
# ---------------------------------------------------------------------------
COLOR_CRITICAL = "#C0392B"      # Red — missing, non-compliant, critical
COLOR_WARNING = "#E67E22"       # Amber — under-utilised, refresh due, data quality
COLOR_HEALTHY = "#27AE60"       # Green — healthy, in use, compliant
COLOR_NEUTRAL = "#7F8C8D"       # Grey — informational
COLOR_PRIMARY = "#2E86AB"       # Primary brand/blue

# Default categorical palette (colour-blind friendly)
CATEGORICAL = px.colors.qualitative.Set2


def base_layout(title: str = "", height: int = 400) -> dict:
    """Return a consistent Plotly layout dict."""
    return {
        "title": {"text": title, "font": {"size": 16}},
        "height": height,
        "margin": {"l": 60, "r": 20, "t": 60, "b": 60},
        "template": "plotly_white",
        "legend": {"orientation": "h", "y": -0.2},
    }


def horizontal_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    color: str = COLOR_PRIMARY,
    height: int = 400,
) -> go.Figure:
    """Horizontal bar chart for ranked lists (locations, models, types)."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        orientation="h",
        title=title,
        color_discrete_sequence=[color],
    )
    fig.update_layout(**base_layout(title, height))
    fig.update_yaxes(autorange="reversed")
    return fig


def vertical_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    color: str = COLOR_PRIMARY,
    height: int = 400,
) -> go.Figure:
    """Vertical bar chart for distributions / trends."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        title=title,
        color_discrete_sequence=[color],
    )
    fig.update_layout(**base_layout(title, height))
    return fig


def stacked_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: str,
    title: str = "",
    height: int = 400,
) -> go.Figure:
    """Stacked bar chart (e.g. asset type by lifecycle stage)."""
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        title=title,
        barmode="stack",
        color_discrete_sequence=CATEGORICAL,
    )
    fig.update_layout(**base_layout(title, height))
    return fig


def line_trend(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    color: str = COLOR_PRIMARY,
    height: int = 350,
) -> go.Figure:
    """Line/area chart for trends over time (purchase cohorts, forecast)."""
    fig = px.line(
        df,
        x=x_col,
        y=y_col,
        title=title,
        markers=True,
        color_discrete_sequence=[color],
    )
    fig.update_traces(fill="tozeroy", fillcolor=f"rgba(46,134,171,0.15)")
    fig.update_layout(**base_layout(title, height))
    return fig


def histogram(
    df: pd.DataFrame,
    col: str,
    title: str = "",
    color: str = COLOR_PRIMARY,
    nbins: int = 30,
    height: int = 350,
) -> go.Figure:
    """Histogram of a numeric column (e.g. age, cost distribution)."""
    fig = px.histogram(
        df,
        x=col,
        nbins=nbins,
        title=title,
        color_discrete_sequence=[color],
    )
    fig.update_layout(**base_layout(title, height))
    return fig


def funnel_stages(
    df: pd.DataFrame,
    stage_col: str,
    count_col: str,
    title: str = "",
    height: int = 400,
) -> go.Figure:
    """Funnel-style horizontal bars for lifecycle stage distribution."""
    # Order by the natural lifecycle sequence
    stage_order = [
        "Requested",
        "Ordered",
        "Received",
        "Deployed",
        "In Use",
        "Refresh Due",
        "Retired",
        "Disposed",
    ]
    present = [s for s in stage_order if s in df[stage_col].astype(str).unique()]
    other = [
        s
        for s in df[stage_col].astype(str).unique()
        if s not in stage_order and s != "Unknown"
    ]
    categories = present + other + (["Unknown"] if "Unknown" in df[stage_col].astype(str).unique() else [])

    fig = px.bar(
        df,
        x=count_col,
        y=stage_col,
        orientation="h",
        category_orders={stage_col: list(reversed(categories))},
        title=title,
        color_discrete_sequence=[COLOR_PRIMARY],
    )
    fig.update_layout(**base_layout(title, height))
    fig.update_yaxes(autorange="reversed")
    return fig


def scatter_priority(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: str,
    hover_cols: list[str],
    title: str = "",
    height: int = 450,
) -> go.Figure:
    """Scatter/bubble for investigation priority views."""
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        hover_data=hover_cols,
        title=title,
        color_continuous_scale=["#27AE60", "#E67E22", "#C0392B"],
    )
    fig.update_layout(**base_layout(title, height))
    return fig


def completeness_heatmap(
    completeness: dict,
    title: str = "Field Completeness (%)",
    height: int = 300,
) -> go.Figure:
    """Horizontal bar showing completeness % per critical field."""
    df = pd.DataFrame(
        {"field": list(completeness.keys()), "completeness": list(completeness.values())}
    ).sort_values("completeness")

    fig = px.bar(
        df,
        x="completeness",
        y="field",
        orientation="h",
        title=title,
        color="completeness",
        color_continuous_scale=["#C0392B", "#E67E22", "#27AE60"],
        range_color=[0, 100],
    )
    fig.update_layout(**base_layout(title, height))
    fig.update_yaxes(autorange="reversed")
    fig.update_coloraxes(colorbar_title="% Complete")
    return fig