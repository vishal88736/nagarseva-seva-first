# Public acquisition receipts

Accessed 18 October 2026 (local date; receipt timestamps use UTC).

- `official-template-access.json`: the official Seva First template was downloaded, ZIP/package checked and SHA-256 recorded. Its six source slides were inspected before adaptation. The final editable deck and raster PDF viewing copy are in `submission/outputs/`.
- `mumbai-context-attempts.json`: a bounded road/amenity query timed out on the main Overpass provider and returned HTTP 500 on the alternate documented provider. No GeoJSON was acquired or validated. `mumbai-context-access.json` is the latest runner outcome.
- A further small bus-stop query through the web reader was not accessible through that tool. It is not evidence of a valid zero-result dataset or of a server-wide outage.

The providers and usage guidance were checked through the [OSM Overpass instance list](https://wiki.openstreetmap.org/wiki/Overpass_API) and [Overpass commons guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html), accessed 18 October 2026. No public Overpass service is used as the live application backend. No bulk tiles were downloaded.

The already-acquired three SRA listing records remain a separate [real desk case](../public_record_case.md). They supply neither permitted settlement geometry nor current service measurements. The five application clusters and their walking graph remain synthetic. A failed public request must never be replaced with invented map or service records.
