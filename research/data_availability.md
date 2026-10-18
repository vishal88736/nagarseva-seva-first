# Acquisition results: 18 October 2026

The local files and request manifests are evidence of these results. Access failures
describe this environment at the recorded time, not worldwide service availability.
[Machine-readable validation](acquisition_results.json) contains checksums, paths,
available fields and counts. [The inventory](dataset_inventory.csv) uses the requested
16-column schema; the previous research inventory is preserved separately.

| Source | Actual result | Appropriate use |
|---|---|---|
| SRA GIS-MIS page | HTML downloaded (42,831 bytes); dynamic page, no usable feature export acquired | Source context only |
| SRA Mumbai MapServer and FeatureServer/layers | Both timed out; no live layer IDs, field schemas, feature counts or CRS retrieved | Do not claim feature ingestion; retry the inspector on a reachable service |
| SRA ward/village map PDF | 7,422,603-byte, one-page A0 PDF, parsed and rendered; title specifies GPS Survey 2024 | Exact printed label lookup, historical source reference; no georeferenced polygons |
| SRA public scheme portal | First page HTML downloaded and parsed: 25 rows | Attributed scheme facts; status/date unknown, no reliable settlement join |
| data.gov.in SRA catalogue | HTML downloaded; no resource rows/structured links in returned page, disabled ZIP and sandbox notice | Metadata only; does not establish that indexed CSVs are currently downloadable |
| Geofabrik India catalogue | HTML parsed; country/zonal extracts offered, no large extract acquired | Extract-size discovery; bounded Mumbai pilot is substantially smaller |
| Overpass API and Kumi endpoint | Timeout/HTTP 502 and HTTP 500; additional small probe received HTTP 406 | Failure recorded; no Overpass success claimed |
| Official OSM map bounding-box API | XML successfully downloaded; 7,106 filtered, clipped and validated features | Mapped roads, buildings and amenity context with ODbL attribution |
| Census NADA 6190, 11436, 11448, 11443 and Population Finder | Direct HTTPS certificate-chain validation failed; browsing yielded some indexed metadata but no local table assets | No numerical Census observations imported |
| Dataful Maharashtra PCA | HTML downloaded; structured download, underlying licence and numerical consistency not verified | Discovery only; not an analysis input |
| KoboToolbox / ODK | Official ODK and Kobo export documentation inspected; Kobo main page returned 403 in browsing | Optional new collection workflow; no existing observations obtained |

Seven unique originals were retained under `data/raw`: SRA GIS HTML, SRA map PDF,
SRA listing HTML, OGD catalogue HTML, Geofabrik catalogue HTML, OSM map XML and
Dataful HTML. Exact filenames, hashes and retrieval times are in the validation JSON.
Raw and processed source assets are excluded from Git and Docker build contexts.

The pilot OSM rectangle is west=72.90, south=19.04, east=72.94, north=19.08 (WGS84).
It is a reproducible Govandi context window, not a municipal ward or approved pilot
boundary. The SRA PDF label extract selects exact `ME_[three digits]` text tokens;
156 unique labels were found. This is not a complete digital registry of M/E slums.

Indexed SRA service descriptions suggest historical 2012/2016 cluster layers and
UTM zone 43N services, but this acquisition could not verify their live schemas.
The ingestion code discovers IDs and CRS from actual responses rather than using
these search-index leads as hardcoded facts. It uses bounded ID queries, respects
record limits, and refuses incomplete batches.

Optional-source triage used browsing only, without downloading dataset assets.
The Maharashtra State GIS map request timed out. Bhuvan redirected to its `ngmaps`
loading shell, without a usable layer/export. [Copernicus Data Space](https://dataspace.copernicus.eu/)
and [WorldPop](https://www.worldpop.org/) portal metadata were readable. No specific
asset was selected to fill the missing authoritative cluster/crosswalk or current
service observations. Satellite/population processing would not justify household
water reliability, sanitation functionality or legal status. State GIS/Bhuvan
remain unverified leads for additional geometry, not acquired boundary sources.

No authentication, CAPTCHA, TLS verification or export restriction was bypassed.
No accounts, government requests, field surveys or cloud deployments were made.
