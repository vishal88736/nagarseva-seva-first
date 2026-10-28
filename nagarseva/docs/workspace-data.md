# Supply your own workspace data

The main workflow is Overview → Settlement map → Priorities → Scenarios → Service
assurance. Data & access contains setup and import tools. No acquisition pipeline
or government endpoint is required for your own dataset.

## Import in the application

1. Configure `NAGARSEVA_OFFICER_KEY` in the API environment; enter the same private
   value in **Data & access**. Keep it out of frontend environment variables.
2. Download the template. Supply your records, then select the JSON/GeoJSON file.
3. **Validate file** checks IDs, geometry, CRS, observations and project links without
   changing the database. Review the counts and any warnings.
4. **Import validated dataset** activates the file. The map, household counts,
   ranking and scenario inputs update together. An intervening import invalidates
   the preview; validate again before applying it.

Imported data persists in SQLite across API restarts. It takes precedence over the
optional bundled source snapshot. Existing interventions, evidence, complaints and
observations are retained. Use stable settlement IDs for the same settlement;
never reuse an ID for a different place. Changed observation facts require a new
observation ID. Reimporting identical facts is safe.

## Accepted files

Up to **10 MiB**: either a standard GeoJSON `FeatureCollection` of settlements, or a
JSON object with the following fields. CSV is not a direct upload format.

| Field | Contents |
|---|---|
| `title` | Workspace title |
| `source` | Your source/publisher description |
| `source_date` | `YYYY-MM-DD`, or `null` when unknown |
| `settlements` | GeoJSON FeatureCollection, 1–10,000 features |
| `observations` | Optional list, at most 50,000 records |
| `projects` | Optional list, at most 10,000 records |
| `spatial` | Optional GeoJSON FeatureCollection, at most 10,000 context features |

Settlement features use Polygon/MultiPolygon geometry or `null` if unavailable.
Coordinates must be **WGS84 longitude, latitude**. Reproject other CRSs before
uploading. Invalid geometries, duplicate IDs and unsupported declared CRSs are
rejected; the importer does not repair them silently.

Required settlement properties: `id`, `name`. IDs use letters, digits, `:`, `_` or
`-`, up to 100 characters. A top-level GeoJSON feature `id` is also accepted.
Optional properties: `source_id`, `administrative_area`, `households`,
`households_source`, `source`, `source_date`. Household counts must be nonnegative
integers or `null`. They feed the scenario form instead of being discarded.
Missing geometry stays missing; the app does not invent a point or boundary.

## Observations and ranking

Put observations in the `observations` list, not in feature properties.

| Field | Meaning |
|---|---|
| `id` | Optional immutable observation ID; generated if omitted |
| `settlement_id` | Exact settlement ID in this file |
| `indicator_type` | `water`, `sanitation`, `housing`, `access` or `risk` for scoring |
| `value` | Numeric 0–100 deficit index, or `null` |
| `unit` | `deficit_0_100` for scoring |
| `reference_year` | Original observation year |
| `observation_date` | ISO timestamp with timezone, such as `2026-10-28T09:00:00+05:30` |
| `geographic_resolution` | `settlement` |
| `source` | Observation source description |
| `verification_status` | `reported`, `field_verified` or `rejected` |
| `inspector_reference` | Inspector reference; do not supply beneficiary details |
| `method` | Normalization/collection protocol, at least 10 characters |
| `reviewer_reference` | Required for reviewed observations; must differ from inspector |
| `evidence_reference` | Required for reviewed observations |

Use `reported` for unreviewed inputs. Import does not upgrade them to verified.
The prototype's ranking rule uses `field_verified` settlement deficit observations
from the last 365 days. Missing, old, conflicting or unreviewed indices do not
receive a rank. Raw physical readings are not automatically converted to deficits.
Review flags are supplied by your organization; they do not establish government
identity or independent field validation.

Default weights are W 30%, S 25%, H 20%, A 15%, R 10%. They are editable planning
assumptions. Scenarios use editable costs and coverage assumptions, not official
estimates. Route-distance comparisons require a validated origin and network;
the importer does not infer routing from a road drawing.

## Projects and context

Each project requires `id` and `scheme_name`. Supply `settlement_id` only for an
explicit, reliable link; otherwise use `null`. Optional fields: `source_id`,
`project_status` (defaults to `unknown`), `source_url`, `source_date`, `geometry`,
`administrative_area`, `village`, `cts_raw`. The settlement detail shows only projects
linked by that exact ID.

Context features need a unique `id`, valid WGS84 geometry and a
`properties.category`: `road`, `building`, `amenity`, `transport`,
`water_infrastructure` or `residential_context`. Preserve attribution and licence
information in your source data. Mapped amenities do not prove service reliability.
Synthetic files belong in the separate demonstration workspace.

## API and isolated local setup

The protected endpoints are `POST /urban/data/workspace/preview` and
`POST /urban/data/workspace/import`. Both accept `{ "dataset": <your JSON> }`;
import additionally needs `expected_snapshot` from the preview. Add the configured
`X-Officer-Key` header. OpenAPI schemas are at `/docs`.

To start with an empty source directory and a separate persistent database, leaving
previous source data and operational records in place:

```bash
mkdir -p .runtime/my-workspace/input
export URBANSAARTHI_DATA_DIR="$PWD/.runtime/my-workspace/input"
export URBANSAARTHI_DB_PATH="$PWD/.runtime/my-workspace/workspace.sqlite3"
read -rsp 'Choose a private local officer key: ' NAGARSEVA_OFFICER_KEY
export NAGARSEVA_OFFICER_KEY
bash start-local.sh
```

Use the same database path on subsequent starts. If default ports are occupied,
set `URBANSAARTHI_API_PORT` and `URBANSAARTHI_WEB_PORT` to unused ports. Optional
consented uploads use `URBANSAARTHI_EVIDENCE_STORAGE=sqlite`. The original acquisition
scripts and archived research remain available separately.

For this checkout's prepared local preview, the private officer key is stored in
`.runtime/my-workspace/officer.key` with owner-only read permissions. Enter that
value in Data & access. It is excluded from Git; fresh setups can choose their own
key using the command above.
