# Mumbai 2015 reference boundaries

The supplied `mumbai_slum_clusters_2015.geojson` is a **historical display-only
reference**, separate from imported settlements, projects and indicator observations.
It is not a current official boundary layer. The map always displays the required
historical notice in English, Hindi or Marathi, matching the language selector.

## Files inspected and actual validation

The supplied directory contained the original KML, converted GeoJSON, converter and
an OpenCity resource metadata receipt. No additional file was downloaded for this
integration. The original source retrieval date is unknown; filesystem timestamps
are not treated as retrieval or observation dates.

| Check | Actual result |
| --- | --- |
| Original GeoJSON features | 2,542 Polygon features |
| Coordinate positions | 70,404 |
| Longitude bounds | 72.78274625762192–72.97183173366705 |
| Latitude bounds | 18.90863286362999–19.26385248981887 |
| Geometry coordinate system | WGS84 longitude/latitude, EPSG:4326 |
| Source attribute | `polyno` only; **all 2,542 values are null** in the supplied GeoJSON |
| Closed-ring/basic checks | Pass; these alone do not establish polygon validity |
| Shapely topology check | **25 invalid** polygons, including self-intersections and degenerate components |
| Polygons rendered | **2,517**; 25 invalid source polygons excluded without repair |
| GeoJSON SHA-256 | `4c83541ace7197e2193584438c31a9684c91bb4776aa7d94772a4d72e5e5970d` |
| KML SHA-256 | `b4541a74213588ce4294435c9c7a1541af8511de35ecc09930de4a5da8ac76c3` |

The original KML has 2,542 placemarks. Its `polyno` values are in KML `SimpleData`
elements; the supplied converter searches only `Data` elements, explaining the
null GeoJSON values. This integration preserves the supplied GeoJSON exactly and
does not infer or reconstruct those attributes. A popup therefore says the
technical polygon reference is unavailable. Even a supplied `polyno` value would
be a **technical source reference, never an SRA cluster ID**.

The exact static asset is
`nagarseva/website/public/data/mumbai_slum_clusters_2015.geojson` (3,064,224 bytes).
The separate adjacent `.metadata.json` records source attribution, reference year,
SHA-256, exclusions with one-based source feature positions and topology reasons,
CRS, unknown dates, counts, bounds and `analysis_allowed=false`. Raw supplied
KML/GeoJSON/metadata bytes are separately preserved under ignored
`data/raw/sra/boundaries-2015/`, with checksum-addressed filenames.

## Source and reuse qualification

The supplied OpenCity receipt describes a Mumbai slum-cluster map **as of 2015**,
attributed to SRA Mumbai. It gives [this source catalogue entry](https://data.opencity.in/dataset/14d06506-9463-446a-b28f-d2ce0fd0c131/resource/b85ea681-22c8-406d-9fae-8c0bd28387cf)
and labels its resource licence `Public Domain`. That is a catalogue claim, not an
independently verified SRA redistribution licence. The map discloses this distinction.
The catalogue's 2025 modification date is not a boundary observation date.

No boundary is evidence of current slum conditions, housing eligibility,
redevelopment progress, household population or reliable basic-service coverage.

## Existing 2024 and Census files remain separate

The existing 79-page SRA 2024 cluster-list PDF was re-parsed using the repository's
validated word-coordinate extractor: **2,597 rows**, 2,596 distinct `Cluster_ID`
values, one duplicated ID (`MW_041`, two rows), 79 missing names and 39 name cells
with source-column overlap. The existing separate table
`data/processed/sra_cluster_register.json` retains `Cluster_ID`, ward, village,
taluka, source name, printed area and provenance, with **no geometries**. No second
competing table was created. Its raw PDF SHA-256 is
`bd9081d656435571c1299b1d82d2dccbf284f3fe7898643fafa278c442625667`.

The existing processed Census context contains **456 observations**, all for
**2011**, across 190 original geographic units: one state and 189 towns.
There are 78 state observations and 378 town observations, with zero settlement
allocations. These are neither cluster-level nor current measurements.

There is **no 2015-to-2024 or Census-to-polygon join**, including by `polyno`, area,
row position or nearest name. A future match needs verified vector boundaries with
published identifiers, an authoritative crosswalk, or a separately reviewed
geographic method with documented uncertainty.

## Loading and map behavior

`historicalBoundaries.ts` loads the bundled local files with a 20-second timeout,
size limits, UTF-8/JSON checks, validated metadata, SHA-256 verification,
FeatureCollection/count checks and basic geometry checks. Only exclusions tied to
that exact source checksum are applied. Failures are retryable; valid empty data
have an explicit empty state. Successful immutable loads are reused across map
navigation. A future reference layer can supply a new `ReferenceLayer` configuration
and separate metadata; it does not require changing settlement models.

`HistoricalReferenceLayer.tsx` uses the existing React Leaflet installation, subtle
outlines and transparent fill. Initial view fits the dataset extent; users can pan,
zoom, hide/show the layer or restore its extent. Click/keyboard popups contain only
source facts, the historical warning and a technical reference if actually present.
Changing language updates controls and open popups without resetting the viewport,
search or visibility. This layer is available even when the operational API is offline.

## Reproduce

Run from the repository root using the existing data dependencies:

```bash
nagarseva/.venv/bin/python scripts/stage_historical_boundaries.py \
  --source-dir "$HOME/UrbanSaarthi/data/boundaries"
```

Staging is safe to rerun with identical input. Different existing assets or receipts
are rejected instead of silently replaced. No new dependency was added. A fresh
checkout already includes the static files and does not read a home directory at
runtime; local source files are needed only to repeat staging.

```bash
PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest tests/test_historical_boundaries.py -q
npm --prefix nagarseva/website test
npm --prefix nagarseva/website run lint
nagarseva/website/node_modules/.bin/tsc --noEmit --noUnusedLocals --noUnusedParameters \
  -p nagarseva/website/tsconfig.app.json
npm --prefix nagarseva/website run build
CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_historical_boundaries_browser.py
```

Open **Settlement map → Layers → 2015 Reference Boundaries**. Inspection evidence,
service calculations and user-import data remain outside this historical layer.

## Checked implementation files

- `scripts/stage_historical_boundaries.py`: immutable raw preservation and topology QA.
- `website/public/data/` under `nagarseva/`: unchanged GeoJSON and separate source manifest.
- `src/urban/historicalBoundaries.ts`, `HistoricalReferenceLayer.tsx`, `PublicMap.tsx` and
  `LocalizedMapControls.tsx` under the website: loader, presentation and localized map controls.
- `PublicWorkspace.tsx` and existing `urban.css`: map placement, API-independent display
  and responsive source notice, reusing the existing light-themed layout.
- Existing `src/i18n/` and screen localization work: shared English/Hindi/Marathi
  text and preserved application state; source names and records remain unchanged.
- Frontend, staging, browser and hosted/container checks, plus the existing CI workflow.
- README, inventory and geographic-join/quality reports. No dependency or database
  migration was added.

## Actual local validation results

- Full Python suite: **293 passed**, with four existing dependency warnings.
- Frontend suite: **28 passed**. Lint, strict application type checking (including
  unused locals/parameters), production build and diff whitespace checks passed.
- Actual Chromium: **6 historical-layer checks**, 6 existing workspace checks,
  4 field-entry checks and 25 synthetic-sandbox checks passed. New map checks cover
  all three languages, visible polygons, click/keyboard and translated open popups,
  toggle, preserved viewport/search, mobile layout, API-offline access, failed/empty/
  malformed loads, retry, and separation from imported names and statistics.
- A separate read-only check of the running local app rendered 2,517 polygons and
  received HTTP 200 for 15 live OpenStreetMap tile responses. Source extent, local
  screenshots and responsive layouts were inspected. Basemap availability may vary.
- The hosted ASGI wrapper serves the exact static file hash while the settlement
  API stays empty. The existing AWS container workflow now also checks both assets
  and source counts over actual container HTTP. Local ASGI checks do not claim a
  deployed AWS site.

See the [browser receipt](verification/historical_boundaries_browser.json) and
[validation summary](verification/historical_boundaries_validation.json).
