# UrbanSaarthi — interface and workflow quality audit

Completed 29 October 2026. Scope: current synthetic application, all main sections,
retained planning routes, English/Hindi/Marathi, desktop and 390px mobile layouts.
No real government records, production deployment or field outcomes were validated.

## Fixed

- **Map:** street tiles were off by default, polygons were difficult to target at
  low zoom, and camera fits could override the user's position. Street context is
  now enabled, nearby records have clickable grouped targets, selection fits actual
  geometry and synchronizes the paginated row. Sorting, language changes and unrelated
  snapshot updates preserve camera position and polygon elements. Initial-fit timing
  and Leaflet event-handler lifecycle issues were fixed.
- **Offline map:** unavailable tiles now expose an accurate coordinate grid, scale,
  center/zoom readout and retry. All synthetic geometry and list selection remain usable.
- **Copy:** ordinary headings, buttons, statuses, charts and displayed names use
  natural civic language. Repeated per-card and per-service demo labels were removed.
  A persistent synthetic-data disclaimer, full explanation, map provenance, source/privacy
  warnings and export notices remain. Stored records and stable IDs were not renamed;
  name aliases affect presentation only. No real settlement or government agency names
  were introduced.
- **Housing:** assessment details were effectively hidden from visitors without an
  administrator key. Read-only fields and notes are now visible, with edits protected.
- **Community:** follow-up events now retain previous and new response/status values,
  so later moderation does not erase earlier responses from the history.
- **Issues:** the status editor offers only transitions accepted by the backend.
- **Projects:** creation deep links respect the same access gate as the Create action;
  overdue milestones use the India calendar; unknown project references show an
  unavailable state. Settlement filters also initialize from linked URLs.
- **Reports:** supporting summary counts and project-stage breakdowns now follow the
  selected settlement. The interface explains that dates apply to the selected report
  table and CSV, since datasets have different date meanings.
- **Visits:** inverted date filters show a validation message; the Upcoming dashboard
  link applies the same date condition as its count instead of including overdue visits.
- **Localization:** visible field errors update immediately when language changes;
  search matches both localized display names and stable source IDs. Event timestamps
  display in Asia/Kolkata while calendar-only dates retain their supplied day.
- **Navigation:** trailing slashes and reports/community aliases resolve consistently;
  an unknown Projects tab falls back to the project directory instead of a blank view.

## Verification actually executed

| Check | Result |
| --- | --- |
| Full Python regression command from README | **382 passed**, 4 existing dependency/legacy warnings |
| `npm --prefix nagarseva/website test` | **48 passed**, 0 failed |
| Repository lint (`tsc --noEmit`) | Passed |
| App TypeScript with `--noUnusedLocals --noUnusedParameters` | Passed |
| `npm --prefix nagarseva/website run build` | Passed; nonblocking bundle-size/static-dynamic import advisories remain |
| `tests/check_synthetic_integration_browser.py` | **12 workflow groups passed**, zero page errors; production build; 16 routes across 3 languages; file onboarding/CSV/reset/error recovery |
| `tests/check_civic_management_browser.py` | **13 workflow groups passed**, zero page errors; projects, milestones, housing, issue-related administration, feedback, visits, reports and validation |
| `tests/check_civic_map_browser.py` | **5 workflow groups passed**, zero page errors; live street tiles and deliberately blocked-provider fallback |
| `git diff --check` | Passed |
| Running local workspace before/after owned-server restart | Identical snapshot checksum; no records reset or deleted |

The two mutation-oriented browser suites use disposable SQLite databases and owned
ports. The map suite is read-only against the running local application. Live
OpenStreetMap tiles loaded successfully during map QA; network availability remains
external to the application. The failed-provider check uses an intentional network block.

Browser screenshots and detailed results are under `.runtime/map-polish/`,
`.runtime/civic-management-browser/`, `.runtime/integration-readiness/` and
`.runtime/ui-polish/`. Earlier reports retain their original implementation/check dates.

## Current configuration and limits

The local app is running at **http://localhost:5173** with API port **8000**.
The active adapter remains synthetic SQLite. Its current workspace contains
100 settlements, 24 wards, 60 issues, 20 projects, 40 milestones and 30 visits;
housing assessments and community feedback are initially empty.

- No blocking runtime error remains in the exercised flows; this is not a guarantee
  against every possible input or future environment change.
- Protected actions and private controlled imports require `NAGARSEVA_OFFICER_KEY`.
  The current local server has no key configured, so these actions remain explicitly
  gated. Authorized paths were tested using temporary test credentials.
- Optional private image storage is disabled on the current server; its setup is
  explained in the application and README.
- No government API or verified real-data adapter is active. Controlled file imports
  stay isolated and do not replace the synthetic application records.
- The production build still reports a bundle-optimization advisory around the
  approximately 598 kB main entry. It does not prevent startup or production builds.

## Main implementation files

Map: `src/civic/CivicMap.tsx`, `mapState.ts`, map rules in `civic.css`.
Copy: `src/i18n/demoMessages.ts`, `integrationMessages.ts`, `messages.ts`, `locale.ts`.
Workflow fixes: `CivicWorkspace.tsx`, `DemoDashboard.tsx`, `DemoSettlements.tsx`,
`DemoIssues.tsx`, `DemoProjects.tsx`, `DemoHousing.tsx`, `DemoVisits.tsx`,
`DemoReports.tsx`, `analytics.ts`, `ui.tsx`, and `model/api/civic_demo.py`.
Frontend paths above are relative to `nagarseva/website/`.

Tests: `tests/check_civic_management_browser.py`, `check_civic_map_browser.py`,
`check_synthetic_integration_browser.py`, `test_civic_demo.py`, and the frontend
`civic.test.mjs`, `mapState.test.mjs` and `locale.test.mjs` suites.
