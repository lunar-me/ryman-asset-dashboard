# Ryman IT Asset Management Dashboard

A Streamlit dashboard demonstrating the analytical work of an **Asset Management Analyst** — managing the full lifecycle of technology assets across Ryman villages in New Zealand and Australia.

## Features

- **7 pages**: Executive Overview, Asset Inventory, Data Quality & Anomalies, Missing/Unassigned/Under-utilised, Lifecycle & Refresh, Cost Savings & Forecasting, Compliance & Risk
- **Dual data mode**: Supabase (primary) with automatic local CSV fallback
- **Global filters**: asset type, location, lifecycle stage, install status, purchase date range, utilisation threshold, stale threshold
- **Export**: every major table downloadable as CSV
- **Role-first design**: every page links to the Asset Management Analyst responsibility it supports

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Configure Supabase credentials
#    Create a .env file (or set env vars):
#    SUPABASE_URL=https://xxxx.supabase.co
#    SUPABASE_SERVICE_ROLE_KEY=eyJ...
#    SUPABASE_TABLE=ryman_assets

# 3. Ensure a local CSV exists (fallback data source)
#    ryman_assets.csv  (15,000 rows × 37 columns)

# 4. Launch
streamlit run streamlit_app.py
```

## Data Sources

| Source | When it's used |
|--------|----------------|
| **Supabase** (`ryman_assets` table) | When `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are valid |
| **Local CSV** (`ryman_assets.csv`) | Automatic fallback when Supabase unavailable or credentials missing |

The data source is shown in the sidebar ("Source: Supabase" / "Source: Local CSV").

## Data

The dataset is fully **synthetic** — no real Ryman Healthcare data. It mimics a ServiceNow `alm_hardware` export with 37 columns and deliberate data-quality anomalies (~10%) to support anomaly-detection demos.

## Project Structure

```text
ryman-asset-dashboard/
├── streamlit_app.py              # Entry point / Home
├── pages/
│   ├── 1_Executive_Overview.py
│   ├── 2_Asset_Inventory.py
│   ├── 3_Data_Quality_&_Anomalies.py
│   ├── 4_Missing_Unassigned_Underutilised.py
│   ├── 5_Lifecycle_&_Refresh.py
│   ├── 6_Cost_Savings_&_Forecasting.py
│   └── 7_Compliance_&_Risk.py
├── utils/
│   ├── data_loader.py            # Supabase + CSV loading, caching
│   ├── metrics.py                # Derived flags, KPIs, business rules
│   ├── charts.py                 # Reusable Plotly helpers
│   └── filters.py                # Sidebar filter widgets + state
├── .streamlit/config.toml        # Theme, wide mode
├── requirements.txt
├── .env                          # Supabase credentials (local only)
├── ryman_assets.csv              # Fallback local data
└── docs/                         # Design specifications
```

## Business Rules (v1)

| Concept | Rule |
|---------|------|
| Unassigned | `assigned_to` is null/blank |
| Missing | `install_status == "Missing"` |
| Under-utilised | `utilisation_score < threshold` (default 30) |
| Stale | `days_since_last_seen > threshold` (default 90) |
| Reclaim candidate | Unassigned OR Missing OR (Under-utilised AND In Use/Installed) |
| Opportunity value | Residual where available; else 40% missing, 25% unassigned, 15% under-utilised |

## Deployment

**Streamlit Community Cloud:** set the same env vars in app secrets:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_TABLE`

The app will load from Supabase automatically.

## Documentation

Full specifications in `docs/`:
- `STREAMLIT_DASHBOARD_SPEC.md` — source-of-truth spec (pages, data contract, success criteria)
- `DASHBOARD_METRICS_AND_FILTERS.md` — metrics, filters, business rules reference
- `DASHBOARD_PROJECT_STRUCTURE.md` — project structure & runbook