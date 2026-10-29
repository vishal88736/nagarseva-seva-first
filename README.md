# UrbanSaarthi

**People • Places • Better Cities**

A working English, Hindi and Marathi civic-tech demonstration for **SEVAMO96**:
General Category, Urban Development; affordable housing, slum redevelopment and
basic-service assurance. React/TypeScript/Leaflet, FastAPI and SQLite are preserved.

**DEMO MODE · Synthetic data.** Settlement records, ward assignments, geometries,
housing estimates, service indicators, issues, projects and owners are fictional.
No government API, authority approval, official eligibility decision or live-record
validation is claimed. Archived acquired files are preserved but are disconnected
from the active application. Nothing is downloaded or reactivated automatically.

## Working application

- **Dashboard** `/dashboard`: actual shared-record summaries, household-weighted
  service coverage, issue/project breakdowns, gaps, map and genuine operation history.
- **Explore Settlements** `/settlements`: search, combined filters, sorting, pagination,
  synchronized synthetic polygons and details for housing, six services and related records.
- **Report an Issue** `/report-issue`: validated submission, optional consented photos
  when enabled, SQLite save, management filters, authorized status updates and follow-up.
- **Projects & Reports** `/projects`: projects and milestones, housing assessments,
  visits/inspections, community feedback, six filtered CSV reports and data management.
- **Real-World Data Integration** `/data-integration`: honest readiness matrix,
  functioning CSV/GeoJSON inspection, mapping, validation, controlled import,
  provenance, proposed roadmap and privacy/governance information.

Additional views: `/housing`, `/services`, `/visits`, `/projects/data`.
Existing secondary hash links and the hypothetical comparison calculator remain.
All data mutations use the same revisioned, transactional synthetic adapter. The
language selection persists in the existing browser preference; IDs do not change.

Initial fixed-seed collections: **100 settlements, 24 demo wards, 60 issues,
20 projects, 40 milestones, 30 visits and 4 data-source records**. Housing assessments
and feedback start empty. Activity is recorded when an actual operation occurs,
including initial workspace creation; seed histories do not invent user actions.
Every synthetic row carries `is_synthetic:true`. Three planted anomaly fixtures
are separate test scenarios and never overwrite active settlement indicators.
The interface and exports label these fictional records **Demo data**.

`/methodology` documents generation and calculation rules and provides adjustable
weight previews, a what-if simulator, budget allocation, planted-anomaly checks,
SLA tracking, date-based project delay flags and a measured 10,000-settlement
diagnostic. The diagnostic does not persist its separate workload or alter the city.
Reports support CSV and browser Print / Save as PDF with source/save/export dates.

## Run locally

Use the existing Python 3.12 and Node 24 environment. The app is nested inside
`seva first/nagarseva-seva-first`; the parent folder has no `package.json`.
From that repository root:

```bash
bash start-local.sh
```

For the chosen Vercel frontend + persistent Python backend deployment, see
[the deployment guide](deploy/vercel/README.md). The root `vercel.json` expects a
real `VITE_API_BASE_URL` and rejects deployment with a disconnected backend.

Open **http://localhost:5173/dashboard**, then **Data Integration** in the sidebar.
API documentation: **http://localhost:8000/docs**. The launcher checks installed
dependency fingerprints and occupied ports; it stops only its own server processes.
For a different pair:

```bash
URBANSAARTHI_API_PORT=8001 URBANSAARTHI_WEB_PORT=5174 bash start-local.sh
```

For a fresh environment, install the declared dependencies first:

```bash
python3.12 -m venv nagarseva/.venv
nagarseva/.venv/bin/python -m pip install -r nagarseva/model/requirements-urban.txt
npm --prefix nagarseva/website ci
```

Public demo issues, visits and feedback can be created without an officer key.
Administrative changes, reset and controlled imports use the existing backend
key authorization. To enable them, set a private key **before starting the API**,
then enter that same key in **Demo data management → Demo administrator access**:

```bash
read -rsp 'Choose a private local administrator key: ' NAGARSEVA_OFFICER_KEY
export NAGARSEVA_OFFICER_KEY
export URBANSAARTHI_EVIDENCE_STORAGE=sqlite  # optional private PNG/JPEG photo storage
bash start-local.sh
```

The key stays in this browser session and is checked on the server. This is demo
administration, not a production identity or government officer system. Never put
keys in `VITE_*` variables, source control, screenshots or logs. See [.env.example](.env.example).
The default database is `nagarseva/model/data/local/urbansaarthi.sqlite3`.
`URBANSAARTHI_DB_PATH` can select a different SQLite file; relative paths resolve
from the API working directory (`nagarseva`). This is server persistence shared by
clients of that server, not localStorage reporting or municipal submission.

## Controlled data onboarding

**Implemented formats:** UTF-8 comma-separated CSV (including BOM, quoted commas
and multiline cells), Excel `.xlsx` with visible-worksheet selection, and GeoJSON
FeatureCollection (`.geojson` or `.json`). Limits:
5 MiB, 5,000 records and 100 source fields. Legacy XLS, Shapefile, KML and PDF ingestion,
coordinate reprojection and external API synchronization are not implemented.

Selecting a file reads it in browser memory. After a permission/data-minimization
attestation, inspection and validation send it to this application's backend;
these requests do not permanently store it. Field suggestions use actual columns,
never fabricated identifiers. Geographic data require explicit WGS84 confirmation.
Schema checks are not source-authenticity or official verification.

A successful explicit, authorized import commits original bytes, SHA-256, mapping,
source provenance, transformed records and actual timestamps to a separate SQLite
batch. Duplicate identifiers are rejected; exact retries are idempotent. Related
records must reference identifiers in an explicitly selected controlled settlement
batch. No row-order or synthetic-to-real geographic join is attempted.

**Imported batches are isolated:** they do not replace demo records, activate real
records in settlement/project pages, or connect a government service. Production
activation needs approved source semantics, compatibility tests, authorization,
a backend integration adapter and operational access controls. Sources may not
contain every desirable field. Static files cannot support two-way complaint sync.

[Detailed contract and dependencies](nagarseva/docs/data-integration.md) ·
[Implementation and verification report](research/integration_readiness_implementation.md).

## Checks

Run from the repository root (use the existing environment; the full Python suite
also requires `nagarseva/model/requirements.txt`):

```bash
PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest tests nagarseva/tests/test_urban.py nagarseva/model/tests deploy/aws/tests submission/scripts/tests .github/tests -q
npm --prefix nagarseva/website test
npm --prefix nagarseva/website run lint
nagarseva/website/node_modules/.bin/tsc -p nagarseva/website/tsconfig.app.json --noEmit --noUnusedLocals --noUnusedParameters
npm --prefix nagarseva/website run build
# Requires the existing Playwright installation and system Chromium; disposable DB only.
PYTHONPATH=nagarseva CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_synthetic_integration_browser.py
```

The browser test uses owned ephemeral ports and synthetic software fixtures. Basemap
requests are blocked. It does not prove an external provider, AWS deployment,
production authorization, source quality or field outcomes. Older historical/public
browser scripts remain archived regression references for the disconnected UI;
they are not acceptance tests for the active synthetic interface.

## Preserved research and deployment materials

- [Earlier civic implementation](research/civic_implementation_report.md) and
  [historical-boundary validation](research/historical_boundaries_2015.md): archived
  source investigations, not the active adapter or current readiness status.
- [Research findings](research/final_report.md), [research overview](research/README.md),
  [original source lineage](integration/source-manifest.json) and [merge record](integration/README.md).
- [Architecture and earlier calculation methods](nagarseva/docs/urbansaarthi.md).
- [Evidence workbench](prototype/README.md), separately available at `/evidence/`.
- [Submission pack](submission/README.md) and [prepared pilot protocols](pilot/README.md):
  preparation does not establish field evidence, official approval or live integration.
- [AWS deployment guide](deploy/aws/README.md): retained deployment tooling; no new
  deployment was performed for the readiness work. Hosting requires suitable credentials,
  security configuration and resources. [Earlier CI evidence](integration/ci-validation.json)
  retains its original revision and scope.

Original source files, archival parsing tools, API compatibility routes, models and
legacy SQLite records remain intact. Synthetic records and controlled imports use
separate additive tables. A confirmed reset affects only the synthetic namespace,
including its demo attachments, and preserves controlled imports and unrelated data.

## End-to-end audit evidence

See [the current audit](research/end_to_end_audit.md) for the full PASS/PARTIAL
checklist, file/line evidence, upload cases, limitations and executed commands.
[Translation checks](research/verification/translation_audit.json) and
[the native-review queue](research/translation_review.csv) distinguish missing
keys from linguistic review. Source values and stable identifiers are preserved.

Re-run the added audit checks after building:

```bash
npm --prefix nagarseva/website run build
PYTHONPATH=nagarseva nagarseva/.venv/bin/python tests/check_full_audit_browser.py
PYTHONPATH=nagarseva nagarseva/.venv/bin/python tests/check_audit_workflows_browser.py
(cd nagarseva/website && node --experimental-strip-types tests/check_translation_audit.mjs)
```

Reproduce the fictional city without touching SQLite:

```bash
nagarseva/.venv/bin/python scripts/generate_demo_city.py --seed 96 --count 100 --output .runtime/demo-city.json
```
