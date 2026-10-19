# Data quality and analysis boundary

Updated **19 October 2026** against the successful local validation at **2026-10-19T06:03:53Z**. Counts describe source/software checks, not field verification, government acceptance or independently measured planning accuracy. Exact original paths, checksums and fields are in [acquisition_results.json](acquisition_results.json); access states and licences are in [dataset_inventory.csv](dataset_inventory.csv).

## Acquired records and fields

| Dataset | Acquired / active records | Analytical geometries | Fields actually available |
|---|---:|---:|---|
| SRA published cluster register 2024 | 2,597 rows; 2,596 distinct official Cluster_ID values | 0 | Source serial, cluster ID, ward, village/division, taluka, nullable slum name, printed m² area, PDF page and provenance |
| SRA GPS Survey 2024 map | 156 distinct M/E printed IDs; one historical raster overlay | 0 settlement polygons | Exact printed ID, title/year, GeoPDF controls/CRS, clipped image bounds, source/image hashes and display limitations |
| SRA public scheme listing | 5,677 source rows across 228 advertised pages | 0 | Scheme name, ward, address, CTS, village, developer, architect, land type, DCR, proposal number, displayed serial and source page |
| OSM Govandi pilot | 7,106 filtered features | 7,106 | OSM type/ID, original tags, nullable name, category, edit timestamp, source URL, clipping flag and WGS84 geometry |
| Census 2011 context | 456 observations: 452 numeric and 4 missing; 190 geographic units | 0 | Original state/town codes and labels, reference year, source table/field/category, value/unit, universe, source-specific denominator, raw path/hash and method |
| Current settlement service baseline | 0 observations acquired | 0 | Water, sanitation/drainage, housing, access and risk indices and current household counts remain missing |

The connected snapshot is data/processed/urban_real.json. Original and processed files remain separate. Missing geometries and observations are not replaced with guessed points, zero or synthetic measurements.

## SRA register, map and schemes

The [official register](https://media.sra.gov.in/sra-automation/sra-website/content/1731566774802_3204_Slum%20Cluster%202024.pdf) is preserved as data/raw/sra/cluster-list-2024-bd9081d656435571.pdf and parsed into data/processed/sra_cluster_register.json. All 79 pages and consecutive serials 1–2,597 passed repeated-header, identifier, administrative-cell and printed-area checks. **79 names are printed as `<Null>`** and remain null in source_name; UI identifier fallbacks are not invented names. **39 long names overlap another printed column** and carry a review warning.

The source genuinely repeats **MW_041** at serials 1410 and 1411: Suman Nagar, 103,909.31 m² and 0.08 m². Both rows remain visible with distinct local IDs and source_id_unique=false; both are excluded from identifier joins. Printed area is a source attribute, not a current land assessment or measured polygon area. Of 174 register rows labelled M/E, **156 exactly match** the earlier printed ME_### map tokens. This is an identifier-only link. Missing extracted map text is not evidence of settlement absence.

The [2024 map](https://media.sra.gov.in/sra-automation/category/docs/1731408978437_4524_slum_cluster_ca_2024%20%281%29.pdf), data/raw/sra/cluster-map-document-082b9b1406b91058.pdf, **is georeferenced**, correcting the initial 18 October report. Its ISO GeoPDF controls declare WGS84 / UTM 43N, but its contents are rasterized, with no imported cluster polygon feature layer. The optional sra_pilot_overlay.png and JSON manifest provide a **1024×1083 EPSG:3857 cartographic image** clipped to the pilot rectangle. All four control-fit residuals are about **0.14826 m**: internal transform consistency, **not surveyed ground accuracy**. The approximately 4.11 m ground output grid does not establish boundary accuracy. The layer has analysis_allowed=false and supplies no area, routing-origin, facility-distance or Census-allocation geometry.

The [scheme portal](https://dms.sra.gov.in/SRAPUBLIC/) reached its last advertised page: **228 pages / 5,677 rows**. Original page retrievals span **2026-10-18T15:21:36Z to 2026-10-19T05:50:06Z**. Cached/resumed pages do not constitute one atomic registry snapshot. The source skips displayed serial 100 and has 10 duplicate-content groups involving 25 rows; these are retained with distinct local identities and ambiguity flags. Displayed serials and local content hashes are not official stable scheme identifiers. All **5,677 project_status values are unknown**, source_id and settlement_id are null, and observation/update dates are unavailable. Source placeholders include 5,195 blank/dash proposal numbers, 579 villages and 23 dash scheme names. Proposed, approved, ongoing, completed and operational phases cannot be established. No structured ongoing-project CSV was obtained from OGD.

## Census geography, fields and denominators

Four official numerical assets were obtained after the initial certificate-chain problem was resolved using a public, OS-root-verified intermediate certificate; hostname and certificate checks remained mandatory.

| Catalogue / local original in data/raw/census/ | Source schema and activated context |
|---|---|
| [6190](https://censusindia.gov.in/nada/index.php/catalog/6190), table-6190-0-693dc15454e8ad53.xls | Original PCA workbook: 2,645 geography rows / 88 columns. Maharashtra state and 189 source town units supply 380 No_HH / TOT_P household and population observations. |
| [11436](https://censusindia.gov.in/nada/index.php/catalog/11436), table-11436-0-b5bfd408fe469d33.pdf | Twelve Maharashtra state cells: all uses, residence and residence-cum-other-use × total/good/livable/dilapidated condition. |
| [11448](https://censusindia.gov.in/nada/index.php/catalog/11448), table-11448-0-14772dbea735ffec.pdf | Twenty Maharashtra state cells: water-location categories with electricity and latrine availability. |
| [11443](https://censusindia.gov.in/nada/index.php/catalog/11443), table-11443-0-8ba15f85577a5d79.pdf | Forty-four Maharashtra state cells: water source by total/within/near/away categories; four printed missing cells remain null. |

Only reviewed adapters are activated in data/processed/census_observations.json. Other pages/cells in a downloaded PDF are not claimed as parsed numerical observations. All observations retain **2011**, not retrieval in 2026. The four nulls are within-premises spring, river/canal, tank/pond/lake and other-source categories in 11443; none becomes zero.

The Maharashtra PCA household total is **2,499,948**, versus **2,449,530** in the Houselisting universe. Residence and residence-cum-other-use subtables also retain their own denominators. These universes must not be substituted or merged. Original labels such as **“Greater Mumbai (M Corp.) (Part)”** are preserved; current municipal equivalence is not assumed. No district, ward or settlement allocation is performed. Historical observations are excluded from current deficit scoring.

## OSM quality and limits

The original data/raw/osm/pilot-map-api-642436ee702273aa.osm was retrieved on 18 October at 10:45:14 UTC; data/processed/osm_pilot.geojson holds the validated selection. The WGS84 rectangle **72.90, 19.04, 72.94, 19.08** is Govandi context, not a ward or approved pilot boundary.

Disjoint display categories are **2,885 roads, 3,692 buildings, 168 amenities, 93 transport, 266 residential context and 2 water-infrastructure objects**. All 7,106 IDs are unique and geometries pass nonempty, validity and WGS84 bounds checks. Unsupported relation topology remains quarantined, clipping is flagged, and contributor usernames/IDs are omitted.

Retained amenity tags include 34 school, 49 hospital, 23 clinic, 7 doctors, 18 toilets, 3 drinking_water, 4 bus_station, 3 college and 2 kindergarten objects. These are mapped tags, not verified institution counts, functioning assets, capacity or household access. Building tags do not establish housing condition. Missing features do not establish missing facilities; mapped water points do not establish reliable household service. Edit times are not field observation dates.

## Supported analysis and remaining evidence

Supported joins are 156 exact unique register–map identifier links, original-code/year Census observation links, and a context-only OSM QA join: whole-geometry coverage by exactly one residential polygon yields **55 matches among 263 objects**, with **208 unmatched or ambiguous**. None establishes scheme-to-cluster linkage, household coverage or current ward boundaries. See [join_strategy.md](join_strategy.md).

Suitable uses are historical lookup, original-geography Census context, mapped-tag inspection, collection planning, explicitly hypothetical scenario arithmetic, and authorized intervention/evidence/complaint workflows. Current household estimates, real cluster-access distances, current deficit rankings and official redevelopment feasibility/costs remain unsupported. Zero documented current deficits means no qualifying measurements were loaded, not absence of need.

Planning still needs permitted dated vector boundaries/stable IDs, an authoritative scheme/parcel crosswalk, current household denominators, repeated water reliability/quality observations, toilet/drainage inspections, engineering/risk assessments, verified facility entrances/capacity, quotations and resident/livelihood consultation. These require an authorized government request and/or field work. A proposed field form is not collected evidence.

OSM attribution and **ODbL-1.0** requirements remain applicable. SRA reuse permission is not established and source assets remain local; no additional third-party licence is asserted for official Census tables.
