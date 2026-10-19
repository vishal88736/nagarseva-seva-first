# SRA acquisition follow-up — 18 October 2026

The application can now use the official historical **2024 published cluster register** and an optional correctly georeferenced **2024 cartographic raster**. Neither source establishes current household services, legal eligibility, operational project status or analytical settlement polygons.

## Published cluster register

Source: [SRA SLUM CLUSTER LIST 2024](https://media.sra.gov.in/sra-automation/sra-website/content/1731566774802_3204_Slum%20Cluster%202024.pdf), discovered through the official GIS-MIS source listing/search index.

- Original: `data/raw/sra/cluster-list-2024-bd9081d656435571.pdf` — **872,732 bytes**, SHA-256 `bd9081d656435571c1299b1d82d2dccbf284f3fe7898643fafa278c442625667`.
- Retrieved: `2026-10-18T15:21:26.115751+00:00`. Reference year **2024** comes from the document title, not the retrieval date. PDF creation metadata is `2024-11-13T20:08:23+05:30`; publication and individual observation dates remain unknown.
- All **79 pages**, source serials **1–2,597**, were parsed using Poppler word coordinates. Repeated header positions, serial sequence, administrative cells, official identifier format and one positive printed decimal area per row are validated.
- Fields: `Sr.no`, `Cluster_ID`, `Ward`, `Village_Division`, `Taluka`, `Slum_Name`, `Shape_Area (Sq.mtrs)`.
- **2,597 rows; 2,596 distinct source Cluster_ID values; 2,597 distinct local row IDs.** The source genuinely prints `MW_041` twice: serial 1410, Suman Nagar, 103,909.31 m²; serial 1411, Suman Nagar, 0.08 m². Both remain visible with `source_id_unique=false`, distinct local row IDs and a warning; neither participates in an identifier join.
- **79 names are `<Null>` in the source** and remain null. A UI fallback may display the official ID, but it is not a claimed settlement name.
- **39 long name cells overlap the area column in the source.** Underlying text is preserved with `name_overflow_in_source=true` and a spelling-review warning. The area is extracted independently; it is never consumed as part of the name.
- The source includes **174 M/E ward rows**. All **156** earlier extracted `ME_###` printed map labels match a unique register `Cluster_ID` exactly. This adds attributed register facts to those identifiers, not geometry or current ward crosswalks. The additional 18 M/E register rows are retained; absence of extracted map text does not imply absence of a cluster.
- Output: `data/processed/sra_cluster_register.json`; acquisition/validation diagnostics: `data/metadata/sra_register_ingestion.json`.

No ward totals are allocated to clusters. No project records are joined by similar names, CTS fragments or vicinity. The licence/reuse permission for SRA material is not established; originals and generated map assets remain local and excluded from Git.

## Georeferenced historical map

Source: [SRA ward/village and competent-authority map, GPS Survey 2024](https://media.sra.gov.in/sra-automation/category/docs/1731408978437_4524_slum_cluster_ca_2024%20%281%29.pdf).

The earlier description that this PDF was *not georeferenced* was incorrect. Inspection found an ISO geospatial `/Viewport` and `/Measure /GEO` dictionary containing four `/GPTS` geographic controls, corresponding `/LPTS` map controls and a declared WGS84 / UTM Zone 43N WKT (**EPSG:32643**).

The map contents are rasterized: **964 embedded images**, no optional-content/feature attribute registry, and no cluster polygon feature layer. The 3,149 drawing operations comprise 2,834 rectangular clip operations, 302 strokes (including outlined text and legend symbols) and 13 fills. Those drawing operations must not be interpreted as settlement polygons.

`scripts/ingest_sra_pdf.py` validates the original PDF checksum and GPS Survey 2024 title, transforms all four latitude/longitude control points into the declared UTM CRS, checks a single affine fit and clips the map to **[72.90, 19.04, 72.94, 19.08]** (west, south, east, north). Rasterio then warps the bounded rendered source into an **EPSG:3857** image grid compatible with Leaflet. There is no image segmentation, tracing or boundary reconstruction.

- Original PDF SHA-256: `082b9b1406b91058799a5741fb2e138722d98bffa26ea4c59c2ac462a27f79ae`.
- Each control-point fit residual: approximately **0.14826 m**. This measures internal transform consistency of rounded PDF controls, **not surveyed ground accuracy**.
- Output: `data/processed/sra_pilot_overlay.png`, **1024 × 1083 RGBA**, **440,631 bytes**; SHA-256 `a8a1d8827ef43a1487edec5a13a97a4bbb73696dfac9531ed03e82b77b4291b1`.
- Output grid: about **4.3484 × 4.3500 Web Mercator metres/pixel**, or approximately **4.11 ground metres/pixel** at the pilot latitude. This grid spacing is not a claim about boundary accuracy.
- Manifest: `data/processed/sra_pilot_overlay.json`, with source/image hashes, CRS, all controls/residuals, source clip, output bounds/resolution, `source_date="2024"`, `analysis_allowed=false` and `settlement_geometry_count=0`.
- PNG parsing, dimensions, full alpha coverage, repeated deterministic output hash, and a rendered visual check succeeded.

Use the overlay only as optional historical cartographic context. It must not supply cluster area calculations, facility-access distances, routing origins, spatial allocation of Census values or legal boundaries. Source cartographic scale, symbols, labels and unknown registration error remain material limitations.

## Public schemes and blocked GIS services

The [public SRA listing](https://dms.sra.gov.in/SRAPUBLIC/) exposes advertised ASP.NET page links without login or CAPTCHA. Pagination follows only those same-origin sequential actions, retains originals and source displayed serials, enforces a page/download limit, and detects repeated/reversed pages or changed schemas. Published serial gaps and duplicate scheme content are preserved and reported, not filled or silently collapsed. Local hashes and duplicate-row suffixes are not official project identifiers. `project_status`, source observation date and settlement linkage remain unknown where absent from the source. See the current `data/metadata/sra_projects_ingestion.json` for the actual acquisition count, final-page confirmation, configured limit and any remaining pagination error.

The official OGD [ongoing-project resource route](https://www.data.gov.in/resource/ongoing-projects-under-slum-rehabilitation-authority-brihanmumbai) and [official regional mirror](https://kerala.data.gov.in/resource/ongoing-projects-under-slum-rehabilitation-authority-brihanmumbai) were downloaded and parsed as HTML. Both returned empty resource shells without downloadable structured assets; the main domain included a sandbox warning. No ongoing-project CSV was obtained from them.

Live HTTPS requests to the supplied SRA MapServer, FeatureServer, REST root and the officially indexed `SRA/SRA_Citizen_Mobile/MapServer` alias timed out. Browsing also failed to fetch current service metadata. Search-index descriptions of past layers are discovery context only; **no live layer schema, feature count, supported query result or vector feature was verified from those services**. Authentication, CAPTCHA, TLS checks and access restrictions were not bypassed.

## Reproduction and verification

From the repository root, with Poppler installed:

```bash
uv pip install --python nagarseva/.venv/bin/python -r scripts/requirements-data.txt
nagarseva/.venv/bin/python scripts/ingest_sra_register.py
nagarseva/.venv/bin/python scripts/ingest_sra_pdf.py
nagarseva/.venv/bin/python scripts/ingest_sra_projects.py --max-pages 400
PYTHONPATH=scripts:nagarseva nagarseva/.venv/bin/python -m pytest tests/test_sra_geopdf.py tests/test_sra_sources.py tests/test_data_pipeline.py -q
```

The combined source/coordinate tests actually run at this stage: **45 passed**. They include the nested pager regression, schema/action/limit/repeated-page/download failure handling, duplicate-content preservation, source register nulls/duplicate IDs/area separation/layout rejection, latitude/longitude order, projected-coordinate hand examples, rounded controls, and rejection of non-affine or changed-CRS inputs. These are protocol and transform checks; they do not establish current SRA service availability or field accuracy.
