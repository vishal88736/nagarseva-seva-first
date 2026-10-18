# Seva First research

## Current acquisition and application: 18 October 2026

Read [data_availability.md](data_availability.md), [data_quality_report.md](data_quality_report.md),
[join_strategy.md](join_strategy.md), [the current acquisition inventory](dataset_inventory.csv),
[machine-readable results](acquisition_results.json) and [the final implementation report](final_report.md).
The previous 32-candidate inventory is preserved as [dataset_inventory_legacy.csv](dataset_inventory_legacy.csv)
for the historical evidence workbench. It is distinct from the actual downloads.

## Earlier policy and feasibility research

Follow-up: [real primary-source SRA record case](public_record_case.md) and [submission, pitch and pilot pack](../submission/README.md). The case is a desk record-quality demonstration; current service measurements and adoption remain unvalidated.

Research and access date: **17 October 2026**. Scope: Urban Development; affordable housing, slum redevelopment and basic-service assurance in Maharashtra.

The original **11 requested deliverables** are complete, with source-access and prototype-validation follow-ups. Coverage: **14 journal publications, one additional government impact report, 32 dataset/input candidates and 13 problem-evidence records**. Full-text access varies: some reviews rely on author manuscripts, indexed sections or abstracts, as marked individually. Failed retrievals are recorded rather than treated as successful access.

Start with [research_summary.md](research_summary.md), then [research_gap.md](research_gap.md) and [technical_feasibility.md](technical_feasibility.md). The authorised follow-up added a [working local prototype](../prototype/README.md) and [self-contained browser entry point](../prototype/dist/standalone.html). It is not an endorsed government pilot or a field-validated service model.

## Navigation

| File | Contents |
|---|---|
| [official_sources.md](official_sources.md) | Verified starting URLs, policy provisions, dated access results, additional primary sources and failed retrievals |
| [literature_review.md](literature_review.md) | Fourteen academic papers, one additional government impact study, bibliographic verification, methods, limitations and access depth |
| [existing_solutions.md](existing_solutions.md) | Existing government and nonprofit capabilities; observations distinguished from documented specifications |
| [research_gap.md](research_gap.md) | Evidence, counterevidence and validation gates for five proposed gaps; city comparison |
| [dataset_inventory_legacy.csv](dataset_inventory_legacy.csv) | Historical candidate inventory: source, year, resolution, fields, licence, access and readiness |
| [problem_evidence_matrix.csv](problem_evidence_matrix.csv) | Housing and service problems, interventions, remaining questions and confidence |
| [technical_feasibility.md](technical_feasibility.md) | Six technical directions, data dependencies, architecture choices and feasible submission scope |
| [evaluation_plan.md](evaluation_plan.md) | Baselines, metric definitions, missing-data treatment and validation boundaries |
| [references.bib](references.bib) | Verified academic publications and the institutional impact report |
| [research_summary.md](research_summary.md) | Decision brief, recommended location, build/cut decisions and unresolved questions |
| [access_followup.md](access_followup.md) | Resolved Census HL-04 metadata, official SBM functional-monitoring prior art, three secondary reference points and repeated acquisition failures |
| [prototype_validation.md](prototype_validation.md) | Executed software/retrieval checks and the remaining browser/field validation boundaries |

## Evidence rules

- **Verified fact:** supported by an identified primary document, publication or directly observed public page. A portal's advertised capability is a documented specification, not a successful transaction test.
- **Inference:** an interpretation of evidence, explicitly identified as such. It is not a measured local effect.
- **Hypothesis:** an unmet-need or operational claim requiring resident, operator or official validation.
- **[VERIFY]:** a specific unresolved point, including a dataset's currency, reuse permission or access to records.
- **High / Moderate / Low confidence:** qualitative assessments of the particular proposition and evidence. These are not statistical confidence intervals or competition scores.

Access labels used in the inventory:

| Label | Meaning |
|---|---|
| PAGE_READ | A public page or catalogue was read through the web research tool |
| DOCUMENT_READ | A document's text was retrieved and relevant sections examined |
| INDEX_ONLY | Search-indexed material was visible; direct retrieval failed |
| SHELL_ONLY | A page loaded, but records/map interaction required JavaScript or unavailable browser interaction |
| LOGIN_VISIBLE | Authentication controls were observed; protected functions were not tested |
| FETCH_FAILED | This research tool could not retrieve the URL; it does not prove the portal is down for everyone |
| NOT_TESTED | A source or method is documented, but the specified record/download was not exercised |

**No raw road network or complete census spreadsheet was downloaded.** The follow-up transcribed three secondary OSM-derived transport reference points into a local JSON/GeoJSON input with per-feature provenance; observation dates and entrances remain unknown. Reference points do not establish routes or service coverage. Public metadata, SRA rows and policy text were inspected through web tools. Shell network/DNS and local-server restrictions are recorded in the validation follow-up. No credentials, CAPTCHA bypasses, resident records or protected APIs were used.

In the CSV inventory, readiness labels distinguish visible rows, verified download routes without ingestion, metadata-only sources, failed/unverified leads, partner-required records and prospective data that do not yet exist. D26–D29 describe requested/future inputs; they are **not available datasets**. All cells are research metadata; CSV dates use ISO text and unknown values are explicit. The second CSV records verified/historical evidence separately from local hypotheses and unsupported claims.

The initial repository inspection found no existing project content outside protected environment directories. The authorised follow-up added `prototype/` and root run instructions while retaining the research package.

## Time and geography

The research uses a solo participant's approximately one-week build constraint from the conversation. Mumbai, Pune, Nagpur and Nashik are compared. Mumbai M/E is recommended for a **desk-based demonstration**, conditional on obtaining a lawful, usable spatial extract. An operational pilot has not been selected or agreed with any authority.

Historical Census 2011 counts and amenity measures retain their observation year. A report uploaded in 2025 or 2026 does not turn an underlying 2011 observation into a current measurement. Ward, city, state, settlement and household denominators must remain separate.

## How to extend the research

For every new source retain publisher, exact URL, publication/version date, observation period, retrieval date, access outcome and licence. For a downloaded file also retain file hash, CRS, schema and row count. Resolve the data-acquisition gates before representing a dataset as an application dependency. Append local validation findings with their actual sample and limitations; do not rewrite desk evidence as fieldwork.
