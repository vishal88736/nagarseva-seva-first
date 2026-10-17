# NagarSeva delivery status

Updated 2026-10-11.

The local competition demonstration is implemented. It connects project selection, planning, household affordability, constrained allocation, source-labelled service records, resident reporting, officer action, repair evidence, confirmation/dispute, and pilot evidence collection.

## Completed locally

- Persistent records, receipt privacy, access checks, consent, audit history, and valid state transitions.
- Working briefs, private receipts, financial scenarios, complaint/allocation CSVs, and pilot evidence exports.
- Approved location imports, unknown/unassessed records, project commitments, dated observations and field review.
- Usability timing/completion and independent classification samples, with demo entries excluded from real-pilot metrics.
- English, Hindi and Marathi layouts; desktop/tablet/mobile forms; dark mode; offline writes/drafts; blocked-storage receipt delivery.
- Live artifact benchmark metadata, all-location maps and imported-city filters.
- OpenStreetMap geography with attribution and schematic fallback; a live seven-day area forecast with persistent caching and explicit provider outage states.
- Eight-source public catalog, source-preserving forecast exports, published service benchmark references and applicable official service portal links.
- Competition deck, demonstration script, implementation guide and pilot protocol.

## Verification

- 25 backend regression tests passed.
- Production TypeScript/Vite build passed.
- Isolated browser workflow passed, including every complaint stage, pilot forms/imports, exports, scenario persistence, languages, mobile layouts, blocked storage, offline drafts, source links and cached/stale/unavailable forecast states.
- Live Open-Meteo retrieval returned seven days; a single map tile responded with a valid PNG. Automated layout/workflow tests block public map-tile requests.
- All 330 production-build layout cases passed with no detected text collisions or horizontal overflow: five viewport widths, three languages, all pages, expanded forms, dark mode and forecast failure states. The saved report is [verification/layout_report.json](verification/layout_report.json).

## Work that needs real inputs or external access

| Work | What the team must provide | Existing support |
| --- | --- | --- |
| Field pilot and user evaluation | Consented participants, measurements, source records and feedback | Pilot workspace and PILOT_PROTOCOL.md |
| Independent model and cost validation | Independently reviewed risk/tenure assessments, labels and actual quotes | Source-labelled imports, evaluation exports and artifact benchmarks |
| Public or operational deployment | Hosting/domain access, deployment configuration, responsible administrator and access/retention requirements | Built frontend, API, configurable origins/URLs, officer key for a controlled pilot |

There is no claimed real field pilot or realized saving. Synthetic model benchmarks do not validate real settlement decisions. The saved cost model's held-out R² is below a mean baseline, and it needs verified quotes and independent validation before operational project decisions.

A public operational service additionally needs deployment-specific individual identities, permissions, retention governance and rate limiting. The current access model is designed for a local demo or a controlled pilot; public deployment has not been performed.

For the competition, demonstrate one complete synthetic workflow and replace exploratory assumptions with evidence collected by the project team. The eight-slide pitch and three-minute script state these limits.

Public web sources cannot provide consented local inspections, independent settlement assessments or actual project quotations. Census 2011 is linked as historical town-level context; its publisher's reproduction permission has not been obtained. See [PUBLIC_INTEGRATIONS.md](PUBLIC_INTEGRATIONS.md) for each implemented connection and its terms.
