# Acquired-data API and storage

Start `model.api.urban:app`. Interactive OpenAPI: `http://127.0.0.1:8000/docs`.
The frontend proxies `/api` to the same backend in development and preview.

All new routes use `/urban/data`. Existing `/urban` synthetic routes are preserved
with their existing contract and separate record storage. The legacy ML API is
retained for its existing tests/clients; acquired-data mode requires the focused API.

| Method / suffix | Working behaviour |
|---|---|
| GET `/health`, `/overview`, `/metadata` | Database/snapshot availability; source-based counts; full inventory/freshness |
| GET `/settlements` | `search`, `page`, `page_size` (1–1000) |
| GET `/settlements/{id}` | Original provenance, nullable geometry, related observations/projects |
| GET `/spatial` | GeoJSON with `category`, optional WGS84 `bbox=w,s,e,n`, `offset`, `limit` (1–10000) |
| GET `/projects` | Search/pagination, actual acquisition scope/page count/completeness; unknown phases and unmatched schemes retained |
| GET `/context` | Census 2011 observations with their original state/town keys, labels, universes and denominators; no cluster allocation |
| GET `/map-overlay`, `/map-overlay/image` | Optional checksummed, PNG/CRS/provenance-validated 2024 cartographic raster; no analytical polygon claims |
| GET/POST `/geographic-units` | Original geography, source ID, resolution and reference year |
| GET/POST `/indicators` | Nullable observations, original resolution/year/source and review status; immutable IDs |
| POST `/priority` | Optional five weights, checked and normalized; transparent contributions, missingness and no rank without all positive-weight inputs |
| POST `/scenarios/{id}` | Validated editable assumptions; real record ID, hypothetical arithmetic, no unsupported access distances |
| GET/POST `/interventions` | Persistent plans with date/cost/target validation and explicit assumption labels |
| PATCH `/interventions/{id}` | Update an open plan; retain audit history |
| POST `/interventions/{id}/actions` | Start, report completion, request review, reopen; invalid transitions return 409 |
| POST `/interventions/{id}/evidence` | Optional configured SQLite upload, verified file signature/size, metadata and hash |
| POST `/interventions/{id}/evidence-references` | Record an approved HTTPS reference; does not fetch or validate remote content |
| GET `/evidence`, `/evidence/{id}/content` | Authorized inspection metadata/download; binary content omitted from listing |
| GET `/verifications`; POST `/interventions/{id}/verifications` | Immutable outcomes; separate reviewer, recent dated measurement, matching fresh evidence and passing target required for verified status |
| GET/POST `/complaints`; PATCH `/complaints/{id}` | Standalone or intervention-linked reports and responses; filing/reopening disputes verified status |
| GET `/reports/{kind}.csv` | Public priority, settlements, projects, datasets and historical aggregates; protected interventions, complaints and surveys; blank missing cells and escaped spreadsheet formulas |
| GET `/surveys/schema`; GET/POST `/surveys` | Proposed field contract and authorized validated imports; spot measurements remain reported |

Use header `X-Officer-Key` for operational reads/writes and intervention, complaint
and survey exports. Public-source and historical CSV exports require no officer key.
Settlement details and indicator listings redact inspector, reviewer and evidence
references from public observations.
Set `NAGARSEVA_OFFICER_KEY` in the backend environment; never use a `VITE_` variable
for it. Missing configuration returns 503, wrong/missing credentials 401. Public
source endpoints remain readable. Other responses include 201 for creation, 404
for unknown records, 409 for duplicate immutable IDs/invalid workflow transitions,
422 for invalid request fields and 503 when optional upload storage is disabled.
The shared key is a prototype authorization mechanism, not production identity/RBAC.

Default priority weights: water .30, sanitation .25, housing .20, access .15, risk .10.
Only independently reviewed, settlement-resolution `deficit_0_100` observations
within 365 days enter current scoring. This freshness window is an explicit
prototype review rule, not policy. Equally dated contradictory values stay missing.
Physical spot measurements require a documented normalization method; they do not
automatically become deficits. Default-weight CSV from the server and current-weight
CSV from the prioritization screen are distinguished by their exported weights.

SQLite is retained because the existing app already uses it and the bounded pilot
fits locally. Migration `model/api/migrations/001_public_data.sql` adds explicit
source, geography, observation, project, spatial, intervention, evidence, verification,
complaint and survey tables. Foreign keys are enabled on every connection.
Geometry JSON is WGS84, with indexed category/bounding columns and exact Shapely
intersections after bounding-box selection. This is not PostGIS.

At startup, the API validates/imports `URBANSAARTHI_DATA_DIR/urban_real.json` using
a checksum. Every source row is checked for schema, provenance, uniqueness and WGS84
geometry bounds before the transaction activates it. Rejected updates preserve the
previous snapshot and operational records. Unchanged snapshots do not duplicate records. Source refreshes keep
past IDs for operational references and mark active IDs separately; no operational
rows are deleted. An unavailable source mount retains an already imported database
snapshot. A fresh database without a snapshot stays empty; synthetic records are
never substituted into acquired mode. Restart the API after preparing a new source
snapshot. SQLite schemas/migrations are applied automatically without manual SQL.

Verification states: planned → in_progress → reported_complete → awaiting_verification
→ verified or requiring_reinspection. Open/reopened complaints block passing review;
recording a response does not reverify a service. Reinspection needs fresh evidence.
Recorded actor references/evidence are user claims; authentication of distinct people,
actual evidence content, engineering safety and continuous uptime remain unvalidated.

Evidence uses SQLite only when `URBANSAARTHI_EVIDENCE_STORAGE=sqlite`. Files are
nonempty PNG/JPEG/PDF/UTF-8 text up to 2 MiB, downloaded as attachments with no-store
and nosniff. This bounded prototype store does not provide a retention service,
object-store integration, malware scanning or a government evidence repository.

Published Census imports are immutable by source observation ID. Retrieval-time-only
changes do not replace original observations. Corrected source facts require versioned
IDs; earlier originals remain available and active context selects the current source
snapshot. Source restoration follows import timestamps, not first-insert row order.
Current-observation selection compares timezone-aware instants, including conflicts
expressed in different timezone offsets.

The optional Service Assurance field forms submit raw surveys as `reported`, retain
blank measurements as null, require coarse paired GPS and consented evidence, and
collect no personal beneficiary fields. A separate deficit-index form requires an
explicit user-supplied method, value, source/evidence and review acknowledgement. It
does not derive deficit scores from raw visits. Field-reviewed references are user
records, not authenticated government identities.

For acquired mode on a server, use [the validated local staging workflow](../../research/data_staging.md).
The public image route serves only the fixed prepared source image after validation;
it accepts no arbitrary filesystem path or remote fetch target. The image layer
reference year comes from the validated source, and control-fit residual is not
ground accuracy.
