# Census numerical acquisition follow-up — 18 October 2026

The earlier certificate failure was resolved without disabling TLS. All four requested official Census catalogue assets were downloaded, parsed and checked. The numerical data describe **2011**, not present conditions.

## HTTPS diagnosis and reproducible repair

The Census server presented its leaf certificate without the `emSign SSL CA - G1` intermediate. Both Python's default trust store and the OS trust store rejected that incomplete chain with `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`.

The leaf certificate's Authority Information Access named the public intermediate. The pipeline obtains it through ordinarily verified HTTPS from [emSign's official repository](https://repository.emsign.com/certs/emSignSSLCAG1.crt), verifies its SHA-256 and runs `openssl verify` against installed OS trust roots before adding that intermediate to the request-specific SSL context. It does not install a root certificate or edit the system trust store. Hostname checks and `CERT_REQUIRED` stay enabled; the downloader rejects unsafe SSL contexts and `verify=False`.

Intermediate SHA-256: `47b2efbc3670e7db4b41f22c51fc02ee84fb2dbf3082a49f2c2688122e9210a1`. Certificate changes require explicit code review of the pin. The verification result and immutable original are recorded in `data/metadata/census_tls.json`. OpenSSL verification returned `OK`, followed by successful verified HTTPS requests to the original Census host. No authentication or access control was bypassed.

Run from the repository root:

```bash
nagarseva/.venv/bin/python scripts/ingest_census.py
```

OpenSSL and Poppler (`pdftotext`) must be available. The standard downloader keeps explicit connect/read timeouts, a 25 MB response limit, checksum-verified cache and immutable originals. `--refresh` creates another snapshot while preserving older bytes. A failed certificate repair falls back to normal certificate verification rather than bypassing it.

## Obtained official table files

| Catalogue / original public download | Local original | Bytes | Parsed/activated scope |
|---|---|---:|---|
| [PCA SLUM 6190](https://censusindia.gov.in/nada/index.php/catalog/6190/download/9267/slum_data_census_2011.xls) | `data/raw/census/table-6190-0-693dc15454e8ad53.xls` | 1,658,368 | 2,645 source geography records, 88 columns; Maharashtra subset: 1 state + 189 towns |
| [HH-1 housing condition 11436](https://censusindia.gov.in/nada/index.php/catalog/11436/download/14549/SHH0101-crc.pdf) | `data/raw/census/table-11436-0-b5bfd408fe469d33.pdf` | 187,584 | 12 Maharashtra state housing-use/condition cells |
| [HH-11 water/electricity/latrine 11448](https://censusindia.gov.in/nada/index.php/catalog/11448/download/14561/SHH3711-crc.pdf) | `data/raw/census/table-11448-0-14772dbea735ffec.pdf` | 550,962 | 20 Maharashtra state cells: all water sources × location × electricity/latrine availability |
| [HH-6 drinking-water source/location 11443](https://censusindia.gov.in/nada/index.php/catalog/11443/download/14556/SHH2206-crc.pdf) | `data/raw/census/table-11443-0-8ba15f85577a5d79.pdf` | 249,697 | 44 Maharashtra state cells; four printed dashes remain null |

All four official HTML catalogues and the Population Finder HTML were also downloaded and parsed for discovery. The latter and the retained Dataful metadata do not add numerical observations. The public CA certificate is transport metadata, not a statistical dataset. SHA-256, source URL, retrieval timestamp and actual local path are retained for each asset. Public download availability is not an assertion of an additional reuse licence; publisher/source attribution and applicable government terms must accompany redistribution.

`data/processed/census_6190_0.json` preserves the full workbook and 2,645 cleaned source rows. `data/processed/census_slum_pca_maharashtra.json` retains all 88 columns for all 190 Maharashtra rows. The other three `census_<catalogue>_0.json` files preserve full PDF text plus reviewed Maharashtra cells. The source PDF pages were rendered and visually checked: HH-1 page 3, HH-6 page 9, HH-11 page 49. Column headers and Maharashtra row values match the implemented adapters. HH-11's remaining source-specific groups are retained in the original/text, with no guessed continuation-page adapter.

## Original geography, figures and validation

PCA retains `State Code`, `Town Code`, `Area Name`, `No_HH`, `TOT_P`, `TOT_M`, `TOT_F`, age 0–6, scheduled caste/tribe, literacy and work-category columns. All 88 columns are preserved; app observations currently activate only `No_HH` and `TOT_P`.

Validation checked the schema, unique original two-digit state/six-digit town keys, integer/nonnegative counts, population sex totals, literacy/illiteracy and worker/non-worker identities. Maharashtra's 189 town rows sum exactly to the state row for households, population and male/female totals.

- Maharashtra `27:000000`: 2,499,948 slum households; 11,848,423 slum population (PCA 2011).
- **`Greater Mumbai (M Corp.) (Part)`**, original `27:802794`: 1,135,514 slum households; 5,206,473 slum population (PCA 2011). The exact `(Part)` label is retained. These are not asserted to represent a present-day municipal boundary.
- Maharashtra Houselisting and Housing tables use **2,449,530 households**, which differs from PCA's 2,499,948. Different table phases/universes are recorded. Values and denominators are never interchanged.

HH-1 preserves total/residence/residence-cum-other-use × total/good/livable/dilapidated. HH-6 preserves source category × total/within/near/away. HH-11's selected cells preserve all-source water location crossed with electricity and latrine availability. Counts and arithmetic subtotals were checked. A printed dash is preserved as null, not assigned zero. Neither “tap water” nor “latrine available” establishes current reliability, household access or facility function.

## Application integration contract

`data/processed/census_observations.json` contains **190 geographic units and 456 historical observations**: 380 PCA population/household counts, 12 housing cells, 44 water cells and 20 combined household-amenity cells. Of these, 452 have numerical values and four retain a missing source value.

Every observation has `settlement_id: null`, `geographic_unit_id`, `reference_year: 2011`, `observation_date: null`, `geographic_resolution`, original source URL/field/label, table phase, universe, retrieval time and raw checksum/path. HH observations additionally retain the relevant denominator and its 2011 reference year. `verification_status` is `historical_published`, not field-verified. Units have no fabricated geometry and no approximate cluster crosswalk.

The units use `census2011-27-<Town Code>` IDs; the state is `census2011-27-000000`. These are local namespace IDs, with original `27:<Town Code>` separately retained. Town parent IDs identify the original state hierarchy. No ward or settlement values are derived from state/town totals. The observations cannot fill W/S/H/A/R settlement deficit indices or produce current settlement rankings.

## Tests and remaining boundary

Executed:

```bash
PYTHONPATH=scripts:nagarseva nagarseva/.venv/bin/python -m pytest tests/test_census_tables.py tests/test_data_pipeline.py -q
```

Result: **40 passed**. These offline regression checks cover schema/count/code errors, duplicate keys, arithmetic mismatches, preserving `(Part)`, dash/null semantics, state reconciliation, no settlement allocation/current date and rejection of disabled TLS checks. Modified acquisition/parser files also passed Ruff F401/F841; `git diff --check` passed. Live acquisition separately confirmed four parsed official assets and zero catalogue errors.

Still missing: current settlement-level observations, an authoritative 2011 administrative/settlement crosswalk, source-permitted settlement polygons and official project links. Historical Census context is now acquired; it does not resolve those independent gaps. Field observations remain necessary for current service assurance.
