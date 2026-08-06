"""
Data loading module for the Ryman IT Asset Management Dashboard.

Handles dual-mode data loading:
  1. Supabase (primary, when credentials are valid)
  2. Local CSV fallback (when Supabase unavailable or CSV specified)

Returns a clean pandas DataFrame plus source metadata.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Tuple

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_env_file(path: str = ".env") -> dict:
    """Load .env file directly (handles UTF-8 BOM)."""
    env: dict = {}
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _get_env(name: str, default: str = "") -> str:
    """Get env var, checking process env first then .env file."""
    val = os.getenv(name, "")
    if not val:
        val = _load_env_file().get(name, "")
    return val or default


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply dtype normalisation and cleanup so the app always gets
    a consistent DataFrame regardless of source (CSV or Supabase).
    """
    df = df.copy()

    # Parse date columns
    date_cols = [
        "purchase_date",
        "warranty_expiration",
        "planned_refresh_date",
        "disposal_date",
        "last_discovered",
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Numeric coercion
    num_cols = [
        "purchase_cost_nzd",
        "days_since_last_seen",
        "utilisation_score",
        "useful_life_years",
        "remaining_life_years",
        "residual_value_nzd",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Boolean coercion
    if "is_non_compliant" in df.columns:
        df["is_non_compliant"] = df["is_non_compliant"].astype(bool)

    # Normalise blank strings to NaN for text fields we care about
    text_cols = [
        "assigned_to",
        "location",
        "serial_number",
        "model",
        "manufacturer",
        "ci_name",
        "po_number",
        "notes",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].replace("", pd.NA).replace(r"^\s*$", pd.NA, regex=True)

    # Fill string categorical fields with 'Unknown' where blank to avoid UI gaps
    cat_cols = [
        "asset_type",
        "install_status",
        "state",
        "lifecycle_stage",
        "department",
        "encryption_status",
        "os_supported",
        "warranty_status",
    ]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)

    return df


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Loading asset data…")
def _load_from_supabase() -> pd.DataFrame:
    """Load full dataset from Supabase via the REST API."""
    url = _get_env("SUPABASE_URL", "").rstrip("/")
    key = _get_env("SUPABASE_SERVICE_ROLE_KEY", "")
    table = _get_env("SUPABASE_TABLE", "ryman_assets")

    if not url or not key:
        raise RuntimeError("Supabase credentials not configured")

    import requests

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "count=exact",
    }

    # First get total count to know pagination range
    count_resp = requests.get(
        f"{url}/rest/v1/{table}?select=sys_id",
        headers={**headers, "Range": "0-0"},
        timeout=30,
    )
    if count_resp.status_code not in (200, 206):
        raise RuntimeError(
            f"Supabase request failed (HTTP {count_resp.status_code}): "
            f"{count_resp.text[:300]}"
        )

    total = 0
    cr = count_resp.headers.get("content-range", "0-0/0")
    try:
        total = int(cr.split("/")[-1])
    except (ValueError, IndexError):
        total = 0

    if total == 0:
        return pd.DataFrame()

    # Fetch in pages of 1000 (PostgREST max is 1000)
    all_rows = []
    page_size = 1000
    for start in range(0, total, page_size):
        end = min(start + page_size - 1, total - 1)
        resp = requests.get(
            f"{url}/rest/v1/{table}?select=*",
            headers={**headers, "Range": f"{start}-{end}"},
            timeout=60,
        )
        if resp.status_code not in (200, 206):
            raise RuntimeError(
                f"Supabase page request failed (HTTP {resp.status_code}): "
                f"{resp.text[:300]}"
            )
        all_rows.extend(resp.json())

    return pd.DataFrame(all_rows)


@st.cache_data(show_spinner="Loading asset data…")
def _load_from_csv(csv_path: str) -> pd.DataFrame:
    """Load dataset from a local CSV file."""
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    return pd.read_csv(p)


def load_data(force_refresh: bool = False) -> Tuple[pd.DataFrame, str, datetime]:
    """
    Load asset data from Supabase (preferred) or local CSV fallback.

    Returns:
        (dataframe, source_label, last_loaded_timestamp)
    """
    if force_refresh:
        # Clear the caches so next call reloads
        _load_from_supabase.clear()
        _load_from_csv.clear()

    now = datetime.now()

    # Try Supabase first
    supabase_configured = bool(
        _get_env("SUPABASE_URL") and _get_env("SUPABASE_SERVICE_ROLE_KEY")
    )

    if supabase_configured:
        try:
            df = _load_from_supabase()
            if len(df) > 0:
                df = _clean_dataframe(df)
                return df, "Supabase", now
            # Empty table — fall through to CSV
        except Exception as e:
            st.warning(f"⚠️ Supabase unavailable ({e}). Falling back to local CSV.")
    else:
        st.info("Supabase credentials not found — using local CSV.")

    # Fallback to CSV
    csv_candidates = [
        _get_env("RYMAN_CSV_PATH", ""),
        "ryman_assets.csv",
        "data/ryman_assets.csv",
    ]
    csv_candidates = [c for c in csv_candidates if c]

    for cand in csv_candidates:
        if Path(cand).exists():
            df = _load_from_csv(cand)
            df = _clean_dataframe(df)
            return df, f"Local CSV ({Path(cand).name})", now

    raise RuntimeError(
        "No data source available. Configure Supabase credentials or "
        "provide ryman_assets.csv."
    )