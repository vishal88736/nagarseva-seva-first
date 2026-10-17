# NagarSeva implementation and pilot guide

Version 0.3.0 · Updated 2026-10-11

## Purpose and implemented behavior

NagarSeva connects housing planning to resident-verified service assurance. A selected project is shared across the map, detail, simulator, service record, resident portal and pilot workspace. The priority/intervention/cost training baseline remains synthetic. Source-labelled pilot locations and observations are distinct records.

The principal demonstration is: report → assignment → work → recorded repair evidence → resident confirmation or dispute → updated service record. There is no automatic displacement, eligibility, demolition or statutory approval decision.

## Architecture

- React 18, TypeScript and Vite provide a multilingual frontend, role entry points, per-project scenario state, Leaflet canvas maps for every valid location, responsive form layouts, and charts/comparisons. Caption and legend occupy a separate map footer. Imports are included in city/priority filters.
- FastAPI validates request bodies and exposes housing planning and operational records.
- SQLite persists complaints, receipt-token hashes, observation histories, service commitments, approved pilot locations and evaluations. It uses transaction-scoped connections, immediate write transactions, parameterized SQL and WAL.
- SciPy/HiGHS solves integer allocations with checked budget, vulnerable-share and distinct ward coverage constraints. The equal-ward baseline is independently solved with additional per-ward budget caps.
- Saved sklearn models support the synthetic planning demonstration. Priority accuracy represents agreement with a constructed policy target. Feature explanations are normalized signals, not SHAP attributions. The service record makes no 90-day forecast claim.

## Main files

| File | Responsibility |
| --- | --- |
| model/api/main.py | Routes, officer/receipt checks, transitions, aggregates and pilot imports |
| model/api/schemas.py | Finite numeric inputs, bounded fields, observation dates and source requirements |
| model/api/store.py | SQLite storage and atomic complaint/observation changes |
| model/src/service_records.py | Accepted evidence, explicit targets, provenance, missing/stale handling |
| model/src/allocation.py | Integer allocation, actual baseline and budget scenarios |
| model/src/eligibility.py | PMAY-U 2.0 pathways and cited review date |
| model/src/public_context.py | Live area weather, units/date validation, persistent cache and outages |
| shared/public-sources.json | Dated publisher catalog, scope, reuse conditions and benchmark references |
| website/src/lib/api.ts | Typed API, receipt handling, exports and explicit offline failures |
| website/src/lib/affordability.ts | Household recurring, income-loss and transition mathematics |
| website/src/components/Records.tsx | Observation forms, service evidence, history and officer access |
| website/src/pages/Pilot.tsx | Location imports, commitments, observations and user evaluations |
| website/src/pages/Sources.tsx | Multilingual source library and forecast view |
| tests/e2e_full_suite.py | Isolated full browser workflow and responsive/offline checks |

## Complaint state machine

Received reports can be assigned. Assigned/reopened work can be started. Assigned or in-progress work can be submitted for resident confirmation. For a measured service, completion requires a matching, dated, sourced after-repair measurement. Demo/real evidence must match the complaint scope.

Only a valid resident receipt can confirm or dispute a pending repair. Confirmation closes the complaint and accepts its measurement as resident-confirmed. Dispute reopens the complaint and marks the measurement disputed. Pending/disputed observations do not update the accepted service record. Closed complaints cannot be escalated or completed again. State conflicts return HTTP 409 and retain history.

Officers may correct suggested category/urgency on assignment. Deadlines are based on receipt time and the reviewed target; assigning work does not restart the SLA clock. Escalations are recorded actions. Overdue state and response/closure metrics are derived from dates and states.

## Provenance and assurance

Each service record exposes value, unit, date, source/method, evidence link, verification state and history. Targets expose source, department and approval metadata. Default targets are visibly demo assumptions. Unknown and observations older than 30 days are excluded from the attainment index. A confirmed issue is not a whole-ward certification or a potable-water test.

Pilot locations require a unique PILOT identifier, coordinates, area/household/population fields, licence, source and importing approver. Unknown features stay unknown. Without an independently approved priority review score, the location is Unassessed and excluded from allocation. Synthetic intervention probabilities are not generated for it.

## Household comparison

Monthly burden = rent/EMI + maintenance + utilities + transport + monthly income loss.

Remaining income = household income − monthly burden.

Temporary cost = temporary rent × temporary months + one-time moving cost.

The user chooses the percentage planning limit. It is not an official eligibility or lender affordability criterion. Starting costs are explicitly editable illustrative assumptions. Project assumptions and household scenarios are persisted per project in browser storage and exported as JSON.

Financial screening marks a project Not viable when required rehab area exceeds available built-up area, including scenarios with positive financial margins. The area shortfall is shown. A market break-even rate is unknown when the saleable share is zero.

## Measured pilot evidence

Actual pilot metrics include only consented entries marked non-synthetic. Paired timing differences require a completed usability task and both baseline and app timings. Classification trials are excluded from usability completion/timing metrics. Classification agreement is grouped by language with sample sizes. Empty sets return unknown metrics instead of fabricated success percentages. Anonymous participant references and feedback make usability findings reviewable. The team must perform the field observations/interviews; the software does not create them.

## Privacy and access

The default mode is local demo. Configure NAGARSEVA_MODE=pilot and a private NAGARSEVA_OFFICER_KEY for a pilot. Officer queue/actions/evidence operations require X-Officer-Key. Resident report access/confirmation requires X-Receipt-Token; the database stores only a hash. The resident portal reads only receipts stored/restored on that device. Keys and local SQLite files are excluded from Git.

Production authentication, retention governance and rate limiting need a deployment-specific implementation. Do not collect personal identifiers in free text or upload original identity documents.

## Offline behavior and exports

Read-only planning screens have a labelled representative synthetic fallback. Counts reflect the actual sample size. Financial sensitivity is computed from the same formula locally. Creating, changing, confirming or verifying records never returns fake success while offline. The report form preserves input and supports a separately labelled local draft. If browser persistence is blocked, a notice explains that temporary state expires on refresh/closure; receipt download still works.

JSON project briefs, financial/household scenarios and private receipts are downloadable. Officer queues and selected allocations export CSV, with formula prefixes neutralized. Pilot evidence exports JSON with provenance and scope. No inactive PDF or assignment affordances remain.

## Policy source

PMAY-U 2.0 national pathway guidance: https://pmaymis.gov.in/pmaymis2_2024/PmayFAQ.aspx, reviewed 2026-10-11. BLC, AHP, ARH and ISS are screened conservatively using declared answers and additional verification conditions. SRA requires statutory tenure/household review; time in a settlement alone establishes no eligibility.

## Public source connections

Maps have OpenStreetMap geography with visible contributor attribution and a schematic fallback. The source library presents official housing/service references, source dates, reuse terms, availability limits and resident handoffs. Published SLB benchmarks remain references; incompatible indicator units are explicitly identified. Census 2011 town aggregates are linked without reproducing data whose publisher requests permission.

The source page loads a live seven-day Open-Meteo area forecast and exports its provenance. The provider receives only coordinates rounded to 0.1 degrees. A persistent 30-minute cache, retry backoff, bounded stale results and explicit unavailable/disabled states prevent invented weather. Forecasts never create field observations, change planning scores or enter verified service metrics. Free API use is noncommercial. See PUBLIC_INTEGRATIONS.md for endpoints, configuration, primary source links and limitations.

## Running and testing

Follow README.md for local startup, configurable API targets, pilot access and database storage. `make test` runs backend/API regressions and a production build. `python3 -u tests/e2e_full_suite.py` runs isolated browser verification with a temporary database. In the managed sandbox used during development, API/browser tests need approved unrestricted execution because asynchronous wakeups stall under sandbox restrictions.

Verification on 2026-10-11: 25 backend tests passed; the production build passed; an isolated browser walkthrough passed report-to-confirmation, receipts, service updates, shared context, scenario persistence, exports, mobile screens, Hindi/Marathi UI, pilot observations/reviews/evaluations/commitments/imports, blocked-storage receipt delivery, offline drafts, source references and forecast export/outage states. A separate live request returned seven forecast days from Open-Meteo. Captured test screenshots are labelled synthetic browser demonstrations.

All 330 production-build layout cases passed with no detected text collisions or horizontal overflow across every page, expanded forms, access controls, dark mode and forecast failure states at five widths in all three languages. See PROJECT_STATUS.md for the final result and the remaining real-data and deployment work.
