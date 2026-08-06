"""
Metrics & business rules module.

All derived columns, KPI calculations, and business logic live here so every
page uses the same definitions (per the spec's design principle of
centralised calculations).
"""
from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Derived columns
# ---------------------------------------------------------------------------


def add_derived_columns(
    df: pd.DataFrame,
    utilisation_threshold: int = 30,
    stale_threshold: int = 90,
) -> pd.DataFrame:
    """
    Add derived boolean/numeric columns to the raw DataFrame.

    Mutates a copy; returns the enriched DataFrame.
    """
    df = df.copy()

    # --- Asset age (years) ---
    if "purchase_date" in df.columns and "asset_age_years" not in df.columns:
        today = pd.Timestamp.now().normalize()
        df["asset_age_years"] = (
            (today - pd.to_datetime(df["purchase_date"], errors="coerce")).dt.days
            / 365.25
        ).round(2)

    # --- is_unassigned ---
    if "assigned_to" in df.columns:
        df["is_unassigned"] = (
            df["assigned_to"].isna()
            | (df["assigned_to"].astype(str).str.strip() == "")
            | (df["assigned_to"].astype(str).str.lower() == "nan")
        )
    else:
        df["is_unassigned"] = False

    # --- is_missing ---
    if "install_status" in df.columns:
        df["is_missing"] = df["install_status"].astype(str) == "Missing"
    else:
        df["is_missing"] = False

    # --- is_underutilised ---
    if "utilisation_score" in df.columns:
        df["is_underutilised"] = (
            pd.to_numeric(df["utilisation_score"], errors="coerce") < utilisation_threshold
        )
    else:
        df["is_underutilised"] = False

    # --- is_stale ---
    if "days_since_last_seen" in df.columns:
        df["is_stale"] = (
            pd.to_numeric(df["days_since_last_seen"], errors="coerce") > stale_threshold
        )
    else:
        df["is_stale"] = False

    # --- is_past_warranty ---
    if "warranty_status" in df.columns:
        df["is_past_warranty"] = df["warranty_status"].astype(str) == "Expired"
    elif "warranty_expiration" in df.columns:
        df["is_past_warranty"] = pd.to_datetime(
            df["warranty_expiration"], errors="coerce"
        ) < pd.Timestamp.now()
    else:
        df["is_past_warranty"] = False

    # --- is_reclaim_candidate ---
    # Unassigned OR Missing OR (Under-utilised AND still In Use / Installed)
    in_use_states = ["Installed", "In Use"]
    if "install_status" in df.columns:
        active_mask = df["install_status"].astype(str).isin(in_use_states)
    else:
        active_mask = pd.Series(False, index=df.index)

    df["is_reclaim_candidate"] = (
        df["is_unassigned"] | df["is_missing"] | (df["is_underutilised"] & active_mask)
    )

    # --- is_refresh_due_soon ---
    current_year = pd.Timestamp.now().year
    df["is_refresh_due_soon"] = False
    if "lifecycle_stage" in df.columns:
        df["is_refresh_due_soon"] |= (
            df["lifecycle_stage"].astype(str) == "Refresh Due"
        )
    if "remaining_life_years" in df.columns:
        df["is_refresh_due_soon"] |= (
            pd.to_numeric(df["remaining_life_years"], errors="coerce") <= 0.5
        )
    if "refresh_year" in df.columns:
        df["is_refresh_due_soon"] |= (
            pd.to_numeric(df["refresh_year"], errors="coerce") == current_year
        )

    # --- is_past_useful_life ---
    df["is_past_useful_life"] = False
    if "remaining_life_years" in df.columns:
        df["is_past_useful_life"] |= (
            pd.to_numeric(df["remaining_life_years"], errors="coerce") <= 0
        )
    if "asset_age_years" in df.columns and "useful_life_years" in df.columns:
        df["is_past_useful_life"] |= (
            df["asset_age_years"] > pd.to_numeric(df["useful_life_years"], errors="coerce")
        )

    # --- Estimated idle / opportunity value (NZD) ---
    # Heuristic per spec:
    #   - residual_value_nzd if present and > 0
    #   - Missing → 40% of purchase_cost_nzd
    #   - Unassigned → 25% of purchase_cost_nzd
    #   - Under-utilised → 15% of purchase_cost_nzd
    #   - else → 0
    cost = pd.to_numeric(df.get("purchase_cost_nzd", 0), errors="coerce").fillna(0)
    residual = pd.to_numeric(df.get("residual_value_nzd", 0), errors="coerce").fillna(0)

    # Start with residual where positive
    opp = residual.where(residual > 0, 0.0)

    # Missing → 40%
    missing_mask = df["is_missing"] & (opp == 0)
    opp = opp.mask(missing_mask, cost * 0.40)

    # Unassigned → 25%
    unassigned_mask = df["is_unassigned"] & (opp == 0)
    opp = opp.mask(unassigned_mask, cost * 0.25)

    # Under-utilised → 15%
    under_mask = df["is_underutilised"] & (opp == 0)
    opp = opp.mask(under_mask, cost * 0.15)

    df["opportunity_value_nzd"] = opp.round(2)

    # --- Investigation priority score ---
    # Simple heuristic: high cost + long time missing/unseen
    days = pd.to_numeric(df.get("days_since_last_seen", 0), errors="coerce").fillna(0)
    norm_cost = cost / cost.max() if cost.max() > 0 else 0
    norm_days = (days / days.max()).fillna(0) if days.max() > 0 else 0

    problem_score = (
        df["is_missing"].astype(int) * 3
        + df["is_unassigned"].astype(int) * 2
        + df["is_underutilised"].astype(int) * 1
    )
    df["investigation_priority"] = (
        problem_score * 0.5 + norm_cost * 0.3 + norm_days * 0.2
    ).round(3)

    return df


# ---------------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------------


def compute_kpis(df: pd.DataFrame) -> dict:
    """Compute the core KPI values for the Executive Overview page."""
    total = len(df)
    if total == 0:
        return {
            "total_assets": 0,
            "total_cost": 0.0,
            "pct_missing_or_unassigned": 0.0,
            "pct_non_compliant": 0.0,
            "pct_underutilised": 0.0,
            "refresh_next_12m": 0,
            "reclaim_opportunity": 0.0,
            "avg_age_years": 0.0,
        }

    total_cost = float(
        pd.to_numeric(df.get("purchase_cost_nzd", 0), errors="coerce").sum()
    )

    pct_missing_unassigned = (
        float((df.get("is_missing", False) | df.get("is_unassigned", False)).sum())
        / total
        * 100
    )

    pct_non_compliant = (
        float(df.get("is_non_compliant", False).sum()) / total * 100
    )

    pct_underutilised = (
        float(df.get("is_underutilised", False).sum()) / total * 100
    )

    # Refresh due in next 12 months
    refresh_12m = 0
    if "is_refresh_due_soon" in df.columns:
        refresh_12m = int(df["is_refresh_due_soon"].sum())
    elif "refresh_year" in df.columns:
        current_year = pd.Timestamp.now().year
        refresh_12m = int(
            (pd.to_numeric(df["refresh_year"], errors="coerce") <= current_year + 1)
            & (pd.to_numeric(df["refresh_year"], errors="coerce") >= current_year)
        ).sum()

    reclaim_opp = float(df.get("opportunity_value_nzd", 0).sum())

    avg_age = float(
        pd.to_numeric(df.get("asset_age_years", 0), errors="coerce").mean()
    )

    return {
        "total_assets": total,
        "total_cost": round(total_cost, 2),
        "pct_missing_or_unassigned": round(pct_missing_unassigned, 1),
        "pct_non_compliant": round(pct_non_compliant, 1),
        "pct_underutilised": round(pct_underutilised, 1),
        "refresh_next_12m": refresh_12m,
        "reclaim_opportunity": round(reclaim_opp, 2),
        "avg_age_years": round(avg_age, 2),
    }


# ---------------------------------------------------------------------------
# Data quality metrics
# ---------------------------------------------------------------------------


def compute_data_quality(df: pd.DataFrame) -> dict:
    """
    Compute data-quality scorecard metrics:
    completeness %, blanks, duplicates, date anomalies.
    """
    total = len(df)
    critical_fields = [
        "serial_number",
        "assigned_to",
        "location",
        "purchase_date",
        "model",
        "manufacturer",
    ]

    completeness = {}
    for col in critical_fields:
        if col in df.columns:
            non_null = df[col].notna().sum()
            completeness[col] = round(non_null / total * 100, 1) if total else 0.0
        else:
            completeness[col] = 0.0

    blank_counts = {}
    for col in critical_fields:
        if col in df.columns:
            blank_counts[col] = int(df[col].isna().sum())
        else:
            blank_counts[col] = total

    # Duplicate serials
    dup_serials = 0
    dup_rows: pd.DataFrame = pd.DataFrame()
    if "serial_number" in df.columns:
        serials = df["serial_number"]
        # Only consider non-null serials; count second+ occurrences as duplicates
        non_null = serials.notna()
        dup_serials = int(serials[non_null].duplicated().sum())
        # Flag ALL rows in duplicate groups (both copies) for the anomaly list
        dup_mask = non_null & serials.duplicated(keep=False)
        dup_rows = df[dup_mask]

    # Date anomalies
    future_purchase = 0
    warranty_before_purchase = 0
    if "purchase_date" in df.columns:
        future_purchase = int(
            (pd.to_datetime(df["purchase_date"], errors="coerce") > pd.Timestamp.now()).sum()
        )
    if {"purchase_date", "warranty_expiration"}.issubset(df.columns):
        p = pd.to_datetime(df["purchase_date"], errors="coerce")
        w = pd.to_datetime(df["warranty_expiration"], errors="coerce")
        warranty_before_purchase = int(((w.notna()) & (p.notna()) & (w < p)).sum())

    # Cost outliers ( > 3x median for that asset_type )
    cost_outliers = 0
    outlier_df: pd.DataFrame = pd.DataFrame()
    if {"purchase_cost_nzd", "asset_type"}.issubset(df.columns):
        cost = pd.to_numeric(df["purchase_cost_nzd"], errors="coerce")
        type_medians = cost.groupby(df["asset_type"]).transform("median")
        outlier_mask = cost > (type_medians * 3)
        cost_outliers = int(outlier_mask.sum())
        outlier_df = df[outlier_mask]

    return {
        "total": total,
        "completeness": completeness,
        "blank_counts": blank_counts,
        "duplicate_serials": dup_serials,
        "duplicate_rows": dup_rows,
        "future_purchase_dates": future_purchase,
        "warranty_before_purchase": warranty_before_purchase,
        "cost_outliers": cost_outliers,
        "cost_outlier_rows": outlier_df,
    }