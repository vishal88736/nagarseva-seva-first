"""Query only discovered SRA cluster/admin/scheme layers using bounded ID batches."""
from __future__ import annotations
import argparse
import json
import re
from shapely.geometry import Polygon, mapping
from data_common import Downloader, DownloadError, META, PROCESSED, PILOT_BBOX, inventory, utcnow, validate_features, write_json, reproject_geometry
from inspect_sra_layers import inspect


def esri_to_geojson(data, oid):
    features = []
    crs = data.get("spatialReference", {}).get("latestWkid", data.get("spatialReference", {}).get("wkid", 4326))
    for row in data.get("features", []):
        source = row.get("geometry") or {}
        if "rings" in source:
            # Even-odd ring rule preserves multipart polygons and holes irrespective of winding.
            geom = Polygon()
            for ring in source["rings"]:
                part = Polygon(ring)
                if not part.is_valid:
                    raise ValueError("Invalid source ring; no silent geometry repair")
                geom = geom.symmetric_difference(part)
            geometry = mapping(geom)
        elif "paths" in source:
            geometry = {"type": "MultiLineString", "coordinates": source["paths"]}
        elif "x" in source and "y" in source:
            geometry = {"type": "Point", "coordinates": [source["x"], source["y"]]}
        else:
            raise ValueError("Unsupported or empty ESRI geometry")
        if crs != 4326:
            geometry = reproject_geometry(geometry, f"EPSG:{crs}")
        features.append({"type": "Feature", "id": row["attributes"][oid], "geometry": geometry, "properties": row["attributes"]})
    return {"type": "FeatureCollection", "features": features}


def query_layer(downloader, base, layer, bbox=PILOT_BBOX, max_features=20_000):
    oid = layer["object_id_field"]
    if not oid:
        raise ValueError("No source object-ID field")
    params = {"f": "json", "where": "1=1", "returnIdsOnly": "true", "geometryType": "esriGeometryEnvelope",
              "geometry": ",".join(map(str, bbox)), "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"}
    ids, info = downloader.json(f"{base}/{layer['id']}/query", f"layer-{layer['id']}-ids", params)
    values = ids.get("objectIds")
    if not isinstance(values, list) or len(values) != len(set(values)):
        raise ValueError("Missing or duplicate source object IDs")
    if len(values) > max_features:
        raise ValueError("Pilot exceeds feature limit; reduce the geographic query")
    rows = []
    size = min(250, layer["max_record_count"])
    for start in range(0, len(values), size):
        batch = sorted(values)[start:start + size]
        query = {"f": "geojson", "objectIds": ",".join(map(str, batch)), "outFields": "*", "returnGeometry": "true", "outSR": "4326"}
        try:
            result, _ = downloader.json(f"{base}/{layer['id']}/query", f"layer-{layer['id']}-batch-{start}", query)
            if result.get("type") != "FeatureCollection":
                raise DownloadError("GeoJSON was not returned")
        except DownloadError:
            query["f"] = "json"
            result, _ = downloader.json(f"{base}/{layer['id']}/query", f"layer-{layer['id']}-esri-{start}", query)
            result = esri_to_geojson(result, oid)
        if result.get("exceededTransferLimit") or len(result["features"]) != len(batch):
            raise ValueError("Incomplete feature batch; refused to publish a partial layer")
        for feature in result["features"]:
            feature["id"] = feature["properties"].get(oid)
        rows.extend(result["features"])
    collection = {"type": "FeatureCollection", "features": rows}
    types = {"esriGeometryPolygon": {"Polygon", "MultiPolygon"}, "esriGeometryPolyline": {"LineString", "MultiLineString"}, "esriGeometryPoint": {"Point"}, "esriGeometryMultipoint": {"MultiPoint"}}
    quality = validate_features(collection, oid, types.get(layer.get("geometry_type")))
    if not quality["valid"] or set(str(f["properties"][oid]) for f in rows) != set(map(str, values)):
        raise ValueError("Feature identifiers or geometries failed validation")
    return collection, quality, info


def ingest(refresh=False):
    path = META / "sra_layers.json"
    metadata = json.loads(path.read_text()) if path.exists() and not refresh else inspect(refresh)
    downloader = Downloader("sra", refresh)
    report = {"attempted_at": utcnow(), "bbox": PILOT_BBOX, "layers": [], "errors": []}
    for layer in metadata.get("layers", []):
        if not re.search(r"cluster|slum declaration|ward|village|scheme", layer["name"], re.I) or not layer.get("query_supported"):
            continue
        name = "SRA GIS " + layer["name"]
        try:
            collection, quality, request = query_layer(downloader, metadata["service_url"], layer)
            output = PROCESSED / f"sra_layer_{layer['id']}.geojson"
            write_json(output, collection)
            report["layers"].append({"layer": layer, "path": str(output), "quality": quality, "request": request})
            year = re.search(r"20\d{2}", layer["name"])
            inventory(dataset_name=name, publisher="SRA / NIC", source_url=f"{metadata['service_url']}/{layer['id']}", retrieved_at=request["retrieved_at"],
                      observation_date=year[0] + " (layer label only; observation date unknown)" if year else "Unknown",
                      geography="Govandi bounded pilot; intersecting whole geometries", resolution="Source feature", format="GeoJSON EPSG:4326", record_count=quality["record_count"],
                      fields=quality["fields"], licence="Not established; retain locally, review reuse before redistribution", access_status="downloaded", validation_status="IDs, count and geometries validated",
                      intended_use="Historical footprints / administrative context / scheme locations", limitations="Not current legal status or measured service access")
        except (DownloadError, ValueError) as exc:
            report["errors"].append({"layer": layer["id"], "error": str(exc)})
            inventory(dataset_name=name, publisher="SRA / NIC", source_url=metadata["service_url"], retrieved_at=utcnow(), access_status="failed", validation_status="not activated", limitations=str(exc))
    if not metadata.get("layers"):
        report["errors"].append({"error": "No live SRA metadata; layer IDs and feature counts remain unverified"})
    write_json(META / "sra_ingestion.json", report)
    downloader.close()
    print(f"SRA features: {sum(r['quality']['record_count'] for r in report['layers'])}; errors: {len(report['errors'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    ingest(parser.parse_args().refresh)
