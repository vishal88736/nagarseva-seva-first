"""Acquire a small, repeatable Overpass pilot, retaining actual tags and geometry."""
from __future__ import annotations
import argparse
import json
from collections import Counter
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from shapely.geometry import Point, Polygon, LineString, box, mapping
from data_common import Downloader, DownloadError, META, PROCESSED, PILOT_BBOX, inventory, utcnow, validate_features, write_json

ENDPOINTS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
MAP_API = "https://www.openstreetmap.org/api/0.6/map"


def query_text(bbox=PILOT_BBOX):
    w, s, e, n = bbox
    area = f"({s},{w},{n},{e})"
    return f'''[out:json][timeout:25][maxsize:20000000];
(
  way[highway]{area};
  way[building]{area};
  nwr[amenity~"^(school|college|kindergarten|hospital|clinic|doctors|toilets|drinking_water|water_point|public_bath|bus_station)$"]{area};
  nwr[public_transport]{area};
  nwr[railway~"^(station|halt|tram_stop)$"]{area};
  node[highway=bus_stop]{area};
  nwr[man_made~"^(water_tap|water_well|water_works|wastewater_plant)$"]{area};
  way[landuse=residential]{area};
);
out geom meta;'''


def category(tags):
    if "amenity" in tags:
        return "amenity"
    if tags.get("highway") == "bus_stop" or "public_transport" in tags or "railway" in tags:
        return "transport"
    if "highway" in tags:
        return "road"
    if "building" in tags:
        return "building"
    if tags.get("landuse") == "residential":
        return "residential_context"
    return "water_infrastructure"


def parse_osm(data, bbox=PILOT_BBOX):
    if not isinstance(data.get("elements"), list) or data.get("remark"):
        raise ValueError("Missing elements array or incomplete Overpass response: " + str(data.get("remark")))
    if len(data["elements"]) > 30_000:
        raise ValueError("Response exceeds feature limit")
    features, rejected, seen = [], [], set()
    clip = box(*bbox)
    for element in data["elements"]:
        identifier = f"{element['type']}/{element['id']}"
        if identifier in seen:
            raise ValueError("Duplicate OSM element ID: " + identifier)
        seen.add(identifier)
        tags = element.get("tags", {})
        try:
            if element["type"] == "node":
                geom = Point(element["lon"], element["lat"])
            elif element["type"] == "way":
                coords = [(point["lon"], point["lat"]) for point in element.get("geometry", [])]
                if len(coords) < 2:
                    raise ValueError("Incomplete way geometry")
                is_area = coords[0] == coords[-1] and len(coords) >= 4 and tags.get("area") != "no" and ("building" in tags or "landuse" in tags or tags.get("area") == "yes" or "amenity" in tags)
                geom = Polygon(coords) if is_area else LineString(coords)
            else:
                # Relations need topology-aware ring assembly; do not substitute a centre for a boundary.
                raise ValueError("Relation topology not supported; retained in raw only")
            if not geom.is_valid or geom.is_empty:
                raise ValueError("Invalid geometry; retained without silent repair")
            clipped = geom.intersection(clip)
            if clipped.is_empty:
                continue
            features.append({"type": "Feature", "id": identifier, "geometry": mapping(clipped), "properties": {
                "source_id": identifier, "name": tags.get("name"), "category": category(tags), "tags": tags,
                "source_url": "https://www.openstreetmap.org/" + identifier,
                "osm_edit_timestamp": element.get("timestamp"), "observation_date": None,
                "clipped": not clipped.equals(geom), "synthetic": False}})
        except (ValueError, KeyError) as exc:
            rejected.append({"source_id": identifier, "reason": str(exc)})
    collection = {"type": "FeatureCollection", "features": features}
    quality = validate_features(collection)
    if not quality["valid"]:
        raise ValueError("Processed OSM geometry validation failed")
    return collection, quality, rejected


def parse_map_xml(raw):
    root = ET.fromstring(raw)
    if root.tag != "osm":
        raise ValueError("Expected OSM XML map response")
    nodes = {n.attrib["id"]: {"lon": float(n.attrib["lon"]), "lat": float(n.attrib["lat"])} for n in root.findall("node")}
    elements = []
    for row in root:
        if row.tag not in ("node", "way", "relation"):
            continue
        tags = {t.attrib["k"]: t.attrib["v"] for t in row.findall("tag")}
        amenity = tags.get("amenity") in {"school", "college", "kindergarten", "hospital", "clinic", "doctors", "toilets", "drinking_water", "water_point", "public_bath", "bus_station"}
        keep = amenity or "highway" in tags or "building" in tags or "public_transport" in tags or tags.get("railway") in {"station", "halt", "tram_stop"} or tags.get("man_made") in {"water_tap", "water_well", "water_works", "wastewater_plant"} or tags.get("landuse") == "residential"
        if not keep:
            continue
        item = {"type": row.tag, "id": int(row.attrib["id"]), "timestamp": row.attrib.get("timestamp"), "tags": tags}
        if row.tag == "node":
            item.update(nodes[row.attrib["id"]])
        elif row.tag == "way":
            try:
                item["geometry"] = [nodes[n.attrib["ref"]] for n in row.findall("nd")]
            except KeyError as exc:
                raise ValueError("OSM way references a missing node") from exc
        elements.append(item)
    return {"elements": elements}


def ingest(refresh=False):
    downloader = Downloader("osm", refresh)
    report = {"attempted_at": utcnow(), "bbox": PILOT_BBOX, "query": query_text(), "errors": [], "source": "OpenStreetMap contributors", "licence": "ODbL-1.0", "attribution_url": "https://www.openstreetmap.org/copyright"}
    write_json(META / "osm_query.json", {"query": query_text(), "bbox_wsen": PILOT_BBOX, "endpoints": ENDPOINTS})
    # Keep the catalogue evidence, but never acquire the 1.6GB India extract for this pilot.
    try:
        raw, info = downloader.fetch("https://download.geofabrik.de/asia/india.html", "geofabrik-india", suffix=".html")
        page = BeautifulSoup(raw, "html.parser")
        report["geofabrik"] = info
        inventory(dataset_name="Geofabrik India download catalogue", publisher="Geofabrik / OpenStreetMap contributors", source_url=info["url"], retrieved_at=info["retrieved_at"],
                  format="HTML", fields=["subregions", "extract links", "extract timestamps and sizes"], licence="OSM data ODbL-1.0", access_status="metadata_only",
                  validation_status="HTML parsed: " + (page.title.get_text() if page.title else "catalogue page"), intended_use="Choose extract size; no large extract downloaded",
                  limitations="Catalogue offers India/zonal extracts; bounded public map API is much smaller for this pilot")
    except DownloadError as exc:
        report["errors"].append(str(exc))
    endpoints = [*ENDPOINTS, MAP_API]
    previous = META / "osm_ingestion.json"
    if not refresh and previous.exists():
        cached_endpoint = json.loads(previous.read_text()).get("request", {}).get("url")
        if cached_endpoint in endpoints:
            endpoints.remove(cached_endpoint); endpoints.insert(0, cached_endpoint)
    for endpoint in endpoints:
        try:
            if endpoint == MAP_API:
                raw, info = downloader.fetch(endpoint, "pilot-map-api", {"bbox": ",".join(map(str, PILOT_BBOX))}, suffix=".osm")
                result = parse_map_xml(raw)
            else:
                result, info = downloader.json(endpoint, f"pilot-{ENDPOINTS.index(endpoint)}", {"data": query_text()})
            collection, quality, rejected = parse_osm(result)
            collection["metadata"] = {"source": "OpenStreetMap contributors", "licence": "ODbL-1.0", "retrieved_at": info["retrieved_at"], "observation_date": None,
                                      "osm_base_timestamp": result.get("osm3s", {}).get("timestamp_osm_base"), "bbox": PILOT_BBOX, "request": info}
            write_json(PROCESSED / "osm_pilot.geojson", collection)
            report.update(request=info, quality=quality, rejected=rejected, counts_by_category=dict(Counter(f["properties"]["category"] for f in collection["features"])))
            inventory(dataset_name="OpenStreetMap Govandi pilot", publisher="OpenStreetMap contributors", source_url=endpoint, retrieved_at=info["retrieved_at"],
                      observation_date="Unknown; OSM edits and base timestamp are not field observation dates", geography=str(PILOT_BBOX) + " W,S,E,N; not a ward", resolution="Mapped object", format=("OSM XML" if endpoint == MAP_API else "Overpass JSON") + " -> GeoJSON EPSG:4326",
                      record_count=quality["record_count"], fields=quality["fields"], licence="ODbL-1.0; attribute OpenStreetMap contributors", access_status="downloaded",
                      validation_status="Parsed; unique IDs, coordinate bounds and geometries checked", intended_use="Roads, buildings and mapped amenities; residential context only",
                      limitations="Missing mapped features do not prove absence; mapping does not prove service functionality; relations quarantined; no household access indicator inferred")
            break
        except (DownloadError, ValueError, ET.ParseError) as exc:
            report["errors"].append({"url": endpoint, "error": str(exc)})
    else:
        inventory(dataset_name="OpenStreetMap Govandi pilot", publisher="OpenStreetMap contributors", source_url=ENDPOINTS[0], retrieved_at=utcnow(),
                  geography=str(PILOT_BBOX), format="Overpass JSON", access_status="failed", validation_status="No usable feature response", licence="ODbL-1.0", intended_use="Mapped context", limitations=report["errors"])
    write_json(META / "osm_ingestion.json", report)
    downloader.close()
    print("OSM:", report.get("counts_by_category", {}), "errors:", len(report["errors"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    ingest(parser.parse_args().refresh)
