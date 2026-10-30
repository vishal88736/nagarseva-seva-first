# UrbanSaarthi

**People • Places • Better Cities**

A civic-tech prototype connecting settlement information, affordable-housing needs,
basic-service gaps, citizen issues and redevelopment follow-up in one application.
The interface supports **English, Hindi and Marathi**.

**Public demonstration:** [Open UrbanSaarthi](https://d2nrwxy6sjb9o8.cloudfront.net/)

> **Demo data:** All active settlement records, ward assignments, map geometries,
> household estimates, service indicators, issues, projects and demonstration
> identities are fictional. They are not official government records, verified
> measurements, housing entitlements or appointments with a public authority.
> No authorized external government service is connected.

## Contents

- [Challenge and purpose](#challenge-and-purpose)
- [Features and navigation](#features-and-navigation)
- [Walk through the prototype](#walk-through-the-prototype)
- [Architecture and repository layout](#architecture-and-repository-layout)
- [Run locally](#run-locally)
- [Configuration](#configuration)
- [Demo data and persistence](#demo-data-and-persistence)
- [Calculation methods](#calculation-methods)
- [Dataset onboarding](#dataset-onboarding)
- [AWS deployment and updates](#aws-deployment-and-updates)
- [API reference](#api-reference)
- [Testing and verification](#testing-and-verification)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Further documentation](#further-documentation)

## Challenge and purpose

| Item | Context |
| --- | --- |
| Challenge ID | SEVAMO96 |
| Category | General Category |
| Sector | Urban Development |
| Sub-theme | Affordable housing, slum redevelopment and basic-service assurance |

Safe, affordable housing depends on reliable services and access to livelihoods.
The problem addressed here is how to connect housing assessments, service needs,
complaints, inspections and project progress without losing the settlement and
resident context between them.

UrbanSaarthi demonstrates a shared workflow: explore a settlement, inspect its
needs, record an issue, follow up through notes or a visit, inspect redevelopment
milestones and produce a report. Intended benefits include clearer priorities,
better coordination and more accountable follow-up. These are proposed outcomes;
field impact has not been measured or established by this demonstration.

## Features and navigation

All views use the same server-backed synthetic workspace. Counts and charts derive
from those records rather than separate presentation arrays.

| Area | Where to open it | Implemented behavior |
| --- | --- | --- |
| Dashboard | `/dashboard` | Clickable summaries, service coverage, issue and project breakdowns, map preview, largest service gaps and recorded activity. |
| Settlement explorer | `/settlements` | Search by name/ID; combined ward, risk, redevelopment and service-gap filters; sorting; pagination; synchronized map/list selection; settlement details. |
| Interactive map | Dashboard and explorer | Generated polygons, grouped location targets, pan/zoom, fit, selection, layer toggles and an unavailable-basemap fallback. OSM street tiles provide geographic context only. |
| Issue reporting | `/report-issue` | Validated submission, settlement association, management filters, status transitions, assignment, follow-up notes and event history. Optional photos depend on server configuration. |
| Redevelopment | `/projects` | Search/filter/sort, project details, progress updates, budgets, planned dates, milestone creation/editing and overdue indicators. All project values are fictional. |
| Affordable Housing | **Projects & Reports → Affordable Housing**, or `/housing` | Household summaries, housing conditions, assessments, improvement categories, priorities, notes and assessment history. It has no separate sidebar entry. |
| Basic-service assurance | `/services` | Water, sanitation, drainage, waste collection, electricity and roads/accessibility coverage; targets; gaps; priority factors and linked follow-up. |
| Site visits | **Projects & Reports → Site visits**, or `/visits` | Schedule, inspect, edit, complete or cancel visits; assign demonstration owners; add notes and service findings. Indicator changes require an explicit operation. |
| Community feedback | `/projects?tab=community` | Settlement/project feedback, moderation, responses and follow-up state. No endorsements or consultation results are fabricated. |
| Reports | **Projects & Reports → Reports**, or `/projects?tab=reports` | Six report types, applicable settlement/date filters, tables, CSV export and browser Print / Save as PDF. |
| Methodology | Sidebar footer, or `/methodology` | Generation rules, missing-data behavior, weight tuning, what-if scenarios, budget allocation, anomaly fixtures, SLA/delay diagnostics and a performance diagnostic. |
| Data management | **Administration**, or `/projects/data` | Entity counts, validation, last recorded save, JSON export, configurable targets/weights, administrator access and confirmed reset. |
| Real-World Data Integration | Sidebar **Data Integration**, or `/data-integration` | Readiness matrix, templates, CSV/XLSX/GeoJSON inspection, mapping, validation, preview, controlled import, provenance, import history and rollback. |

Existing comparison and planning deep links, including `/projects/scenarios`,
`/projects/priorities` and `/projects/assurance`, remain supported.

## Walk through the prototype

1. Open the dashboard and inspect the **Demo data** notice and source/save captions.
2. Open **Explore Settlements**, filter or search, and select a polygon or table row.
   Inspect the profile, housing information, six services and related records.
3. Use **Report an Issue** for that settlement. Enter the category, title,
   description, priority and location. Wait for confirmed server success before
   treating it as saved; reopen the list or reload to inspect the result.
4. With demonstration administrator access enabled, acknowledge the issue and add
   an owner or follow-up note. Review its actual recorded history.
5. Open **Projects & Reports** and inspect a project, its settlement and milestones.
   Open **Affordable Housing** to inspect or create a housing-needs assessment.
6. Schedule a visit and record findings. Completing a visit does not automatically
   resolve an issue or change a settlement's service indicators.
7. Open **Reports**, choose a report and filters, then download CSV or use browser
   printing to save a PDF. Exports retain the **Demo data** disclaimer.
8. Switch language and reload. The language preference persists; record IDs and
   source values remain unchanged.

Use fictional descriptions and identities. Keep administrator credentials out of
screen recordings. Public issue/visit/feedback creation and administrator-only
actions are distinguished in the [configuration section](#configuration).

## Architecture and repository layout

```text
React UI → civic domain services/context → CivicAdapter
                                           └─ FastAPI → transactional SQLite workspace

File onboarding UI → integration adapter → FastAPI validation
                                            └─ isolated SQLite import batches
```

- **Frontend:** React 18, TypeScript, Vite 6, Leaflet/react-leaflet and Lucide icons.
- **Backend:** Python 3.12, FastAPI, Pydantic, SQLite, Shapely and openpyxl.
- **Persistence:** revision checks and idempotent operations protect shared state;
  confirmed mutations return the updated workspace to the UI.
- **Localization:** resource catalogues, locale-aware formatting and self-hosted
  Devanagari fonts; India calendar boundaries use `Asia/Kolkata`.
- **Hosted application:** Docker on EC2 behind CloudFront. Website assets and API
  use the same public origin. AWS-only hosting is the current deployment choice.

```text
README.md                         Main project and operating guide
start-local.sh                    Owns local API/frontend startup and shutdown
nagarseva/
  website/src/civic/              Typed entities, adapter, calculations and civic UI
  website/src/integration/        Controlled dataset-onboarding UI and adapter
  website/src/i18n/               English, Hindi and Marathi resources/formatters
  website/public/fonts/          Devanagari font, provenance and licence notice
  website/tests/                 Frontend domain, map, adapter and locale tests
  model/api/civic_demo.py         Seed generator, validation and civic operations
  model/api/data_onboarding.py    File mapping, validation, imports and rollback
  model/api/file_formats.py       Bounded CSV/XLSX/GeoJSON parsing
  model/api/store.py              Existing SQLite storage infrastructure
  model/api/urban.py              Active FastAPI application factory
  docs/                          Detailed data contracts and preserved architecture
scripts/generate_demo_city.py     Reproduce the fictional city without changing SQLite
tests/                           Backend, import, data-integrity and browser checks
deploy/aws/                      Dockerfile, CloudFormation, bootstrap and operations
.github/workflows/               Checks and preserved source/evidence workflows
research/                       Dated audits, validation evidence and archived research
prototype/                      Separate preserved evidence workbench
```

Original datasets, older models and compatibility APIs are retained. Their presence
does not make them active integrations. Do not run archival acquisition/activation
commands as part of the normal synthetic demonstration setup.

## Run locally

### Prerequisites

- Git, Bash and npm.
- **Python 3.12** with venv support, or `uv` able to create that environment.
- **Node.js 24** matches the Docker build and GitHub workflow configuration.
- Internet access for the first dependency installation and optional OSM tiles.

The repository has a nested frontend. The parent `seva first` directory and the
repository root have no frontend `package.json`; run the commands below from the
repository root, **`nagarseva-seva-first`**.

```bash
git clone https://github.com/vishal88736/nagarseva-seva-first.git
cd nagarseva-seva-first
bash start-local.sh
```

For the existing local checkout:

```bash
cd "/home/vishal/D DRIVE/seva first/nagarseva-seva-first"
bash start-local.sh
```

Open **http://localhost:5173/dashboard**. API documentation is at
**http://localhost:8000/docs**. Stop both owned processes with **Ctrl+C**.

The launcher creates `nagarseva/.venv` when needed, installs the focused backend
requirements and frontend lockfile dependencies when their fingerprints change,
checks ports, and waits for real API/frontend health responses. Installation can
download packages. Logs are in `.runtime/local/8000-5173/` for the default ports.

To install dependencies explicitly before launching:

```bash
python3.12 -m venv nagarseva/.venv
nagarseva/.venv/bin/python -m pip install -r nagarseva/model/requirements-urban.txt
npm --prefix nagarseva/website ci
bash start-local.sh
```

For alternative ports:

```bash
URBANSAARTHI_API_PORT=8001 URBANSAARTHI_WEB_PORT=5174 bash start-local.sh
```

The launcher rejects invalid, occupied or equal ports and leaves other listeners
untouched. Full legacy/model tests require additional dependencies; they are not
necessary to run the civic application.

## Configuration

[`.env.example`](.env.example) documents configuration names without secrets. The
launcher does **not** automatically source this file or a root `.env`; export the
required backend variables in the shell that starts it.

| Variable | Purpose and default behavior |
| --- | --- |
| `NAGARSEVA_OFFICER_KEY` | Private shared key for demonstration administrative operations. Unset locally by default; generated on EC2 during initial bootstrap. Never expose it in frontend variables. |
| `URBANSAARTHI_DB_PATH` | SQLite path. Local default: `nagarseva/model/data/local/urbansaarthi.sqlite3`; hosted image default: `/data/urbansaarthi.sqlite3`. Explicit relative paths resolve from the API working directory. |
| `URBANSAARTHI_EVIDENCE_STORAGE` | Set to `sqlite` to enable consented PNG/JPEG issue photos, maximum 2 MiB each. Unset disables photo persistence; the form reports that limitation. |
| `URBANSAARTHI_API_PORT` / `URBANSAARTHI_WEB_PORT` | Launcher ports; defaults `8000` / `5173`. |
| `NAGARSEVA_API_TARGET` | Vite development/preview proxy target. The launcher sets it to the chosen local API port. |
| `NAGARSEVA_MODE` | Environment label used by retained API configuration; the AWS image selects `hosted-demo`. It does not authorize access or activate real data. |
| `NAGARSEVA_CORS_ORIGINS` | Exact allowed browser origins for direct cross-origin API use. The AWS website uses the same origin, so a Vercel CORS setup is unnecessary. |
| `VITE_API_BASE_URL` | Optional **public, build-time** API prefix. Leave unset for local proxy and AWS-only hosting; the frontend uses `/api`. Never include credentials. |
| `URBANSAARTHI_ORIGIN_SECRET` | AWS-only private CloudFront-to-origin token, separate from the administrator key. Bootstrap/CloudFormation manage it. |

To enable local demonstration administration, stop the current local launcher,
then start it from the repository root with a privately entered key:

```bash
read -rsp 'Choose a private local administrator key: ' NAGARSEVA_OFFICER_KEY
export NAGARSEVA_OFFICER_KEY
bash start-local.sh
```

Enter the same key in **Administration → Demo administrator access**. It is kept in
that browser session and checked on the server. Creating demo issues, visits and
feedback is public; status changes, project/milestone edits, housing assessments,
imports, private downloads, configuration changes and reset require administrator
access. This is a shared-key demonstration boundary, not production identity/RBAC.

To enable local photo storage, export `URBANSAARTHI_EVIDENCE_STORAGE=sqlite` before
starting the launcher. Existing databases and attachments are private runtime data;
do not commit them, keys, `.env` files or backup files.

## Demo data and persistence

The seed generator uses **seed 96**. These are the initial collection sizes, not
hardcoded dashboard statistics; saved user operations can change them.

| Collection | Initial records |
| --- | ---: |
| Settlements | 100 |
| Fictional wards | 24 |
| Issue reports | 60 |
| Redevelopment projects | 20 |
| Project milestones | 40 |
| Site visits | 30 |
| Housing assessments | 0 |
| Community feedback | 0 |
| Data-source descriptions | 4 |
| Separate planted anomaly fixtures | 3 |

Stable IDs and fictional names connect records. Each synthetic row carries
`is_synthetic: true`. Geometry illustrates locations around Mumbai without claiming
real settlement or ward boundaries. Scenario dates are fixed fixture values;
activity timestamps are created only by actual operations, including workspace
initialization. Time-dependent diagnostics can change as the clock advances.

The backend validates duplicate IDs, references, supported statuses, percentages,
dates, geometry and related counts. It loads the saved workspace across refreshes;
it does not generate a different city on each page. SQLite is shared by clients
of that API server. Browser storage holds preferences/session access, not the
application's reporting database.

Reproduce the seed without touching the running database:

```bash
nagarseva/.venv/bin/python scripts/generate_demo_city.py \
  --seed 96 --count 100 --output .runtime/demo-city.json
```

**Reset:** use the confirmed reset in **Administration** to restore the initial
synthetic workspace. It removes local demo changes and associated demo attachments
in that server's synthetic namespace, records a reset event and preserves controlled
imports and unrelated records. Export anything wanted first. A JSON export is useful
for inspection, but no UI restore-from-JSON workflow is implemented.

## Calculation methods

`/methodology` documents the formulas and exposes interactive previews. The rules
below are demonstration assumptions, not official planning standards.

- **Aggregate service coverage:** household-weighted mean over settlements with a
  known value: `sum(coverage × households) / sum(households)`. Unknown coverage is
  excluded from both numerator and denominator; no usable denominator returns
  unavailable.
- **Service gap:** `max(0, target − coverage)` in percentage points. A missing input
  produces an unavailable gap rather than zero.
- **Default planning targets:** water 95%, sanitation 90%, drainage 85%, waste 90%,
  electricity 95%, roads/access 90%. Authorized changes persist in the workspace.
- **Demo priority score:** weighted mean of mean service gap, unresolved-issue
  priority, unresolved-issue count and oldest unresolved age. Default weights are
  0.50 / 0.20 / 0.20 / 0.10. Available factors are renormalized; missing weighted
  inputs or service cells mark the result **Partial**. No usable factor means no score.
- **Scenario and budget tools:** hypothetical previews. They do not change stored
  coverage, approve funding or resolve issues.
- **Anomaly checks:** explicit rules for unusually high persons per household,
  very low coverage and missing coverage. Three independent planted fixtures check
  detection without modifying the active city. These rules are not a trained model.
- **SLA and delay flags:** configurable-by-code demonstration rules based on stored
  dates/statuses. They are not statutory service deadlines or validated predictions.
- **Performance diagnostic:** a separate deterministic 10,000-settlement calculation
  workload. It measures that browser/workload only, not multi-user server capacity.

Reports retain source/save/export metadata and a **Demo data** watermark. The saved
workspace time is not a claimed service measurement date. CSV exports contain the
filtered records, a notice row, localized display headers and spreadsheet-formula
protection. PDF export uses the browser's **Print / Save as PDF** flow and the
display-column subset; CSV is the full-field export.

## Dataset onboarding

The active demonstration stays synthetic. File imports are stored separately and
do not activate real records in dashboards, maps, reports or rankings.

| Implemented input | Behavior |
| --- | --- |
| CSV | UTF-8, optional BOM, comma delimiter, quoted commas/multiline fields and real template downloads. |
| Excel `.xlsx` | Visible worksheet selection; safe read-only parsing; percentage-format conversion disclosed in preview. Legacy `.xls` is unsupported. |
| GeoJSON `.geojson` / `.json` | FeatureCollection inspection; supported geographic types validated; boundary records require Polygon/MultiPolygon. Explicit WGS84 confirmation is required. |

Limits are **5 MiB per file, 5,000 records and 100 fields**. Geographic checks also
bound coordinate counts. Shapefile, KML, PDF import, reprojection and external
two-way synchronization are not implemented.

The workflow is: permission/data-minimization attestation → file selection and
inspection → actual source-column mapping → row-level validation → transformed
preview → provenance entry and explicit import confirmation. Required provenance
includes **source name, publisher, source date, licence and source link**.

Validation checks required values, duplicate identifiers, numeric/date/percentage
types and ranges, applicable geometry/topology/coordinates and linked settlement
references. Preview requests are not permanent uploads. A confirmed authorized
import preserves source bytes, SHA-256, mapping, provenance, timestamps and records
in an isolated batch. An exact active retry is idempotent; conflicting identifiers
do not silently overwrite records.

Receipts distinguish **Demo** from **Manually provided · unverified**. Uploading a
file cannot establish **Official** status. Completeness measures supplied fields,
not accuracy. History and authorized, reasoned rollback retain audit evidence and
protect dependent batches. Rollback does not replace/reset the synthetic city.

See the [complete onboarding contract](nagarseva/docs/data-integration.md) for
category schemas, format restrictions, authorization and activation dependencies.

## AWS deployment and updates

**Current hosting is entirely on AWS. Vercel is not part of this deployment.**

```text
Browser ── HTTPS ── CloudFront ── restricted HTTP origin ── EC2 Docker container
                                                             ├─ React assets
                                                             ├─ FastAPI /api
                                                             └─ SQLite /data → EBS
```

The [AWS operations guide](deploy/aws/README.md) covers first launch, access,
manual updates, health checks, backup, rollback, troubleshooting and removal. The
template defaults to a `t3.micro` instance with encrypted 20 GiB gp3 storage. The
launcher defaults to `ap-south-1`; pass `URBANSAARTHI_AWS_REGION=us-east-1` when using
the region chosen in the existing deployment. Do not infer a live instance's region
from its CloudFront URL.

**A GitHub push does not update EC2 automatically.** The application workflow runs
backend, frontend, documentation/evidence and current synthetic-browser checks,
then uploads generated test evidence as workflow artifacts. It has read-only
repository permission and does not merge source, rewrite this README or publish
bot commits. Original source-bootstrap scripts remain archived helpers. There is
no configured automatic AWS release job. Updating the website requires fetching a
reviewed commit on EC2, building its Docker image and replacing the container while
retaining `/var/lib/urbansaarthi`
and `/etc/urbansaarthi/runtime.env`. `docker restart` alone does not load new code or
new `--env-file` values. The initial launcher only verifies an existing completed
stack; it does not update its container.

SQLite survives container replacement and reboot **with the existing mounted
volume**. The template deletes the root volume on instance termination or stack
deletion, so off-instance backups are necessary before destructive changes. AWS
credits are finite; EC2, EBS, public IPv4 and traffic can incur charges. Account
credit coverage and expiry must be checked by the account owner.

The earlier [Vercel split-host guide](deploy/vercel/README.md) is an alternative
retained for reference. Its `vercel.json` and preflight script are unused by the
AWS Docker build; Vercel setup is not a prerequisite for running this project.

## API reference

The active app factory is `model.api.urban:create_app`; local Uvicorn serves
`model.api.urban:app`. Swagger documentation is available locally at `/docs`.

| Purpose | Local API server | AWS public endpoint |
| --- | --- | --- |
| General health | `/urban/health` | `/api/urban/health` |
| Synthetic adapter health | `/urban/demo/health` | `/api/urban/demo/health` |
| Shared workspace | `/urban/demo/workspace` | `/api/urban/demo/workspace` |
| Civic commands | `POST /urban/demo/commands` | `POST /api/urban/demo/commands` |
| Integration readiness | `/urban/integration/readiness` | `/api/urban/integration/readiness` |
| Import schema | `/urban/integration/schema` | `/api/urban/integration/schema` |
| File inspection | `POST /urban/integration/inspect` | `POST /api/urban/integration/inspect` |
| File validation | `POST /urban/integration/validate` | `POST /api/urban/integration/validate` |
| Controlled imports/history | `/urban/integration/imports` | `/api/urban/integration/imports` |

Commands include revision and operation identifiers. Administrative requests use
the private `X-Officer-Key` header. The AWS wrapper also requires the origin header
supplied privately by CloudFront; public clients must use the CloudFront address.
The hosted outer wrapper disables its own API docs; use the local app for schema
discovery. Do not assume a missing API path is a frontend route.

## Testing and verification

Run checks from the repository root. The full Python suite also exercises retained
model and source-reader code and therefore needs its additional dependencies:

```bash
nagarseva/.venv/bin/python -m pip install \
  -r nagarseva/model/requirements.txt \
  -r nagarseva/model/requirements-urban.txt \
  -r scripts/requirements-data.txt
PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest \
  tests nagarseva/tests/test_urban.py nagarseva/model/tests \
  deploy/aws/tests submission/scripts/tests .github/tests -q
npm --prefix nagarseva/website test
npm --prefix nagarseva/website run lint
nagarseva/website/node_modules/.bin/tsc -p nagarseva/website/tsconfig.app.json \
  --noEmit --noUnusedLocals --noUnusedParameters
npm --prefix nagarseva/website run build
```

For a focused backend check with the civic application's smaller dependency set:

```bash
PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest \
  tests/test_civic_demo.py tests/test_data_onboarding.py \
  tests/test_audit_features.py deploy/aws/tests -q
```

Production-build browser acceptance uses a **disposable SQLite database and owned
local processes**, not public demo records. After the frontend build, install the
declared browser-test dependency if it is not already available:

```bash
nagarseva/.venv/bin/python -m pip install -r nagarseva/tests/requirements-browser.txt
nagarseva/.venv/bin/python -m playwright install chromium
export CHROMIUM_PATH="$(nagarseva/.venv/bin/python -c 'from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print(p.chromium.executable_path); p.stop()')"
PYTHONPATH=nagarseva nagarseva/.venv/bin/python tests/check_synthetic_integration_browser.py
```

If system Chromium is already installed, skip the browser download and use
`export CHROMIUM_PATH=/usr/bin/chromium` instead. The script uses that path by
default. Browser installation can require OS libraries. Do not run these tests
against an existing application DB.
The acceptance script blocks external map tiles and tests their fallback; that is
not evidence of the live OSM provider or an authorized government connection.

Additional browser matrices and upload/report workflows are documented in the
[dated end-to-end audit](research/end_to_end_audit.md). They create screenshots and
reports under ignored `.runtime/` paths. Older public/historical browser scripts
remain compatibility references, not acceptance checks for the active interface.

The [application workflow](.github/workflows/merge-original.yml) runs the current
synthetic acceptance, upload/export workflows and responsive/accessibility matrix.
Its downloadable `urbansaarthi-check-results` artifact contains the generated
reports and visual evidence. Those files are not committed source links. Run
`python3 .github/scripts/check_docs.py` to check that published documentation links
target tracked files even when extra local runtime files exist.

The documentation refresh re-ran the existing commands; current results and their
scope are recorded below. Passing local checks does not establish field outcomes,
production access control, AWS account configuration or durability after deletion.

### Verification recorded on 31 October 2026

This documentation refresh used the existing Python **3.12.15**, Node
**26.12.1** and system Chromium installation. The pinned Docker/CI frontend runtime
remains Node 24; no global runtime or project dependency was changed.

| Executed check | Result | Evidence scope |
| --- | --- | --- |
| Full Python command above | **410 passed** | Local API, persistence, import, compatibility, hosting-wrapper, published-link and validation tests. Four deprecation/future warnings remain. |
| Frontend test command | **56 passed** | Domain calculations, selection state, locales, adapters, export and retained compatibility tests. |
| Frontend lint script | **Passed** | The existing script runs TypeScript checking. |
| Explicit strict TypeScript command | **Passed** | Application types plus unused-local/parameter checks. |
| Production frontend build | **Passed** | Vite reports a large main chunk and a mixed static/dynamic import advisory; both are nonfatal. |
| Synthetic browser acceptance | **12 checks passed**, no uncaught browser errors | Local production build, disposable SQLite, issue/follow-up, milestone, visit, import/export, localization, reset and failure states. |
| Seed CLI reproduction | **Passed** | Two seed-96 exports were byte-identical; generated relationships validated without changing SQLite. |
| Public AWS HTTP/API check | **Passed** | Homepage, housing route, synthetic health, workspace validation and seven unconnected real-data categories. No public records were changed. |
| Markdown links and shell examples | **Passed** | Local link/heading targets resolve and Bash blocks pass `bash -n`; this does not execute AWS update/removal commands. |
| Live server restart / Docker engine smoke | **Not run in this refresh** | Requires a separately controlled container/live-deployment check. |

The seed still starts with 60 issues; the public workspace contained **62** at the
read-only check, reflecting saved operations. Treat deployed counts as mutable
application state, not generator constants.

To regenerate the static translation-key evidence and native-review CSV:

```bash
(cd nagarseva/website && node --experimental-strip-types tests/check_translation_audit.mjs)
```

This command updates dated files under `research/`; review those diffs before
committing. A successful structural/key audit does not certify linguistic quality.

## Known limitations

- Active records are **Demo data**. Original GeoJSON/KML and acquired-source files
  remain disconnected. There is no official/live government integration or verified
  source-to-settlement geographic match.
- Controlled imports genuinely persist, but remain isolated. Activating approved
  records in the main UI needs an adapter, verified semantics/identifiers and tests.
- Shared-key demo administration is not production user authentication, agency
  authorization, independent officer identity or a secure public-service rollout.
- The current public health response reports photo storage disabled. Enabling it
  requires the backend setting, container recreation and a privacy decision.
- Household estimates, budgets, eligibility-related assessments, planning targets,
  prioritization and anomaly/SLA rules are fictional assumptions, not official
  statistics, scheme eligibility decisions, scientific predictions or funding.
- Seeded issues and visits are scenarios. Only actual operations create activity
  history; an empty history is not supplemented with invented events.
- Hindi/Marathi resources and locale formatting are implemented. Native-speaker
  terminology review remains necessary; see the [review queue](research/translation_review.csv).
- AWS is a single-instance SQLite deployment without managed replication or
  automatic off-instance backups. CloudFront-to-EC2 traffic uses restricted HTTP,
  not end-to-end TLS. Production security, retention and restore procedures need
  further design and validation.
- Deployed submission/restart persistence requires an explicit live write/restart
  check; read-only website/API checks alone do not prove it.
- The repository does not declare a project-wide licence. Third-party fonts and
  dependencies retain their own licences/notices; see the bundled
  [font licence](nagarseva/website/public/fonts/OFL.txt) and
  [font provenance](nagarseva/website/public/fonts/provenance.json).

## Troubleshooting

| Symptom | Check or action |
| --- | --- |
| `npm` cannot find `package.json` | Enter `nagarseva-seva-first` and use `bash start-local.sh`; frontend-only npm commands use `--prefix nagarseva/website`. |
| Port already in use | Choose unused launcher ports. Existing listeners are deliberately left running. |
| Dashboard cannot reach the API | Inspect `.runtime/local/<api>-<web>/api.log` and `web.log`; check the proxied `/api/urban/demo/health` response. |
| Old unrelated API URL is used | Remove an unintended `VITE_API_BASE_URL` override from the frontend build environment and rebuild. AWS-only hosting uses `/api`. |
| Map background unavailable | Keep synthetic geometry enabled; use fit/zoom and the coordinate fallback. OSM tiles require network access and may be unavailable. |
| Administrator action returns 401/503 | Set the server key before startup/recreate the container; enter the matching key privately in Administration. A browser value alone cannot configure the backend. |
| Photo cannot be saved | Confirm `URBANSAARTHI_EVIDENCE_STORAGE=sqlite`, consent, PNG/JPEG type and the 2 MiB limit. |
| Concurrent change/revision error | Reload the actual workspace before retrying. Do not overwrite another operation with stale data. |
| Imported records do not appear on the map | Expected: imports are isolated batches, not active adapters or verified matches. |
| Housing page is hard to find | **Projects & Reports → Affordable Housing**, or open `/housing` directly. |
| GitHub changes are absent on AWS | Fetch/build/replace the container using the [manual update procedure](deploy/aws/README.md#publish-code-updates-manually). A push/restart alone is insufficient. |
| AWS returns 403 or fails startup | Use the CloudFront URL and the [AWS diagnostics](deploy/aws/README.md#troubleshooting). Do not bypass origin checks or expose the API port. |

## Further documentation

- [Application entry points and commands](nagarseva/README.md).
- [AWS deployment, maintenance, backups and rollback](deploy/aws/README.md).
- [Controlled data integration contract](nagarseva/docs/data-integration.md).
- [End-to-end audit and its exact evidence scope](research/end_to_end_audit.md).
- [Integration-readiness implementation report](research/integration_readiness_implementation.md).
- [Translation evidence](research/verification/translation_audit.json) and
  [Hindi/Marathi review queue](research/translation_review.csv).
- [Earlier civic implementation](research/civic_implementation_report.md),
  [historical-boundary validation](research/historical_boundaries_2015.md) and
  [research overview](research/README.md): archived investigations, not current
  official integration claims.
- [Earlier architecture](nagarseva/docs/urbansaarthi.md),
  [source lineage/merge record](integration/README.md) and
  [preserved evidence workbench](prototype/README.md): retained reference material;
  the separate workbench is not mounted by the current AWS application.
- [Submission materials](submission/README.md) and [pilot protocols](pilot/README.md):
  preparation does not establish field validation or authority approval.
