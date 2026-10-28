# Focused workspace repair — 28 October 2026

The requested scope changed to the core application with user-supplied data.
No new government-data acquisition was performed for this repair.

The main application now presents Overview, Settlement map, Priorities, Scenarios
and Service assurance. Imports and access controls are in Data & access. Historical
Census tables, source catalogues and the synthetic sandbox remain optional reference
material, outside the main workflow.

## Concrete fixes

- The map fits supplied settlement geometries and follows the selected record.
  It no longer forces every dataset into the Govandi viewport. Context amenities
  remain clickable above polygon fills.
- Supplied household counts and their source reach scenario inputs. They are no
  longer replaced with null by the frontend adapter.
- Project details use an exact settlement-ID filter. Unmatched projects are not
  displayed as though they belong to the selected settlement.
- Rankings use reviewed, current observations, configurable weights and a paginated
  queue. Missing, old, conflicting or unreviewed inputs remain unranked.
- Dataset preview does not mutate storage. Activation validates the complete file,
  guards against stale previews, persists across restart and retains operational
  records. Retired imports cannot contribute stale indices to the active dataset.
- Due-date updates have their own date input. A complaint against a work record
  inherits that work's service type, rather than the service in an unrelated form.
- Hosted import requests have a bounded larger envelope for the 10 MiB file format;
  the existing smaller limit for other requests remains intact, including chunked
  requests. Source and officer protections remain enabled.

## Checked results

284 Python tests, 20 frontend tests, production build, unused-TypeScript checks
and targeted Python unused checks passed. The actual Chromium/API import workflow
passed six groups with zero JavaScript errors: upload/preview/activation, map and
joins, hand-calculated priority, scenario-to-verification/complaint workflow,
persistence, mobile and offline states. The retained demo passed 25 checks and the
field-form UI passed four groups.

The score fixture is 51 points: .30×80 + .25×60 + .20×40 + .15×20 + .10×10.
The editable scenario fixture totals ₹1,199 and agrees with the API. These are
software fixtures, not service observations or official estimates.

See [the executed receipt](verification/workspace_summary.json) and
[the data contract](https://github.com/vishal88736/nagarseva-seva-first/blob/main/nagarseva/docs/workspace-data.md).
The earlier acquisition report and its validation records remain historical.
