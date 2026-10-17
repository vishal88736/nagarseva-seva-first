# UrbanSaarthi

Explainable settlement prioritization, hypothetical intervention comparison and basic-service assurance for a Maharashtra urban-development challenge prototype.

## Five screens, one workflow

1. **Overview** — demonstration cluster coverage, rankability and services awaiting review.
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

Set `NAGARSEVA_OFFICER_KEY` on the API and enter it through **Officer access** to protect server records. Do not put the key in a frontend build or commit it. This shared-key demo is not production identity or role management.

## Deploy on AWS

Use the [AWS CloudShell deployment guide](deploy/aws/README.md) for one EC2 instance, persistent encrypted-volume demo records and an HTTPS CloudFront address. Active credits must cover usage; this is not permanently free hosting. The guide and readiness CI do not imply that an AWS account has already been provisioned.

## Data and validation boundaries

The five cluster polygons, normalized deficit indicators, roads, amenities and household/cost assumptions are **synthetic**. No current field-service baseline or permitted settlement boundary dataset has been acquired. The three attributed SRA listing records are a separate desk case with no geometry or service claims. Mumbai is a demonstration context; no ward-level pilot partnership has been secured.

Calculations run deterministically in Python and the browser, with API consistency checks when connected. The final CI executes the retained backend suite, new calculation/API tests, browser-engine tests, frontend production build and actual Chromium workflow. [Executed UrbanSaarthi browser results](integration/urban-validation.json) and [application CI results](integration/ci-validation.json) record the actual boundary. No field impact, independent ranking accuracy, resident consent or government adoption is claimed. Dependency remediation and actual advisory outcomes are tracked in `integration/security-audit-before.json` and the subsequent audit report.

## Project materials

- [Architecture, formulas, state transitions and evaluation](nagarseva/docs/urbansaarthi.md)
- [Focused application guide](nagarseva/README.md)
- [Research overview](research/README.md) and [executive research findings](research/research_summary.md)
- [Evidence workbench](prototype/README.md), also available at `/evidence/`
- [UrbanSaarthi submission pack](submission/README.md): official-template deck and PDF, budget, answers and pitch. Authenticated form/upload limits remain unverified and personal fields remain omitted.
- [Original source lineage](integration/source-manifest.json) and [merge record](integration/README.md)

The original GitHub repository remains untouched. This fresh repository preserves the imported model artifacts and legacy components; the original interface is in `nagarseva/website/src/LegacyApp.tsx`. UrbanSaarthi's default API does not use those synthetic-trained models. PostgreSQL/PostGIS and agency integrations are later production work; the prototype uses SQLite and a small labelled graph.

The [prepared pilot kit](pilot/README.md) identifies a prospective BMC M-East water-domain owner and includes an unsent request, independent-baseline protocol, observation/indicator rules and blank quote templates. Prepared protocols are not completed field evidence.
