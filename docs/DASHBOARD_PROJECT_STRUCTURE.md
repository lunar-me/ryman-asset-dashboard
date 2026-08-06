# Recommended Streamlit Project Structure & Runbook

This document tells the future implementer how to organise the codebase and how a user should run the finished dashboard.

---

## 1. Suggested Repository Layout

```text
ryman-itam-dashboard/                 # new repo or folder
├── streamlit_app.py                  # entry point (or Home.py)
├── pages/
│   ├── 1_Executive_Overview.py
│   ├── 2_Asset_Inventory.py
│   ├── 3_Data_Quality_&_Anomalies.py
│   ├── 4_Missing_Unassigned_Underutilised.py
│   ├── 5_Lifecycle_&_Refresh.py
│   ├── 6_Cost_Savings_&_Forecasting.py
│   └── 7_Compliance_&_Risk.py
├── utils/
│   ├── __init__.py
│   ├── data_loader.py                # CSV + Supabase loading, caching
│   ├── metrics.py                    # derived flags, KPIs, business rules
│   ├── charts.py                     # reusable Plotly/Altair helpers
│   └── filters.py                    # sidebar filter widgets + state
├── data/
│   └── ryman_assets.csv              # sample / default local file (optional)
├── .streamlit/
│   └── config.toml                   # theme, wide mode, etc.
├── requirements.txt
├── .env.example                      # SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
├── README.md                         # how to run the dashboard
└── docs/                             # copy or link the design docs
    ├── STREAMLIT_DASHBOARD_SPEC.md
    ├── DASHBOARD_METRICS_AND_FILTERS.md
    └── DASHBOARD_PROJECT_STRUCTURE.md
```

Keep the design documents in `docs/` so the specification travels with the code.

---

## 2. Data Loading Contract (`utils/data_loader.py`)

Responsibilities:

1. Try Supabase when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` exist.
2. Fall back to local CSV path (default `ryman_assets.csv` or path from env / sidebar).
3. Return `(dataframe, source_label, last_loaded_timestamp)`.
4. Use `@st.cache_data` (with a sensible ttl or manual clear).
5. Ensure column dtypes are sensible (dates parsed, booleans correct).
6. Never raise an unhandled error that crashes the whole app; show a clear message instead.

---

## 3. Metrics Contract (`utils/metrics.py`)

All derived columns and KPI calculations live here.

- Input: raw DataFrame + threshold parameters  
- Output: DataFrame with extra boolean/numeric columns, plus helper functions that return scalar KPIs or grouped summaries  

Pages must **not** re-implement `is_unassigned`, under-utilised logic, etc. They call the shared functions. This guarantees consistent numbers across the app.

---

## 4. Filter State

- Prefer Streamlit widgets in a shared sidebar function.
- Persist selected filters in `st.session_state` if cross-page consistency is required.
- Provide a “Reset filters” control.

---

## 5. How a User Runs the Dashboard

```bash
# 1. Clone / open the project
cd ryman-itam-dashboard

# 2. Install
pip install -r requirements.txt

# 3. (Optional) point at Supabase
export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJ..."

# 4. Ensure a local CSV exists if not using Supabase
#    (copy from the generator project or generate fresh)
python /path/to/ryman-asset-generator.py --output data/ryman_assets.csv

# 5. Launch
streamlit run streamlit_app.py
```

On Streamlit Community Cloud the same env vars are set in the app secrets.

---

## 6. Minimum Viable Implementation Order

Recommended build sequence so value appears early:

1. `data_loader.py` + basic Home / Executive Overview (KPIs + 2–3 charts)
2. Global sidebar filters
3. Missing / Unassigned / Under-utilised page (highest role relevance)
4. Data Quality & Anomalies page
5. Asset Inventory (full table + download)
6. Lifecycle & Refresh
7. Cost Savings & Forecasting
8. Compliance & Risk
9. Polish: insight text, consistent colours, empty states, error handling

---

## 7. Testing Checklist (manual)

- [ ] Loads from CSV when no Supabase credentials
- [ ] Loads from Supabase when credentials present
- [ ] Source indicator shows correct origin
- [ ] Changing utilisation threshold updates under-utilised counts
- [ ] Filters reduce row counts and KPIs correctly
- [ ] CSV download contains only the filtered rows
- [ ] No page crashes on empty filter result
- [ ] Numbers on Executive Overview match detail pages for the same filters

---

## 8. Relationship to the Generator & Upload Scripts

| Artefact | Role |
|----------|------|
| `ryman-asset-generator.py` | Creates the synthetic CSV (source data) |
| `upload_to_supabase.py` | Loads CSV into Supabase `ryman_assets` table |
| This Streamlit app | Reads from CSV **or** Supabase and presents the analytical views |

The dashboard never generates data; it only consumes it.

---

## 9. Definition of Done (reminder)

See section 11 of `STREAMLIT_DASHBOARD_SPEC.md`.  
The implementer should treat that checklist as the acceptance criteria.
