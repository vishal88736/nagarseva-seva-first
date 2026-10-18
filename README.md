# UrbanSaarthi

Explainable settlement prioritization, hypothetical intervention comparison and basic-service assurance for a Maharashtra urban-development challenge prototype.

**18 October 2026:** the default workspace now uses acquired public data: **7,106
validated OSM geometries, 156 printed SRA M/E map labels and 25 published scheme
rows**. The labels and schemes have no acquired georeferenced polygons. Current
service indicators remain missing; no real cluster is ranked. The existing synthetic
five-cluster sandbox remains available through an explicit mode switch.

- [Acquisition results and source limitations](research/data_availability.md)
- [Dataset inventory](research/dataset_inventory.csv), [quality report](research/data_quality_report.md), [join strategy](research/join_strategy.md)
- [API, database migration and state transitions](nagarseva/docs/public-data-api.md)
- [Optional Kobo/ODK field workflow](pilot/field_collection.md)
- [Executed results](research/final_report.md) and [dead-code cleanup](research/cleanup.md)

## Five screens, one workflow

1. **Overview** — acquired record coverage, rankability and services awaiting review.
2. **Explore Settlements** — interactive Leaflet map, deficit filters, source cards and missing data.
3. **Prioritize Needs** — configurable weighted scores, explanations, uncertainty intervals and ranking sensitivity.
4. **Compare Scenarios** — two in-place options, conditional relocation thought experiment, cost/access/disruption assumptions.
5. **Service Assurance** — planned works, physical completion, uploaded evidence, measurements, review, issues and audit history.

The priority example in the brief is **65.0/100**, not 65.5. Unknown indicators stay missing; clusters with missing positive-weight inputs receive an interval and no rank. No eligibility or resident-relocation decision is automated.

## Run locally

Use Python 3.12 and Node 24. No model training or API key is required for the focused demo.

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
and starts both processes, with owned-process cleanup on exit. Acquired mode shows
an error/retry when its API is unavailable; it never silently substitutes synthetic
data. A fresh checkout needs the acquisition steps below before real records appear.

For authorized work/complaint/inspection records, configure the API environment
before running the launcher. Choose a private local key and enter the same value
through **Officer access** in the application:

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
# Poppler's pdftotext/pdfinfo are required for the SRA reference map.
nagarseva/.venv/bin/python scripts/acquire_data.py
```

The staged runner continues after source failures and records them in the inventory.
It never treats a failed source as a successful dataset. Successful downloads are
cached with checked SHA-256 hashes; `--refresh` rechecks sources and preserves older
content-addressed originals. No large Geofabrik extract is downloaded for this pilot.
Raw files are in `data/raw/{sra,census,osm,other}` as applicable, cleaned files in
`data/processed`, and request/quality manifests in `data/metadata`. Source files are
not committed automatically. No source credentials are required or bypassed.

Individual repeatable stages:

```bash
nagarseva/.venv/bin/python scripts/inspect_sra_layers.py
nagarseva/.venv/bin/python scripts/ingest_sra.py
nagarseva/.venv/bin/python scripts/ingest_sra_projects.py
nagarseva/.venv/bin/python scripts/ingest_osm.py
nagarseva/.venv/bin/python scripts/ingest_census.py
nagarseva/.venv/bin/python scripts/prepare_real_data.py
nagarseva/.venv/bin/python scripts/prepare_demo_data.py
nagarseva/.venv/bin/python scripts/validate_datasets.py
```

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
geometry and observations. SRA feature services timed out; Census assets could not
be downloaded because HTTPS certificate validation failed. The 2024 PDF labels are
not current boundaries, OSM mappings do not prove service operation, and a shared CTS
string does not establish a project join. No current service baseline, official cost
estimate, approved ward pilot or field impact is claimed.

Calculations run deterministically in Python and the browser. Current local results
are recorded in [the final report](research/final_report.md) and
[Chromium workflow results](research/verification/browser_results.json). Prior CI
artifacts in `integration/` retain their original dates and validation scope.

Run checks from the repository root:

```bash
PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest tests nagarseva/tests/test_urban.py deploy/aws/tests/test_hosted.py -q
npm --prefix nagarseva/website test
npm --prefix nagarseva/website run build
# System Chromium + Playwright; uses a disposable database and owned ports.
uv pip install --python nagarseva/.venv/bin/python playwright==1.56.0
nagarseva/.venv/bin/python tests/check_public_browser.py
```

Full retained model checks additionally require `nagarseva/model/requirements.txt`
and `PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest nagarseva/model/tests -q`.
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
