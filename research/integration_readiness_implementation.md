# UrbanSaarthi integration readiness — implementation report

Validated locally on 2026-10-29T17:24:00.393715+00:00. Challenge context: **SEVAMO96**, General Category, Urban Development; affordable housing, slum redevelopment and basic-service assurance.

## Result

`/data-integration` is a working English, Hindi and Marathi section within the existing light civic interface. It includes five capability cards, a seven-category readiness matrix, a six-step real file-onboarding flow, an eight-step proposed roadmap, and privacy/governance information. Capability support is distinguished from evidence of an actual connection.

The inspected checkout contained the earlier historical/acquired-data UI and a separate small sandbox, rather than the requested shared 100-settlement prototype. This continuation preserved React, routing conventions, Leaflet, FastAPI, SQLite, localization, the supplied civic styling and logo, existing API compatibility, and all prior uncommitted work. A centralized synthetic adapter now supplies the active application. No extra library was installed and no dependency/lockfile changed.

## Active data and persistence

| Entity | Actual default count |
| --- | ---: |
| settlements | 100 |
| wards | 24 |
| issues | 60 |
| projects | 20 |
| milestones | 40 |
| visits | 30 |
| assessments | 0 |
| feedback | 0 |
| dataSources | 4 |
| activity | 1 |

The one activity event is actual workspace initialization, not a fabricated citizen report. Fixed-seed scenario records do not receive fake operation histories. Counts above were read from the running local API; real-data readiness currently has seven `not_provided` states and zero controlled imports.

The existing SQLite store has additive `civic_demo_workspace`, `civic_demo_operations` and `civic_demo_attachments` tables. Mutations use transactions, optimistic revisions and idempotency keys. All pages consume the same snapshot; no localStorage reporting substitute or competing per-page fixtures were added. The original operational records are not deleted or mixed with synthetic records. Language uses the existing browser preference; the administrator key is session-only.

## Working prototype workflows

- Dashboard metrics, household-weighted six-service coverage, issue/project breakdowns and genuine activity derive from the shared collections.
- Settlement directory combines search, ward/risk/redevelopment/service-gap filters, sorting and real pagination. Polygon/list selection shares stable IDs and brings the corresponding table page into view. The map has pan/zoom, fit, hover, visibility, explicit illustrative-geometry labels and an optional basemap fallback.
- Settlement details expose synthetic housing and service estimates, configurable demo targets, explicit gap calculations, issue/project links, visit history and feedback. Missing values remain unavailable. Applied inspection findings have before/after history; completing a visit alone does not alter indicators.
- Issues support accessible field-level validation, SQLite submission, optional bounded consented private image attachments when enabled, filters, server-authorized status transitions, assignment and follow-up history. Project completion does not resolve complaints.
- Projects support search/filter/sort/pagination, creation and updates, timelines, fictional budgets, milestone creation/edit/status/completion dates, overdue display and separate reported progress vs stored milestone counts.
- Site visits can be scheduled, edited, cancelled or completed. Findings are recorded separately and require explicit authorized application to indicators. Housing assessments and anonymous community feedback use the same persistent service layer.
- Six report types export actual filtered records as real CSV downloads with a synthetic-data notice and spreadsheet-formula protection. Demo data management supports JSON export, validation, settings and confirmed scoped reset. Reset preserves controlled imports and unrelated data.
- Existing scenario comparison is retained with records derived from the same synthetic settlements. Historical source-specific components and API behavior remain available as archival compatibility code, disconnected from the active UI.

These are persisted backend workflows, not merely frontend success states. Administrative operations require the configured server key. The default running server has no administrator key and photo storage disabled; those dependencies are visibly explained. Public issue, visit and feedback creation remain available.

## Implemented onboarding

**Actually supported:** UTF-8 comma-delimited CSV (BOM, quoted commas and multiline cells) and GeoJSON FeatureCollection in `.geojson`/`.json`. File limits are 5 MiB, 5,000 records, 100 fields and bounded coordinate/error counts. KML, shapefile, XLSX and PDF imports are described as future capabilities only.

1. Selecting a file reads browser memory. A permission/minimization attestation is required before it is sent to this backend. Inspection and validation do not persist an upload.
2. Actual metadata includes filename, byte count, detected format, SHA-256, source columns/properties, record/feature count, geometry bounds and genuine timestamps. No placeholder preview is used.
3. Suggestions appear only for fields present in the selected source. Users can change the actual mapping. No settlement ID, row-order join or geographic crosswalk is invented.
4. Validation checks required mappings/values, duplicates, field types, finite numbers, integer/nonnegative counts, 0–100 percentages, workflow enums, ISO dates/timezones and date order. Geometry checks cover coordinate ranges, ring closure, topology, nonempty supported geometry and polygon requirements. Present geometry is checked even if unmapped. Legacy CRS declarations fail; explicit WGS84 confirmation is required. There is no automatic CRS identification or reprojection.
5. A transformed preview and actual change count precede import. Related datasets must select an existing controlled settlement batch and use exact source IDs; they cannot be attached to demo settlements by assumed matching.
6. Explicit confirmation, provenance fields and the existing officer-key check are required to commit a batch. Original bytes, mapped records, hash, source information, mapping and actual validation/save timestamps are stored in `civic_import_batches`. Exact retries are idempotent; conflicting duplicate IDs are rejected without replacement.

Original and mapped-record retrieval is private. Public readiness exposes only category/count/status. Responses are checked structurally so a malformed HTTP-success response cannot confirm a save. A successful batch has `stored:true`, `active:false`, `sourceVerified:false`. Source URLs are metadata only and are never fetched.

**The imports genuinely work in the local SQLite import store, but do not activate those records in the settlement/project UI or establish a government connection.** The browser acceptance run imported both synthetic CSV and synthetic GeoJSON software fixtures, downloaded identical original bytes, verified refresh persistence, and proved the active demo remained at 100 settlements. All acceptance mutations occurred in disposable databases, not the user workspace.

## Calculations and validation boundaries

Aggregate coverage is `sum(households × known settlement coverage) / sum(households with known coverage)`. Missing coverage is excluded from both numerator and denominator. A settlement gap is `max(0, demo target − coverage)` in percentage points. Demo prioritization normalizes configured weights across mean six-service gap, highest unresolved priority, capped unresolved count and capped oldest unresolved age; factors and contributions are shown. Targets and scores are demonstration assumptions, not government standards or validated risk models.

Dates are stored as UTC timestamps where events occur; planned calendar dates and display/report filters use the Asia/Kolkata convention. Source dates and source values are retained. Schema consistency does not establish authenticity, lawful use, geographic accuracy or current real-world service coverage.

## Old integration disconnected

- `App.tsx` enters the new civic workspace; the original GeoJSON/KML hooks are not part of the active application graph.
- The default API source directory is inactive unless an operator explicitly opts into a legacy source-reader configuration; the active adapter is independently synthetic.
- Obsolete reference-layer configuration is removed from active environment examples. Original GIS files, conversion/research tools, source-specific modules and legacy API/test behavior were preserved.
- Browser request monitoring confirms no active request for `mumbai_slum_clusters_2015` or the acquired source snapshot. The dashboard shows the actual 100 synthetic settlements, not the old 2,542 count.

## Executed verification

| Command | Actual result |
| --- | --- |
| `PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest tests nagarseva/tests/test_urban.py nagarseva/model/tests deploy/aws/tests submission/scripts/tests .github/tests -q` | 381 passed; 4 dependency/legacy warnings; 13.94 seconds |
| `npm --prefix nagarseva/website test` | 42 passed; 0 failed |
| `npm --prefix nagarseva/website run lint` | passed; existing script is TypeScript checking, not an ESLint run |
| `nagarseva/website/node_modules/.bin/tsc -p nagarseva/website/tsconfig.app.json --noEmit --noUnusedLocals --noUnusedParameters` | passed; no diagnostics |
| `npm --prefix nagarseva/website run build` | passed; Vite advisory for a roughly 601 kB entry chunk and an existing mixed static/dynamic PlanningPages import |
| `PYTHONPATH=nagarseva nagarseva/.venv/bin/python tests/check_synthetic_integration_browser.py` | passed; production Chromium, disposable SQLite, 12 workflow assertions/groups, zero uncaught page errors |
| `bash start-local.sh` | started successfully on API 8000 and frontend 5173; existing installed dependencies reused |
| `git diff --check` | passed |

The Chromium run covers selection including an off-page polygon, issue save/refresh/status history, milestone creation, visits/cancellation, CSV export, both file formats, manual mapping, missing fields, duplicates, confirmation, original-file retrieval, false-success rejection, three languages across ten main routes, 390px layouts/navigation, reset isolation and backend failure/retry. There were no uncaught page errors. Basemap requests were blocked; real tile-provider availability was not tested.

The running default preview was checked separately without mutating it: seven honest missing-data states, missing administrator configuration, disabled empty-file inspection, translated interfaces and mobile layout. Logs/screenshots are under `.runtime/integration-readiness/`. Structured results are in [integration_readiness_validation.json](verification/integration_readiness_validation.json). Earlier failed test iterations were fixed; results above refer to the final runs.

Python warnings concern existing Starlette/AnyIO and pandas behavior. The build advisory is a bundle-optimization opportunity, not a type/build failure. There is no separate ESLint configuration in this checkout. Older historical/public browser scripts are retained for the disconnected implementation and were not presented as acceptance tests for this UI.

## Production dependencies and remaining limits

- Receive suitable source files and documented ownership/usage authorization; establish definitions, years, measurement dates, geographic granularity and supported identifiers.
- Independently validate authenticity, permissions, CRS and geographic/identifier compatibility. Range checks and an attestation do not prove positional accuracy. Source datasets may lack desired fields.
- Implement and authorize a production adapter activation path, field/enum mappings, crosswalks and workflow comparison tests. Controlled imports currently remain isolated.
- Configure an authorized API/database contract, credentials and synchronization/conflict/update rules for live two-way civic operations. Static CSV, GeoJSON or PDF files cannot provide live synchronization.
- Configure `NAGARSEVA_OFFICER_KEY` for current administrative use; enable `URBANSAARTHI_EVIDENCE_STORAGE=sqlite` only when optional consented demo photo storage is desired. Neither is a production identity or privacy system.
- Add production identity/roles, TLS/access controls, retention/deletion processes, audit access, monitoring and tested backup/restore before handling sensitive real records. No real household data or government connection was used in these checks.
- No new backend technology, external service, real-data activation, production deployment, public-authority approval, field validation or live government-record validation was performed.

## Files created in this continuation

- `nagarseva/website/src/civic/CivicMap.tsx`
- `nagarseva/website/src/civic/CivicProvider.tsx`
- `nagarseva/website/src/civic/CivicWorkspace.tsx`
- `nagarseva/website/src/civic/DemoCommunity.tsx`
- `nagarseva/website/src/civic/DemoDashboard.tsx`
- `nagarseva/website/src/civic/DemoHousing.tsx`
- `nagarseva/website/src/civic/DemoIssues.tsx`
- `nagarseva/website/src/civic/DemoManagement.tsx`
- `nagarseva/website/src/civic/DemoProjects.tsx`
- `nagarseva/website/src/civic/DemoReports.tsx`
- `nagarseva/website/src/civic/DemoServices.tsx`
- `nagarseva/website/src/civic/DemoSettlements.tsx`
- `nagarseva/website/src/civic/DemoVisits.tsx`
- `nagarseva/website/src/civic/adapter.ts`
- `nagarseva/website/src/civic/analytics.ts`
- `nagarseva/website/src/civic/civic.css`
- `nagarseva/website/src/civic/services.ts`
- `nagarseva/website/src/civic/types.ts`
- `nagarseva/website/src/civic/ui.tsx`
- `nagarseva/website/src/integration/DataIntegration.tsx`
- `nagarseva/website/src/integration/adapter.ts`
- `nagarseva/model/api/civic_demo.py`
- `nagarseva/model/api/data_onboarding.py`
- `nagarseva/website/src/i18n/demoMessages.ts`
- `nagarseva/website/src/i18n/integrationMessages.ts`
- `nagarseva/website/tests/civic.test.mjs`
- `nagarseva/website/tests/onboardingAdapter.test.mjs`
- `tests/test_civic_demo.py`
- `tests/test_data_onboarding.py`
- `tests/check_synthetic_integration_browser.py`
- `nagarseva/docs/data-integration.md`
- `research/integration_readiness_implementation.md`
- `research/verification/integration_readiness_validation.json`

## Existing files modified in this continuation

- `.env.example`
- `README.md`
- `deploy/aws/app.py`
- `deploy/aws/tests/test_hosted.py`
- `nagarseva/README.md`
- `nagarseva/docs/product.md`
- `nagarseva/model/api/urban.py`
- `nagarseva/website/index.html`
- `nagarseva/website/src/App.tsx`
- `nagarseva/website/src/i18n/messages.ts`
- `nagarseva/website/src/main.tsx`
- `start-local.sh`

The checkout was already dirty. Other previously changed civic modules, source validation reports, logo assets and tests were preserved; their existing Git status is not claimed as new work here. No commits, pushes, production deployment, source-data deletion or third-party uploads were performed.

Format contracts and operational details are documented in [data-integration.md](../nagarseva/docs/data-integration.md), with primary RFC/Esri/Python references. The roadmap shown in the UI is explicitly proposed work, not completed external integration.
