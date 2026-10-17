# NagarSeva

**Plan housing improvements. Verify that residents receive the promised services.**

NagarSeva connects housing prioritization, redevelopment finance, household affordability, budget allocation and resident-verified service resolution. Its planning baseline contains seeded synthetic MMR pockets. Local operational records persist in SQLite; approved pilot locations, consented observations and user evaluations have independent source and verification labels.

No field pilot or realized financial saving is claimed. Real-pilot metrics start empty. Synthetic model accuracy measures performance on constructed labels, not policy effectiveness. Methodology reads benchmark values from the saved artifact files, including the cost model's negative held-out R²; project quotes and independent validation are still required.

**Public sources & weather** adds OpenStreetMap geography, a dated seven-day Open-Meteo area forecast, national service benchmark references, and official PMAY-U/SRA/BMC/IMD links. Public context is kept separate from synthetic planning data and verified field evidence. See [public integrations and source terms](docs/PUBLIC_INTEGRATIONS.md).

## Run locally

From `nagarseva`, with the existing dependencies installed:

```bash
make api  # terminal 1: API on localhost:8000
make web  # terminal 2: website on localhost:5173
```

For a fresh installation: `make setup`, then `make train`. `make train` regenerates synthetic planning data and models; it does not replace SQLite operational records. `make all` performs installation/training and starts both processes. API reference: http://localhost:8000/docs.

The website proxies `/api` to the backend. `NAGARSEVA_API_TARGET` changes the Vite development/preview proxy target. For a separate hosted API, build with `VITE_API_BASE_URL` set to its URL and configure `NAGARSEVA_CORS_ORIGINS` accordingly. No deployment is included in this change.

## A complete demonstration

1. Choose **Guided demo**. It has six manual steps and does not change pages while you are working.
2. Select a project on the map. The same project stays selected in its detail, financial scenario, service record, resident portal and pilot workspace.
3. Download its JSON project brief. Inspect the source-labelled service record and the synthetic priority/intervention limits.
4. Compare redevelopment finance and the household's recurring rent/EMI, maintenance, utilities, transport and income loss. Temporary rent and moving expenses are shown separately. Every household assumption is editable and the scenario is saved per project on this browser.
5. Submit a **demo report** in the resident portal and download its private receipt.
6. In Officer view, review category/urgency, enter officer, department and action notes, then assign and start work.
7. Record the after-repair service measurement, timestamp, source/method and evidence note/link. Submit the repair for confirmation.
8. Return to the resident portal. Review the proposed evidence, then confirm resolution or dispute it. A dispute reopens the report; the disputed reading is excluded. An accepted reading updates the project service record and ward aggregates.
9. Refresh or restart the backend: records and history persist. Operational counts, SLA breaches and response metrics are calculated from stored records.

The map renders every valid location with a canvas renderer and fits the filtered locations. Its caption and legend sit below the map, keeping them separate from map content. Imported cities and Unassessed records can be filtered.

A resident receipt grants access to that report and its confirmation controls. The public resident view does not list other residents' complaints. Store the downloaded receipt privately; restoring a receipt requires its reference and token. Server storage contains a hash of the token. When browser storage is blocked or full, the app reports it, keeps temporary state until page refresh/closure, and still delivers the private receipt for download.

Financial screening rejects a scenario whose required rehab area exceeds available built-up area, even when financial assumptions produce a positive margin. With no saleable share, a market break-even rate is unavailable. Capacity, construction, fees and household costs remain editable planning assumptions.

## Allocation and comparisons

The SciPy/HiGHS integer optimizer checks total budget, minimum selected-pocket vulnerable share, and **distinct city/ward** coverage. Vulnerability is explicitly a priority ≥65 proxy. Each published plan is checked again against these constraints. An infeasible or timed-out search returns an explanation and no fabricated plan.

The equal-ward baseline is solved independently using the same input cost and risk-weighted population proxy, total budget, vulnerable share and coverage constraints, with an additional equal budget cap for each ward. Its unused budget and infeasibility are visible. Budget scenarios use the same constraints. These are screening allocations using synthetic cost/impact assumptions; they are not measured beneficiaries, redevelopment DPR budgets or realized savings.

## Service evidence and commitments

Each service shows the latest accepted value and unit, target and source, observation date, verification state, responsible department and observation history. Unknown and readings older than 30 days are excluded from the attainment index. Baseline synthetic readings have no invented field date. Pending or disputed repair evidence does not change the accepted record.

Verification states: `reported`, `pending_confirmation`, `resident_confirmed`, `field_verified`, `disputed`. Resident confirmation does not certify a whole ward or establish water potability. Field verification is a recorded reviewer action, not government certification.

Default water, sanitation, power, waste and clinic targets are local demo assumptions. **Pilot evidence → Pilot setup** can record a project-specific commitment, unit-compatible target, responsible department, source reference/link and approver. Real commitments require a reference link. Changes retain a history.

## A real-data pilot

1. Configure officer access as described below.
2. Obtain licensed/approved location information and consent for collecting observations. Start with one project or ward.
3. Import one JSON location through **Pilot setup**. A schema/template is visible there. Required fields are `pocket_id` (unique `PILOT-…`), city, ward, lat, lon, area_sqm, households, population, source_label, source_url, licence, approved_by and consent. `avg_household_income_inr` and an independently approved `approved_priority_score` are optional.
4. Imported locations receive **no invented risk values, service readings or model scores**. A location without an approved review score remains Unassessed and is excluded from allocation. The synthetic-trained intervention model is not applied to it. The background MMR illustration remains schematic.
5. Record actual service observations, source, date, evidence and consent. A field reviewer can review recorded observations; pending repair evidence first requires resident confirmation.
6. Record anonymous task evaluations and independently labelled multilingual classification trials. The workspace reports sample sizes, completion, paired timing differences and classification agreement by language. Demo entries are excluded from these real-pilot metrics.
7. Export the evidence and document limitations. A small pilot supports exploratory usability conclusions, not citywide causal claims or a validated prioritization model.

Timing savings include only completed usability tasks with both timings. Classification trials have their own language metrics and do not enter usability completion rates or timing savings.

The system stores evidence supplied by the importing officer/reviewer; it cannot independently establish the truth of a field visit or licence. Do not import names, phone numbers, Aadhaar numbers or original identity documents. A field pilot and interviews still need to be carried out by the project team.

## Officer access and storage

The default is a local **demo** workspace. For a real pilot, set a strong private officer key and pilot mode before starting the API:

```bash
export NAGARSEVA_MODE=pilot
export NAGARSEVA_OFFICER_KEY='set-a-private-officer-key'
make api
```

Enter the key in **Officer access** in Officer view or Pilot evidence; it is kept in session storage, not the repository. Queue access, officer actions, evidence imports/reviews and evaluation writes require this key. Pilot mode with no key refuses these operations. A public production deployment would additionally require per-person identities, audit/access governance, retention controls and rate limiting.

The default database is `model/data/local/nagarseva.sqlite3`, ignored by Git. Override it with `NAGARSEVA_DB_PATH`. Keep SQLite backups with their WAL/SHM lifecycle managed correctly. Demo and real operational entries retain their own flags.

## Housing screening

The wizard screens PMAY-U 2.0 BLC/AHP/ARH/ISS pathways against declared income, urban residence, family pucca-house ownership and prior housing benefits. BLC land rights and ISS loan/property/area conditions are exposed as additional checks. Results are pathways for authority verification. Aadhaar availability and a ten-year stay do not produce an SRA entitlement.

Policy source and review date are shown in results: https://pmaymis.gov.in/pmaymis2_2024/PmayFAQ.aspx (reviewed 2026-10-11). Final eligibility remains with the relevant authority.

## Verification

```bash
make test
# Optional browser-test dependencies, installed once:
python3 -m pip install playwright
python3 -m playwright install chromium
python3 -u tests/e2e_full_suite.py
# With localhost running, audit pages, expanded forms and dark mode:
python3 -u tests/review_layout.py --matrix --assert-clean
```

Backend tests exercise API contracts, persistence, receipt privacy, action transitions, consent, confirmation/dispute effects, source-labelled pilot imports, explicit commitments, current screening, SLA calculations and allocation constraints. The production build type-checks the frontend. The browser suite starts isolated servers and a temporary database, checks the complete complaint flow, shared project context, exports, mobile layout and offline behavior, and writes screenshots to `/tmp`.

In this execution environment, AnyIO event-loop wakeups stall inside the restricted sandbox. Run API/browser verification with the execution environment's approved unrestricted test permission; ordinary installation environments do not require this sandbox-specific step.

See [current project status](docs/PROJECT_STATUS.md) for the delivery scope and remaining field/deployment work.
