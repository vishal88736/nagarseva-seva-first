# UrbanSaarthi implementation results

Work executed locally on 18 October 2026 in the existing `nagarseva-seva-first`
checkout. Existing UrbanSaarthi and evidence-workbench functionality was extended.
No remote runtime deployment or agency submission was performed.

## Acquired sources and files

Seven unique originals exist, were parsed, and pass recorded SHA-256 checks.
Exact paths, source URLs, retrieval times, byte sizes and hashes are in
[acquisition_results.json](acquisition_results.json).

| Original under `data/raw` | Result |
|---|---|
| `sra/cluster-map-document-082b9b1406b91058.pdf` | 7,422,603 bytes; one A0 page; text parsed, full map rendered and inspected |
| `sra/public-projects-679b04a07aa2d7fc.html` | 69,041 bytes; expected public listing columns and 25 distinct rows parsed |
| `sra/gis-page-9890a859ea7a1d5b.html` | 42,831 bytes; dynamic HTML context, no feature export obtained |
| `sra/ogd-catalogue-1eee48a33bafd7ac.html` | 1,138,796 bytes; catalogue metadata, no usable structured download in fetched page |
| `osm/pilot-map-api-642436ee702273aa.osm` | 12,908,245 bytes; official bounded OSM XML; filtered/processed geometries validated |
| `osm/geofabrik-india-5ba5a279ab369fd9.html` | 19,150 bytes; extract catalogue, not a country extract |
| `census/dataful-maharashtra-64cf58194ffe4c76.html` | 135,231 bytes; secondary metadata only, no numerical table used |

The SRA GIS endpoints, two Overpass endpoints, all four requested Census catalogues
and Population Finder were also attempted. The GIS service timed out. Overpass
failed, followed by a successful official OSM map-API fallback. Census direct HTTPS
requests failed certificate-chain verification; no numerical Census asset was
downloaded. Kobo/ODK official documentation was inspected for a proposed collection
workflow; no existing observations or platform account was acquired.

Optional portal triage: Maharashtra State GIS timed out, Bhuvan returned a loading
shell, and Copernicus/WorldPop metadata were readable. No asset from these portals
was downloaded, no satellite processing was added, and no gridded population was
assigned to a cluster.

Raw source files and processed snapshots remain local and excluded from Git/Docker
build contexts. Original downloads are content addressed and never overwritten.
The compact inventory/results and reproducible scripts remain reviewable.

## Records, fields and geographic joins

- **156 exact M/E printed map labels:** source ID, title reference 2024, original
  URL/retrieval and missing-data flags. No acquired geometry, official settlement
  name, household count or current service observation. This is a text extract,
  not a complete authoritative settlement register.
- **25 SRA first-page scheme rows:** scheme name, ward, address, CTS, village,
  developer, architect, land type, DCR, proposal and displayed row number. All have
  unknown current status and source date; no official stable scheme key was found.
- **7,106 OSM features/geometries:** 2,885 road-category, 3,692 building-category,
  168 amenity-category, 93 transport, 266 residential-context and 2 water-infrastructure
  objects. Tags, source IDs/URLs, nullable names, edit timestamps and clipping flags
  are preserved. All processed geometries are nonempty, valid and WGS84; IDs unique.
- **0 acquired numerical Census rows; 0 current cluster service observations.**

Original amenity tags include 34 schools, 49 hospitals, 23 clinics, 7 doctors,
18 toilets and 3 drinking-water objects. Mapped presence does not establish facility
operation, reliable water access, capacity or complete coverage. OSM observation
dates remain unknown; timestamps represent edits/retrieval instead.

No reliable SRA scheme-to-settlement or Census-to-cluster join is established.
A context QA join found 55 of 263 amenity/transport/water objects uniquely covered
by an OSM residential polygon; 208 were unmatched or ambiguous. It does not identify
slum membership or allocate population/service statistics. All current five-indicator
scores remain missing/unranked. See the [quality report](data_quality_report.md) and
[join strategy](join_strategy.md) for fields, geography, dates and limitations.

## Functional application and pipeline

The React/TypeScript/Leaflet frontend defaults to acquired mode. It includes a
source/count/freshness dashboard, actual OSM vector layers and tag search, settlement
label search and provenance, published scheme facts, configurable explainable
priorities, CSV export, editable hypothetical scenarios and protected assurance.
The existing synthetic sandbox remains explicitly selectable and separate.

Scenario arithmetic requires a supplied household assumption. Costs, coverage and
disruption are hypothetical. Real settlement-origin/route/destination data are
unavailable, so distance comparisons remain unavailable rather than zero.

The FastAPI/SQLite extension has migrated source/geography/indicator/project/spatial
tables and separate intervention/evidence/verification/complaint/survey tables.
It supports validated listing/detail/spatial/metadata/priority/scenario/report routes,
authorized plan updates and status actions, configured evidence upload/reference
storage, independent review records, complaints and immutable survey imports.
Reported completion and complaint responses never automatically verify a service.

Acquisition scripts have request timeouts, byte/record limits, checked caches,
immutable originals, schema and geometry checks, source failures, ID batching,
CRS transformation support and rerunnable processed snapshots. They discover SRA
layers when available, rather than guessing IDs. The field form/schema/importer
preserve missing answers, timezone and coarse GPS; raw measurements do not become
fabricated 0–100 deficit indices.

Cleanup removed **26 unreachable frontend files**, four orphan source directories,
the unused chart dependency and 38 packages in its dependency tree. The legacy
backend/model tests, directly referenced fixtures, evidence workbench, deployment
code, research, presentation/submission materials and pilot protocols remain.
No tests were removed. The UI spacing follow-up removes forced map height, stretched
overview cards and duplicate spacing; long tables scroll within compact panels.
[Cleanup evidence](cleanup.md).

## Executed verification

The combined Python suite passed **104 tests**: acquisition protocols, failures,
schema/ID/geometry/CRS/joins, new SQLite/API workflows, missing/current/historical
observations, priority/weight/scenario calculations, legacy model/backend tests and
hosted-app middleware tests. Four dependency deprecation/future warnings were emitted.
See [JUnit results](verification/pytest.xml).

Browser-engine tests passed **18/18**, including the hand-worked INR 1,199 scenario,
65-point priority example, missing observations, formulas and workflow state rules.
The TypeScript/Vite production build passed. Unused-import/variable checks and
`git diff --check` were run; current execution summaries are in
[verification/summary.json](verification/summary.json).

The retained synthetic-app Chromium suite passed **25 workflow/responsive checks**.
The separate evidence workbench passed **32 engine tests**, **3 converter tests**,
**10 template checks**, **25 development queries** and standalone packaging checks;
its optional browser script was not run.

Actual system Chromium executed the acquired dashboard/map/filter/empty-state
workflow, priority CSV, scenario-to-plan flow, completion/evidence/independent review,
complaint response/dispute, mode separation and API-offline error state. The test
used a disposable SQLite database with clearly test-only operational records; none
were imported as field evidence. [Browser results](verification/browser_results.json).
Screenshots are retained locally in `.runtime/public-browser/` for visual inspection.

The documented `bash start-local.sh` launcher was also executed. Both processes
started, the API health and acquired overview requests returned HTTP 200, and the
frontend on port 5173 returned HTTP 200. The overview returned 156 source labels,
25 schemes and zero settlements with acquired polygons or sufficient indicators.

Actual Docker image build/container execution was **not run**: the Docker CLI
reported `permission denied while trying to connect to the docker API at
unix:///var/run/docker.sock`. Hosted middleware/unit tests passed; that does not
prove container startup, current AWS deployment or a public URL. No field reliability,
independent ranking accuracy, production identity or government adoption was tested.

## Run the application

In the existing prepared checkout:

```bash
cd "/home/vishal/D DRIVE/seva first/nagarseva-seva-first"
bash start-local.sh
```

Open `http://localhost:5173`; API documentation is `http://127.0.0.1:8000/docs`.
Set `NAGARSEVA_OFFICER_KEY` privately before launching and enter it through Officer
access for assurance writes. Set `URBANSAARTHI_EVIDENCE_STORAGE=sqlite` only when
consented local uploads are intended. Without it, approved evidence references are
supported. [README setup and ingestion commands](../README.md) include fresh-checkout
dependencies, individual stages, safe environment configuration and test commands.

For separate terminals, from `nagarseva`:

```bash
.venv/bin/python -m uvicorn model.api.urban:app --host 127.0.0.1 --port 8000
npm --prefix website run dev
```

SQLite migration and snapshot import are automatic. Source refresh requires preparing
`data/processed/urban_real.json` and restarting the API. Reuse the existing database;
do not discard operational records to refresh public data.

## Deployment and remaining work

Delivery is organized into substantive Git commits for public acquisition, API
workflows, the connected frontend and cleanup, optional field collection, and
documentation/verification. Raw downloads, processed snapshots, local databases
and generated credentials are excluded from these commits.

The existing AWS Dockerfile now includes the new API modules and SQL migration,
retaining the non-root permission repair. Data assets are excluded from the image.
To include acquired mode in an authorized deployment, stage the processed snapshot
and mirrored inventory in the persistent data volume (`/data/processed` and
`/data/metadata/dataset_inventory.csv`), configure the officer secret and optional
evidence storage, build/test the updated image, then follow the existing
[AWS guide](../deploy/aws/README.md). Do not recreate or repin a live stack merely
to view this local implementation. No deployment was performed by this task.

Incomplete due to actual data/service limits: live SRA layer enumeration/export,
georeferenced cluster/project polygons, complete or status-dated scheme records,
downloaded Census numeric tables, official geographic crosswalks, household counts,
current W/S/H/A/R observations, routable cluster origins, official estimates and
engineering/resident feasibility evidence. These are explicitly missing in the app.
PostGIS, production RBAC/identity, an object store, platform account sync, agency
adoption and field validation remain future work, not implemented placeholders.
