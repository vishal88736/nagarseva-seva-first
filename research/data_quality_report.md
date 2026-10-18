# Data quality and analysis boundary

Validated locally on 18 October 2026. This report describes source/software checks,
not field verification, government acceptance or independently measured performance.

## Obtained records and fields

| Dataset | Records | Geometries | Available fields |
|---|---:|---:|---|
| SRA PDF M/E label extract | 156 distinct exact labels | 0 | Printed source ID, map title, 2024 title reference, source URL, retrieval time; names and household counts unavailable |
| SRA first public listing page | 25 | 0 | Scheme name, ward, address, CTS, village, developer, architect, land type, DCR, proposal and displayed row number |
| OSM pilot | 7,106 | 7,106 | OSM type/ID, original tags, nullable name, category, edit timestamp, source URL, clipping flag, geometry; observation date remains null |
| Census numerical observations | 0 acquired | 0 | No locally parsed numerical table; source metadata identifies historical 2011 tables only |
| Current cluster service observations | 0 acquired | 0 | None; field form is a proposal, not collected data |

OSM disjoint display categories: 2,885 roads, 3,692 buildings, 168 amenities,
93 transport objects, 266 residential context objects and 2 water infrastructure
objects. These are category counts, not counts of mutually exclusive original tags:
some amenities are also tagged as buildings. A building tag does not identify its
inhabitants or establish housing condition.

Actual `amenity` tags include 34 schools, 49 hospitals, 23 clinics, 7 doctors,
18 toilets, 3 drinking-water objects, 4 bus stations, 3 colleges and 2 kindergartens.
Additional tags, including place_of_worship and commercial uses on otherwise
selected buildings, are retained and inspectable. These categories describe mapping;
they are not verified institutional counts, openings, capacities or functioning assets.
Two objects in the separate water-infrastructure category are not household-access
measurements. An absent feature is not proof of an absent facility.

All 7,106 processed OSM geometries pass Shapely validity/nonempty checks and WGS84
coordinate bounds; all source IDs are unique. Invalid or unsupported relation
topology is retained in the immutable original and quarantined from the processed
features. The rejection list and null/blank attribute counts are in
`data/metadata/osm_ingestion.json` and `research/acquisition_results.json`.
Clipped geometry is explicitly flagged. OSM contributor user names/IDs are not
propagated into the processed app data.

## Dates and completeness

The SRA PDF title specifies GPS Survey 2024. PDF creation metadata is 30 May 2024;
HTTP Last-Modified is a server timestamp, not a publication or observation date.
Individual label observation dates, current official recognition and machine-readable
boundaries are unavailable. The 156 identifiers are unique printed tokens, not a
certified total. They are neither geocoded nor interpolated onto the map.

SRA scheme update dates and project phases are absent from the acquired listing.
All 25 have `project_status=unknown`, `source_id=null` and `settlement_id=null`.
The displayed row number is preserved separately; the local content hash is never
represented as an official identifier. Proposed/ongoing/completed classifications
cannot be established from this page. OGD advertises an ongoing-project resource
in indexed metadata, but that resource was not downloaded or joined here.

OSM edit times and retrieval dates are not facility observation dates. All current
W/S/H/A/R deficit indices and settlement household counts remain null. Zero
documented deficits on the dashboard means no qualifying observations were loaded;
it does not mean that services have no deficits.

Census 2011 remains historical. Metadata for 6190 describes country/state/town
PCA slum counts; metadata for HL-01 and HL-06 identifies India/state household
tables. The exact local files, numerical values and full schema of 11448 remain
unverified. No state, town or ward values are assigned to any cluster. Census
catalogue creation dates in 2021 are not dates of the underlying observations.

## Joins and suitable analysis

No SRA scheme-to-settlement or Census-to-settlement join is justified by these
downloads. A QA join of 263 mapped amenity/transport/water features to acquired
OSM residential polygons used whole-geometry coverage by exactly one polygon:
55 unique containment matches and 208 unmatched or ambiguous cases. This is
context-only spatial association, never a slum, household or service-coverage join.
See [join_strategy.md](join_strategy.md).

Suitable now: inspect mapped context/tags, review source labels and scheme facts,
identify missing evidence, test deterministic arithmetic, and record authorized
user plans, evidence references and review outcomes. Cluster walking distances,
facility accessibility, service-deficit rankings, current household estimates,
official project costs and redevelopment feasibility cannot currently be derived.
Scenario costs/coverage/disruption remain explicit user assumptions.

Required for substantive planning: permitted authoritative polygons with dates and
stable IDs; a dated scheme/land-parcel crosswalk; current household denominators;
repeated water availability/quality observations; functional shared-toilet and
drainage inspections; housing/engineering assessments; facility entrances/capacity;
resident/livelihood consultation; approved quotations and infrastructure constraints.
These require an agreed government data request and/or authorized field work.
