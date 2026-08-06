# Ryman Asset Dataset — Metadata

## What's included

The CSV (`ryman_assets.csv`) mimics a typical export from ServiceNow Hardware Asset Management / CMDB (`alm_hardware` / `cmdb_ci_computer`-style fields). It is *fully synthetic* — no real organisation data is used.

## Full column reference

| # | Column | Type | Description |
|---|--------|------|-------------|
| 1 | `sys_id` | string | Unique ServiceNow-style 32-char hex ID |
| 2 | `asset_tag` | string | Ryman-style tag, e.g. `RYM-LAP-100003` |
| 3 | `serial_number` | string | Realistic serial (some blanks + deliberate duplicates) |
| 4 | `ci_name` | string | Configuration item name, e.g. `Dell Latitude 5440` |
| 5 | `model` | string | Device model, e.g. `Latitude 5440` |
| 6 | `manufacturer` | string | Vendor, e.g. `Dell`, `HP`, `Apple`, `Lenovo`, `Samsung` |
| 7 | `asset_type` | string | `Laptop`, `Mobile Phone`, `Tablet`, `Monitor`, `Accessory` |
| 8 | `category` | string | Always `Hardware` |
| 9 | `subcategory` | string | Same as `asset_type` |
| 10 | `install_status` | string | `Installed`, `In Stock`, `In Transit`, `Pending Install`, `Retired`, `Missing`, `In Repair` |
| 11 | `state` | string | `In Use`, `Available`, `In Transit`, `Reserved`, `Retired`, `Lost`, `In Repair` |
| 12 | `lifecycle_stage` | string | `Requested`, `Ordered`, `Received`, `Deployed`, `In Use`, `Refresh Due`, `Retired`, `Disposed` |
| 13 | `assigned_to` | string | Staff name (intentional blanks for unassigned assets) |
| 14 | `location` | string | ~49 Ryman-style villages + Christchurch Head Office (NZ + Australia) |
| 15 | `department` | string | `Clinical`, `Administration`, `Facilities`, `Technology`, `Finance`, `Procurement`, `Village Management`, `Care Services`, `Kitchen`, `Maintenance`, `Reception`, `HR` |
| 16 | `purchase_date` | date | Purchase date (`YYYY-MM-DD`), biased toward recent; occasional future-date anomalies |
| 17 | `purchase_cost_nzd` | float | Cost in NZD; occasional extreme outliers |
| 18 | `po_number` | string | Purchase order, e.g. `PO-2024xxxx` (some blanks) |
| 19 | `cost_center` | string | Cost centre, e.g. `CC-1234` |
| 20 | `warranty_expiration` | date | Warranty end date (`YYYY-MM-DD`); occasional invalid (before purchase) |
| 21 | `warranty_status` | string | `Active`, `Expired`, `Invalid` |
| 22 | `encryption_status` | string | `Enabled`, `Disabled`, `Unknown`, `N/A` (non-computing assets) |
| 23 | `os_supported` | string | `Supported`, `Unsupported`, `Unknown`, `N/A` |
| 24 | `is_non_compliant` | boolean | True if encryption disabled, OS unsupported, or installed-but-unassigned |
| 25 | `last_discovered` | datetime | Last seen timestamp (`YYYY-MM-DD HH:MM:SS`) — for utilisation / stale-asset analysis |
| 26 | `days_since_last_seen` | int | Days since last discovery |
| 27 | `utilisation_score` | int | 0–100 heuristic (higher = more recently seen / active) |
| 28 | `useful_life_years` | int | Typical useful life by asset type (Laptop 4, Tablet 3, Mobile 3, Monitor 5, Accessory 4) |
| 29 | `planned_refresh_date` | date | Planned refresh date (`YYYY-MM-DD`) |
| 30 | `refresh_year` | int | Year of planned refresh (for forecasting) |
| 31 | `remaining_life_years` | float | Years remaining until planned refresh |
| 32 | `disposal_date` | date | Disposal date (only for retired/disposed assets) |
| 33 | `disposal_method` | string | `Secure wipe + resale`, `Secure wipe + recycle`, `Manufacturer return`, `Certified destruction`, `Donation`, `Parts harvest` |
| 34 | `residual_value_nzd` | float | Estimated residual value in NZD (only for retired/disposed assets) |
| 35 | `owned_by` | string | Always `Ryman Healthcare` |
| 36 | `company` | string | Always `Ryman Healthcare Limited` |
| 37 | `notes` | string | Audit / investigation notes (some blanks) |

## Deliberate data-quality anomalies (~10%)

The generator intentionally injects realistic data-quality issues to support anomaly-detection demos:

- **Blank `assigned_to`** (~3.5%) — unassigned / ownership unclear
- **Blank `location`** (~2.2%) — missing location
- **Blank `serial_number`** (~1.8%) — missing serial
- **Duplicate serials** (~1 per 350 rows) — duplicate device records
- **Future `purchase_date`** (~1.2%) — impossible dates
- **`warranty_expiration` before purchase** (~1.0%) — invalid warranty
- **Extreme `purchase_cost_nzd` outliers** (~0.8%) — 4.5–9× normal cost
- **`Missing` install status** (~5%) — lost / stolen assets
- **Low utilisation** — assets with `utilisation_score < 30` for stale-asset analysis
- **Non-compliant assets** — encryption disabled, unsupported OS, or unassigned installed devices

## Usage

```bash
# Regenerate the dataset (default: 15,000 rows, seed 42)
python ryman_asset_generator.py

# Custom row count, seed, and output file
python ryman_asset_generator.py --rows 20000 --seed 123 --output my_assets.csv
```

## License

Synthetic data only — no real organisation data is used. See `LICENSE`.