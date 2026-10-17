# Input schema — Seva Evidence 1.0

Import a single UTF-8 JSON file, at most **5 MB**. The file remains in the browser tab. Download the synthetic template from the import dialog for a complete example. No input is independently verified merely because it passes schema validation.

Required root fields:

| Field | Format / boundary |
|---|---|
| `schema_version` | Exactly `"1.0"` |
| `metadata` | Source, date, licence and synthetic-status fields below |
| `network` | GeoJSON `FeatureCollection` of `LineString` features; empty array allowed |
| `amenities` | GeoJSON `FeatureCollection` of `Point` features; empty array allowed |
| `origins` | GeoJSON `FeatureCollection` of `Point` features; empty array allowed |
| `areas` | Area-level service observations; empty array allowed |
| `observations` | Dated asset claims; empty array allowed |
| `interventions` | Cost/coverage options; empty array allowed |

## Metadata

Required: `title`, `publisher`, `source_url`, `licence`, `geographic_scope`, `is_synthetic`, `observed_at`, `retrieved_at`.

- Mark `is_synthetic: true` for invented inputs. Non-synthetic data require a credential-free HTTPS `source_url`. Imported records remain user-supplied and independently unverified.
- Use ISO dates `YYYY-MM-DD`, or `null` when observation/retrieval time is unknown. Dates after the selected review date are rejected. A retrieval date is not an observation date.
- Identify the exact geographic unit and boundary version. An analysis extent or representative point is not a legally recognised settlement boundary or household entrance.
- Describe reuse permission in `licence`. Passing validation does not confer permission. Use `limitations` to record uncertainty, source coverage and unresolved access questions.

## Geometry and walking network

All geometry uses **WGS84 `[longitude, latitude]`**. IDs must be unique within each feature collection. Lines have at least two finite coordinates.

Network properties:

- `highway`: OSM-style road/path class, e.g. `footway`, `residential`, `service`, `steps`.
- `node_ids`: optional array of source node identifiers matching every line vertex. Shared IDs establish connections. Contradictory coordinates for one ID are rejected.
- `foot`, `access`, `oneway:foot`, `layer`, `bridge`, `tunnel`: supplied walking/topology attributes. A motor-vehicle `oneway` flag is not automatically applied to pedestrians.
- Without node IDs, only identical coordinates **on the same supplied layer** connect. Geometric crossings are not automatically joined. Source topology, bridges and barriers need inspection.

The prototype excludes motorways, private/no pedestrian access and primary roads without explicit walking permission. “Avoid mapped steps” removes step features; it does not establish wheelchair accessibility. Restrictions can be incomplete in source data.

Routes snap to **graph vertices**, not nearest segments. The maximum snap distance is explicit. This can overestimate routes or yield unavailable results. Connector segments are unverified; they must not cross barriers in an operational appraisal. Facilities with no mapped path are not assumed absent. Limits: 3,000 lines, 30,000 vertices, 500 amenities, 100 origins.

## Amenities and origins

Amenity properties require `name` and `category`. Categories: `toilets`, `water_point`, `clinic`, `school`, `transport_stop`. `access: private` or `no` excludes the amenity from candidate access. Optional `source_url`, `osm_url`, `observation_date`, `location_type` preserve per-feature provenance.

A representative facility point may not be a public entrance. Presence does not establish hours, fees, capacity, admissions, operating status or safe access. Origins represent explicitly chosen analysis points, not assumed household distributions. Do not upload precise household locations.

## Area service observations

Each area record requires:

```json
{
  "id": "public-analysis-area-id",
  "name": "Area label",
  "water_deficit": null,
  "sanitation_deficit": null,
  "waste_deficit": null,
  "observed_at": null,
  "source_url": "https://authoritative.example/public-evidence",
  "method": "Explain the source population, denominator, date window and 0–1 normalisation anchors."
}
```

Deficits must be **0–1**, with **0 meaning no measured deficit on the stated criterion** and **1 the maximum under the documented measurement definition**. Use `null` for unknown; never encode missing evidence as zero. Do not substitute historical ward averages, imagery or population models for current area/household observations. Comparisons need compatible measurement definitions and geographic units. Limit: 1,000 area records.

Weighted scores show each contribution. Unknown criteria span 0–1, creating a lower/upper score bound. Entirely unobserved rows receive no deprivation position. Position bounds include uncertainty and ties; the table order by lower bound is not an approved intervention order. Sensitivity tests include complete rows only and use competition ranks for ties.

## Asset observations

Each claim requires `id`, `asset_id`, `service_type`, `observed_at`, `value`, `evidence_type`, `source_url`; `note` is optional. Values: `working`, `not_working`, `unknown`. Types: `official_record`, `operator_claim`, `independent_observation`, `resident_report`.

Contradictory values for the **same asset, service and date** remain visible. Different dates/services are not automatically contradictions. An “independent observation” label is a supplied claim, not verified by software. Photographs and one-time observations cannot certify structural completion, potable water or continuous service. Limit: 1,000 claims.

## Maintenance scenarios

Each option requires `id`, `label`, nonnegative finite `cost`, `coverage_ids` array, explicit boolean `feasible`, and `assumption_label`. Maximum 18 options for exact enumeration, with a combined workload limit: `2^(feasible options − 1) × total feasible coverage references ≤ 5,000,000`. Oversized inputs are rejected before synchronous enumeration. The objective maximises distinct supplied coverage IDs under budget and then prefers lower cost. The greedy comparator uses incremental coverage per cost. Overlap is deduplicated.

Coverage IDs are abstract input units, not verified households. No housing eligibility, resident allocation, relocation, legal consent or compensation decision is modelled. Identify invented costs as synthetic and retain actual estimate versions if real data become available. The model omits O&M, causal impact, engineering approval and financing feasibility.

## Privacy and exports

Do not upload resident names, household IDs, Aadhaar, phone/email, bank details, caste, religion or patient records. Recognised sensitive field names and unsafe object keys are rejected, but this is **not a complete personal-data detector**. The user must inspect the file. Imported data stay in memory until the page is closed/refreshed; no login, shared database or production access control is provided.

Exports retain metadata, the input-file SHA-256 when browser cryptography is available, parameters, score bounds, conflicts, hypothetical maintenance results and limitations. Ranking CSV rows repeat synthetic status, review date, normalised weights, dataset title/licence and input hash, so the table remains interpretable separately from its JSON brief. Keep exported files subject to the same permissions as their inputs. No export submits a grievance or records an official decision.
