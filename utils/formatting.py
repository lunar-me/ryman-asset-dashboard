"""
Number & money formatting helpers for table display.

Formats:
  - Money columns as $12,345 (no cents)
  - Count columns as 12,345
  - Calendar year columns as 2025 (no comma)
  - Percentage columns as 60.1%
  - Age columns as "1 yr 6 mo" / "10 mo" / "3 yr"
  - Date columns as YYYY-MM-DD
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


def format_year(value) -> str:
    """Format a calendar year without comma: 2025."""
    try:
        return f"{int(float(value))}"
    except (TypeError, ValueError):
        return str(value)


def format_percent(value) -> str:
    """Format a percentage value as 60.1%."""
    try:
        v = float(value)
        return f"{v:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def format_age_years(value, zero_as_dash: bool = False) -> str:
    """
    Format an age in years as "X yr Y mo".

    Examples:
        1.5  -> "1 yr 6 mo"
        0.8  -> "10 mo"
        0.25 -> "3 mo"
        2.0  -> "2 yr"
        3.25 -> "3 yr 3 mo"

    If zero_as_dash is True, a value of 0 renders as "-"
    (used for remaining_life_years where 0 = end of life).
    """
    try:
        v = float(value)
        if pd.isna(v):
            return ""
        total_months = round(v * 12)
        years = total_months // 12
        months = total_months % 12

        if years == 0 and months == 0:
            return "-" if zero_as_dash else "0 mo"
        if years == 0:
            return f"{months} mo"
        if months == 0:
            return f"{years} yr"
        return f"{years} yr {months} mo"
    except (TypeError, ValueError):
        return str(value)


def format_date(value) -> str:
    """Format a datetime value as YYYY-MM-DD."""
    try:
        if pd.isna(value):
            return ""
        ts = pd.Timestamp(value)
        return ts.strftime("%Y-%m-%d")
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

# Column names that are calendar years (no comma formatting)
YEAR_COLUMNS = {
    "year",
    "refresh_year",
    "purchase_year",
    "disposal_year",
    "warranty_year",
}

# Column names that are dates (format as YYYY-MM-DD)
DATE_COLUMNS = {
    "purchase_date",
    "planned_refresh_date",
    "disposal_date",
    "warranty_expiration",
    "last_discovered",
}

# Column name substrings that indicate percentages
PERCENT_HINTS = (
    "pct",
    "percent",
    "%",
    "rate",
    "completeness",
)


def _is_year_col(col: str) -> bool:
    return str(col).lower() in YEAR_COLUMNS


def _is_date_col(col: str) -> bool:
    return str(col).lower() in DATE_COLUMNS


def _is_percent_col(col: str) -> bool:
    col_lower = str(col).lower()
    return any(hint in col_lower for hint in PERCENT_HINTS)


def _is_age_col(col: str) -> bool:
    col_lower = str(col).lower()
    return (
        "age" in col_lower
        or "life_years" in col_lower
        or "remaining_life" in col_lower
    )


def _is_money_col(col: str, money_cols: set) -> bool:
    col_lower = str(col).lower()
    return (
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


def format_dataframe_for_display(
    df: pd.DataFrame, money_cols: set | None = None
) -> pd.DataFrame:
    """
    Return a copy of the DataFrame with formatted columns:

      - Money columns  -> $12,345
      - Year columns   -> 2025 (no comma)
      - Percent columns -> 60.1%
      - Age columns     -> "1 yr 6 mo"
      - Date columns    -> "2025-03-14"
      - Integer counts  -> 12,345
    """
    if money_cols is None:
        money_cols = MONEY_COLUMNS

    out = df.copy()

    for col in out.columns:
        col_str = str(col)

        # Check for date columns first (datetime dtype or known date name)
        if _is_date_col(col_str):
            # Handle both datetime dtype and object/string dates
            try:
                if pd.api.types.is_datetime64_any_dtype(out[col]):
                    out[col] = out[col].map(format_date)
                else:
                    # Try converting to datetime first
                    converted = pd.to_datetime(out[col], errors="coerce")
                    if converted.notna().any():
                        out[col] = converted.map(format_date)
            except Exception:
                pass
            continue

        if not pd.api.types.is_numeric_dtype(out[col]):
            continue

        # Priority: year > percent > age > money > plain number
        if _is_year_col(col_str):
            out[col] = out[col].map(format_year)
        elif _is_percent_col(col_str):
            out[col] = out[col].map(format_percent)
        elif _is_age_col(col_str):
            # remaining_life_years: 0 = end of life → show "-"
            use_dash = "remaining_life" in col_str.lower()
            out[col] = out[col].map(lambda v: format_age_years(v, zero_as_dash=use_dash))
        elif _is_money_col(col_str, money_cols):
            out[col] = out[col].map(format_money)
        elif pd.api.types.is_integer_dtype(out[col]):
            out[col] = out[col].map(format_number)

    return out