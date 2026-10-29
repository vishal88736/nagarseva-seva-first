# Controlled data integration contract

The active adapter is `sqlite-synthetic`. The UI at `/data-integration` explains
capabilities, current evidence-based readiness, onboarding, the proposed roadmap
and governance in English, Hindi and Marathi. No external authority API is connected.

## Adapter boundary

`CivicWorkspace → CivicProvider / domain services → CivicAdapter → sqliteDemoAdapter`

`CivicAdapter` exposes snapshot loading, integration health and transactional commands.
The existing backend `RecordStore` provides SQLite transactions. Its new synthetic
namespace is independent of archived source/API records. UI metrics are derived from
this snapshot, never re-created per page.

`DataIntegration → controlledImportAdapter → /urban/integration/*`

The controlled import adapter is intentionally separate. It validates and stores
supplied files, with no activation path into the synthetic workspace. Future verified
file and authorized API/database adapters must satisfy the domain contract and
resolve source semantics and identifier/geometry compatibility. Schema validation
alone does not establish independent verification or permission.

## Implemented inputs and limits

- UTF-8 CSV, optionally BOM, comma delimiter, consistent headers and quoted multiline
  cells. Reject duplicate/blank headers, inconsistent widths and malformed quoting.
- GeoJSON `FeatureCollection` in `.geojson` or `.json`. Properties must be objects or
  null. No feature-index ID generation. Geographic validation supports Point,
  Polygon and MultiPolygon; boundary records require Polygon or MultiPolygon.
- XLSX (`.xlsx`) visible-sheet selection using read-only openpyxl; no formula
  evaluation. Formula/error cells, macros, external links, unsafe XML and oversized
  archives are rejected. Percentage-formatted fractions are converted to the
  displayed 0–100 units and disclosed in preview. Original bytes stay unchanged.
  Worksheet errors retain actual row numbers. Legacy `.xls` is unsupported.
- Maximum 5 MiB, 5,000 records, 100 fields, 100,000 accepted coordinate positions
  across a file and 50,000 positions in one geometry. Error display is bounded at
  300 entries with the full error count retained.
- Finite WGS84 longitude/latitude only, ranges ±180/±90, correctly closed rings,
  nonempty valid topology checked with the existing Shapely library. No geometry
  repair, coordinate-system detection, reprojection or coordinate-to-ward inference.
  Users must explicitly confirm WGS84. Non-Mumbai extents produce a warning,
  not an invented geographic match. Legacy `crs` declarations fail validation.
- Shapefile bundles, KML and PDF import are proposed future capabilities,
  not implemented parsers. Potential inputs are explained separately from support.

The geographic convention follows [RFC 7946](https://www.rfc-editor.org/rfc/rfc7946).
Potential shapefile components are documented by
[Esri](https://doc.arcgis.com/en/arcgis-online/reference/shapefiles.htm).
CSV parsing uses Python's [standard csv module](https://docs.python.org/3/library/csv.html).

## Field mapping and linked datasets

`GET /urban/integration/schema` is the actual field/type/requirement contract.
Mappings contain internal field → actual source column pairs; available GeoJSON
geometry appears as `@geometry`. Suggestions are conditional on actual columns.
Unmapped original values remain in the retained original file. Canonical workflow
values are checked, not silently inferred or translated during import.

| Category | Minimum mapped values |
| --- | --- |
| Boundaries | stable ID, source name, valid polygon/multipolygon |
| Identifiers/admin mapping | stable ID, source name; optional coordinate pair and admin fields |
| Housing | record ID, settlement ID, household count, assessment date |
| Services | record ID, settlement ID, measurement date, at least one percentage |
| Projects | project ID, settlement ID, project name |
| Issues | issue ID, settlement ID, category, status, creation date/time |
| Visits | visit ID, settlement ID, date, type, status |

Optional values remain unavailable. Invalid numbers, negative counts/budgets,
noninteger counts, percentages outside 0–100, invalid ISO dates, timestamps without
a timezone, reversed dates, unsupported enums and missing values fail validation.
Dates can be ISO calendar dates; full timestamps need an explicit timezone.

Every nonsettlement category requires an explicitly selected stored settlement
batch and exact source IDs. Validation against private batches requires the officer
key. Synthetic IDs, row ordering and `polyno` do not provide a geographic crosswalk.
The import path does not deduplicate or silently repair individual records.

## Actual onboarding and persistence

1. Selecting a file reads browser memory; no permanent upload occurs.
2. A permission and data-minimization attestation permits sending the file only to
   the configured UrbanSaarthi backend for inspection. No third-party processor is used.
3. Inspection reports actual bytes, format, SHA-256, record count, fields, valid
   geographic bounds, errors and conditional mapping suggestions. It does not store files.
4. The user confirms mapping/CRS and validates. Results include actual errors,
   warnings, missing mappings, transformed preview and a real validation timestamp.
5. The user supplies a required source title, publisher/data owner, source date, licence/permitted
   use, HTTP(S) source link and scope; publication year is optional. The user
   explicitly confirms the isolated import. Source URLs are retained only;
   they are never fetched and cannot contain embedded credentials.
6. The server checks authorization, revalidates the exact file and hash, validates
   foreign keys, checks duplicates, and commits original bytes, mapped records,
   mapping, provenance and actual commit timestamp to `civic_import_batches`.

`GET /urban/integration/templates/{category}` downloads actual schema headers
only, without fictional example rows.

A fingerprint makes exact active retries idempotent. A conflicting reused ID in the same
category/settlement batch returns HTTP 409. Replacement is unavailable. Original
files and mapped-record downloads require authorization; public readiness exposes
only category/count/status, not file contents or source details.

Current saved readiness is `not_provided` or `imported_demo`, derived from receipts.
Session evidence distinguishes `file_received`, `validation_failed`,
`validation_passed`, and configuration failures. Labels for future connection states
are defined, but the application does not assert them without a working adapter.
An imported receipt has `stored:true`, `active:false`, `sourceVerified:false`.
Reset of synthetic records does not delete controlled batches.

Confirmed, authorized rollback requires a reason. It marks a batch `rolled_back`,
excludes it from readiness and available reference batches, and retains originals,
mapped records and a timestamped audit history. Dependent imports must be rolled
back first. Rollback is scoped to the selected import and does not reset the city.

Imports are explicitly classified `demo` or `manually_provided`; transformed rows
carry `is_synthetic`. Upload alone cannot establish an `Official` classification.
Completeness is nonempty transformed schema cells divided by all schema cells;
required-field completeness is separate. Neither is a data-quality certification.

## Authorization and production dependencies

`NAGARSEVA_OFFICER_KEY` must be set on the API and match the session key for imports,
private original/record access and synthetic administrative edits. Missing server
configuration returns 503; a missing/wrong client key returns 401. A browser role
selector cannot bypass these checks. Existing key authorization is a demonstration
boundary, not a production user directory, agency identity or RBAC system.

Production use still needs explicit source permission, documented field definitions,
coverage and measurement dates, validated crosswalks, appropriate treatment of
sensitive households/locations, backend adapter activation, end-to-end comparison
against approved records, and operational security. This includes authenticated
roles, TLS, retention/deletion policy, audit access, monitoring, backups and tested
restore. A remote API also needs an authorized contract/credentials, synchronization
and conflict rules, rate-limit/error handling and update schedules. A static PDF or
CSV cannot provide live two-way complaint updates. No production deployment or
external integration was performed by this work.
