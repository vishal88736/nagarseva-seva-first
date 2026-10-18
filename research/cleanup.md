# Dead-code cleanup

The active entry is `main.tsx` → `App.tsx` → acquired workspace / retained
UrbanSaarthi sandbox. Static imports, dynamic imports, styles, tests and documented
commands were checked before cleanup.

Removed 26 frontend files unreachable from either active application: the old
`LegacyApp.tsx`, `styles.css`, and the orphan `pages/`, `components/`, `i18n/` and
`lib/` trees. They had no active route before this task. Removed the now-unused
`recharts` package, its Vite chunk and 38 packages in its dependency tree.
TypeScript unused-import checking and Python unused-import/variable checking were
run on the resulting active code; leftover unused icons/imports were removed.
Evidence-file decoding and planning request schemas are shared by both modes.

Retained the fallback JSON directly referenced by legacy regression tooling,
legacy backend/model artifacts and their passing tests, the separate evidence
workbench and packaging scripts, presentation/submission materials, pilot protocols,
source-lineage manifests, required dependencies, source originals and databases.
The previous research inventory is retained as `dataset_inventory_legacy.csv`:
the historical evidence workbench still reads that schema, while the new app uses
the required acquisition inventory. Its packaging/validation scripts were adapted
to keep both workflows functional.

No Git commits, remote updates, public deployments, credentials or user operational
records were removed. New large raw/processed assets and transient reports/caches
are excluded from Git as appropriate; source scripts and compact evidence reports
remain reviewable. No tests were removed to obtain a passing result.

The UI spacing follow-up removes a forced map minimum height, avoids stretching
overview cards to their neighbour's height, removes duplicated panel spacing and
keeps long inventory/project/priority tables in scrollable panels with visible
headers. Every record remains available; the selected priority explanation stays
near the controls instead of following 156 full-height rows.
