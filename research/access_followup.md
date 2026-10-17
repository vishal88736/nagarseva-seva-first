# Source-access follow-up

Access date for every attempt in this note: **2026-10-17**. This is an addendum to the original inventory, not a claim that the restricted or failed inputs have now been downloaded. Only this addendum was created during the follow-up. No household records, logins, CAPTCHA responses or complaint submissions were used.

## Results that change the research position

| Question | Result | Appropriate interpretation |
|---|---|---|
| What is Census catalogue 11441? | Official indexed catalogue metadata resolves its identity and schema. Direct requests still fail. | Upgrade metadata confidence; preserve the file-acquisition barrier. |
| Is there an official SBM-U 2.0 operational-guidelines source? | Maharashtra DMA publishes the October 2021 guidelines; official indexed Chapter 10 text was readable. | Existing functional-asset monitoring and integration are stronger counterevidence to generic product novelty. |
| Can this environment retrieve a small road/amenity extract? | Direct Overpass and OSM bounding-box requests were inaccessible to the web tool. Three OSM-derived transport reference points were readable on Mapcarta. | Reference-marker transcription is possible; no acquired routing network or verified service inventory exists from these attempts. |

## Census catalogue 11441: identity resolved, file not acquired

The official indexed record identifies **“SLUM HL-04: Slum households by ownership status of the census houses, size of the household and number of dwelling rooms - 2011”**, reference **PC11_SLUM_HL04**. The publisher is the Office of the Registrar General & Census Commissioner, India. It records 2011 observations, metadata created/modified 2021-01-21, and **India/State** geography, including Maharashtra. It advertises **`SHH1604-crc.pdf`**. Columns classify dwelling-room counts; rows cross household size with owned/rented/other ownership. These are aggregate historical tables, not settlement polygons or current household records. [Official catalogue](https://censusindia.gov.in/nada/index.php/catalog/11441).

The direct catalogue request returned **502 Bad Gateway**, while its [study-description route](https://censusindia.gov.in/nada/index.php/catalog/11441/study-description) returned a cache miss. An exact-URL search retrieved the above official indexed metadata. The advertised PDF was **not downloaded or ingested**. Its exact download link, numerical table values and reuse conditions remain unverified. A dwelling-ownership category must not be converted into a legal tenure or scheme-eligibility determination.

## SBM-U 2.0: official source and material counterevidence

Maharashtra's Directorate of Municipal Administration [mission archive](https://mahadma.maharashtra.gov.in/en/services-type/mission/sbm/) lists the operational guidelines with a **2025-07-11 posting date** and **10.6 MB** size. The [official PDF URL](https://mahadma.maharashtra.gov.in/wp-content/uploads/2025/07/swachh-bharat-2.pdf) is indexed as the Ministry of Housing and Urban Affairs' **October 2021** document. Posting date and guideline vintage differ.

The indexed **Chapter 10, printed page 81, sections 10.1–10.3.1** describes digital monitoring of functional assets, ICT/GIS evaluation, and an integrated platform containing city/ward profiles, infrastructure/asset details and periodic sanitation/waste-management reporting. Section 10.3.2 describes Swachhata complaint handling. Therefore, a proposal cannot defensibly claim that integration, functional-asset monitoring or digital complaints are absent from existing mission design. Whether these functions work adequately in the selected ward requires local evidence. [Official guidelines, indexed relevant section](https://mahadma.maharashtra.gov.in/wp-content/uploads/2025/07/swachh-bharat-2.pdf).

Access classification: **INDEXED_SECTION_READ**, not full-document acquisition. Direct PDF fetch failed without a useful response. The [individual DMA listing](https://mahadma.maharashtra.gov.in/en/services/swachh-bharat-mission-urban-2-0-operational-guidelines/) and archive returned page content containing “Content is protected”; no restriction was bypassed. A [second official SBM document route](https://www.swachhbharaturban.gov.in/sbmdocumentfile.aspx?DOCID=57&DOCTYPE=9999&id=2yq6fatgof67yj4d) timed out. A [Mizoram government mirror](https://udpa.mizoram.gov.in/uploads/attachments/2022/07/98dd10d220bb79bd82dd8728df5a8064/4.pdf) returned 403. These are tool/session results, not findings that the sources are globally unavailable.

## Small public spatial inputs: what is and is not usable

The following coordinates were genuinely visible as **secondary, OSM-derived public reference records**. They can support a small attributed location display if kept separate from operationally verified assets. Their underlying observation/edit dates were not established; an access date is not a survey date. The points were transcribed from rendered records, not downloaded as a geospatial dataset.

| Reference | OSM feature identifier reported by source | Longitude | Latitude | Reported mapping classification | Source and boundary |
|---|---|---:|---:|---|---|
| Govandi railway station | node 3205733664 | 72.91507 | 19.05537 | `railway=station`; `public_transport=station` | [Mapcarta record](https://mapcarta.com/N3205733664). Not an entrance, timetable, fare, capacity or verified step-free route. Its reported wheelchair tag is not an accessibility inspection. |
| Bainganwadi bus stop | node 3439107263 | 72.92437 | 19.05903 | `highway=bus_stop` | [Mapcarta record](https://mapcarta.com/N3439107263). No verified current route, frequency, safe crossing or accessible boarding information. |
| Shivaji Nagar Bus Depot | way 395230147 | 72.92915 | 19.06604 | `amenity=bus_station`; `public_transport=station` | [Mapcarta record](https://mapcarta.com/W395230147). A displayed representative point for a way, not its acquired boundary or passenger entrance. |

Mapcarta explicitly attributes its records to sources including OpenStreetMap. Any reuse of underlying OSM data needs [OpenStreetMap attribution and applicable ODbL obligations](https://www.openstreetmap.org/copyright). This does not grant reuse rights to unrelated photographs, satellite tiles or all third-party page content. Preserve each record's source URL, reported OSM identifier, secondary-source status and unknown observation date. These three points cannot establish amenity completeness or household access.

### Requests that did not yield data

| Exact requested endpoint | Observed result | Consequence |
|---|---|---|
| [Small OSM bounding-box API request](https://api.openstreetmap.org/api/0.6/map?bbox=72.9100%2C19.0500%2C72.9110%2C19.0510) | Web tool reported URL inaccessible. | No XML, road geometry, nodes, tags or data timestamp obtained. |
| [Small Overpass toilet query](https://overpass-api.de/api/interpreter?data=%5Bout%3Ajson%5D%5Btimeout%3A10%5D%3Bnwr%5Bamenity%3Dtoilets%5D%2819.045%2C72.905%2C19.065%2C72.925%29%3Bout%20center%205%3B) | Web tool reported URL inaccessible. | No toilet records or count obtained. An empty result was not observed; missing acquisition must not become a zero count. |
| [OSM Baiganwadi feature](https://www.openstreetmap.org/way/289795851) | Web tool reported URL inaccessible. | Mapcarta's [Baiganwadi location record](https://mapcarta.com/W289795851) supplies a reference location, but no primary polygon was acquired. A residential mapping tag is not legal slum recognition. |

A historical [Pune road-data author page](https://manishraj.dev/blog/post/generate_vector_tiles_built_in_postgis_functions/) advertises an OSM-derived road extract from **2019** and links a GitHub archive. This is a discovery lead only: archive contents, current availability, topology, licence packaging and extraction were not tested. It is unsuitable as an assumed current routing network. [Advertised GitHub project](https://github.com/androidfanatic/tiles_with_st_asmvt).

## Consequences for the working prototype

1. Keep official guideline evidence, real public reference markers and illustrative scenarios in separate data layers with visible provenance. No current asset-health or service-deficit label follows from a marker's presence.
2. If a real road extract is acquired later, validate its geometry, topology, pedestrian permissions, relevant barriers, dates and licence before labelling any result a network route. Until then, only calculate explicitly labelled straight-line reference distances or use an honestly labelled illustrative network. Do not call either measured walking access.
3. The incremental-value test is whether traceable evidence and repeat observations improve a specific existing review workflow; generic GIS, asset monitoring and complaint handling already have documented precedents.
4. Remaining acquisition gates are a lawful small road extract, authoritative/approved geographic units, a current asset list, independent repeat service observations and an accountable local workflow owner. No contact, survey, adoption agreement or official operational validation occurred in this follow-up.

