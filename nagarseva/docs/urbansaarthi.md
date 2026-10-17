# UrbanSaarthi: focused implementation and validation boundary

Prepared 18 October 2026. This is the focused successor to the merged NagarSeva application and Seva Evidence research workbench. The original application components remain in the repository; `website/src/LegacyApp.tsx` preserves the previous shell. The default app now exposes five screens.

| Screen | Implemented workflow | Data boundary |
| --- | --- | --- |
| Overview | Rankability, demonstration deficit counts, pending reviews and a connected workflow | Counts describe the supplied synthetic fixture and entered demo works |
| Explore Settlements | Leaflet polygons, configurable layers, deficit/missing-data filters, accessible cluster selector, source cards, graph access distances | Five authored polygons; no verified settlement geometry or current field labels |
| Prioritize Needs | Configurable normalized weights, contributions, missing-data intervals, shared-rank ties, equal-weight baseline and tie-aware Spearman correlation | MCDA preferences are design assumptions; equal weights are a sensitivity baseline, not an independent ground truth |
| Compare Scenarios | In-place improvement and redevelopment, conditional relocation thought experiment, editable cost/support/O&M assumptions, network accessibility and a livelihood proxy | No quotations, engineering validation, household eligibility count, verified relocation destination or consent process |
| Service Assurance | Persistent works, physical completion, evidence uploads/downloads and SHA-256, measured service review, issues, response records and an audit trail | Self-entered demonstration identities and measurements do not establish real independent inspections |

## Scoring and missing data

The default design weights are water .30, sanitation/drainage .25, housing .20, amenity access .15 and risk .10. Each indicator is a normalized 0–100 deficit index. The example [80, 70, 60, 50, 40] sums to **65.0**, correcting the supplied proposal's 65.5.

Weights are nonnegative, finite and normalized to sum to one. If a positive-weight input is missing, the engine reports a lower/upper contribution interval and does not assign an exact score or rank. The lower bound represents the most favorable possible missing contribution, not an imputed zero. An unavailable zero-weight input remains visibly missing but does not prevent calculation of that particular weighted score.

Python and browser calculations use the same explicit fixtures and hand-worked validation cases. In API mode the browser checks its ranking and scenario results against the Python endpoints. A mismatch is surfaced; drafting a scenario work requires the scenario check to pass. This is consistency verification, not model accuracy or field validation.

## Scenarios and access

Capital/support cost is `(households × unit cost + shared works + ceil(households × disruption share) × temporary months × rent/month) × (1 + contingency/100)`. Annual maintenance is separate. The user must supply an explicit household assumption when none is available. No legal eligibility is inferred.

The walking graph is authored synthetic data. Dijkstra uses geodesic edge lengths and excludes non-walkable edges. Disconnected amenities remain unavailable. The livelihood column is distance to a synthetic employment hub, not measured income or actual livelihood loss. In-place alternatives keep the same graph origin; a relocation thought experiment uses a separate synthetic node only after an explicit opt-in and reason. No option is automatically selected as socially or legally preferable.

## Service verification state machine

Physical works move from planned to in progress to completed. A separate verification state starts unverified. Review requires completion, an evidence file belonging to that work, a reviewer different from the completion/evidence actors, a fresh timezone-aware inspection, a measurement meeting the explicit service target, confirmation of functioning and no open complaint. A five-minute clock tolerance and seven-day freshness rule are prototype design assumptions.

An interruption report disputes existing verification. Recording a response never automatically restores it. A subsequent review must use evidence uploaded after the latest complaint. Updates, file associations and complaint invalidations are transactionally stored in SQLite. Uploads accept at most 2 MiB of PNG, JPEG, PDF or UTF-8 text; signatures are checked for the binary types. Downloads are attachments, with `nosniff`. Evidence metadata is exported without file content or officer keys.

These safeguards constrain record transitions; they cannot prove that a person is independent or an inspection is truthful. Names are self-entered. A configured officer key protects server records, writes and downloads; it does not implement production RBAC, resident identity/receipt workflows, multi-agency governance or tamper-proof audit storage. The broader legacy resident-confirmation workflow remains in the original code but is not misrepresented as integrated into this focused interface.

## API, local mode and storage

The recommended FastAPI entrypoint is `model.api.urban:app`, which needs no saved ML models. It is also mounted under `/urban` in the legacy API. `/urban/settlements`, `/urban/priority` and `/urban/scenarios/{id}` serve the demonstration planning data and calculations. Operational state, uploads, actions and complaints use the configured SQLite store.

When the API cannot be reached, the frontend explicitly uses a separate browser sandbox. Edits must save successfully to browser storage, or the action reports failure. Browser records are not silently uploaded when the server becomes available. Exports are the handoff boundary. Do not treat this mode as a shared municipal record or as an offline copy of the server database.

SQLite is intentional for a one-participant prototype. PostgreSQL/PostGIS, authenticated roles, file scanning, object storage, backups, approved aggregates, permitted geospatial imports and agency ownership are production work. GeoPandas and Shapely are not unnecessary dependencies of the current simple fixture calculations. No LLM is used for scores, service facts or relocation decisions, and the app is not advertised as having a validated AI advantage.

## Sources and mapping terms

The three real SRA listing rows are copied with their original source/access metadata from `prototype/dist/data/public-schemes.json`, acquired 17 October 2026. They have no acquired geometry, service observations, durable official scheme ID or current project status. They are never joined to the synthetic clusters. Absence in the acquired listing does not establish absence in other SRA systems. No open-data licence was established; wider reuse needs publisher review.

The optional online basemap uses visible attribution and the correct tile endpoint, without tile prefetching, proxying or offline tile downloads. Browser tests keep the basemap disabled and do not download OSM tiles. Review the [OSMF tile policy](https://operations.osmfoundation.org/policies/tiles/) and [OSM copyright/ODbL notice](https://www.openstreetmap.org/copyright), accessed 18 October 2026. `VITE_TILE_URL` and `VITE_TILE_ATTRIBUTION` support a provider with appropriate terms for a real deployment.

## Evaluation and demo

Run `make test` for the focused Python API/calculation checks, browser-engine tests and frontend build. The full CI also exercises the preserved model tests. Install the pinned browser requirements and Chromium to run `python tests/check_urban_browser.py` from `nagarseva`; the script starts owned servers, uses a disposable database, records actual results and closes its processes. The [Playwright 1.63.0 publication](https://pypi.org/project/playwright/1.63.0/), accessed 18 October 2026, verifies the test-runtime pin.

The end-to-end check covers map selection, missing inputs, the 65.0 example, ranking sensitivity, opt-in relocation, scenario drafting, completion without verification, file attachment, a failed measurement, successful review, a complaint disputing review, a response not restoring it, fresh evidence, report export, database persistence, three viewport widths across all five screens, and explicitly separate browser storage. See `integration/urban-validation.json` at the repository root for executed outcomes. A passing automated browser run does not substitute for user testing, accessibility review or independent field validation.

For judges: select a demo cluster; inspect provenance; explain its contributions; compare the two in-place scenarios; draft one service work; start and complete it; attach a harmless text inspection record; show a failing then passing measurement; report an interruption and show verification being disputed; export the reviewable brief. State explicitly that the physical geography, service values, costs and operations are demonstration data.
