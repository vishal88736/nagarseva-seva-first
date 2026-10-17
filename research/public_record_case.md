# Real public-record desk demonstration: SRA listing quality

Access date: **2026-10-17**. This is a small, deliberately selected public-record case, not a representative sample, field survey or redevelopment-performance assessment.

## Decision and limits

**This is a valid real-data desk demonstration of evidence handling and record-linkage caution.** Three exact primary-source listing records can be checked, preserved with provenance and audited reproducibly. They cannot establish current water or sanitation conditions, construction progress, delay, resident displacement, legal eligibility, scheme boundaries or the operational usefulness of a new government system. A real service-access demonstration still requires an acquired road network, independently checked amenities and dated service observations.

The demonstrated question is narrow: **can an inspection workbench retain distinct listed schemes, expose missing context, and prevent an unsupported join based only on a CTS string?** A spreadsheet can already perform this audit. The software's incremental value remains a hypothesis requiring comparison with the adopting officer's existing workflow.

## Primary source and extraction boundary

The official [SRA public scheme listing](https://dms.sra.gov.in/SRAPUBLIC/) was read afresh on 2026-10-17. Its first rendered view contained 25 rows and controls for scheme, address, CTS, village, developer and architect. An indexed [alternate page path](https://dms.sra.gov.in/SRAPUBLIC/MainNewExplorer.aspx) also exposes the listing. The three rows below were transcribed from the fresh root-page response; they were not obtained through a bulk export or authenticated API. Source publication and individual record-update dates were not displayed in the inspected table. Retrieval date is not a record observation or update date.

Only institutional scheme labels and non-expressive field facts are reproduced. Addresses, developer names, architect names and the rest of the listing are deliberately omitted. Source spellings and CTS punctuation remain unchanged. The page's footer says “All Rights Reserved”; no open-data licence was found in the inspected response. This limited attributed demonstration is not a conclusion that unrestricted republication, bulk harvesting or commercial redistribution is licensed. Confirm reuse conditions with the publisher before broader distribution. No photographs, logos, tiles or descriptive paragraphs were copied.

## The three records

Each source serial number identifies its position in the inspected listing, **not a verified durable project identifier**. Each dash below is the literal proposal-field placeholder; the derived proposal identifier is unknown, not a validated blank database field. All facts in this table come from the [official listing](https://dms.sra.gov.in/SRAPUBLIC/), accessed 2026-10-17.

| Source serial | Scheme label | Ward | Village | Raw CTS | Raw proposal value |
|---:|---|---|---|---|---|
| 3 | Bharti CHS | M-E | Deonar | `1-A` | `-` |
| 4 | Universal CHS | M-E | Deonar | `1-A` | `-` |
| 9 | Navi Disha & Gurukrupa C.H.S | M-E | Deonar | `1 A` | `-` |

The [machine-readable case](../prototype/dist/data/public-schemes.json) preserves raw values, unknowns, source URLs, the snapshot date and derived diagnostics. Its local row keys are generated for this demonstration and explicitly are not SRA-issued identifiers. It is a separate record-case format, not a geospatial service dataset or an importable household registry.

## Reproducible audit

| Check on this selected sample only | Result | Meaning | Required response |
|---|---:|---|---|
| Rows with a supplied scheme label, ward, village and CTS | 3/3 | These basic listing fields can be retained. | Keep the original strings and retrieval context. |
| Distinct raw CTS strings | 2 across 3 rows | Two records use exactly the same CTS string. | Do not use raw CTS as a unique scheme key. |
| Rows in the exact `(ward, village, CTS)` collision | 2 | The first two named entries share that tuple. | Flag for review; do not merge, delete or call the entries erroneous duplicates. |
| Rows in a *candidate* normalized-CTS group | 3 | Removing spaces/hyphens for this illustration yields `1A` for all three. | Treat as a possible association for authoritative checking, not cadastral equivalence. |
| Non-placeholder proposal values displayed | 0/3 | This view supplies no usable proposal identifier for these rows. | Request an authoritative scheme/project crosswalk if linkage is required. |
| Rows with an explicit current status in the inspected table | 0/3 | The inspected table has no status column. | Record `unknown`; check permitted detail records and official status definitions. |
| Rows with a record-update date in the inspected table | 0/3 | No record-update column appears in this table. | Do not substitute retrieval date or label a row stale. |

The calculations above are deterministic checks of the three transcribed rows. They are **not** percentages of the SRA database, estimates of Mumbai's project quality or findings that SRA lacks such fields elsewhere. Current status and update-date information may exist in action/detail records, other SRA systems or official files that were not inspected for this case. The public table's `Action` controls were visible in the text response, but their detail workflows, exports and underlying identifiers were **not tested**. No login, CAPTCHA or access restriction was bypassed.

For the normalization demonstration only, apply uppercase and remove ASCII spaces and hyphens from these three CTS strings. Such a transformation is not a validated general cadastral-normalization rule; punctuation, suffixes, part references and village context can be legally meaningful. Even a village/ward match and normalized CTS match do not identify a single scheme or prove spatial overlap.

## Demonstration script

1. Display the three records with the primary source link and the 2026-10-17 retrieval date. Show **real public listing; current project status unknown**.
2. Show that exact matching retains three separate rows and flags the two rows sharing `1-A`; it performs no automatic deduplication.
3. Show the possible `1 A`/`1-A` formatting association as a separate, explicitly tentative review flag. Retain the raw values beside it.
4. Show the proposal placeholders and absent listing-level status/update fields as unknowns. Ask for authoritative project IDs, permitted detail records and a defined status/date source before any progress analysis.
5. Export the original rows, diagnostics and evidence boundary. Do not display a delay rank, deprivation score, map location, service failure or resident inference for these records.

This gives judges a real, source-checkable demonstration without dressing synthetic geometry or service observations as measured conditions. It demonstrates handling of ambiguity; it does not prove an unmet need or field benefit.

## Validation and follow-up

**Calculable now:** transcription/schema checks, row count, exact CTS collision count, candidate normalization group, placeholder count, explicit unknowns and preservation of source/date fields. The expected outputs are shown above and recorded in JSON.

**Requires independent checking:** another reader's transcription against the live source, stable official record identifiers, the meaning of each scheme/CTS relationship, current progress, access to detail records and data-reuse permission. Obtain a permitted crosswalk rather than infer correspondence from a locality name or shared CTS.

**Requires a real workflow owner:** whether this review is already handled adequately, whether a source-linked workbench reduces review time or errors, which officer can correct source records, and whether any local operational service issue exists. Compare with the current spreadsheet/portal process on additional independently chosen records; this authored three-row example is not a held-out evaluation.

## Access log and unresolved acquisition gates

| Access or activity | Result on this case | Boundary |
|---|---|---|
| Official listing root, 2026-10-17 | Fresh public HTML/text read succeeded; 25 displayed rows. | A public rendered view, not a full database acquisition. |
| Official alternate `MainNewExplorer.aspx` path, 2026-10-17 | Search-index result exposed the same listing and relevant rows. | An indexed corroboration, not a separate independent dataset. |
| Detail/action controls, pagination and export | Not tested. | No claim that these functions or fields are absent. |
| Road/Overpass data | Not acquired for this case. Earlier requests in the same project failed; exact endpoints and outcomes are preserved in [the access follow-up](access_followup.md#requests-that-did-not-yield-data). | No failed request is treated as an empty dataset or zero amenity count. No network/service result follows from this case. |

No SRA source fetch failed during this fresh three-row check. Earlier failed geospatial requests remain unresolved; they are not silently reclassified as successful data acquisition. No interviews, official validation, contact, formal pilot or adoption commitment occurred.
