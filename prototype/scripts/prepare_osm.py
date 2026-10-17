"""Convert an acquired Overpass JSON response to the documented prototype schema.

This script does not download data or imply that local sources were acquired.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse

TYPES = {"toilets": "toilets", "clinic": "clinic", "hospital": "clinic", "school": "school", "drinking_water": "water_point", "bus_station": "transport_stop"}


def convert(raw, source_url, retrieved_at, title):
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Provide a credential-free HTTPS source URL.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", retrieved_at):
        raise ValueError("retrieved_at must be YYYY-MM-DD.")
    dt.date.fromisoformat(retrieved_at)
    network, amenities = [], []
    for element in raw.get("elements", []):
        tags = element.get("tags", {})
        feature_id = f"osm-{element.get('type')}-{element.get('id')}"
        if element.get("type") == "way" and tags.get("highway"):
            geometry = element.get("geometry", [])
            if len(geometry) >= 2:
                props = {k: tags[k] for k in ["highway", "name", "foot", "access", "oneway:foot", "layer", "bridge", "tunnel"] if k in tags}
                if len(element.get("nodes", [])) == len(geometry):
                    props["node_ids"] = [str(n) for n in element["nodes"]]
                network.append(dict(type="Feature", id=feature_id, geometry=dict(type="LineString", coordinates=[[p["lon"], p["lat"]] for p in geometry]), properties=props))
        category = TYPES.get(tags.get("amenity"))
        if tags.get("highway") == "bus_stop" or tags.get("railway") == "station":
            category = "transport_stop"
        if not category:
            continue
        if element.get("type") == "node" and "lon" in element and "lat" in element:
            coords, location_type = [element["lon"], element["lat"]], "OSM point; public entrance not verified"
        elif "center" in element:
            coords, location_type = [element["center"]["lon"], element["center"]["lat"]], "Overpass representative centre; not a passenger/public entrance"
        else:
            continue
        props = dict(name=tags.get("name", feature_id), category=category, source_url=source_url, osm_url=f"https://www.openstreetmap.org/{element['type']}/{element['id']}", observation_date=None, location_type=location_type)
        if "access" in tags:
            props["access"] = tags["access"]
        amenities.append(dict(type="Feature", id=feature_id, geometry=dict(type="Point", coordinates=coords), properties=props))
    return dict(schema_version="1.0", metadata=dict(title=title, publisher="OpenStreetMap contributors via acquired Overpass response", source_url=source_url, licence="ODbL 1.0; © OpenStreetMap contributors; applicable attribution/database obligations", geographic_scope="Extent of supplied response; not an authoritative settlement boundary", is_synthetic=False, observed_at=None, retrieved_at=retrieved_at, snapshot_at=raw.get("osm3s", {}).get("timestamp_osm_base"), limitations="OSM database snapshot is not a survey date. Mapping completeness, pedestrian access and facility entrances/operation require independent checks."), network=dict(type="FeatureCollection", features=network), amenities=dict(type="FeatureCollection", features=amenities), origins=dict(type="FeatureCollection", features=[]), areas=[], observations=[], interventions=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--title", default="User-acquired OSM extract")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new filename.")
    raw = json.loads(args.input.read_text())
    result = convert(raw, args.source_url, args.retrieved_at, args.title)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(result['network']['features'])} network ways and {len(result['amenities']['features'])} amenity references. No field validation implied.")


if __name__ == "__main__":
    main()
