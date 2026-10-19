# Acquisition results: 19 October 2026

This report reflects the successful local validation at **2026-10-19T06:03:53Z**, following acquisition and resumed pagination on **18–19 October 2026**. Initial 18 October findings of only 25 project rows and no numerical Census files are superseded below. Failures describe this environment at recorded times, not worldwide availability.

[acquisition_results.json](acquisition_results.json) records original paths, hashes, retrieval times, fields and checks; all originals listed there passed checksum checks. [dataset_inventory.csv](dataset_inventory.csv) retains the requested 16-column schema and source-specific access states. Raw/processed source assets remain separate and excluded from Git and Docker build contexts.

| Source | Actual final result | Appropriate use / limit |
|---|---|---|
| [SRA GIS-MIS page](https://sra.gov.in/details/sub-category/gis-mis-slum-data) | Official HTML downloaded/parsed | Source discovery, not vector export |
| SRA Mumbai MapServer, FeatureServer, REST root and citizen-mobile alias | HTTPS timeouts; no current live responses verified | No live layer schemas/counts or vector ingestion claimed |
| [2024 cluster register](https://media.sra.gov.in/sra-automation/sra-website/content/1731566774802_3204_Slum%20Cluster%202024.pdf) | 872,732-byte / 79-page PDF; **2,597 rows / 2,596 distinct source IDs** | Historical names/admin strings/printed areas; no polygons or services |
| [GPS Survey 2024 map](https://media.sra.gov.in/sra-automation/category/docs/1731408978437_4524_slum_cluster_ca_2024%20%281%29.pdf) | 7,422,603-byte GeoPDF; **156 exact M/E IDs**, one bounded **1024×1083 raster** | Identifier links and historical cartographic imagery; no analytical settlement polygons |
| [SRA public schemes](https://dms.sra.gov.in/SRAPUBLIC/) | **5,677 rows / 228 advertised pages**, final page reached | Listing facts; status/date, official IDs and settlement joins unknown |
| [OGD catalogue](https://www.data.gov.in/catalog/slum-rehabilitation-authority-brihanmumbai), resource route and official regional mirror | HTML parsed; empty resource shells, main-domain sandbox notice | Metadata only; no ongoing-project CSV obtained |
| [Geofabrik India](https://download.geofabrik.de/asia/india.html) | Catalogue HTML parsed; no large country/zonal extract downloaded | Size discovery; targeted pilot used instead |
| Overpass / Kumi | Recorded timeout / HTTP 502, 500 and small-probe 406 | No successful Overpass acquisition claimed |
| [Official OSM bounding-box API](https://www.openstreetmap.org/api/0.6/map?bbox=72.9,19.04,72.94,19.08) | 12,908,245-byte XML; **7,106 valid selected/clipped features** | Roads, buildings and mapped amenities; operation/access unverified |
| [Census 6190](https://censusindia.gov.in/nada/index.php/catalog/6190) | Official XLS: **2,645 original geography rows / 88 columns** parsed | Reviewed Maharashtra state/town adapter activates 380 PCA observations |
| [Census 11436](https://censusindia.gov.in/nada/index.php/catalog/11436), [11448](https://censusindia.gov.in/nada/index.php/catalog/11448), [11443](https://censusindia.gov.in/nada/index.php/catalog/11443) | Three official PDFs parsed; **12 + 20 + 44** reviewed Maharashtra state cells activated | Historical housing/water/electricity/latrine categories; four missing cells remain null |
| Population Finder / Dataful Maharashtra PCA | No Population Finder numerical extract used; Dataful HTML metadata only | Official assets above used instead; Dataful download/licence/consistency unestablished |
| KoboToolbox / ODK | Official deployment/export documentation inspected; proposed form/import workflow prepared | Optional future authorized collection, not existing observations |

## Parsed source files

| Original under data/raw/ | Parsed result |
|---|---|
| sra/cluster-list-2024-bd9081d656435571.pdf | Serials 1–2,597; Cluster_ID, ward, village/division, taluka, nullable name, printed m² area; 79 null names, 39 overlaps and duplicate MW_041 retained/flagged |
| sra/cluster-map-document-082b9b1406b91058.pdf | GPS Survey 2024 title, printed IDs and four geospatial controls in EPSG:32643 verified; raster map preserved without digitization |
| sra/public-projects-679b04a07aa2d7fc.html through sra/public-projects-page-228-f3193c64017eb572.html | Advertised pages preserved separately; scheme/ward/address/CTS/village/developer/architect/land-type/DCR/proposal and displayed serial fields parsed |
| osm/pilot-map-api-642436ee702273aa.osm | Original tags, unique IDs and WGS84 geometries; unsupported relation topology quarantined |
| census/table-6190-0-693dc15454e8ad53.xls | PCA schema/codes, nonnegative values, population identities and Maharashtra totals checked; selected fields No_HH and TOT_P |
| census/table-11436-0-b5bfd408fe469d33.pdf | Reviewed state housing-condition cells: all uses/residence/residence-cum-other-use × total/good/livable/dilapidated |
| census/table-11448-0-14772dbea735ffec.pdf | Reviewed state water-location × electricity/latrine availability cells |
| census/table-11443-0-8ba15f85577a5d79.pdf | Reviewed state drinking-water source × location cells, retaining four missing values |

HTML source/catalogue files and the public CA intermediate are also retained but are not numerical or geospatial observations. Processed outputs include sra_cluster_register.json, sra_projects.json, sra_pilot_overlay.png/.json, osm_pilot.geojson, census_observations.json and the connected urban_real.json. Exact filenames/hashes/bytes for every original are in the machine-readable report; downloaded whole PDFs are not claimed to have every cell numerically activated.

## Dates and completeness

The register was retrieved **18 October 15:21:26 UTC**. Its **2024** title supplies the reference year; creation metadata is 13 November 2024, while publication/per-cluster dates are unknown. The map was retrieved **18 October 10:42:33 UTC**, has GPS Survey **2024** in its title and creation metadata 30 May 2024. HTTP modification dates are not observation dates.

Project originals span **18 October 15:21:36 UTC to 19 October 05:50:06 UTC**. Completion means reaching the last advertised page, not obtaining an immutable master registry or an ongoing-status extract. Cached/resumed pages may reflect changes during that window. Serial 100 is absent; 10 duplicate-content groups involving 25 rows remain preserved. All **5,677 statuses are unknown** and none is labelled completed/operational without evidence. Source dates, official scheme IDs and reliable settlement joins remain null.

Four numerical Census assets were retrieved on **18 October around 15:23 UTC**. The initial certificate-chain failure was resolved by obtaining the public emSign intermediate and verifying it against installed OS roots. Hostname checks and CERT_REQUIRED remained enabled; **TLS verification was not disabled**. Certificate/verification evidence is in data/metadata/census_tls.json.

The resulting **456 observations** cover **190 original units** (one Maharashtra state plus 189 towns), with **452 numeric values and 4 nulls**, all retaining **2011**. PCA/Houselisting denominators remain separate. State categories are not allocated to towns or SRA clusters. See [data_quality_report.md](data_quality_report.md) and [join_strategy.md](join_strategy.md).

## Spatial, licence and remaining access limits

The WGS84 OSM rectangle is **72.90, 19.04, 72.94, 19.08**: Govandi context, not a current ward or approved pilot boundary. Attribution is **© OpenStreetMap contributors**, under **ODbL-1.0**. Missing features do not prove absent facilities; mapped water points do not establish reliable household access.

The SRA map **is georeferenced**, correcting the initial description, but is cartographic raster context. All four controls were checked before a UTM43N-to-EPSG:3857 warp. Approximately **0.14826 m fit residuals are internal consistency, not ground accuracy**; the roughly 4.11 m ground output grid is not an accuracy claim. No image-derived polygons, cluster access distances or demographic allocations were created. SRA reuse/redistribution terms remain unestablished and assets remain local; no additional third-party licence is asserted for official Census tables.

Maharashtra State GIS timed out; Bhuvan exposed a loading shell without a verified export. Copernicus Data Space and WorldPop metadata were inspected without selecting assets. None supplies the absent dated official vectors, scheme crosswalk or current settlement service baseline. No satellite/population processing was added to imply those missing measurements.

No authentication, CAPTCHA, TLS checks or export restrictions were bypassed. No accounts, government requests or field surveys were created. Remaining substantive inputs require a permitted official boundary/crosswalk extract and/or authorized field inspection; missing values remain missing until then.
