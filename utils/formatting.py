"""
Number & money formatting helpers for table display.

Formats currency columns as $12,345 (no cents) and count columns as 12,345.
"""
from __future__ import annotations

import pandas as pd


def format_money(value) -> str:
    """Format a value as NZD currency without cents: $12,345."""
    try:
        v = float(value)
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return str(value)


def format_number(value) -> str:
    """Format a value with thousands separator: 12,345."""
    try:
        v = float(value)
        return f"{v:,.0f}"
    except (TypeError, ValueError):
        return str(value)


# Column names that typically contain money values
MONEY_COLUMNS = {
    "purchase_cost_nzd",
    "residual_value_nzd",
    "opportunity_value_nzd",
    "est_cost",
    "estimated_cost",
    "total_cost",
    "total_spend",
    "recovered",
    "cost",
    "est_savings",
    "estimated_savings",
    "reclaim_opportunity",
    "total_savings",
    "cost_at_risk",
    "opportunity",
}


def format_dataframe_for_display(
    df: pd.DataFrame, money_cols: set | None = None, number_cols: set | None = None
) -> pd.DataFrame:
    """
    Return a copy of the DataFrame with money columns formatted as $12,345
    and numeric count columns formatted as 12,345.

    If money_cols/number_cols are not provided, heuristically detects columns.
    """
    if money_cols is None:
        money_cols = MONEY_COLUMNS

    out = df.copy()

    # Detect money columns
    for col in out.columns:
        col_lower = str(col).lower()
        is_money = (
            col_lower in money_cols
            or "cost" in col_lower
            or "value" in col_lower
            or "saving" in col_lower
            or "opportunity" in col_lower
            or "reclaim" in col_lower
            or "spend" in col_lower
            or "recovered" in col_lower
            or "residual" in col_lower
            or "price" in col_lower
            or "nzd" in col_lower
        )
        if is_money and pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].map(format_money)

    # Detect count/number columns (integers, not money)
    for col in out.columns:
        col_lower = str(col).lower()
        is_money = (
            col_lower in money_cols
            or "cost" in col_lower
            or "value" in col_lower
            or "saving" in col_lower
            or "opportunity" in col_lower
            or "reclaim" in col_lower
            or "spend" in col_lower
            or "recovered" in col_lower
            or "residual" in col_lower
            or "price" in col_lower
            or "nzd" in col_lower
        )
        if is_money:
            continue
        if pd.api.types.is_integer_dtype(out[col]):
            out[col] = out[col].map(format_number)

    return out