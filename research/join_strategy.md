# Defensible geographic joins

1. **SRA PDF tokens:** use the exact printed token as `source_id`, with a local
   `sra-map-` namespace for database IDs. Keep geometry null. The `ME_` prefix is
   a map-context lead, not a verified crosswalk to a current ward polygon.
2. **GIS services when reachable:** discover layer IDs, OID fields, field schemas,
   CRS and query support; request WGS84 or transform the declared CRS with
   `always_xy=True`. Namespace object IDs by service/layer. Never mix 2012 and 2016
   layer IDs or combine different vintages into an apparent current layer.
3. **Public projects:** preserve raw ward/village/CTS and proposal strings. Names,
   shared CTS `1-A`, missing proposal numbers and first-page row positions are not
   unique geographic keys. Keep `settlement_id=null` until a documented official
   crosswalk or unique, dated parcel intersection is verified. No fuzzy name join.
4. **Census:** retain the original table ID, reference year, geographic resolution
   and official unit code. The API validates a matching unit/year and rejects
   assigning an observation labelled ward/state/etc directly to a settlement.
   Historical or aggregate observations never enter current cluster scoring.
5. **OSM context:** namespace IDs as `node/…`, `way/…`, `relation/…`; preserve tags
   and edit timestamps. Unsupported relations are quarantined. Exact whole-geometry
   containment in one residential polygon is recorded as context only. Crossing,
   uncontained or overlapping objects remain unmatched; no nearest-centroid join.

`strict_spatial_join` records the method and number of candidates. Source and
processed geometries remain separate. Project/settlement layers have empty feature
collections when no geometry exists; their labels are not placed at guessed points.

No current source supports a cluster origin, entrance or street connection. The
scenario API therefore returns `access_available=false` and empty distance arrays,
not zero metres or an invented route. Metric reprojection is tested on independent
fixtures, but no unsupported distance claim is made for the acquired data.
