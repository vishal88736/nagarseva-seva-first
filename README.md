# UrbanSaarthi

A working multilingual prototype for affordable housing, settlement exploration and
basic-service issue reporting in Mumbai, built for the Seva First Maharashtra Zone
problem statement. The application uses React/TypeScript/Leaflet, FastAPI and SQLite.
It does not claim official municipal submission or government integration.

## Four primary sections

- **Dashboard** (`/dashboard`): sourced dataset counts, historical map preview and recent reports.
- **Explore Settlements** (`/settlements`): independent 2015 polygons and the 2024 register, with source-supported filters.
- **Report an Issue** (`/report-issue`): validated, persisted anonymous reports and stable references.
- **Projects & Reports** (`/projects`): sourced project records, details, filters and downloads.

English, हिंदी and मराठी use the existing translation provider, with feature dictionaries
in `nagarseva/website/src/i18n/locales/`. Changing language preserves forms and filters.
Published names and original source values are retained rather than machine-translated.

Existing prioritization, hypothetical scenarios, officer service assurance and Data &
access remain secondary tools under Projects & Reports. Legacy hash links still work.
[Product, routing, source and API contract](nagarseva/docs/product.md).

## Data currently connected in the local workspace

| Dataset | Actual imported count | Scope |
| --- | --- | --- |
| Historical 2015 boundaries | 2,542 source polygons; 2,517 displayed | 25 topology-invalid polygons excluded without repair |
| SRA 2024 register | 2,597 source rows | No verified join to 2015 polygons |
| SRA scheme listings | 5,677 records | Unknown status/progress stays unknown |
| OSM context | 7,106 mapped objects | Mapping does not establish operation or household access |
| Census 2011 | 456 observations across 190 state/town units | No cluster allocation; historical reference year retained |

The supplied GeoJSON has only `polyno`, null in every feature. It provides no verified
settlement names or SRA IDs. Geometry, register records, project listings, Census
observations and user reports remain distinct. [Boundary validation and limitations](research/historical_boundaries_2015.md).
The original retrieval date and independently verified SRA reuse terms remain unknown.

## Run locally

Use Python 3.12 and Node 24. From the repository root:

```bash
python3.12 -m venv nagarseva/.venv
nagarseva/.venv/bin/python -m pip install -r nagarseva/model/requirements-urban.txt
npm --prefix nagarseva/website ci
bash start-local.sh
```

Open **http://localhost:5173/dashboard**. API documentation: **http://localhost:8000/docs**.
The launcher reuses installed dependencies and reports occupied ports without stopping
unrelated processes. To use the current alternate ports:

```bash
URBANSAARTHI_API_PORT=8001 URBANSAARTHI_WEB_PORT=5174 bash start-local.sh
```

A fresh checkout already includes the 2015 static layer. The other acquired source files
remain local and are not silently downloaded or replaced. When `data/processed` and its
validated originals are available, connect them reproducibly:

```bash
nagarseva/.venv/bin/python -m pip install -r scripts/requirements-data.txt
nagarseva/.venv/bin/python scripts/activate_public_data.py
export URBANSAARTHI_DB_PATH="$PWD/.runtime/my-workspace/workspace.sqlite3"
export URBANSAARTHI_DATA_DIR="$PWD/.runtime/my-workspace/input"
URBANSAARTHI_API_PORT=8001 URBANSAARTHI_WEB_PORT=5174 bash start-local.sh
```

Activation verifies source hashes, backs up an existing database, preserves operational
records and refuses to replace a user import. Repeated identical activation is safe.
[Bring-your-own-data import format](nagarseva/docs/workspace-data.md) also remains available.

Public issue creation requires no officer key. For operator actions and private evidence:

```bash
read -rsp 'Choose a private local officer key: ' NAGARSEVA_OFFICER_KEY
export NAGARSEVA_OFFICER_KEY
export NAGARSEVA_MODE=pilot-prototype
export URBANSAARTHI_EVIDENCE_STORAGE=sqlite  # optional consented image storage
bash start-local.sh
```

See [.env.example](.env.example). Never put officer keys in VITE_* variables or commit
runtime databases, images or real credentials. Schema migrations are applied at API
startup. Reports are saved in SQLite and explicitly marked as prototype self-reports;
they are not forwarded to a municipality. Shared keys are not production identity/RBAC.

## Acquire and validate data

From the repository root, after creating `nagarseva/.venv` as above:

```bash
uv pip install --python nagarseva/.venv/bin/python -r scripts/requirements-data.txt
# Poppler (pdftotext/pdfinfo) and OpenSSL must be on PATH.
nagarseva/.venv/bin/python scripts/acquire_data.py
```

The staged runner continues after source failures and records them in the inventory.
It never treats a failed source as a successful dataset. Successful downloads are
cached with checked SHA-256 hashes; `--refresh` rechecks sources and preserves older
content-addressed originals. No large Geofabrik extract is downloaded for this pilot.
Raw files are in `data/raw/{sra,census,osm,other}` as applicable, cleaned files in
`data/processed`, and request/quality manifests in `data/metadata`. Source originals and large processed assets are
excluded from Git; the checked local handoff bundle is prepared separately. No source credentials are required or bypassed.

Individual repeatable stages:

```bash
nagarseva/.venv/bin/python scripts/inspect_sra_layers.py
nagarseva/.venv/bin/python scripts/ingest_sra.py
nagarseva/.venv/bin/python scripts/ingest_sra_register.py
nagarseva/.venv/bin/python scripts/ingest_sra_pdf.py
nagarseva/.venv/bin/python scripts/ingest_sra_projects.py
nagarseva/.venv/bin/python scripts/ingest_osm.py
nagarseva/.venv/bin/python scripts/ingest_census.py
nagarseva/.venv/bin/python scripts/prepare_real_data.py
nagarseva/.venv/bin/python scripts/prepare_demo_data.py
nagarseva/.venv/bin/python scripts/validate_datasets.py
```

The Census trust repair is request-specific and does not disable TLS or change the
system trust store. See [Census acquisition details](research/census_followup.md).

Restart the API after preparing a new source snapshot. Set `URBANSAARTHI_DATA_DIR`
to another processed directory if needed. The acquisition inventory records source
dates and unresolved licences separately from retrieval dates. The PDF map and
listing are retained for local research; wider redistribution needs source-specific
reuse review. OSM data require OpenStreetMap contributor attribution and ODbL terms.

Set `NAGARSEVA_OFFICER_KEY` on the API and enter it through **Officer access** to protect server records. Do not put the key in a frontend build or commit it. This shared-key demo is not production identity or role management.

## Deploy on AWS

Use the [AWS CloudShell deployment guide](deploy/aws/README.md) for one EC2 instance, persistent encrypted-volume demo records and an HTTPS CloudFront address. Active credits must cover usage; this is not permanently free hosting. The guide and readiness CI do not imply that an AWS account has already been provisioned.

## Data and validation boundaries

The separate five-cluster sandbox's polygons, indices, routes and household/cost
assumptions are **synthetic**. Acquired mode uses actual source records with nullable
geometry and observations. SRA feature services still timed out. The Census server's
missing intermediate certificate was repaired using verified public CA material,
with hostname and certificate verification retained; all four official table assets
were downloaded. Historical 2011 state/town observations are not assigned to SRA
clusters. The georeferenced 2024 source map is raster imagery, not current analytical
boundaries. OSM mappings do not prove service operation, and a shared CTS
string does not establish a project join. No current service baseline, official cost
estimate, approved ward pilot or field impact is claimed.

Calculations run deterministically in Python and the browser. The four-section product's
current checks are recorded in [product validation](research/verification/product_validation.json),
including a browser run with the acquired register and project records. Earlier acquisition
findings remain in [the research report](research/final_report.md). CI artifacts in
`integration/` retain their own dates, source revisions and validation scope.

Run checks from the repository root:

```bash
PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest tests nagarseva/tests/test_urban.py nagarseva/model/tests deploy/aws/tests submission/scripts/tests .github/tests -q
npm --prefix nagarseva/website test
npm --prefix nagarseva/website run lint
nagarseva/website/node_modules/.bin/tsc -p nagarseva/website/tsconfig.app.json --noEmit --noUnusedLocals --noUnusedParameters
npm --prefix nagarseva/website run build
# System Chromium + Playwright; uses a disposable database and owned ports.
uv pip install --python nagarseva/.venv/bin/python playwright==1.56.0
CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_product_browser.py
CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_historical_boundaries_browser.py
CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_public_browser.py
CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_field_collection_browser.py
# Optional: requires the locally acquired data/processed/urban_real.json.
URBANSAARTHI_BROWSER_REAL_DATA=1 CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_product_browser.py
```

The full Python command additionally requires `nagarseva/model/requirements.txt`.
CI uses Playwright-managed Chromium; the local commands above select the installed system browser.
The original synthetic-trained models are not used to rank acquired settlements.

## Project materials

- [Architecture, formulas, state transitions and evaluation](nagarseva/docs/urbansaarthi.md)
- [Focused application guide](nagarseva/README.md)
- [Research overview](research/README.md) and [executive research findings](research/research_summary.md)
- [Evidence workbench](prototype/README.md), also available at `/evidence/`
- [UrbanSaarthi submission pack](submission/README.md): official-template deck and PDF, budget, answers and pitch. Authenticated form/upload limits remain unverified and personal fields remain omitted.
- [Original source lineage](integration/source-manifest.json) and [merge record](integration/README.md)

The original remote repository remains untouched. Imported model artifacts and
legacy API/tests are retained. Unreachable frontend files were removed as documented
in the cleanup report. The existing SQLite database remains the development store;
PostGIS, production identity and agency integrations are not implemented.

The [prepared pilot kit](pilot/README.md) identifies a prospective BMC M-East water-domain owner and includes an unsent request, independent-baseline protocol, observation/indicator rules and blank quote templates. Prepared protocols are not completed field evidence.

## Published source and checks

The source merge and per-file hashes were verified in [this workflow](https://github.com/vishal88736/nagarseva-seva-first/actions/runs/39140508298). See [the recorded validation outcomes](integration/ci-validation.json) for backend, frontend and evidence-check results. Browser and field validation remain separate.
