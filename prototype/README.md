# Seva Evidence — working research prototype

Open **[dist/standalone.html](dist/standalone.html)** in a modern browser. It contains the interface, analytical code, reference/example inputs and downloadable research text in one file. No server, account, API key, package installation or internet connection is required for the embedded analysis. Original-source links require internet access.

For a modular local preview, from the project root:

```bash
python3 prototype/serve.py
```

Open the printed `http://127.0.0.1:8765` URL. This workspace blocks socket creation, so the file-based entry point is the supported handoff here. No server was left running.

## What works

| Screen | Implemented behaviour | Evidence boundary |
|---|---|---|
| Overview | Research counts, historical M/E WASH context and locality reference display | Census figures remain 2011 ward-wide context; not current/slum-only observations |
| Service access | Imported-graph shortest paths, explicit node-snapping limit, mapped pedestrian restrictions, step avoidance, disconnection handling and per-marker provenance | Built-in real references have no road graph. Routing is demonstrated on a labelled invented grid until a lawful network is imported |
| Inspection priorities | Source-supplied 0–1 deficits, visible weighted contributions, missing-value intervals, possible position bounds and weight stress tests | No current local deficit survey or independently validated priorities; no eligibility or relocation decisions |
| Evidence claims | Conflicting same-asset/service/date reports remain visible with their supplied evidence types | The software does not decide which report is true or certify engineering/service quality |
| Evidence search | BM25-style retrieval over 14 curated, cited source cards; abstention on unsupported current measurements, personal decisions and claimed prototype impact | No LLM, full-document RAG, trained classifier or general retrieval-accuracy claim |
| Scenario lab | Exact hypothetical maintenance-budget comparison, deduplicated coverage, infeasible-option exclusion and a greedy comparator | Built-in costs/coverage are invented; abstract units are not households, and no O&M/finance/relocation appraisal is established |
| Research library | Publication appraisals, searchable dataset inventory, original eleven deliverables and follow-up reports | Metadata/indexed access is distinguished from acquired data |
| Real public-record case | Three attributed SRA listing rows, exact CTS-context collisions, tentative formatting associations, unknown status/update fields and a JSON case export | Separate desk case, not a geospatial import. No automatic merge, delay finding, current service claim or validated cadastral equivalence |
| Import/export | Schema-checked public/aggregate JSON, input hash, provenance dialog, Markdown/JSON review brief and context-bearing ranking CSV | Files stay in tab memory. Source/licence declarations are not independently verified; no official complaint is submitted |

## Real records and synthetic tests

**Research references**, the default, contains three coordinates transcribed from OSM-derived Mapcarta pages near Govandi/Baiganwadi. Each marker retains its secondary source, reported OSM feature ID and unknown observation date. Entrances, current operation and completeness were not checked. The depot coordinate is representative of a way. OSM attribution is retained; no tiles or photographs are copied.

**Synthetic sandbox** uses invented geometry near 0° latitude/longitude, invented service deficits/claims and hypothetical costs. It includes an inaccessible/private feature, a disconnected facility, missing values/dates, conflicting claims, ranking instability and overlapping coverage. These are engineering fixtures, not Mumbai findings or projected benefits.

**Imported dataset** is user-supplied and independently unverified. Its declared synthetic status and source/licence remain visible. A non-OSM import does not automatically receive an OSM attribution label. The [input schema](dist/schema.md) documents limits and assumptions.

## Five-minute demonstration

1. Open the standalone file. Explain the real-reference and historical-data boundaries on **Overview**.
2. Open **Real public-record demonstration**. Inspect the three SRA entries, raw CTS values, source/date and unknown status fields. All records remain separate; export the case with its computed audit.
3. Open **Service access**. The real reference view has no acquired road network and withholds route distances.
4. Select **Synthetic sandbox**, then **Calculate access**. Inspect the computed candidate, disconnected facility and access restriction. Change the snap limit: stale results clear until recalculated.
5. Open **Inspection priorities**. Change the weights, inspect the interval for missing sanitation evidence, and find the fully unobserved area that receives no deprivation position. Read the conflicting claims.
6. Search **“SBM functional asset monitoring”**. Existing policy capability appears with the source. Search **“What is current M/E toilet reliability?”**: the workbench abstains and labels related notes as background.
7. In **Scenario lab**, change the budget and compare exact/greedy selections. Emphasise that costs/units are invented and overlap is deduplicated.
8. Export the brief/analysis and inspect the input hash, assumptions, source trail and limitations.


## Rebuild and verify

The browser application has **zero third-party runtime dependencies**. Maintenance scripts require Python 3; engineering tests require a Node version supporting `--test-isolation=none` (tested with the recorded runtime in [validation](../research/prototype_validation.md)).

From the project root:

```bash
python3 prototype/scripts/verify.py
```

This checks source syntax, engine tests, converter tests, a 25-prompt development retrieval checklist, template contracts, HTML structure and research-file consistency, then rebuilds the standalone file and validation report. The template harness is not a browser.

Optional real-browser QA needs Playwright and an available browser:

```bash
node prototype/scripts/browser_check.mjs
```

The runner detects installed Playwright or the existing bundled runtime and common Linux/macOS Chromium paths. `NODE_PATH` and `BROWSER_PATH` can override discovery. It installs nothing. In this workspace, browser launch fails with socket-permission errors; no screenshot, layout, real-DOM interaction or accessibility pass is claimed. The report distinguishes dependency/launch blocks from application-startup/check failures and records the tested entry-file hash. See the [executed validation report](../research/prototype_validation.md) for actual results and the boundary.

If public Overpass JSON is acquired independently, convert it without treating a database timestamp as a survey date:

```bash
python3 prototype/scripts/prepare_osm.py acquired-overpass.json prototype-input.json --source-url https://overpass-api.de/api/interpreter --retrieved-at 2026-10-17
```

The converter does not download data and refuses to overwrite an existing output. It retains source node IDs and labels representative centres. Inspect geometry, walkable connections, legal reuse and facility entrances before importing. Never infer rights, poverty or service functionality from mapped morphology.

## Operating and adoption boundary

The [submission pack](../submission/README.md) adds a six-slide editable deck, application drafts, scripts, a transparent cost workbook, validation materials and phase checklists. Personal details are omitted. Official-template visual compliance and actual portal word limits remain unverified.

This is a local, single-user research aid. It has no shared case database, production identity/access controls, complete personal-data detection, authoritative asset registry, approved integration, enforcement power or engineering certification. Recognised sensitive field names are rejected, but users must remove personal information themselves. Exports inherit input restrictions.

The recommended prospective sponsor remains BMC M/E ward administration with the relevant service department and actual operator. No agency, NGO, resident or contractor has been contacted or endorsed the prototype. The required next validation is one real workflow review with lawful current records and an independent comparator. Existing SRA, PMAY, AMRUT, SBM and grievance capabilities are prior art, not features this prototype invents.

## Files

- `dist/index.html`, `app.mjs`, `lib/engine.mjs`, `style.css`: modular application sources.
- `dist/standalone.html`: generated, self-contained entry point.
- `dist/data/`: public reference inputs, synthetic fixture and generated research index.
- `scripts/sync_research.py`: derives the source-card/library index and copies public research files.
- `scripts/build_standalone.py`: embeds assets and research text; no external runtime assets.
- `scripts/prepare_osm.py`: optional converter for an independently acquired response.
- `tests/`: meaningful numerical, missingness, permission, source and export regression cases.
- `test-artifacts/`: generated local reports; excluded from source sharing by `.gitignore`.
