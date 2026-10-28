# UrbanSaarthi

Explainable settlement prioritization, hypothetical intervention comparison and basic-service assurance for a Maharashtra urban-development challenge prototype.

The main application contains five planning screens. **Data & access** holds your
imports, officer access and optional reference material. Research catalogues and
historical source tables are kept out of the main workflow.

**Bring your own data:** upload a GeoJSON settlement collection or a workspace JSON
from **Data & access → Validate file → Import validated dataset**. Download the
in-app template first. [Dataset format and import instructions](nagarseva/docs/workspace-data.md).
Household counts, boundaries, observations and explicit project joins feed the same
selected settlement across the map, scoring, scenarios and service assurance.

- [API, database and state transitions](nagarseva/docs/public-data-api.md)
- [Optional field collection](pilot/field_collection.md)
- [Historical acquisition archive](research/final_report.md) and [dataset inventory](research/dataset_inventory.csv)
- [Local/test port configuration](research/local_runtime.md)

## Five screens, one workflow

1. **Overview** — settlement coverage, data gaps and services awaiting verification.
2. **Settlement map** — imported boundaries, name/ward search, indicator details and explicitly linked projects.
3. **Priorities** — configurable weights, a paginated ranking and the five input contributions; missing evidence stays unranked.
4. **Scenarios** — compare improvement and redevelopment costs, coverage and disruption using editable assumptions.
5. **Service Assurance** — planned works, physical completion, uploaded evidence, measurements, review, issues and audit history.

The priority example in the brief is **65.0/100**, not 65.5. Unknown indicators stay missing; clusters with missing positive-weight inputs receive an interval and no rank. No eligibility or resident-relocation decision is automated.

## Run locally

Use Python 3.12 and Node 24. Public data browsing requires no model training or source API key.

```bash
cd nagarseva
python3.12 -m venv .venv
.venv/bin/python -m pip install -r model/requirements-urban.txt
npm --prefix website ci
```

Start the API:

```bash
.venv/bin/python -m uvicorn model.api.urban:app --host 127.0.0.1 --port 8000
```

In another terminal, from `nagarseva`:

```bash
npm --prefix website run dev
```

Open **http://localhost:5173**. API documentation: http://localhost:8000/docs. If the API is unavailable, the app explicitly offers a browser sandbox; those records remain separate from server records. Uploads accept consented demo files, up to 2 MiB. SQLite operational files are ignored by Git.

From this existing checkout, `bash start-local.sh` installs missing runtime packages
and starts both processes, with owned-process cleanup on exit. The workspace shows
an error/retry when its API is unavailable; it never silently substitutes synthetic
data. A fresh checkout can import your own data without running the acquisition pipeline.
To use explicit free ports without stopping another service:

```bash
URBANSAARTHI_API_PORT=8001 URBANSAARTHI_WEB_PORT=5174 bash start-local.sh
```

This prints the actual frontend/API URLs and sets the frontend proxy accordingly.

For authorized work/complaint/inspection records, configure the API environment
before running the launcher. Choose a private local key and enter the same value
through **Data & access** in the application:

```bash
read -rsp 'Choose a private local officer key: ' NAGARSEVA_OFFICER_KEY
export NAGARSEVA_OFFICER_KEY
export NAGARSEVA_MODE=pilot-prototype
export URBANSAARTHI_EVIDENCE_STORAGE=sqlite  # optional consented uploads
bash start-local.sh
```

See [.env.example](.env.example). Do not place the officer key in a frontend variable.
SQLite and the versioned schema are initialized automatically. Keep the API bound
to loopback for local development; shared keys are not production identity/RBAC.

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

Calculations run deterministically in Python and the browser. Current local results
are recorded in [the final report](research/final_report.md) and
[Chromium workflow results](research/verification/browser_results.json). Prior CI
artifacts in `integration/` retain their original dates and validation scope.

Run checks from the repository root:

```bash
PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest tests nagarseva/tests/test_urban.py nagarseva/model/tests deploy/aws/tests submission/scripts/tests .github/tests -q
npm --prefix nagarseva/website test
npm --prefix nagarseva/website run build
# System Chromium + Playwright; uses a disposable database and owned ports.
uv pip install --python nagarseva/.venv/bin/python playwright==1.56.0
CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_public_browser.py
CHROMIUM_PATH=/usr/bin/chromium nagarseva/.venv/bin/python tests/check_field_collection_browser.py
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
