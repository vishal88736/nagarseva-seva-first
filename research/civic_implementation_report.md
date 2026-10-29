# UrbanSaarthi implementation report — 29 October 2026

Implemented in the existing `nagarseva-seva-first` React/TypeScript/Leaflet application and FastAPI/SQLite backend. No package dependencies, replacement architecture, source downloads or source-geometry repairs were introduced. Existing import, planning, scenario and officer-assurance routes remain available.

Local preview: http://localhost:5173/dashboard. API documentation: http://localhost:8000/docs. The documented `bash start-local.sh` started successfully with the already-installed dependencies. Existing servers on 8001/5174 were left running. No public deployment, commit or push was performed.

## Data found and used

| Source | Files / actual state | Evidence limits |
| --- | --- | --- |
| OpenCity 2015 geometry | `nagarseva/website/public/data/mumbai_slum_clusters_2015.geojson` and its checksum-bound metadata | Historical reference only; unchanged original bytes |
| Original OpenCity KML | `data/raw/sra/boundaries-2015/b4541a74213588ce-mumbai_slum_clusters_2015.kml` | 2,542 placemarks; integer `polyno` schema and 2,542 unique technical values; never treated as SRA IDs or copied into GeoJSON |
| SRA 2024 list | `data/raw/sra/cluster-list-2024-bd9081d656435571.pdf`, identical to the supplied parent-folder `data/1731566774802_3204_Slum Cluster 2024 (1).pdf`; `data/processed/sra_cluster_register.json` | All 79 pages re-extracted with the existing Poppler word-coordinate parser; all 2,597 stored rows reproduced exactly. Automated extraction is not manual verification |
| Census 2011 | `data/raw/census/table-6190-0-693dc15454e8ad53.xls`, `data/processed/census_slum_pca_maharashtra.json`, `census_observations.json` | 190 Maharashtra state/town rows; State Code, Town Code, No_HH and person-count fields; 456 observations kept at original geography, without polygon/cluster linkage |
| SRA scheme listings | `data/processed/sra_projects.json` and the existing acquired snapshot | 5,677 published listings, all with unknown project status; no invented progress, budgets, dates, beneficiaries or project-to-polygon matching |
| Issue reports | Existing `citizen_issues` SQLite table and API | Zero records before and after live verification; all test submissions used disposable databases |
| Existing context | Existing OSM/source layers and 2024 raster integration retained | Context/raster display does not establish current service conditions or analytical 2024 geometry |

These were existing local sources and existing imports. This change validates and presents them; it does not claim a new source import. The expected repository-root `data/boundaries/` files are absent: the established public static geometry and archived original KML above are the actual files used. No replacement was downloaded.

The SRA extraction preserves `Cluster_ID`, ward, village/division, taluka, source slum-name text and printed `Shape_Area` in square metres. It retains one duplicate Cluster_ID across two separate source rows, 79 missing names and 39 source name-column overflow flags. No match to the 2015 polygons was attempted.

## Current boundary validation

- FeatureCollection parses; **2,542 Polygon features**; **70,404 coordinate points**.
- Missing geometry: **0**. Unclosed rings: **0**. Available property key: `polyno`, null in every GeoJSON feature. No genuine settlement/SRA identifier is available in this GeoJSON.
- Bounds `[west, south, east, north]`: **[72.78274625762192, 18.90863286362999, 72.97183173366705, 19.26385248981887]**.
- Additional topology finding: **25 invalid polygons**, including self-intersections and insufficient distinct points. **2,517** are displayed; all original 2,542 remain in the unmodified download. Exclusions are visible and inspectable, without repair or silent renumbering.
- SHA-256: `4c83541ace7197e2193584438c31a9684c91bb4776aa7d94772a4d72e5e5970d`.
- Known reference counts/ranges agree with the actual source. Closed rings do not imply valid topology.

[The source-validation receipt](verification/civic_sources_validation.json) records the actual validation time, geometry diagnostics and full SRA extraction reproduction. Browser loads independently check file size, JSON structure, WGS84 coordinates, source counts and SHA-256, and compute bounds/counts from the loaded geometry.

## Completed functionality

- Light civic shell, teal building mark, four persistent desktop navigation links, mobile drawer, active route, skip link, keyboard focus and Escape handling; legacy deep links retained.
- Actual dataset overview, five coverage rows, truthful empty project/issue/activity states and activity derived only from persisted reports.
- Actual historical map: zoom, pan, fit, selected-feature highlighting, source-only popup/detail panel, legend, layer visibility and the required disclaimer in all three languages.
- Paginated historical table, exact numeric/reference lookup, deterministic references tied to original file positions (including gaps for exclusions), real source properties and a clear explanation that references are application-generated. Name, ward and SRA-ID search are unavailable for this layer; separate imported-register filters use actual source fields.
- Issue form: required category, description and location; optional free-text ward and approximate paired coordinates; client/server validation; loading/failure states; idempotent SQLite saving and saved-reference reload. An unexpected HTTP 200 response cannot produce a fake success state. No reporter contact information is collected.
- Optional consented PNG/JPEG handling: 2 MiB limit, type/signature checks, safe filenames and private SQLite attachment access. In the running preview storage is disabled, so a localized unavailable message replaces the uploader. Enabled-storage validation/persistence paths were tested with isolated databases.
- Projects/source listings, genuine details, search/filtering, CSV exports, dataset provenance/status/notes, genuine GeoJSON and metadata downloads, and actual recorded timestamps.
- English, Hindi and Marathi resources for new interface, validation, accessibility and status text. Selection persists through language changes, the language preference persists on reload, and official source values/field names remain unchanged.

No 2015 polygon area is calculated or presented as an official SRA area. The screenshot supplies visual direction only.

## Commands and actual results

Run from the repository root:

| Command | Result |
| --- | --- |
| `nagarseva/.venv/bin/python scripts/validate_civic_sources.py --output research/verification/civic_sources_validation.json` | Passed; existing files inspected, no download/import/replacement |
| `PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest tests nagarseva/tests/test_urban.py nagarseva/model/tests deploy/aws/tests submission/scripts/tests .github/tests -q` | **322 passed**, four dependency/legacy warnings |
| `npm --prefix nagarseva/website test` | **33 passed** |
| `npm --prefix nagarseva/website run lint` | Passed; existing command is a TypeScript alias, not an ESLint check |
| `nagarseva/website/node_modules/.bin/tsc -p nagarseva/website/tsconfig.app.json --noEmit --noUnusedLocals --noUnusedParameters` | Passed |
| `npm --prefix nagarseva/website run build` | Passed; advisory main-chunk size warning (~502 kB) |
| `CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_product_browser.py` | Six groups passed: missing sources, real geometry, pagination, validation/persistence/failures, three languages and 390px layouts |
| `URBANSAARTHI_BROWSER_REAL_DATA=1 CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_product_browser.py` | Same six groups passed against actual acquired source records in disposable SQLite |
| `CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_historical_boundaries_browser.py` | Six groups passed: geometry, translated popups, viewport/filter preservation, offline API, malformed/empty source/retry and separate imported geometry |
| `CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_public_browser.py` | Six retained import/planning/scenario/assurance workflow groups passed |
| `CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_field_collection_browser.py` | Four retained field-form UI groups passed; synthetic API fixtures, not field/backend verification |
| `bash start-local.sh` | API/web/proxy ready on 8000/5173; no installation needed |
| `git diff --check` | Passed |

All browser runs report zero JavaScript page errors. Repeatable browser tests block basemap tiles. A separate read-only Chromium check of the actual running local app captured four desktop routes and Hindi/Marathi mobile views, loaded six live basemap tiles, confirmed required server-side location validation via OpenAPI, and left issue count at zero. This is local software/visual validation, not public deployment or field validation.

[Consolidated validation receipt](verification/civic_implementation_validation.json). Local screenshots/logs are under `.runtime/civic-implementation/`, `.runtime/civic-browser-empty/`, `.runtime/civic-browser-real/` and the existing regression-output directories. The live preview screenshots contain no test complaints.

## Unavailable integrations and configuration

No core backend service, API key or environment value is missing for the local app. Source imports already exist in this workspace. A fresh clone without ignored acquired originals/processed files correctly shows pending/empty source states; the existing activation workflow can load an available validated local bundle.

The following remain unavailable because the evidence/integration is missing: verified current SRA geometry; a verified 2015–2024 crosswalk; polygon-level Census linkage; current service/population/household values for the historical layer; independently verified current project progress; municipal case forwarding and government identity integration. Their UI states do not represent completed integrations.

Optional images require `URBANSAARTHI_EVIDENCE_STORAGE=sqlite` on the backend. Officer operations retain the existing `NAGARSEVA_OFFICER_KEY` requirement. No secrets are sent to frontend build variables. Optional public geometry URLs are configurable through `VITE_REFERENCE_GEOMETRY_URL` and `VITE_REFERENCE_METADATA_URL`; serve a matching unchanged file/metadata pair. No absolute machine path is hardcoded into frontend loading.

Maps, table, provenance and language UI are frontend features backed by actual source files/API data. Issue saving is backend-backed, not browser storage. Missing links/verification are explicitly unavailable states; there is no frontend-only simulated submission or fake integration.

## Design differences

The existing Leaflet/OpenStreetMap basemap is retained rather than reproducing the reference's tile style. The language selector uses the existing accessible select. The five required coverage rows and fuller source caveats take more space than the screenshot. No unsupported ward filter, notification/avatar data, fake record names or decorative project statistics were added. The logo is a code-native teal skyline matching the civic direction rather than a raster crop.

## Files created

```text
nagarseva/website/src/urban/DatasetReports.tsx
nagarseva/website/src/urban/ReferencePolygonDetails.tsx
nagarseva/website/src/urban/ReferencePolygonTable.tsx
nagarseva/website/src/urban/referencePresentation.ts
nagarseva/website/tests/issueClient.test.mjs
research/civic_implementation_report.md
research/verification/civic_implementation_validation.json
research/verification/civic_sources_validation.json
scripts/validate_civic_sources.py
```

## Files modified

```text
.env.example
README.md
nagarseva/docs/product.md
nagarseva/model/api/citizen_issues.py
nagarseva/website/index.html
nagarseva/website/public/urbansaarthi-mark.svg
nagarseva/website/src/i18n/LanguageProvider.tsx
nagarseva/website/src/i18n/locales/en.ts
nagarseva/website/src/i18n/locales/hi.ts
nagarseva/website/src/i18n/locales/mr.ts
nagarseva/website/src/urban/HistoricalReferenceLayer.tsx
nagarseva/website/src/urban/IssueReport.tsx
nagarseva/website/src/urban/ProductDashboard.tsx
nagarseva/website/src/urban/ProjectsReports.tsx
nagarseva/website/src/urban/PublicMap.tsx
nagarseva/website/src/urban/PublicWorkspace.tsx
nagarseva/website/src/urban/historicalBoundaries.ts
nagarseva/website/src/urban/issueClient.ts
nagarseva/website/src/urban/product.css
nagarseva/website/tests/historicalBoundaries.test.mjs
tests/check_historical_boundaries_browser.py
tests/check_product_browser.py
tests/check_public_browser.py
tests/test_citizen_issues.py
```
