# UrbanSaarthi real-data implementation

Started 2026-10-18; completed local follow-up 2026-10-19. Extend the existing React/Leaflet and FastAPI/SQLite application.
Preserve the active interface, evidence workbench, AWS deployment and labelled demo.

Status: local implementation, acquisition attempts, data validation, API/database,
five connected screens, historical Census context, georeferenced source raster,
authorized field forms/imports, safe data staging, cleanup and verification
executed. The active UrbanSaarthi sandbox, backend and workbench are preserved;
unreachable frontend files were removed. External source/field/deployment limits
are itemized in [final_report.md](final_report.md).

1. Inspect repository, existing workflows and available tooling. Baseline: clean main;
   five-screen synthetic app, persistent operational records, no acquired boundaries.
2. Acquire public SRA metadata/features/projects, bounded OSM and official historical
   Census tables. Keep immutable originals, request manifests and per-source errors.
3. Validate IDs, schemas, geometry/CRS, source dates, record counts and geography.
   Record limitations before choosing joins or service indicators.
4. Extend SQLite with versioned data tables, explicit geography/provenance and
   independent operational records. Connect a separate real-data API and UI mode.
5. Reuse tested priority/scenario calculations; keep missing indicators null and
   real geometry separate from hypothetical assumptions and sandbox records.
6. Add field form/import validation, source inventory, quality/join reports, API and
   setup documentation. Preserve earlier research in a legacy inventory.
7. Run ingestion, backend, browser-engine, production build and browser workflow
   checks. Fix regressions and record actual evidence and remaining limitations.

No cloud resources, accounts, deployments, government submissions or messages are
created by this local implementation task. No data licence is inferred from access.
