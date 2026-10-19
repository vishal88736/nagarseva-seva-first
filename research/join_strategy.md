# Defensible geographic joins

Updated **19 October 2026**. Sources retain original identifiers, geography, dates and table universes. There are **no acquired analytical SRA settlement polygons** and no reliable project-to-settlement crosswalk.

## Implemented joins

1. **Register to printed map identifier:** the 2024 register has 2,597 rows / 2,596 distinct Cluster_ID values. Exact equality against 156 printed ME_### map tokens yields **156 unique matches**. A source_aliases entry preserves both source references and the identifier-only method. It adds historical name/ward/village/taluka/printed-area context, not position, polygon or current legal status. The register has 174 M/E rows; missing extracted map text does not establish absence of a cluster.
2. **Census observations to original units:** match explicit source codes and **2011 reference year**, retaining state code 27 and source town codes. The active context has one Maharashtra state unit plus 189 town units. Each observation must match its unit's resolution/year; settlement_id remains null. Maharashtra Houselisting categories stay at state resolution. Labels including **“Greater Mumbai (M Corp.) (Part)”** are not current municipal-boundary crosswalks.
3. **OSM objects to residential context:** source IDs retain node/…, way/… and relation/… namespaces. The strict spatial join accepts only whole-geometry coverage by **exactly one** residential polygon. Among 263 amenity/transport/water objects, **55 match** and **208 remain unmatched or ambiguous**. The method/candidate count is recorded in data/processed/osm_residential_context_join.json. A residential tag is not an official slum or household boundary; this is context-only association.

No nearest-centroid, fuzzy-name, area-weighted population or approximate CTS join is used.

## Ambiguous source identities

The register genuinely repeats MW_041 at source serials 1410 and 1411. Both rows retain separate local IDs, source_id_unique=false and warnings; **neither participates in automatic identifier joins**. Other register IDs retain the sra-map- namespace so existing M/E operational references remain usable. Seventy-nine source-null names remain null in source_name. Thirty-nine overlapping name cells are flagged for review, not corrected by approximate matching.

The **5,677 scheme rows** preserve displayed serials, page, content hash and raw ward/village/CTS/proposal strings. Ten repeated-content groups involving 25 rows retain distinct local identities. Hashes, duplicate-row suffixes and displayed serials are **not official stable scheme IDs**. Shared CTS values, absent proposals, dash names and village strings are insufficient geographic keys. Keep settlement_id=null until an official dated crosswalk or a unique, independently reviewed parcel intersection supports linkage.

Completion of 228 pages proves only that the last advertised public page was reached. Its **18–19 October 2026** retrieval window is not an atomic registry export; original source-page times remain attached to records.

## CRS and vintage boundaries

The 2024 reference PDF contains ISO GeoPDF controls in **WGS84 / UTM 43N**, but map contents are rasterized. The optional pilot image is transformed to an **EPSG:3857 image grid** for Leaflet with WGS84 image bounds and analysis_allowed=false. Approximately **0.14826 m control-fit residuals measure internal consistency, not ground accuracy**. Pixels must not become analytical settlement polygons, household allocations, routing origins or facility distances. Printed area is not a reconstructed polygon.

If a live SRA vector service becomes accessible, discover actual IDs, official/OID fields, schemas, query support and CRS before ingestion. Request WGS84 or explicitly transform the declared CRS using longitude/latitude order; namespace IDs by service/layer. Do not merge historical 2012/2016 service layers with a 2024 register into an apparent current boundary layer. Endpoint accessibility does not establish publication or observation dates. No current live vector schema or features were verified during this acquisition.

OSM geometry is WGS84; invalid/unsupported relation topology is quarantined and clipping is explicit. Edit timestamps are not verified facility-operation dates. Missing objects do not establish missing facilities.

## Measures that remain incompatible

PCA and Houselisting household universes differ: Maharashtra has **2,499,948 PCA households versus 2,449,530 Houselisting households**, with further category-specific denominators. Preserve table, phase, source unit, universe and denominator on every observation. No state/town/ward statistic is distributed among SRA clusters. Historical aggregates and raw physical field measurements do not become normalized current indices without an approved protocol.

No acquired settlement entrance, origin or defensible street connection exists. Scenario responses therefore keep access_available=false and empty distance arrays; missing access is not zero metres. Current households, W/S/H/A/R indices, land/infrastructure constraints and official costs remain unavailable, while hypothetical assumptions are labelled.

Additional joins require a permitted dated vector extract/stable IDs, original Census geography boundaries or crosswalks where needed, an authoritative scheme/parcel link and checked settlement entrances. Compatible geometry alone does not resolve different reference years, legal definitions or household universes.
