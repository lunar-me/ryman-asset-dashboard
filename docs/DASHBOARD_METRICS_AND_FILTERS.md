# Dashboard Metrics, Filters & Business Rules Reference

Companion to `STREAMLIT_DASHBOARD_SPEC.md`.  
Use this as the quick lookup for calculations and filter behaviour.

---

## Global Filters (Sidebar)

| Filter | Type | Default | Applies to |
|--------|------|---------|------------|
| Asset type | Multi-select | All | Most pages |
| Location | Multi-select (or Region → Site) | All | Most pages |
| Lifecycle stage | Multi-select | All | Overview, Inventory, Lifecycle, Cost |
| Install status | Multi-select | All | Inventory, Missing page, etc. |
| Purchase date range | Date range | Full history | Optional on cost/lifecycle pages |
| Utilisation threshold | Slider (0–100) | 30 | Under-utilised logic |
| Stale threshold (days) | Slider | 90 | Stale / last-seen logic |

When a filter is applied, all KPIs, charts and tables on the current page must respect it (unless the page explicitly shows “unfiltered estate” for comparison).

---

## Core Derived Flags

```text
is_unassigned      = assigned_to is null / blank
is_missing         = install_status == "Missing"
is_underutilised   = utilisation_score < utilisation_threshold
is_stale           = days_since_last_seen > stale_threshold
is_reclaim_candidate = is_unassigned OR is_missing OR (is_underutilised AND install_status in ["Installed", "In Use"]-equivalent)
```

Use the source column `is_non_compliant` directly.  
Also expose the underlying `encryption_status` and `os_supported` for transparency.

---

## Recommended KPI Definitions

### Executive Overview

| KPI | Calculation |
|-----|-------------|
| Total assets | `COUNT(*)` |
| Total cost (NZD) | `SUM(purchase_cost_nzd)` |
| Missing or Unassigned % | `(is_missing OR is_unassigned) / total * 100` |
| Non-compliant % | `is_non_compliant / total * 100` |
| Under-utilised % | `is_underutilised / total * 100` |
| Refresh next 12 months | Count where `refresh_year == current_year` OR `remaining_life_years <= 1` OR `lifecycle_stage == "Refresh Due"` |
| Reclaim opportunity value | Sum of opportunity value for reclaim candidates (see heuristic below) |

### Missing / Unassigned / Under-utilised page

| KPI | Calculation |
|-----|-------------|
| Missing count & cost | Filter `is_missing` → count + sum cost |
| Unassigned count & cost | Filter `is_unassigned` → count + sum cost |
| Under-utilised count & cost | Filter `is_underutilised` → count + sum cost |
| Priority list | Sort by cost DESC, then days_since_last_seen DESC |

### Lifecycle & Refresh

| KPI | Calculation |
|-----|-------------|
| Avg age (years) | Mean of asset_age_years (overall and by type) |
| % past useful life | `remaining_life_years <= 0` or age > useful_life_years |
| Refresh volume by year | Group by `refresh_year` |
| Est. refresh cost by year | Count × average recent purchase cost for that asset_type (or overall) |

### Cost & Forecasting

| KPI | Calculation |
|-----|-------------|
| Spend by year | Group purchase_date year → sum cost |
| Problem asset cost | Sum cost where is_missing OR is_unassigned OR is_underutilised |
| Model proliferation | Count distinct models; Pareto of assets by model |
| Residual on retired | Sum `residual_value_nzd` for lifecycle_stage in (Retired, Disposed) |

### Compliance & Risk

| KPI | Calculation |
|-----|-------------|
| Compliance rate | `1 - (is_non_compliant / total)` |
| Encryption disabled | Count where encryption_status == "Disabled" |
| OS unsupported | Count where os_supported == "Unsupported" |
| In-use past warranty | install_status/lifecycle indicates in use AND warranty_status == "Expired" |

---

## Opportunity / Idle Value Heuristic (v1)

Document this clearly in the UI so numbers are not mysterious.

**Suggested simple rule:**

- If `residual_value_nzd` is present and > 0 → use it  
- Else if Missing → 40% of `purchase_cost_nzd`  
- Else if Unassigned → 25% of `purchase_cost_nzd`  
- Else if Under-utilised → 15% of `purchase_cost_nzd`  
- Else → 0  

This is deliberately conservative and transparent. The implementer may expose the percentages as advanced settings later; for v1 hard-code and label them.

---

## Colour Semantics

| Meaning | Suggested colour |
|---------|------------------|
| Critical / Missing / Non-compliant | Red / strong |
| Warning / Under-utilised / Refresh Due / Data quality | Amber / orange |
| Healthy / In Use / Compliant | Green or neutral blue |
| Neutral informational | Grey / Streamlit default |

---

## Export Expectations

Every major table must offer:

- Download current filtered view as CSV  
- Columns that an analyst would send to a village manager or ticketing system (asset_tag, serial, location, assigned_to, status, last_discovered, notes, cost)

---

## Page-to-Role Mapping (quick reference)

| Page | Primary role activities supported |
|------|-----------------------------------|
| Executive Overview | Reporting, decision support, stakeholder communication |
| Asset Inventory | Accurate records, visibility, audit preparation |
| Data Quality & Anomalies | Data management, data quality, process improvement |
| Missing / Unassigned / Under-utilised | Investigation, accountability, maximising value |
| Lifecycle & Refresh | Lifecycle management, refresh programmes, budgeting |
| Cost Savings & Forecasting | Cost analysis, waste reduction, forecasting |
| Compliance & Risk | Governance, compliance, risk reduction |
