# UrbanSaarthi end-to-end audit and fixes

Completed 30 October 2026 (Asia/Kolkata). The existing React/TypeScript/Vite,
Leaflet and FastAPI/SQLite architecture and working civic workflows were preserved.
This is a synthetic demonstration, not a verified government system. No real records
were invented, downloaded into the active workspace or mixed into its rankings.

**52 PASS, 6 PARTIAL, 0 unresolved FAIL** in the checklist below.
PARTIAL items identify honest source/configuration/human-review limits; they do not
represent simulated successful integrations. This evidence covers the exercised
inputs and states, not every possible future environment or payload.

The local app is running at **http://localhost:5173/dashboard**. From the original
parent directory, use `cd "nagarseva-seva-first"` then `bash start-local.sh`.
Running `npm run dev` in `seva first` fails because that parent has no package.json.

## What was fixed

Added XLSX inspection, sheet selection and safe parsing; real CSV templates;
required provenance; completeness; explicit import classification; dependency-safe
audited rollback; missing-input Partial scoring; methodology, what-if, budget,
planted anomaly, SLA and delay diagnostics; fixed-seed CLI reproduction; explicit
synthetic flags; source/date badges; self-hosted Devanagari; working CSV and browser
PDF exports. Completed locale formatting for remaining counts/targets and the
JSON Demo data watermark. Fixed contrast in headers, buttons, muted timestamps, selected rows
and retained comparison cards, keyboard focus and mobile navigation. A routed
font-loading failure in print previews was resolved by using a real Blob document
navigation and waiting for fonts before printing.

## Feature checklist with current file and line evidence

| ID / check | Result | What exists, was fixed and actually exercised | File and line | Remaining dependency/decision |
| --- | --- | --- | --- | --- |
| F01 · CSV/Excel upload, template, mapping, preview and row errors | PASS | Added bounded XLSX reading and visible-sheet selection; real CSV header-only templates. The browser parsed and imported an XLSX fixture, changed an actual column mapping, downloaded the exact original and exercised row errors. | [nagarseva/model/api/file_formats.py:10](../nagarseva/model/api/file_formats.py#L10) | None for the tested scope. |
| F02 · Required source, publisher, date, licence and link | PASS | All five fields are required on the server and in the form. Links are retained, never fetched; embedded credentials are rejected. Source date cannot be in the future in the India calendar. | [nagarseva/model/api/data_onboarding.py:64](../nagarseva/model/api/data_onboarding.py#L64) | None for the tested scope. |
| F03 · Official / Manually provided / Demo classification | PARTIAL | Demo and Manually provided · unverified badges work. An upload cannot select or assert Official; all receipts have sourceVerified:false. | [nagarseva/website/src/civic/SourceNote.tsx:5](../nagarseva/website/src/civic/SourceNote.tsx#L5) | An independently verified source and an authorized verification policy are needed before an Official status can be supported. |
| F04 · Completeness percentage | PASS | Import completeness counts nonempty transformed cells over all category schema cells. Required-field completeness is separate. Service completeness counts available service inputs. Neither certifies accuracy. | [nagarseva/model/api/data_onboarding.py:248](../nagarseva/model/api/data_onboarding.py#L248) | None for the tested scope. |
| F05 · Upload history, original preservation and rollback | PASS | Confirmed imports persist original bytes, hash, mapping, classification, provenance and timestamps. Authorized rollback requires confirmation and a reason, retains audit evidence, excludes archived batches and protects dependent imports. | [nagarseva/model/api/data_onboarding.py:323](../nagarseva/model/api/data_onboarding.py#L323) | None for the tested scope. |
| F06 · Missing-dataset empty states and upload prompt | PASS | All seven real-data categories currently report not_provided. Readiness and empty states link to the working onboarding interface. | [nagarseva/website/src/integration/DataIntegration.tsx:40](../nagarseva/website/src/integration/DataIntegration.tsx#L40) | None for the tested scope. |
| F07 · Missing-input scoring and Partial results | PASS | Missing factors are not treated as zero. Weights are normalized over available factors; unavailable weighted inputs and missing service cells mark results Partial. No usable factor yields an unavailable score. | [nagarseva/website/src/civic/analytics.ts:16](../nagarseva/website/src/civic/analytics.ts#L16) | None for the tested scope. |
| F08 · Map/ward table, search, combined filters, sorting and ranking | PASS | Shared records drive map and paginated directory. Stable-ID selections synchronize the polygon and table. Live street tiles and blocked-provider fallback both passed. | [nagarseva/website/src/civic/CivicMap.tsx:60](../nagarseva/website/src/civic/CivicMap.tsx#L60) | None for the tested scope. |
| F09 · Comparison and adjustable methodology weights | PASS | Existing comparison workflow is preserved. Methodology adds weight previews and authorized saved weights; a browser save and refresh confirmed SQLite persistence. | [nagarseva/website/src/civic/Methodology.tsx:11](../nagarseva/website/src/civic/Methodology.tsx#L11) | None for the tested scope. |
| F10 · CSV and PDF exports with sources and dates | PASS | CSV contains all filtered report fields, source/save/export metadata, localized display headers and formula protection. Browser Print / Save as PDF generated real PDFs in all three languages; every page was rendered for QA. | [nagarseva/website/src/civic/printReport.ts:6](../nagarseva/website/src/civic/printReport.ts#L6) | PDF is a browser print workflow and summarizes the first nine display columns; CSV contains all fields. This scope is explained in the interface. |
| F11 · Source and date under data charts, cards and tables | PASS | Shared source captions and explicit summary/related-record captions label Demo data, generator source and actual workspace save time. Imported previews/history show the supplied source and source date, or unavailable. | [nagarseva/website/src/civic/SourceNote.tsx:5](../nagarseva/website/src/civic/SourceNote.tsx#L5) | Workspace save time is explicitly labelled Saved; it is not a claimed real measurement date. |
| U01 · Valid file | PASS | A valid CSV and XLSX import completed in disposable SQLite with explicit provenance and confirmation. GeoJSON import also passed the regression browser suite. | [tests/test_audit_features.py:34](../tests/test_audit_features.py#L34) | None for the tested scope. |
| U02 · Missing columns | PASS | Missing identifier mapping was reported; manually mapping the real code column allowed validation. Missing row values and mappings are rejected. | [tests/test_audit_features.py:68](../tests/test_audit_features.py#L68) | None for the tested scope. |
| U03 · Wrong data types | PASS | Nonnumeric coverage/counts, bad dates, invalid ranges and formulas produce clear errors; numeric row errors retain source row 2. | [tests/test_audit_features.py:68](../tests/test_audit_features.py#L68) | None for the tested scope. |
| U04 · Duplicate rows/identifiers | PASS | Duplicate identifiers fail validation; cross-batch conflicts cannot silently overwrite records. Exact active retries are idempotent. | [tests/test_audit_features.py:68](../tests/test_audit_features.py#L68) | None for the tested scope. |
| U05 · Empty file | PASS | Zero-byte and header-only files are rejected without a new import or fake success. | [tests/test_audit_features.py:68](../tests/test_audit_features.py#L68) | None for the tested scope. |
| U06 · Very large file | PASS | A file of 5 MiB + 1 byte was rejected by both UI and API. It was not read into a preview or persisted. | [tests/test_audit_features.py:68](../tests/test_audit_features.py#L68) | None for the tested scope. |
| U07 · Workbook units, worksheet choice and safe formulas | PASS | Percentage-formatted 0.75 becomes displayed 75 with a disclosure; selected-sheet metadata is real. Original bytes stay unchanged. Formula/error cells are never evaluated. | [tests/test_audit_features.py:111](../tests/test_audit_features.py#L111) | None for the tested scope. |
| L01 · Hardcoded application text and resource parity | PASS | AST/key checks found no unhandled application JSX text, missing literal translation calls, missing parameters or missing locale keys. The three locale files each have 255 keys; the merged catalogue has 3012. | [nagarseva/website/tests/check_translation_audit.mjs:15](../nagarseva/website/tests/check_translation_audit.mjs#L15) | None for the tested scope. |
| L02 · Missing and unchanged translation keys | PASS | Missing keys: none. Parameter mismatches: none. Intentionally unchanged technical labels: CSV, SHA-256:, and · CTS in Hindi and Marathi (six entries). Proper names, source values, IDs, URLs and technical formulas remain unchanged. | [research/verification/translation_audit.json:1](../research/verification/translation_audit.json#L1) | None for the tested scope. |
| L03 · Dates, numbers, currency and units | PASS | Intl en-IN/hi-IN/mr-IN formatting is shared across UI and print reports. Full timestamps use Asia/Kolkata; calendar-only dates retain their day. CSV machine values retain ISO dates and numeric semantics, with localized display headers. | [nagarseva/website/src/i18n/locale.ts:31](../nagarseva/website/src/i18n/locale.ts#L31) | None for the tested scope. |
| L04 · Language persistence after refresh | PASS | English, Hindi and Marathi selections persisted across reloads in actual browser tests and updated the full current UI. | [nagarseva/website/src/i18n/locale.ts:12](../nagarseva/website/src/i18n/locale.ts#L12) | None for the tested scope. |
| L05 · Errors, tooltips, empty states, exports and methodology | PASS | Resource and parameter checks, nine populated upload previews, field-error switching and all-language PDF/CSV exports passed. Unknown uploaded source text is preserved rather than invented or mistranslated. | [tests/check_audit_workflows_browser.py:41](../tests/check_audit_workflows_browser.py#L41) | None for the tested scope. |
| L06 · Devanagari font loads and renders | PASS | Self-hosted Noto Sans Devanagari, with its OFL and source/hash manifest, loaded in Hindi and Marathi browser screens. Representative full-size screenshots and all PDF pages were visually inspected. | [nagarseva/website/src/civic/audit.css:1](../nagarseva/website/src/civic/audit.css#L1) | None for the tested scope. |
| L07 · Native Hindi and Marathi language quality | PARTIAL | There is no native-speaker certification. The review CSV lists all 104 new/overridden audit strings in English/Hindi/Marathi. Existing translations also remain linguistically unverified. | [research/translation_review.csv:1](../research/translation_review.csv#L1) | A native Hindi and Marathi reviewer should review technical and civic terminology, especially the examples listed below. |
| R01 · Every page at 375 / 768 / 1280 in three languages | PASS | 23 page/detail/dialog states × 3 widths × 3 languages = 207 screenshots, plus nine populated upload previews. Automated overflow/key/accessibility checks passed. Contact sheets cover every combination; full-size representative screens were inspected. | [tests/check_full_audit_browser.py:11](../tests/check_full_audit_browser.py#L11) | None for the tested scope. |
| R02 · Overflow, overlap, spacing, theme and readable tables | PASS | The examined states have no document overflow. Tables scroll within labelled keyboard-focusable regions. Pale background, navy text, teal controls, rounded white cards and Devanagari typography remain consistent. | [nagarseva/website/src/civic/audit.css:15](../nagarseva/website/src/civic/audit.css#L15) | None for the tested scope. |
| R03 · Loading, error and empty states | PASS | Backend failure and Retry recovery, missing datasets, zero assessments/feedback, unavailable tiles, invalid uploads and failed saves were exercised without invented success or metrics. | [tests/check_synthetic_integration_browser.py:42](../tests/check_synthetic_integration_browser.py#L42) | None for the tested scope. |
| A01 · Keyboard navigation, dialog focus and focus indicators | PASS | Native dialogs, semantic controls, visible focus, skip link and horizontally scrollable tables are retained. Mobile navigation traps focus, closes with Escape and restores focus. | [nagarseva/website/src/civic/CivicWorkspace.tsx:47](../nagarseva/website/src/civic/CivicWorkspace.tsx#L47) | None for the tested scope. |
| A02 · Labels, alt text and automated accessibility | PASS | WCAG 2 A/AA and 2.1 AA axe checks report no violations in the 216 examined states. Brand artwork is decorative inside a labelled button; controls have accessible labels. | [nagarseva/website/src/civic/ui.tsx:14](../nagarseva/website/src/civic/ui.tsx#L14) | None for the tested scope. |
| A03 · Colour-blind-safe charts and status information | PASS | Charts include numeric values and text labels. Status and selection are not conveyed by colour alone. Contrast fixes cover active controls, headers, selected-row links, muted text and validation timestamps. | [nagarseva/website/src/civic/audit.css:15](../nagarseva/website/src/civic/audit.css#L15) | None for the tested scope. |
| A04 · Assistive-technology certification | PARTIAL | Automated Chromium checks and keyboard tests are evidence, not a screen-reader certification. | [tests/check_full_audit_browser.py:41](../tests/check_full_audit_browser.py#L41) | A manual review with the intended screen reader/device remains useful before public deployment. |
| S01 · Seeded fictional city and ward names | PASS | The seed=96 CLI generated byte-identical files twice. Demo City 96 contains only numbered fictional Demo Ward and Demo Settlement source names; no real ward/slum names are generated. | [scripts/generate_demo_city.py:7](../scripts/generate_demo_city.py#L7) | None for the tested scope. |
| S02 · is_synthetic on every synthetic record | PASS | All active entity collections and nested operation/indicator histories receive explicit flags. Existing stored civic values were preserved while adding metadata. | [nagarseva/model/api/civic_demo.py:41](../nagarseva/model/api/civic_demo.py#L41) | None for the tested scope. |
| S03 · Permanent Demo data banner | PASS | A visible banner and header indicator remain across every route. Ordinary record display names stay concise; stable DEMO IDs and fictional source names are preserved. | [nagarseva/website/src/civic/CivicWorkspace.tsx:64](../nagarseva/website/src/civic/CivicWorkspace.tsx#L64) | None for the tested scope. |
| S04 · Demo data badges on data visualizations | PASS | Shared Panels, Tables, Progress bars, summary cards, mini cards, related records and map source captions carry the badge. | [nagarseva/website/src/civic/ui.tsx:8](../nagarseva/website/src/civic/ui.tsx#L8) | None for the tested scope. |
| S05 · Synthetic exports watermarked Demo data | PASS | CSV notice and record metadata, JSON source flags and all PDF pages identify Demo data. The exact English watermark remains in multilingual exports. | [nagarseva/website/src/civic/services.ts:20](../nagarseva/website/src/civic/services.ts#L20) | None for the tested scope. |
| S06 · Synthetic/real ranking isolation | PASS | Supplied batches cannot enter the synthetic adapter or rankings. Imports stay active:false and sourceVerified:false. There is no mixed-source ranking option. | [nagarseva/model/api/data_onboarding.py:319](../nagarseva/model/api/data_onboarding.py#L319) | A future mixed-source opt-in, warning and compatible source-specific methodology have not been implemented; no mixing is currently possible. |
| S07 · What-if simulator | PASS | Changing a service estimate recalculates household-weighted before/after values for the same settlement collection. It is explicitly a preview and does not alter saved indicators. | [nagarseva/website/src/civic/Methodology.tsx:16](../nagarseva/website/src/civic/Methodology.tsx#L16) | None for the tested scope. |
| S08 · Budget allocation | PASS | Actual priority order and service gaps determine households needing coverage. User-supplied budget/unit cost are assumptions; cents-based allocation cannot exceed the budget and skips unknown inputs. | [nagarseva/website/src/civic/simulations.ts:24](../nagarseva/website/src/civic/simulations.ts#L24) | None for the tested scope. |
| S09 · Weight tuning | PASS | Previewed rankings update immediately; all-zero weights fail validation. Authorized saved weights survived refresh in the browser test. | [nagarseva/website/src/civic/Methodology.tsx:19](../nagarseva/website/src/civic/Methodology.tsx#L19) | None for the tested scope. |
| S10 · Anomaly detector with planted cases | PASS | Three separate seeded fixtures test household ratio >8, service coverage <10%, and a missing service value. The real predicates caught 3/3. Active settlement metrics are never overwritten by planted cases. | [nagarseva/website/src/civic/simulations.ts:4](../nagarseva/website/src/civic/simulations.ts#L4) | None for the tested scope. |
| S11 · Grievance SLA tracker | PASS | Elapsed time is derived from actual stored submission/resolution timestamps; missing/invalid resolution dates stay unavailable. High/medium/low 2/7/14-day targets are explicitly demo assumptions. Filtering and pagination work. | [nagarseva/website/src/civic/simulations.ts:12](../nagarseva/website/src/civic/simulations.ts#L12) | None for the tested scope. |
| S12 · Project delay-risk flag | PASS | Unfinished projects past expected end dates are High; overdue unfinished milestones produce Watch. The rule does not imply an official risk assessment or resolve complaints. | [nagarseva/website/src/civic/simulations.ts:17](../nagarseva/website/src/civic/simulations.ts#L17) | None for the tested scope. |
| S13 · Large-dataset performance test | PASS | An actual separate 10,000-settlement workload generated, validated, filtered and sorted in 420.81 ms on this machine. It did not persist or change active counts. | [nagarseva/model/api/civic_demo.py:308](../nagarseva/model/api/civic_demo.py#L308) | This is a local generator/validation/filter/sort diagnostic, not a concurrent-user test or a 10,000-polygon browser-load guarantee. |
| S14 · Synthetic methodology documentation | PASS | The methodology explains fixed-seed generation, fictional geometry, household-weighted coverage, service gaps, factor scales, missing data, targets, anomaly rules, budget assumptions and source isolation. | [nagarseva/website/src/civic/Methodology.tsx:18](../nagarseva/website/src/civic/Methodology.tsx#L18) | None for the tested scope. |
| C01 · Settlement detail, housing and six basic services | PASS | Profile, linked records, targets, gaps and inspection history use shared IDs and records; absent values remain unavailable. | [nagarseva/website/src/civic/DemoSettlements.tsx:9](../nagarseva/website/src/civic/DemoSettlements.tsx#L9) | None for the tested scope. |
| C02 · Issue creation, follow-up and dashboard updates | PASS | Public issue creation persists to SQLite before success; authorized status/assignment/notes produce actual history and activity. Allowed transitions match the backend. | [nagarseva/website/src/civic/DemoIssues.tsx:10](../nagarseva/website/src/civic/DemoIssues.tsx#L10) | None for the tested scope. |
| C03 · Projects, milestones and progress persistence | PASS | Creation, progress editing, required milestone completion dates, rejected keys and reload persistence passed in a disposable database. | [nagarseva/website/src/civic/DemoProjects.tsx:11](../nagarseva/website/src/civic/DemoProjects.tsx#L11) | None for the tested scope. |
| C04 · Visits, cancellation and explicit indicator updates | PASS | Scheduling/cancellation persist; completing a visit does not silently change indicators. Applying findings requires an explicit confirmed operation with a change history. | [nagarseva/website/src/civic/DemoVisits.tsx:10](../nagarseva/website/src/civic/DemoVisits.tsx#L10) | None for the tested scope. |
| C05 · Housing assessment creation and editing | PASS | Creation, editing and public read-only details work; no official eligibility or personal information is invented. | [nagarseva/website/src/civic/DemoHousing.tsx:9](../nagarseva/website/src/civic/DemoHousing.tsx#L9) | None for the tested scope. |
| C06 · Community feedback and moderation history | PASS | Feedback and responses persist. Administrative changes retain previous responses and status transitions in actual events. | [nagarseva/website/src/civic/DemoCommunity.tsx:6](../nagarseva/website/src/civic/DemoCommunity.tsx#L6) | None for the tested scope. |
| C07 · Reports and dashboard use the same filtered records | PASS | Settlement-scoped report summaries and infrastructure use the same records as the supporting table. Open/upcoming metrics and navigation apply matching filters. | [nagarseva/website/src/civic/DemoReports.tsx:12](../nagarseva/website/src/civic/DemoReports.tsx#L12) | None for the tested scope. |
| C08 · Scoped reset and replaceable persistence adapter | PASS | Confirmed reset restores deterministic demo records and preserves controlled source imports. Existing SQLite/RecordStore and CivicAdapter architecture remain intact. | [nagarseva/website/src/civic/adapter.ts:16](../nagarseva/website/src/civic/adapter.ts#L16) | None for the tested scope. |
| C09 · Old GIS integration stays disconnected | PASS | No old boundary/KML requests were observed in the browser regression. Original source files were not deleted or replaced. | [tests/check_synthetic_integration_browser.py:42](../tests/check_synthetic_integration_browser.py#L42) | None for the tested scope. |
| C10 · Production data connection | PARTIAL | No external government/authority service is configured or tested. All seven real-data categories are honestly Not provided. Controlled uploads are real isolated imports, not production activation. | [nagarseva/model/api/data_onboarding.py:273](../nagarseva/model/api/data_onboarding.py#L273) | Provide authorized sources, definitions/licences/dates, validated geographic crosswalks, credentials where needed, security/access controls, retention, monitoring and backups. |
| C11 · Current local administrator configuration | PARTIAL | The running server has adminConfigured:false. Protected routes correctly explain the limitation; authorized and rejected-key flows were exercised with temporary credentials. | [nagarseva/model/api/civic_demo.py:299](../nagarseva/model/api/civic_demo.py#L299) | Set a private NAGARSEVA_OFFICER_KEY before starting the API and enter it in Data management to use protected actions locally. No secret was invented or printed. |
| C12 · Optional photo storage | PARTIAL | Current photoStorage:false is truthful. Form/API validation exists; private attachment-storage tests use isolated configuration. | [nagarseva/model/api/civic_demo.py:299](../nagarseva/model/api/civic_demo.py#L299) | Enable the existing URBANSAARTHI_EVIDENCE_STORAGE=sqlite option if photo persistence is desired. Production storage/privacy policy remains a separate decision. |

## Current data and preservation

| Collection | Actual persisted count |
| --- | --- |
| settlements | 100 |
| wards | 24 |
| issues | 60 |
| projects | 20 |
| milestones | 40 |
| visits | 30 |
| assessments | 0 |
| feedback | 0 |
| dataSources | 4 |
| anomalyFixtures | 3 |
| activity | 2 |

The two activity records are actual workspace initialization and metadata-upgrade
operations, not fictional citizen actions. The three anomaly fixtures are separate
test scenarios. Existing civic values compare equal to the pre-audit snapshot after
excluding the newly added synthetic flags; no original collection was reset or replaced.
The server stores changes in SQLite, shared by clients of that server, rather than
pretending local browser state is a shared reporting system. What-if, budget and
preview weights are explicitly unsaved scenarios. Authorized weight saves, issues,
projects, visits, assessments, feedback and source imports genuinely persist.

No real dataset is configured: all seven readiness categories currently have
zero imports and `not_provided`. Import tests used labelled Demo data fixtures in
temporary databases. Original GIS/KML files remain untouched and disconnected.

## Executed commands and results

| Check | Command | Actual result |
| --- | --- | --- |
| Dependencies | UV_CACHE_DIR=.runtime/end-to-end-audit/cache/uv uv pip install --python nagarseva/.venv/bin/python -r nagarseva/model/requirements-urban.txt | PASS: declared packages resolved; defusedxml installed; existing openpyxl reused. |
| Frontend install | npm ci --cache ../../.runtime/end-to-end-audit/cache/npm (from website/) | PASS: 83 packages installed, npm reported 0 vulnerabilities. esbuild postinstall-policy warning remained; its installed platform binary built the app. |
| Python environment | uv pip check --python nagarseva/.venv/bin/python | PASS: 65 packages compatible. |
| Python regression | PYTHONPATH=nagarseva nagarseva/.venv/bin/python -m pytest tests nagarseva/tests/test_urban.py nagarseva/model/tests deploy/aws/tests submission/scripts/tests .github/tests -q | PASS: 398 tests, 4 nonblocking dependency/legacy warnings. |
| JavaScript tests | npm --prefix nagarseva/website test | PASS: 53 tests, 0 failures. |
| Repository lint | npm --prefix nagarseva/website run lint | PASS. The configured linter is TypeScript tsc --noEmit, not an ESLint/style audit. |
| Strict app types | npx --no-install tsc -p tsconfig.app.json --noEmit --noUnusedLocals --noUnusedParameters (website/) | PASS after removing one unused import. |
| Production build | npm --prefix nagarseva/website run build | PASS: tsc -b and Vite. Main bundle-size and existing static/dynamic PlanningPages import advisories remain. |
| Integration regression browser | PYTHONPATH=nagarseva nagarseva/.venv/bin/python tests/check_synthetic_integration_browser.py | PASS: 12 workflow groups, 0 page errors; disposable SQLite. |
| Management browser | PYTHONPATH=nagarseva nagarseva/.venv/bin/python tests/check_civic_management_browser.py | PASS: 13 workflow groups, 0 page errors; disposable SQLite. |
| Map browser | PYTHONPATH=nagarseva nagarseva/.venv/bin/python tests/check_civic_map_browser.py | PASS: 5 read-only workflow groups, live tiles and intentional fallback, 0 page errors. |
| Extended browser matrix | PYTHONPATH=nagarseva nagarseva/.venv/bin/python tests/check_full_audit_browser.py | PASS: 207 screenshots; no overflow, missing keys, page errors or axe violations. |
| New upload/simulation/export browser | PYTHONPATH=nagarseva nagarseva/.venv/bin/python tests/check_audit_workflows_browser.py | PASS: 8 workflow groups; 9 populated upload previews; actual multilingual PDFs and CSV. |
| Translation audit | node --experimental-strip-types tests/check_translation_audit.mjs (website/) | PASS: 3012 catalogue keys; no missing keys/parameters or unhandled JSX/literal calls. |
| Generator repeat | nagarseva/.venv/bin/python scripts/generate_demo_city.py --seed 96 --count 100 --output <two task-local paths> | PASS: byte-identical output; SHA-256 fa56d8231dfa448d79759299575155e901b10f1527305698e74784b23ffb4af5 |
| PDF visual checks | pdfinfo and pdftoppm for report-en.pdf, report-hi.pdf and report-mr.pdf | PASS: all 14 pages rendered; source/date, watermark, table repetition and Devanagari shaping inspected. |
| Diff whitespace | git diff --check | PASS. |
| Local startup | bash start-local.sh | PASS at http://localhost:5173 and http://localhost:8000/docs. Restarted only task-owned processes. |

Python warnings: one Starlette/AnyIO deprecation and three warnings from a retained
legacy pandas concatenation test. Build warnings: approximately 637 kB main entry
before gzip and an existing static/dynamic import overlap. These are nonblocking;
they were not suppressed or represented as errors fixed. No live government API,
cloud deployment or production capacity validation was performed.

## Language findings and human review

The three locale files have the same 255 keys. The merged catalogue
has 3012 keys. Missing keys: **none**. Mismatched parameters: **none**.
Unchanged technical labels are `CSV`, `SHA-256:` and `· CTS` in both Hindi and Marathi.
Unknown source/user text, IDs, machine CSV fields, canonical values, URLs and
technical formulas are deliberately preserved. Dates, numbers and currency use the
language locale; timestamps use Asia/Kolkata. CSV keeps machine-readable ISO dates
and numeric values, with a localized display-header row and a language identifier.

[Translation evidence](verification/translation_audit.json) lists every checked
exception. [Native review queue](translation_review.csv) contains all
104 new/overridden audit strings. These are AI-assisted translations, not
native-speaker approved copy. Review literal/technical wording first, including
`audit.generator` ("निश्चित-बीज जनरेटर"), `audit.anomalyMethod` ("रोपे गए फ़िक्स्चर"),
`audit.budgetNote`, `audit.generatedMethod`, `audit.slaNote`, `audit.manual`,
`audit.rollbackConfirm` and `audit.mixingRule`. A native reviewer should also review
the older catalogue's civic terminology. No linguistic certification is claimed.

The self-hosted font's licence, upstream URL and checksum are included in
`public/fonts/OFL.txt` and `public/fonts/provenance.json`. Upstream:
[Noto Devanagari](https://github.com/notofonts/devanagari).

## Screenshots and visual evidence

The local screenshot gallery is `.runtime/end-to-end-audit/gallery.html`.
It is generated evidence excluded from Git, so it is not a downloadable link in a
clean GitHub checkout. Run `tests/check_full_audit_browser.py` after the frontend
build to regenerate the page screenshots locally; the broader audit workflow
produces the additional upload/export evidence described below.
It contains 216 screenshots, including 207 page screenshots: 23 page/detail/dialog states at 375, 768
and 1280 pixels, in all three languages. Nine additional populated upload-preview
screenshots are in `../.runtime/end-to-end-audit/workflows/`.
All 216 states passed automated document-overflow and axe checks.
Nine contact sheets cover every page/width/language combination. Representative
full-size mobile, desktop and Devanagari screens and all 14 PDF pages were visually
inspected. Wide tables intentionally scroll inside labelled, focusable containers.
The persistent disclaimer and small data-source badges fulfil the latest request;
they intentionally supersede the earlier request to remove per-card demo labels.

## Important files added or extended in this audit

Added: `model/api/file_formats.py`; `src/civic/SourceNote.tsx`, `Methodology.tsx`,
`simulations.ts`, `printReport.ts`, `audit.css`; `src/i18n/auditMessages.ts`;
`public/fonts/` with licence/provenance; `scripts/generate_demo_city.py`;
`tests/test_audit_features.py`, `check_audit_workflows_browser.py`,
`check_full_audit_browser.py`; `website/tests/check_translation_audit.mjs`,
`simulations.test.mjs`; this report, its JSON evidence and translation review CSV.

Extended existing implementation: `model/api/data_onboarding.py`, `civic_demo.py`,
`model/requirements-urban.txt`; civic services/types/analytics/shared UI, shell,
dashboard, settlement/project/housing/report/management views; LanguageProvider and message
composition; retained PlanningPages source captions and one legacy unit label;
frontend dependency lock (axe-core), tests, README and integration documentation.
Paths beginning `model/` are relative to `nagarseva/`; `src/` and `public/` are
relative to `nagarseva/website/`. Earlier unrelated and uncommitted changes were
preserved. No commit, push or deployment was performed.

## Decisions and data still required

1. Supply authorized real sources, definitions, measurement/publication dates,
   licences and identifier/geographic mappings before enabling a verified adapter.
   Receiving or structurally validating a file is not independent verification.
2. Set a private server administrator key if protected local actions are needed;
   optionally enable existing SQLite photo storage. Current defaults honestly
   disable those functions. Production identity/roles, retention, backup and API
   synchronization need an explicit deployment design and permissions.
3. Obtain native Hindi/Marathi review and a manual assistive-technology review.
4. Legacy XLS, KML, shapefile and PDF ingestion, mixed-source rankings and
   activation of supplied imports remain unavailable. The current XLSX/CSV/GeoJSON
   controlled import and rollback work; they do not claim a government connection.

Machine-readable results: [end_to_end_audit.json](verification/end_to_end_audit.json).
