> Current active UI: the centralized synthetic prototype and controlled onboarding described in [the repository guide](../../README.md). Historical source integration described below is archived and disconnected from the active UI.

# UrbanSaarthi product and data contract

The primary application has four routes:

| Route | Purpose |
| --- | --- |
| `/dashboard` | Dataset coverage, historical map preview, recent self-reported issues and sourced project counts |
| `/settlements` | Independently explore 2015 geometry and search the published 2024 register by name/ID, ward and village |
| `/report-issue` | Save an anonymous prototype issue and retrieve its stable reference |
| `/projects` | Search published project listings, inspect provenance and download reports |

The existing `/projects/data`, `/projects/priorities`, `/projects/scenarios` and
`/projects/assurance` tools remain available as secondary views. Older hash links
remain accepted. Navigation uses the existing React state and the browser History
API; there is no additional router or competing store. Hosted known-route refreshes
serve the SPA while missing assets and API endpoints retain proper 404 responses.

## Data that is actually connected

The local running workspace is backed by the validated acquired-data snapshot:

- 2,597 source rows from the SRA 2024 register, with no acquired matching polygons.
- 5,677 published SRA project listings. Their count is not an active/completed total;
  missing project phase, dates, costs and beneficiary counts remain unknown.
- 7,106 OSM objects: 2,885 roads, 168 amenities, 93 transport objects, 266 residential
  context features, 3,692 buildings and 2 water-infrastructure features. Mapped
  objects do not prove operation or reliable household access.
- 456 Census observations at their original 2011 geography: one state and 189
  town units. No town/state statistics are assigned to individual clusters.
- A separate unchanged 2015 GeoJSON with 2,542 polygons. Shapely finds 25 invalid
  polygons; the map displays 2,517 without repairing or replacing the source.

All GeoJSON `polyno` values are null. The KML's `SimpleData` attribute was missed by
the supplied converter. No IDs are recovered by row order or presented as SRA IDs.
Polygon selection highlights the historical feature and opens its source-only
panel. Selecting a register entry without geometry does not move the map or imply
that it has a corresponding 2015 polygon.

[The boundary audit](../../research/historical_boundaries_2015.md) records hashes,
source bounds, topology exclusions, unknown retrieval date and licence qualifications.
The 2024 register has one duplicate source ID (two rows), 79 missing names and 39
printed name-column overlap flags. Original values and separate local row identities
are retained. There is no automatic 2015/2024, project, CTS, name or Census join.

## Activation and persistence

`scripts/activate_public_data.py` verifies the existing public bundle contract and
247 distinct raw-source checksums for the current local dataset, preserves a SQLite
backup, mounts immutable source inputs and activates the existing PublicStore.
It refuses to replace a user-imported workspace. Repeating activation with the same
snapshot reuses the receipt rather than generating more backups. Operational records
are retained. No download or external deployment is performed by activation.

The original failure was a running API pointed at an empty input directory. A map
layer could render while all SQL-backed dashboard counts remained empty. Activation
now connects the prepared source tables to the same database used by the application.
The dashboard independently counts validated historical polygons; it never adds
that number to the register count.

## Issue reports

Migration `002_citizen_issues.sql` stores public prototype reports separately from
protected intervention complaints, since a new report need not have any verified
settlement association. It collects no reporter name, phone or beneficiary details.

- `POST /urban/data/issues`: anonymous creation with an `Idempotency-Key` header.
- `GET /urban/data/issues`: paginated public records; optional category/status filters.
- `GET /urban/data/issues/summary`: actual totals and the five latest records.
- `GET /urban/data/issues/{id}`: reload a saved reference.
- `GET /urban/data/issues/report.csv`: available report fields, with formula escaping.
- `PATCH /urban/data/issues/{id}`: existing officer key required for a recorded review.
- `GET /urban/data/issues/{id}/image`: officer key required for private image content.

The browser uses `/api` as its existing same-origin proxy. API documentation is
available at `/docs` on the development API.

Required category, description length, location description, dates, coordinates and uploads are validated
on the server. The report date uses the Mumbai calendar. Coordinates are optional,
paired and limited to three decimal places. Empty coordinates remain null; zero is
accepted only when supplied. Optional consented PNG/JPEG images have a 2 MiB limit,
type/signature checks, private storage and a content hash. The application does not
remove photo metadata; the form explicitly asks users to remove identifying details.
Uploaded images are not public, authenticated field inspections or proof of service.

Duplicate retries with the same request key and payload return the same saved ID.
Reusing a key for different content is an explicit conflict. Success is shown only
after a committed, schema-checked API response; an unexpected HTTP 200 payload cannot
claim success. Failed submissions remain editable. Saved references
survive refresh through the report URL. Statuses are `submitted`, `under_review` and
`resolved`, and never automatically create verified service interventions.

Every report includes `official_submission=false` and `verification_status=self_reported`.
No request is sent to a municipality, SRA or other external authority.

## Language, UI and accessibility

The existing translation provider and formatter are reused. Feature dictionaries are
in `src/i18n/locales/en.ts`, `hi.ts` and `mr.ts`; namespaced keys are merged with the
existing catalog. The language persists in local storage, changes `html.lang`, and
updates forms, native validation messages, statuses, dialogs and map controls without
remounting forms or clearing filters. Original source names and table values retain
their original language. Exports use stable machine-readable source columns.

`product.css` defines scoped surfaces, compact metrics, responsive navigation,
Devanagari font fallbacks and visible focus styles. The project
dialog uses native focus trapping and Escape behavior. The original planning/demo
workflows remain optional; the research archive is retained outside the primary UI.
No new package dependency was added. No live AI, government identity, official case
resolution, validated policy weight or current service baseline is claimed.

### Supplied visual reference

The current 29 October update follows the supplied light civic dashboard: a persistent
left sidebar, teal building mark, pale blue-grey background, white rounded panels,
four overview cards, five dataset-coverage rows, actual report activity, the historical
map and a paginated reference table. The screenshot supplies no application data.

The displayed source total is calculated from the parsed GeoJSON. The map separately
shows the 2,517 displayable features and explains the 25 topology exclusions. The
reference table numbers use original one-based file positions; excluded positions
are not renumbered or converted to official identifiers. The label explicitly explains
its application-generated meaning. Selecting a row or polygon highlights and fits
its actual geometry and displays its original properties, including null values.
Name, ward and SRA-ID search are unavailable for this historical layer. The imported
2024 register retains separate source-supported search and filters.

The source report distinguishes original geometry, extracted SRA records, unmatched
historical Census context, and unverified scheme listings. It exposes genuine source
links and downloads, recorded staging/source timestamps and validator diagnostics.
A staging timestamp is not presented as a new import or field-verification date.

The same light palette applies to all four routes and retained tools. The mobile
sidebar is a drawer with an explicit close action and Escape support. All application
strings use the existing English, Hindi and Marathi resources; original source text
and machine field names remain unchanged. No new dependency was installed.

[`scripts/validate_civic_sources.py`](../../scripts/validate_civic_sources.py) validates
local files without downloads, replacement or import, including reproducing all 79
pages of the saved SRA extraction. Its [current receipt](../../research/verification/civic_sources_validation.json)
records actual inspection time. Geometry/metadata URLs can be configured using
`VITE_REFERENCE_GEOMETRY_URL` and `VITE_REFERENCE_METADATA_URL`; use a matching
checksum-bound pair. Defaults serve the existing single public geometry file.

[The current implementation report](../../research/civic_implementation_report.md)
records changes, evidence, commands, browser verification and outstanding data limits.

## Replacing historical geometry later

Keep the unchanged 2015 files and notices. Put a separately sourced 2024 collection
and its provenance/validation metadata at a new static path. Add a ReferenceLayer
configuration to the existing loader and a distinct layer label. Only introduce
register associations when a verified identifier crosswalk or reviewed geographic
method exists; record its source, method and uncertainty. A new filename, geometry
intersection or equal `polyno` is insufficient evidence for a join.

## Implementation and validation

The main implementation is in the existing `website/src/urban/PublicWorkspace.tsx`
and its `ProductDashboard`, `PublicMap`, `IssueReport` and `ProjectsReports` views.
`routing.ts` defines the four primary paths; `product.css` scopes the light design.
Feature translation dictionaries extend the existing provider. `citizen_issues.py`
and migration `002_citizen_issues.sql` add report persistence to the same SQLite store.
`scripts/activate_public_data.py` connects the verified acquired bundle without
overwriting a user import. No package dependency was added.

Historical validation on 28 October 2026 (superseded by the current report above):

| Check | Actual result |
| --- | --- |
| Full Python suites | 318 passed, four dependency/legacy warnings |
| Frontend unit tests | 30 passed |
| Existing lint, strict unused/type checks, production build | Passed |
| New product browser, both software fixtures and acquired source records | Six groups passed in each run |
| Historical geometry browser | Six groups passed |
| Retained workspace/planning browser | Six groups passed |
| Retained field-entry UI browser | Four groups passed, synthetic API fixtures |
| Retained sandbox browser | 25 checks passed, synthetic demonstration |
| Actual running local app | Four routes and sourced counts checked; ten basemap tiles loaded |

The acquired-data browser run uses the real 2,597 register rows and 5,677 project
listings in a disposable database. Its issue submissions are explicitly software
fixtures. The actual running database was checked read-only and contains no test
issues. These checks establish software behavior, not current field conditions,
official project completion or deployment of the source mount to a public server.
[Commands and machine-readable receipts](../../research/verification/product_validation.json)
record the precise scope. The README contains startup and repeatable validation commands.

## Remaining prototype limits

Shared officer keys are local prototype access controls, not government identity or
production RBAC. Anonymous reporting would need deployment-specific moderation,
abuse controls and a retention policy before a public rollout. Current household
services, official costs and project progress remain unavailable. The local source
activation and container validation do not establish a deployed public site's data
mount. Restricted or unlicensed originals and operational SQLite files are not
committed; a fresh checkout can show the bundled historical map without those files.
