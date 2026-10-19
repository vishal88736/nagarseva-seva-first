# UrbanSaarthi implementation and data-integration results

Completed local engineering and public-source follow-up on **19 October 2026** in
the existing `nagarseva-seva-first` repository. The five-screen application, legacy
backend/model checks, evidence workbench and AWS deployment structure were retained.
Unreachable frontend code was removed; blank dashboard/mobile gaps were tightened.

## 1. Sources accessed and files actually obtained

The final acquisition report checks **248 download receipts covering 247 unique
original files**, all with matching SHA-256 hashes. Most are the **228 public scheme
listing pages**, not 247 independent statistical datasets. The exact URLs, retrieval
times, paths, byte sizes and hashes are in [acquisition_results.json](acquisition_results.json).
The [29-entry inventory](dataset_inventory.csv) has the requested 16 columns and
separates downloaded assets, metadata-only pages and failed services.

| Source | Actual file/result |
|---|---|
| SRA official 2024 cluster register | `data/raw/sra/cluster-list-2024-bd9081d656435571.pdf`, 872,732 bytes, 79 pages; 2,597 rows parsed |
| SRA official 2024 map | `data/raw/sra/cluster-map-document-082b9b1406b91058.pdf`, 7,422,603 bytes; printed IDs and ISO GeoPDF control points parsed |
| SRA public scheme portal | First page `public-projects-679b04a07aa2d7fc.html`, followed by checked `public-projects-page-*.html`; 228 advertised pages reached, 5,677 rows |
| OSM official bounded map API | `data/raw/osm/pilot-map-api-642436ee702273aa.osm`, 12,908,245 bytes; 7,106 processed geometries |
| Census PCA SLUM 6190 | `data/raw/census/table-6190-0-693dc15454e8ad53.xls`, 1,658,368 bytes; 2,645 rows × 88 columns |
| Census housing 11436 | `data/raw/census/table-11436-0-b5bfd408fe469d33.pdf`, 187,584 bytes; 12 Maharashtra cells activated |
| Census household amenities 11448 | `data/raw/census/table-11448-0-14772dbea735ffec.pdf`, 550,962 bytes; 20 Maharashtra cells activated |
| Census drinking water 11443 | `data/raw/census/table-11443-0-8ba15f85577a5d79.pdf`, 249,697 bytes; 44 Maharashtra cells activated |

The Census catalogues and Population Finder, SRA GIS page, OGD catalogue/resource
pages, Geofabrik India and Dataful metadata were also retrieved. The Census server's
missing intermediate certificate was repaired using a pinned public CA certificate
verified against OS roots; TLS and hostname validation remain enabled. That public
certificate is transport metadata, not a statistical observation.

SRA MapServer/FeatureServer and investigated official aliases still timed out. OGD
structured CSV was not obtained; readable HTML does not establish a successful
structured export. Overpass failed, and the bounded official OSM API fallback
succeeded. State GIS failed; Bhuvan returned a loading shell; Copernicus/WorldPop
metadata were readable but no useful additional asset was selected. Kobo/ODK were
investigated as collection platforms, not existing observations.

Raw downloads, large processed files, databases, uploaded evidence and credentials
are excluded from Git and Docker build contexts. See [availability](data_availability.md),
[SRA follow-up](sra_followup.md), [scheme pagination](sra_projects_followup.md) and
[Census source/transport details](census_followup.md).

## 2. Parsed records and available fields

- **SRA register:** 2,597 source rows, 2,596 distinct official `Cluster_ID` values.
  Fields include published name, ward, village/division, taluka, printed area in m²,
  source serial/page and 2024 reference. Preserve 79 missing names, 39 overflowing
  name cells and the two `MW_041` rows; ambiguous IDs do not enter automatic joins.
- **Schemes:** 5,677 rows, 228 pages; scheme, ward, address, CTS, village, developer,
  architect, land type, DCR, proposal and displayed serial. Ten identical-content
  groups comprising 25 rows remain visible. The source gap 99→101 is retained.
  Official stable IDs, current status, observation dates, geometry and settlement
  joins remain null/unknown. Complete means the advertised public pagination ended;
  it does not establish all ongoing/approved schemes. Retrieval spans 18–19 October
  and is not a server-atomic snapshot.
- **OSM:** 7,106 valid, unique, nonempty WGS84 geometries: 2,885 road-category,
  3,692 building-category, 168 amenity-category, 93 transport, 266 residential-context
  and 2 water-infrastructure objects. Original IDs, tags, nullable names, edit times,
  clipping flags and source URLs are retained. Tag objects are not deduplicated
  operational facilities or proof of reliable household service.
- **Census:** the full PCA workbook and 88 fields are preserved. The application
  imports 190 original Maharashtra units (1 state + 189 towns) and **456 historical
  observations: 452 numbers and four missing values**. These are 380 PCA population/
  household counts, 12 housing cells, 44 water cells and 20 household-amenity cells.
  Every reference year remains **2011**; none is allocated to a settlement.
- **Historical raster:** a 1024×1083 EPSG:3857 PNG covers the Govandi pilot bounds.
  The original PDF has georeferencing but rasterized map contents, not extractable
  cluster feature vectors. Four controls have about 0.148 m internal fit residual;
  this is not ground accuracy. The overlay is **display-only** and supplies **zero
  analytical settlement polygons**.

PCA and Houselisting have different universes: Maharashtra household denominators
are respectively 2,499,948 and 2,449,530. They are not interchanged. The exact Census
label `Greater Mumbai (M Corp.) (Part)` and original code `27:802794` are retained;
its 2011 totals do not establish a present municipal boundary or current households.

## 3. Defensible joins and current missing indicators

All **156 printed M/E map tokens match unique register IDs** exactly. This is an
identifier/provenance link, not a spatial boundary reconstruction. The original
Census state/town keys link tables only at their reviewed original geography and
reference year, with table-specific universes retained.

A separate QA join uniquely contains 55 of 263 OSM amenity/transport/water objects
inside mapped residential polygons; 208 are unmatched/ambiguous. This is context
only, with no slum membership or household-statistics allocation.

There is **no reliable scheme-to-settlement or Census-to-cluster crosswalk**.
Current settlement-level W/S/H/A/R indices, household denominators, service uptime,
facility capacity and measured route origins remain unavailable. Real records stay
unranked; missing indicators are null. See [quality](data_quality_report.md) and
[join strategy](join_strategy.md).

## 4. Functional application, storage and pipeline

Acquired mode is the default. All source records load through bounded pagination.
The five screens provide provenance/freshness metrics, OSM vectors and historical
SRA raster, register/scheme search, historical Census context/CSV, transparent
configurable priority calculations, hypothetical scenario comparison and protected
service assurance. The explicitly selected synthetic sandbox remains separate.

SQLite migrations retain source/geography/indicator/project/spatial tables and
independent intervention/evidence/verification/complaint/survey records. Source
refresh validates row flags, IDs, CRS, geometry bounds, references and counts before
activation; rejected refreshes preserve operational records and the prior snapshot.
Historical facts are immutable by source observation ID. Public observations redact
inspector, reviewer and evidence references. Source CSV exports are public;
operational exports require officer access.

Authorized field forms now persist reported visits, retain blank answers as null,
validate timezone/coarse GPS/consented evidence and collect no beneficiary details.
Separately entered deficit indices require a supplied normalization method and
explicit review. No raw reading automatically becomes a deficit or verified service.
Completion, inspection, distinct review and complaint reopening remain separate.

The pipeline is rerunnable with checked caches, immutable originals, request timeouts,
byte/page/record limits, schema/CRS/geometry checks and recorded source failures.
The complete staged runner was executed after the follow-up and passed local
validation while keeping the inaccessible SRA GIS endpoints explicitly failed.

[Safe staging](data_staging.md) creates a deterministic, content-addressed local
bundle containing only the public snapshot/inventory and optional overlay. Final
bundle verification and actual API loading with disposable SQLite confirmed all
counts, historical context and raster availability. [Bundle receipt](verification/public_bundle.json)
and [actual API check](verification/staged_api.json) retain the exact identity and results. No operational database,
credentials, raw originals or field evidence are included.

## 5. Executed verification

- Combined Python checks: **262 passed**, four existing dependency warnings. Includes
  ingestion/failure/schema/CRS/joins, source refresh rollback, public privacy,
  historical geography, priority/scenario/CRUD, packaging, staging, legacy model/API
  and hosted middleware tests. [JUnit](verification/pytest.xml).
- Frontend engine/pagination/CSV checks: **20 passed**. TypeScript unused checks and
  the Vite production build passed.
- Acquired-data Chromium: **10 grouped workflows passed**, zero JavaScript errors,
  including all source pages, Census CSV/context, source raster, raw survey→actual
  disposable API persistence, assurance/review/complaint workflows, mobile and
  offline states. [Browser receipt](verification/browser_results.json).
- Retained synthetic Chromium: **25 checks passed**, zero page errors, using explicit
  isolated ports. Field-form fixture Chromium: **4 groups passed**; these are UI
  contract checks, not real field observations. [Field UI receipt](verification/field_browser.json).
- Actual launcher HTTP/proxy checks and owned-process cleanup passed; configurable
  ports leave existing listeners untouched. Portable public bundle rerun, transfer
  verification and disposable API loading passed.
- GitHub workflows passed for application push `c84bcc1`:
  [container readiness](https://github.com/vishal88736/nagarseva-seva-first/actions/runs/39209217898)
  and [application validation](https://github.com/vishal88736/nagarseva-seva-first/actions/runs/39209217806).
  These exercised Docker image build, HTTP/auth/upload/restart persistence,
  restrictive-permission recovery and the regular application checks. The generated
  [CI receipt](../integration/ci-validation.json) distinguishes the pinned imported
  upstream revision (`upstream_source_commit`, with legacy `source_commit` scoped
  to that import), `validated_checkout_commit` and `triggering_commit`. The checked
  checkout can include workflow-generated changes after the trigger. Subsequent
  CI-receipt changes receive their own application checks before delivery.

Local Docker CLI access remains blocked by socket permissions; the remote GitHub
runner performed container checks. No public AWS URL, real officer identity,
independent ranking accuracy, agency adoption or field impact is claimed.

## 6. Run and deploy the prepared application

```bash
cd "/home/vishal/D DRIVE/seva first/nagarseva-seva-first"
bash start-local.sh
```

Default app: `http://localhost:5173`; API docs: `http://localhost:8000/docs`.
If those ports belong to an existing session, use explicit unused ports:

```bash
URBANSAARTHI_API_PORT=8001 URBANSAARTHI_WEB_PORT=5174 bash start-local.sh
```

That example serves `http://localhost:5174` and `http://localhost:8001/docs` and sets
the Vite proxy correctly. Set a private `NAGARSEVA_OFFICER_KEY` in the API environment
and enter it through Officer access for operational forms. Optional consented local
uploads require `URBANSAARTHI_EVIDENCE_STORAGE=sqlite`. Shared keys are prototype
access control, not government identity/RBAC. [Runtime details](local_runtime.md).

Fresh-checkout dependencies, ingestion, environment and test commands are in the
[root README](../README.md). Database initialization/migration is automatic. Rebuild
public inputs and restart the API to refresh sources; retain the operational database.

For a server, prepare and verify the local bundle, mount its `processed` and
`metadata` subdirectories read-only beside the existing writable database volume,
and set `URBANSAARTHI_DATA_DIR=/data/processed`. [Staging instructions](data_staging.md)
and the [existing AWS guide](../deploy/aws/README.md) give paths/checks. This task did
not alter AWS resources, publish source-restricted assets or deploy a public site.

## 7. Remaining external requirements

Still unavailable: authoritative analytical cluster/project polygons and live GIS
schemas, dated official project status/keys, original-boundary crosswalks, current
verified settlement/household service measurements, actual household denominators,
route origins and official cost/engineering/resident feasibility evidence. These
require accessible government exports or an authorized field workflow; values and
boundaries were not fabricated to fill them.

Optional production work remains: real identity/roles, a managed evidence store,
PostGIS when scale requires it, account-level Kobo/ODK synchronization, agency
workflow acceptance and independent field validation. These are not described as
working integrations. Wider source redistribution needs source-specific reuse review.

Cleanup removed 26 unreachable frontend files and unused chart dependencies without
removing tests or retained backend/workbench functionality. The layout changes keep
long tables scrollable and remove forced map height/stretched cards. [Cleanup evidence](cleanup.md).
