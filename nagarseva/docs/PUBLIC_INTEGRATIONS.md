# Public source integrations

Reviewed on 2026-10-11. Open **Public sources & weather** in the website or `/#sources/NS-0001`. The downloadable source catalog is maintained in `shared/public-sources.json` and served by `GET /sources`.

| Source | Implemented use | Coverage and limits |
| --- | --- | --- |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Interactive geographic background on existing Leaflet maps | Background geography only; marker records retain their own provenance. ODbL contributor attribution is visible. |
| [Open-Meteo](https://open-meteo.com/en/docs) | Seven-day precipitation, precipitation probability and maximum temperature by approximate area | Model forecast with retrieval time, provider grid centre and CC BY 4.0 attribution. No field observation, flood-risk score or official alert is inferred. |
| [PMAY-U 2.0 FAQ](https://pmaymis.gov.in/pmaymis2_2024/PmayFAQ.aspx) | Existing conservative pathway screening reviewed again, source library and official handoff | National guidance; local authority/lender verification remains required. |
| [CPHEEO SLB handbook](https://cpheeo.gov.in/upload/uploadfiles/files/Handbook.pdf) | Four published benchmark references on the assurance/source pages | Historical indicator definitions checked in indexed publisher content; direct PDF download timed out during review. References do not overwrite approved project commitments or certify compliance. |
| [Census 2011 slum abstract](https://censusindia.gov.in/nada/index.php/catalog/6190/study-description) | Official historical dataset reference | Town aggregates from 2011, not current pocket geometry. Direct retrieval failed certificate verification. Dataset values have not been copied. |
| [Mumbai SRA](https://sra.gov.in/onlineservices) and [BMC](https://www.mcgm.gov.in/) | Resident links to responsible official service portals | Mumbai-specific links appear for Mumbai projects. No NagarSeva complaint is submitted to an authority automatically. |
| [IMD](https://mausam.imd.gov.in/) | Official-warning handoff from weather and source pages | The publisher portal is opened separately; official warnings are not scraped or recreated. |

## Weather operation

`GET /context/{pocket_id}/weather` resolves an existing project. Only coordinates rounded to 0.1 degrees are sent to the fixed Open-Meteo endpoint. No resident text, identity, receipt, project identifier or exact household coordinate is sent. Nearby projects share a persistent SQLite cache. Fresh results last 30 minutes; failed refreshes have a 60-second retry backoff. A cached result up to 24 hours old is explicitly stale after refresh failure; past forecast dates are removed. Older results return unavailable with no sample weather.

Responses retain null measurements. Unexpected units, dates, array lengths and nonfinite/out-of-range values are rejected. The retrieval timestamp is not a model issuance timestamp. Displayed forecast context never creates pilot observations, changes a priority score or enters verified service metrics. Synthetic selected locations remain clearly labelled.

The current educational demo uses the free [noncommercial API terms](https://open-meteo.com/en/terms), with CC BY 4.0 attribution. Set `NAGARSEVA_WEATHER_ENABLED=0` to disable external forecast requests. A commercial deployment needs a permitted provider plan and corresponding provider configuration before enabling weather. No paid account was created.

## Map operation

The default URL is `https://tile.openstreetmap.org/{z}/{x}/{y}.png`. `VITE_TILE_URL` can select another OSM-derived raster provider; verify its attribution and terms when changing providers. Standard browser caching and Referer behavior are retained. There is no prefetch or offline tile download. The [OSMF tile policy](https://operations.osmfoundation.org/policies/tiles/) permits ordinary interactive viewing and provides no availability guarantee. Users can switch to the existing schematic; tile failures also select that fallback. Automated browser checks block public tile requests.

## Benchmark compatibility and reuse

Water continuity uses hours/day, but the national indicator needs appropriate operational records and representative consumer measurements. Water quantity uses litres/person/day; toilet and daily doorstep waste collection indicators use coverage percentages. They cannot be computed from this application's toilets-per-100-people or collections-per-week readings. The reference cards state these measurement limits.

The [Census website reuse policy](https://censusindia.gov.in/census.website/en/node/286) requests reproduction permission. This integration links to its dataset and records that requirement. It does not redistribute the workbook, fabricate settlement records or label historical totals as current. Licensed approved pilot records can still be imported using the existing pilot workflow.

Some government documents were available through indexed publisher content but could not be downloaded directly during review. The catalog and UI expose that limitation. A source review date is not a guarantee of continuing link availability.

Real field measurements, independent assessments, project quotations and consented usability feedback remain tasks for the project team. Public geography and forecasts cannot supply those inputs.
