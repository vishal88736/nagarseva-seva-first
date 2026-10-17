# Synthetic data quality report

> Demo data only; missingness and outliers are intentionally injected.

| Table | Rows | Columns | Missing cells | Duplicate rows |
|---|---:|---:|---:|---:|
| `budget_scenarios.csv` | 5 | 6 | 0 | 0 |
| `grievances.csv` | 20,000 | 8 | 0 | 0 |
| `households_sample.csv` | 10,000 | 8 | 0 | 0 |
| `redevelopment_projects.csv` | 400 | 15 | 0 | 0 |
| `service_access.csv` | 1,500 | 13 | 816 | 0 |
| `slum_pockets.csv` | 1,500 | 23 | 1,287 | 0 |

## Checks

- Identifiers are generated and do not contain resident names, phone numbers or addresses.
- Pocket coordinates are plausible demo locations around the MMR; they are not settlement boundaries.
- Numeric missingness is expected at roughly 3–8% in pocket and service tables.
- Replace this report with source-specific validation before any policy use.
