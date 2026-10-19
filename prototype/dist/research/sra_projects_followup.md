# SRA public scheme pagination follow-up — 19 October 2026

The [official public scheme listing](https://dms.sra.gov.in/SRAPUBLIC/) was acquired through its publicly advertised ASP.NET page actions. **All 228 advertised pages were reached**, yielding **5,677 published rows**. The last page contained two rows and showed no subsequent page action. `complete: true` means final-page navigation was confirmed for this acquired listing; it does not establish a complete government scheme registry, current project status or completeness outside the public portal.

The earlier 200-page / 5,000-row snapshot stopped at a configured safety limit. The continuation reused its checksum-verified cache and requested only the remaining sequential pages. A subsequent full replay from cache reproduced the final result. No second concurrent crawler or authentication bypass was used. The public requests had explicit downloader timeouts and a 25 MB per-response ceiling; new page requests were sequential with a 0.5-second delay. Total original listing HTML: **15,409,430 bytes** across 228 pages. Originals remain separate from processed JSON.

## Actual fields and source limitations

The source presents `Action`, `SrNo`, `Scheme Name`, `Ward Name`, `Address`, `CTS No`, `Village`, `Developer Name`, `Architect Name`, `Land Type`, `DCR No` and `Proposal No`. Action/pager controls are excluded from scheme facts. Source spelling and ward/village/CTS strings remain unchanged.

All **5,677 rows have unique local IDs**. The displayed source serials run from 1 to 5,678 with one published gap: **99 → 101**. No row with displayed serial 100 was present in the acquired pages. It was not fabricated, and the gap alone is not treated as proof of a missed page.

There are **10 identical-content groups involving 25 rows**; the number of distinct displayed-content hashes is 5,662. Every published duplicate row is preserved. All members of a duplicate group have `source_content_unique: false`. A duplicate's displayed source serial may disambiguate its local content-hash ID; neither that suffix nor the serial is represented as an official stable scheme ID. Identical content is insufficient evidence to merge these into distinct or identical underlying projects.

Duplicate groups by displayed source serial:

- 1612, 1613
- 2370, 2371, 2372, 2373, 2374
- 2483, 2484
- 2500, 2501, 2502
- 2899, 2900
- 3167, 3168, 3169
- 3750, 3751
- 3849, 3850
- 4819, 4828
- 5132, 5133

For every row, `source_id`, `source_date`, `geometry` and `settlement_id` remain null; `project_status` remains `unknown`. A proposal number, name or shared CTS string does not by itself establish a reliable settlement join or current completion/operation. The dashboard's project count therefore represents **published scheme rows**, not verified unique ongoing projects.

Original listing retrievals span **18 October 2026 15:21:36 UTC through 19 October 2026 05:50:06 UTC**. Some originals were reused across the continuation. This is not an atomic server snapshot, and the live portal could change between page retrievals. Individual observation/publication dates were not supplied by the listing. Retrieval must not be presented as the date a scheme was observed or updated.

## Reproducibility and safeguards

```bash
nagarseva/.venv/bin/python scripts/ingest_sra_projects.py --max-pages 400
```

The default is now also 400 pages so an ordinary rerun can replay this complete cached listing rather than stopping at the former 200-page default. The hard limits are **400 pages and 20,000 rows**; no unlimited crawler was added. A page that would exceed the row ceiling is not partially imported. The pipeline follows only the next sequential action advertised by the same-origin `/SRAPUBLIC/` form, preserves hidden ASP.NET state and refuses malformed actions, changed columns, inconsistent active-page markers, repeated response hashes, reversed/repeated source serials or duplicate local row identities. Source content duplication at different serials is preserved and flagged rather than mistaken for a pagination loop.

A page/network/schema/limit failure results in explicit partial status and a recorded error, never a claim of final-page completion. Requests are content-addressed and checksum-verified, so successful cached responses are reused and original bytes are not silently replaced. `--refresh` is optional and downloads new source snapshots.

Outputs:

- `data/processed/sra_projects.json`: all 5,677 rows and complete pagination/source metadata.
- `data/metadata/sra_projects_ingestion.json`: actual page requests, raw paths, checksums, source fields, retrieval window, completion status, serial gaps and duplicate groups.
- `data/raw/sra/public-projects-*.html` and `public-projects-page-<n>-*.html`: immutable source originals.
- `research/dataset_inventory.csv`: locked inventory update for `SRA public scheme listing paginated` with the actual downloaded/parsed count.

Source reuse terms are not established beyond public access; the portal reserves rights. Originals remain local research material, outside Git. Public access does not establish a new redistribution licence.

## Verification

Executed the actual acquisition and a complete cached replay: **228 pages, 5,677 rows, zero ingestion errors**, 5,677 unique local IDs, 10 duplicate-content groups / 25 rows, one preserved serial gap and no inferred statuses/geometries/settlement joins.

Executed:

```bash
PYTHONPATH=scripts:nagarseva nagarseva/.venv/bin/python -m pytest tests/test_sra_project_pagination.py tests/test_sra_sources.py tests/test_data_pipeline.py -q
```

Result: **55 passed**. Tests include legitimate duplicated content within/across pages, repeated responses, malformed/missing pager state, empty/login/changed-schema responses, source serial order, page and row limits, explicit partial status and prohibited external form actions. Ruff F401/F841 and `git diff --check` passed for the changed files. These fixture tests are separate from the actual source acquisition described above.

The OGD catalogue still exposes no acquired structured project CSV. No claim of an ongoing/completed dataset or a reliable project-to-settlement join is made.
